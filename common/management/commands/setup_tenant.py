"""
Management command to set up tenant databases and test JWT authentication.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections
from common.database_router import TenantDatabaseManager
import jwt
import uuid


class Command(BaseCommand):
    help = 'Set up tenant database and test JWT authentication'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='Tenant ID to set up database for',
        )
        parser.add_argument(
            '--database-url',
            type=str,
            help='Database URL for the tenant (optional)',
        )
        parser.add_argument(
            '--test-jwt',
            action='store_true',
            help='Generate and test a sample JWT token',
        )
        parser.add_argument(
            '--list-tenants',
            action='store_true',
            help='List all configured tenant databases',
        )

    def handle(self, *args, **options):
        if options['list_tenants']:
            self.list_tenant_databases()
        elif options['test_jwt']:
            self.test_jwt_generation()
        elif options['tenant_id']:
            self.setup_tenant_database(options['tenant_id'], options.get('database_url'))
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --tenant-id, --test-jwt, or --list-tenants')
            )

    def setup_tenant_database(self, tenant_id, database_url=None):
        """Set up a tenant database."""
        try:
            self.stdout.write(f'Setting up tenant database for: {tenant_id}')
            
            # Create database configuration
            if database_url:
                self.stdout.write(f'Using provided database URL: {database_url}')
                db_config = self._parse_database_url(database_url)
            else:
                # Use default configuration with tenant-specific name
                default_config = settings.DATABASES['default'].copy()
                db_config = default_config.copy()
                db_config['NAME'] = f'tenant_{tenant_id}'
                self.stdout.write(f'Using default config with database name: tenant_{tenant_id}')
            
            # Add to Django connections
            database_name = f'tenant_{tenant_id}'
            connections.databases[database_name] = db_config
            
            # Test connection
            connection = connections[database_name]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Database connection successful for {database_name}')
                    )
            
            # Run migrations
            self.stdout.write('Running migrations for tenant database...')
            from django.core.management import call_command
            call_command('migrate', database=database_name, verbosity=0)
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Tenant database {database_name} set up successfully')
            )
            
        except Exception as e:
            raise CommandError(f'Failed to set up tenant database: {str(e)}')

    def test_jwt_generation(self):
        """Generate and test a sample JWT token."""
        try:
            # Generate sample JWT payload
            payload = {
                'user_id': str(uuid.uuid4()),
                'email': 'doctor@test-hospital.com',
                'tenant_id': 'test-hospital-123',
                'tenant_slug': 'test-hospital',
                'is_super_admin': False,
                'permissions': {
                    'hms.patients.view': 'all',
                    'hms.patients.create': True,
                    'hms.patients.edit': True,
                    'hms.patients.delete': False,
                    'hms.appointments.view': 'own',
                    'hms.appointments.create': True,
                    'hms.appointments.edit': True,
                    'hms.appointments.delete': True,
                },
                'enabled_modules': ['hms'],
                'database_url': 'postgresql://user:pass@localhost:5432/test_hospital_db'
            }
            
            # Generate JWT token
            token = jwt.encode(
                payload,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            )
            
            self.stdout.write('Generated JWT Token:')
            self.stdout.write(self.style.WARNING(token))
            self.stdout.write('')
            
            # Test decoding
            decoded = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            self.stdout.write('Decoded JWT Payload:')
            import json
            self.stdout.write(json.dumps(decoded, indent=2, default=str))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ JWT generation and validation successful'))
            
            # Test with curl command
            self.stdout.write('')
            self.stdout.write('Test with curl:')
            self.stdout.write(f'curl -H "Authorization: Bearer {token}" http://localhost:8002/api/patients/')
            
        except Exception as e:
            raise CommandError(f'JWT test failed: {str(e)}')

    def list_tenant_databases(self):
        """List all configured tenant databases."""
        tenant_dbs = TenantDatabaseManager.get_tenant_databases()
        
        if not tenant_dbs:
            self.stdout.write('No tenant databases configured.')
            return
        
        self.stdout.write('Configured Tenant Databases:')
        for db_name in tenant_dbs:
            try:
                connection = connections[db_name]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    status_icon = self.style.SUCCESS('✓')
            except Exception:
                status_icon = self.style.ERROR('✗')
            
            self.stdout.write(f'{status_icon} {db_name}')

    def _parse_database_url(self, database_url):
        """Parse database URL into Django configuration."""
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