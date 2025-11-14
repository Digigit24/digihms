# HMS SuperAdmin JWT Authentication System

## Overview

This document describes the implementation of SuperAdmin JWT authentication for the Hospital Management System (HMS) Django application. The HMS uses a **separate database per tenant** strategy, where each hospital gets its own Neon database for complete data isolation.

## Architecture

### Key Components

1. **JWT Validation Middleware** ([`common/middleware.py`](common/middleware.py))
2. **Database Router** ([`common/database_router.py`](common/database_router.py))
3. **Permission Helpers** ([`common/permissions.py`](common/permissions.py))
4. **Multi-tenant Models** (All HMS models with `tenant_id`)

### Database Strategy

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SuperAdmin    │    │  HMS Metadata   │    │ Tenant Database │
│   (CRM System)  │    │   (default)     │    │ (city-hospital) │
│                 │    │                 │    │                 │
│ • User Auth     │───▶│ • Migrations    │    │ • Patients      │
│ • JWT Creation  │    │ • Admin Data    │    │ • Appointments  │
│ • Tenant Mgmt   │    │ • User Accounts │    │ • Doctors       │
└─────────────────┘    └─────────────────┘    │ • All HMS Data  │
                                              └─────────────────┘
```

## JWT Structure

The SuperAdmin system provides JWTs with the following structure:

```json
{
  "user_id": "uuid",
  "email": "doctor@hospital.com",
  "tenant_id": "city-hospital-123",
  "tenant_slug": "city-hospital",
  "is_super_admin": false,
  "permissions": {
    "hms.patients.view": "all",
    "hms.patients.create": true,
    "hms.appointments.view": "own"
  },
  "enabled_modules": ["hms"],
  "database_url": "postgresql://...city_hospital_db"
}
```

## Implementation Details

### 1. JWT Validation Middleware

**File**: [`common/middleware.py`](common/middleware.py)

**Features**:
- Validates JWT from `Authorization: Bearer <token>` header
- Uses same `JWT_SECRET_KEY` as SuperAdmin
- Extracts user info, tenant info, and permissions
- Checks if "hms" module is enabled
- Sets up tenant-specific database connection
- Stores tenant info in thread-local storage

**Request Attributes Set**:
- `request.user_id` - User UUID from JWT
- `request.email` - User email
- `request.tenant_id` - Tenant identifier
- `request.tenant_slug` - Human-readable tenant slug
- `request.is_super_admin` - Admin flag
- `request.permissions` - Permission dictionary
- `request.database_url` - Optional tenant database URL

### 2. Database Router

**File**: [`common/database_router.py`](common/database_router.py)

**Features**:
- Routes HMS models to tenant-specific databases
- Routes auth/admin models to default database
- Handles database connections dynamically
- Supports database URL parsing from JWT
- Manages migration routing

**Database Naming**:
- Default database: `hms_metadata_db` (migrations, admin)
- Tenant databases: `tenant_{tenant_id}` (e.g., `tenant_city-hospital-123`)

### 3. Permission System

**File**: [`common/permissions.py`](common/permissions.py)

**Permission Keys**:
```python
# Patient permissions
hms.patients.view     # Scope: all/team/own/none
hms.patients.create   # Boolean: true/false
hms.patients.edit     # Boolean: true/false
hms.patients.delete   # Boolean: true/false

# Appointment permissions
hms.appointments.view
hms.appointments.create
hms.appointments.edit
hms.appointments.delete

# Other modules...
hms.prescriptions.*
hms.billing.*
hms.opd.*
hms.pharmacy.*
```

**Permission Scopes**:
- `"all"` - Access to all records
- `"team"` - Access to team records (future implementation)
- `"own"` - Access to own records only
- `"none"` - No access
- `true/false` - Boolean permissions for create/edit/delete

### 4. Model Updates

All HMS models now include:

```python
# Tenant Information
tenant_id = models.UUIDField(
    db_index=True,
    help_text="Tenant identifier for multi-tenancy"
)
```

**Purpose of tenant_id**:
- Safety verification (ensure data is in correct database)
- Audit trail and logging
- Analytics across tenants
- Future-proofing for data migration
- **NOT for filtering** (database isolation handles that)

## Usage Examples

### 1. Using PermissionMixin in ViewSets

```python
from common.permissions import PermissionMixin, HMSPermissions

