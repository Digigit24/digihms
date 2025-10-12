from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorProfileViewSet, SpecialtyViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'profiles', DoctorProfileViewSet, basename='doctor-profile')
router.register(r'specialties', SpecialtyViewSet, basename='specialty')

urlpatterns = [
    path('', include(router.urls)),
]