"""Файл со всеми вьюхами приложения"""
from urllib.parse import urlparse
from difflib import SequenceMatcher
from json import loads

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View
from django.db.models.query import QuerySet
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView

from core.utils.parsers import OzonParser, WbParser, YandexMarketParser, AbstractParser
from core.models import Product, Shop, Offer, Subscription, UserSetting
from core.utils.product_utils import save_parsed_offer
from core.utils.string_utils import normalize_name
from core.forms import EditProfileForm, CustomRegistrationForm, CustomLoginForm, CustomPasswordChangeForm


CACHE_PRODUCTS_THRESHOLD: int = 8
PARSERS_BY_SLUG: dict[str, AbstractParser] = {
    'wb': WbParser,
    'ozon': OzonParser,
    'yandex': YandexMarketParser,
}
USER_SETTINGS_VALUES: dict[str, set[str | int | bool]] = {
    'theme': ('dark', 'light'),
    'cur': ('RUB', 'USD', 'EUR', 'KZT'),
    'inter': (24, 48, 72, 96),
    'email': (True, False),
}


# Вспомогательные функции
def get_shop_and_parser_by_url(url: str) -> tuple[str | None, AbstractParser | None]:
    """
    Определяет магазин (slug) и соответствующий класс парсера по URL товара.

    :param url: Полный URL страницы товара
    :type url: str
    :return: Кортеж (slug магазина, класс парсера) или (None, None) если магазин не поддерживается.
    :rtype: tuple[str | None, AbstractParser | None]
    """
    domain = urlparse(url).netloc.lower()
    if 'wildberries' in domain:
        return 'wb', WbParser
    if 'ozon' in domain:
        return 'ozon', OzonParser
    if 'yandex' or 'market' in domain:
        return 'yandex', YandexMarketParser
    return None, None


def add_product_in_matches(p: Product, matches: list) -> None:
    """
    Формирует структуру данных для продукта и добавляет её в список matches.

    Структура содержит сам продукт, минимальную и максимальную цену среди его активных предложений,
    количество предложений и набор магазинов.

    :param p: Объект Product
    :type p: Product
    :param matches: Список, в который будет добавлен словарь с данными продукта
    :type matches: list
    """
    offers = p.offers.filter(is_active=True)
    if not offers:
        return
    product: dict[str, Product | int | set[str]] = {
        'product': p,
        'min_price': int(min([o.price for o in offers])),
        'max_price': int(max([o.price for o in offers])),
        'offers_cnt': offers.count(),
        'shops': {o.shop.name for o in offers},
    }
    matches.append(product)


def check_name_matches(name1: str, name2: str, best_ratio: float = 0.8) -> bool:
    """
    Сравнивает 2 имени на похожесть

    :param name1: Первое имя
    :type name1: str
    :param name2: Второе имя
    :type name2: str
    :param best_ratio: Порог схожести, default 0.8
    :type best_ratio: float
    :return: True, если имена схожи
    :rtype: bool
    """
    ratio = SequenceMatcher(None, name1, name2).ratio()
    if ratio >= best_ratio:
        return True
    return False


# Основные view-функции
def query_search(request: HttpRequest) -> HttpResponse:
    """
    Поиск товаров по названию с гибридным кешированием.
    1. Нормализует запрос и ищет Product в БД.
    2. Если есть свежие (не старше MAX_AGE_HOURS) предложения – возвращает их.
    3. Если не хватает – запускает парсер, сохраняет новые предложения и объединяет результаты.

    Параметры GET:
        query (str) – поисковый запрос.

    :param request: HTTP-запрос.
    :type request: HttpRequest
    :return: HTML-фрагмент с карточками продуктов или сообщение об ошибке.
    :rtype: HttpResponse
    """
    try:
        query: str = normalize_name(request.GET.get('query', '').strip())
        if not query:
            return render(request, 'core/partials/search_results.html', {'products': []})

        all_products: QuerySet[Product] = Product.objects.all()
        best_matches: list[dict[str, Product | int | set[str]]] = []
        for p in all_products:
            if check_name_matches(query, p.normalized_name):
                add_product_in_matches(p, best_matches)

        if best_matches:
            best_matches = sorted(best_matches, key=lambda x: x['min_price'])

        if len(best_matches) >= 8:
            return render(request, 'core/partials/search_results.html', context={'products': best_matches})

        limit: int = max(CACHE_PRODUCTS_THRESHOLD - len(best_matches), 1)
        for sl, shop in PARSERS_BY_SLUG.items():
            if limit <= 0:
                break
            parsed: list[dict[str, float | str | bool]] = shop.search_by_query(query, answer_cnt=limit * 2)
            if not parsed or (isinstance(parsed, dict) and 'error' in parsed):
                continue

            for offer in parsed:
                if Offer.objects.filter(article_number=offer['article_number'], url=offer['url']):
                    continue
                shop_obj, _ = Shop.objects.get_or_create(slug=sl, defaults={'name': offer['marketplace']})
                save_parsed_offer(offer, shop_obj)

        all_products = Product.objects.all()
        best_matches.clear()
        for p in all_products:
            if check_name_matches(query, p.normalized_name):
                add_product_in_matches(p, best_matches)

        best_matches = sorted(best_matches, key=lambda x: x['min_price'])
        return render(request, 'core/partials/search_results.html', context={"products": best_matches})

    except Exception:
        return HttpResponse(status=500)


