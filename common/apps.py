from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'
    verbose_name = 'Common HMS Components'
    
    def ready(self):
        """Initialize app when Django starts."""
        # Import any signals or startup code here if needed
        pass