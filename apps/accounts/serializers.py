"""
DigiHMS Accounts Serializers

Serializers for doctor profiles and specialties.
Authentication is handled by SuperAdmin - no local user serializers.
"""

from rest_framework import serializers
from apps.accounts.models import DoctorProfile, Specialty, DoctorAvailability


class SpecialtySerializer(serializers.ModelSerializer):
    """Serializer for medical specialties."""

    class Meta:
        model = Specialty
        fields = [
            'id', 'name', 'code', 'description', 'department',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant_id']


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for doctor availability schedules."""
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = DoctorAvailability
        fields = [
            'id', 'day_of_week', 'day_of_week_display', 'start_time', 'end_time',
            'is_available', 'max_appointments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant_id']


class DoctorProfileListSerializer(serializers.ModelSerializer):
    """
    Serializer for doctor profile list view.

    Lightweight serializer for listing doctors.
    """
    full_name = serializers.CharField(read_only=True)
    is_license_valid = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    specialties = SpecialtySerializer(many=True, read_only=True)

    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'medical_license_number', 'status', 'status_display',
            'specialties', 'years_of_experience', 'consultation_fee',
            'is_available_online', 'is_available_offline',
            'average_rating', 'total_consultations', 'is_license_valid'
        ]
        read_only_fields = [
            'id', 'user_id', 'email', 'tenant_id', 'last_synced_at',
            'average_rating', 'total_reviews', 'total_consultations'
        ]


class DoctorProfileDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for doctor profile detail view.

    Complete doctor information including availability.
    """
    full_name = serializers.CharField(read_only=True)
    is_license_valid = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    specialties = SpecialtySerializer(many=True, read_only=True)
    availability = DoctorAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'full_name',
            'tenant_id', 'medical_license_number', 'license_issuing_authority',
            'license_issue_date', 'license_expiry_date', 'is_license_valid',
            'qualifications', 'specialties', 'years_of_experience',
            'consultation_fee', 'follow_up_fee', 'consultation_duration',
            'is_available_online', 'is_available_offline',
            'status', 'status_display', 'average_rating', 'total_reviews',
            'total_consultations', 'signature', 'languages_spoken',
            'availability', 'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = [
            'id', 'user_id', 'email', 'tenant_id', 'last_synced_at',
            'average_rating', 'total_reviews', 'total_consultations'
        ]


class DoctorProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating doctor profiles.

    Used by staff with appropriate permissions to create or update doctor info.
    """
    specialty_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of specialty IDs to assign to doctor"
    )

    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name',
            'medical_license_number', 'license_issuing_authority',
            'license_issue_date', 'license_expiry_date',
            'qualifications', 'specialty_ids', 'years_of_experience',
            'consultation_fee', 'follow_up_fee', 'consultation_duration',
            'is_available_online', 'is_available_offline',
            'status', 'signature', 'languages_spoken'
        ]
        read_only_fields = ['id', 'tenant_id', 'last_synced_at']

    def validate_user_id(self, value):
        """Ensure user_id is not already linked to another doctor profile."""
        # Check if updating existing profile
        if self.instance:
            # Allow same user_id if it's the same doctor
            if self.instance.user_id == value:
                return value

        # Check if user_id is already used
        if DoctorProfile.objects.filter(user_id=value).exists():
            raise serializers.ValidationError(
                "This user already has a doctor profile."
            )

        return value

    def validate(self, attrs):
        """Validate license dates and other fields."""
        issue_date = attrs.get('license_issue_date')
        expiry_date = attrs.get('license_expiry_date')

        # If updating, get existing values if not provided
        if self.instance:
            issue_date = issue_date or self.instance.license_issue_date
            expiry_date = expiry_date or self.instance.license_expiry_date

        if issue_date and expiry_date:
            if expiry_date < issue_date:
                raise serializers.ValidationError({
                    'license_expiry_date': 'Expiry date must be after issue date.'
                })

        # Validate consultation fees
        consultation_fee = attrs.get('consultation_fee')
        if consultation_fee is not None and consultation_fee < 0:
            raise serializers.ValidationError({
                'consultation_fee': 'Consultation fee cannot be negative.'
            })

        follow_up_fee = attrs.get('follow_up_fee')
        if follow_up_fee is not None and follow_up_fee < 0:
            raise serializers.ValidationError({
                'follow_up_fee': 'Follow-up fee cannot be negative.'
            })

        # Validate consultation duration
        duration = attrs.get('consultation_duration')
        if duration and duration < 5:
            raise serializers.ValidationError({
                'consultation_duration': 'Consultation duration must be at least 5 minutes.'
            })

        return attrs

    def create(self, validated_data):
        """Create doctor profile with specialties."""
        specialty_ids = validated_data.pop('specialty_ids', [])

        doctor = DoctorProfile.objects.create(**validated_data)

        # Add specialties
        if specialty_ids:
            specialties = Specialty.objects.filter(id__in=specialty_ids)
            doctor.specialties.set(specialties)

        return doctor

    def update(self, instance, validated_data):
        """Update doctor profile with specialties."""
        specialty_ids = validated_data.pop('specialty_ids', None)

        # Update doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update specialties if provided
        if specialty_ids is not None:
            specialties = Specialty.objects.filter(id__in=specialty_ids)
            instance.specialties.set(specialties)

        return instance
