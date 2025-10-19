# 🏥 Hospital Management System - Development Rules & Guidelines

## 📁 Project Structure

```
hospital_management/
├── venv/                          # Virtual environment
├── hms/                           # Main project folder
│   ├── __init__.py
│   ├── settings.py               # Project settings
│   ├── urls.py                   # Main URL configuration
│   ├── asgi.py
│   └── wsgi.py
├── apps/                          # All Django apps
│   ├── __init__.py
│   ├── accounts/                 # ✅ User management & auth
│   │   ├── migrations/
│   │   ├── management/
│   │   │   └── commands/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   ├── admin.py
│   │   └── apps.py
│   ├── doctors/                  # 🔜 Doctor profiles & availability
│   ├── patients/                 # 🔜 Patient records & vitals
│   ├── appointments/             # 🔜 Appointment scheduling
│   ├── prescriptions/            # 🔜 Prescriptions
│   ├── pharmacy/                 # 🔜 Pharmacy & inventory
│   ├── laboratory/               # 🔜 Lab tests & results
│   ├── billing/                  # 🔜 Billing & payments
│   └── medical_records/          # 🔜 Medical records
├── media/                         # User uploaded files
│   ├── profiles/                 # Profile pictures
│   ├── doctors/                  # Doctor-related files
│   │   └── signatures/
│   ├── prescriptions/            # Prescription documents
│   └── lab_reports/              # Lab report files
├── staticfiles/                   # Collected static files
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
├── .gitignore                    # Git ignore rules
├── rules.md                      # This file
├── test_api.py                   # API testing script
└── manage.py                     # Django management script
```

---

## 🎯 Core Architecture Principles

### 1. Authentication & Authorization
- ✅ **USE** Django's built-in User model by extending `AbstractUser`
- ✅ **USE** Django Groups for role-based access control (RBAC)
- ✅ **USE** Django's native permissions system
- ✅ **USE** DRF Token Authentication (`rest_framework.authtoken`)
- ❌ **DO NOT** create custom permission tables
- ❌ **DO NOT** add `role` field to User model (use Group membership)

### 2. User & Profile Architecture
```
Central User Model (AbstractUser)
    ↓
Role determined by Django Group membership
    ↓
Profile Models (OneToOneField to User):
    - DoctorProfile
    - PatientProfile
    - PharmacistProfile
    - NurseProfile
    - ReceptionistProfile
    - LabTechnicianProfile
```

### 3. Django Groups (Roles)
```
- Administrator       → Full access
- Doctor              → Patient, Appointment, Prescription management
- Nurse               → Patient vitals, limited patient info
- Receptionist        → Patient registration, Appointments, Billing
- Pharmacist          → Prescriptions, Medications, Inventory
- Lab Technician      → Lab tests, Results
- Patient             → Own records only (read-only)
```

---

## 📋 Model Development Rules

### File Upload Fields
- ✅ **USE** `ImageField` for images (profile pictures, signatures, scans)
- ✅ **USE** `FileField` for documents (PDFs, reports)
- ✅ **ALWAYS** specify `upload_to` parameter
- ✅ **ALWAYS** add `blank=True, null=True` for optional uploads
- ❌ **DO NOT** use `CharField` for storing file paths

**Example:**
```python
# ✅ CORRECT
profile_picture = models.ImageField(
    upload_to='profiles/',
    blank=True,
    null=True
)

signature = models.ImageField(
    upload_to='doctors/signatures/',
    blank=True,
    null=True
)

# ❌ WRONG
profile_picture = models.CharField(max_length=500)
```

### Required Model Components

Every model MUST have:
```python
class YourModel(models.Model):
    # Fields...
    
    # ✅ REQUIRED: Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ✅ REQUIRED: Meta class
    class Meta:
        db_table = 'your_table_name'
        verbose_name = 'Your Model'
        verbose_name_plural = 'Your Models'
        ordering = ['-created_at']  # or appropriate field
    
    # ✅ REQUIRED: __str__ method
    def __str__(self):
        return f"{self.name}"  # or appropriate representation
```

### Foreign Key & OneToOne Relationships
```python
# ✅ User relationships (can be null if user is deleted)
user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,  # or SET_NULL
    related_name='doctor_profile'
)

# ✅ Other relationships
doctor = models.ForeignKey(
    DoctorProfile,
    on_delete=models.CASCADE,
    related_name='appointments'
)

# ✅ ALWAYS use settings.AUTH_USER_MODEL
from django.conf import settings
# NOT: from apps.accounts.models import User

# ✅ ALWAYS use related_name
# ✅ ALWAYS use on_delete parameter
```

### Indexing
```python
class Meta:
    indexes = [
        models.Index(fields=['patient_id']),
        models.Index(fields=['created_at']),
        models.Index(fields=['last_name', 'first_name']),
    ]
```

---

## 🔐 Permissions & Access Control

