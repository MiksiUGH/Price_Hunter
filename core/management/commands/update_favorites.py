"""Файл с кастомной командой для обновления предложений из избранного"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.models import Subscription, UserSetting, PriceHistory, Offer


CURRENCY_SYMBOLS: dict[str, str] = {
    'RUB': '₽',
    'USD': '$',
    'EUR': '€',
    'KZT': '₸',
}


class Command(BaseCommand):
    """
    Django-команда для обновления подписок и отправки уведомлений

    Основные функции:
    * Проверка активных подписок
    * Мониторинг изменений цен и параметров товаров
    * Отправка email-уведомлений пользователям
    * Обновление статусов подписок
    """
    help = 'Обновление активных подписок на товары и отправка уведомлений юзеру при необходимости'

    def handle(self, *args, **options) -> None:
        """
        Основной метод обработки команды

        Выполняет следующие действия:
        1. Получение всех активных подписок
        2. Группировка подписок по пользователям
        3. Проверка изменений для каждой подписки
        4. Формирование и отправка уведомлений
        5. Обновление статусов подписок
        """
        all_active_subs = Subscription.objects.filter(is_active=True).select_related('user', 'offer')
        user_subs_map = defaultdict(list)
        offers = {sub.offer for sub in all_active_subs}
        offer_histories = {}

        for offer in offers:
            histories = list(offer.price_history.order_by('-checked_at')[:2])
            offer_histories[offer.id] = histories

        for sub in all_active_subs:
            user_subs_map[sub.user].append(sub)

        for user, subs in user_subs_map.items():
            settings = user.settings
            if not settings.email_notifications:
                continue

            currency_sym = CURRENCY_SYMBOLS.get(settings.currency, '₽')

            for sub in subs:
                check_offer = sub.offer

                price_with_currency = f"{check_offer.price} {currency_sym}"
                if check_offer.delivery_days is not None:
                    delivery_text = f"{check_offer.delivery_days} дн."
                else:
                    delivery_text = "не указан"

                need_init = False
                if sub.last_notified_price is None:
                    sub.last_notified_price = check_offer.price
                    need_init = True
                if sub.last_notified_delivery_days is None:
                    sub.last_notified_delivery_days = check_offer.delivery_days
                    need_init = True
                if need_init:
                    sub.save(update_fields=['last_notified_price', 'last_notified_delivery_days'])

                price_change = False
                if sub.last_notified_price is not None:
                    percent_change = abs(check_offer.price - sub.last_notified_price) / sub.last_notified_price * 100
                    if percent_change >= settings.price_change_threshold:
                        price_change = True

                histories = offer_histories.get(check_offer.id, [])
                previous = histories[1] if len(histories) > 1 else None
                in_stock_change = previous and previous.in_stock != check_offer.in_stock

                delivery_days_change = (sub.last_notified_delivery_days is not None and
                                        sub.last_notified_delivery_days != check_offer.delivery_days)

                changes = []
                if price_change:
                    actual_pct = percent_change
                    changes.append(f"Цена: {price_with_currency} (изменение на {actual_pct:.1f}%)")
                if in_stock_change:
                    changes.append(f"Наличие: {'есть' if check_offer.in_stock else 'нет'}")
                if delivery_days_change:
                    changes.append(f"Срок доставки: {delivery_text}")

                subject = None
                plain_body = None
                html_body = None

                if changes:
                    subject = f"PriceHunter: изменения по товару «{check_offer.title}»"
                    plain_body = "\n".join(changes)
                    html_context = {
                        'product_title': check_offer.title,
                        'current_price': price_with_currency,
                        'delivery_days': delivery_text,
                        'in_stock': check_offer.in_stock,
                        'product_url': check_offer.url,
                        'changes': changes,
                    }
                    html_body = render_to_string('email/significant_change.html', html_context)

                elif (settings.last_checked_at is None or
                    (timezone.now() - settings.last_checked_at).total_seconds() / 3600 >= settings.check_interval):
                    summary_lines = [
                        f"Цена: {price_with_currency}",
                        f"Срок доставки: {delivery_text}",
                        f"Наличие: {'есть' if check_offer.in_stock else 'нет'}"
                    ]

                    subject = f"PriceHunter: сводка по товару «{check_offer.title}»"
                    plain_body = "\n".join(summary_lines)
                    html_context = {
                        'product_title': check_offer.title,
                        'current_price': price_with_currency,
                        'delivery_days': delivery_text,
                        'in_stock': check_offer.in_stock,
                        'product_url': check_offer.url,
                    }
                    html_body = render_to_string('email/periodic_summary.html', html_context)

                if subject:
                    email_msg = EmailMultiAlternatives(
                        subject=subject,
                        body=plain_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[user.email],
                    )
                    email_msg.attach_alternative(html_body, 'text/html')
                    email_msg.send()

                    # Обновляем данные после отправки
                    sub.last_notified_price = check_offer.price
                    sub.last_notified_delivery_days = check_offer.delivery_days
                    settings.last_checked_at = timezone.now()

                    sub.save(update_fields=['last_notified_price', 'last_notified_delivery_days'])
                    settings.save(update_fields=['last_checked_at'])
