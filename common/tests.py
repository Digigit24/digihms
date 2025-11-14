"""
Tests for HMS JWT authentication system.
"""

import jwt
import uuid
from django.test import TestCase, RequestFactory
from django.conf import settings
from django.http import JsonResponse
from unittest.mock import patch, MagicMock

from common.middleware import JWTAuthenticationMiddleware, get_tenant_info
from common.permissions import check_permission, HMSPermissions
from common.database_router import HMSDatabaseRouter


class JWTMiddlewareTest(TestCase):
    """Test JWT authentication middleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = JWTAuthenticationMiddleware()
        self.test_secret = 'test-jwt-secret-key'
        
        # Mock settings
        self.original_jwt_secret = getattr(settings, 'JWT_SECRET_KEY', None)
        self.original_jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', None)
        settings.JWT_SECRET_KEY = self.test_secret
        settings.JWT_ALGORITHM = 'HS256'
    
    def tearDown(self):
        # Restore original settings
        if self.original_jwt_secret:
            settings.JWT_SECRET_KEY = self.original_jwt_secret
        if self.original_jwt_algorithm:
            settings.JWT_ALGORITHM = self.original_jwt_algorithm
    
    def create_test_jwt(self, payload=None):
        """Create a test JWT token."""
        default_payload = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@hospital.com',
            'tenant_id': 'test-hospital-123',
            'tenant_slug': 'test-hospital',
            'is_super_admin': False,
            'permissions': {
                'hms.patients.view': 'all',
                'hms.patients.create': True,
            },
            'enabled_modules': ['hms'],
            'database_url': 'postgresql://user:pass@localhost:5432/test_db'
        }
        
        if payload:
            default_payload.update(payload)
        
        return jwt.encode(default_payload, self.test_secret, algorithm='HS256')
    
    def test_valid_jwt_processing(self):
        """Test processing of valid JWT token."""
        token = self.create_test_jwt()
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        
        with patch.object(self.middleware, '_setup_tenant_database'):
            response = self.middleware.process_request(request)
        
        # Should return None (no error)
        self.assertIsNone(response)
        
        # Check request attributes
        self.assertEqual(request.tenant_id, 'test-hospital-123')
        self.assertEqual(request.email, 'test@hospital.com')
        self.assertIn('hms.patients.view', request.permissions)
    
    def test_missing_authorization_header(self):
        """Test request without Authorization header."""
        request = self.factory.get('/')
        response = self.middleware.process_request(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
    
    def test_invalid_jwt_format(self):
        """Test invalid JWT format."""
        request = self.factory.get('/', HTTP_AUTHORIZATION='Bearer invalid-token')
        response = self.middleware.process_request(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
    
    def test_missing_hms_module(self):
        """Test JWT without HMS module enabled."""
        token = self.create_test_jwt({'enabled_modules': ['crm']})
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.middleware.process_request(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)
    
    def test_skip_paths(self):
        """Test that certain paths skip JWT validation."""
        request = self.factory.get('/admin/')
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)  # Should skip validation


class PermissionTest(TestCase):
    """Test permission checking functions."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def create_mock_request(self, permissions=None):
        """Create a mock request with permissions."""
        request = self.factory.get('/')
        request.user_id = str(uuid.uuid4())
        request.email = 'test@hospital.com'
        request.tenant_id = 'test-hospital'
        request.permissions = permissions or {}
        return request
    
    def test_check_permission_boolean_true(self):
        """Test boolean permission check (true)."""
        request = self.create_mock_request({
            'hms.patients.create': True
        })
        
        result = check_permission(request, 'hms.patients.create')
        self.assertTrue(result)
    
    def test_check_permission_boolean_false(self):
        """Test boolean permission check (false)."""
        request = self.create_mock_request({
            'hms.patients.delete': False
        })
        
        result = check_permission(request, 'hms.patients.delete')
        self.assertFalse(result)
    
    def test_check_permission_scope_all(self):
        """Test scope-based permission (all)."""
        request = self.create_mock_request({
            'hms.patients.view': 'all'
        })
        
        result = check_permission(request, 'hms.patients.view')
        self.assertTrue(result)
    
    def test_check_permission_scope_own_with_owner(self):
        """Test scope-based permission (own) with matching owner."""
        request = self.create_mock_request({
            'hms.patients.view': 'own'
        })
        
        result = check_permission(request, 'hms.patients.view', request.user_id)
        self.assertTrue(result)
    
    def test_check_permission_scope_own_without_owner(self):
        """Test scope-based permission (own) with different owner."""
        request = self.create_mock_request({
            'hms.patients.view': 'own'
        })
        
        different_user_id = str(uuid.uuid4())
        result = check_permission(request, 'hms.patients.view', different_user_id)
        self.assertFalse(result)
    
    def test_check_permission_missing(self):
        """Test checking non-existent permission."""
        request = self.create_mock_request({})
        
        result = check_permission(request, 'hms.patients.view')
        self.assertFalse(result)


