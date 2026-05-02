"""Файл со всеми вьюхами приложения"""
from copy import deepcopy
from urllib.parse import urlparse
from difflib import SequenceMatcher
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from core.utils.parsers import OzonParser, WbParser, YandexMarketParser, AbstractParser
from core.models import Product, Shop, Offer
from core.utils.product_utils import save_parsed_offer
from core.utils.string_utils import normalize_name


MIN_PRODUCTS_CNT = 8
PARSERS_BY_SLUG = {
    'wb': WbParser,
    'ozon': OzonParser,
    'yandex': YandexMarketParser,
}


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


def query_search(request: HttpRequest) -> HttpResponse:
    """
    Поиск товаров по названию с гибридным кешированием.
    1. Нормализует запрос и ищет Product в БД.
    2. Если есть свежие (не старше MAX_AGE_HOURS) предложения – возвращает их.
    3. Если не хватает – запускает парсер, сохраняет новые предложения и объединяет результаты.

    Параметры GET (на данный момент не используются для фильтрации, но оставлены для будущего):
        query (str) – поисковый запрос.
        limit (int) – количество товаров (1–30), по умолчанию 20.
        price_min (int) – минимальная цена.
        price_max (int) – максимальная цена.
        delivery_days (int) – максимальный срок доставки в днях.

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
        best_ratio: float = 0.8
        for p in all_products:
            ratio = SequenceMatcher(None, query, p.normalized_name).ratio()
            if ratio >= best_ratio:
                add_product_in_matches(p, best_matches)

        best_matches = sorted(best_matches, key=lambda x: x['min_price'])
        if len(best_matches) >= 8:
            return render(request, 'core/partials/search_results.html', context={'products': best_matches[:MIN_PRODUCTS_CNT]})

        limit: int = max(MIN_PRODUCTS_CNT - len(best_matches), 0)
        while limit > 0:
            old_matches: list[dict[str, Product | int | set[str]]] = deepcopy(best_matches)
            for sl, shop in PARSERS_BY_SLUG.items():
                if limit <= 0:
                    break
                parsed: list[dict[str, float | str | bool]] = shop.search_by_query(query, answer_cnt=limit)
                if not parsed or (isinstance(parsed, dict) and 'error' in parsed):
                    continue

                parsed_products: set[Product] = set()
                for offer in parsed:
                    if Offer.objects.filter(article_number=offer['article_number'], url=offer['url']):
                        continue
                    shop_obj, _ = Shop.objects.get_or_create(slug=sl, defaults={'name': offer['marketplace']})
                    parsed_offer = save_parsed_offer(offer, shop_obj)
                    if parsed_offer.product.id not in [m['product'].id for m in best_matches]:
                        parsed_products.add(parsed_offer.product)

                for p in parsed_products:
                    add_product_in_matches(p, best_matches)
                    limit -= 1

            if best_matches == old_matches:
                break

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
