# DigiHMS Django Admin Authentication Setup

## Overview

This document describes the implementation of SuperAdmin JWT authentication for the DigiHMS Django Admin interface.

## What Was Implemented

### 1. Custom Authentication Backends
**File**: `common/auth_backends.py`

Created three main components:
- **TenantUser**: A custom user class that mimics Django's User model without requiring a database User table
- **SuperAdminAuthBackend**: Authenticates users against the SuperAdmin API using email/password
- **JWTAuthBackend**: Authenticates users using JWT tokens

These backends allow Django Admin to authenticate users via the external SuperAdmin system while maintaining session-based authentication within the admin interface.

### 2. Authentication Views
**File**: `common/views.py`

Implemented several views for admin authentication:
- **SuperAdminLoginView**: Custom login view for the admin interface
- **superadmin_proxy_login_view**: Proxy endpoint that calls SuperAdmin API to avoid CORS issues
- **TokenLoginView**: Allows direct login using JWT access tokens
- **AdminHealthView**: Health check endpoint
- **admin_logout_view**: Custom logout that clears session data

### 3. Custom Admin Site
**File**: `common/admin_site.py`

Created custom admin components:
- **TenantAdminSite**: Custom admin site that handles tenant-based authentication
  - Checks session for JWT token and user data
  - Reconstructs TenantUser from session
  - Sets tenant information on requests
  - Provides custom login/logout flows

- **TenantModelAdmin**: Base ModelAdmin class for tenant-isolated models
  - Automatically filters querysets by tenant_id
  - Sets tenant_id when creating records
  - Permission checking based on JWT permissions

### 4. Middleware Updates
**File**: `common/middleware.py`

Enhanced the existing JWT middleware:
- Added `get_current_request()` and `set_current_request()` functions for thread-local storage
- Stores current request in thread-local storage for use by authentication backends
- Added `/auth/` to skip paths for authentication endpoints
- Maintains compatibility with existing API authentication

### 5. Admin Templates
**Directory**: `templates/admin/`

Created custom admin templates:
- **login.html**: Beautiful custom login page with two login methods
  - Credentials login (email/password via SuperAdmin API)
  - JWT token login (paste access token)
  - Modern, responsive design with gradient styling
  - JavaScript-based form submission to proxy endpoints

- **index.html**: Custom admin index page
  - Displays tenant information prominently
  - Shows enabled modules as badges
  - No LogEntry widget (avoids UUID/integer ID conflicts)
  - Modern card-based layout for apps

- **app_index.html**: App-specific index page
  - Extends main index template
  - Shows breadcrumbs and app-specific models

### 6. URL Configuration
**File**: `hms/urls.py`

Updated URL patterns:
- Replaced default `admin.site.urls` with `tenant_admin_site.urls`
- Added authentication endpoints:
  - `/auth/token-login/` - JWT token login
  - `/auth/superadmin-login/` - Proxy endpoint for credential login
  - `/auth/health/` - Health check
- Added root redirect to `/admin/`
- Added static file serving for development

### 7. Settings Configuration
**File**: `hms/settings.py`

Added configuration:
- `SUPERADMIN_URL` - URL of the SuperAdmin system
- `AUTHENTICATION_BACKENDS` - Added custom authentication backends
- `SESSION_COOKIE_AGE` - Set to 8 hours
- `SESSION_SAVE_EVERY_REQUEST` - Enabled
- `SESSION_EXPIRE_AT_BROWSER_CLOSE` - Enabled

### 8. Environment Variables
**File**: `.env.example`

