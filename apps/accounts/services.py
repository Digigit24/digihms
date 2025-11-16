"""
SuperAdmin Integration Services

Functions for syncing with SuperAdmin and managing user/patient relationships.
"""

import requests
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import DoctorProfile
from apps.patients.models import PatientProfile
import logging

logger = logging.getLogger(__name__)


def sync_doctor_from_jwt(user_id, jwt_payload):
    """
    Sync doctor data from JWT payload to local doctor profile cache.

    Creates or updates doctor profile with latest user data from SuperAdmin.

    Args:
        user_id: UUID of SuperAdmin user
        jwt_payload: JWT payload containing user data

    Returns:
        DoctorProfile instance if exists, None otherwise
    """
    try:
        doctor = DoctorProfile.objects.filter(user_id=user_id).first()
        if doctor:
            # Update cached user data
            doctor.email = jwt_payload.get('email', '')
            doctor.first_name = jwt_payload.get('first_name', '')
            doctor.last_name = jwt_payload.get('last_name', '')
            doctor.last_synced_at = timezone.now()
            doctor.save(update_fields=['email', 'first_name', 'last_name', 'last_synced_at'])
            logger.info(f"Synced doctor profile for user {user_id}")
            return doctor
    except Exception as e:
        logger.error(f"Error syncing doctor {user_id}: {e}")
    return None


def create_doctor_profile(user_id, tenant_id, email, first_name='', last_name='', **kwargs):
    """
    Create a new doctor profile for a SuperAdmin user.

    Args:
        user_id: UUID of SuperAdmin user
        tenant_id: UUID of tenant
        email: Doctor's email
        first_name: Doctor's first name (optional)
        last_name: Doctor's last name (optional)
        **kwargs: Additional doctor profile fields

    Returns:
        DoctorProfile instance
    """
    try:
        doctor = DoctorProfile.objects.create(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            **kwargs
        )
        logger.info(f"Created doctor profile for user {user_id}")
        return doctor
    except Exception as e:
        logger.error(f"Error creating doctor profile: {e}")
        raise


def create_patient_portal_access(patient_profile_id, request):
    """
    Create SuperAdmin user account for patient portal access.

    Calls SuperAdmin API to create a patient user account and links it
    to the existing patient profile.

    Args:
        patient_profile_id: ID of PatientProfile
        request: Django request object with JWT auth

    Returns:
        dict: Result with success status and user details or error
    """
    try:
        patient = PatientProfile.objects.get(id=patient_profile_id)

        if patient.has_portal_access:
            return {
                'success': False,
                'error': 'Patient already has portal access'
            }

        # Prepare email for patient account
        email = patient.email or f"patient{patient.patient_id}@temp.com"

        # Call SuperAdmin API to create patient user
        superadmin_url = settings.SUPERADMIN_URL

        # Get JWT token from request
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return {
                'success': False,
                'error': 'Missing or invalid authorization token'
            }

        token = auth_header.split(' ')[1]

        response = requests.post(
            f"{superadmin_url}/api/auth/register-patient/",
            json={
                'email': email,
                'password': 'ChangeMe123!',  # Temporary password - should be sent to patient
                'first_name': patient.first_name,
                'last_name': patient.last_name or '',
                'tenant_id': str(request.tenant_id),
                'user_type': 'patient'
            },
            headers={'Authorization': f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            user_data = data.get('user', {})
            user_id = user_data.get('id')

            # Update patient profile with user linkage
            patient.user_id = user_id
            patient.has_portal_access = True
            patient.portal_created_at = timezone.now()
            patient.portal_email = user_data.get('email')
            patient.save(update_fields=[
                'user_id', 'has_portal_access',
                'portal_created_at', 'portal_email'
            ])

            logger.info(f"Created portal access for patient {patient_profile_id}")

            return {
                'success': True,
                'user_id': user_id,
                'email': patient.portal_email,
                'temporary_password': 'ChangeMe123!',
                'message': 'Portal access created successfully. Patient should change password on first login.'
            }
        elif response.status_code == 400:
            error_data = response.json()
            return {
                'success': False,
                'error': error_data.get('error', 'Bad request to SuperAdmin')
            }
        else:
            logger.error(f"SuperAdmin API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'Failed to create portal access: {response.status_code}'
            }

    except PatientProfile.DoesNotExist:
        return {
            'success': False,
            'error': 'Patient not found'
        }
    except requests.RequestException as e:
        logger.error(f"Error connecting to SuperAdmin: {e}")
        return {
            'success': False,
            'error': 'Unable to connect to SuperAdmin service'
        }
    except Exception as e:
        logger.error(f"Error creating portal access: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def revoke_patient_portal_access(patient_profile_id, request):
    """
    Revoke patient portal access.

    Note: This only unlinks the user from the patient profile.
    The SuperAdmin user account remains but loses HMS access.

    Args:
        patient_profile_id: ID of PatientProfile
        request: Django request object

    Returns:
        dict: Result with success status or error
    """
    try:
        patient = PatientProfile.objects.get(id=patient_profile_id)

        if not patient.has_portal_access:
            return {
                'success': False,
                'error': 'Patient does not have portal access'
            }

        # Unlink user from patient profile
        patient.user_id = None
        patient.has_portal_access = False
        patient.portal_email = None
        # Keep portal_created_at for audit purposes
        patient.save(update_fields=[
            'user_id', 'has_portal_access', 'portal_email'
        ])

        logger.info(f"Revoked portal access for patient {patient_profile_id}")

        return {
            'success': True,
            'message': 'Portal access revoked successfully'
        }

    except PatientProfile.DoesNotExist:
        return {
            'success': False,
            'error': 'Patient not found'
        }
    except Exception as e:
        logger.error(f"Error revoking portal access: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def get_or_create_doctor_profile(user_id, tenant_id, email, first_name='', last_name=''):
    """
    Get existing doctor profile or create a new one.

    Helper function for view logic.

    Args:
        user_id: UUID of SuperAdmin user
        tenant_id: UUID of tenant
        email: Doctor's email
        first_name: Doctor's first name
        last_name: Doctor's last name

    Returns:
        tuple: (DoctorProfile, created boolean)
    """
    try:
        doctor, created = DoctorProfile.objects.get_or_create(
            user_id=user_id,
            defaults={
                'tenant_id': tenant_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        if not created:
            # Update cached data if exists
            doctor.email = email
            doctor.first_name = first_name
            doctor.last_name = last_name
            doctor.save(update_fields=['email', 'first_name', 'last_name'])

        return doctor, created
    except Exception as e:
        logger.error(f"Error in get_or_create_doctor_profile: {e}")
        raise
