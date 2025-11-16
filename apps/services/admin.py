from django.contrib import admin
from common.admin_site import tenant_admin_site, TenantModelAdmin
from .models import (
    ServiceCategory, 
    DiagnosticTest, 
    NursingCarePackage, 
    HomeHealthcareService
)

class ServiceCategoryAdmin(TenantModelAdmin):
    list_display = ['name', 'type', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name']


class DiagnosticTestAdmin(TenantModelAdmin):
    list_display = [
        'name', 'code', 'category', 
        'sample_type', 'is_active', 'base_price'
    ]
    list_filter = [
        'category', 'sample_type', 
        'is_active', 'is_home_collection'
    ]
    search_fields = ['name', 'code']


class NursingCarePackageAdmin(TenantModelAdmin):
    list_display = [
        'name', 'code', 'category', 
        'package_type', 'is_active', 'base_price'
    ]
    list_filter = ['category', 'package_type', 'is_active']
    search_fields = ['name', 'code']


class HomeHealthcareServiceAdmin(TenantModelAdmin):
    list_display = [
        'name', 'code', 'category', 
        'service_type', 'is_active', 'base_price'
    ]
    list_filter = [
        'category', 'service_type', 
        'staff_type_required', 'is_active'
    ]
    search_fields = ['name', 'code']

# Register with tenant_admin_site
tenant_admin_site.register(ServiceCategory, ServiceCategoryAdmin)
tenant_admin_site.register(DiagnosticTest, DiagnosticTestAdmin)
tenant_admin_site.register(NursingCarePackage, NursingCarePackageAdmin)
tenant_admin_site.register(HomeHealthcareService, HomeHealthcareServiceAdmin)
