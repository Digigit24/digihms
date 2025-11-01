from django.contrib import admin
from django.utils.html import format_html
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
    """Admin for Product Categories"""
    list_display = ['name', 'type', 'is_active', 'created_at']
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PharmacyProduct)
class PharmacyProductAdmin(admin.ModelAdmin):
    """Admin for Pharmacy Products"""
    list_display = [
        'product_name',
        'category',
        'company',
        'mrp',
        'selling_price',
        'quantity',
        'stock_status',
        'expiry_date',
        'is_active'
    ]
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['product_name', 'company', 'batch_no']
    readonly_fields = ['created_at', 'updated_at', 'is_in_stock', 'low_stock_warning']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product_name', 'category', 'company', 'batch_no')
        }),
        ('Pricing', {
            'fields': ('mrp', 'selling_price')
        }),
        ('Inventory', {
            'fields': ('quantity', 'minimum_stock_level', 'expiry_date')
        }),
        ('Status', {
            'fields': ('is_active', 'is_in_stock', 'low_stock_warning')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stock_status(self, obj):
        """Display stock status with color coding"""
        if obj.quantity == 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.low_stock_warning:
            return format_html('<span style="color: orange;">Low Stock</span>')
        else:
            return format_html('<span style="color: green;">In Stock</span>')
    stock_status.short_description = 'Stock Status'


class CartItemInline(admin.TabularInline):
    """Inline admin for Cart Items"""
    model = CartItem
    extra = 0
    readonly_fields = ['price_at_time', 'total_price']
    fields = ['product', 'quantity', 'price_at_time', 'total_price']
    
    def total_price(self, obj):
        """Calculate total price for cart item"""
        if obj.id:
            return obj.total_price
        return 0
    total_price.short_description = 'Total Price'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin for Shopping Carts"""
    list_display = ['user', 'total_items', 'total_amount', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'total_items', 'total_amount']
    inlines = [CartItemInline]
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'total_items', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class PharmacyOrderItemInline(admin.TabularInline):
    """Inline admin for Order Items"""
    model = PharmacyOrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price_at_time', 'total_price']
    can_delete = False
    
    def total_price(self, obj):
        """Calculate total price for order item"""
        if obj.id:
            return obj.total_price
        return 0
    total_price.short_description = 'Total Price'


@admin.register(PharmacyOrder)
class PharmacyOrderAdmin(admin.ModelAdmin):
    """Admin for Pharmacy Orders"""
    list_display = [
        'id',
        'user',
        'total_amount',
        'status',
        'payment_status',
        'created_at'
    ]
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['user__username', 'user__email', 'id']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    inlines = [PharmacyOrderItemInline]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'total_amount')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual order creation in admin"""
        return False