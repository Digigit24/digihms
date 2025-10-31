from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

class ProductCategory(models.Model):
    """Product category for pharmacy items"""
    CATEGORY_TYPES = [
        ('medicine', 'Medicine'),
        ('healthcare_product', 'Healthcare Product'),
        ('medical_equipment', 'Medical Equipment')
    ]

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, choices=CATEGORY_TYPES)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pharmacy_product_categories'
        verbose_name_plural = 'Product Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


from rest_framework import serializers
from .models import (
    ProductCategory, 
    PharmacyProduct, 
    Cart, 
    CartItem, 
    PharmacyOrder, 
    PharmacyOrderItem
)

class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for Product Categories"""
    class Meta:
        model = ProductCategory
        fields = '__all__'


class PharmacyProductSerializer(serializers.ModelSerializer):
    """Serializer for Pharmacy Products"""
    category = ProductCategorySerializer(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    low_stock_warning = serializers.BooleanField(read_only=True)

    class Meta:
        model = PharmacyProduct
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for Cart Items"""
    product = PharmacyProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price_at_time', 'total_price']

    def get_total_price(self, obj):
        return obj.quantity * obj.price_at_time


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart"""
    cart_items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = Cart
        fields = ['id', 'user', 'cart_items', 'total_items', 'total_amount', 'created_at', 'updated_at']


class PharmacyOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for Order Items"""
    product = PharmacyProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = PharmacyOrderItem
        fields = ['id', 'product', 'quantity', 'price_at_time', 'total_price']

    def get_total_price(self, obj):
        return obj.quantity * obj.price_at_time


class PharmacyOrderSerializer(serializers.ModelSerializer):
    """Serializer for Pharmacy Orders"""
    order_items = PharmacyOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = PharmacyOrder
        fields = [
            'id', 'user', 'total_amount', 
            'status', 'payment_status', 
            'shipping_address', 'billing_address', 
            'created_at', 'updated_at',
            'order_items'
        ]

class Cart(models.Model):
    """Shopping cart for pharmacy products"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='pharmacy_cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_items(self):
        return self.cart_items.count()

    @property
    def total_amount(self):
        return sum(
            item.product.selling_price * item.quantity 
            for item in self.cart_items.all()
        )


class CartItem(models.Model):
    """Individual items in the shopping cart"""
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        related_name='cart_items'
    )
    product = models.ForeignKey(
        PharmacyProduct, 
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        unique_together = ['cart', 'product']

    def save(self, *args, **kwargs):
        """Set price at time of adding to cart"""
        if not self.price_at_time:
            self.price_at_time = self.product.selling_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"


class PharmacyOrder(models.Model):
    """Pharmacy order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='pharmacy_orders'
    )
    
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending'
    )
    
    shipping_address = models.TextField()
    billing_address = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.get_status_display()}"


class PharmacyOrderItem(models.Model):
    """Items in a pharmacy order"""
    order = models.ForeignKey(
        PharmacyOrder, 
        on_delete=models.CASCADE, 
        related_name='order_items'
    )
    product = models.ForeignKey(
        PharmacyProduct, 
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField()
    price_at_time = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.price_at_time