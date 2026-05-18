"""Утилиты для работы с продуктами (поиск, создание, обновление)"""
from datetime import timedelta, date

from django.utils import timezone
from django.utils.text import slugify
from rapidfuzz import fuzz

from core.models import Product, Offer, Shop, PriceHistory
from core.utils.string_utils import normalize_name, str_in_date, clean_product_name


def get_or_create_product_by_name(name: str, similarity_threshold: float = 0.7) -> Product:
    """
    Находит существующий Product по нормализованному имени или создаёт новый.
    Сначала ищет точное совпадение normalized_name, затем нечёткое (difflib).
    При нахождении похожего обновляет оригинальное имя.

    :param name: Исходное название товара (от парсера)
    :type name: str
    :param similarity_threshold: Порог схожести для нечёткого поиска (0..1), default 0.77
    :type similarity_threshold: float
    :return: Объект Product (существующий или новый)
    :rtype: Product
    """
    cleaned_name = clean_product_name(name)
    if not cleaned_name:
        cleaned_name = name or "Unknown product"

    normalized = normalize_name(cleaned_name)
    product = Product.objects.filter(normalized_name=normalized).first()
    if product:
        return product

    all_products = Product.objects.all()
    best_match = None
    best_ratio = 0.0
    for p in all_products:
        ratio = fuzz.token_sort_ratio(normalized, p.normalized_name) / 100.0
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = p
    if best_match and best_ratio >= similarity_threshold:
        return best_match

    base_slug = slugify(cleaned_name)
    slug = base_slug
    counter = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return Product.objects.create(
        name=cleaned_name,
        slug=slug,
        normalized_name=normalized
    )


def get_fresh_offers_for_product(product: Product, max_age_hours: int = 2) -> list[Offer]:
    """
    Возвращает список Offer продукта, обновлённых не позже max_age_hours часов,
    отсортированных по возрастанию цены.

    :param product: Объект Product
    :type product: Product
    :param max_age_hours: Максимальный возраст данных в часах
    :type max_age_hours: int
    :return: Список объектов Offer (может быть пустым)
    :rtype: Offer
    """
    cutoff: datetime = timezone.now() - timedelta(hours=max_age_hours)
    return list(product.offers.filter(last_updated__gte=cutoff, is_active=True).order_by('price'))


def save_parsed_offer(parsed: dict[str, str | bool | float], shop: Shop) -> Offer:
    """
    Сохраняет один спарсенный товар (словарь от парсера) в БД.
    Создаёт или обновляет Product, Offer и PriceHistory.

    :param parsed: Словарь с данными товара (name, article_number, url, price, availability)
    :type parsed: dict[str, str | bool | float]
    :param shop: Магазин предложения
    :type shop: Shop
    :return: Объект Offer (созданный или обновлённый)
    :rtype: Offer
    """
    product: Product = get_or_create_product_by_name(parsed['name'])

    offer, created = Offer.objects.update_or_create(
        url=parsed['url'],
        defaults={
            'product': product,
            'shop': shop,
            'article': parsed['article_number'],
            'price': parsed['price'],
            'delivery_days': (str_in_date(parsed['delivery_time']) - date.today()).days,
            'in_stock': parsed['availability'],
            'is_active': True,
            'title': parsed['name'],
        }
    )

    if not created:
        offer.last_updated = timezone.now()
        offer.save()

    last_history = offer.price_history.first()
    if not last_history or last_history.price != parsed['price']:
        PriceHistory.objects.create(offer=offer, price=parsed['price'], in_stock=parsed['availability'])

    return offer
