import jwt
import threading
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.db import connections
from django.db.utils import ConnectionDoesNotExist
import logging

logger = logging.getLogger(__name__)

# Thread-local storage for tenant information
_thread_local = threading.local()


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    JWT Authentication Middleware for HMS with separate database per tenant.
    
    Validates JWT from SuperAdmin and sets up tenant-specific database routing.
    """
    
    def process_request(self, request):
        """Process incoming request and validate JWT."""
        
        # Skip JWT validation for certain paths
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/health/',
            '/docs/',
            '/redoc/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Get JWT token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Missing or invalid Authorization header',
                'detail': 'Expected format: Bearer <token>'
            }, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Validate required fields
            required_fields = ['user_id', 'email', 'tenant_id', 'tenant_slug', 'enabled_modules']
            for field in required_fields:
                if field not in payload:
                    return JsonResponse({
                        'error': 'Invalid JWT token',
                        'detail': f'Missing required field: {field}'
                    }, status=401)
            
            # Check if HMS module is enabled
            enabled_modules = payload.get('enabled_modules', [])
            if 'hms' not in enabled_modules:
                return JsonResponse({
                    'error': 'Access denied',
                    'detail': 'HMS module not enabled for this tenant'
                }, status=403)
            
            # Extract tenant information
            tenant_id = payload['tenant_id']
            tenant_slug = payload['tenant_slug']
            database_url = payload.get('database_url')
            
            # Set request attributes
            request.user_id = payload['user_id']
            request.email = payload['email']
            request.tenant_id = tenant_id
            request.tenant_slug = tenant_slug
            request.is_super_admin = payload.get('is_super_admin', False)
            request.permissions = payload.get('permissions', {})
            request.database_url = database_url
            
            # Set up tenant database connection
            self._setup_tenant_database(tenant_id, database_url)
            
            # Store tenant info in thread-local storage
            _thread_local.tenant_id = tenant_id
            _thread_local.tenant_slug = tenant_slug
            _thread_local.database_name = f'tenant_{tenant_id}'
            
            logger.info(f"JWT validated for user {payload['email']} on tenant {tenant_id}")
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({
                'error': 'Token expired',
                'detail': 'JWT token has expired'
            }, status=401)
        
        except jwt.InvalidTokenError as e:
            return JsonResponse({
                'error': 'Invalid token',
                'detail': str(e)
            }, status=401)
        
        except Exception as e:
            logger.error(f"JWT validation error: {str(e)}")
            return JsonResponse({
                'error': 'Authentication failed',
                'detail': 'Unable to validate token'
            }, status=500)
        
        return None
    
    def _setup_tenant_database(self, tenant_id, database_url=None):
        """
        Set up tenant-specific database connection.
        
        Args:
            tenant_id: Unique tenant identifier
            database_url: Optional database URL from JWT
        """
        database_name = f'tenant_{tenant_id}'
        
        # Check if database connection already exists
        if database_name in connections.databases:
            return
        
        try:
            if database_url:
                # Parse database URL if provided
                db_config = self._parse_database_url(database_url)
            else:
                # Use default configuration with tenant-specific database name
                default_db = settings.DATABASES['default'].copy()
                db_config = default_db.copy()
                db_config['NAME'] = database_name
            
            # Add tenant database to Django connections
            connections.databases[database_name] = db_config
            
            logger.info(f"Tenant database '{database_name}' configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup tenant database '{database_name}': {str(e)}")
            raise
    
    def _parse_database_url(self, database_url):
        """
        Parse database URL into Django database configuration.
        
        Args:
            database_url: PostgreSQL URL (e.g., postgresql://user:pass@host:port/dbname)
        
        Returns:
            dict: Django database configuration
        """
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(database_url)
            
            return {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': parsed.path[1:],  # Remove leading slash
                'USER': parsed.username,
                'PASSWORD': parsed.password,
                'HOST': parsed.hostname,
                'PORT': parsed.port or 5432,
                'CONN_MAX_AGE': 600,
                'OPTIONS': {},
            }
        except Exception as e:
            logger.error(f"Failed to parse database URL: {str(e)}")
            raise ValueError(f"Invalid database URL format: {database_url}")


def get_tenant_info():
    """
    Get current tenant information from thread-local storage.
    
    Returns:
        dict: Tenant information or None if not set
    """
    try:
        return {
            'tenant_id': getattr(_thread_local, 'tenant_id', None),
            'tenant_slug': getattr(_thread_local, 'tenant_slug', None),
            'database_name': getattr(_thread_local, 'database_name', None),
        }
    except AttributeError:
        return None


def get_tenant_database_name():
    """
    Get current tenant database name.
    
    Returns:
        str: Database name or 'default' if not set
    """
    try:
        return getattr(_thread_local, 'database_name', 'default')
    except AttributeError:
        return 'default'


def clear_tenant_info():
    """Clear tenant information from thread-local storage."""
    for attr in ['tenant_id', 'tenant_slug', 'database_name']:
        if hasattr(_thread_local, attr):
            delattr(_thread_local, attr)