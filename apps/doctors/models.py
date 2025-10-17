from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Specialty(models.Model):
    """Medical specialties"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True,null=True,)
    department = models.CharField(max_length=100,null=True, blank=True)
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
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile'
    )

    # License
    medical_license_number = models.CharField(max_length=64, blank=True)
    license_issuing_authority = models.CharField(max_length=128, blank=True)
    license_issue_date = models.DateField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)

    # Professional
    qualifications = models.TextField(blank=True)
    specialties = models.ManyToManyField(Specialty, related_name='doctors', blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)

    # Consultation
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    consultation_duration = models.PositiveIntegerField(default=15)  # minutes
    is_available_online = models.BooleanField(default=False)
    is_available_offline = models.BooleanField(default=True)

    # Status
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='active')

    # Ratings & stats
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    total_consultations = models.PositiveIntegerField(default=0)

    # Misc
    signature = models.TextField(null=True,blank=True)
    languages_spoken = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'doctor_profiles'
        verbose_name = 'Doctor Profile'
        verbose_name_plural = 'Doctor Profiles'
        ordering = ['-created_at']

    def __str__(self):
        u = getattr(self, 'user', None)
        if not u:
            return f'DoctorProfile #{self.pk or "unsaved"}'
        full_name = getattr(u, 'get_full_name', lambda: '')() or f'{getattr(u, "first_name", "")} {getattr(u, "last_name", "")}'.strip()
        return full_name or getattr(u, 'email', '') or f'DoctorProfile #{self.pk}'

    @property
    def is_license_valid(self):
        """
        True  -> expiry date today or in future
        False -> expiry date in past
        None  -> unknown (no expiry set)
        """
        exp = self.license_expiry_date
        if not exp:
            return None
        return exp >= timezone.localdate()

    def clean(self):
        # Validate license dates only when both present
        if self.license_issue_date and self.license_expiry_date:
            if self.license_expiry_date < self.license_issue_date:
                raise ValidationError({'license_expiry_date': 'Expiry date cannot be before issue date.'})
        # Fee non-negative
        if self.consultation_fee is not None and self.consultation_fee < 0:
            raise ValidationError({'consultation_fee': 'Fee cannot be negative.'})


class DoctorAvailability(models.Model):
    """Weekly availability slots for a doctor"""
    DAYS = [
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
    day_of_week = models.CharField(max_length=16, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_appointments = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'doctor_availability'
        verbose_name = 'Doctor Availability'
        verbose_name_plural = 'Doctor Availability'
        ordering = ['doctor_id', 'day_of_week', 'start_time']

    def __str__(self):
        return f'{self.doctor} - {self.day_of_week} {self.start_time}-{self.end_time}'

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})