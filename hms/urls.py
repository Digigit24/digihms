from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.decorators.csrf import csrf_exempt

# ✅ Import drf-spectacular views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)

# ✅ Import custom admin site and authentication views
from common.admin_site import tenant_admin_site
from common.views import (
    TokenLoginView,
    AdminHealthView,
    superadmin_proxy_login_view
)

urlpatterns = [
    # Root URL - redirect to admin
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='home'),

    # ✅ Admin authentication endpoints (must be before admin/ to avoid conflicts)
    path('auth/token-login/', csrf_exempt(TokenLoginView.as_view()), name='admin-token-login'),
    path('auth/superadmin-login/', superadmin_proxy_login_view, name='admin-superadmin-login'),
    path('auth/health/', AdminHealthView.as_view(), name='admin-health'),

    # ✅ Custom tenant-based admin (replaces default admin.site.urls)
    path('admin/', tenant_admin_site.urls),

    # API endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/doctors/', include('apps.doctors.urls')),
    path('api/patients/', include('apps.patients.urls')),
    path('api/hospital/', include('apps.hospital.urls')),
    path('api/appointments/', include('apps.appointments.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/pharmacy/', include('apps.pharmacy.urls')),
    path('api/services/', include('apps.services.urls')),
    path('api/opd/', include('apps.opd.urls')),

    # ✅ API Documentation endpoints
    # OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI (Interactive documentation)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ReDoc UI (Alternative documentation)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)