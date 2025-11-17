"""
Accounts Views - SuperAdmin API Proxy

These views proxy requests to the SuperAdmin backend APIs for user and role management.
They validate input, call the appropriate API endpoints, and return formatted responses.
"""

from rest_framework import status, viewsets, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse
)
import logging

from .api_client import SuperAdminAPIClient, SuperAdminAPIError
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    RoleSerializer,
    LoginSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
    TokenRefreshSerializer,
    AssignRolesSerializer,
    RemoveRoleSerializer,
    LoginResponseSerializer,
    RegisterResponseSerializer,
    SuccessMessageSerializer,
    ErrorResponseSerializer,
)

logger = logging.getLogger(__name__)


# ==================== Authentication Views ====================

@extend_schema(tags=['Authentication'])
class RegisterView(generics.GenericAPIView):
    """
    Tenant Registration

    Register a new tenant with an admin user via SuperAdmin backend.
    This will create a new tenant, admin user, and return JWT tokens.
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register new tenant",
        description="Create new tenant with admin user",
        request=RegisterSerializer,
        responses={
            201: RegisterResponseSerializer,
            400: ErrorResponseSerializer
        },
        examples=[
            OpenApiExample(
                'Tenant Registration Example',
                value={
                    'tenant_name': 'City Hospital',
                    'tenant_slug': 'city-hospital',
                    'admin_email': 'admin@cityhospital.com',
                    'admin_password': 'SecurePass123',
                    'admin_password_confirm': 'SecurePass123',
                    'admin_first_name': 'John',
                    'admin_last_name': 'Doe',
                    'enabled_modules': ['crm', 'whatsapp', 'meetings', 'hms']
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request):
        """Handle tenant registration"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient()
            result = client.register(serializer.validated_data)

            logger.info(f"New tenant registered: {serializer.validated_data['tenant_slug']}")

            return Response(result, status=status.HTTP_201_CREATED)

        except SuperAdminAPIError as e:
            logger.warning(f"Registration failed: {e.message}")
            return Response({
                'success': False,
                'error': e.message,
                'detail': e.response_data
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class LoginView(generics.GenericAPIView):
    """
    User Login

    Authenticate user via SuperAdmin backend and receive JWT tokens.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="User login",
        description="Authenticate and receive JWT tokens",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            401: ErrorResponseSerializer
        },
        examples=[
            OpenApiExample(
                'Login Example',
                value={
                    'email': 'admin@cityhospital.com',
                    'password': 'SecurePass123'
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request):
        """Handle user login"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient()
            result = client.login(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )

            logger.info(f"User logged in successfully: {serializer.validated_data['email']}")

            # Store JWT token in session for admin access
            if 'tokens' in result and 'access' in result['tokens']:
                request.session['jwt_token'] = result['tokens']['access']
                if 'user' in result and 'tenant' in result['user']:
                    request.session['tenant_id'] = result['user']['tenant']
                    request.session['tenant_slug'] = result['user'].get('tenant_name')

            return Response(result, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.warning(f"Login failed for {serializer.validated_data['email']}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_401_UNAUTHORIZED)


@extend_schema(tags=['Authentication'])
class LogoutView(generics.GenericAPIView):
    """
    User Logout

    Logout user and blacklist refresh token.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="User logout",
        description="Logout and blacklist tokens",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh_token': {'type': 'string'}
                }
            }
        },
        responses={
            200: SuccessMessageSerializer,
            400: ErrorResponseSerializer
        }
    )
    def post(self, request):
        """Handle user logout"""
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response({
                'success': False,
                'error': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get access token from request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            access_token = None
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

            client = SuperAdminAPIClient(request)
            result = client.logout(token=access_token, refresh_token=refresh_token)

            # Clear session
            if hasattr(request, 'session'):
                request.session.flush()

            logger.info(f"User logged out successfully")

            return Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.warning(f"Logout failed: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class MeView(generics.GenericAPIView):
    """
    Current User Profile

    Get or update the authenticated user's profile via SuperAdmin backend.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        description="Retrieve authenticated user's profile",
        responses={200: UserSerializer}
    )
    def get(self, request):
        """Get current user profile"""
        try:
            client = SuperAdminAPIClient(request)
            user_data = client.get_me()

            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get current user: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Update current user profile",
        description="Update authenticated user's profile",
        request=UserSerializer,
        responses={200: UserSerializer}
    )
    def patch(self, request):
        """Update current user profile"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            user_data = client.update_me(serializer.validated_data)

            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to update current user: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Full update of current user profile"""
        return self.patch(request)


@extend_schema(tags=['Authentication'])
class ChangePasswordView(generics.GenericAPIView):
    """
    Change Password

    Change the authenticated user's password via SuperAdmin backend.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change user password",
        description="Change password and receive new tokens",
        request=ChangePasswordSerializer,
        responses={
            200: SuccessMessageSerializer,
            400: ErrorResponseSerializer
        }
    )
    def post(self, request):
        """Handle password change"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Get access token from request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            access_token = None
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

            client = SuperAdminAPIClient(request)
            result = client.change_password(
                token=access_token,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password'],
                new_password_confirm=serializer.validated_data['new_password_confirm']
            )

            return Response(result, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Password change failed: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Authentication'])
class TokenRefreshView(generics.GenericAPIView):
    """
    Refresh JWT Token

    Get a new access token using refresh token.
    """
    serializer_class = TokenRefreshSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh JWT token",
        description="Get new access token",
        request=TokenRefreshSerializer,
        responses={200: OpenApiResponse(description="New access token")}
    )
    def post(self, request):
        """Handle token refresh"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient()
            result = client.refresh_token(serializer.validated_data['refresh'])

            return Response(result, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Token refresh failed: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_401_UNAUTHORIZED)


# ==================== User Management ViewSet ====================

@extend_schema_view(
    list=extend_schema(
        summary="List users",
        description="Get list of users for current tenant",
        parameters=[
            OpenApiParameter(name='search', type=str, description='Search by name or email'),
            OpenApiParameter(name='role', type=str, description='Filter by role'),
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
        description="Create a new user in the current tenant",
        tags=['Users']
    ),
    update=extend_schema(
        summary="Update user",
        description="Update user information",
        tags=['Users']
    ),
    partial_update=extend_schema(
        summary="Partial update user",
        description="Partially update user information",
        tags=['Users']
    ),
    destroy=extend_schema(
        summary="Delete user",
        description="Delete a user",
        tags=['Users']
    ),
)
class UserViewSet(viewsets.ViewSet):
    """
    User Management via SuperAdmin API

    CRUD operations for user management through SuperAdmin backend.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Get appropriate serializer class"""
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def list(self, request):
        """List users"""
        try:
            client = SuperAdminAPIClient(request)
            users = client.get_users(**request.query_params.dict())

            serializer = UserSerializer(users, many=True)

            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get users: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get user by ID"""
        try:
            client = SuperAdminAPIClient(request)
            user_data = client.get_user(pk)

            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get user {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_404_NOT_FOUND)

    def create(self, request):
        """Create new user"""
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            user_data = client.create_user(serializer.validated_data)

            logger.info(f"User created: {user_data.get('email')}")

            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_201_CREATED)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to create user: {e.message}")
            return Response({
                'success': False,
                'error': e.message,
                'detail': e.response_data
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """Update user (PUT)"""
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            user_data = client.update_user(pk, serializer.validated_data, partial=False)

            logger.info(f"User {pk} updated")

            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to update user {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """Update user (PATCH)"""
        serializer = UserSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            user_data = client.update_user(pk, serializer.validated_data, partial=True)

            logger.info(f"User {pk} updated")

            return Response({
                'success': True,
                'data': user_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to update user {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """Delete user"""
        try:
            client = SuperAdminAPIClient(request)
            client.delete_user(pk)

            logger.info(f"User {pk} deleted")

            return Response({
                'success': True,
                'message': 'User deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to delete user {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Assign roles to user",
        description="Assign roles to a user",
        request=AssignRolesSerializer,
        responses={200: SuccessMessageSerializer},
        tags=['Users']
    )
    @action(detail=True, methods=['post'])
    def assign_roles(self, request, pk=None):
        """Assign roles to user"""
        serializer = AssignRolesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            result = client.assign_roles(pk, serializer.validated_data['role_ids'])

            return Response(result, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to assign roles to user {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Remove role from user",
        description="Remove a role from user",
        request=RemoveRoleSerializer,
        responses={200: SuccessMessageSerializer},
        tags=['Users']
    )
    @action(detail=True, methods=['delete'])
    def remove_role(self, request, pk=None):
        """Remove role from user"""
        serializer = RemoveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            result = client.remove_role(pk, serializer.validated_data['role_id'])

            return Response(result, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to remove role from user {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)


# ==================== Role Management ViewSet ====================

@extend_schema_view(
    list=extend_schema(
        summary="List roles",
        description="Get list of roles for current tenant",
        tags=['Roles']
    ),
    retrieve=extend_schema(
        summary="Get role details",
        description="Retrieve detailed information about a specific role",
        tags=['Roles']
    ),
    create=extend_schema(
        summary="Create role",
        description="Create a new role",
        tags=['Roles']
    ),
    update=extend_schema(
        summary="Update role",
        description="Update role information",
        tags=['Roles']
    ),
    partial_update=extend_schema(
        summary="Partial update role",
        description="Partially update role information",
        tags=['Roles']
    ),
    destroy=extend_schema(
        summary="Delete role",
        description="Delete a role",
        tags=['Roles']
    ),
)
class RoleViewSet(viewsets.ViewSet):
    """
    Role Management via SuperAdmin API

    CRUD operations for role management through SuperAdmin backend.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RoleSerializer

    def list(self, request):
        """List roles"""
        try:
            client = SuperAdminAPIClient(request)
            roles = client.get_roles(**request.query_params.dict())

            serializer = RoleSerializer(roles, many=True)

            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get roles: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get role by ID"""
        try:
            client = SuperAdminAPIClient(request)
            role_data = client.get_role(pk)

            return Response({
                'success': True,
                'data': role_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get role {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_404_NOT_FOUND)

    def create(self, request):
        """Create new role"""
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            role_data = client.create_role(serializer.validated_data)

            logger.info(f"Role created: {role_data.get('name')}")

            return Response({
                'success': True,
                'data': role_data
            }, status=status.HTTP_201_CREATED)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to create role: {e.message}")
            return Response({
                'success': False,
                'error': e.message,
                'detail': e.response_data
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """Update role (PUT)"""
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            role_data = client.update_role(pk, serializer.validated_data, partial=False)

            logger.info(f"Role {pk} updated")

            return Response({
                'success': True,
                'data': role_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to update role {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """Update role (PATCH)"""
        serializer = RoleSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            client = SuperAdminAPIClient(request)
            role_data = client.update_role(pk, serializer.validated_data, partial=True)

            logger.info(f"Role {pk} updated")

            return Response({
                'success': True,
                'data': role_data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to update role {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """Delete role"""
        try:
            client = SuperAdminAPIClient(request)
            client.delete_role(pk)

            logger.info(f"Role {pk} deleted")

            return Response({
                'success': True,
                'message': 'Role deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to delete role {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get role members",
        description="Get list of users with this role",
        responses={200: UserSerializer(many=True)},
        tags=['Roles']
    )
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get role members"""
        try:
            client = SuperAdminAPIClient(request)
            members = client.get_role_members(pk)

            serializer = UserSerializer(members, many=True)

            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get members for role {pk}: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get permissions schema",
        description="Get the available permissions schema",
        responses={200: OpenApiResponse(description="Permissions schema")},
        tags=['Roles']
    )
    @action(detail=False, methods=['get'])
    def permissions_schema(self, request):
        """Get permissions schema"""
        try:
            client = SuperAdminAPIClient(request)
            schema = client.get_permissions_schema()

            return Response(schema, status=status.HTTP_200_OK)

        except SuperAdminAPIError as e:
            logger.error(f"Failed to get permissions schema: {e.message}")
            return Response({
                'success': False,
                'error': e.message
            }, status=e.status_code or status.HTTP_400_BAD_REQUEST)
