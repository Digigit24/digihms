# opd/admin.py
from django.contrib import admin
from common.admin_site import tenant_admin_site, TenantModelAdmin
from django.utils.html import format_html
from .models import (
    ClinicalNoteTemplate, ClinicalNoteTemplateField, ClinicalNoteTemplateFieldOption, 
    ClinicalNoteTemplateFieldResponse, ClinicalNoteTemplateGroup, ClinicalNoteTemplateResponse, 
    Visit, OPDBill, ProcedureMaster, ProcedurePackage,
    ProcedureBill, ProcedureBillItem, ClinicalNote,
    VisitFinding, VisitAttachment
)
from django import forms


class VisitAdmin(TenantModelAdmin):
    """Admin interface for Visit model."""
    
    list_display = [
        'visit_number',
        'patient',
        'doctor',
        'visit_date',
        'visit_type',
        'status',
        'payment_status_badge',
        'total_amount',
    ]
    list_filter = [
        'status',
        'payment_status',
        'visit_type',
        'visit_date',
        'is_follow_up',
    ]
    search_fields = [
        'visit_number',
        'patient__first_name',
        'patient__last_name',
        'doctor__first_name',
        'doctor__last_name',
    ]
    readonly_fields = [
        'visit_number',
        'entry_time',
        'visit_date',
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['patient', 'doctor', 'appointment', 'referred_by']
    
    fieldsets = (
        ('Visit Information', {
            'fields': (
                'visit_number',
                'visit_date',
                'entry_time',
                'visit_type',
                'is_follow_up',
            )
        }),
        ('Patient & Doctor', {
            'fields': (
                'patient',
                'doctor',
                'appointment',
                'referred_by',
            )
        }),
        ('Queue Management', {
            'fields': (
                'status',
                'queue_position',
                'consultation_start_time',
                'consultation_end_time',
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_status',
                'total_amount',
                'paid_amount',
                'balance_amount',
            )
        }),
        ('Audit', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def payment_status_badge(self, obj):
        """Display payment status with color badge."""
        colors = {
            'paid': 'green',
            'partial': 'orange',
            'unpaid': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.payment_status, 'gray'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment Status'


class OPDBillAdmin(TenantModelAdmin):
    """Admin interface for OPDBill model."""
    
    list_display = [
        'bill_number',
        'visit',
        'doctor',
        'bill_date',
        'total_amount',
        'payable_amount',
        'payment_status_badge',
    ]
    list_filter = [
        'payment_status',
        'opd_type',
        'charge_type',
        'payment_mode',
        'bill_date',
    ]
    search_fields = [
        'bill_number',
        'visit__visit_number',
        'doctor__first_name',
        'doctor__last_name',
    ]
    readonly_fields = [
        'bill_number',
        'bill_date',
        'payable_amount',
        'balance_amount',
        'payment_status',
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['visit', 'doctor']
    
    fieldsets = (
        ('Bill Information', {
            'fields': (
                'bill_number',
                'bill_date',
                'visit',
                'doctor',
            )
        }),
        ('Bill Classification', {
            'fields': (
                'opd_type',
                'opd_subtype',
                'charge_type',
            )
        }),
        ('Medical Details', {
            'fields': (
                'diagnosis',
                'remarks',
            )
        }),
        ('Financial Details', {
            'fields': (
                'total_amount',
                'discount_percent',
                'discount_amount',
                'payable_amount',
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_mode',
                'payment_details',
                'received_amount',
                'balance_amount',
                'payment_status',
            )
        }),
        ('Audit', {
            'fields': (
                'billed_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def payment_status_badge(self, obj):
        """Display payment status with color badge."""
        colors = {
            'paid': 'green',
            'partial': 'orange',
            'unpaid': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.payment_status, 'gray'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment Status'


class ProcedureMasterAdmin(TenantModelAdmin):
    """Admin interface for ProcedureMaster model."""
    
    list_display = [
        'code',
        'name',
        'category',
        'default_charge',
        'is_active_badge',
    ]
    list_filter = [
        'category',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'code',
        'name',
        'description',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'code',
                'category',
                'description',
            )
        }),
        ('Pricing', {
            'fields': (
                'default_charge',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def is_active_badge(self, obj):
        """Display active status with badge."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'green' if obj.is_active else 'red',
            'Active' if obj.is_active else 'Inactive'
        )
    is_active_badge.short_description = 'Status'


class ProcedurePackageAdmin(TenantModelAdmin):
    """Admin interface for ProcedurePackage model."""
    
    list_display = [
        'code',
        'name',
        'total_charge',
        'discounted_charge',
        'savings_display',
        'is_active_badge',
    ]
    list_filter = [
        'is_active',
        'created_at',
    ]
    search_fields = [
        'code',
        'name',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    filter_horizontal = ['procedures']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'code',
            )
        }),
        ('Procedures', {
            'fields': (
                'procedures',
            )
        }),
        ('Pricing', {
            'fields': (
                'total_charge',
                'discounted_charge',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def savings_display(self, obj):
        """Display savings amount and percentage."""
        return format_html(
            '₹{} ({}%)',
            obj.savings_amount,
            round(obj.discount_percent, 2)
        )
    savings_display.short_description = 'Savings'
    
    def is_active_badge(self, obj):
        """Display active status with badge."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'green' if obj.is_active else 'red',
            'Active' if obj.is_active else 'Inactive'
        )
    is_active_badge.short_description = 'Status'


class ProcedureBillItemInline(admin.TabularInline):
    """Inline admin for ProcedureBillItem."""
    
    model = ProcedureBillItem
    extra = 1
    fields = [
        'procedure',
        'particular_name',
        'quantity',
        'unit_charge',
        'amount',
        'note',
        'item_order',
    ]
    autocomplete_fields = ['procedure']


class ProcedureBillAdmin(TenantModelAdmin):
    """Admin interface for ProcedureBill model."""
    
    list_display = [
        'bill_number',
        'visit',
        'doctor',
        'bill_date',
        'total_amount',
        'payable_amount',
        'payment_status_badge',
    ]
    list_filter = [
        'payment_status',
        'bill_type',
        'payment_mode',
        'bill_date',
    ]
    search_fields = [
        'bill_number',
        'visit__visit_number',
        'doctor__first_name',
        'doctor__last_name',
    ]
    readonly_fields = [
        'bill_number',
        'bill_date',
        'total_amount',
        'payable_amount',
        'balance_amount',
        'payment_status',
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['visit', 'doctor']
    
    def get_inlines(self, request, obj=None):
        """Only show inlines when editing an existing object."""
        if obj:  # obj exists, so we're on the change page
            return [ProcedureBillItemInline]
        return []  # No inlines when creating new object
    
    fieldsets = (
        ('Bill Information', {
            'fields': (
                'bill_number',
                'bill_date',
                'visit',
                'doctor',
            )
        }),
        ('Bill Classification', {
            'fields': (
                'bill_type',
                'category',
            )
        }),
        ('Financial Details', {
            'fields': (
                'total_amount',
                'discount_percent',
                'discount_amount',
                'payable_amount',
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_mode',
                'payment_details',
                'received_amount',
                'balance_amount',
                'payment_status',
            )
        }),
        ('Audit', {
            'fields': (
                'billed_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def payment_status_badge(self, obj):
        """Display payment status with color badge."""
        colors = {
            'paid': 'green',
            'partial': 'orange',
            'unpaid': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.payment_status, 'gray'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment Status'


class ClinicalNoteAdmin(TenantModelAdmin):
    """Admin interface for ClinicalNote model."""
    
    list_display = [
        'visit',
        'note_date',
        'diagnosis_short',
        'next_followup_date',
    ]
    list_filter = [
        'note_date',
        'next_followup_date',
    ]
    search_fields = [
        'visit__visit_number',
        'diagnosis',
        'present_complaints',
    ]
    readonly_fields = [
        'note_date',
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['visit', 'referred_doctor']
    
    fieldsets = (
        ('Visit Information', {
            'fields': (
                'visit',
                'ehr_number',
                'note_date',
            )
        }),
        ('Clinical Assessment', {
            'fields': (
                'present_complaints',
                'observation',
                'diagnosis',
            )
        }),
        ('Treatment', {
            'fields': (
                'investigation',
                'treatment_plan',
                'medicines_prescribed',
                'doctor_advice',
            )
        }),
        ('Surgery/Referral', {
            'fields': (
                'suggested_surgery_name',
                'suggested_surgery_reason',
                'referred_doctor',
            )
        }),
        ('Follow-up', {
            'fields': (
                'next_followup_date',
            )
        }),
        ('Audit', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def diagnosis_short(self, obj):
        """Display truncated diagnosis."""
        if obj.diagnosis:
            return obj.diagnosis[:50] + ('...' if len(obj.diagnosis) > 50 else '')
        return '-'
    diagnosis_short.short_description = 'Diagnosis'


class VisitFindingAdmin(TenantModelAdmin):
    """Admin interface for VisitFinding model."""
    
    list_display = [
        'visit',
        'finding_date',
        'finding_type',
        'temperature',
        'pulse',
        'bp_display',
        'bmi',
        'bmi_category_display',
    ]
    list_filter = [
        'finding_type',
        'finding_date',
    ]
    search_fields = [
        'visit__visit_number',
    ]
    readonly_fields = [
        'bmi',
        'finding_date',
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['visit']
    
    fieldsets = (
        ('Visit Information', {
            'fields': (
                'visit',
                'finding_date',
                'finding_type',
            )
        }),
        ('Vital Signs', {
            'fields': (
                'temperature',
                'pulse',
                'bp_systolic',
                'bp_diastolic',
                'respiratory_rate',
                'spo2',
            )
        }),
        ('Anthropometry', {
            'fields': (
                'weight',
                'height',
                'bmi',
            )
        }),
        ('Systemic Examination', {
            'fields': (
                'tongue',
                'throat',
                'cns',
                'rs',
                'cvs',
                'pa',
            )
        }),
        ('Audit', {
            'fields': (
                'recorded_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def bp_display(self, obj):
        """Display formatted blood pressure."""
        return obj.blood_pressure or '-'
    bp_display.short_description = 'BP'
    
    def bmi_category_display(self, obj):
        """Display BMI category with color."""
        category = obj.bmi_category
        if not category:
            return '-'
        
        colors = {
            'Underweight': 'orange',
            'Normal': 'green',
            'Overweight': 'orange',
            'Obese': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(category, 'gray'),
            category
        )
    bmi_category_display.short_description = 'BMI Category'


class VisitAttachmentAdmin(TenantModelAdmin):
    """Admin interface for VisitAttachment model."""
    
    list_display = [
        'visit',
        'file_name',
        'file_type',
        'file_size_display',
        'uploaded_at',
        'uploaded_by',
    ]
    list_filter = [
        'file_type',
        'uploaded_at',
    ]
    search_fields = [
        'visit__visit_number',
        'file_name',
        'description',
    ]
    readonly_fields = [
        'uploaded_at',
    ]
    autocomplete_fields = ['visit']
    
    fieldsets = (
        ('Attachment Information', {
            'fields': (
                'visit',
                'file',
                'file_name',
                'file_type',
                'description',
            )
        }),
        ('Audit', {
            'fields': (
                'uploaded_by',
                'uploaded_at',
            )
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size."""
        return obj.get_file_size() or '-'
    file_size_display.short_description = 'File Size'

    
class ClinicalNoteTemplateGroupAdmin(TenantModelAdmin):
    """Admin interface for Template Groups."""
    
    list_display = [
        'name',
        'display_order',
        'template_count',
        'is_active_badge',
        'created_at',
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('Group Information', {
            'fields': ('name', 'description', 'display_order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def template_count(self, obj):
        """Display number of templates in this group."""
        count = obj.templates.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    template_count.short_description = 'Templates'
    
    def is_active_badge(self, obj):
        """Display active status with badge."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'green' if obj.is_active else 'red',
            'Active' if obj.is_active else 'Inactive'
        )
    is_active_badge.short_description = 'Status'


# ============================================================================
# TEMPLATE FIELD OPTION INLINE
# ============================================================================

class ClinicalNoteTemplateFieldOptionInline(admin.TabularInline):
    """Inline admin for field options."""
    
    model = ClinicalNoteTemplateFieldOption
    extra = 1
    fields = [
        'option_value',
        'option_label',
        'display_order',
        'is_active',
        'metadata',
    ]
    ordering = ['display_order', 'option_label']


# ============================================================================
# TEMPLATE FIELD INLINE
# ============================================================================

class ClinicalNoteTemplateFieldInline(admin.StackedInline):
    """Inline admin for template fields."""
    
    model = ClinicalNoteTemplateField
    extra = 1
    fields = [
        ('field_name', 'field_label'),
        ('field_type', 'is_required'),
        ('placeholder', 'help_text'),
        'default_value',
        ('display_order', 'column_width'),
        ('min_value', 'max_value'),
        ('min_length', 'max_length'),
        'show_condition',
        'is_active',
    ]
    ordering = ['display_order']
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/template_field_admin.js',)


# ============================================================================
# TEMPLATE FIELD ADMIN (Separate)
# ============================================================================

class ClinicalNoteTemplateFieldAdmin(TenantModelAdmin):
    """Standalone admin for managing template fields."""
    
    list_display = [
        'field_label',
        'template',
        'field_type_badge',
        'is_required_badge',
        'display_order',
        'option_count',
        'is_active_badge',
    ]
    list_filter = [
        'field_type',
        'is_required',
        'is_active',
        'template__group',
        'template',
    ]
    search_fields = [
        'field_name',
        'field_label',
        'template__name',
    ]
    ordering = ['template', 'display_order']
    inlines = [ClinicalNoteTemplateFieldOptionInline]
    
    fieldsets = (
        ('Field Definition', {
            'fields': (
                'template',
                ('field_name', 'field_label'),
                'field_type',
            )
        }),
        ('Field Configuration', {
            'fields': (
                'help_text',
                'placeholder',
                'default_value',
            )
        }),
        ('Validation Rules', {
            'fields': (
                'is_required',
                ('min_value', 'max_value'),
                ('min_length', 'max_length'),
            )
        }),
        ('Display Configuration', {
            'fields': (
                ('display_order', 'column_width'),
                'show_condition',
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def field_type_badge(self, obj):
        """Display field type with badge."""
        colors = {
            'text': '#6c757d',
            'number': '#007bff',
            'boolean': '#28a745',
            'date': '#fd7e14',
            'select': '#17a2b8',
            'multiselect': '#6610f2',
            'image': '#e83e8c',
        }
        color = colors.get(obj.field_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_field_type_display()
        )
    field_type_badge.short_description = 'Type'
    
    def is_required_badge(self, obj):
        """Display required status."""
        if obj.is_required:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">Required</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">Optional</span>'
        )
    is_required_badge.short_description = 'Required'
    
    def option_count(self, obj):
        """Display number of options."""
        count = obj.options.count()
        if count > 0:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                count
            )
        return '-'
    option_count.short_description = 'Options'
    
    def is_active_badge(self, obj):
        """Display active status."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'green' if obj.is_active else 'red',
            'Active' if obj.is_active else 'Inactive'
        )
    is_active_badge.short_description = 'Status'


# ============================================================================
# TEMPLATE ADMIN
# ============================================================================

class ClinicalNoteTemplateAdmin(TenantModelAdmin):
    """Admin interface for Clinical Note Templates."""
    
    list_display = [
        'code',
        'name',
        'group',
        'field_count',
        'response_count',
        'is_active_badge',
        'display_order',
    ]
    list_filter = [
        'is_active',
        'group',
        'created_at',
    ]
    search_fields = [
        'name',
        'code',
        'description',
    ]
    ordering = ['display_order', 'name']
    inlines = [ClinicalNoteTemplateFieldInline]
    
    fieldsets = (
        ('Template Information', {
            'fields': (
                ('name', 'code'),
                'group',
                'description',
            )
        }),
        ('Display Settings', {
            'fields': (
                'display_order',
                'is_active',
            )
        }),
    )
    
    def field_count(self, obj):
        """Display number of fields."""
        count = obj.fields.filter(is_active=True).count()
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    field_count.short_description = 'Fields'
    
    def response_count(self, obj):
        """Display number of responses."""
        count = obj.responses.count()
        if count > 0:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                count
            )
        return '0'
    response_count.short_description = 'Responses'
    
    def is_active_badge(self, obj):
        """Display active status."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'green' if obj.is_active else 'red',
            'Active' if obj.is_active else 'Inactive'
        )
    is_active_badge.short_description = 'Status'


# ============================================================================
# TEMPLATE RESPONSE FIELD INLINE
# ============================================================================

class ClinicalNoteTemplateFieldResponseInline(admin.TabularInline):
    """Inline admin for field responses."""
    
    model = ClinicalNoteTemplateFieldResponse
    extra = 0
    can_delete = False
    fields = [
        'field',
        'get_field_type',
        'value_display',
    ]
    readonly_fields = [
        'field',
        'get_field_type',
        'value_display',
    ]
    
    def get_field_type(self, obj):
        """Display field type."""
        return obj.field.get_field_type_display()
    get_field_type.short_description = 'Type'
    
    def value_display(self, obj):
        """Display the value."""
        return obj.get_display_value()
    value_display.short_description = 'Value'


# ============================================================================
# TEMPLATE RESPONSE ADMIN
# ============================================================================

class ClinicalNoteTemplateResponseAdmin(TenantModelAdmin):
    """Admin interface for Template Responses."""
    
    list_display = [
        'visit',
        'template',
        'response_date',
        'status_badge',
        'filled_by',
        'reviewed_by',
    ]
    list_filter = [
        'status',
        'template',
        'response_date',
    ]
    search_fields = [
        'visit__visit_number',
        'visit__patient__first_name',
        'visit__patient__last_name',
        'template__name',
    ]
    ordering = ['-response_date']
    readonly_fields = [
        'response_date',
        'response_summary',
        'created_at',
        'updated_at',
    ]
    inlines = [ClinicalNoteTemplateFieldResponseInline]
    
    fieldsets = (
        ('Response Information', {
            'fields': (
                'visit',
                'template',
                'response_date',
                'status',
            )
        }),
        ('Summary', {
            'fields': ('response_summary',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': (
                'filled_by',
                'reviewed_by',
                'reviewed_at',
            )
        }),
    )
    
    def status_badge(self, obj):
        """Display status with badge."""
        colors = {
            'draft': '#6c757d',
            'completed': '#007bff',
            'reviewed': '#28a745',
            'archived': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

# Register with tenant_admin_site
tenant_admin_site.register(Visit, VisitAdmin)
tenant_admin_site.register(OPDBill, OPDBillAdmin)
tenant_admin_site.register(ProcedureMaster, ProcedureMasterAdmin)
tenant_admin_site.register(ProcedurePackage, ProcedurePackageAdmin)
tenant_admin_site.register(ProcedureBill, ProcedureBillAdmin)
tenant_admin_site.register(ClinicalNote, ClinicalNoteAdmin)
tenant_admin_site.register(VisitFinding, VisitFindingAdmin)
tenant_admin_site.register(VisitAttachment, VisitAttachmentAdmin)
tenant_admin_site.register(ClinicalNoteTemplateGroup, ClinicalNoteTemplateGroupAdmin)
tenant_admin_site.register(ClinicalNoteTemplateField, ClinicalNoteTemplateFieldAdmin)
tenant_admin_site.register(ClinicalNoteTemplate, ClinicalNoteTemplateAdmin)
tenant_admin_site.register(ClinicalNoteTemplateResponse, ClinicalNoteTemplateResponseAdmin)
