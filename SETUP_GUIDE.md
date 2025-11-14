# HMS SuperAdmin JWT Authentication - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy and configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Django Settings
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT Configuration (MUST MATCH SuperAdmin!)
JWT_SECRET_KEY=same-as-superadmin-secret-key
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

### 3. Database Setup

Create the metadata database:

```sql
-- Connect to PostgreSQL
CREATE DATABASE hms_metadata_db;
```

Run migrations:

```bash
python manage.py migrate
```

### 4. Test JWT Authentication

Generate a test JWT token:

```bash
python manage.py setup_tenant --test-jwt
```

This will output a test token you can use for API testing.

### 5. Start HMS Server

```bash
python manage.py runserver 8002
```

HMS will run on port 8002 (different from CRM on 8001).

## Testing the Implementation

### 1. Test JWT Validation

```bash
# Get test token
python manage.py setup_tenant --test-jwt

# Use token to test API
curl -H "Authorization: Bearer <token>" \
     http://localhost:8002/api/patients/
```

### 2. Test Permission System

```bash
# Test with different permission scopes
# Doctor with 'all' scope - should see all patients
curl -H "Authorization: Bearer <doctor_token>" \
     http://localhost:8002/api/patients/

# Receptionist with 'own' scope - should see only own patients
curl -H "Authorization: Bearer <receptionist_token>" \
     http://localhost:8002/api/patients/
```

### 3. Test Database Isolation

```bash
# List configured tenant databases
python manage.py setup_tenant --list-tenants

# Set up a specific tenant database
python manage.py setup_tenant --tenant-id city-hospital-123
```

## Integration with SuperAdmin

### 1. SuperAdmin Configuration

Ensure SuperAdmin is configured with:

```env
# SuperAdmin .env
JWT_SECRET_KEY=same-secret-as-hms
JWT_ALGORITHM=HS256
```

### 2. JWT Generation in SuperAdmin

SuperAdmin should generate JWTs with this structure:

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

### 3. Frontend Integration

Frontend should:

1. Login via SuperAdmin
2. Receive JWT token
3. Use JWT for all HMS API calls
4. Handle token expiration

```javascript
// Example frontend code
const token = localStorage.getItem('jwt_token');

fetch('http://localhost:8002/api/patients/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

## Updating Existing ViewSets

### 1. Add Permission Mapping

```python
from common.permissions import PermissionMixin, HMSPermissions

class YourViewSet(PermissionMixin, viewsets.ModelViewSet):
    permission_mapping = {
        'list': HMSPermissions.PATIENTS_VIEW,
        'create': HMSPermissions.PATIENTS_CREATE,
        'update': HMSPermissions.PATIENTS_EDIT,
        'destroy': HMSPermissions.PATIENTS_DELETE,
    }
    owner_field = 'created_by_id'  # or 'doctor_id', etc.
```

### 2. Remove Old Permission Classes

```python
# OLD
permission_classes = [IsAuthenticated, ActionPermissions]

# NEW (PermissionMixin handles this automatically)
# No permission_classes needed
```

### 3. Update Create Methods

```python
# OLD
def perform_create(self, serializer):
    serializer.save(created_by=self.request.user)

# NEW (PermissionMixin handles this automatically)
def perform_create(self, serializer):
    super().perform_create(serializer)  # Auto-sets tenant_id and owner
```

## Production Deployment

### 1. Security Checklist

- [ ] JWT_SECRET_KEY is secure and matches SuperAdmin
- [ ] DEBUG=False in production
- [ ] ALLOWED_HOSTS configured properly
- [ ] Database credentials secured
- [ ] CORS origins restricted to frontend domains
- [ ] HTTPS enabled for all communications

### 2. Database Setup

```bash
# Create metadata database
createdb hms_metadata_db

# Run migrations
python manage.py migrate

# Tenant databases will be created automatically
```

### 3. Monitoring

Monitor these metrics:
- JWT validation success/failure rates
- Database connection pool usage
- Permission denial patterns
- Response times per tenant

## Troubleshooting

### Common Issues

1. **"Missing JWT_SECRET_KEY"**
   - Add JWT_SECRET_KEY to .env file
   - Ensure it matches SuperAdmin exactly

2. **"HMS module not enabled"**
   - Check JWT payload contains `"enabled_modules": ["hms"]`
   - Verify SuperAdmin is generating correct JWT

3. **"Permission denied"**
   - Check JWT contains required permission keys
   - Verify permission values (true/false for actions, all/own for views)
   - Check resource ownership for 'own' scope permissions

4. **"Database routing issues"**
   - Verify DATABASE_ROUTERS in settings.py
   - Check middleware order (JWT before Django Auth)
   - Ensure tenant database exists and is accessible

### Debug Commands

```bash
# Test JWT generation
python manage.py setup_tenant --test-jwt

# List tenant databases
python manage.py setup_tenant --list-tenants

# Check middleware configuration
python manage.py shell
>>> from django.conf import settings
>>> print(settings.MIDDLEWARE)

# Test database routing
>>> from common.database_router import HMSDatabaseRouter
>>> router = HMSDatabaseRouter()
>>> from apps.patients.models import PatientProfile
>>> print(router.db_for_read(PatientProfile))
```

## Success Criteria Verification

✅ **Doctor logs in → SuperAdmin → Gets JWT**
- SuperAdmin generates JWT with tenant and permission info

✅ **JWT includes tenant_id and database info**
- JWT contains tenant_id, permissions, and optional database_url

✅ **HMS validates JWT locally**
- Middleware validates JWT signature and extracts data

✅ **Middleware routes to correct tenant database**
- Database router automatically routes HMS models to tenant DB

✅ **Queries automatically go to tenant DB**
- All HMS model queries use tenant-specific database

✅ **Complete isolation per hospital**
- Each hospital has separate database, no cross-tenant access

✅ **Permissions enforced correctly**
- Permission system enforces granular access control

✅ **Can run on different port (8002) alongside CRM**
- HMS runs independently on port 8002

The implementation is now complete and ready for production use!