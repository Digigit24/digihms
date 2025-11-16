from django.contrib import admin
from common.admin_site import tenant_admin_site, TenantModelAdmin
from .models import Specialty, DoctorProfile, DoctorAvailability


class SpecialtyAdmin(TenantModelAdmin):
    """Admin for Medical Specialties"""
    list_display = ['name', 'code', 'department', 'is_active', 'doctors_count', 'created_at']
    list_filter = ['is_active', 'department', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'department')
        }),
        ('Details', {
            'fields': ('description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def doctors_count(self, obj):
        """Count of active doctors in this specialty"""
        return obj.doctors.filter(status='active').count()
    doctors_count.short_description = 'Active Doctors'


class DoctorAvailabilityInline(admin.TabularInline):
    """Inline admin for Doctor Availability"""
    model = DoctorAvailability
    extra = 1
    fields = ['day_of_week', 'start_time', 'end_time', 'is_available', 'max_appointments']


class DoctorProfileAdmin(TenantModelAdmin):
    """Admin for Doctor Profiles"""
    list_display = [
        'get_doctor_name', 'medical_license_number', 'status',
        'consultation_fee', 'years_of_experience', 'average_rating',
        'is_license_valid', 'created_at'
    ]
    list_filter = [
        'status', 'is_available_online', 'is_available_offline',
        'specialties', 'created_at'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'medical_license_number', 'qualifications'
    ]
    readonly_fields = [
        'average_rating', 'total_reviews', 'total_consultations',
        'is_license_valid', 'created_at', 'updated_at'
    ]
    filter_horizontal = ['specialties']
    inlines = [DoctorAvailabilityInline]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',),
            'description': 'Link to user account (required for login)'
        }),
        ('License Information', {
            'fields': (
                'medical_license_number', 'license_issuing_authority',
                'license_issue_date', 'license_expiry_date', 'is_license_valid'
            )
        }),
        ('Professional Information', {
            'fields': (
                'qualifications', 'specialties', 'years_of_experience'
            )
        }),
        ('Consultation Settings', {
            'fields': (
                'consultation_fee', 'consultation_duration',
                'is_available_online', 'is_available_offline'
            )
        }),
        ('Ratings & Statistics', {
            'fields': (
                'average_rating', 'total_reviews', 'total_consultations'
            ),
            'classes': ('collapse',),
            'description': 'Read-only statistics updated by the system'
        }),
        ('Additional Information', {
            'fields': ('signature', 'languages_spoken', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_doctor_name(self, obj):
        """Display doctor's full name"""
        if obj.full_name:
            return f"Dr. {obj.full_name}"
        return f"Dr. {obj.user.email}"
    get_doctor_name.short_description = 'Doctor Name'
    get_doctor_name.admin_order_field = 'user__first_name'
    
    def is_license_valid(self, obj):
        """Display license validity status"""
        return obj.is_license_valid
    is_license_valid.boolean = True
    is_license_valid.short_description = 'License Valid'


class DoctorAvailabilityAdmin(TenantModelAdmin):
    """Admin for Doctor Availability"""
    list_display = [
        'doctor', 'day_of_week', 'start_time', 'end_time',
        'is_available', 'max_appointments', 'created_at'
    ]
    list_filter = ['day_of_week', 'is_available', 'doctor__status', 'created_at']
    search_fields = [
        'doctor__user__first_name', 'doctor__user__last_name',
        'doctor__medical_license_number'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['doctor', 'day_of_week', 'start_time']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Doctor', {
            'fields': ('doctor',)
        }),
        ('Schedule', {
            'fields': (
                'day_of_week', 'start_time', 'end_time',
                'is_available', 'max_appointments'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Register with tenant_admin_site
tenant_admin_site.register(Specialty, SpecialtyAdmin)
tenant_admin_site.register(DoctorProfile, DoctorProfileAdmin)
tenant_admin_site.register(DoctorAvailability, DoctorAvailabilityAdmin)