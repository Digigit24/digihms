from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    
    list_display = [
        'email', 'username', 'first_name', 'last_name',
        'role', 'is_active', 'is_staff', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser',
        'groups', 'created_at'
    ]
    search_fields = [
        'email', 'username', 'first_name',
        'last_name', 'employee_id'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'date_of_birth',
                'gender', 'phone', 'alternate_phone',
                'profile_picture', 'bio'
            )
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2',
                'city', 'state', 'country', 'pincode'
            )
        }),
        ('Hospital Info', {
            'fields': (
                'employee_id', 'department', 'joining_date'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'is_verified', 'groups', 'user_permissions'
            )
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'password1', 'password2',
                'first_name', 'last_name', 'is_staff', 'is_active'
            ),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']
    
    def role(self, obj):
        """Display user's primary role"""
        return obj.role
    role.short_description = 'Role'