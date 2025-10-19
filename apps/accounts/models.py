from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model - Role is determined by Group membership.
    DO NOT add role field - use groups instead.
    """
    
    # Contact Information
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    alternate_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Personal Information
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other')
        ],
        blank=True,
        null=True
    )
    
    # Address
    address_line1 = models.CharField(max_length=200, blank=True, null=True)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10, blank=True, null=True)
    
    # Profile
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    bio = models.TextField(blank=True, null=True)
    
    # Hospital-specific (optional fields)
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = [
            ("view_all_users", "Can view all users"),
            ("manage_staff", "Can manage staff members"),
        ]
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['employee_id']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})" if self.get_full_name() else self.email
    
    @property
    def role(self):
        """Returns primary role based on group membership (for display only)"""
        groups = self.groups.values_list('name', flat=True)
        role_priority = [
            'Administrator',
            'Doctor',
            'Nurse',
            'Receptionist',
            'Pharmacist',
            'Lab Technician',
            'Patient'
        ]
        for role in role_priority:
            if role in groups:
                return role
        return 'No Role'
    
    @property
    def full_address(self):
        """Returns formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.pincode
        ]
        return ', '.join(filter(None, parts))