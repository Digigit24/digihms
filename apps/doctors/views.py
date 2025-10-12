from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count

# ✅ Import drf-spectacular decorators
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse
)

from .models import DoctorProfile, Specialty, DoctorAvailability
from .serializers import (
    DoctorProfileListSerializer,
    DoctorProfileDetailSerializer,
    DoctorProfileCreateUpdateSerializer,
    SpecialtySerializer,
    DoctorAvailabilitySerializer,
    DoctorAvailabilityCreateUpdateSerializer
)
from apps.accounts.permissions import IsAdministrator, IsDoctor


@extend_schema_view(
    list=extend_schema(
        summary="List specialties",
        description="Get list of all medical specialties",
        parameters=[
            OpenApiParameter(name='is_active', type=bool, description='Filter by active status'),
            OpenApiParameter(name='search', type=str, description='Search by name or code'),
        ],
        tags=['Specialties']
    ),
    retrieve=extend_schema(
        summary="Get specialty details",
        description="Retrieve detailed information about a specific specialty",
        tags=['Specialties']
    ),
    create=extend_schema(
        summary="Create specialty",
        description="Create a new medical specialty (Admin only)",
        tags=['Specialties']
    ),
    update=extend_schema(
        summary="Update specialty",
        description="Update a medical specialty (Admin only)",
        tags=['Specialties']
    ),
    partial_update=extend_schema(
        summary="Partial update specialty",
        description="Partially update a medical specialty (Admin only)",
        tags=['Specialties']
    ),
    destroy=extend_schema(
        summary="Delete specialty",
        description="Delete a medical specialty (Admin only). Cannot delete if specialty has active doctors.",
        tags=['Specialties']
    ),
)
class SpecialtyViewSet(viewsets.ModelViewSet):
    """
    Medical Specialties Management
    
    Manage medical specialties like Cardiology, Neurology, etc.
    """
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'department']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdministrator()]
        return [IsAuthenticated()]
    
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
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({
            'success': True,
            'message': 'Specialty created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'success': True,
            'message': 'Specialty updated successfully',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Check if specialty has active doctors
        if instance.doctors.filter(status='active').exists():
            return Response({
                'success': False,
                'error': 'Cannot delete specialty with active doctors'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Specialty deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary="List doctors",
        description="Get list of doctor profiles with filtering options",
        parameters=[
            OpenApiParameter(name='specialty', type=str, description='Filter by specialty name'),
            OpenApiParameter(name='available', type=bool, description='Filter by availability'),
            OpenApiParameter(name='city', type=str, description='Filter by city'),
            OpenApiParameter(name='min_rating', type=float, description='Minimum rating'),
            OpenApiParameter(name='min_fee', type=float, description='Minimum consultation fee'),
            OpenApiParameter(name='max_fee', type=float, description='Maximum consultation fee'),
            OpenApiParameter(name='search', type=str, description='Search by name or license number'),
        ],
        tags=['Doctors']
    ),
    retrieve=extend_schema(
        summary="Get doctor details",
        description="Retrieve detailed information about a specific doctor including availability",
        tags=['Doctors']
    ),
    create=extend_schema(
        summary="Create doctor profile",
        description="Create a new doctor profile (Admin only)",
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
                    'status': 'active'
                },
                request_only=True,
            ),
        ],
        tags=['Doctors']
    ),
    update=extend_schema(
        summary="Update doctor profile",
        description="Update doctor profile (Doctor or Admin)",
        tags=['Doctors']
    ),
    partial_update=extend_schema(
        summary="Partial update doctor profile",
        description="Partially update doctor profile (Doctor or Admin)",
        tags=['Doctors']
    ),
    destroy=extend_schema(
        summary="Deactivate doctor profile",
        description="Soft delete - deactivate doctor profile (Admin only)",
        tags=['Doctors']
    ),
)
class DoctorProfileViewSet(viewsets.ModelViewSet):
    """
    Doctor Profile Management
    
    Complete CRUD operations for doctor profiles including:
    - Profile management
    - Availability scheduling
    - Statistics and reporting
    """
    queryset = DoctorProfile.objects.select_related('user').prefetch_related(
        'specialties', 'availability'
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_available_online', 'is_available_offline']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 
                     'medical_license_number', 'qualifications']
    ordering_fields = ['created_at', 'consultation_fee', 'average_rating', 
                      'years_of_experience']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return DoctorProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DoctorProfileCreateUpdateSerializer
        return DoctorProfileDetailSerializer
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        elif self.action in ['create', 'destroy']:
            return [IsAdministrator()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated()]  # Will check ownership in update method
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role and query params"""
        queryset = DoctorProfile.objects.select_related('user').prefetch_related(
            'specialties', 'availability'
        )
        
        user = self.request.user
        
        # Doctors can only see their own profile (unless admin)
        if user.groups.filter(name='Doctor').exists():
            if not user.groups.filter(name='Administrator').exists():
                queryset = queryset.filter(user=user)
        
        # Filter by specialty
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(
                specialties__name__icontains=specialty
            )
        
        # Filter by availability status
        available = self.request.query_params.get('available')
        if available and available.lower() == 'true':
            queryset = queryset.filter(status='active')
        
        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(user__city__icontains=city)
        
        # Filter by minimum rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass
        
        # Filter by consultation fee range
        min_fee = self.request.query_params.get('min_fee')
        max_fee = self.request.query_params.get('max_fee')
        if min_fee:
            try:
                queryset = queryset.filter(consultation_fee__gte=float(min_fee))
            except ValueError:
                pass
        if max_fee:
            try:
                queryset = queryset.filter(consultation_fee__lte=float(max_fee))
            except ValueError:
                pass
        
        return queryset.distinct()
    
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
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Doctor profile created successfully',
            'data': DoctorProfileDetailSerializer(doctor).data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check permission - only admin or self can update
        if instance.user != request.user and not request.user.groups.filter(
            name='Administrator'
        ).exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Doctor profile updated successfully',
            'data': DoctorProfileDetailSerializer(doctor).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Soft delete - set status to inactive
        instance.status = 'inactive'
        instance.save()
        
        return Response({
            'success': True,
            'message': 'Doctor profile deactivated successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        summary="Get doctor availability",
        description="Retrieve doctor's weekly availability schedule",
        responses={200: DoctorAvailabilitySerializer(many=True)},
        tags=['Doctors']
    )
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Get doctor's availability schedule"""
        doctor = self.get_object()
        availability = doctor.availability.all()
        serializer = DoctorAvailabilitySerializer(availability, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @extend_schema(
        summary="Set doctor availability",
        description="Add a new availability slot for the doctor",
        request=DoctorAvailabilityCreateUpdateSerializer,
        responses={
            201: DoctorAvailabilitySerializer,
            403: OpenApiResponse(description="Permission denied")
        },
        examples=[
            OpenApiExample(
                'Availability Example',
                value={
                    'day_of_week': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'is_available': True,
                    'max_appointments': 20
                },
                request_only=True,
            ),
        ],
        tags=['Doctors']
    )
    @action(detail=True, methods=['post'])
    def set_availability(self, request, pk=None):
        """Set doctor's availability"""
        doctor = self.get_object()
        
        # Check permission
        if doctor.user != request.user and not request.user.groups.filter(
            name='Administrator'
        ).exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = DoctorAvailabilityCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(doctor=doctor)
            return Response({
                'success': True,
                'message': 'Availability added successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get doctor statistics",
        description="Get statistical overview of all doctors (Admin only)",
        responses={200: OpenApiResponse(description="Statistics object")},
        tags=['Doctors']
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get doctor statistics (Admin only)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        total = DoctorProfile.objects.count()
        active = DoctorProfile.objects.filter(status='active').count()
        on_leave = DoctorProfile.objects.filter(status='on_leave').count()
        inactive = DoctorProfile.objects.filter(status='inactive').count()
        
        # Average stats
        avg_stats = DoctorProfile.objects.aggregate(
            avg_rating=Avg('average_rating'),
            avg_experience=Avg('years_of_experience'),
            avg_fee=Avg('consultation_fee'),
            total_consultations=Count('id')
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
            }
        })
    
    @extend_schema(
        summary="Activate doctor profile",
        description="Activate a doctor profile (Admin only)",
        request=None,
        responses={200: DoctorProfileDetailSerializer},
        tags=['Doctors']
    )
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate doctor profile (Admin only)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        doctor = self.get_object()
        doctor.status = 'active'
        doctor.save()
        
        return Response({
            'success': True,
            'message': 'Doctor profile activated successfully',
            'data': DoctorProfileDetailSerializer(doctor).data
        })
    
    @extend_schema(
        summary="Deactivate doctor profile",
        description="Deactivate a doctor profile (Admin only)",
        request=None,
        responses={200: DoctorProfileDetailSerializer},
        tags=['Doctors']
    )
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate doctor profile (Admin only)"""
        if not request.user.groups.filter(name='Administrator').exists():
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        doctor = self.get_object()
        doctor.status = 'inactive'
        doctor.save()
        
        return Response({
            'success': True,
            'message': 'Doctor profile deactivated successfully',
            'data': DoctorProfileDetailSerializer(doctor).data
        })