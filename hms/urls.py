from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ✅ Import drf-spectacular views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
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
    
    # ✅ API Documentation endpoints
    # OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI (Interactive documentation)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ReDoc UI (Alternative documentation)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)