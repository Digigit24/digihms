from rest_framework import serializers
from .models import Appointment, AppointmentType
from django.contrib.auth import get_user_model
from apps.patients.serializers import PatientProfileListSerializer
from apps.doctors.serializers import DoctorProfileListSerializer

User = get_user_model()

class AppointmentTypeSerializer(serializers.ModelSerializer):
    """Serializer for AppointmentType"""
    class Meta:
        model = AppointmentType
        fields = '__all__'

class AppointmentListSerializer(serializers.ModelSerializer):
    """List view serializer for appointments"""
    patient = PatientProfileListSerializer(read_only=True)
    doctor = DoctorProfileListSerializer(read_only=True)
    appointment_type = serializers.StringRelatedField()
    
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display', 
        read_only=True
    )
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_id', 'patient', 'doctor', 
            'appointment_type', 'appointment_date', 'appointment_time', 
            'status', 'status_display', 'priority', 'priority_display',
            'consultation_fee', 'is_follow_up',
            'created_at', 'updated_at'
        ]

class AppointmentDetailSerializer(serializers.ModelSerializer):
    """Detail view serializer for appointments"""
    patient = PatientProfileListSerializer(read_only=True)
    doctor = DoctorProfileListSerializer(read_only=True)
    appointment_type = serializers.StringRelatedField()
    
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display', 
        read_only=True
    )
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', 
        read_only=True,
        allow_null=True
    )
    cancelled_by_name = serializers.CharField(
        source='cancelled_by.get_full_name', 
        read_only=True,
        allow_null=True
    )
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Appointment
        exclude = ['patient', 'doctor', 'appointment_type']
        read_only_fields = [
            'id', 'appointment_id', 
            'created_at', 'updated_at',
            'checked_in_at', 'actual_start_time', 
            'actual_end_time', 'waiting_time_minutes',
            'cancelled_at', 'approved_at'
        ]

class AppointmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Create/Update serializer for appointments"""
    patient_id = serializers.IntegerField(write_only=True)
    doctor_id = serializers.IntegerField(write_only=True)
    appointment_type_id = serializers.IntegerField(write_only=True)
    original_appointment_id = serializers.IntegerField(
        write_only=True, 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = Appointment
        exclude = [
            'patient', 'doctor', 'appointment_type', 
            'original_appointment', 
            'created_by', 'cancelled_by', 'approved_by'
        ]
    
    def validate(self, attrs):
        """Perform additional validation"""
        # Validate patient
        try:
            from apps.patients.models import PatientProfile
            patient = PatientProfile.objects.get(id=attrs['patient_id'])
            attrs['patient'] = patient
        except PatientProfile.DoesNotExist:
            raise serializers.ValidationError({'patient_id': 'Invalid patient ID'})
        
        # Validate doctor
        try:
            from apps.doctors.models import DoctorProfile
            doctor = DoctorProfile.objects.get(id=attrs['doctor_id'])
            attrs['doctor'] = doctor
        except DoctorProfile.DoesNotExist:
            raise serializers.ValidationError({'doctor_id': 'Invalid doctor ID'})
        
        # Validate appointment type
        try:
            appointment_type = AppointmentType.objects.get(id=attrs['appointment_type_id'])
            attrs['appointment_type'] = appointment_type
        except AppointmentType.DoesNotExist:
            raise serializers.ValidationError({'appointment_type_id': 'Invalid appointment type ID'})
        
        # Validate original appointment if follow-up
        if attrs.get('is_follow_up'):
            if not attrs.get('original_appointment_id'):
                raise serializers.ValidationError({
                    'original_appointment_id': 'Original appointment ID is required for follow-up'
                })
            try:
                original_appointment = Appointment.objects.get(id=attrs['original_appointment_id'])
                attrs['original_appointment'] = original_appointment
            except Appointment.DoesNotExist:
                raise serializers.ValidationError({
                    'original_appointment_id': 'Invalid original appointment ID'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Custom create method to set creator"""
        request = self.context.get('request')
        
        # Remove write-only fields
        validated_data.pop('patient_id', None)
        validated_data.pop('doctor_id', None)
        validated_data.pop('appointment_type_id', None)
        validated_data.pop('original_appointment_id', None)
        
        # Set creator
        if request and request.user:
            validated_data['created_by'] = request.user
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Custom update method"""
        # Remove write-only fields
        validated_data.pop('patient_id', None)
        validated_data.pop('doctor_id', None)
        validated_data.pop('appointment_type_id', None)
        validated_data.pop('original_appointment_id', None)
        
        return super().update(instance, validated_data)