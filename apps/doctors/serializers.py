from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DoctorProfile, Specialty, DoctorAvailability
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class SpecialtySerializer(serializers.ModelSerializer):
    """Specialty serializer"""
    doctors_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Specialty
        fields = '__all__'
    
    def get_doctors_count(self, obj):
        return obj.doctors.filter(status='active').count()


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """Doctor availability serializer"""
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DoctorAvailability
        fields = [
            'id', 'day_of_week', 'day_display', 'start_time', 'end_time',
            'is_available', 'max_appointments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DoctorProfileListSerializer(serializers.ModelSerializer):
    """List view serializer for doctors - minimal fields"""
    user = UserSerializer(read_only=True)
    specialties = SpecialtySerializer(many=True, read_only=True)
    is_license_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'medical_license_number',
            'qualifications', 'specialties', 'years_of_experience',
            'consultation_fee', 'consultation_duration',
            'is_available_online', 'is_available_offline',
            'average_rating', 'total_reviews', 'total_consultations',
            'status', 'is_license_valid'
        ]


class DoctorProfileDetailSerializer(serializers.ModelSerializer):
    """Detail view serializer for doctors - all fields"""
    user = UserSerializer(read_only=True)
    specialties = SpecialtySerializer(many=True, read_only=True)
    availability = DoctorAvailabilitySerializer(many=True, read_only=True)
    is_license_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = DoctorProfile
        fields = '__all__'


class DoctorProfileCreateUpdateSerializer(serializers.ModelSerializer):
    """Create/Update serializer for doctors"""
    user_id = serializers.IntegerField(write_only=True)
    specialty_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = DoctorProfile
        exclude = ['user', 'average_rating', 'total_reviews', 
                   'total_consultations', 'specialties']
    
    def validate_user_id(self, value):
        """Validate user exists and doesn't have doctor profile"""
        try:
            user = User.objects.get(id=value)
            
            # Check if creating new profile
            if self.instance is None:
                if hasattr(user, 'doctor_profile'):
                    raise serializers.ValidationError(
                        'User already has a doctor profile'
                    )
                
                # Check if user is in Doctor group
                if not user.groups.filter(name='Doctor').exists():
                    raise serializers.ValidationError(
                        'User must be in Doctor group'
                    )
            
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found')
    
    def validate_license_expiry_date(self, value):
        """Ensure license expiry date is in the future"""
        import datetime
        if value <= datetime.date.today():
            raise serializers.ValidationError(
                'License expiry date must be in the future'
            )
        return value
    
    def validate(self, attrs):
        """Validate license dates"""
        issue_date = attrs.get('license_issue_date')
        expiry_date = attrs.get('license_expiry_date')
        
        if issue_date and expiry_date:
            if issue_date >= expiry_date:
                raise serializers.ValidationError({
                    'license_expiry_date': 'Expiry date must be after issue date'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create doctor profile"""
        user_id = validated_data.pop('user_id')
        specialty_ids = validated_data.pop('specialty_ids', [])
        
        user = User.objects.get(id=user_id)
        doctor = DoctorProfile.objects.create(
            user=user,
            **validated_data
        )
        
        # Add specialties
        if specialty_ids:
            specialties = Specialty.objects.filter(id__in=specialty_ids)
            doctor.specialties.set(specialties)
        
        return doctor
    
    def update(self, instance, validated_data):
        """Update doctor profile"""
        specialty_ids = validated_data.pop('specialty_ids', None)
        validated_data.pop('user_id', None)  # Don't allow user change
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update specialties if provided
        if specialty_ids is not None:
            specialties = Specialty.objects.filter(id__in=specialty_ids)
            instance.specialties.set(specialties)
        
        return instance


class DoctorAvailabilityCreateUpdateSerializer(serializers.ModelSerializer):
    """Create/Update serializer for doctor availability"""
    
    class Meta:
        model = DoctorAvailability
        exclude = ['doctor']
    
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