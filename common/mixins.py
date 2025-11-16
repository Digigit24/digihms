"""
Mixins for HMS multi-tenant system.

Provides common functionality for:
- Tenant-based filtering
- Patient access control
- ViewSet permissions
"""

from django.db import models
from rest_framework import viewsets
import logging

logger = logging.getLogger(__name__)


class TenantMixin(models.Model):
    """
    Mixin to add tenant_id field to models.

    All models that need tenant isolation should inherit from this.
    """
    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant identifier for multi-tenancy"
    )

    class Meta:
        abstract = True


class TenantViewSetMixin:
    """
    ViewSet mixin for automatic tenant filtering.

    Automatically filters querysets by tenant_id from JWT request.
    """

    def get_queryset(self):
        """Filter queryset by tenant_id from request."""
        queryset = super().get_queryset()

        # Check if model has tenant_id field
        if hasattr(queryset.model, 'tenant_id') and hasattr(self.request, 'tenant_id'):
            queryset = queryset.filter(tenant_id=self.request.tenant_id)
            logger.debug(f"Filtered queryset by tenant_id: {self.request.tenant_id}")

        return queryset

    def perform_create(self, serializer):
        """Automatically set tenant_id when creating objects."""
        save_kwargs = {}

        # Set tenant_id if model has this field
        if hasattr(serializer.Meta.model, 'tenant_id') and hasattr(self.request, 'tenant_id'):
            save_kwargs['tenant_id'] = self.request.tenant_id

        # Call parent method if it exists
        if hasattr(super(), 'perform_create'):
            super().perform_create(serializer)
        else:
            serializer.save(**save_kwargs)


class PatientAccessMixin:
    """
    Mixin to restrict patients to their own records.

    If the current user is a patient (has is_patient flag),
    filter records to only show their own data.
    """

    def get_queryset(self):
        """Filter queryset for patient users to see only their own records."""
        queryset = super().get_queryset()

        # Check if user is a patient
        if hasattr(self.request, 'user_type') and self.request.user_type == 'patient':
            # If model has user_id field, filter by it
            if hasattr(queryset.model, 'user_id') and hasattr(self.request, 'user_id'):
                queryset = queryset.filter(user_id=self.request.user_id)
                logger.debug(f"Filtered patient records for user_id: {self.request.user_id}")

        return queryset
