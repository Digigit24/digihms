from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Seed authentication groups with permissions'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Creating groups and assigning permissions...'))
        
        # Define groups and their permissions
        groups_config = {
            'Administrator': {
                'all': True,  # Gets all permissions
            },
            'Doctor': {
                'doctors': ['view', 'change'],  # Own profile
                'patients': ['view', 'add', 'change'],  # Patient management
            },
            'Patient': {
                'patients': ['view'],  # Own profile only (enforced in queryset)
            },
            'Nurse': {
                'patients': ['view', 'change'],
            },
            'Receptionist': {
                'patients': ['view', 'add', 'change'],
                'accounts': ['view'],
            },
            'Pharmacist': {
                'patients': ['view'],
            },
            'Lab Technician': {
                'patients': ['view'],
            },
        }
        
        created_count = 0
        updated_count = 0
        
        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                created_count += 1
            else:
                updated_count += 1
            
            if config.get('all'):
                # Administrator gets everything
                permissions = Permission.objects.all()
                group.permissions.set(permissions)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {group_name}: ALL permissions ({permissions.count()} perms)')
                )
                continue
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add specific permissions
            perm_count = 0
            for app_label, actions in config.items():
                for action in actions:
                    # Find permissions like: view_patientprofile, add_doctorprofile
                    perms = Permission.objects.filter(
                        codename__startswith=action,
                        content_type__app_label=app_label
                    )
                    
                    for perm in perms:
                        group.permissions.add(perm)
                        perm_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {group_name}: {perm_count} permissions assigned'
                )
            )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Groups seeded successfully!'))
        self.stdout.write(self.style.SUCCESS(f'   Created: {created_count} groups'))
        self.stdout.write(self.style.SUCCESS(f'   Updated: {updated_count} groups'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('📝 Note: Run this command again after adding new models to update permissions.'))