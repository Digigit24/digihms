"""
SuperAdmin API Client for HMS User Management

This module provides a client to interact with the SuperAdmin backend APIs
for user and role management without requiring local database models.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SuperAdminAPIError(Exception):
    """Custom exception for SuperAdmin API errors"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class SuperAdminAPIClient:
    """
    Client for interacting with SuperAdmin backend APIs

    Handles authentication, request formatting, and error handling
    for all SuperAdmin API calls.
    """

    def __init__(self, request=None):
        """
        Initialize the API client

        Args:
            request: Django request object containing JWT token
        """
        self.base_url = getattr(settings, 'SUPERADMIN_URL', 'https://admin.celiyo.com')
        self.api_url = f"{self.base_url}/api"
        self.request = request
        self.timeout = 30  # 30 seconds timeout

    def _get_headers(self, token: str = None) -> Dict[str, str]:
        """
        Get headers for API requests

        Args:
            token: JWT token (optional, will extract from request if not provided)

        Returns:
            Dict containing authorization and content-type headers
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        if token:
            headers['Authorization'] = f'Bearer {token}'
        elif self.request:
            # Extract token from request
            auth_header = self.request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                headers['Authorization'] = f'Bearer {token}'
            elif hasattr(self.request, 'session'):
                # Try to get from session (for admin)
                session_token = self.request.session.get('jwt_token')
                if session_token:
                    headers['Authorization'] = f'Bearer {session_token}'

        return headers

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions

        Args:
            response: requests Response object

        Returns:
            Parsed JSON response data

        Raises:
            SuperAdminAPIError: If the API returns an error
        """
        try:
            data = response.json()
        except ValueError:
            data = {'error': 'Invalid JSON response'}

        if response.status_code >= 400:
            error_message = data.get('error') or data.get('detail') or f'API error: {response.status_code}'
            raise SuperAdminAPIError(
                message=error_message,
                status_code=response.status_code,
                response_data=data
            )

        return data

    # ==================== Authentication APIs ====================

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login user via SuperAdmin

        Args:
            email: User email
            password: User password

        Returns:
            Dict containing tokens and user data
        """
        url = f"{self.api_url}/auth/login/"

        try:
            response = requests.post(
                url,
                json={'email': email, 'password': password},
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Login request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def register(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register new tenant and admin user

        Args:
            data: Registration data (tenant_name, admin_email, etc.)

        Returns:
            Dict containing created tenant and user data
        """
        url = f"{self.api_url}/auth/register/"

        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Registration request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def change_password(self, token: str, old_password: str, new_password: str, new_password_confirm: str) -> Dict[str, Any]:
        """
        Change user password

        Args:
            token: JWT token
            old_password: Current password
            new_password: New password
            new_password_confirm: Password confirmation

        Returns:
            Success message
        """
        url = f"{self.api_url}/auth/password/change/"

        try:
            response = requests.post(
                url,
                json={
                    'old_password': old_password,
                    'new_password': new_password,
                    'new_password_confirm': new_password_confirm
                },
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Change password request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh JWT token

        Args:
            refresh_token: Refresh token

        Returns:
            New access token
        """
        url = f"{self.api_url}/auth/token/refresh/"

        try:
            response = requests.post(
                url,
                json={'refresh': refresh_token},
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def logout(self, token: str, refresh_token: str) -> Dict[str, Any]:
        """
        Logout user (blacklist token)

        Args:
            token: JWT access token
            refresh_token: JWT refresh token

        Returns:
            Success message
        """
        url = f"{self.api_url}/auth/logout/"

        try:
            response = requests.post(
                url,
                json={'refresh_token': refresh_token},
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Logout request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    # ==================== User Management APIs ====================

    def get_users(self, token: str = None, **filters) -> List[Dict[str, Any]]:
        """
        Get list of users for current tenant

        Args:
            token: JWT token (optional)
            **filters: Query parameters for filtering

        Returns:
            List of user dictionaries
        """
        url = f"{self.api_url}/users/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                params=filters,
                timeout=self.timeout
            )
            data = self._handle_response(response)

            # Handle paginated response
            if isinstance(data, dict) and 'results' in data:
                return data['results']
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            logger.error(f"Get users request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def get_user(self, user_id: str, token: str = None) -> Dict[str, Any]:
        """
        Get user by ID

        Args:
            user_id: User UUID
            token: JWT token (optional)

        Returns:
            User dictionary
        """
        url = f"{self.api_url}/users/{user_id}/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Get user request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def get_me(self, token: str = None) -> Dict[str, Any]:
        """
        Get current authenticated user

        Args:
            token: JWT token (optional)

        Returns:
            User dictionary
        """
        url = f"{self.api_url}/users/me/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Get me request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def create_user(self, data: Dict[str, Any], token: str = None) -> Dict[str, Any]:
        """
        Create new user

        Args:
            data: User data (email, password, first_name, etc.)
            token: JWT token (optional)

        Returns:
            Created user dictionary
        """
        url = f"{self.api_url}/users/"

        try:
            response = requests.post(
                url,
                json=data,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Create user request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def update_user(self, user_id: str, data: Dict[str, Any], token: str = None, partial: bool = True) -> Dict[str, Any]:
        """
        Update user

        Args:
            user_id: User UUID
            data: User data to update
            token: JWT token (optional)
            partial: Whether to do partial update (PATCH) or full update (PUT)

        Returns:
            Updated user dictionary
        """
        url = f"{self.api_url}/users/{user_id}/"

        try:
            if partial:
                response = requests.patch(
                    url,
                    json=data,
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            else:
                response = requests.put(
                    url,
                    json=data,
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Update user request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def update_me(self, data: Dict[str, Any], token: str = None) -> Dict[str, Any]:
        """
        Update current authenticated user

        Args:
            data: User data to update
            token: JWT token (optional)

        Returns:
            Updated user dictionary
        """
        url = f"{self.api_url}/users/update_me/"

        try:
            response = requests.patch(
                url,
                json=data,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Update me request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def delete_user(self, user_id: str, token: str = None) -> None:
        """
        Delete user

        Args:
            user_id: User UUID
            token: JWT token (optional)
        """
        url = f"{self.api_url}/users/{user_id}/"

        try:
            response = requests.delete(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            if response.status_code not in [200, 204]:
                self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Delete user request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def assign_roles(self, user_id: str, role_ids: List[str], token: str = None) -> Dict[str, Any]:
        """
        Assign roles to user

        Args:
            user_id: User UUID
            role_ids: List of role UUIDs
            token: JWT token (optional)

        Returns:
            Success message
        """
        url = f"{self.api_url}/users/{user_id}/assign_roles/"

        try:
            response = requests.post(
                url,
                json={'role_ids': role_ids},
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Assign roles request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def remove_role(self, user_id: str, role_id: str, token: str = None) -> Dict[str, Any]:
        """
        Remove role from user

        Args:
            user_id: User UUID
            role_id: Role UUID
            token: JWT token (optional)

        Returns:
            Success message
        """
        url = f"{self.api_url}/users/{user_id}/remove_role/"

        try:
            response = requests.delete(
                url,
                json={'role_id': role_id},
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Remove role request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    # ==================== Role Management APIs ====================

    def get_roles(self, token: str = None, **filters) -> List[Dict[str, Any]]:
        """
        Get list of roles for current tenant

        Args:
            token: JWT token (optional)
            **filters: Query parameters for filtering

        Returns:
            List of role dictionaries
        """
        url = f"{self.api_url}/roles/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                params=filters,
                timeout=self.timeout
            )
            data = self._handle_response(response)

            # Handle paginated response
            if isinstance(data, dict) and 'results' in data:
                return data['results']
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            logger.error(f"Get roles request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def get_role(self, role_id: str, token: str = None) -> Dict[str, Any]:
        """
        Get role by ID

        Args:
            role_id: Role UUID
            token: JWT token (optional)

        Returns:
            Role dictionary
        """
        url = f"{self.api_url}/roles/{role_id}/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Get role request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def create_role(self, data: Dict[str, Any], token: str = None) -> Dict[str, Any]:
        """
        Create new role

        Args:
            data: Role data (name, description, permissions)
            token: JWT token (optional)

        Returns:
            Created role dictionary
        """
        url = f"{self.api_url}/roles/"

        try:
            response = requests.post(
                url,
                json=data,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Create role request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def update_role(self, role_id: str, data: Dict[str, Any], token: str = None, partial: bool = True) -> Dict[str, Any]:
        """
        Update role

        Args:
            role_id: Role UUID
            data: Role data to update
            token: JWT token (optional)
            partial: Whether to do partial update (PATCH) or full update (PUT)

        Returns:
            Updated role dictionary
        """
        url = f"{self.api_url}/roles/{role_id}/"

        try:
            if partial:
                response = requests.patch(
                    url,
                    json=data,
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            else:
                response = requests.put(
                    url,
                    json=data,
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Update role request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def delete_role(self, role_id: str, token: str = None) -> None:
        """
        Delete role

        Args:
            role_id: Role UUID
            token: JWT token (optional)
        """
        url = f"{self.api_url}/roles/{role_id}/"

        try:
            response = requests.delete(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            if response.status_code not in [200, 204]:
                self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Delete role request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def get_role_members(self, role_id: str, token: str = None) -> List[Dict[str, Any]]:
        """
        Get members of a role

        Args:
            role_id: Role UUID
            token: JWT token (optional)

        Returns:
            List of user dictionaries
        """
        url = f"{self.api_url}/roles/{role_id}/members/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            data = self._handle_response(response)
            return data if isinstance(data, list) else []
        except requests.RequestException as e:
            logger.error(f"Get role members request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")

    def get_permissions_schema(self, token: str = None) -> Dict[str, Any]:
        """
        Get permissions schema

        Args:
            token: JWT token (optional)

        Returns:
            Permissions schema dictionary
        """
        url = f"{self.api_url}/roles/permissions_schema/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(token),
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Get permissions schema request failed: {e}")
            raise SuperAdminAPIError(f"Connection error: {str(e)}")
