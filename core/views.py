"""Файл со всеми вьюхами приложения"""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from core.utils.parsers import WbParser
from core.models import Product, Shop, Offer
from core.utils.product_utils import get_fresh_offers_for_product, save_parsed_offer
from core.utils.string_utils import normalize_name


MAX_AGE_HOURS = 2


def query_search(request: HttpRequest) -> HttpResponse:
    """
    Поиск товаров по названию с гибридным кешированием.
    1. Нормализует запрос и ищет Product в БД.
    2. Если есть свежие (не старше MAX_AGE_HOURS) предложения – возвращает их.
    3. Если не хватает – запускает парсер, сохраняет новые предложения и объединяет результаты.

    Параметры GET:
        query (str) – поисковый запрос.
        limit (int, по умолч. 20) – количество товаров (1–30).
        price_min (int, по умолч. 0) – минимальная цена.
        price_max (int, по умолч. 999999) – максимальная цена.
        delivery_days (int, по умолч. 9999) – максимальный срок доставки в днях.

    :param request: HTTP-запрос
    :type request: HttpRequest
    :return: HTML-фрагмент с карточками товаров или сообщением об ошибке
    :rtype: HttpResponse
    """
    try:
        query: str = request.GET.get('query', '').strip()
        if not query:
            return render(request, 'core/partials/search_results.html', {'offers': []})

        try:
            limit: int = int(request.GET.get('limit', 20))
            limit = max(1, min(limit, 30))
        except ValueError:
            limit = 20

        try:
            price_min: int = int(request.GET.get('price_min', 0))
            price_min = max(0, price_min)
        except ValueError:
            price_min = 0

        try:
            price_max: int = int(request.GET.get('price_max', 999999))
            price_max = min(999999, price_max)
        except ValueError:
            price_max = 999999

        try:
            delivery_days: int = int(request.GET.get('delivery_days', 9999))
            delivery_days = max(1, min(delivery_days, 999))
        except ValueError:
            delivery_days = 9999

        normalized_query: str = normalize_name(query)
        product: Product = Product.objects.filter(normalized_name=normalized_query).first()

        fresh_offers: list[Offer] = []
        if product:
            fresh_offers = get_fresh_offers_for_product(product, max_age_hours=MAX_AGE_HOURS)
            fresh_offers = [o for o in fresh_offers if price_min <= o.price <= price_max]

        if len(fresh_offers) >= limit:
            fresh_offers.sort(key=lambda o: o.price)
            return render(request, 'core/partials/search_results.html', {'offers': fresh_offers[:limit]})

        needed: int = limit - len(fresh_offers)
        fetch_cnt: int = min(needed, 30)
        existing_keys: set[tuple[str, str | None]] = {(o.shop.slug, o.article) for o in fresh_offers}

        shop, _ = Shop.objects.get_or_create(
            slug='wb',
            defaults={
                'name': 'Wildberries',
                'search_url_template': 'https://www.wildberries.ru/catalog/0/search.aspx?search={query}'
            }
        )

        parser_result: list[dict[str, str | bool | float]] = WbParser.search_by_query(
            query=query,
            answer_cnt=fetch_cnt,
            price_limit=[price_min, price_max] if price_min > 0 or price_max < 999999 else None,
            delivery_limit=delivery_days if delivery_days < 9999 else None
        )

        if not parser_result or (isinstance(parser_result, dict) and 'error' in parser_result):
            return render(request, 'core/partials/search_results.html', {'offers': fresh_offers})

        new_offers: list[Offer] = []
        for parsed in parser_result:
            key: tuple[str, str | bool | float | None] = (shop.slug, parsed.get('article_number'))
            if key in existing_keys:
                continue
            offer: Offer = save_parsed_offer(parsed, shop)
            new_offers.append(offer)
            existing_keys.add(key)

        all_offers: list[Offer] = fresh_offers + new_offers
        all_offers.sort(key=lambda o: o.price)
        result_offers: list[Offer] = all_offers[:limit]

        return render(request, 'core/partials/search_results.html', {'offers': result_offers})

    except Exception:
        return HttpResponse(status=500)
