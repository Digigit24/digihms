from functools import wraps
from django.http import JsonResponse
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


def check_permission(request, permission_key, resource_owner_id=None):
    """
    Check if the current user has the specified permission.
    
    Args:
        request: Django request object with JWT data
        permission_key: Permission key (e.g., 'hms.patients.view')
        resource_owner_id: Optional resource owner ID for 'own' scope checking
        
    Returns:
        bool: True if permission is granted, False otherwise
    """
    if not hasattr(request, 'permissions'):
        logger.warning("No permissions found in request. JWT middleware may not be configured.")
        return False
    
    permissions = request.permissions
    
    # Check if permission exists
    if permission_key not in permissions:
        logger.debug(f"Permission '{permission_key}' not found for user {request.email}")
        return False
    
    permission_value = permissions[permission_key]
    
    # Handle boolean permissions (create, edit, delete)
    if isinstance(permission_value, bool):
        return permission_value
    
    # Handle scope-based permissions (view)
    if isinstance(permission_value, str):
        if permission_value == 'all':
            return True
        elif permission_value == 'team':
            # TODO: Implement team-based filtering
            # For now, treat as 'own'
            return True
        elif permission_value == 'own':
            # Check if resource belongs to the user
            if resource_owner_id is None:
                return True  # Allow if no specific resource check needed
            return str(resource_owner_id) == str(request.user_id)
        elif permission_value == 'none':
            return False
    
    logger.warning(f"Unknown permission value type for '{permission_key}': {permission_value}")
    return False


def permission_required(permission_key, resource_owner_field=None):
    """
    Decorator to check permissions for view functions.
    
    Args:
        permission_key: Permission key to check
        resource_owner_field: Field name to get resource owner ID from view kwargs
        
    Returns:
        Decorator function
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get resource owner ID if specified
            resource_owner_id = None
            if resource_owner_field and resource_owner_field in kwargs:
                resource_owner_id = kwargs[resource_owner_field]
            
            # Check permission
            if not check_permission(request, permission_key, resource_owner_id):
                return JsonResponse({
                    'error': 'Permission denied',
                    'detail': f'Insufficient permissions for {permission_key}'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_queryset_for_permission(queryset, request, view_permission_key, owner_field='created_by_id'):
    """
    Filter queryset based on user permissions.
    
    Args:
        queryset: Django QuerySet to filter
        request: Django request object with JWT data
        view_permission_key: Permission key for viewing (e.g., 'hms.patients.view')
        owner_field: Field name that contains the owner/creator ID
        
    Returns:
        QuerySet: Filtered queryset based on permissions
    """
    if not hasattr(request, 'permissions'):
        logger.warning("No permissions found in request. Returning empty queryset.")
        return queryset.none()
    
    permissions = request.permissions
    
    # Check if user has view permission
    if view_permission_key not in permissions:
        logger.debug(f"No view permission '{view_permission_key}' for user {request.email}")
        return queryset.none()
    
    permission_value = permissions[view_permission_key]
    
    # Handle scope-based filtering
    if permission_value == 'all':
        # User can see all records
        return queryset
    elif permission_value == 'team':
        # TODO: Implement team-based filtering
        # For now, treat as 'own'
        return queryset.filter(**{owner_field: request.user_id})
    elif permission_value == 'own':
        # User can only see their own records
        return queryset.filter(**{owner_field: request.user_id})
    elif permission_value == 'none' or not permission_value:
        # User cannot see any records
        return queryset.none()
    
    logger.warning(f"Unknown permission value for '{view_permission_key}': {permission_value}")
    return queryset.none()


class PermissionMixin:
    """
    Mixin for ViewSets to handle permission-based filtering and validation.
    """
    
    # Override these in your ViewSet
    permission_mapping = {
        'list': None,      # e.g., 'hms.patients.view'
        'retrieve': None,  # e.g., 'hms.patients.view'
        'create': None,    # e.g., 'hms.patients.create'
        'update': None,    # e.g., 'hms.patients.edit'
        'partial_update': None,  # e.g., 'hms.patients.edit'
        'destroy': None,   # e.g., 'hms.patients.delete'
    }
    
    owner_field = 'created_by_id'  # Field that contains owner/creator ID
    
    def get_required_permission(self):
        """Get the required permission for the current action."""
        action = getattr(self, 'action', None)
        return self.permission_mapping.get(action)
    
    def check_object_permission(self, obj):
        """Check if user has permission to access specific object."""
        permission_key = self.get_required_permission()
        if not permission_key:
            return True
        
        # Get owner ID from object
        owner_id = None
        if hasattr(obj, self.owner_field.replace('_id', '')):
            owner_obj = getattr(obj, self.owner_field.replace('_id', ''))
            owner_id = getattr(owner_obj, 'id', None) if owner_obj else None
        elif hasattr(obj, self.owner_field):
            owner_id = getattr(obj, self.owner_field)
        
        return check_permission(self.request, permission_key, owner_id)
    
    def get_queryset(self):
        """Filter queryset based on permissions."""
        queryset = super().get_queryset()
        
        # Get view permission for list/retrieve actions
        if self.action in ['list', 'retrieve']:
            view_permission = self.permission_mapping.get(self.action)
            if view_permission:
                queryset = get_queryset_for_permission(
                    queryset, 
                    self.request, 
                    view_permission, 
                    self.owner_field
                )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set owner fields when creating objects."""
        # Check create permission
        create_permission = self.permission_mapping.get('create')
        if create_permission and not check_permission(self.request, create_permission):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Insufficient permissions to create this resource")
        
        # Set tenant_id and owner fields
        save_kwargs = {}
        
        # Set tenant_id if model has this field
        if hasattr(serializer.Meta.model, 'tenant_id'):
            save_kwargs['tenant_id'] = self.request.tenant_id
        
        # Set owner field if it exists
        owner_field_name = self.owner_field.replace('_id', '')
        if hasattr(serializer.Meta.model, owner_field_name):
            save_kwargs[owner_field_name + '_id'] = self.request.user_id
        elif hasattr(serializer.Meta.model, self.owner_field):
            save_kwargs[self.owner_field] = self.request.user_id
        
        serializer.save(**save_kwargs)
    
    def perform_update(self, serializer):
        """Check permissions before updating."""
        update_permission = self.permission_mapping.get('update') or self.permission_mapping.get('partial_update')
        if update_permission and not self.check_object_permission(serializer.instance):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Insufficient permissions to update this resource")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Check permissions before deleting."""
        delete_permission = self.permission_mapping.get('destroy')
        if delete_permission and not self.check_object_permission(instance):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Insufficient permissions to delete this resource")
        
        instance.delete()


