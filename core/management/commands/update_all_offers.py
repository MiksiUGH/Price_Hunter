"""Файл с кастомной командой для обновления предложений, которых нет в избранном"""
import logging

from django.core.management.base import BaseCommand

from core.models import Offer
from core.utils.parsers import WbParser, OzonParser, YandexMarketParser, AbstractParser


PARSERS_BY_SLUG: dict[str, AbstractParser] = {
    'wb': WbParser,
    # 'ozon': OzonParser,
    # 'yandex': YandexMarketParser,
}


class Command(BaseCommand):
    """
    Django-команда для обновления информации о торговых предложениях

    Команда выполняет массовое обновление данных о предложениях, включая:
    * Название товара
    * Текущую цену
    * Информацию о наличии
    * Сроки доставки
    """
    help = 'Обновление информации(название, цена, наличие и срок доставки) о всех предложениях'

    def handle(self, *args, **options) -> None:
        """
        Основной метод обработки команды

        Выполняет следующие действия:
        1. Получает все активные URL предложений для каждого маркетплейса
        2. Обновляет данные через соответствующие парсеры
        3. Сохраняет обновленные данные
        4. Логирует URL, которые не удалось обновить
        """
        not_updated: set[str] = set()
        for sl, parser in PARSERS_BY_SLUG.items():
            all_active_offers_urls: set[str] = set(Offer.objects.filter(is_active=True, shop__slug=sl).values_list('url', flat=True))
            if all_active_offers_urls:
                updated_offers: set[Offer] = parser.update_and_save_batch(all_active_offers_urls)
                updated_urls: set[str] = set(x.url for x in updated_offers)
                not_updated.update(set(url for url in all_active_offers_urls if url not in updated_urls))

        if not_updated:
            logging.info("Не обновлены URL:\n%s", "\n".join(not_updated))