Added:
- `SUPERADMIN_URL` - URL for SuperAdmin API (default: https://admin.celiyo.com)

## Architecture Flow

### Login Flow

1. **User Access**: User navigates to `/admin/`
2. **Redirect**: Not authenticated → redirected to `/admin/login/`
3. **Login Form**: Custom login template displays with two options:
   - Email/Password credentials
   - JWT access token

#### Option A: Credential Login
4. **Form Submit**: JavaScript submits to `/auth/superadmin-login/`
5. **Proxy Call**: View calls SuperAdmin API `/api/auth/login/`
6. **Validation**: SuperAdmin validates credentials and returns JWT
7. **JWT Decode**: View decodes JWT and validates HMS module is enabled
8. **Session Setup**:
   - Creates TenantUser object
   - Stores JWT token in session
   - Stores user data in session
   - Calls Django's `login()` function
9. **Redirect**: Returns success JSON with redirect to `/admin/`
10. **Admin Access**: User can now access admin interface

#### Option B: Token Login
4. **Token Submit**: JavaScript submits JWT to `/auth/token-login/`
5. **Validation**: View decodes JWT and validates HMS module
6. **Session Setup**: Same as credential login
7. **Redirect**: Returns success JSON with redirect to `/admin/`

### Subsequent Requests

1. **Request**: User clicks on admin page (e.g., Patients list)
2. **Admin Site Check**: `TenantAdminSite.has_permission()` is called
3. **Session Check**: Looks for `jwt_token` and `user_data` in session
4. **User Reconstruction**: Creates TenantUser from session data
5. **Tenant Setup**: Sets `request.tenant_id`, `request.tenant_slug`, etc.
6. **Authorization**: Checks if user has permission for the app/model
7. **Query Filter**: `TenantModelAdmin.get_queryset()` filters by tenant_id
8. **Response**: Returns tenant-isolated data

### Logout Flow

1. **Logout Click**: User clicks logout in admin
2. **Session Clear**: `admin_logout_view()` calls `session.flush()`
3. **Django Logout**: Calls Django's `logout()` function
4. **Redirect**: Redirects to `/admin/login/`

## Key Features

### ✅ No User Models in HMS Database
- HMS app does not have auth_user table
- All user data comes from SuperAdmin via JWT
- TenantUser exists only in memory during requests

### ✅ UUID User IDs Support
- User IDs from SuperAdmin are UUIDs (not integers)
- TenantUser stores UUID in `id` and `pk` fields
- No LogEntry widget to avoid UUID/integer conflicts

### ✅ Session-Based Admin Authentication
- Admin uses standard Django session authentication
- JWT validated once during login
- Subsequent requests use session (no repeated JWT validation)
- Sessions expire after 8 hours or browser close

### ✅ Tenant Isolation
- All queries automatically filtered by tenant_id
- TenantModelAdmin sets tenant_id on record creation
- Tenant info displayed prominently in admin interface

### ✅ Module-Based Access Control
- Checks if 'hms' module is enabled in JWT
- Returns 403 if module not enabled for user
- Prevents unauthorized access to HMS admin

### ✅ Permission Checking
- Permissions from JWT payload
- Granular permission checks for add/change/delete
- App-level permission checks via `has_module_perms()`

### ✅ Beautiful UI
- Modern, responsive admin login page
- Gradient design with HMS branding
- Tenant information dashboard
- Module badges showing enabled features

## Configuration Requirements

### Environment Variables (.env)
```env
# Required
JWT_SECRET_KEY=same-as-superadmin-secret-key
JWT_ALGORITHM=HS256
SUPERADMIN_URL=https://admin.celiyo.com

# Optional (defaults shown)
SESSION_COOKIE_AGE=28800  # 8 hours
```

### SuperAdmin Requirements

The SuperAdmin system must:
1. Provide `/api/auth/login/` endpoint
2. Accept `email` and `password` in request body
3. Return response format:
```json
{
  "tokens": {
    "access": "eyJhbGc...",
    "refresh": "eyJhbG..."
  },
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "tenant": "tenant-uuid",
    "tenant_name": "hospital-name",
    "is_super_admin": false
  }
}
```

4. JWT payload must include:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "tenant_id": "tenant-uuid",
  "tenant_slug": "hospital-name",
  "is_super_admin": false,
  "permissions": {
    "patients": ["view", "create", "edit"],
    "appointments": ["view", "create"]
  },
  "enabled_modules": ["hms"]
}
```

5. Use same `JWT_SECRET_KEY` as HMS
6. Enable 'hms' module for users who should access HMS admin

## Usage

### Starting the Server
```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Collect static files
python manage.py collectstatic

