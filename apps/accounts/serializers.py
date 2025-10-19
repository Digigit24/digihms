from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Group
from django.db import transaction

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer with role info and profiles"""
    role = serializers.CharField(read_only=True)
    groups = serializers.StringRelatedField(many=True, read_only=True)
    full_address = serializers.CharField(read_only=True)
    
    # Profile indicators
    has_doctor_profile = serializers.SerializerMethodField()
    has_patient_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'phone', 'alternate_phone', 'date_of_birth', 'gender',
            'address_line1', 'address_line2', 'city', 'state',
            'country', 'pincode', 'full_address', 'profile_picture',
            'bio', 'employee_id', 'department', 'joining_date',
            'is_verified', 'is_active', 'role', 'groups',
            'has_doctor_profile', 'has_patient_profile',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_has_doctor_profile(self, obj):
        return hasattr(obj, 'doctor_profile')
    
    def get_has_patient_profile(self, obj):
        return hasattr(obj, 'patient_profile')


class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(
            username=email,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError('Invalid credentials')
        
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled')
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password': 'Passwords do not match'
            })
        return attrs


# ============================================
# NESTED PROFILE SERIALIZERS
# ============================================

class DoctorProfileNestedSerializer(serializers.Serializer):
    """Nested serializer for doctor profile creation"""
    medical_license_number = serializers.CharField(max_length=64, required=True)
    license_issuing_authority = serializers.CharField(max_length=128, required=False, allow_blank=True)
    license_issue_date = serializers.DateField(required=False, allow_null=True)
    license_expiry_date = serializers.DateField(required=False, allow_null=True)
    qualifications = serializers.CharField(required=False, allow_blank=True)
    specialty_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    years_of_experience = serializers.IntegerField(default=0)
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    consultation_duration = serializers.IntegerField(default=15)
    is_available_online = serializers.BooleanField(default=False)
    is_available_offline = serializers.BooleanField(default=True)
    signature = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    languages_spoken = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate(self, attrs):
        """Validate license dates"""
        issue_date = attrs.get('license_issue_date')
        expiry_date = attrs.get('license_expiry_date')
        
        if issue_date and expiry_date:
            if expiry_date < issue_date:
                raise serializers.ValidationError({
                    'license_expiry_date': 'Expiry date must be after issue date'
                })
        
        return attrs


class PatientProfileNestedSerializer(serializers.Serializer):
    """Nested serializer for patient profile creation"""
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=True)
    gender = serializers.ChoiceField(choices=['male', 'female', 'other'], required=True)
    
    mobile_primary = serializers.CharField(max_length=15, required=True)
    mobile_secondary = serializers.CharField(max_length=15, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    
    address_line1 = serializers.CharField(max_length=200, required=True)
    address_line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=True)
    state = serializers.CharField(max_length=100, required=True)
    country = serializers.CharField(max_length=100, default='India')
    pincode = serializers.CharField(max_length=10, required=True)
    
    blood_group = serializers.ChoiceField(
        choices=['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        required=False,
        allow_blank=True,
        allow_null=True
    )
    height = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    weight = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    
    marital_status = serializers.ChoiceField(
        choices=['single', 'married', 'divorced', 'widowed'],
        default='single'
    )
    occupation = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    emergency_contact_name = serializers.CharField(max_length=100, required=True)
    emergency_contact_phone = serializers.CharField(max_length=15, required=True)
    emergency_contact_relation = serializers.CharField(max_length=50, required=True)
    
    insurance_provider = serializers.CharField(max_length=200, required=False, allow_blank=True)
    insurance_policy_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    insurance_expiry_date = serializers.DateField(required=False, allow_null=True)
    
    def validate_date_of_birth(self, value):
        """Ensure date of birth is in the past"""
        import datetime
        if value > datetime.date.today():
            raise serializers.ValidationError('Date of birth cannot be in the future')
        return value


class UserCreateWithProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user creation with optional profile attachment
    
    Supports creating:
    1. User only (no profile) - for staff roles
    2. User + Doctor Profile
    3. User + Patient Profile
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.CharField(write_only=True, required=True)
    
    # Optional nested profiles
    doctor_profile = DoctorProfileNestedSerializer(write_only=True, required=False)
    patient_profile = PatientProfileNestedSerializer(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'role',
            'doctor_profile', 'patient_profile'
        ]
    
    def validate(self, attrs):
        """Validate passwords match and role consistency"""
        # Password validation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Passwords do not match'
            })
        attrs.pop('password_confirm')
        
        # Role validation
        role = attrs.get('role')
        doctor_profile = attrs.get('doctor_profile')
        patient_profile = attrs.get('patient_profile')
        
        # Check if role matches profile
        if role == 'Doctor' and not doctor_profile:
            raise serializers.ValidationError({
                'doctor_profile': 'Doctor profile is required for Doctor role'
            })
        
        if role == 'Patient' and not patient_profile:
            raise serializers.ValidationError({
                'patient_profile': 'Patient profile is required for Patient role'
            })
        
        # Cannot have both profiles
        if doctor_profile and patient_profile:
            raise serializers.ValidationError(
                'Cannot create both doctor and patient profiles simultaneously'
            )
        
        # Non-doctor/patient roles should not have profiles
        if role not in ['Doctor', 'Patient'] and (doctor_profile or patient_profile):
            raise serializers.ValidationError(
                f'{role} role cannot have doctor or patient profile'
            )
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """Create user and associated profile"""
        from apps.doctors.models import DoctorProfile, Specialty
        from apps.patients.models import PatientProfile
        
        # Extract profile data
        role = validated_data.pop('role')
        doctor_profile_data = validated_data.pop('doctor_profile', None)
        patient_profile_data = validated_data.pop('patient_profile', None)
        password = validated_data.pop('password')
        
        # Create user
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Assign to group
        try:
            group = Group.objects.get(name=role)
            user.groups.add(group)
        except Group.DoesNotExist:
            raise serializers.ValidationError(f'Role "{role}" does not exist')
        
        # Create Doctor Profile if provided
        if doctor_profile_data:
            specialty_ids = doctor_profile_data.pop('specialty_ids', [])
            
            doctor_profile = DoctorProfile.objects.create(
                user=user,
                **doctor_profile_data
            )
            
            # Add specialties
            if specialty_ids:
                specialties = Specialty.objects.filter(id__in=specialty_ids)
                doctor_profile.specialties.set(specialties)
        
        # Create Patient Profile if provided
        if patient_profile_data:
            # Get request context for created_by
            request = self.context.get('request')
            created_by = request.user if request and request.user.is_authenticated else None
            
            PatientProfile.objects.create(
                user=user,
                created_by=created_by,
                **patient_profile_data
            )
        
        return user