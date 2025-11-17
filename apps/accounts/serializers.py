"""
Accounts Serializers - API Data Validators

These serializers validate and format data for SuperAdmin API calls.
They work with dictionaries instead of Django models.
"""

from rest_framework import serializers
from typing import Dict, Any, List


class RoleSerializer(serializers.Serializer):
    """Serializer for Role data from SuperAdmin API"""

    id = serializers.UUIDField(read_only=True)
    tenant = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    permissions = serializers.JSONField(default=dict)
    is_active = serializers.BooleanField(default=True)
    created_by = serializers.UUIDField(read_only=True)
    created_by_email = serializers.EmailField(read_only=True)
    member_count = serializers.IntegerField(read_only=True, required=False)
    created_at = serializers.DateTimeField(read_only=True, required=False)
    updated_at = serializers.DateTimeField(read_only=True, required=False)

    def validate_permissions(self, value):
        """Validate permissions structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Permissions must be a JSON object")
        return value


class UserSerializer(serializers.Serializer):
    """Serializer for User data from SuperAdmin API"""

    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    tenant = serializers.UUIDField(read_only=True, required=False)
    tenant_name = serializers.CharField(read_only=True, required=False)
    roles = RoleSerializer(many=True, read_only=True, required=False)
    role_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    is_super_admin = serializers.BooleanField(read_only=True, required=False)
    profile_picture = serializers.URLField(max_length=500, required=False, allow_blank=True, allow_null=True)
    timezone = serializers.CharField(max_length=50, default='Asia/Kolkata')
    is_active = serializers.BooleanField(default=True)
    date_joined = serializers.DateTimeField(read_only=True, required=False)

    # Additional HMS-specific fields (optional)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    employee_id = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)

    def validate_email(self, value):
        """Validate email format"""
        value = value.lower().strip()
        return value


class UserCreateSerializer(serializers.Serializer):
    """Serializer for creating new users via SuperAdmin API"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    timezone = serializers.CharField(max_length=50, default='Asia/Kolkata')

    # HMS-specific fields
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    employee_id = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate password match"""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if password != password_confirm:
            raise serializers.ValidationError({
                "password": "Passwords don't match"
            })

        # Remove password_confirm as it's not needed for API call
        attrs.pop('password_confirm')
        return attrs

    def validate_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()


class RegisterSerializer(serializers.Serializer):
    """Serializer for tenant registration via SuperAdmin API"""

    tenant_name = serializers.CharField(max_length=255)
    tenant_slug = serializers.SlugField(max_length=255)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    admin_password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    admin_first_name = serializers.CharField(max_length=150)
    admin_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    enabled_modules = serializers.ListField(
        child=serializers.CharField(),
        default=['crm', 'whatsapp', 'meetings', 'hms']  # Add HMS by default
    )

    def validate(self, attrs):
        """Validate passwords match"""
        password = attrs.get('admin_password')
        password_confirm = attrs.get('admin_password_confirm')

        if password != password_confirm:
            raise serializers.ValidationError({
                "admin_password": "Passwords don't match"
            })

        # Ensure HMS is in enabled modules
        enabled_modules = attrs.get('enabled_modules', [])
        if 'hms' not in enabled_modules:
            enabled_modules.append('hms')
            attrs['enabled_modules'] = enabled_modules

        return attrs

    def validate_admin_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""

    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    def validate(self, attrs):
        """Validate new passwords match"""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                "new_password": "Passwords don't match"
            })

        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for refreshing JWT token"""

    refresh = serializers.CharField()


class AssignRolesSerializer(serializers.Serializer):
    """Serializer for assigning roles to a user"""

    role_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )


class RemoveRoleSerializer(serializers.Serializer):
    """Serializer for removing a role from a user"""

    role_id = serializers.UUIDField()


# ==================== Response Serializers ====================
# These are for documenting API responses

class TokenPairSerializer(serializers.Serializer):
    """Serializer for JWT token pair"""

    access = serializers.CharField()
    refresh = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""

    message = serializers.CharField()
    user = UserSerializer()
    tokens = TokenPairSerializer()


class RegisterResponseSerializer(serializers.Serializer):
    """Serializer for registration response"""

    message = serializers.CharField()
    user = UserSerializer()
    tokens = TokenPairSerializer()


class SuccessMessageSerializer(serializers.Serializer):
    """Generic success message serializer"""

    success = serializers.BooleanField(default=True)
    message = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    """Generic error response serializer"""

    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    detail = serializers.CharField(required=False)