### Permission Classes Pattern
use inbuilt django  auth groups for permissions handling
### Check Group Membership
```python
# ✅ CORRECT
if request.user.groups.filter(name='Doctor').exists():
    # Do something

# ✅ Check multiple groups
user_groups = request.user.groups.values_list('name', flat=True)
if 'Doctor' in user_groups or 'Administrator' in user_groups:
    # Do something
```

---

## 📡 API Response Format

### ✅ ALWAYS use consistent response format:

**Success Response:**
```python
return Response({
    'success': True,
    'data': {...}
}, status=status.HTTP_200_OK)
```

**Error Response:**
```python
return Response({
    'success': False,
    'error': 'Error message here'
}, status=status.HTTP_400_BAD_REQUEST)
```

**List Response (with pagination):**
```python
def list(self, request, *args, **kwargs):
    queryset = self.filter_queryset(self.get_queryset())
    page = self.paginate_queryset(queryset)
    
    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    serializer = self.get_serializer(queryset, many=True)
    return Response({
        'success': True,
        'data': serializer.data
    })
```

---

## 🎨 Serializer Patterns

### List vs Detail Serializers
```python
# ✅ Use different serializers for list and detail views
class YourViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return YourModelListSerializer  # Minimal fields
        elif self.action in ['create', 'update', 'partial_update']:
            return YourModelCreateUpdateSerializer
        return YourModelDetailSerializer  # Full fields
```

### Create/Update Patterns
```python
class ModelCreateUpdateSerializer(serializers.ModelSerializer):
    # ✅ Use write_only for IDs
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = YourModel
        exclude = ['created_at', 'updated_at']
    
    def validate_user_id(self, value):
        # Validation logic
        return value
    
    def create(self, validated_data):
        # Custom creation logic
        user_id = validated_data.pop('user_id')
        # ...
        return instance
```

### Read-Only Fields
```python
class YourSerializer(serializers.ModelSerializer):
    # ✅ Computed/property fields are read_only
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    
    class Meta:
        read_only_fields = ['id', 'created_at', 'updated_at']
```

---

## 🎯 ViewSet Patterns

### Query Optimization
```python
# ✅ ALWAYS use select_related and prefetch_related
queryset = Model.objects.select_related(
    'foreign_key_field'
).prefetch_related(
    'many_to_many_field'
)
```

### Filtering & Search
```python
class YourViewSet(viewsets.ModelViewSet):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['status', 'city']
    search_fields = ['name', 'email']
    ordering_fields = ['created_at', 'name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Custom filters
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
        
        return queryset
```

### Custom Actions
```python
@action(detail=True, methods=['post'])
def custom_action(self, request, pk=None):
    """Custom action description"""
    instance = self.get_object()
    
    # Business logic
    
    return Response({
        'success': True,
        'message': 'Action completed'
    })

@action(detail=False, methods=['get'])
def statistics(self, request):
    """Get statistics"""
    return Response({
        'success': True,
        'data': {...}
    })
```

---

## 🔗 URL Patterns

### URL Structure
```python
# app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'resource', ResourceViewSet, basename='resource')

urlpatterns = [
    # Standalone views
    path('action/', ActionView.as_view(), name='action'),
    
    # ViewSet routes
    path('', include(router.urls)),
]
```

### Main URLs
```python
# hms/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.accounts.urls')),
    path('api/doctors/', include('apps.doctors.urls')),
    path('api/patients/', include('apps.patients.urls')),
    # ...
]
```

---

## 🔨 Admin Configuration

### Always Register Models
```python
from django.contrib import admin
from .models import YourModel

@admin.register(YourModel)
class YourModelAdmin(admin.ModelAdmin):
    list_display = ['field1', 'field2', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('field1', 'field2')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
```

---

## 🗄️ Database Best Practices

### Unique Fields
```python
# ✅ Use unique=True for identifiers
patient_id = models.CharField(max_length=20, unique=True)
email = models.EmailField(unique=True)
license_number = models.CharField(max_length=50, unique=True)
```

### Choices
```python
# ✅ Define choices as constants
class YourModel(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
```

### Soft Deletes
```python
# ✅ Use status field instead of hard delete
status = models.CharField(
    max_length=20,
    choices=[
        ('active', 'Active'),
        ('deleted', 'Deleted'),
    ],
    default='active'
)

# Filter active records
queryset = Model.objects.filter(status='active')
```

---

## 🧪 Testing Guidelines

### API Testing Pattern
```python
# Use test_api.py pattern
import requests

BASE_URL = 'http://127.0.0.1:8000/api'

def test_endpoint(token):
    url = f'{BASE_URL}/endpoint/'
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(url, headers=headers)
    return response.json()
```

---

## ⚙️ Settings Configuration

### Environment Variables
```python
# .env file
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:password@localhost:5432/db_name
```

### Load in settings.py
```python
from decouple import config, Csv

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
```

---

## 📝 Naming Conventions

### Models
- Use singular names: `Patient`, `Doctor`, `Appointment`
- Use PascalCase: `PatientProfile`, `DoctorAvailability`

