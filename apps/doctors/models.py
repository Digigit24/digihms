from django.db import models
from django.conf import settings
import datetime


class Specialty(models.Model):
    """Medical specialties"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'specialties'
        verbose_name = 'Specialty'
        verbose_name_plural = 'Specialties'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    """Doctor profile linked to User"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('inactive', 'Inactive')
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile'
    )
    
    # Professional Information
    medical_license_number = models.CharField(max_length=50, unique=True)
    license_issuing_authority = models.CharField(max_length=200)
    license_issue_date = models.DateField()
    license_expiry_date = models.DateField()
    
    # Qualifications
    qualifications = models.TextField(
        help_text="Comma-separated degrees (MBBS, MD, etc.)"
    )
    specialties = models.ManyToManyField(
        Specialty, 
        related_name='doctors',
        blank=True
    )
    
    # Experience
    years_of_experience = models.PositiveIntegerField(default=0)
    
    # Consultation
    consultation_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    consultation_duration = models.PositiveIntegerField(
        default=30, 
        help_text="Minutes"
    )
    is_available_online = models.BooleanField(default=True)
    is_available_offline = models.BooleanField(default=True)
    
    # Ratings & Stats
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00
    )
    total_reviews = models.PositiveIntegerField(default=0)
    total_consultations = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Additional
    signature = models.ImageField(
        upload_to='doctors/signatures/', 
        blank=True, 
        null=True
    )
    languages_spoken = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Comma-separated languages"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_profiles'
        verbose_name = 'Doctor Profile'
        verbose_name_plural = 'Doctor Profiles'
        permissions = [
            ("approve_doctor", "Can approve doctor registration"),
            ("view_doctor_schedule", "Can view doctor schedule"),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"
    
    @property
    def is_license_valid(self):
        """Check if medical license is valid"""
        return self.license_expiry_date > datetime.date.today()


class DoctorAvailability(models.Model):
    """Doctor's weekly availability schedule"""
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_appointments = models.PositiveIntegerField(default=20)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_availability'
        verbose_name = 'Doctor Availability'
        verbose_name_plural = 'Doctor Availabilities'
        unique_together = ['doctor', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()}"