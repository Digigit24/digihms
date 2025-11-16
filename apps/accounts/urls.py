"""
DigiHMS Accounts URLs

API endpoints for doctor profiles and specialties.
Authentication is handled by SuperAdmin - no local auth endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorProfileViewSet, SpecialtyViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'doctors', DoctorProfileViewSet, basename='doctor')
router.register(r'specialties', SpecialtyViewSet, basename='specialty')

urlpatterns = [
    # All endpoints are from the router
    path('', include(router.urls)),
]

# Available endpoints:
# GET    /api/auth/doctors/              - List doctor profiles
# POST   /api/auth/doctors/              - Create doctor profile
# GET    /api/auth/doctors/{id}/         - Get doctor profile details
# PUT    /api/auth/doctors/{id}/         - Update doctor profile
# PATCH  /api/auth/doctors/{id}/         - Partial update doctor profile
# DELETE /api/auth/doctors/{id}/         - Delete doctor profile
# GET    /api/auth/doctors/me/           - Get current user's doctor profile
# POST   /api/auth/doctors/sync_from_jwt/ - Sync doctor profile from JWT
# POST   /api/auth/doctors/{id}/set_availability/ - Set doctor availability
# GET    /api/auth/doctors/{id}/statistics/ - Get doctor statistics
#
# GET    /api/auth/specialties/          - List specialties
# POST   /api/auth/specialties/          - Create specialty
# GET    /api/auth/specialties/{id}/     - Get specialty details
# PUT    /api/auth/specialties/{id}/     - Update specialty
# DELETE /api/auth/specialties/{id}/     - Delete specialty