### Variables & Functions
- Use snake_case: `patient_id`, `get_user_role`
- Be descriptive: `calculate_total_amount` not `calc_tot`

### URLs
- Use kebab-case: `/change-password/`, `/doctor-availability/`
- Use plural for resources: `/patients/`, `/appointments/`

### Fields
- Use snake_case: `first_name`, `created_at`
- Boolean fields: start with `is_` or `has_`: `is_active`, `has_insurance`

---

## 🚫 Common Mistakes to Avoid

### ❌ DO NOT
1. Add `role` field to User model (use Groups)
2. Use `CharField` for file uploads (use `ImageField`/`FileField`)
3. Forget `on_delete` in ForeignKey/OneToOne
4. Forget `related_name` in relationships
5. Hard-code user roles in logic (use Groups)
6. Return inconsistent API response formats
7. Skip timestamps (`created_at`, `updated_at`)
8. Skip `__str__` method in models
9. Import User model directly (use `settings.AUTH_USER_MODEL`)
10. Create migrations without checking database state

### ✅ ALWAYS DO
1. Use Groups for role management
2. Use `ImageField` with Pillow for images
3. Include timestamps in all models
4. Optimize queries with `select_related`/`prefetch_related`
5. Use consistent API response format
6. Add proper docstrings
7. Create migrations before running migrate
8. Test APIs after implementation
9. Use transaction.atomic for critical operations
10. Validate data in serializers

---

## 🔄 Development Workflow

### Creating New App
```bash
# 1. Create app
python manage.py startapp appname apps/appname

# 2. Create __init__.py
echo. > apps/__init__.py

# 3. Update apps.py
class AppnameConfig(AppConfig):
    name = 'apps.appname'

# 4. Add to INSTALLED_APPS in settings.py
'apps.appname.apps.AppnameConfig',

# 5. Create migrations folder
mkdir apps/appname/migrations
echo. > apps/appname/migrations/__init__.py

# 6. Develop models, serializers, views, urls

# 7. Make migrations
python manage.py makemigrations appname

# 8. Migrate
python manage.py migrate appname
python manage.py migrate

# 9. Register in admin
# Update apps/appname/admin.py

# 10. Test
python test_api.py
```

---

## 📦 Dependencies

### Current Stack
```
Django==4.2.7
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-filter==23.5
python-decouple==3.8
dj-database-url==2.1.0
psycopg2-binary==2.9.9
Pillow==10.1.0              # ✅ For ImageField support
whitenoise==6.6.0
```

### When to Add New Packages
- ✅ Add if it solves a specific problem
- ✅ Check Django compatibility
- ✅ Update requirements.txt
- ❌ Don't add unnecessary packages

---

## 🎯 Project Goals & Priorities

### Priority Order
1. **Authentication & User Management** ✅ Complete
2. **Doctor Management** 🔜 Next
3. **Patient Management** 🔜
4. **Appointment System** 🔜
5. **Prescriptions** 🔜
6. **Pharmacy & Inventory** 🔜
7. **Laboratory** 🔜
8. **Billing & Payments** 🔜
9. **Medical Records** 🔜

### Feature Checklist (Per App)
- [ ] Models defined with all fields
- [ ] Migrations created and applied
- [ ] Serializers (List, Detail, Create/Update)
- [ ] ViewSets with proper permissions
- [ ] URLs configured
- [ ] Admin registration
- [ ] API endpoints tested
- [ ] Documentation updated

---

## 📚 Additional Resources

### Django Docs
- Models: https://docs.djangoproject.com/en/4.2/topics/db/models/
- DRF: https://www.django-rest-framework.org/

### Project Docs
- README.md - Project overview & setup
- rules.md - This file
- API_DOCS.md - API documentation (to be created)

---

## 🎨 Code Style

### Imports Order
```python
# 1. Standard library
import os
import datetime

# 2. Django
from django.db import models
from django.contrib.auth import get_user_model

# 3. Third party
from rest_framework import serializers

# 4. Local
from .models import YourModel
from apps.accounts.permissions import IsAdmin
```

### Comments
```python
# ✅ Use docstrings for classes and functions
def function_name(param):
    """
    Brief description.
    
    Args:
        param: Description
    
    Returns:
        Description
    """
    pass

# ✅ Use inline comments for complex logic
# Calculate BMI using metric system
bmi = weight / (height ** 2)
```

---

## 🔍 Debug Mode

### Development
```python
DEBUG = True  # Show detailed errors
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
```

### Production
```python
DEBUG = False  # Hide errors
ALLOWED_HOSTS = ['yourdomain.com']
SECURE_SSL_REDIRECT = True
```

---

## 🎉 Summary

This rules.md file is your development bible. Follow these guidelines strictly to ensure:
- ✅ Consistent code quality
- ✅ Maintainable codebase
- ✅ Scalable architecture
- ✅ Security best practices
- ✅ Team collaboration

**When in doubt, refer back to this file!**

---

*Last Updated: October 13, 2025*
*Project: Hospital Management System*
*Stack: Django 4.2.7 + DRF + PostgreSQL*