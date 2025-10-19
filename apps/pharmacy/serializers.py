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