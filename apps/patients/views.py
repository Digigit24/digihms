from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone

# ✅ Import drf-spectacular decorators
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse
)

from .models import PatientProfile, PatientVitals, PatientAllergy
from .serializers import (
    PatientProfileListSerializer,
    PatientProfileDetailSerializer,
    PatientProfileCreateUpdateSerializer,
    PatientVitalsSerializer,
    PatientVitalsCreateUpdateSerializer,
    PatientAllergySerializer,
    PatientAllergyCreateUpdateSerializer,
    PatientStatisticsSerializer
)
from apps.accounts.permissions import (
    IsAdministrator, IsDoctor, IsReceptionist, IsNurse
)


@extend_schema_view(
    list=extend_schema(
        summary="List patients",
        description="Get list of patient profiles with extensive filtering options",
        parameters=[
            OpenApiParameter(name='status', type=str, description='Filter by status'),
            OpenApiParameter(name='gender', type=str, description='Filter by gender'),
            OpenApiParameter(name='blood_group', type=str, description='Filter by blood group'),
            OpenApiParameter(name='city', type=str, description='Filter by city'),
            OpenApiParameter(name='age_min', type=int, description='Minimum age'),
            OpenApiParameter(name='age_max', type=int, description='Maximum age'),
            OpenApiParameter(name='has_insurance', type=bool, description='Filter by insurance status'),
            OpenApiParameter(name='date_from', type=str, description='Registration date from (YYYY-MM-DD)'),
            OpenApiParameter(name='date_to', type=str, description='Registration date to (YYYY-MM-DD)'),
            OpenApiParameter(name='search', type=str, description='Search by name, patient ID, or phone'),
        ],
        tags=['Patients']
    ),
    retrieve=extend_schema(
        summary="Get patient details",
        description="Retrieve complete patient profile with vitals and allergies",
        tags=['Patients']
    ),
    create=extend_schema(
        summary="Register patient",
        description="Create a new patient profile (Walk-in or registered user)",
        examples=[
            OpenApiExample(
                'Patient Registration Example',
                value={
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'date_of_birth': '1990-01-15',
                    'gender': 'male',
                    'mobile_primary': '+919876543210',
                    'email': 'john.doe@example.com',
                    'address_line1': '123 Main Street',
                    'city': 'Mumbai',
                    'state': 'Maharashtra',
                    'country': 'India',
                    'pincode': '400001',
                    'blood_group': 'O+',
                    'height': 175.5,
                    'weight': 70.0,
                    'emergency_contact_name': 'Jane Doe',
                    'emergency_contact_phone': '+919876543211',
                    'emergency_contact_relation': 'Spouse'
                },
                request_only=True,
            ),
        ],
        tags=['Patients']
    ),
    update=extend_schema(
        summary="Update patient profile",
        description="Update patient profile information",
        tags=['Patients']
    ),
    partial_update=extend_schema(
        summary="Partial update patient profile",
        description="Partially update patient profile",
        tags=['Patients']
    ),
    destroy=extend_schema(
        summary="Deactivate patient profile",
        description="Soft delete - deactivate patient profile (Admin only)",
        tags=['Patients']
    ),
)
class PatientProfileViewSet(viewsets.ModelViewSet):
    """
    Patient Profile Management
    
    Complete patient management including:
    - Patient registration (walk-in or registered users)
    - Profile management
    - Vitals tracking
    - Allergy management
    - Visit tracking
    """
    queryset = PatientProfile.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'gender', 'blood_group', 'city', 'state']
    search_fields = [
        'patient_id', 'first_name', 'last_name', 'middle_name',
        'mobile_primary', 'email'
    ]
    ordering_fields = [
        'registration_date', 'last_visit_date', 'age',
        'total_visits', 'first_name', 'last_name'
    ]
    ordering = ['-registration_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return PatientProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientProfileCreateUpdateSerializer
        return PatientProfileDetailSerializer
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        elif self.action == 'create':
            # Receptionists, Doctors, Nurses, Admins can create
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update']:
            # Receptionists, Doctors, Admins can update
            return [IsAuthenticated()]
        elif self.action == 'destroy':
            return [IsAdministrator()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role and query params"""
        queryset = PatientProfile.objects.prefetch_related(
            'vitals', 'allergies'
        )
        
        user = self.request.user
        
        # Patients can only see their own profile
        if user.groups.filter(name='Patient').exists():
            if hasattr(user, 'patient_profile'):
                queryset = queryset.filter(id=user.patient_profile.id)
            else:
                queryset = queryset.none()
        
        # Filter by age range
        age_min = self.request.query_params.get('age_min')
        age_max = self.request.query_params.get('age_max')
        if age_min:
            try:
                queryset = queryset.filter(age__gte=int(age_min))
            except ValueError:
                pass
        if age_max:
            try:
                queryset = queryset.filter(age__lte=int(age_max))
            except ValueError:
                pass
        
        # Filter by insurance status
        has_insurance = self.request.query_params.get('has_insurance')
        if has_insurance:
            if has_insurance.lower() == 'true':
                queryset = queryset.filter(
                    insurance_provider__isnull=False
                ).exclude(insurance_provider='')
            else:
                queryset = queryset.filter(
                    Q(insurance_provider__isnull=True) | 
                    Q(insurance_provider='')
                )
        
        # Filter by registration date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(registration_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(registration_date__lte=date_to)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Patients can only view their own profile
        if request.user.groups.filter(name='Patient').exists():
            if not hasattr(request.user, 'patient_profile') or \
               instance.id != request.user.patient_profile.id:
                return Response({
                    'success': False,
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Patient registered successfully',
            'data': PatientProfileDetailSerializer(patient).data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check permission
        if request.user.groups.filter(name='Patient').exists():
            if not hasattr(request.user, 'patient_profile') or \
               instance.id != request.user.patient_profile.id:
                return Response({
                    'success': False,
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Patient profile updated successfully',
            'data': PatientProfileDetailSerializer(patient).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Soft delete - set status to inactive
        instance.status = 'inactive'
        instance.save()
        
        return Response({
            'success': True,
            'message': 'Patient profile deactivated successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    

# ============================================
    # CUSTOM ACTIONS - ADD THESE TO PatientProfileViewSet CLASS
    # ============================================
    
    @extend_schema(
        summary="Record patient vitals",
        description="Record vital signs for a patient",
        request=PatientVitalsCreateUpdateSerializer,
        responses={
            201: PatientVitalsSerializer,
            400: OpenApiResponse(description="Validation error")
        },
        examples=[
            OpenApiExample(
                'Vitals Example',
                value={
                    'temperature': 98.6,
                    'blood_pressure_systolic': 120,
                    'blood_pressure_diastolic': 80,
                    'heart_rate': 72,
                    'respiratory_rate': 16,
                    'oxygen_saturation': 98.5,
                    'blood_glucose': 95.0,
                    'notes': 'Normal vitals'
                },
                request_only=True,
            ),
        ],
        tags=['Vitals']
    )
    @action(detail=True, methods=['post'])
    def record_vitals(self, request, pk=None):
        """Record patient vitals"""
        patient = self.get_object()
        
        serializer = PatientVitalsCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                patient=patient,
                recorded_by=request.user
            )
            return Response({
                'success': True,
                'message': 'Vitals recorded successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get patient vitals history",
        description="Retrieve patient's vital signs history",
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                description='Number of records to return (default: 10)',
                required=False
            ),
        ],
        responses={200: PatientVitalsSerializer(many=True)},
        tags=['Vitals']
    )
    @action(detail=True, methods=['get'])
    def vitals(self, request, pk=None):
        """Get patient vitals history"""
        patient = self.get_object()
        
        # Get query params for filtering
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        
        vitals = patient.vitals.all()[:limit]
        serializer = PatientVitalsSerializer(vitals, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @extend_schema(
        summary="Add patient allergy",
        description="Add a new allergy to patient's record",
        request=PatientAllergyCreateUpdateSerializer,
        responses={
            201: PatientAllergySerializer,
            400: OpenApiResponse(description="Validation error")
        },
        examples=[
            OpenApiExample(
                'Allergy Example',
                value={
                    'allergy_type': 'drug',
                    'allergen': 'Penicillin',
                    'severity': 'severe',
                    'symptoms': 'Skin rash, breathing difficulty',
                    'treatment': 'Avoid penicillin-based medications',
                    'is_active': True
                },
                request_only=True,
            ),
        ],
        tags=['Allergies']
    )
    @action(detail=True, methods=['post'])
    def add_allergy(self, request, pk=None):
        """Add patient allergy"""
        patient = self.get_object()
        
        serializer = PatientAllergyCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                patient=patient,
                recorded_by=request.user
            )
            return Response({
                'success': True,
                'message': 'Allergy added successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get patient allergies",
        description="Retrieve patient's allergy records",
        parameters=[
            OpenApiParameter(
                name='active_only',
                type=bool,
                description='Show only active allergies (default: true)',
                required=False
            ),
        ],
        responses={200: PatientAllergySerializer(many=True)},
        tags=['Allergies']
    )
    @action(detail=True, methods=['get'])
    def allergies(self, request, pk=None):
        """Get patient allergies"""
        patient = self.get_object()
        
        # Filter active allergies by default
        active_only = request.query_params.get('active_only', 'true')
        allergies = patient.allergies.all()
        
        if active_only.lower() == 'true':
            allergies = allergies.filter(is_active=True)
        
        serializer = PatientAllergySerializer(allergies, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @extend_schema(
        summary="Update patient allergy",
        description="Update a specific allergy record",
        request=PatientAllergyCreateUpdateSerializer,
        responses={
            200: PatientAllergySerializer,
            404: OpenApiResponse(description="Allergy not found")
        },
        tags=['Allergies']
    )
    @action(detail=True, methods=['put', 'patch'], url_path='allergies/(?P<allergy_id>[^/.]+)')
    def update_allergy(self, request, pk=None, allergy_id=None):
        """Update specific allergy"""
        patient = self.get_object()
        
        try:
            allergy = patient.allergies.get(id=allergy_id)
        except PatientAllergy.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Allergy not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        partial = request.method == 'PATCH'
        serializer = PatientAllergyCreateUpdateSerializer(
            allergy, data=request.data, partial=partial
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Allergy updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Delete/deactivate patient allergy",
        description="Soft delete - deactivate an allergy record",
        responses={
            204: OpenApiResponse(description="Allergy deactivated"),
            404: OpenApiResponse(description="Allergy not found")
        },
        tags=['Allergies']
    )
    @action(detail=True, methods=['delete'], url_path='allergies/(?P<allergy_id>[^/.]+)')
    def delete_allergy(self, request, pk=None, allergy_id=None):
        """Delete/deactivate specific allergy"""
        patient = self.get_object()
        
        try:
            allergy = patient.allergies.get(id=allergy_id)
            # Soft delete - set is_active to False
            allergy.is_active = False
            allergy.save()
            
            return Response({
                'success': True,
                'message': 'Allergy deactivated successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except PatientAllergy.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Allergy not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        summary="Record patient visit",
        description="Increment visit count and update last visit date",
        request=None,
        responses={200: OpenApiResponse(description="Visit recorded")},
        tags=['Patients']
    )
    @action(detail=True, methods=['post'])
    def update_visit(self, request, pk=None):
        """Increment visit count and update last visit date"""
        patient = self.get_object()
        
        patient.total_visits += 1
        patient.last_visit_date = timezone.now()
        patient.save()
        
        return Response({
            'success': True,
            'message': 'Visit recorded successfully',
            'data': {
                'total_visits': patient.total_visits,
                'last_visit_date': patient.last_visit_date
            }
        })
    
    @extend_schema(
        summary="Get patient statistics",
        description="Get statistical overview of all patients (Admin only)",
        responses={200: PatientStatisticsSerializer},
        tags=['Patients']
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get patient statistics (Admin only)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        total = PatientProfile.objects.count()
        active = PatientProfile.objects.filter(status='active').count()
        inactive = PatientProfile.objects.filter(status='inactive').count()
        deceased = PatientProfile.objects.filter(status='deceased').count()
        
        # Patients with valid insurance
        import datetime
        patients_with_insurance = PatientProfile.objects.filter(
            insurance_provider__isnull=False,
            insurance_expiry_date__gte=datetime.date.today()
        ).count()
        
        # Average age
        avg_age = PatientProfile.objects.aggregate(
            avg=Avg('age')
        )['avg'] or 0
        
        # Total visits
        total_visits = PatientProfile.objects.aggregate(
            total=Sum('total_visits')
        )['total'] or 0
        
        # Gender distribution
        gender_dist = {}
        for gender in PatientProfile.GENDER_CHOICES:
            count = PatientProfile.objects.filter(gender=gender[0]).count()
            gender_dist[gender[1]] = count
        
        # Blood group distribution
        blood_dist = {}
        for bg in PatientProfile.BLOOD_GROUP_CHOICES:
            count = PatientProfile.objects.filter(blood_group=bg[0]).count()
            if count > 0:
                blood_dist[bg[0]] = count
        
        data = {
            'total_patients': total,
            'active_patients': active,
            'inactive_patients': inactive,
            'deceased_patients': deceased,
            'patients_with_insurance': patients_with_insurance,
            'average_age': round(avg_age, 1),
            'total_visits': total_visits,
            'gender_distribution': gender_dist,
            'blood_group_distribution': blood_dist
        }
        
        serializer = PatientStatisticsSerializer(data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @extend_schema(
        summary="Activate patient profile",
        description="Activate a patient profile (Admin only)",
        request=None,
        responses={200: PatientProfileDetailSerializer},
        tags=['Patients']
    )
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate patient profile (Admin only)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient = self.get_object()
        patient.status = 'active'
        patient.save()
        
        return Response({
            'success': True,
            'message': 'Patient profile activated successfully',
            'data': PatientProfileDetailSerializer(patient).data
        })
    
    @extend_schema(
        summary="Mark patient as deceased",
        description="Mark a patient as deceased (Admin only)",
        request=None,
        responses={200: PatientProfileDetailSerializer},
        tags=['Patients']
    )
    @action(detail=True, methods=['post'])
    def mark_deceased(self, request, pk=None):
        """Mark patient as deceased (Admin only)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient = self.get_object()
        patient.status = 'deceased'
        patient.save()
        
        return Response({
            'success': True,
            'message': 'Patient marked as deceased',
            'data': PatientProfileDetailSerializer(patient).data
        })