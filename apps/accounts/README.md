# Accounts App - SuperAdmin API Integration

This accounts app has been refactored to use the SuperAdmin backend API for user and role management instead of local Django models.

## Architecture

### Key Components

1. **API Client** (`api_client.py`): HTTP client for communicating with SuperAdmin backend
2. **Models** (`models.py`): Minimal proxy models (no database tables)
3. **Serializers** (`serializers.py`): Data validators for API requests
4. **Views** (`views.py`): API proxy views that forward requests to SuperAdmin
5. **Auth Backends** (`common/auth_backends.py`): JWT authentication handlers

## How It Works

### Authentication Flow

1. User logs in via HMS `/api/accounts/auth/login/`
2. Request is proxied to SuperAdmin API at `admin.celiyo.com/api/auth/login/`
3. SuperAdmin validates credentials and returns JWT tokens
4. JWT token contains:
   - User ID, email, tenant info
   - Enabled modules (must include 'hms')
   - Permissions
5. Future requests include JWT token in Authorization header
6. Middleware validates JWT and sets up tenant database connection

### User Management Flow

1. Admin creates user via HMS `/api/accounts/users/`
2. Request data is validated by serializers
3. API client calls SuperAdmin `/api/users/` with JWT token
4. SuperAdmin creates user in its database
5. Response is returned to HMS frontend

**Important**: All users are stored in the SuperAdmin database, not in HMS database.

## API Endpoints

### Authentication

- `POST /api/accounts/auth/register/` - Register new tenant (creates tenant + admin user)
- `POST /api/accounts/auth/login/` - Login user
- `POST /api/accounts/auth/logout/` - Logout user
- `GET /api/accounts/auth/me/` - Get current user profile
- `PATCH /api/accounts/auth/me/` - Update current user profile
- `POST /api/accounts/auth/change-password/` - Change password
- `POST /api/accounts/auth/token/refresh/` - Refresh JWT token

### User Management

- `GET /api/accounts/users/` - List users for tenant
- `POST /api/accounts/users/` - Create new user
- `GET /api/accounts/users/{id}/` - Get user details
- `PATCH /api/accounts/users/{id}/` - Update user
- `DELETE /api/accounts/users/{id}/` - Delete user
- `POST /api/accounts/users/{id}/assign_roles/` - Assign roles to user
- `DELETE /api/accounts/users/{id}/remove_role/` - Remove role from user

### Role Management

- `GET /api/accounts/roles/` - List roles for tenant
- `POST /api/accounts/roles/` - Create new role
- `GET /api/accounts/roles/{id}/` - Get role details
- `PATCH /api/accounts/roles/{id}/` - Update role
- `DELETE /api/accounts/roles/{id}/` - Delete role
- `GET /api/accounts/roles/{id}/members/` - Get users with this role
- `GET /api/accounts/roles/permissions_schema/` - Get permissions schema

## Configuration

### Environment Variables

```bash
# SuperAdmin Backend URL
SUPERADMIN_URL=https://admin.celiyo.com

# JWT Configuration (MUST match SuperAdmin)
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
```

### Settings

```python
# hms/settings.py

# SuperAdmin URL
SUPERADMIN_URL = config('SUPERADMIN_URL', default='https://admin.celiyo.com')

# JWT Configuration
JWT_SECRET_KEY = config('JWT_SECRET_KEY')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'common.auth_backends.SuperAdminAuthBackend',  # For admin login
    'common.auth_backends.JWTAuthBackend',         # For API requests
    'django.contrib.auth.backends.ModelBackend',   # Fallback
]

# Middleware
MIDDLEWARE = [
    # ...
    'common.middleware.JWTAuthenticationMiddleware',  # JWT validation
    # ...
]
```

## Usage Examples

### Login

```bash
curl -X POST http://localhost:8000/api/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "tenant": "tenant-uuid",
    "roles": [...]
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

### Create User

```bash
curl -X POST http://localhost:8000/api/accounts/users/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "email": "doctor@example.com",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "role_ids": ["role-uuid"],
    "department": "Cardiology",
    "employee_id": "EMP001"
  }'
```

### Get Current User

```bash
curl -X GET http://localhost:8000/api/accounts/auth/me/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Create Role

```bash
curl -X POST http://localhost:8000/api/accounts/roles/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Doctor",
    "description": "Hospital doctor role",
    "permissions": {
      "hms": {
        "patients": {
          "view": true,
          "create": true,
          "edit": true
        },
        "appointments": {
          "view": true,
          "create": true
        }
      }
    }
  }'
```

## Important Notes

### No Migrations Required

Since users are managed via API, **no database migrations are needed** for the User model. The User model exists only for Django compatibility.

### Tenant Isolation

- All API calls are automatically scoped to the tenant from the JWT token
- Users can only see/manage users and roles within their tenant
- SuperAdmins can see across all tenants

### Error Handling

The API client raises `SuperAdminAPIError` exceptions with:
- `message`: Error description
- `status_code`: HTTP status code
- `response_data`: Full error response from SuperAdmin

### Caching

Consider adding caching for frequently accessed data:
- User profile
- Roles list
- Permissions schema

## Troubleshooting

### JWT Token Issues

- Ensure `JWT_SECRET_KEY` matches between HMS and SuperAdmin
- Check token expiration time
- Verify 'hms' is in enabled_modules

### Connection Errors

- Verify `SUPERADMIN_URL` is accessible
- Check network/firewall settings
- Ensure SSL certificates are valid

### Permission Errors

- Verify user has correct roles assigned
- Check JWT token contains expected permissions
- Ensure tenant has 'hms' module enabled

## Testing

To test the integration:

```bash
# 1. Start the server
python manage.py runserver

# 2. Test login
curl -X POST http://localhost:8000/api/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'

# 3. Test user creation (use token from login)
curl -X POST http://localhost:8000/api/accounts/users/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", ...}'
```

## Migration from Old System

If migrating from the old local User model:

1. **Backup existing users** from local database
2. **Create users in SuperAdmin** via API or admin interface
3. **Update references** to use JWT authentication
4. **Test thoroughly** before deploying

## Future Improvements

- Add response caching for better performance
- Implement retry logic with exponential backoff
- Add comprehensive error logging and monitoring
- Create admin interface for user management
- Add bulk user import/export functionality
