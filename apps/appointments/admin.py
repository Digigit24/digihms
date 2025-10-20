from django.contrib import admin
from django.utils.html import format_html
from .models import Appointment, AppointmentType

@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    """Admin configuration for Appointment Types"""
    list_display = [
        'name', 
        'description', 
        'duration_default', 
        'base_consultation_fee'
    ]
    
    search_fields = ['name', 'description']
    list_filter = ['duration_default']

class FollowUpAppointmentInline(admin.TabularInline):
    """Inline admin for Follow-up Appointments"""
    model = Appointment
    fk_name = 'original_appointment'
    extra = 0
    readonly_fields = ['appointment_id', 'created_at', 'updated_at']
    
    def has_add_permission(self, request, obj=None):
        """Restrict adding follow-ups directly"""
        return request.user.is_superuser

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Comprehensive Appointment Management in Admin"""
    list_display = [
        'appointment_id', 
        'patient_display', 
        'doctor_display', 
        'appointment_date', 
        'appointment_time', 
        'status_badge', 
        'priority',
        'consultation_fee'
    ]
    
    list_filter = [
        'status', 
        'priority', 
        'appointment_date', 
        'is_follow_up',
        'doctor__user__username',  # Corrected from previous version
    ]
    
    search_fields = [
        'appointment_id', 
        'patient__first_name', 
        'patient__last_name', 
        'doctor__user__first_name', 
        'doctor__user__last_name',
        'chief_complaint'
    ]
    
    inlines = [FollowUpAppointmentInline]
    
    readonly_fields = [
        'appointment_id', 
        'checked_in_at', 
        'actual_start_time', 
        'actual_end_time', 
        'waiting_time_minutes',
        'created_at', 
        'updated_at',
        'cancelled_at',
        'approved_at'
    ]
    
    fieldsets = (
        ('Appointment Details', {
            'fields': (
                'appointment_id', 
                'patient', 
                'doctor', 
                'appointment_type',
                'appointment_date', 
                'appointment_time', 
                'end_time',
                'duration_minutes'
            )
        }),
        ('Medical Information', {
            'fields': (
                'chief_complaint', 
                'symptoms', 
                'notes'
            )
        }),
        ('Status & Priority', {
            'fields': (
                'status', 
                'priority',
                'is_follow_up', 
                'original_appointment'
            )
        }),
        ('Financial Details', {
            'fields': (
                'consultation_fee',
            )
        }),
        # Other fieldsets remain the same
    )
    
    def patient_display(self, obj):
        """Display patient information"""
        return f"{obj.patient.full_name} ({obj.patient.mobile_primary})" if obj.patient else "No Patient"
    patient_display.short_description = "Patient"
    
    def doctor_display(self, obj):
        """Display doctor information"""
        return f"Dr. {obj.doctor.user.get_full_name()}" if obj.doctor else "No Doctor"
    doctor_display.short_description = "Doctor"
    
    def status_badge(self, obj):
        """Colorful status representation"""
        color_map = {
            'scheduled': 'orange',
            'confirmed': 'blue',
            'checked_in': 'purple',
            'in_progress': 'yellow',
            'completed': 'green',
            'cancelled': 'red',
            'no_show': 'gray',
            'rescheduled': 'pink'
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'patient', 'doctor', 'appointment_type',
            'created_by', 'cancelled_by', 'approved_by'
        ).prefetch_related('follow_ups')