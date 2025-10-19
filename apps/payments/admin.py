from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentCategory, Transaction, AccountingPeriod


@admin.register(PaymentCategory)
class PaymentCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Payment Categories"""
    list_display = [
        'name', 
        'category_type', 
        'description'
    ]
    
    list_filter = ['category_type']
    search_fields = ['name', 'description']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Comprehensive Transaction Management in Admin"""
    list_display = [
        'transaction_number', 
        'amount', 
        'category', 
        'transaction_type', 
        'payment_method', 
        'status_badge',
        'created_at'
    ]
    
    list_filter = [
        'transaction_type', 
        'category', 
        'payment_method', 
        'is_reconciled', 
        'created_at'
    ]
    
    search_fields = [
        'transaction_number', 
        'description', 
        'user__first_name', 
        'user__last_name', 
        'user__email'
    ]
    
    readonly_fields = [
        'transaction_number', 
        'created_at', 
        'updated_at',
        'reconciled_at'
    ]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'transaction_number', 
                'amount', 
                'category', 
                'transaction_type', 
                'payment_method', 
                'description'
            )
        }),
        ('Related Object', {
            'fields': (
                'content_type', 
                'object_id'
            )
        }),
        ('User Information', {
            'fields': ('user',)
        }),
        ('Reconciliation', {
            'fields': (
                'is_reconciled', 
                'reconciled_at', 
                'reconciled_by'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 
                'updated_at'
            )
        }),
    )
    
    def status_badge(self, obj):
        """Colorful status representation"""
        color_map = {
            'payment': 'green',
            'refund': 'blue',
            'expense': 'red',
            'adjustment': 'orange'
        }
        color = color_map.get(obj.transaction_type, 'gray')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.get_transaction_type_display()
        )
    status_badge.short_description = "Transaction Type"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'category', 'user', 'reconciled_by'
        )


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    """Admin configuration for Accounting Periods"""
    list_display = [
        'name', 
        'start_date', 
        'end_date', 
        'period_type', 
        'total_income', 
        'total_expenses', 
        'net_profit', 
        'is_closed'
    ]
    
    list_filter = [
        'period_type', 
        'is_closed', 
        'start_date', 
        'end_date'
    ]
    
    search_fields = ['name']
    
    readonly_fields = [
        'total_income', 
        'total_expenses', 
        'net_profit', 
        'closed_at'
    ]
    
    actions = ['calculate_financial_summary']
    
    def calculate_financial_summary(self, request, queryset):
        """
        Action to recalculate financial summary for selected accounting periods
        """
        for period in queryset:
            period.calculate_financial_summary()
        
        self.message_user(request, f"{queryset.count()} accounting periods updated.")
    calculate_financial_summary.short_description = "Recalculate Financial Summary"