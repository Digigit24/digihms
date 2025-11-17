"""
DigiHMS Accounts Views

ViewSets for managing doctor profiles and specialties.
Authentication is handled by SuperAdmin - no local auth views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from common.permissions import PermissionMixin, HMSPermissions
from common.mixins import TenantViewSetMixin
from apps.accounts.models import DoctorProfile, Specialty, DoctorAvailability
from apps.accounts.serializers import (
    DoctorProfileListSerializer,
    DoctorProfileDetailSerializer,
    DoctorProfileCreateUpdateSerializer,
    SpecialtySerializer,
    DoctorAvailabilitySerializer
)
from apps.accounts.services import sync_doctor_from_jwt


@extend_schema_view(
    list=extend_schema(
        summary="List specialties",
        description="Get list of medical specialties",
        tags=['Specialties']
    ),
    retrieve=extend_schema(
        summary="Get specialty details",
        description="Retrieve detailed information about a specific specialty",
        tags=['Specialties']
    ),
    create=extend_schema(
        summary="Create specialty",
        description="Create a new medical specialty",
        tags=['Specialties']
    ),
    update=extend_schema(
        summary="Update specialty",
        description="Update a medical specialty",
        tags=['Specialties']
    ),
    destroy=extend_schema(
        summary="Delete specialty",
        description="Delete a medical specialty",
        tags=['Specialties']
    ),
)
class SpecialtyViewSet(TenantViewSetMixin, PermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing medical specialties.

    Provides CRUD operations for specialties used by doctors.
    """
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer

    permission_mapping = {
        'list': HMSPermissions.DOCTORS_VIEW,
        'retrieve': HMSPermissions.DOCTORS_VIEW,
        'create': HMSPermissions.DOCTORS_CREATE,
        'update': HMSPermissions.DOCTORS_EDIT,
        'partial_update': HMSPermissions.DOCTORS_EDIT,
        'destroy': HMSPermissions.DOCTORS_DELETE,
    }

    owner_field = 'tenant_id'

    def get_queryset(self):
        """Filter specialties by tenant and active status."""
        queryset = super().get_queryset()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset.order_by('name')


# ==================== User Management ViewSet ====================

