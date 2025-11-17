"""
DigiHMS Doctor Serializers

NOTE: These serializers use the OLD User model approach.
For NEW SuperAdmin-based authentication, use serializers from apps.accounts.serializers instead.
This file is kept for backwards compatibility only.
"""

from rest_framework import serializers
from django.db import transaction
from .models import DoctorProfile, Specialty, DoctorAvailability

# NOTE: UserSerializer removed - no local User model with SuperAdmin authentication


class SpecialtySerializer(serializers.ModelSerializer):
    """Specialty serializer"""
    doctors_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Specialty
        fields = [
            'id', 'name', 'code', 'description', 'department',
            'is_active', 'doctors_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_doctors_count(self, obj):
        """Count active doctors in this specialty"""
        return obj.doctors.filter(status='active').count()


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """Doctor availability serializer"""
    day_display = serializers.CharField(
        source='get_day_of_week_display',
        read_only=True
    )
    
    class Meta:
        model = DoctorAvailability
        fields = [
            'id', 'day_of_week', 'day_display', 'start_time', 'end_time',
            'is_available', 'max_appointments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DoctorAvailabilityCreateUpdateSerializer(serializers.ModelSerializer):
    """Create/Update serializer for doctor availability"""
    
    class Meta:
        model = DoctorAvailability
        exclude = ['doctor', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate time range"""
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })
        
        return attrs


class DoctorProfileListSerializer(serializers.ModelSerializer):
    """
    DEPRECATED: Use apps.accounts.serializers.DoctorProfileListSerializer instead.
    This uses the old User model structure.
    """
    specialties = SpecialtySerializer(many=True, read_only=True)
    is_license_valid = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'medical_license_number', 'qualifications', 'specialties',
            'years_of_experience', 'consultation_fee', 'consultation_duration',
            'is_available_online', 'is_available_offline',
            'average_rating', 'total_reviews', 'total_consultations',
            'status', 'is_license_valid', 'created_at'
        ]


class DoctorProfileDetailSerializer(serializers.ModelSerializer):
    """
    DEPRECATED: Use apps.accounts.serializers.DoctorProfileDetailSerializer instead.
    This uses the old User model structure.
    """
    specialties = SpecialtySerializer(many=True, read_only=True)
    availability = DoctorAvailabilitySerializer(many=True, read_only=True)
    is_license_valid = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = DoctorProfile
        fields = '__all__'


class DoctorProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """
    DEPRECATED: Use apps.accounts.serializers.DoctorProfileCreateUpdateSerializer instead.
    This requires the SuperAdmin authentication system.
    """
    specialty_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = DoctorProfile
        exclude = [
            'average_rating', 'total_reviews',
            'total_consultations', 'specialties', 'created_at', 'updated_at'
        ]
    
    def validate_license_expiry_date(self, value):
        """Ensure license expiry date is in the future or today"""
        import datetime
        if value and value < datetime.date.today():
            raise serializers.ValidationError(
                'License expiry date must be today or in the future'
            )
        return value
    
    def validate_consultation_fee(self, value):
        """Validate consultation fee"""
        if value is not None and value < 0:
            raise serializers.ValidationError('Consultation fee cannot be negative')
        return value
    
    def validate_consultation_duration(self, value):
        """Validate consultation duration"""
        if value and value < 5:
            raise serializers.ValidationError(
                'Consultation duration must be at least 5 minutes'
            )
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        issue_date = attrs.get('license_issue_date') or (
            self.instance.license_issue_date if self.instance else None
        )
        expiry_date = attrs.get('license_expiry_date') or (
            self.instance.license_expiry_date if self.instance else None
        )
        
        if issue_date and expiry_date:
            if expiry_date < issue_date:
                raise serializers.ValidationError({
                    'license_expiry_date': 'Expiry date must be after issue date'
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        DEPRECATED: Create doctor profile.
        Use apps.accounts.services.create_doctor_profile() instead.
        """
        specialty_ids = validated_data.pop('specialty_ids', [])

        doctor = DoctorProfile.objects.create(**validated_data)

        # Add specialties
        if specialty_ids:
            specialties = Specialty.objects.filter(id__in=specialty_ids)
            doctor.specialties.set(specialties)

        return doctor

    def update(self, instance, validated_data):
        """Update doctor profile"""
        specialty_ids = validated_data.pop('specialty_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update specialties if provided
        if specialty_ids is not None:
            specialties = Specialty.objects.filter(id__in=specialty_ids)
            instance.specialties.set(specialties)

        return instance


# =============================================================================
# DEPRECATED: DOCTOR REGISTRATION SERIALIZER
# =============================================================================
# This serializer is NO LONGER SUPPORTED with SuperAdmin authentication.
# Doctor users must be created in SuperAdmin first, then linked to profiles.
# Use apps.accounts.services.create_doctor_profile() instead.
# =============================================================================

class DoctorRegistrationSerializer(serializers.Serializer):
    """
    Serializer for doctor registration with user creation.
    Creates User + DoctorProfile in one transaction.
    """
    # User fields
    email = serializers.EmailField(required=True)
    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    phone = serializers.CharField(max_length=15, required=True)
    
    # Optional user fields
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        required=False,
        allow_null=True
    )
    address_line1 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, default='India')
    pincode = serializers.CharField(max_length=10, required=False, allow_blank=True)
    
    # Doctor Profile fields (REQUIRED)
    medical_license_number = serializers.CharField(max_length=64, required=True)
    license_issuing_authority = serializers.CharField(max_length=128, required=True)
    license_issue_date = serializers.DateField(required=True)
    license_expiry_date = serializers.DateField(required=True)
    qualifications = serializers.CharField(required=True)
    specialty_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    years_of_experience = serializers.IntegerField(default=0)
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    consultation_duration = serializers.IntegerField(default=30)
    is_available_online = serializers.BooleanField(default=True)
    is_available_offline = serializers.BooleanField(default=True)
    status = serializers.ChoiceField(
        choices=[('active', 'Active'), ('on_leave', 'On Leave'), ('inactive', 'Inactive')],
        default='active'
    )
    signature = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    languages_spoken = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_email(self, value):
        """DEPRECATED: Use SuperAdmin for user creation"""
        return value

    def validate_username(self, value):
        """DEPRECATED: Use SuperAdmin for user creation"""
        return value
    
    def validate_medical_license_number(self, value):
        """Check if license number already exists"""
        if DoctorProfile.objects.filter(medical_license_number=value).exists():
            raise serializers.ValidationError('Doctor with this license number already exists')
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Password confirmation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Passwords do not match'
            })
        
        # License dates validation
        if attrs['license_expiry_date'] < attrs['license_issue_date']:
            raise serializers.ValidationError({
                'license_expiry_date': 'Expiry date must be after issue date'
            })
        
        # License expiry date must be in future
        import datetime
        if attrs['license_expiry_date'] < datetime.date.today():
            raise serializers.ValidationError({
                'license_expiry_date': 'License expiry date must be in the future'
            })
        
        # Consultation duration validation
        if attrs['consultation_duration'] < 5:
            raise serializers.ValidationError({
                'consultation_duration': 'Consultation duration must be at least 5 minutes'
            })
        
        # Consultation fee validation
        if attrs['consultation_fee'] < 0:
            raise serializers.ValidationError({
                'consultation_fee': 'Consultation fee cannot be negative'
            })
        
        # Years of experience validation
        if attrs['years_of_experience'] < 0:
            raise serializers.ValidationError({
                'years_of_experience': 'Years of experience cannot be negative'
            })
        
        # Specialty validation
        specialty_ids = attrs.get('specialty_ids', [])
        if specialty_ids:
            existing_specialties = Specialty.objects.filter(id__in=specialty_ids).count()
            if existing_specialties != len(specialty_ids):
                raise serializers.ValidationError({
                    'specialty_ids': 'One or more specialty IDs are invalid'
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        DEPRECATED: This serializer is no longer supported.

        DigiHMS now uses SuperAdmin for authentication. To create a doctor:
        1. Create user in SuperAdmin first
        2. Use apps.accounts.services.create_doctor_profile() to link the profile
        """
        raise NotImplementedError(
            "DoctorRegistrationSerializer is deprecated. "
            "Use SuperAdmin to create users, then apps.accounts.services.create_doctor_profile() "
            "to create the doctor profile."
        )