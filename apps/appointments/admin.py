from django.contrib import admin
from .models import Appointment, AppointmentType


@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    """Admin configuration for AppointmentType"""
    list_display = ['name', 'duration_default']
    search_fields = ['name', 'description']
    
    def get_queryset(self, request):
        """Optimize the queryset"""
        return super().get_queryset(request)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin configuration for Appointment"""
    list_display = [
        'appointment_id', 'patient', 'doctor', 'appointment_date', 
        'appointment_time', 'status', 'priority', 'is_paid'
    ]
    list_filter = [
        'status', 'priority', 'is_paid', 
        'is_follow_up', 'appointment_date',
        ('doctor', admin.RelatedOnlyFieldListFilter),
        ('patient', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'appointment_id', 'patient__first_name', 
        'patient__last_name', 'doctor__user__first_name', 
        'doctor__user__last_name', 'chief_complaint'
    ]
    
    readonly_fields = [
        'appointment_id', 'created_at', 'updated_at', 
        'checked_in_at', 'actual_start_time', 'actual_end_time',
        'waiting_time_minutes', 'cancelled_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'appointment_id', 'patient', 'doctor', 
                'appointment_type', 'appointment_date', 
                'appointment_time', 'end_time', 'duration_minutes'
            )
        }),
        ('Status & Priority', {
            'fields': (
                'status', 'priority', 'is_follow_up', 
                'original_appointment'
            )
        }),
        ('Medical Details', {
            'fields': (
                'chief_complaint', 'symptoms', 'notes'
            )
        }),
        ('Financial Details', {
            'fields': (
                'consultation_fee', 'is_paid', 'payment_method'
            )
        }),
        ('Timing Details', {
            'fields': (
                'checked_in_at', 'actual_start_time', 
                'actual_end_time', 'waiting_time_minutes'
            )
        }),
        ('Cancellation Details', {
            'fields': (
                'cancelled_at', 'cancelled_by', 
                'cancellation_reason'
            )
        }),
        ('Approval Details', {
            'fields': (
                'approved_by', 'approved_at'
            )
        }),
        ('Creation Tracking', {
            'fields': (
                'created_by', 'created_at', 'updated_at'
            )
        })
    )