# Permission key constants for HMS
class HMSPermissions:
    """Constants for HMS permission keys."""
    
    # Patient permissions
    PATIENTS_VIEW = 'hms.patients.view'
    PATIENTS_CREATE = 'hms.patients.create'
    PATIENTS_EDIT = 'hms.patients.edit'
    PATIENTS_DELETE = 'hms.patients.delete'
    
    # Appointment permissions
    APPOINTMENTS_VIEW = 'hms.appointments.view'
    APPOINTMENTS_CREATE = 'hms.appointments.create'
    APPOINTMENTS_EDIT = 'hms.appointments.edit'
    APPOINTMENTS_DELETE = 'hms.appointments.delete'
    
    # Doctor permissions
    DOCTORS_VIEW = 'hms.doctors.view'
    DOCTORS_CREATE = 'hms.doctors.create'
    DOCTORS_EDIT = 'hms.doctors.edit'
    DOCTORS_DELETE = 'hms.doctors.delete'
    
    # Prescription permissions
    PRESCRIPTIONS_VIEW = 'hms.prescriptions.view'
    PRESCRIPTIONS_CREATE = 'hms.prescriptions.create'
    PRESCRIPTIONS_EDIT = 'hms.prescriptions.edit'
    PRESCRIPTIONS_DELETE = 'hms.prescriptions.delete'
    
    # Billing permissions
    BILLING_VIEW = 'hms.billing.view'
    BILLING_CREATE = 'hms.billing.create'
    BILLING_EDIT = 'hms.billing.edit'
    BILLING_DELETE = 'hms.billing.delete'
    
    # OPD permissions
    OPD_VIEW = 'hms.opd.view'
    OPD_CREATE = 'hms.opd.create'
    OPD_EDIT = 'hms.opd.edit'
    OPD_DELETE = 'hms.opd.delete'
    
    # Pharmacy permissions
    PHARMACY_VIEW = 'hms.pharmacy.view'
    PHARMACY_CREATE = 'hms.pharmacy.create'
    PHARMACY_EDIT = 'hms.pharmacy.edit'
    PHARMACY_DELETE = 'hms.pharmacy.delete'
    
    # Reports permissions
    REPORTS_VIEW = 'hms.reports.view'
    REPORTS_CREATE = 'hms.reports.create'
    
    # Admin permissions
    ADMIN_VIEW = 'hms.admin.view'
    ADMIN_MANAGE = 'hms.admin.manage'


def has_any_permission(request, permission_keys):
    """
    Check if user has any of the specified permissions.
    
    Args:
        request: Django request object
        permission_keys: List of permission keys to check
        
    Returns:
        bool: True if user has at least one permission
    """
    return any(check_permission(request, key) for key in permission_keys)


def has_all_permissions(request, permission_keys):
    """
    Check if user has all of the specified permissions.
    
    Args:
        request: Django request object
        permission_keys: List of permission keys to check
        
    Returns:
        bool: True if user has all permissions
    """
    return all(check_permission(request, key) for key in permission_keys)


def get_user_permissions(request):
    """
    Get all permissions for the current user.
    
    Args:
        request: Django request object
        
    Returns:
        dict: User permissions from JWT
    """
    return getattr(request, 'permissions', {})