class PatientViewSet(PermissionMixin, viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    
    # Define permissions for each action
    permission_mapping = {
        'list': HMSPermissions.PATIENTS_VIEW,
        'retrieve': HMSPermissions.PATIENTS_VIEW,
        'create': HMSPermissions.PATIENTS_CREATE,
        'update': HMSPermissions.PATIENTS_EDIT,
        'destroy': HMSPermissions.PATIENTS_DELETE,
    }
    
    # Field containing owner ID for permission checks
    owner_field = 'created_by_id'
    
    # PermissionMixin automatically handles:
    # - Permission checking
    # - Queryset filtering based on scope
    # - Setting tenant_id and owner fields on create
```

### 2. Function-based View with Permissions

```python
from common.permissions import permission_required, HMSPermissions

@permission_required(HMSPermissions.PATIENTS_VIEW)
def patient_list(request):
    # Automatically routed to tenant database
    patients = PatientProfile.objects.all()
    return JsonResponse({'patients': list(patients.values())})

@permission_required(HMSPermissions.PATIENTS_EDIT, resource_owner_field='patient_id')
def update_patient(request, patient_id):
    # Checks if user can edit this specific patient
    patient = PatientProfile.objects.get(id=patient_id)
    # Update logic...
    return JsonResponse({'success': True})
```

### 3. Manual Permission Checking

```python
from common.permissions import check_permission, HMSPermissions

def my_view(request):
    # Check basic permission
    if not check_permission(request, HMSPermissions.PATIENTS_VIEW):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Check permission with resource ownership
    patient = PatientProfile.objects.get(id=patient_id)
    if not check_permission(request, HMSPermissions.PATIENTS_EDIT, patient.created_by_id):
        return JsonResponse({'error': 'Cannot edit this patient'}, status=403)
    
    # Proceed with logic...
```

## Configuration

### Environment Variables

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT Configuration (MUST MATCH SuperAdmin!)
JWT_SECRET_KEY=same-as-superadmin-secret-key-here
JWT_ALGORITHM=HS256

# Database Configuration (Metadata Database Only)
DB_NAME=hms_metadata_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Settings Updates

```python
# JWT Configuration
JWT_SECRET_KEY = config('JWT_SECRET_KEY')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')

# Middleware (JWT before Django Auth)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'common.middleware.JWTAuthenticationMiddleware',  # JWT Auth
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Database Router
DATABASE_ROUTERS = ['common.database_router.HMSDatabaseRouter']

# Add common app
INSTALLED_APPS = [
    # ... other apps ...
    'common',  # For migrations
    # ... HMS apps ...
]
```

## Migration Strategy

### For New HMS Installation

1. Run initial migrations on metadata database:
```bash
python manage.py migrate
```

2. Tenant databases are created automatically when users access the system with valid JWTs.

### For Existing HMS with Data

1. Add tenant_id fields (nullable initially):
```bash
python manage.py migrate
```

2. Set tenant_id for existing records:
```python
# Custom data migration script
from apps.patients.models import PatientProfile
import uuid

# Set a default tenant_id for existing records
default_tenant_id = uuid.uuid4()
PatientProfile.objects.filter(tenant_id__isnull=True).update(tenant_id=default_tenant_id)
```

3. Make tenant_id non-nullable in a follow-up migration.

## Example Flow

### 1. Doctor Login → SuperAdmin
```
Doctor logs in to SuperAdmin system
↓
SuperAdmin validates credentials
↓
SuperAdmin generates JWT with:
- tenant_id: "city-hospital-123"
- permissions: {"hms.patients.view": "all", ...}
- database_url: "postgresql://...city_hospital_db"
```

### 2. Doctor Requests Patients → HMS
```
GET /api/patients/
Authorization: Bearer <jwt_token>
```

### 3. HMS Processing
```
JWT Middleware:
├─ Validates JWT signature
├─ Extracts tenant_id: "city-hospital-123"
├─ Sets up database connection: tenant_city-hospital-123
├─ Stores tenant info in thread-local
└─ Sets request attributes

Database Router:
├─ Routes PatientProfile queries to tenant database
└─ Ensures complete isolation

ViewSet:
├─ Checks permission: "hms.patients.view"
├─ Applies scope filtering (all/team/own)
├─ Queries: PatientProfile.objects.all()
└─ Returns City Hospital patients only
```

## Security Features

### Complete Tenant Isolation
- **Database Level**: Each tenant has separate database
- **No Cross-Tenant Queries**: Impossible by design
- **Automatic Routing**: No manual database selection needed

### Permission Enforcement
- **JWT-based**: No database lookups for permissions
- **Granular Control**: Per-module, per-action permissions
- **Scope-based**: all/team/own access levels
- **Resource-level**: Check ownership for specific records

### Safety Measures
- **tenant_id Verification**: Ensures data is in correct database
- **Audit Trail**: Track all operations with tenant context
- **Error Handling**: Graceful handling of invalid JWTs
- **Logging**: Comprehensive logging for debugging

## API Examples

### Patient Management

```bash
# List all patients (requires hms.patients.view)
curl -H "Authorization: Bearer <jwt>" \
     http://localhost:8002/api/patients/

# Create patient (requires hms.patients.create)
curl -X POST \
     -H "Authorization: Bearer <jwt>" \
     -H "Content-Type: application/json" \
     -d '{"first_name": "John", "last_name": "Doe", ...}' \
     http://localhost:8002/api/patients/

# Get patient statistics (requires hms.patients.view with "all" scope)
curl -H "Authorization: Bearer <jwt>" \
     http://localhost:8002/api/patients/statistics/
```

### Appointment Management

```bash
# List appointments (filtered by permission scope)
curl -H "Authorization: Bearer <jwt>" \
     http://localhost:8002/api/appointments/

# Schedule appointment (requires hms.appointments.create)
curl -X POST \
     -H "Authorization: Bearer <jwt>" \
     -H "Content-Type: application/json" \
     -d '{"patient_id": 1, "doctor_id": 2, ...}' \
     http://localhost:8002/api/appointments/
```

## Deployment

### Running HMS Alongside CRM

```bash
# CRM runs on port 8001
python manage.py runserver 8001

# HMS runs on port 8002
python manage.py runserver 8002
```

### Database Setup

1. **Metadata Database**: Create `hms_metadata_db`
2. **Tenant Databases**: Created automatically via middleware
3. **Migrations**: Run on metadata DB, tenant DBs handled automatically

## Troubleshooting

### Common Issues

1. **JWT Validation Fails**
   - Check `JWT_SECRET_KEY` matches SuperAdmin
   - Verify JWT format and expiration
   - Check middleware order in settings

2. **Database Routing Issues**
   - Verify database router is configured
   - Check tenant database connection setup
   - Review middleware thread-local storage

3. **Permission Denied**
   - Verify JWT contains required permissions
   - Check permission key spelling
   - Validate scope requirements (all/own)

### Debug Commands

```bash
# Check middleware configuration
python manage.py shell
>>> from django.conf import settings
>>> print(settings.MIDDLEWARE)

# Test database routing
>>> from common.database_router import HMSDatabaseRouter
>>> router = HMSDatabaseRouter()
>>> from apps.patients.models import PatientProfile
>>> print(router.db_for_read(PatientProfile))

# Check JWT decoding
>>> import jwt
>>> from django.conf import settings
>>> token = "your-jwt-token"
>>> payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
>>> print(payload)
```

## Testing

### Manual Testing

1. **Get JWT from SuperAdmin**:
   ```bash
   # Login to SuperAdmin and get JWT token
   curl -X POST http://localhost:8001/api/auth/login/ \
        -d '{"email": "doctor@hospital.com", "password": "password"}'
   ```

2. **Test HMS Endpoints**:
   ```bash
   # Use JWT to access HMS
   curl -H "Authorization: Bearer <jwt>" \
        http://localhost:8002/api/patients/
   ```

### Unit Testing

```python
# Test JWT middleware
from django.test import TestCase, RequestFactory
from common.middleware import JWTAuthenticationMiddleware
import jwt

class JWTMiddlewareTest(TestCase):
    def test_valid_jwt(self):
        # Create test JWT
        payload = {
            'user_id': 'test-uuid',
            'email': 'test@hospital.com',
            'tenant_id': 'test-hospital',
            'enabled_modules': ['hms'],
            'permissions': {'hms.patients.view': 'all'}
        }
        token = jwt.encode(payload, 'test-secret', algorithm='HS256')
        
        # Test middleware
        factory = RequestFactory()
        request = factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        
        middleware = JWTAuthenticationMiddleware()
        response = middleware.process_request(request)
        
        self.assertIsNone(response)  # No error response
        self.assertEqual(request.tenant_id, 'test-hospital')
```

## Performance Considerations

### Database Connections
- **Connection Pooling**: Each tenant database uses connection pooling
- **Lazy Loading**: Tenant databases added only when needed
- **Caching**: Database configurations cached in Django connections

### Query Optimization
- **Automatic Routing**: No manual database selection overhead
- **Indexed Fields**: tenant_id fields are indexed for safety queries
- **Efficient Filtering**: Permission-based filtering at database level

## Security Considerations

### JWT Security
- **Shared Secret**: Must match SuperAdmin exactly
- **Token Expiration**: Handled by SuperAdmin
- **Algorithm**: HS256 (configurable)

### Database Security
- **Complete Isolation**: No cross-tenant data access possible
- **Connection Security**: Standard PostgreSQL security
- **Audit Trail**: All operations logged with tenant context

## Monitoring and Logging

### Log Levels
- **INFO**: Successful JWT validations, database setups
- **WARNING**: Permission denials, missing permissions
- **ERROR**: JWT validation failures, database connection issues

### Metrics to Monitor
- JWT validation success/failure rates
- Database connection pool usage
- Permission denial patterns
- Cross-tenant access attempts (should be zero)

## Future Enhancements

### Planned Features
1. **Team-based Permissions**: Implement team scope filtering
2. **Dynamic Permission Updates**: Real-time permission changes
3. **Database Health Monitoring**: Monitor tenant database status
4. **Automated Backup**: Per-tenant backup strategies

### Scalability
- **Database Sharding**: Support for multiple database servers
- **Caching Layer**: Redis for permission and tenant info caching
- **Load Balancing**: Multiple HMS instances with shared tenant routing

## Conclusion

This implementation provides:
- ✅ Complete tenant isolation at database level
- ✅ JWT-based authentication matching SuperAdmin
- ✅ Granular permission system
- ✅ Automatic database routing
- ✅ Safety measures with tenant_id verification
- ✅ Scalable architecture for multiple hospitals

The system ensures that each hospital's data is completely isolated while providing a unified authentication and permission system through the SuperAdmin JWT tokens.