@extend_schema_view(
    list=extend_schema(
        summary="List doctor profiles",
        description="Get list of doctor profiles with optional filters",
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                description='Filter by status (active, on_leave, inactive)'
            ),
            OpenApiParameter(
                name='specialty',
                type=int,
                description='Filter by specialty ID'
            ),
            OpenApiParameter(
                name='search',
                type=str,
                description='Search by name, email, or license number'
            ),
        ],
        tags=['Doctors']
    ),
    retrieve=extend_schema(
        summary="Get doctor profile",
        description="Retrieve detailed doctor profile information",
        tags=['Doctors']
    ),
    create=extend_schema(
        summary="Create doctor profile",
        description="Create a new doctor profile for a SuperAdmin user",
        tags=['Doctors']
    ),
    update=extend_schema(
        summary="Update doctor profile",
        description="Update doctor profile information",
        tags=['Doctors']
    ),
    partial_update=extend_schema(
        summary="Partial update doctor profile",
        description="Partially update doctor profile information",
        tags=['Doctors']
    ),
    destroy=extend_schema(
        summary="Delete doctor profile",
        description="Delete a doctor profile",
        tags=['Doctors']
    ),
)
class DoctorProfileViewSet(TenantViewSetMixin, PermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing doctor profiles.

    Provides CRUD operations for doctor profiles linked to SuperAdmin users.
    """
    queryset = DoctorProfile.objects.all().select_related().prefetch_related('specialties')

    permission_mapping = {
        'list': HMSPermissions.DOCTORS_VIEW,
        'retrieve': HMSPermissions.DOCTORS_VIEW,
        'create': HMSPermissions.DOCTORS_CREATE,
        'update': HMSPermissions.DOCTORS_EDIT,
        'partial_update': HMSPermissions.DOCTORS_EDIT,
        'destroy': HMSPermissions.DOCTORS_DELETE,
        'me': None,  # No permission check - own profile
        'sync_from_jwt': None,  # No permission check - own profile sync
    }

    owner_field = 'tenant_id'

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DoctorProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DoctorProfileCreateUpdateSerializer
        return DoctorProfileDetailSerializer

    def get_queryset(self):
        """
        Get queryset with permission-based filtering and search.
        """
        queryset = super().get_queryset()

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(medical_license_number__icontains=search)
            )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by specialty
        specialty_id = self.request.query_params.get('specialty')
        if specialty_id:
            queryset = queryset.filter(specialties__id=specialty_id)

        return queryset.distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """Create doctor profile with auto-set tenant_id."""
        serializer.save(tenant_id=self.request.tenant_id)

    @extend_schema(
        summary="Get current user's doctor profile",
        description="Retrieve doctor profile for the currently authenticated user",
        responses={
            200: DoctorProfileDetailSerializer,
            404: {'description': 'Doctor profile not found for current user'}
        },
        tags=['Doctors']
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get doctor profile for the current user.

        Returns the doctor profile associated with the authenticated user's user_id.
        """
        try:
            doctor = DoctorProfile.objects.select_related().prefetch_related(
                'specialties', 'availability'
            ).get(
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )

            serializer = DoctorProfileDetailSerializer(doctor)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except DoctorProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Doctor profile not found for current user'
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Sync doctor profile from JWT",
        description="Update doctor profile cached user data from JWT token",
        responses={
            200: DoctorProfileDetailSerializer,
            404: {'description': 'Doctor profile not found'}
        },
        tags=['Doctors']
    )
    @action(detail=False, methods=['post'])
    def sync_from_jwt(self, request):
        """
        Sync doctor profile data from JWT payload.

        Updates cached user information (email, first_name, last_name) from JWT.
        """
        # Build user payload from request (set by JWT middleware)
        user_payload = {
            'email': request.email,
            'first_name': getattr(request, 'first_name', ''),
            'last_name': getattr(request, 'last_name', ''),
        }

        doctor = sync_doctor_from_jwt(request.user_id, user_payload)

        if doctor:
            serializer = DoctorProfileDetailSerializer(doctor)
            return Response({
                'success': True,
                'message': 'Doctor profile synced successfully',
                'data': serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': 'Doctor profile not found for current user'
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Manage doctor availability",
        description="Add or update doctor availability schedules",
        request=DoctorAvailabilitySerializer(many=True),
        responses={
            200: DoctorAvailabilitySerializer(many=True)
        },
        tags=['Doctors']
    )
    @action(detail=True, methods=['post'])
    def set_availability(self, request, pk=None):
        """
        Set availability schedule for a doctor.

        Accepts a list of availability slots and replaces existing schedule.
        """
        doctor = self.get_object()

        # Validate and create availability slots
        availability_data = request.data if isinstance(request.data, list) else [request.data]

        # Delete existing availability
        doctor.availability.all().delete()

        # Create new availability slots
        created_slots = []
        for slot_data in availability_data:
            slot_data['tenant_id'] = request.tenant_id
            serializer = DoctorAvailabilitySerializer(data=slot_data)
            if serializer.is_valid(raise_exception=True):
                availability = serializer.save(doctor=doctor)
                created_slots.append(availability)

        # Return created slots
        output_serializer = DoctorAvailabilitySerializer(created_slots, many=True)
        return Response({
            'success': True,
            'message': f'Created {len(created_slots)} availability slots',
            'data': output_serializer.data
        })

    @extend_schema(
        summary="Get doctor statistics",
        description="Get statistics for a specific doctor",
        responses={
            200: {
                'description': 'Doctor statistics',
                'type': 'object'
            }
        },
        tags=['Doctors']
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Get statistics for a specific doctor.

        Returns consultation counts, ratings, and other metrics.
        """
        doctor = self.get_object()

        return Response({
            'success': True,
            'data': {
                'total_consultations': doctor.total_consultations,
                'average_rating': float(doctor.average_rating),
                'total_reviews': doctor.total_reviews,
                'status': doctor.status,
                'years_of_experience': doctor.years_of_experience,
                'specialties_count': doctor.specialties.count(),
                'is_license_valid': doctor.is_license_valid,
            }
        })
