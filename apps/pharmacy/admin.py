from django.contrib import admin
from .models import (
    ProductCategory, 
    PharmacyProduct, 
    Cart, 
    CartItem, 
    PharmacyOrder, 
    PharmacyOrderItem
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name']


@admin.register(PharmacyProduct)
class PharmacyProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 
        'category', 
        'company', 
        'quantity', 
        'mrp', 
        'is_active'
    ]
    list_filter = ['category', 'is_active', 'prescription_required']
    search_fields = ['product_name', 'company']
    list_editable = ['is_active']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    list_filter = ['created_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'price_at_time']
    list_filter = ['product__category']


@admin.register(PharmacyOrder)
class PharmacyOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'user', 
        'total_amount', 
        'status', 
        'payment_status', 
        'created_at'
    ]
    list_filter = ['status', 'payment_status']
    search_fields = ['user__username', 'user__email']


@admin.register(PharmacyOrderItem)
class PharmacyOrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price_at_time']
    list_filter = ['product__category']