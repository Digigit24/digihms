from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, FeeTypeViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'', OrderViewSet, basename='orders')
router.register(r'fee-types', FeeTypeViewSet, basename='fee-types')

urlpatterns = [
    path('', include(router.urls)),
]