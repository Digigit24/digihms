from django.contrib import admin
from .models import Specialty, DoctorProfile, DoctorAvailability


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'is_active', 'created_at']
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


class DoctorAvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 1
    fields = ['day_of_week', 'start_time', 'end_time', 'is_available', 'max_appointments']


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
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
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Professional Information', {
            'fields': (
                'medical_license_number', 'license_issuing_authority',
                'license_issue_date', 'license_expiry_date', 'is_license_valid'
            )
        }),
        ('Qualifications & Experience', {
            'fields': (
                'qualifications', 'specialties', 'years_of_experience'
            )
        }),
        ('Consultation Details', {
            'fields': (
                'consultation_fee', 'consultation_duration',
                'is_available_online', 'is_available_offline'
            )
        }),
        ('Ratings & Statistics', {
            'fields': (
                'average_rating', 'total_reviews', 'total_consultations'
            ),
            'classes': ('collapse',)
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
        return f"Dr. {obj.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor Name'
    get_doctor_name.admin_order_field = 'user__first_name'
    
    def is_license_valid(self, obj):
        return obj.is_license_valid
    is_license_valid.boolean = True
    is_license_valid.short_description = 'License Valid'


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        'doctor', 'day_of_week', 'start_time', 'end_time',
        'is_available', 'max_appointments'
    ]
    list_filter = ['day_of_week', 'is_available', 'doctor__status']
    search_fields = [
        'doctor__user__first_name', 'doctor__user__last_name',
        'doctor__medical_license_number'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['doctor', 'day_of_week', 'start_time']
    
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