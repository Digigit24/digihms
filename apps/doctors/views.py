# apps/doctors/views.py

from django.db.models import Avg
from django.utils.timezone import now

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions

from django_filters.rest_framework import DjangoFilterBackend

# drf-spectacular
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
)

from .models import DoctorProfile, Specialty, DoctorAvailability
from .serializers import (
    DoctorProfileListSerializer,
    DoctorProfileDetailSerializer,
    DoctorProfileCreateUpdateSerializer,
    SpecialtySerializer,
    DoctorAvailabilitySerializer,
    DoctorAvailabilityCreateUpdateSerializer,
)


# -----------------------------
# Specialties
# -----------------------------
@extend_schema_view(
    list=extend_schema(
        summary="List specialties",
        description="Get list of all medical specialties (requires view permission).",
        parameters=[
            OpenApiParameter(name='is_active', type=bool, description='Filter by active status'),
            OpenApiParameter(name='department', type=str, description='Filter by department'),
            OpenApiParameter(name='search', type=str, description='Search by name, code, description'),
        ],
        tags=['Specialties'],
    ),
    retrieve=extend_schema(
        summary="Get specialty details",
        description="Retrieve a specialty by ID (requires view permission).",
        tags=['Specialties'],
    ),
    create=extend_schema(
        summary="Create specialty",
        description="Create a new medical specialty (requires add permission).",
        tags=['Specialties'],
    ),
    update=extend_schema(
        summary="Update specialty",
        description="Update a medical specialty (requires change permission).",
        tags=['Specialties'],
    ),
    partial_update=extend_schema(
        summary="Partial update specialty",
        description="Partially update a medical specialty (requires change permission).",
        tags=['Specialties'],
    ),
    destroy=extend_schema(
        summary="Delete specialty",
        description="Delete a medical specialty (requires delete permission). "
                    "Deletion is blocked if the specialty has active doctors.",
        tags=['Specialties'],
    ),
)
class SpecialtyViewSet(viewsets.ModelViewSet):
    """
    Medical Specialties Management

    Uses Django model permissions:
    - GET    list/retrieve  -> view_specialty
    - POST   create         -> add_specialty
    - PUT/PATCH update      -> change_specialty
    - DELETE destroy        -> delete_specialty
    """
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer

    # Auth + built-in model permissions only
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    # Filtering / search / ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'department']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': ser.data})

    def retrieve(self, request, *args, **kwargs):
        inst = self.get_object()
        ser = self.get_serializer(inst)
        return Response({'success': True, 'data': ser.data})

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        return Response(
            {'success': True, 'message': 'Specialty created successfully', 'data': ser.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        inst = self.get_object()
        ser = self.get_serializer(inst, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        self.perform_update(ser)
        return Response({'success': True, 'message': 'Specialty updated successfully', 'data': ser.data})

    def destroy(self, request, *args, **kwargs):
        inst = self.get_object()
        # Business rule: prevent delete if specialty has active doctors
        if inst.doctors.filter(status='active').exists():
            return Response(
                {'success': False, 'error': 'Cannot delete specialty with active doctors'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(inst)
        return Response(
            {'success': True, 'message': 'Specialty deleted successfully'},
            status=status.HTTP_204_NO_CONTENT,
        )


# -----------------------------
# Doctor Profiles
# -----------------------------
@extend_schema_view(
    list=extend_schema(
        summary="List doctors",
        description="List doctor profiles (requires view permission).",
        parameters=[
            OpenApiParameter(name='specialty', type=str, description='Filter by specialty name (icontains)'),
            OpenApiParameter(name='available', type=bool, description='Filter active doctors'),
            OpenApiParameter(name='city', type=str, description='Filter by user.city (if present on User model)'),
            OpenApiParameter(name='min_rating', type=float, description='Minimum average rating'),
            OpenApiParameter(name='min_fee', type=float, description='Minimum consultation fee'),
            OpenApiParameter(name='max_fee', type=float, description='Maximum consultation fee'),
            OpenApiParameter(name='search', type=str, description='Search by name, email, license, qualifications'),
        ],
        tags=['Doctors'],
    ),
    retrieve=extend_schema(
        summary="Get doctor details",
        description="Retrieve a doctor profile by ID (requires view permission).",
        tags=['Doctors'],
    ),
    create=extend_schema(
        summary="Create doctor profile",
        description="Create a doctor profile (requires add permission).",
        examples=[
            OpenApiExample(
                'Doctor Profile Example',
                value={
                    'user_id': 2,
                    'medical_license_number': 'MED123456',
                    'license_issuing_authority': 'Medical Council of India',
                    'license_issue_date': '2020-01-01',
                    'license_expiry_date': '2030-01-01',
                    'qualifications': 'MBBS, MD',
                    'specialty_ids': [1, 2],
                    'years_of_experience': 5,
                    'consultation_fee': 500.00,
                    'consultation_duration': 30,
                    'status': 'active',
                },
                request_only=True,
            ),
        ],
        tags=['Doctors'],
    ),
    update=extend_schema(
        summary="Update doctor profile",
        description="Update doctor profile (requires change permission, or will be allowed if the requester is the owner).",
        tags=['Doctors'],
    ),
    partial_update=extend_schema(
        summary="Partial update doctor profile",
        description="Partially update doctor profile (requires change permission, or will be allowed if the requester is the owner).",
        tags=['Doctors'],
    ),
    destroy=extend_schema(
        summary="Deactivate doctor profile",
        description="Soft delete (set status=inactive). Requires delete permission.",
        tags=['Doctors'],
    ),
)
class DoctorProfileViewSet(viewsets.ModelViewSet):
    """
    Doctor Profile Management

    Uses Django model permissions:
    - GET    list/retrieve  -> view_doctorprofile
    - POST   create         -> add_doctorprofile
    - PUT/PATCH update      -> change_doctorprofile (or owner shortcut)
    - DELETE destroy        -> delete_doctorprofile (soft-delete implemented)

    Notes:
    - We include an 'owner shortcut' for update/partial_update: if the requester is the linked user,
      we allow the change even if they don't hold the global change permission. This keeps a practical
      "self can edit" rule without any custom permission classes.
    - For other custom actions we check built-in perms by codename.
    """

    queryset = (
        DoctorProfile.objects.select_related('user')
        .prefetch_related('specialties', 'availability')
        .all()
    )

    # Auth + built-in model permissions only
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    # Filtering / search / ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_available_online', 'is_available_offline']
    search_fields = [
        'user__first_name',
        'user__last_name',
        'user__email',
        'medical_license_number',
        'qualifications',
    ]
    ordering_fields = ['created_at', 'consultation_fee', 'average_rating', 'years_of_experience']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DoctorProfileCreateUpdateSerializer
        return DoctorProfileDetailSerializer

    # ---- Queryset filtering by query params (pure business logic, not permissions) ----
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        specialty = params.get('specialty')
        if specialty:
            qs = qs.filter(specialties__name__icontains=specialty)

        available = params.get('available')
        if available and available.lower() == 'true':
            qs = qs.filter(status='active')

        city = params.get('city')  # only works if your User model has a 'city' field
        if city:
            qs = qs.filter(user__city__icontains=city)

        min_rating = params.get('min_rating')
        if min_rating:
            try:
                qs = qs.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass

        min_fee = params.get('min_fee')
        max_fee = params.get('max_fee')
        if min_fee:
            try:
                qs = qs.filter(consultation_fee__gte=float(min_fee))
            except ValueError:
                pass
        if max_fee:
            try:
                qs = qs.filter(consultation_fee__lte=float(max_fee))
            except ValueError:
                pass

        return qs.distinct()

    # ---- Standard actions with consistent API envelopes ----
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response({'success': True, 'data': ser.data})

    def retrieve(self, request, *args, **kwargs):
        inst = self.get_object()
        ser = self.get_serializer(inst)
        return Response({'success': True, 'data': ser.data})

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        doctor = ser.save()
        return Response(
            {
                'success': True,
                'message': 'Doctor profile created successfully',
                'data': DoctorProfileDetailSerializer(doctor).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _is_owner(self, request, instance: DoctorProfile) -> bool:
        return instance.user_id == getattr(request.user, 'id', None)

    def update(self, request, *args, **kwargs):
        """
        Allow update if:
        - user has global change permission for DoctorProfile, OR
        - user is the owner of this DoctorProfile (owner shortcut).
        """
        partial = kwargs.pop('partial', False)
        inst = self.get_object()

        # Check global change permission
        app_label = inst._meta.app_label
        change_perm = f'{app_label}.change_{inst._meta.model_name}'
        if not request.user.has_perm(change_perm) and not self._is_owner(request, inst):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        ser = self.get_serializer(inst, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        doctor = ser.save()
        return Response(
            {'success': True, 'message': 'Doctor profile updated successfully',
             'data': DoctorProfileDetailSerializer(doctor).data}
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete: requires delete permission on DoctorProfile.
        """
        inst = self.get_object()
        app_label = inst._meta.app_label
        delete_perm = f'{app_label}.delete_{inst._meta.model_name}'
        if not request.user.has_perm(delete_perm):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        inst.status = 'inactive'
        inst.save(update_fields=['status'])
        return Response({'success': True, 'message': 'Doctor profile deactivated successfully'},
                        status=status.HTTP_204_NO_CONTENT)

    # ---- Extra actions ----
    @extend_schema(
        summary="Get doctor availability",
        description="Get weekly availability for a doctor (requires view_doctoravailability OR view_doctorprofile).",
        responses={200: DoctorAvailabilitySerializer(many=True)},
        tags=['Doctors'],
    )
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        doctor = self.get_object()
        avail = doctor.availability.all()
        ser = DoctorAvailabilitySerializer(avail, many=True)
        return Response({'success': True, 'data': ser.data})

    @extend_schema(
        summary="Add availability slot",
        description=(
            "Add a new availability slot. Requires add_doctoravailability. "
            "If the requester is the owner of the profile, owner shortcut also allows it."
        ),
        request=DoctorAvailabilityCreateUpdateSerializer,
        responses={201: DoctorAvailabilitySerializer, 403: OpenApiResponse(description="Permission denied")},
        examples=[
            OpenApiExample(
                'Availability Example',
                value={
                    'day_of_week': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'is_available': True,
                    'max_appointments': 20,
                },
                request_only=True,
            ),
        ],
        tags=['Doctors'],
    )
    @action(detail=True, methods=['post'])
    def set_availability(self, request, pk=None):
        doctor = self.get_object()

        # Permission check: built-in add permission OR owner shortcut
        app_label = DoctorAvailability._meta.app_label
        add_perm = f'{app_label}.add_{DoctorAvailability._meta.model_name}'
        if not (request.user.has_perm(add_perm) or self._is_owner(request, doctor)):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        ser = DoctorAvailabilityCreateUpdateSerializer(data=request.data)
        if ser.is_valid():
            ser.save(doctor=doctor)
            return Response(
                {'success': True, 'message': 'Availability added successfully', 'data': ser.data},
                status=status.HTTP_201_CREATED,
            )
        return Response({'success': False, 'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Statistics",
        description="Basic doctor statistics. Requires view_doctorprofile.",
        responses={200: OpenApiResponse(description="Statistics object")},
        tags=['Doctors'],
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        # Require 'view' permission on DoctorProfile to access stats
        app_label = DoctorProfile._meta.app_label
        view_perm = f'{app_label}.view_{DoctorProfile._meta.model_name}'
        if not request.user.has_perm(view_perm):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        total = DoctorProfile.objects.count()
        active = DoctorProfile.objects.filter(status='active').count()
        on_leave = DoctorProfile.objects.filter(status='on_leave').count()
        inactive = DoctorProfile.objects.filter(status='inactive').count()

        avg_stats = DoctorProfile.objects.aggregate(
            avg_rating=Avg('average_rating'),
            avg_experience=Avg('years_of_experience'),
            avg_fee=Avg('consultation_fee'),
        )

        return Response({
            'success': True,
            'data': {
                'total_doctors': total,
                'active_doctors': active,
                'on_leave_doctors': on_leave,
                'inactive_doctors': inactive,
                'average_rating': round(float(avg_stats['avg_rating'] or 0), 2),
                'average_experience': round(float(avg_stats['avg_experience'] or 0), 1),
                'average_consultation_fee': round(float(avg_stats['avg_fee'] or 0), 2),
                'generated_at': now().isoformat(),
            }
        })

    @extend_schema(
        summary="Activate doctor profile",
        description="Activate a doctor profile. Requires change_doctorprofile.",
        request=None,
        responses={200: DoctorProfileDetailSerializer},
        tags=['Doctors'],
    )
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        doctor = self.get_object()
        app_label = doctor._meta.app_label
        change_perm = f'{app_label}.change_{doctor._meta.model_name}'
        if not request.user.has_perm(change_perm):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        doctor.status = 'active'
        doctor.save(update_fields=['status'])
        return Response({
            'success': True,
            'message': 'Doctor profile activated successfully',
            'data': DoctorProfileDetailSerializer(doctor).data,
        })

    @extend_schema(
        summary="Deactivate doctor profile",
        description="Deactivate a doctor profile. Requires change_doctorprofile.",
        request=None,
        responses={200: DoctorProfileDetailSerializer},
        tags=['Doctors'],
    )
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        doctor = self.get_object()
        app_label = doctor._meta.app_label
        change_perm = f'{app_label}.change_{doctor._meta.model_name}'
        if not request.user.has_perm(change_perm):
            return Response({'success': False, 'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        doctor.status = 'inactive'
        doctor.save(update_fields=['status'])
        return Response({
            'success': True,
            'message': 'Doctor profile deactivated successfully',
            'data': DoctorProfileDetailSerializer(doctor).data,
        })


# Note: URL routing is handled in apps/doctors/urls.py using DefaultRouter to register the viewsets.