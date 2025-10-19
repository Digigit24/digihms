from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, F
from django.utils import timezone

from .models import (
    ProductCategory, 
    PharmacyProduct, 
    Cart, 
    CartItem, 
    PharmacyOrder, 
    PharmacyOrderItem
)
from .serializers import (
    ProductCategorySerializer,
    PharmacyProductSerializer,
    CartSerializer,
    CartItemSerializer,
    PharmacyOrderSerializer
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    """Product Category Management"""
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'type']
    ordering_fields = ['name']

    def get_queryset(self):
        """Filter active categories"""
        return self.queryset.filter(is_active=True)


class PharmacyProductViewSet(viewsets.ModelViewSet):
    """Pharmacy Product Management"""
    queryset = PharmacyProduct.objects.select_related('category')
    serializer_class = PharmacyProductSerializer
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_fields = ['category', 'company', 'is_active']
    search_fields = ['product_name', 'company']
    ordering_fields = ['product_name', 'mrp', 'created_at']

    def get_queryset(self):
        """Filter and annotate products"""
        queryset = self.queryset.filter(is_active=True)
        
        # Additional filtering options
        category = self.request.query_params.get('category')
        in_stock = self.request.query_params.get('in_stock')
        
        if category:
            queryset = queryset.filter(category__name__icontains=category)
        
        if in_stock == 'true':
            queryset = queryset.filter(quantity__gt=0)
        
        return queryset

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock products"""
        queryset = self.get_queryset()
        low_stock_products = queryset.filter(
            quantity__lte=F('minimum_stock_level')
        )
        serializer = self.get_serializer(low_stock_products, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['get'])
    def near_expiry(self, request):
        """Get products near expiry (within 90 days)"""
        queryset = self.get_queryset()
        threshold_date = timezone.now() + timezone.timedelta(days=90)
        near_expiry = queryset.filter(expiry_date__lte=threshold_date)
        serializer = self.get_serializer(near_expiry, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get pharmacy product statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_products': queryset.count(),
            'in_stock_products': queryset.filter(quantity__gt=0).count(),
            'low_stock_products': queryset.filter(quantity__lte=F('minimum_stock_level')).count(),
            'near_expiry_products': queryset.filter(
                expiry_date__lte=timezone.now() + timezone.timedelta(days=90)
            ).count(),
        }
        return Response({
            'success': True,
            'data': stats
        })


class CartViewSet(viewsets.ModelViewSet):
    """Cart Management"""
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only access current user's cart"""
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['POST'])
    def add_item(self, request):
        """Add item to cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        try:
            product = PharmacyProduct.objects.get(id=product_id)
        except PharmacyProduct.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check stock availability
        if product.quantity < quantity:
            return Response({
                'success': False,
                'error': 'Insufficient stock'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'price_at_time': product.selling_price
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


class PharmacyOrderViewSet(viewsets.ModelViewSet):
    """Pharmacy Order Management"""
    queryset = PharmacyOrder.objects.prefetch_related('order_items')
    serializer_class = PharmacyOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend, 
        filters.OrderingFilter
    ]
    filterset_fields = ['status', 'payment_status']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        """Only access current user's orders"""
        return self.queryset.filter(user=self.request.user)

    def create(self, request):
        """Create order from cart"""
        cart = Cart.objects.get(user=request.user)

        # Validate cart
        if cart.total_items == 0:
            return Response({
                'success': False,
                'error': 'Cart is empty'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create order
        order = PharmacyOrder.objects.create(
            user=request.user,
            total_amount=cart.total_amount,
            shipping_address=request.data.get('shipping_address', ''),
            billing_address=request.data.get('billing_address', '')
        )

        # Convert cart items to order items
        order_items = []
        for cart_item in cart.cart_items.all():
            # Validate stock availability
            product = cart_item.product
            if product.quantity < cart_item.quantity:
                order.delete()
                return Response({
                    'success': False,
                    'error': f'Insufficient stock for {product.product_name}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create order item
            order_item = PharmacyOrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart_item.quantity,
                price_at_time=cart_item.price_at_time
            )
            order_items.append(order_item)

            # Update product inventory
            product.quantity -= cart_item.quantity
            product.save()

        # Clear cart
        cart.cart_items.all().delete()

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)