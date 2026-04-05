"""Файл с настройками администраторской панели"""
from django.contrib import admin
from core.models import Shop, Product, Offer, PriceHistory, Subscription


class ShopAdmin(admin.ModelAdmin):
    """Настройка отображения магазинов в админке"""
    list_display = ['name', 'slug', 'is_active', 'created_at']
    search_fields = ['name', 'slug']
    list_filter = ['is_active']


class ProductAdmin(admin.ModelAdmin):
    """Настройка отображения товаров в админке"""
    list_display = ['name', 'slug', 'created_at', 'updated_at']
    search_fields = ['name', 'slug']
    list_filter = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}


class OfferAdmin(admin.ModelAdmin):
    """Настройка отображения предложений в админке"""
    list_display = ['product', 'shop', 'price', 'in_stock', 'is_active', 'last_updated']
    list_filter = ['shop', 'in_stock', 'is_active']
    search_fields = ['product__name', 'article', 'url']
    raw_id_fields = ['product', 'shop']


class PriceHistoryAdmin(admin.ModelAdmin):
    """Настройка отображения истории цен в админке"""
    list_display = ['offer', 'price', 'in_stock', 'checked_at']
    list_filter = ['checked_at', 'in_stock']
    search_fields = ['offer__product__name', 'offer__article']
    raw_id_fields = ['offer']


class SubscriptionAdmin(admin.ModelAdmin):
    """Настройка отображения подписок в админке"""
    list_display = ['user', 'offer', 'target_price', 'notify_on_drop', 'is_active', 'created_at']
    list_filter = ['is_active', 'notify_on_drop', 'notify_on_restore', 'created_at']
    search_fields = ['user__username', 'user__email', 'offer__product__name']
    raw_id_fields = ['user', 'offer']


admin.site.register(Shop, ShopAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Offer, OfferAdmin)
admin.site.register(PriceHistory, PriceHistoryAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
