from django.contrib import admin
from .models import (
    ServiceCategory, 
    DiagnosticTest, 
    NursingCarePackage, 
    HomeHealthcareService
)

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name']


@admin.register(DiagnosticTest)
class DiagnosticTestAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'category', 
        'sample_type', 'is_active', 'base_price'
    ]
    list_filter = [
        'category', 'sample_type', 
        'is_active', 'is_home_collection'
    ]
    search_fields = ['name', 'code']


@admin.register(NursingCarePackage)
class NursingCarePackageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'category', 
        'package_type', 'is_active', 'base_price'
    ]
    list_filter = ['category', 'package_type', 'is_active']
    search_fields = ['name', 'code']


@admin.register(HomeHealthcareService)
class HomeHealthcareServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'category', 
        'service_type', 'is_active', 'base_price'
    ]
    list_filter = [
        'category', 'service_type', 
        'staff_type_required', 'is_active'
    ]
    search_fields = ['name', 'code']