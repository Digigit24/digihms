from django.conf import settings
from .middleware import get_tenant_database_name
import logging

logger = logging.getLogger(__name__)


class HMSDatabaseRouter:
    """
    Database router for HMS with separate database per tenant strategy.
    
    Routes HMS models to tenant-specific databases while keeping
    other models on the default database.
    """
    
    # HMS app labels that should use tenant databases
    HMS_APPS = {
        'patients',
        'doctors', 
        'appointments',
        'hospital',
        'opd',
        'pharmacy',
        'payments',
        'orders',
        'services',
    }
    
    # Models that should always use default database (metadata)
    DEFAULT_DB_MODELS = {
        'auth',
        'admin',
        'contenttypes',
        'sessions',
        'messages',
        'staticfiles',
        'accounts',  # User management stays on default
    }
    
    def db_for_read(self, model, **hints):
        """
        Suggest the database to read from for a model.
        
        Args:
            model: Django model class
            **hints: Additional routing hints
            
        Returns:
            str: Database name or None
        """
        app_label = model._meta.app_label
        
        # Always use default database for certain models
        if app_label in self.DEFAULT_DB_MODELS:
            return 'default'
        
        # Use tenant database for HMS models
        if app_label in self.HMS_APPS:
            tenant_db = get_tenant_database_name()
            logger.debug(f"Routing read for {app_label}.{model.__name__} to {tenant_db}")
            return tenant_db
        
        # Default database for everything else
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        Suggest the database to write to for a model.
        
        Args:
            model: Django model class
            **hints: Additional routing hints
            
        Returns:
            str: Database name or None
        """
        app_label = model._meta.app_label
        
        # Always use default database for certain models
        if app_label in self.DEFAULT_DB_MODELS:
            return 'default'
        
        # Use tenant database for HMS models
        if app_label in self.HMS_APPS:
            tenant_db = get_tenant_database_name()
            logger.debug(f"Routing write for {app_label}.{model.__name__} to {tenant_db}")
            return tenant_db
        
        # Default database for everything else
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between objects.
        
        Args:
            obj1: First model instance
            obj2: Second model instance
            **hints: Additional routing hints
            
        Returns:
            bool: True if relation is allowed, False if not, None if no opinion
        """
        # Get database names for both objects
        db1 = self._get_object_db(obj1)
        db2 = self._get_object_db(obj2)
        
        # Allow relations within the same database
        if db1 == db2:
            return True
        
        # Allow relations between default DB models and tenant models
        # (e.g., User from default DB can relate to Patient in tenant DB)
        if (db1 == 'default' and db2.startswith('tenant_')) or \
           (db2 == 'default' and db1.startswith('tenant_')):
            return True
        
        # Disallow relations between different tenant databases
        if db1.startswith('tenant_') and db2.startswith('tenant_') and db1 != db2:
            return False
        
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Determine if a migration should be run on a database.
        
        Args:
            db: Database alias
            app_label: App label
            model_name: Model name (optional)
            **hints: Additional routing hints
            
        Returns:
            bool: True if migration is allowed, False if not, None if no opinion
        """
        # Default database migrations
        if db == 'default':
            # Allow migrations for default DB models
            if app_label in self.DEFAULT_DB_MODELS:
                return True
            # Disallow HMS app migrations on default DB
            if app_label in self.HMS_APPS:
                return False
            # Allow other migrations on default DB
            return True
        
        # Tenant database migrations
        if db.startswith('tenant_'):
            # Allow HMS app migrations on tenant databases
            if app_label in self.HMS_APPS:
                return True
            # Disallow default DB model migrations on tenant databases
            if app_label in self.DEFAULT_DB_MODELS:
                return False
            # No opinion on other migrations
            return None
        
        # No opinion for other databases
        return None
    
    def _get_object_db(self, obj):
        """
        Get the database name for a model instance.
        
        Args:
            obj: Model instance
            
        Returns:
            str: Database name
        """
        app_label = obj._meta.app_label
        
        if app_label in self.DEFAULT_DB_MODELS:
            return 'default'
        elif app_label in self.HMS_APPS:
            return get_tenant_database_name()
        else:
            return 'default'


class TenantDatabaseManager:
    """
    Utility class for managing tenant databases.
    """
    
    @staticmethod
    def create_tenant_database(tenant_id, database_config=None):
        """
        Create a new tenant database.
        
        Args:
            tenant_id: Unique tenant identifier
            database_config: Optional database configuration
            
        Returns:
            str: Database name
        """
        from django.db import connections
        from django.core.management import execute_from_command_line
        import sys
        
        database_name = f'tenant_{tenant_id}'
        
        try:
            # Add database configuration
            if database_config:
                connections.databases[database_name] = database_config
            else:
                # Use default configuration with tenant-specific name
                default_config = settings.DATABASES['default'].copy()
                default_config['NAME'] = database_name
                connections.databases[database_name] = default_config
            
            # Run migrations for the new tenant database
            old_argv = sys.argv
            sys.argv = ['manage.py', 'migrate', '--database', database_name]
            
            try:
                execute_from_command_line(sys.argv)
                logger.info(f"Successfully created and migrated tenant database: {database_name}")
            finally:
                sys.argv = old_argv
            
            return database_name
            
        except Exception as e:
            logger.error(f"Failed to create tenant database {database_name}: {str(e)}")
            raise
    
    @staticmethod
    def get_tenant_databases():
        """
        Get list of all tenant databases.
        
        Returns:
            list: List of tenant database names
        """
        from django.db import connections
        
        return [
            db_name for db_name in connections.databases.keys()
            if db_name.startswith('tenant_')
        ]
    
    @staticmethod
    def remove_tenant_database(tenant_id):
        """
        Remove tenant database configuration.
        
        Note: This only removes the configuration, not the actual database.
        
        Args:
            tenant_id: Unique tenant identifier
        """
        from django.db import connections
        
        database_name = f'tenant_{tenant_id}'
        
        if database_name in connections.databases:
            del connections.databases[database_name]
            logger.info(f"Removed tenant database configuration: {database_name}")