from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db.models import Q

# ✅ Import drf-spectacular decorators
from drf_spectacular.utils import (
    extend_schema, 
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse
)

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    LoginSerializer,
    ChangePasswordSerializer
)
from .permissions import IsAdministrator

User = get_user_model()


@extend_schema(tags=['Authentication'])
class RegisterView(generics.CreateAPIView):
    """
    User Registration
    
    Register a new user account. After successful registration, 
    a token will be automatically generated.
    """
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Register new user",
        description="Create a new user account with role assignment",
        request=UserCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=UserSerializer,
                description="User created successfully"
            ),
            400: OpenApiResponse(description="Bad request - validation errors")
        },
        examples=[
            OpenApiExample(
                'Registration Example',
                value={
                    'email': 'doctor@hospital.com',
                    'username': 'doctor1',
                    'password': 'SecurePass123',
                    'password_confirm': 'SecurePass123',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'phone': '+919876543210',
                    'role': 'Doctor'
                },
                request_only=True,
            ),
        ]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'data': {
                'token': token.key,
                'user': UserSerializer(user).data
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Authentication'])
class LoginView(generics.GenericAPIView):
    """
    User Login
    
    Authenticate user and receive an authentication token.
    Use this token in the Authorization header for subsequent requests.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="User login",
        description="Authenticate and receive token",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="Login successful"
            ),
            400: OpenApiResponse(description="Invalid credentials")
        },
        examples=[
            OpenApiExample(
                'Login Example',
                value={
                    'email': 'doctor@hospital.com',
                    'password': 'SecurePass123'
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        
        # Login user (session)
        login(request, user)
        
        return Response({
            'success': True,
            'data': {
                'token': token.key,
                'user': UserSerializer(user).data
            }
        })


@extend_schema(tags=['Authentication'])
class LogoutView(generics.GenericAPIView):
    """
    User Logout
    
    Delete the authentication token and logout the user.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="User logout",
        description="Delete authentication token and logout",
        request=None,
        responses={
            200: OpenApiResponse(description="Logged out successfully")
        }
    )
    def post(self, request):
        try:
            # Delete token
            request.user.auth_token.delete()
        except:
            pass
        
        logout(request)
        
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        })


@extend_schema(tags=['Authentication'])
class MeView(generics.RetrieveUpdateAPIView):
    """
    Current User Profile
    
    Get or update the authenticated user's profile.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="Get current user profile",
        description="Retrieve authenticated user's profile information",
        responses={200: UserSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update current user profile",
        description="Update authenticated user's profile information",
        request=UserSerializer,
        responses={200: UserSerializer}
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


@extend_schema(tags=['Authentication'])
class ChangePasswordView(generics.GenericAPIView):
    """
    Change Password
    
    Change the authenticated user's password.
    A new token will be generated after password change.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Change user password",
        description="Change password and receive new token",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Invalid old password")
        },
        examples=[
            OpenApiExample(
                'Change Password Example',
                value={
                    'old_password': 'OldPass123',
                    'new_password': 'NewSecurePass123',
                    'new_password_confirm': 'NewSecurePass123'
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'success': False,
                'error': 'Invalid old password'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Regenerate token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        
        return Response({
            'success': True,
            'message': 'Password changed successfully',
            'data': {'token': token.key}
        })


@extend_schema_view(
    list=extend_schema(
        summary="List users",
        description="Get list of users (admins see all, others see only themselves)",
        parameters=[
            OpenApiParameter(
                name='search',
                type=str,
                description='Search by name, email, or username',
                required=False
            ),
        ],
        tags=['Users']
    ),
    retrieve=extend_schema(
        summary="Get user details",
        description="Retrieve detailed information about a specific user",
        tags=['Users']
    ),
    create=extend_schema(
        summary="Create user",
        description="Create a new user (Admin only)",
        tags=['Users']
    ),
    update=extend_schema(
        summary="Update user",
        description="Update user information (Admin or self)",
        tags=['Users']
    ),
    partial_update=extend_schema(
        summary="Partial update user",
        description="Partially update user information (Admin or self)",
        tags=['Users']
    ),
    destroy=extend_schema(
        summary="Delete user",
        description="Delete a user (Admin only)",
        tags=['Users']
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    User Management
    
    CRUD operations for user management.
    - Admins can view and manage all users
    - Regular users can only view and update their own profile
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        elif self.action in ['create', 'destroy']:
            return [IsAdministrator()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        queryset = User.objects.all()
        
        # Non-admins can only see themselves
        if not self.request.user.groups.filter(name='Administrator').exists():
            queryset = queryset.filter(id=self.request.user.id)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'success': True,
            'data': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check permission - only admin or self
        if instance != request.user and not request.user.groups.filter(
            name='Administrator'
        ).exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'User deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="Get available roles",
        description="List all available user roles (groups)",
        responses={200: OpenApiResponse(description="List of roles")},
        tags=['Users']
    )
    @action(detail=False, methods=['get'])
    def roles(self, request):
        """Get available roles (groups)"""
        from django.contrib.auth.models import Group
        groups = Group.objects.all()
        return Response({
            'success': True,
            'data': {
                'roles': [g.name for g in groups]
            }
        })
    
    @extend_schema(
        summary="Assign role to user",
        description="Assign a role (group) to user (Admin only)",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'role': {'type': 'string', 'example': 'Doctor'}
                }
            }
        },
        responses={
            200: OpenApiResponse(description="Role assigned successfully"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Invalid role")
        },
        tags=['Users']
    )
    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        """Assign role (add to group)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user = self.get_object()
        role_name = request.data.get('role')
        
        if not role_name:
            return Response({
                'success': False,
                'error': 'Role is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.contrib.auth.models import Group
            group = Group.objects.get(name=role_name)
            user.groups.clear()  # Remove from all groups
            user.groups.add(group)  # Add to new group
            
            return Response({
                'success': True,
                'message': f'User assigned to {role_name} role',
                'data': UserSerializer(user).data
            })
        except Group.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid role'
            }, status=status.HTTP_404_NOT_FOUND)