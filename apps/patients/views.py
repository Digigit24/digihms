from django.db.models import Q, Avg, Sum
from django.utils import timezone

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import (
    extend_schema, extend_schema_view,
    OpenApiParameter, OpenApiExample, OpenApiResponse
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

# --------------------------------------------------------------------------------------
# Permission helper that maps DRF actions -> Django model permission codenames
# Adjust APP_LABEL if your app label isn't literally "patients".
# --------------------------------------------------------------------------------------
class ActionPermissions(BasePermission):
    APP_LABEL = 'patients'  # change if your app label differs

    action_map = {
        # Core CRUD
        'list':            [f'{APP_LABEL}.view_patientprofile'],
        'retrieve':        [f'{APP_LABEL}.view_patientprofile'],
        'create':          [f'{APP_LABEL}.add_patientprofile'],
        'update':          [f'{APP_LABEL}.change_patientprofile'],
        'partial_update':  [f'{APP_LABEL}.change_patientprofile'],
        'destroy':         [f'{APP_LABEL}.delete_patientprofile'],

        # Vitals
        'record_vitals':   [f'{APP_LABEL}.add_patientvitals'],
        'vitals':          [f'{APP_LABEL}.view_patientvitals'],

        # Allergies
        'add_allergy':     [f'{APP_LABEL}.add_patientallergy'],
        'allergies':       [f'{APP_LABEL}.view_patientallergy'],
        'update_allergy':  [f'{APP_LABEL}.change_patientallergy'],
        'delete_allergy':  [f'{APP_LABEL}.delete_patientallergy'],

        # Other
        'update_visit':    [f'{APP_LABEL}.change_patientprofile'],
        'statistics':      [f'{APP_LABEL}.view_patientprofile'],  # plus admin-group check in view
        'activate':        [f'{APP_LABEL}.change_patientprofile'], # plus admin-group check in view
        'mark_deceased':   [f'{APP_LABEL}.change_patientprofile'], # plus admin-group check in view
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        needed = self.action_map.get(getattr(view, 'action', None), [])
        return user.has_perms(needed) if needed else True


@extend_schema_view(
    list=extend_schema(
        summary="List patients",
        description="Get list of patient profiles with filtering, search and ordering.",
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
        description="Retrieve a complete patient profile with vitals and allergies.",
        tags=['Patients']
    ),
    create=extend_schema(
        summary="Register patient",
        description="Create a new patient profile (walk-in or registered user).",
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
        description="Update patient profile information.",
        tags=['Patients']
    ),
    partial_update=extend_schema(
        summary="Partial update patient profile",
        description="Partially update patient profile.",
        tags=['Patients']
    ),
    destroy=extend_schema(
        summary="Deactivate patient profile",
        description="Soft delete - set status to inactive (Admin only).",
        tags=['Patients']
    ),
)
class PatientProfileViewSet(viewsets.ModelViewSet):
    """
    Patient Profile Management: registration, profile CRUD, vitals, allergies, visits.
    """
    queryset = PatientProfile.objects.all()
    permission_classes = [IsAuthenticated, ActionPermissions]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'gender', 'blood_group', 'city', 'state']
    search_fields = ['patient_id', 'first_name', 'last_name', 'middle_name', 'mobile_primary', 'email']
    ordering_fields = ['registration_date', 'last_visit_date', 'age', 'total_visits', 'first_name', 'last_name']
    ordering = ['-registration_date']

    # ----- serializers -----
    def get_serializer_class(self):
        if self.action == 'list':
            return PatientProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientProfileCreateUpdateSerializer
        return PatientProfileDetailSerializer

    # ----- queryset scoping -----
    def get_queryset(self):
        qs = PatientProfile.objects.prefetch_related('vitals', 'allergies')
        user = self.request.user

        # Patients can only see their own profile
        if user.groups.filter(name='Patient').exists():
            if hasattr(user, 'patient_profile'):
                qs = qs.filter(id=user.patient_profile.id)
            else:
                return PatientProfile.objects.none()

        # age range
        age_min = self.request.query_params.get('age_min')
        age_max = self.request.query_params.get('age_max')
        if age_min:
            try: qs = qs.filter(age__gte=int(age_min))
            except ValueError: pass
        if age_max:
            try: qs = qs.filter(age__lte=int(age_max))
            except ValueError: pass

        # insurance
        has_insurance = self.request.query_params.get('has_insurance')
        if has_insurance:
            if has_insurance.lower() == 'true':
                qs = qs.filter(insurance_provider__isnull=False).exclude(insurance_provider='')
            else:
                qs = qs.filter(Q(insurance_provider__isnull=True) | Q(insurance_provider=''))

        # registration dates
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(registration_date__gte=date_from)
        if date_to:
            qs = qs.filter(registration_date__lte=date_to)

        return qs

    # ----- standard actions -----
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            s = self.get_serializer(page, many=True)
            return self.get_paginated_response(s.data)
        s = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': s.data})

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        # Patient self-view check
        if request.user.groups.filter(name='Patient').exists():
            if not hasattr(request.user, 'patient_profile') or obj.id != request.user.patient_profile.id:
                return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        s = self.get_serializer(obj)
        return Response({'success': True, 'data': s.data})

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        patient = s.save()
        return Response(
            {'success': True, 'message': 'Patient registered successfully',
             'data': PatientProfileDetailSerializer(patient).data},
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        obj = self.get_object()
        # Patient self-edit check
        if request.user.groups.filter(name='Patient').exists():
            if not hasattr(request.user, 'patient_profile') or obj.id != request.user.patient_profile.id:
                return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        s = self.get_serializer(obj, data=request.data, partial=partial, context={'request': request})
        s.is_valid(raise_exception=True)
        patient = s.save()
        return Response({'success': True, 'message': 'Patient profile updated successfully',
                         'data': PatientProfileDetailSerializer(patient).data})

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = 'inactive'  # soft-delete
        obj.save()
        return Response({'success': True, 'message': 'Patient profile deactivated successfully'},
                        status=status.HTTP_204_NO_CONTENT)

    # =========================
    # Custom Actions (Vitals)
    # =========================
    @extend_schema(
        summary="Record patient vitals",
        description="Record vital signs for a patient.",
        request=PatientVitalsCreateUpdateSerializer,
        responses={201: PatientVitalsSerializer, 400: OpenApiResponse(description="Validation error")},
        examples=[OpenApiExample('Vitals Example', value={
            'temperature': 98.6,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'heart_rate': 72,
            'respiratory_rate': 16,
            'oxygen_saturation': 98.5,
            'blood_glucose': 95.0,
            'notes': 'Normal vitals'
        }, request_only=True)],
        tags=['Vitals']
    )
    @action(detail=True, methods=['post'])
    def record_vitals(self, request, pk=None):
        patient = self.get_object()
        s = PatientVitalsCreateUpdateSerializer(data=request.data)
        if s.is_valid():
            s.save(patient=patient, recorded_by=request.user)
            return Response({'success': True, 'message': 'Vitals recorded successfully', 'data': s.data},
                            status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': s.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get patient vitals history",
        description="Retrieve a patient's vital signs history.",
        parameters=[OpenApiParameter(name='limit', type=int, description='Number of records (default 10)')],
        responses={200: PatientVitalsSerializer(many=True)},
        tags=['Vitals']
    )
    @action(detail=True, methods=['get'])
    def vitals(self, request, pk=None):
        patient = self.get_object()
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        items = patient.vitals.all()[:limit]
        s = PatientVitalsSerializer(items, many=True)
        return Response({'success': True, 'data': s.data})

    # =========================
    # Custom Actions (Allergies)
    # =========================
    @extend_schema(
        summary="Add patient allergy",
        description="Add a new allergy to a patient's record.",
        request=PatientAllergyCreateUpdateSerializer,
        responses={201: PatientAllergySerializer, 400: OpenApiResponse(description="Validation error")},
        examples=[OpenApiExample('Allergy Example', value={
            'allergy_type': 'drug',
            'allergen': 'Penicillin',
            'severity': 'severe',
            'symptoms': 'Skin rash, breathing difficulty',
            'treatment': 'Avoid penicillin-based medications',
            'is_active': True
        }, request_only=True)],
        tags=['Allergies']
    )
    @action(detail=True, methods=['post'])
    def add_allergy(self, request, pk=None):
        patient = self.get_object()
        s = PatientAllergyCreateUpdateSerializer(data=request.data)
        if s.is_valid():
            s.save(patient=patient, recorded_by=request.user)
            return Response({'success': True, 'message': 'Allergy added successfully', 'data': s.data},
                            status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': s.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get patient allergies",
        description="Retrieve a patient's allergy records.",
        parameters=[OpenApiParameter(name='active_only', type=bool, description='Only active (default true)')],
        responses={200: PatientAllergySerializer(many=True)},
        tags=['Allergies']
    )
    @action(detail=True, methods=['get'])
    def allergies(self, request, pk=None):
        patient = self.get_object()
        active_only = request.query_params.get('active_only', 'true')
        qs = patient.allergies.all()
        if str(active_only).lower() == 'true':
            qs = qs.filter(is_active=True)
        s = PatientAllergySerializer(qs, many=True)
        return Response({'success': True, 'data': s.data})

    @extend_schema(
        summary="Update patient allergy",
        description="Update a specific allergy record.",
        request=PatientAllergyCreateUpdateSerializer,
        responses={200: PatientAllergySerializer, 404: OpenApiResponse(description="Allergy not found")},
        tags=['Allergies']
    )
    @action(detail=True, methods=['put', 'patch'], url_path='allergies/(?P<allergy_id>[^/.]+)')
    def update_allergy(self, request, pk=None, allergy_id=None):
        patient = self.get_object()
        try:
            allergy = patient.allergies.get(id=allergy_id)
        except PatientAllergy.DoesNotExist:
            return Response({'success': False, 'error': 'Allergy not found'}, status=status.HTTP_404_NOT_FOUND)

        partial = request.method == 'PATCH'
        s = PatientAllergyCreateUpdateSerializer(allergy, data=request.data, partial=partial)
        if s.is_valid():
            s.save()
            return Response({'success': True, 'message': 'Allergy updated successfully', 'data': s.data})
        return Response({'success': False, 'errors': s.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete/deactivate patient allergy",
        description="Soft delete - set is_active to False.",
        responses={204: OpenApiResponse(description="Allergy deactivated"), 404: OpenApiResponse(description="Not found")},
        tags=['Allergies']
    )
    @action(detail=True, methods=['delete'], url_path='allergies/(?P<allergy_id>[^/.]+)')
    def delete_allergy(self, request, pk=None, allergy_id=None):
        patient = self.get_object()
        try:
            allergy = patient.allergies.get(id=allergy_id)
        except PatientAllergy.DoesNotExist:
            return Response({'success': False, 'error': 'Allergy not found'}, status=status.HTTP_404_NOT_FOUND)
        allergy.is_active = False
        allergy.save()
        return Response({'success': True, 'message': 'Allergy deactivated successfully'},
                        status=status.HTTP_204_NO_CONTENT)

    # =========================
    # Visits / Stats / Admin ops
    # =========================
    @extend_schema(
        summary="Record patient visit",
        description="Increment visit count and update last visit date.",
        request=None,
        responses={200: OpenApiResponse(description="Visit recorded")},
        tags=['Patients']
    )
    @action(detail=True, methods=['post'])
    def update_visit(self, request, pk=None):
        patient = self.get_object()
        patient.total_visits += 1
        patient.last_visit_date = timezone.now()
        patient.save()
        return Response({
            'success': True,
            'message': 'Visit recorded successfully',
            'data': {'total_visits': patient.total_visits, 'last_visit_date': patient.last_visit_date}
        })

    @extend_schema(
        summary="Get patient statistics",
        description="Statistical overview of all patients (Admin only).",
        responses={200: PatientStatisticsSerializer},
        tags=['Patients']
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        # Keep your strict admin requirement
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        total = PatientProfile.objects.count()
        active = PatientProfile.objects.filter(status='active').count()
        inactive = PatientProfile.objects.filter(status='inactive').count()
        deceased = PatientProfile.objects.filter(status='deceased').count()

        import datetime
        patients_with_insurance = PatientProfile.objects.filter(
            insurance_provider__isnull=False,
            insurance_expiry_date__gte=datetime.date.today()
        ).count()

        avg_age = PatientProfile.objects.aggregate(avg=Avg('age'))['avg'] or 0
        total_visits = PatientProfile.objects.aggregate(total=Sum('total_visits'))['total'] or 0

        gender_dist = {label: PatientProfile.objects.filter(gender=code).count()
                       for code, label in getattr(PatientProfile, 'GENDER_CHOICES', [])}

        blood_dist = {}
        for bg_code, _bg_label in getattr(PatientProfile, 'BLOOD_GROUP_CHOICES', []):
            c = PatientProfile.objects.filter(blood_group=bg_code).count()
            if c > 0:
                blood_dist[bg_code] = c

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

        s = PatientStatisticsSerializer(data)
        return Response({'success': True, 'data': s.data})

    @extend_schema(
        summary="Activate patient profile",
        description="Activate a patient profile (Admin only).",
        request=None,
        responses={200: PatientProfileDetailSerializer},
        tags=['Patients']
    )
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        patient = self.get_object()
        patient.status = 'active'
        patient.save()
        return Response({'success': True, 'message': 'Patient profile activated successfully',
                         'data': PatientProfileDetailSerializer(patient).data})

    @extend_schema(
        summary="Mark patient as deceased",
        description="Mark a patient as deceased (Admin only).",
        request=None,
        responses={200: PatientProfileDetailSerializer},
        tags=['Patients']
    )
    @action(detail=True, methods=['post'])
    def mark_deceased(self, request, pk=None):
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        patient = self.get_object()
        patient.status = 'deceased'
        patient.save()
        return Response({'success': True, 'message': 'Patient marked as deceased',
                         'data': PatientProfileDetailSerializer(patient).data})