def url_search(request: HttpRequest) -> HttpResponse:
    """
    Поиск товара по прямому URL (одиночный товар).
    Получает данные через парсер, сохраняет/обновляет в БД и возвращает большую карточку товара.

    Параметры GET:
        url (str) – полный URL товара на поддерживаемом маркетплейсе.

    :param request: HTTP-запрос.
    :type request: HttpRequest
    :return: HTML-фрагмент с большой карточкой товара или сообщение об ошибке.
    :rtype: HttpResponse
    """
    try:
        query_url: str = request.GET.get('url', '').strip()
        if not query_url:
            return render(request, 'includes/core/product_big_card.html', {})

        slug, parser_class = get_shop_and_parser_by_url(query_url)
        if not slug:
            return render(request, 'includes/core/product_big_card.html', {})

        parsed: dict[str, str | bool | float] = parser_class.search_by_url(query_url)
        if not parsed or 'error' in parsed:
            return render(request, 'includes/core/product_big_card.html', {})

        shop, _ = Shop.objects.get_or_create(
            slug=slug,
            defaults={'name': parsed.get('marketplace', slug.capitalize()), 'search_url_template': ''}
        )
        offer: Offer = save_parsed_offer(parsed, shop)
        return render(request, 'includes/core/product_big_card.html', {'offer': offer})

    except Exception:
        return HttpResponse(status=500)