class DatabaseRouterTest(TestCase):
    """Test database routing functionality."""
    
    def setUp(self):
        self.router = HMSDatabaseRouter()
    
    def test_hms_model_routing(self):
        """Test that HMS models are routed to tenant database."""
        from apps.patients.models import PatientProfile
        
        with patch('common.database_router.get_tenant_database_name', return_value='tenant_test'):
            db = self.router.db_for_read(PatientProfile)
            self.assertEqual(db, 'tenant_test')
    
    def test_auth_model_routing(self):
        """Test that auth models are routed to default database."""
        from django.contrib.auth.models import User
        
        db = self.router.db_for_read(User)
        self.assertEqual(db, 'default')
    
    def test_migration_routing_default_db(self):
        """Test migration routing for default database."""
        # Auth app migrations should run on default DB
        result = self.router.allow_migrate('default', 'auth')
        self.assertTrue(result)
        
        # HMS app migrations should NOT run on default DB
        result = self.router.allow_migrate('default', 'patients')
        self.assertFalse(result)
    
    def test_migration_routing_tenant_db(self):
        """Test migration routing for tenant database."""
        # HMS app migrations should run on tenant DB
        result = self.router.allow_migrate('tenant_test', 'patients')
        self.assertTrue(result)
        
        # Auth app migrations should NOT run on tenant DB
        result = self.router.allow_migrate('tenant_test', 'auth')
        self.assertFalse(result)


