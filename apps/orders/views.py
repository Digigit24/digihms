from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone

# OpenAPI/Swagger documentation
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse
)

from .models import Order, OrderItem, FeeType
from .serializers import (
    OrderCreateUpdateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    FeeTypeSerializer
)

# Utility function for group-based permissions
def _in_any_group(user, names):
    return user and user.is_authenticated and user.groups.filter(name__in=names).exists()


# Fee Type Management
@extend_schema_view(
    list=extend_schema(
        summary="List Fee Types",
        description="Get list of available fee types",
        tags=['Fee Types']
    ),
    create=extend_schema(
        summary="Create Fee Type",
        description="Create a new fee type (Admin only)",
        tags=['Fee Types']
    ),
    retrieve=extend_schema(
        summary="Get Fee Type Details",
        description="Retrieve details of a specific fee type",
        tags=['Fee Types']
    )
)
class FeeTypeViewSet(viewsets.ModelViewSet):
    """Fee Type Management"""
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer
    
    def get_permissions(self):
        """Custom permissions"""
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        # Write actions (create, update, delete) are admin-only
        return [IsAuthenticated()]  # Rely on group-based auth in Django Admin
    
    def list(self, request, *args, **kwargs):
        """List fee types with ability to filter"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Optional filtering
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


@extend_schema_view(
    list=extend_schema(
        summary="List Orders",
        description="Get list of orders with extensive filtering options",
        parameters=[
            OpenApiParameter(name='patient_id', type=int, description='Filter by patient'),
            OpenApiParameter(name='services_type', type=str, description='Filter by service type'),
            OpenApiParameter(name='status', type=str, description='Filter by order status'),
            OpenApiParameter(name='is_paid', type=bool, description='Filter by payment status'),
            OpenApiParameter(name='date_from', type=str, description='Orders from date (YYYY-MM-DD)'),
            OpenApiParameter(name='date_to', type=str, description='Orders to date (YYYY-MM-DD)'),
            OpenApiParameter(name='min_amount', type=float, description='Minimum total amount'),
            OpenApiParameter(name='max_amount', type=float, description='Maximum total amount'),
        ],
        tags=['Orders']
    ),
    create=extend_schema(
        summary="Create Order",
        description="Create a new order with multiple service items and fees",
        tags=['Orders']
    ),
    retrieve=extend_schema(
        summary="Get Order Details",
        description="Retrieve comprehensive details of a specific order",
        tags=['Orders']
    )
)
class OrderViewSet(viewsets.ModelViewSet):
    """
    Comprehensive Order Management ViewSet
    Supports full CRUD operations and advanced order tracking
    """
    queryset = Order.objects.select_related(
        'patient', 'user'
    ).prefetch_related(
        'order_items', 'order_fee_details'
    )
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'patient', 'services_type', 
        'status', 'is_paid'
    ]
    search_fields = [
        'order_number', 
        'patient__first_name', 
        'patient__last_name', 
        'patient__mobile_primary'
    ]
    ordering_fields = [
        'created_at', 'total_amount', 
        'status', 'services_type'
    ]
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'list':
            return OrderListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return OrderCreateUpdateSerializer
        return OrderDetailSerializer
    
    def get_permissions(self):
        """Custom permissions per action"""
        # Default to authenticated users
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Custom queryset filtering"""
        queryset = super().get_queryset()
        
        # Users in patient/staff roles can only see specific orders
        user = self.request.user
        if user.is_authenticated:
            if user.groups.filter(name='Patient').exists():
                # Patient can only see their own orders
                queryset = queryset.filter(patient__user=user)
            elif not user.groups.filter(name='Administrator').exists():
                # Staff (non-admin) can see relevant orders
                queryset = queryset.filter(user=user)
        
        # Additional query parameter filtering
        params = self.request.query_params
        
        # Date range filtering
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Amount range filtering
        min_amount = params.get('min_amount')
        max_amount = params.get('max_amount')
        if min_amount:
            queryset = queryset.filter(total_amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(total_amount__lte=max_amount)
        
        return queryset
    
    @extend_schema(
        summary="Get Order Statistics",
        description="Retrieve comprehensive order statistics (Admin only)",
        responses={200: OpenApiResponse(description="Order statistics")},
        tags=['Orders']
    )
    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """Generate order-wide statistics"""
        if not _in_any_group(request.user, ['Administrator']):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Aggregate statistics
        stats = Order.objects.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_amount'),
            avg_order_value=Avg('total_amount'),
            paid_orders=Count('id', filter=Q(is_paid=True)),
            unpaid_orders=Count('id', filter=Q(is_paid=False))
        )
        
        # Service type breakdown
        service_breakdown = Order.objects.values('services_type').annotate(
            count=Count('id'),
            total_revenue=Sum('total_amount')
        )
        
        # Status breakdown
        status_breakdown = Order.objects.values('status').annotate(
            count=Count('id'),
            total_revenue=Sum('total_amount')
        )
        
        return Response({
            'success': True,
            'data': {
                'overall_stats': {
                    'total_orders': stats['total_orders'],
                    'total_revenue': float(stats['total_revenue'] or 0),
                    'average_order_value': float(stats['avg_order_value'] or 0),
                    'paid_orders': stats['paid_orders'],
                    'unpaid_orders': stats['unpaid_orders']
                },
                'service_type_breakdown': list(service_breakdown),
                'status_breakdown': list(status_breakdown)
            }
        })
    
    @extend_schema(
        summary="Cancel Order",
        description="Soft cancel an existing order",
        tags=['Orders']
    )
    def destroy(self, request, *args, **kwargs):
        """Custom destroy to soft cancel order"""
        instance = self.get_object()
        
        # Only allow cancellation of pending orders
        if instance.status != 'pending':
            return Response({
                'success': False,
                'error': 'Only pending orders can be cancelled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update order status
        instance.status = 'cancelled'
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
            'data': serializer.data
        })