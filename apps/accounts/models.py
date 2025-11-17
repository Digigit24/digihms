"""
Accounts Models - API Proxy Models

This module provides proxy models that represent users and roles from the SuperAdmin backend.
No database tables are created for these models - they exist only as API data containers.
"""

from django.db import models


# NOTE: We keep the User model for Django Admin compatibility but it's not used for HMS users
# HMS users are managed through the SuperAdmin API

class User(models.Model):
    """
    Minimal User model for Django Admin compatibility.

    This model is NOT used for HMS user management. All HMS users are managed
    through the SuperAdmin backend API.

    This model only exists to satisfy Django's AUTH_USER_MODEL requirement
    and should not be used directly in the application.
    """

    class Meta:
        db_table = 'users'
        managed = False  # Don't create or manage this table
        verbose_name = 'User (SuperAdmin Managed)'
        verbose_name_plural = 'Users (SuperAdmin Managed)'

    def __str__(self):
        return "SuperAdmin Managed User - Use API Client"


# ==================== API Proxy Classes ====================
# These classes represent data from the SuperAdmin API
# They are not Django models and do not interact with the database

class APIUser:
    """
    Proxy class representing a User from SuperAdmin API

    This is not a Django model - it's a simple data container for API responses.
    """

    def __init__(self, data: dict):
        """
        Initialize from API response data

        Args:
            data: Dictionary containing user data from SuperAdmin API
        """
        self.id = data.get('id')
        self.email = data.get('email')
        self.phone = data.get('phone')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.tenant = data.get('tenant')
        self.tenant_name = data.get('tenant_name')
        self.roles = data.get('roles', [])
        self.is_super_admin = data.get('is_super_admin', False)
        self.profile_picture = data.get('profile_picture')
        self.timezone = data.get('timezone', 'Asia/Kolkata')
        self.is_active = data.get('is_active', True)
        self.date_joined = data.get('date_joined')

        # Store original data
        self._data = data

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self._data

    def __str__(self):
        return f"{self.email} ({self.tenant_name or 'No Tenant'})"

    def __repr__(self):
        return f"<APIUser: {self.email}>"

    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def role_names(self):
        """Get list of role names"""
        return [role.get('name') for role in self.roles if isinstance(role, dict)]


class APIRole:
    """
    Proxy class representing a Role from SuperAdmin API

    This is not a Django model - it's a simple data container for API responses.
    """

    def __init__(self, data: dict):
        """
        Initialize from API response data

        Args:
            data: Dictionary containing role data from SuperAdmin API
        """
        self.id = data.get('id')
        self.tenant = data.get('tenant')
        self.name = data.get('name')
        self.description = data.get('description', '')
        self.permissions = data.get('permissions', {})
        self.is_active = data.get('is_active', True)
        self.created_by = data.get('created_by')
        self.created_by_email = data.get('created_by_email')
        self.member_count = data.get('member_count', 0)
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

        # Store original data
        self._data = data

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self._data

    def __str__(self):
        return f"{self.name} ({self.member_count} members)"

    def __repr__(self):
        return f"<APIRole: {self.name}>"

    def has_permission(self, permission_path: str) -> bool:
        """
        Check if role has a specific permission

        Args:
            permission_path: Dot-separated permission path (e.g., 'crm.leads.create')

        Returns:
            True if role has the permission
        """
        parts = permission_path.split('.')
        perms = self.permissions

        for part in parts:
            if isinstance(perms, dict):
                perms = perms.get(part)
                if perms is None:
                    return False
            else:
                return bool(perms)

        return bool(perms)
