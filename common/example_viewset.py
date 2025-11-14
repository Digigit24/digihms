"""
Example ViewSet demonstrating JWT-based permissions for HMS multi-tenant system.

This shows how to properly implement ViewSets with:
- JWT authentication from SuperAdmin
- Tenant-specific database routing
- Permission-based access control
- Automatic tenant_id assignment
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from common.permissions import PermissionMixin, HMSPermissions, check_permission
from apps.patients.models import PatientProfile
from apps.patients.serializers import (
    PatientProfileListSerializer,
    PatientProfileDetailSerializer,
    PatientProfileCreateUpdateSerializer
)


class ExamplePatientViewSet(PermissionMixin, viewsets.ModelViewSet):
    """
    Example Patient ViewSet with JWT-based permissions.
    
    Demonstrates:
    - Permission mapping for all CRUD operations
    - Automatic tenant_id assignment
    - Permission-based queryset filtering
    - Proper error handling
    """
    
    queryset = PatientProfile.objects.all()
    
    # Define permission mapping for each action
    permission_mapping = {
        'list': HMSPermissions.PATIENTS_VIEW,
        'retrieve': HMSPermissions.PATIENTS_VIEW,
        'create': HMSPermissions.PATIENTS_CREATE,
        'update': HMSPermissions.PATIENTS_EDIT,
        'partial_update': HMSPermissions.PATIENTS_EDIT,
        'destroy': HMSPermissions.PATIENTS_DELETE,
        'statistics': HMSPermissions.PATIENTS_VIEW,
        'my_patients': HMSPermissions.PATIENTS_VIEW,
    }
    
    # Field that contains the owner/creator ID for permission checking
    owner_field = 'created_by_id'
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PatientProfileListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientProfileCreateUpdateSerializer
        return PatientProfileDetailSerializer
    
    def get_queryset(self):
        """
        Get queryset with permission-based filtering.
        
        The PermissionMixin automatically handles:
        - Filtering based on permission scope (all/team/own)
        - Tenant isolation (handled by database router)
        """
        # Call parent method which applies permission filtering
        queryset = super().get_queryset()
        
        # Add any additional filtering logic here
        # For example, exclude deceased patients by default
        if self.action == 'list':
            exclude_deceased = self.request.query_params.get('include_deceased', 'false')
            if exclude_deceased.lower() != 'true':
                queryset = queryset.exclude(status='deceased')
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Create patient with automatic tenant_id and owner assignment.
        
        The PermissionMixin automatically:
        - Checks create permission
        - Sets tenant_id from request.tenant_id
        - Sets created_by from request.user_id
        """
        # Call parent method which handles permission checks and field assignment
        super().perform_create(serializer)
    
    def perform_update(self, serializer):
        """
        Update patient with permission checks.
        
        The PermissionMixin automatically:
        - Checks edit permission
        - Validates user can edit this specific resource
        """
        super().perform_update(serializer)
    
    def perform_destroy(self, instance):
        """
        Soft delete patient (set status to inactive).
        
        The PermissionMixin automatically:
        - Checks delete permission
        - Validates user can delete this specific resource
        """
        # Instead of hard delete, set status to inactive
        instance.status = 'inactive'
        instance.save()
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get patient statistics.
        
        Requires 'hms.patients.view' permission with 'all' scope.
        """
        # Check if user has permission to view all patients
        if not check_permission(request, HMSPermissions.PATIENTS_VIEW):
            return Response({
                'error': 'Permission denied',
                'detail': 'Insufficient permissions to view patient statistics'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get permission scope
        permission_value = request.permissions.get(HMSPermissions.PATIENTS_VIEW)
        
        if permission_value != 'all':
            return Response({
                'error': 'Permission denied',
                'detail': 'Statistics require "all" scope for patient view permission'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Calculate statistics (automatically uses tenant database)
        total_patients = PatientProfile.objects.count()
        active_patients = PatientProfile.objects.filter(status='active').count()
        inactive_patients = PatientProfile.objects.filter(status='inactive').count()
        
        # Gender distribution
        gender_stats = {}
        for gender_code, gender_label in PatientProfile.GENDER_CHOICES:
            count = PatientProfile.objects.filter(gender=gender_code).count()
            if count > 0:
                gender_stats[gender_label] = count
        
        return Response({
            'success': True,
            'data': {
                'total_patients': total_patients,
                'active_patients': active_patients,
                'inactive_patients': inactive_patients,
                'gender_distribution': gender_stats,
                'tenant_id': request.tenant_id,
                'tenant_slug': request.tenant_slug,
            }
        })
    
    @action(detail=False, methods=['get'])
    def my_patients(self, request):
        """
        Get patients created by the current user.
        
        Demonstrates filtering by owner regardless of permission scope.
        """
        # This will automatically filter to user's own patients
        # even if they have 'all' scope permission
        queryset = PatientProfile.objects.filter(created_by_id=request.user_id)
        
        # Apply standard filtering
        queryset = self.filter_queryset(queryset)
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': queryset.count()
        })


class ExampleAppointmentViewSet(PermissionMixin, viewsets.ModelViewSet):
    """
    Example Appointment ViewSet with JWT-based permissions.
    
    Demonstrates different permission patterns for appointments.
    """
    
    # Import the model and serializers as needed
    # from apps.appointments.models import Appointment
    # from apps.appointments.serializers import AppointmentSerializer
    
    # queryset = Appointment.objects.all()
    
    # Define permission mapping
    permission_mapping = {
        'list': HMSPermissions.APPOINTMENTS_VIEW,
        'retrieve': HMSPermissions.APPOINTMENTS_VIEW,
        'create': HMSPermissions.APPOINTMENTS_CREATE,
        'update': HMSPermissions.APPOINTMENTS_EDIT,
        'partial_update': HMSPermissions.APPOINTMENTS_EDIT,
        'destroy': HMSPermissions.APPOINTMENTS_DELETE,
        'schedule': HMSPermissions.APPOINTMENTS_CREATE,
        'cancel': HMSPermissions.APPOINTMENTS_EDIT,
    }
    
    # For appointments, the owner might be the doctor who created it
    owner_field = 'created_by_id'
    
    def get_queryset(self):
        """Filter appointments based on permissions."""
        queryset = super().get_queryset()
        
        # Additional filtering based on user role
        permission_value = self.request.permissions.get(HMSPermissions.APPOINTMENTS_VIEW)
        
        if permission_value == 'own':
            # Show only appointments created by this user OR assigned to this user (if doctor)
            queryset = queryset.filter(
                Q(created_by_id=self.request.user_id) |
                Q(doctor__user_id=self.request.user_id)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an appointment."""
        appointment = self.get_object()
        
        # Check if user can edit this appointment
        if not self.check_object_permission(appointment):
            return Response({
                'error': 'Permission denied',
                'detail': 'Cannot cancel this appointment'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Update appointment status
        appointment.status = 'cancelled'
        appointment.cancelled_by_id = request.user_id
        appointment.cancelled_at = timezone.now()
        appointment.cancellation_reason = request.data.get('reason', 'Cancelled by user')
        appointment.save()
        
        return Response({
            'success': True,
            'message': 'Appointment cancelled successfully'
        })


# Usage in urls.py:
"""
from rest_framework.routers import DefaultRouter
from common.example_viewset import ExamplePatientViewSet

router = DefaultRouter()
router.register(r'patients', ExamplePatientViewSet, basename='patients')
urlpatterns = router.urls
"""

# Example of permission checking in a function-based view:
"""
from django.http import JsonResponse
from common.permissions import permission_required, HMSPermissions

@permission_required(HMSPermissions.PATIENTS_VIEW)
def patient_list_view(request):
    # This view will only be accessible if user has 'hms.patients.view' permission
    patients = PatientProfile.objects.all()  # Automatically routed to tenant DB
    return JsonResponse({'patients': list(patients.values())})

@permission_required(HMSPermissions.PATIENTS_EDIT, resource_owner_field='patient_id')
def update_patient_view(request, patient_id):
    # This view checks if user can edit the specific patient
    # The patient_id from URL kwargs is used for ownership checking
    patient = PatientProfile.objects.get(id=patient_id)
    # Update logic here
    return JsonResponse({'success': True})
"""