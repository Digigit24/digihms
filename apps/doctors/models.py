"""
DigiHMS Doctors Models

Models moved to apps.accounts.models for centralized management.
This file now re-exports them for backwards compatibility.
"""

# Import models from accounts app
from apps.accounts.models import DoctorProfile, Specialty, DoctorAvailability

__all__ = ['DoctorProfile', 'Specialty', 'DoctorAvailability']
