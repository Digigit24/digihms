"""
DigiHMS Accounts Admin

Admin interface for doctor profiles and specialties.
NO local User model - authentication via SuperAdmin.
"""

from django.contrib import admin
from django.utils.html import format_html
from common.admin_site import tenant_admin_site, TenantModelAdmin
from apps.accounts.models import DoctorProfile, Specialty, DoctorAvailability


@admin.register(Specialty, site=tenant_admin_site)
class SpecialtyAdmin(TenantModelAdmin):
    """Admin for medical specialties."""
    list_display = ['name', 'code', 'department', 'is_active', 'tenant_id']
    list_filter = ['is_active', 'department']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['tenant_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'department')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Tenant & Metadata', {
            'fields': ('tenant_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class DoctorAvailabilityInline(admin.TabularInline):
    """Inline admin for doctor availability."""
    model = DoctorAvailability
    extra = 1
    fields = ['day_of_week', 'start_time', 'end_time', 'is_available', 'max_appointments']
    readonly_fields = ['tenant_id']


@admin.register(DoctorProfile, site=tenant_admin_site)
class DoctorProfileAdmin(TenantModelAdmin):
    """Admin for doctor profiles."""
    list_display = [
        'full_name_display', 'email', 'medical_license_number',
        'status_badge', 'experience_display', 'license_status',
        'consultation_fee', 'tenant_id'
    ]
    list_filter = ['status', 'is_available_online', 'is_available_offline', 'specialties']
    search_fields = ['email', 'first_name', 'last_name', 'medical_license_number']
    readonly_fields = [
        'user_id', 'email', 'tenant_id', 'last_synced_at',
        'average_rating', 'total_reviews', 'total_consultations',
        'license_status_display', 'created_at', 'updated_at'
    ]
    filter_horizontal = ['specialties']
    inlines = [DoctorAvailabilityInline]

    fieldsets = (
        ('SuperAdmin User Reference', {
            'fields': ('user_id', 'email', 'first_name', 'last_name', 'last_synced_at'),
            'description': 'User data cached from SuperAdmin. Email and name sync automatically.'
        }),
        ('License Information', {
            'fields': (
                'medical_license_number', 'license_issuing_authority',
                'license_issue_date', 'license_expiry_date', 'license_status_display'
            )
        }),
        ('Professional Information', {
            'fields': (
                'qualifications', 'specialties', 'years_of_experience'
            )
        }),
        ('Consultation Details', {
            'fields': (
                'consultation_fee', 'follow_up_fee', 'consultation_duration',
                'is_available_online', 'is_available_offline'
            )
        }),
        ('Status & Ratings', {
            'fields': (
                'status', 'average_rating', 'total_reviews', 'total_consultations'
            )
        }),
        ('Additional Information', {
            'fields': ('signature', 'languages_spoken'),
            'classes': ('collapse',)
        }),
        ('Tenant & Metadata', {
            'fields': ('tenant_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def full_name_display(self, obj):
        """Display doctor's full name."""
        return obj.full_name or obj.email
    full_name_display.short_description = 'Doctor Name'

    def status_badge(self, obj):
        """Display status with colored badge."""
        color_map = {
            'active': '#27ae60',
            'on_leave': '#f39c12',
            'inactive': '#95a5a6'
        }
        color = color_map.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def experience_display(self, obj):
        """Display years of experience."""
        return f"{obj.years_of_experience} years" if obj.years_of_experience else '-'
    experience_display.short_description = 'Experience'

    def license_status(self, obj):
        """Display license validity status."""
        is_valid = obj.is_license_valid
        if is_valid is None:
            return format_html('<span style="color: #95a5a6;">Unknown</span>')
        elif is_valid:
            return format_html('<span style="color: #27ae60;">✓ Valid</span>')
        else:
            return format_html('<span style="color: #e74c3c;">✗ Expired</span>')
    license_status.short_description = 'License'

    def license_status_display(self, obj):
        """Display detailed license status."""
        is_valid = obj.is_license_valid
        if is_valid is None:
            return 'No expiry date set'
        elif is_valid:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold;">✓ Valid</span> '
                '(Expires: {})',
                obj.license_expiry_date
            )
        else:
            return format_html(
                '<span style="color: #e74c3c; font-weight: bold;">✗ Expired</span> '
                '(Expired on: {})',
                obj.license_expiry_date
            )
    license_status_display.short_description = 'License Status'


# Note: NO User model admin - authentication is handled by SuperAdmin
