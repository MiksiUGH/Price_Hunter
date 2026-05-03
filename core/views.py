"""Файл со всеми вьюхами приложения"""
from urllib.parse import urlparse
from difflib import SequenceMatcher
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from core.utils.parsers import OzonParser, WbParser, YandexMarketParser, AbstractParser
from core.models import Product, Shop, Offer, Subscription
from core.utils.product_utils import save_parsed_offer
from core.utils.string_utils import normalize_name


CACHE_PRODUCTS_THRESHOLD: int = 8
PARSERS_BY_SLUG: dict[str, AbstractParser] = {
    'wb': WbParser,
    'ozon': OzonParser,
    'yandex': YandexMarketParser,
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

        all_products = Product.objects.all()
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
        query_url = request.GET.get('url', '').strip()
        if not query_url:
            return render(request, 'includes/core/product_big_card.html', {})

        slug, parser_class = get_shop_and_parser_by_url(query_url)
        if not slug:
            return render(request, 'includes/core/product_big_card.html', {})

        parsed = parser_class.search_by_url(query_url)
        if not parsed or 'error' in parsed:
            return render(request, 'includes/core/product_big_card.html', {})

        shop, _ = Shop.objects.get_or_create(
            slug=slug,
            defaults={'name': parsed.get('marketplace', slug.capitalize()), 'search_url_template': ''}
        )
        offer = save_parsed_offer(parsed, shop)
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
        return render(request, 'core/product_offers.html', context={})

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