class IntegrationTest(TestCase):
    """Integration tests for the complete JWT authentication flow."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = JWTAuthenticationMiddleware()
        
        # Mock settings
        settings.JWT_SECRET_KEY = 'test-secret'
        settings.JWT_ALGORITHM = 'HS256'
    
    @patch('common.middleware.JWTAuthenticationMiddleware._setup_tenant_database')
    def test_complete_authentication_flow(self, mock_setup_db):
        """Test complete authentication flow from JWT to database routing."""
        # Create test JWT
        payload = {
            'user_id': str(uuid.uuid4()),
            'email': 'doctor@city-hospital.com',
            'tenant_id': 'city-hospital-123',
            'tenant_slug': 'city-hospital',
            'is_super_admin': False,
            'permissions': {
                'hms.patients.view': 'all',
                'hms.patients.create': True,
                'hms.appointments.view': 'own',
            },
            'enabled_modules': ['hms'],
            'database_url': 'postgresql://user:pass@localhost:5432/city_hospital_db'
        }
        
        token = jwt.encode(payload, 'test-secret', algorithm='HS256')
        request = self.factory.get('/api/patients/', HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Process request through middleware
        response = self.middleware.process_request(request)
        
        # Should succeed
        self.assertIsNone(response)
        
        # Verify request attributes
        self.assertEqual(request.user_id, payload['user_id'])
        self.assertEqual(request.tenant_id, 'city-hospital-123')
        self.assertEqual(request.permissions['hms.patients.view'], 'all')
        
        # Verify database setup was called
        mock_setup_db.assert_called_once_with(
            'city-hospital-123',
            'postgresql://user:pass@localhost:5432/city_hospital_db'
        )
        
        # Test permission checking
        self.assertTrue(check_permission(request, 'hms.patients.view'))
        self.assertTrue(check_permission(request, 'hms.patients.create'))
        self.assertFalse(check_permission(request, 'hms.patients.delete'))  # Not in JWT
    
    def test_permission_scope_filtering(self):
        """Test permission scope filtering logic."""
        # Test 'all' scope
        request = self.factory.get('/')
        request.permissions = {'hms.patients.view': 'all'}
        request.user_id = str(uuid.uuid4())
        
        self.assertTrue(check_permission(request, 'hms.patients.view'))
        
        # Test 'own' scope with matching owner
        request.permissions = {'hms.patients.view': 'own'}
        self.assertTrue(check_permission(request, 'hms.patients.view', request.user_id))
        
        # Test 'own' scope with different owner
        different_user = str(uuid.uuid4())
        self.assertFalse(check_permission(request, 'hms.patients.view', different_user))


class TenantDatabaseTest(TestCase):
    """Test tenant database management."""
    
    @patch('django.db.connections')
    def test_tenant_database_setup(self, mock_connections):
        """Test tenant database configuration setup."""
        from common.database_router import TenantDatabaseManager
        
        mock_connections.databases = {'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'default_db',
            'USER': 'postgres',
            'PASSWORD': 'password',
            'HOST': 'localhost',
            'PORT': '5432',
        }}
        
        # Test database URL parsing
        middleware = JWTAuthenticationMiddleware()
        db_config = middleware._parse_database_url(
            'postgresql://user:pass@host:5432/tenant_db'
        )
        
        expected = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'tenant_db',
            'USER': 'user',
            'PASSWORD': 'pass',
            'HOST': 'host',
            'PORT': 5432,
            'CONN_MAX_AGE': 600,
            'OPTIONS': {},
        }
        
        self.assertEqual(db_config, expected)


# Performance and Load Testing Helpers
class PerformanceTestMixin:
    """Mixin for performance testing of JWT operations."""
    
    def time_jwt_validation(self, num_requests=100):
        """Time JWT validation performance."""
        import time
        
        token = self.create_test_jwt()
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        
        start_time = time.time()
        
        for _ in range(num_requests):
            with patch.object(self.middleware, '_setup_tenant_database'):
                self.middleware.process_request(request)
        
        end_time = time.time()
        avg_time = (end_time - start_time) / num_requests
        
        print(f"Average JWT validation time: {avg_time:.4f} seconds")
        return avg_time
    
    def test_permission_check_performance(self):
        """Test permission checking performance."""
        import time
        
        request = self.factory.get('/')
        request.permissions = {
            'hms.patients.view': 'all',
            'hms.patients.create': True,
            'hms.appointments.view': 'own',
        }
        request.user_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        for _ in range(1000):
            check_permission(request, 'hms.patients.view')
        
        end_time = time.time()
        avg_time = (end_time - start_time) / 1000
        
        print(f"Average permission check time: {avg_time:.6f} seconds")
        return avg_time


# Example test data for manual testing
TEST_JWT_PAYLOADS = {
    'doctor_all_permissions': {
        'user_id': 'doctor-uuid-123',
        'email': 'doctor@city-hospital.com',
        'tenant_id': 'city-hospital-123',
        'tenant_slug': 'city-hospital',
        'is_super_admin': False,
        'permissions': {
            'hms.patients.view': 'all',
            'hms.patients.create': True,
            'hms.patients.edit': True,
            'hms.patients.delete': True,
            'hms.appointments.view': 'all',
            'hms.appointments.create': True,
            'hms.appointments.edit': True,
            'hms.appointments.delete': True,
            'hms.prescriptions.view': 'all',
            'hms.prescriptions.create': True,
            'hms.billing.view': 'all',
            'hms.billing.create': True,
        },
        'enabled_modules': ['hms'],
        'database_url': 'postgresql://user:pass@localhost:5432/city_hospital_db'
    },
    
    'nurse_limited_permissions': {
        'user_id': 'nurse-uuid-456',
        'email': 'nurse@city-hospital.com',
        'tenant_id': 'city-hospital-123',
        'tenant_slug': 'city-hospital',
        'is_super_admin': False,
        'permissions': {
            'hms.patients.view': 'all',
            'hms.patients.create': True,
            'hms.patients.edit': True,
            'hms.patients.delete': False,
            'hms.appointments.view': 'all',
            'hms.appointments.create': False,
            'hms.appointments.edit': False,
            'hms.appointments.delete': False,
        },
        'enabled_modules': ['hms'],
        'database_url': 'postgresql://user:pass@localhost:5432/city_hospital_db'
    },
    
    'receptionist_own_only': {
        'user_id': 'receptionist-uuid-789',
        'email': 'receptionist@city-hospital.com',
        'tenant_id': 'city-hospital-123',
        'tenant_slug': 'city-hospital',
        'is_super_admin': False,
        'permissions': {
            'hms.patients.view': 'own',
            'hms.patients.create': True,
            'hms.patients.edit': 'own',
            'hms.patients.delete': False,
            'hms.appointments.view': 'own',
            'hms.appointments.create': True,
            'hms.appointments.edit': 'own',
        },
        'enabled_modules': ['hms'],
        'database_url': 'postgresql://user:pass@localhost:5432/city_hospital_db'
    }
}


def generate_test_tokens():
    """Generate test JWT tokens for manual testing."""
    secret = getattr(settings, 'JWT_SECRET_KEY', 'test-secret')
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    
    tokens = {}
    for role, payload in TEST_JWT_PAYLOADS.items():
        tokens[role] = jwt.encode(payload, secret, algorithm=algorithm)
    
    return tokens


if __name__ == '__main__':
    # Generate test tokens for manual testing
    print("=== HMS JWT Test Tokens ===")
    tokens = generate_test_tokens()
    
    for role, token in tokens.items():
        print(f"\n{role.upper()}:")
        print(f"Token: {token}")
        print(f"Test command:")
        print(f'curl -H "Authorization: Bearer {token}" http://localhost:8002/api/patients/')