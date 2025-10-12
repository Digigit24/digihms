from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientProfileViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'', PatientProfileViewSet, basename='patient')

urlpatterns = [
    path('', include(router.urls)),
]