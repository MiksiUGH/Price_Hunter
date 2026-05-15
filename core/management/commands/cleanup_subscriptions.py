"""Файл с кастомной командой для удалений давно неактивных подписок на предложения"""
from datetime import timedelta, datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Subscription


class Command(BaseCommand):
    """
    Django-команда для очистки неактивных подписок

    Команда выполняет поиск и удаление подписок, которые:
    * Имеют статус is_active=False
    * Не обновлялись более 30 дней
    * Больше не используются пользователями
    """
    help = 'Удаление подписок на товары, которые неактивны более 30 дней...'

    def handle(self, *args, **options) -> None:
        """
        Основной метод обработки команды

        Выполняет следующие действия:
        1. Определяет временную границу для поиска устаревших записей
        2. Находит все подписки, удовлетворяющие критериям удаления
        3. Удаляет найденные записи
        4. Выводит информацию о количестве удаленных записей
        """
        threshold: datetime = timezone.now() - timedelta(days=30)
        count, _ = Subscription.objects.filter(is_active=False, updated_at__lt=threshold).delete()
        self.stdout.write(self.style.SUCCESS(f'Удалено {count} старых неактивных подписок'))