def product_offers(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Отображает страницу со всеми активными предложениями (Offer) для заданного продукта.
    Для авторизованных пользователей помечает избранные предложения (is_favorite).
    Вычисляет минимальную и максимальную цену среди всех предложений продукта.

    :param request: Http-запрос
    :type request: HttpRequest
    :param slug: Уникальный идентификатор (slug) продукта
    :type slug: str
    :return: HTTP-ответ с рендером шаблона core/product_offers.html
    :rtype: HttpResponse
    """
    product: Product = get_object_or_404(Product, slug=slug)

    offers: list[dict[str, Offer | bool]] = [{'offer': o, 'is_favorite': False} for o in product.offers.filter(is_active=True).select_related('shop')]
    if not offers:
        return render(request, 'core/product_offers.html', context={
            'offers': [],
            'product': product,
            'min_price': 0,
            'max_price': 0,
        })

    if request.user.is_authenticated:
        favorite_offers: set[int] = set(Subscription.objects.filter(user=request.user, is_active=True).values_list('offer_id', flat=True))
        if favorite_offers:
            for o in offers:
                if int(o['offer'].id) in favorite_offers:
                    o['is_favorite'] = True

    offers = sorted(offers, key=lambda x: x['offer'].price)
    try:
        min_price: int = min([o['offer'].price for o in offers])
        max_price: int = max([o['offer'].price for o in offers])
    except ValueError:
        min_price, max_price = 0, 0

    return render(request, 'core/product_offers.html', context={
        'offers': offers,
        'product': product,
        'min_price': min_price,
        'max_price': max_price,
    })


def edit_profile(request: HttpRequest) -> HttpResponse:
    """
    Редактирование профиля пользователя (имя, фамилия, email).
    
    GET – отображает форму с текущими данными пользователя.
    POST – обновляет поля first_name, last_name, email (с валидацией) и сохраняет.
    
    При успешном сохранении перенаправляет на страницу профиля.
    При ошибках валидации возвращает форму с сообщениями об ошибках.

    :param request: HTTP-запрос
    :type request: HttpRequest
    :return: HTML-форма (GET) или редирект/форма с ошибками (POST)
    :rtype: HttpResponse
    """
    try:
        if not request.user.is_authenticated:
            return redirect('login')

        if request.method == 'POST':
            form = EditProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                return redirect('profile')

            return render(request, 'core/edit_profile.html', context={'form': form})

        else:
            form = EditProfileForm(instance=request.user)
            return render(request, 'core/edit_profile.html', context={'form': form})

    except Exception:
        return HttpResponse(status=500)


def register(request: HttpRequest) -> HttpResponse:
    """
    Регистрация нового пользователя.

    GET – отображает форму регистрации.
    POST – создаёт нового пользователя и автоматически выполняет вход.

    :param request: HTTP-запрос
    :type request: HttpRequest
    :return: HTTP-ответ с рендером шаблона auth.html или редирект на профиль
    :rtype: HttpResponse
    """
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('profile')
    else:
        form = CustomRegistrationForm()

    context = {
        'login_form': CustomLoginForm(),
        'register_form': form,
        'register_mode': True,
    }
    return render(request, 'core/auth.html', context)


# Основные view-классы
class FavoritesView(View):
    """
    Обрабатывает операции добавления и удаления товаров из избранного (подписки).
    
    POST /favorites/<offer_id>/ – добавляет предложение в избранное.
    DELETE /favorites/<offer_id>/ – удаляет предложение из избранного.
    """
    def post(self, request: HttpRequest, offer_id: int) -> HttpResponse:
        """
        Добавляет указанное предложение в избранное текущего пользователя.
        
        Если подписка ещё не существует – создаётся новая с is_active=True.
        Если подписка уже есть, но неактивна – активируется.
        Поля target_price и last_notified_price остаются None.

        :param request: Http-запрос
        :type request: HttpRequest
        :param offer_id: ID предложения
        :type offer_id: int
        :return: HTTP-ответ со статусом 200 (успех), 401 (не авторизован) или 500 (ошибка)
        :rtype: HttpResponse
        """
        try:
            if not request.user.is_authenticated:
                return HttpResponse(status=401)

            offer = get_object_or_404(Offer, id=offer_id)
            subscription, created = Subscription.objects.get_or_create(
                user=request.user,
                offer=offer,
                defaults={
                    'target_price': None,
                    'last_notified_price': None,
                    'is_active': True,
                }
            )

            if not created:
                if not subscription.is_active:
                    subscription.is_active = True
                    subscription.save()

            return HttpResponse(status=200)

        except Exception:
            return HttpResponse(status=500)


    def delete(self, request: HttpRequest, offer_id: int) -> HttpResponse:
        """
        Удаляет указанное предложение из избранного текущего пользователя.
        
        Находит активную подписку и деактивирует её (is_active=False).
        Если подписка не найдена, возвращает 404.

        :param request: Http-запрос
        :type request: HttpRequest
        :param offer_id: ID предложения
        :type offer_id: int
        :return: HTTP-ответ со статусом 200 (успех), 401 (не авторизован), 404 (не найдено) или 500 (ошибка)
        :rtype: HttpResponse
        """
        try:
            if not request.user.is_authenticated:
                return HttpResponse(status=401)

            del_sub: Subscription = Subscription.objects.filter(user=request.user, offer_id=offer_id, is_active=True).first()
            if not del_sub:
                return HttpResponse(status=404)

            del_sub.is_active = False
            del_sub.save()

            return HttpResponse(status=200)

        except Exception:
            return HttpResponse(status=500)


class ProfileView(View):
    """
    Обрабатывает операции получения профиля пользователя.

    GET /profile/ – рендерит шаблон профиля и возвращает пользователю.
    """
    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Отображает страницу профиля пользователя с его избранными товарами.
    
        Если пользователь не авторизован – перенаправляет на страницу входа.
        Извлекает все активные подписки (избранные) текущего пользователя,
        выбирает связанные с ними предложения (Offer) и передаёт их в шаблон.

        :param request: HTTP-запрос
        :type request: HttpRequest
        :return: HTTP-ответ с рендером шаблона core/profile.html или редирект на login
        :rtype: HttpResponse
        """
        try:
            if not request.user.is_authenticated:
                return redirect('login')

            favorite_items: QuerySet[Offer] = Offer.objects.filter(
                subs__user=request.user,
                subs__is_active=True
            ).select_related('product', 'shop').order_by('price')

            context = {
                'favorite_items': favorite_items,
                'user': request.user,
            }

            unique_shops = list(set(favorite_items.values_list('shop__name', flat=True)))
            context['unique_shops'] = unique_shops

            return render(request, 'core/profile.html', context=context)

        except Exception:
            return HttpResponse(status=500)


class SettingsView(View):
    """
    Управление пользовательскими настройками (тема, валюта, интервал проверок, email-уведомления).
    
    GET /settings/ - получение текущих настроек пользователя.
    PUT /settings/ - изменение текущих настроек пользователя.
    """
    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Возвращает текущие настройки пользователя в формате JSON.
        
        Проверяет авторизацию пользователя. Если пользователь не авторизован, возвращает ошибку 401.
        Получает или создает объект настроек пользователя и возвращает его параметры.
        
        :param request: входящий HTTP-запрос
        :type request: HttpRequest
        :return: JSON-ответ с текущими настройками или ошибку
        :rtype: HttpResponse
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Unauthorized'}, status=401)

            settings, _ = UserSetting.objects.get_or_create(user=request.user)
            json_settings: dict[str, str | bool | int] = {
                'theme': settings.theme,
                'currency': settings.currency,
                'check_interval': settings.check_interval,
                'email_notifications': settings.email_notifications,
            }

            return JsonResponse(json_settings, status=200)

        except Exception:
            return HttpResponse(status=500)

    def put(self, request: HttpRequest) -> HttpResponse:
        """
        Обновляет настройки пользователя на основе переданных данных.
        
        Проверяет авторизацию пользователя. Валидирует новые настройки перед сохранением.
        Обновляет только те параметры, которые присутствуют в запросе и проходят валидацию.
        
        :param request: входящий HTTP-запрос с новыми настройками
        :type request: HttpRequest
        :return: HTTP-ответ со статусом операции
        :rtype: HttpResponse
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Unauthorized'}, status=401)

            new_settings: dict[str, str | bool | int] = loads(request.body)
            settings, _ = UserSetting.objects.get_or_create(user=request.user)

            if 'theme' in new_settings and new_settings['theme'] in USER_SETTINGS_VALUES['theme']:
                settings.theme = new_settings['theme']
            if 'currency' in new_settings and new_settings['currency'] in USER_SETTINGS_VALUES['cur']:
                settings.currency = new_settings['currency']
            if 'check_interval' in new_settings:
                try:
                    interval = int(new_settings['check_interval'])
                    if interval in USER_SETTINGS_VALUES['inter']:
                        settings.check_interval = interval
                except ValueError:
                    pass
            if 'email_notifications' in new_settings and new_settings['email_notifications'] in USER_SETTINGS_VALUES['email']:
                settings.email_notifications = new_settings['email_notifications']

            settings.save()
            return HttpResponse(status=200)

        except Exception:
            return HttpResponse(status=500)


class CustomPasswordChangeView(PasswordChangeView):
    """
    Кастомное представление для смены пароля с поддержкой AJAX-запросов.
    При AJAX-запросе возвращает JSON с результатом валидации,
    при обычном – стандартный HTML-рендер.
    """
    form_class = CustomPasswordChangeForm
    template_name = 'core/change_password.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form: CustomPasswordChangeForm) -> HttpResponse | JsonResponse:
        """
        Обрабатывает валидную форму смены пароля.

        Для AJAX-запросов (XMLHttpRequest) сохраняет пароль и возвращает JSON.
        Для обычных – вызывает родительский метод.

        :param form: Валидная форма смены пароля
        :type form: CustomPasswordChangeForm
        :return: JSON-ответ при AJAX, иначе HttpResponse
        :rtype: JsonResponse | HttpResponse
        """
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form.save()
            return JsonResponse({'status': 'success'})
        return super().form_valid(form)

    def form_invalid(self, form: CustomPasswordChangeForm) -> HttpResponse | JsonResponse:
        """
        Обрабатывает невалидную форму смены пароля.

        Для AJAX-запросов возвращает JSON с ошибками валидации (статус 400).
        Для обычных – вызывает родительский метод.

        :param form: Невалидная форма смены пароля
        :type form: CustomPasswordChangeForm
        :return: JSON-ответ при AJAX, иначе HttpResponse
        :rtype: JsonResponse | HttpResponse
        """
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)
