"""Утилиты для работы сс продуктами"""
from difflib import SequenceMatcher
from datetime import timedelta

from django.utils import timezone
from django.utils.text import slugify

from core.models import Product, Offer, Shop, PriceHistory
from core.utils.string_utils import normalize_name


def get_or_create_product_by_name(name: str, similarity_threshold: float = 0.85) -> Product:
    """
    

    :param name: _description_
    :type name: str
    :param similarity_threshold: _description_, defaults to 0.85
    :type similarity_threshold: float, optional
    :return: _description_
    :rtype: Product
    """
    normalized = normalize_name(name)
    product = Product.objects.filter(normalized_name=normalized).first()
    if product:
        if product.name != name:
            product.name = name
            product.save()
        return product

    # нечёткий поиск (если точного совпадения нет)
    all_products = Product.objects.all()
    best_match = None
    best_ratio = 0.0
    for p in all_products:
        ratio = SequenceMatcher(None, normalized, p.normalized_name).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = p
    if best_match and best_ratio >= similarity_threshold:
        if best_match.name != name:
            best_match.name = name
            best_match.save()
        return best_match

    return Product.objects.create(
        name=name,
        slug=slugify(name),
        normalized_name=normalized
    )


def get_fresh_offers_for_product(product: Product, max_age_hours: int = 2):
    """
    

    :param product: _description_
    :type product: Product
    :param max_age_hours: _description_, defaults to 2
    :type max_age_hours: int, optional
    :return: _description_
    :rtype: _type_
    """
    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    return list(product.offers.filter(last_updated__gte=cutoff, is_active=True).order_by('price'))


def save_parsed_offer(parsed: dict, shop: Shop) -> Offer:
    """
    

    :param parsed: _description_
    :type parsed: dict
    :param shop: _description_
    :type shop: Shop
    :return: _description_
    :rtype: Offer
    """
    product = get_or_create_product_by_name(parsed['name'])
    offer, created = Offer.objects.get_or_create(
        product=product,
        shop=shop,
        article=parsed['article_number'],
        defaults={
            'url': parsed['url'],
            'price': parsed['price'],
            'in_stock': parsed['availability'],
            'is_active': True,
        }
    )
    if not created:
        offer.price = parsed['price']
        offer.in_stock = parsed['availability']
        offer.last_updated = timezone.now()
        offer.save()

    last_history = offer.price_history.first()
    if not last_history or last_history.price != parsed['price']:
        PriceHistory.objects.create(offer=offer, price=parsed['price'], in_stock=parsed['availability'])
    return offer
