from rest_framework import permissions


class IsAdministrator(permissions.BasePermission):
    """Allow access only to administrators"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Administrator').exists()
        )


class IsDoctor(permissions.BasePermission):
    """Allow access only to doctors"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Doctor').exists()
        )


class IsDoctorOrReadOnly(permissions.BasePermission):
    """Allow doctors to edit, others to view"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Doctor').exists()
        )


class IsPatient(permissions.BasePermission):
    """Allow access only to patients"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Patient').exists()
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow owners to edit their own data, admins can edit all"""
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.groups.filter(name='Administrator').exists():
            return True
        
        # Check if object has user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsReceptionist(permissions.BasePermission):
    """Allow access only to receptionists"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Receptionist').exists()
        )


class IsPharmacist(permissions.BasePermission):
    """Allow access only to pharmacists"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Pharmacist').exists()
        )


class IsLabTechnician(permissions.BasePermission):
    """Allow access only to lab technicians"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Lab Technician').exists()
        )


class IsNurse(permissions.BasePermission):
    """Allow access only to nurses"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Nurse').exists()
        )


class CanManageStaff(permissions.BasePermission):
    """Check if user can manage staff"""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_perm('accounts.manage_staff')
        )