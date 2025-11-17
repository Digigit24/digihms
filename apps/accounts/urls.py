"""
Accounts URLs - SuperAdmin API Proxy

URL configuration for user and role management through SuperAdmin backend.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ChangePasswordView,
    TokenRefreshView,
    UserViewSet,
    RoleViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # User and Role management endpoints (from router)
    # - /api/accounts/users/ - List/Create users
    # - /api/accounts/users/{id}/ - Retrieve/Update/Delete user
    # - /api/accounts/users/{id}/assign_roles/ - Assign roles to user
    # - /api/accounts/users/{id}/remove_role/ - Remove role from user
    # - /api/accounts/roles/ - List/Create roles
    # - /api/accounts/roles/{id}/ - Retrieve/Update/Delete role
    # - /api/accounts/roles/{id}/members/ - Get role members
    # - /api/accounts/roles/permissions_schema/ - Get permissions schema
    path('', include(router.urls)),
]
