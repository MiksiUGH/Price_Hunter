"""Файл со всеми моделями БД"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .utils.normalize import normalize_name


class Shop(models.Model):
    """
    Модель маркетплейса
    """
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Идентификатор', max_length=50, unique=True)
    search_url_template = models.CharField('Поисковой URL', max_length=300)
    is_active = models.BooleanField('Активен ли', default=True)
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return f'{self.name}'


class Product(models.Model):
    """
    Модель абстрактного продукта
    """
    name = models.CharField('Название', max_length=500)
    slug = models.SlugField('Идентификатор', unique=True, db_index=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    normalized_name = models.CharField(
        max_length=500,
        blank=True,
        db_index=True,
        verbose_name='Нормализованное название'
    )

    def save(self, *args, **kwargs):
        if not self.normalized_name and self.name:
            self.normalized_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'


class Offer(models.Model):
    """
    Модель конкретного предложения с маркетплейсов
    """
    url = models.URLField('URL страницы', unique=True)
    article = models.CharField('Артикул', max_length=100, blank=True, null=True, db_index=True)
    price = models.DecimalField('Текущая цена', decimal_places=2, max_digits=10)
    in_stock = models.BooleanField('Есть в наличии', default=True)
    is_active = models.BooleanField('Активно ли', default=True)
    last_updated = models.DateTimeField('Дата последнего обновления', auto_now=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='offers',
        verbose_name='Продукт',
        db_index=True
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='offers',
        verbose_name='Маркетплейс',
        db_index=True
    )

    def __str__(self):
        return f"{self.product.name} - {self.shop.name} ({self.price})"

    class Meta:
        unique_together = (('product', 'shop', 'article'),)


class PriceHistory(models.Model):
    """
    Модель истории цен предложений
    """
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    in_stock = models.BooleanField('Есть в наличии', default=True)
    checked_at = models.DateTimeField('Время проверки', auto_now_add=True)

    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='Предложение'
    )

    class Meta:
        ordering = ['-checked_at']
        unique_together = (('offer', 'checked_at'),)
        verbose_name_plural = 'PriceHistories'


class Subscription(models.Model):
    """
    Модель подписки на предложение
    """
    target_price = models.DecimalField(
        'Цена', max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    notify_on_drop = models.BooleanField('Уведомлять при снижении цены', default=True)
    notify_on_restore = models.BooleanField('Уведомлять при появлении в наличии', default=True)
    last_notified_price = models.DecimalField(
        'Цена при прошлом уведомлении', max_digits=10,
        decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField('Активность', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subs',
        verbose_name='Пользователь',
        db_index=True
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name='subs',
        verbose_name='Предложение',
        db_index=True
    )

    def __str__(self):
        return f"{self.user.email} - {self.offer}"

    class Meta:
        unique_together = (('user', 'offer'),)


class UserSetting(models.Model):
    """Модель настроек для пользователя"""
    theme = models.CharField(
        max_length=10,
        choices=[('dark','Тёмная'),('light','Светлая')],
        default='dark'
    )
    language = models.CharField(
        max_length=2,
        choices=[('ru','Русский'),('en','English')],
        default='ru'
    )
    currency = models.CharField(
        max_length=3,
        choices=[('RUB','Рубль'),('USD','Доллар'),('EUR','Евро')],
        default='RUB'
    )
    check_interval = models.PositiveSmallIntegerField(
        default=24,
        help_text='Частота проверки (часы)'
    )
    email_notifications = models.BooleanField(default=False)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='settings'
    )

    def __str__(self):
        return f'Настройки {self.user.username}'


@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    """
    Сигнал для создания настроек пользователя

    :param sender: От какой модели сигналы мы обрабатываем
    :type sender: object
    :param instance: Сам созданный объект модели, передающей сигналы
    :type instance: User
    :param created: Был ли создан объект, модель которого передает сигналы
    :type created: bool
    """
    if created:
        UserSetting.objects.create(user=instance)
