from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    ChangePasswordView,
    UserViewSet
)

# Router for viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # ============================================
    # AUTHENTICATION ENDPOINTS
    # ============================================
    
    # User Registration (with optional profile)
    # POST /api/auth/register/
    # Body: { email, username, password, role, doctor_profile/patient_profile }
    path('register/', RegisterView.as_view(), name='register'),
    
    # User Login
    # POST /api/auth/login/
    # Body: { email, password }
    path('login/', LoginView.as_view(), name='login'),
    
    # User Logout
    # POST /api/auth/logout/
    # Headers: Authorization: Token <token>
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Get/Update Current User Profile
    # GET/PUT/PATCH /api/auth/me/
    # Headers: Authorization: Token <token>
    path('me/', MeView.as_view(), name='me'),
    
    # Change Password
    # POST /api/auth/change-password/
    # Body: { old_password, new_password, new_password_confirm }
    # Headers: Authorization: Token <token>
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # ============================================
    # USER MANAGEMENT ENDPOINTS
    # ============================================
    
    # All user management routes from router
    # GET    /api/auth/users/              - List users
    # POST   /api/auth/users/              - Create user (Admin only)
    # GET    /api/auth/users/{id}/         - User detail
    # PUT    /api/auth/users/{id}/         - Update user
    # PATCH  /api/auth/users/{id}/         - Partial update
    # DELETE /api/auth/users/{id}/         - Delete user (Admin only)
    # GET    /api/auth/users/roles/        - Get available roles
    # POST   /api/auth/users/{id}/assign_role/ - Assign role to user
    path('', include(router.urls)),
]