# Run server
python manage.py runserver 127.0.0.1:8002
```

### Accessing Admin
1. Navigate to `http://127.0.0.1:8002/admin/`
2. Login using SuperAdmin credentials or JWT token
3. Access tenant-isolated data

### Registering Models
```python
# In your app's admin.py
from common.admin_site import tenant_admin_site, TenantModelAdmin
from .models import YourModel

class YourModelAdmin(TenantModelAdmin):
    list_display = ['name', 'created_at']
    # ... other admin options

# Register with tenant_admin_site, NOT admin.site
tenant_admin_site.register(YourModel, YourModelAdmin)
```

## Security Considerations

### ✅ Implemented
- JWT signature validation
- Module-based access control ('hms' must be enabled)
- Tenant isolation at database and query level
- Session expiration (8 hours, browser close)
- CSRF protection maintained
- Proxy endpoint to avoid exposing SuperAdmin API to frontend

### ⚠️ Important Notes
- JWT_SECRET_KEY must be kept secret and match SuperAdmin exactly
- SuperAdmin API must be secured (HTTPS in production)
- Session cookies should use secure flag in production
- Consider rate limiting on auth endpoints

## Troubleshooting

### Login fails with "HMS module not enabled"
- Check user's enabled_modules in SuperAdmin
- Ensure 'hms' is in the list
- Verify JWT payload includes enabled_modules

### Session expires immediately
- Check SESSION_COOKIE_AGE setting
- Verify browser accepts cookies
- Check for clock skew between servers

### Static files not loading
- Run `python manage.py collectstatic`
- Check STATIC_URL and STATIC_ROOT settings
- Ensure static file serving is configured

### Permission denied errors
- Check user's permissions in JWT payload
- Verify TenantModelAdmin permission methods
- Check app_label matches permission keys

## Files Changed/Created

### Created
- `common/auth_backends.py` - Authentication backends
- `common/views.py` - Login/logout views
- `common/admin_site.py` - Custom admin site
- `templates/admin/login.html` - Custom login template
- `templates/admin/index.html` - Custom admin index
- `templates/admin/app_index.html` - App index template
- `ADMIN_AUTHENTICATION_SETUP.md` - This documentation

### Modified
- `common/middleware.py` - Added thread-local request storage
- `hms/settings.py` - Added auth backends and SUPERADMIN_URL
- `hms/urls.py` - Added auth endpoints and custom admin site
- `.env.example` - Added SUPERADMIN_URL

## Testing Checklist

- [x] Syntax validation of Python files
- [ ] Login with valid SuperAdmin credentials
- [ ] Login with invalid credentials (should fail gracefully)
- [ ] Login with JWT token
- [ ] Login without 'hms' module (should deny access)
- [ ] Access admin index after login
- [ ] View tenant information display
- [ ] Access model list pages
- [ ] Create new records (tenant_id auto-set)
- [ ] Verify tenant isolation (no cross-tenant data)
- [ ] Logout and verify session cleared
- [ ] Session expiration after 8 hours
- [ ] Permission-based access control

## Next Steps

1. Set up proper environment variables
2. Configure SuperAdmin URL
3. Ensure JWT_SECRET_KEY matches SuperAdmin
4. Test login flow with actual SuperAdmin instance
5. Register your HMS models with tenant_admin_site
6. Test tenant isolation
7. Deploy to production with proper security settings

## Support

For issues or questions:
1. Check this documentation
2. Review the implementation guide in the original specification
3. Verify SuperAdmin API response format
4. Check Django and middleware logs
5. Ensure all environment variables are set correctly

---

**Implementation Date**: 2025-11-16
**Django Version**: 4.2+
**Python Version**: 3.8+
**HMS Module Version**: 1.0.0
