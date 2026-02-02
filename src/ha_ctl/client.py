"""Home Assistant API client."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import ApiError, EntityState, ServiceCall

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """HTTP client for Home Assistant REST API."""

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        """Initialize the Home Assistant client.

        Args:
            base_url: Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: Long-lived access token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

        # Configure session with retry logic
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

        # Setup retry strategy for transient errors
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=0.3,  # 0.3s, 0.6s, 1.2s delays
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make HTTP request to Home Assistant API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /api/states)
            json_data: JSON payload for POST requests

        Returns:
            JSON response data

        Raises:
            ApiError: On API errors or connection issues
        """
        url = urljoin(self.base_url, endpoint)

        try:
            logger.debug(f"{method} {url}")
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                timeout=self.timeout,
            )

            logger.debug(f"Response: {response.status_code}")

            # Raise for HTTP errors
            if response.status_code >= 400:
                error_msg = self._parse_error_response(response)
                raise ApiError(
                    message=error_msg,
                    status_code=response.status_code,
                    response=response.text,
                )

            # Parse JSON response
            try:
                return response.json()
            except ValueError:
                # Empty or non-JSON response
                return None

        except requests.exceptions.ConnectionError as e:
            raise ApiError(
                f"Connection failed to {self.base_url}. "
                f"Ensure Home Assistant is reachable and URL is correct. Error: {e}"
            )
        except requests.exceptions.Timeout as e:
            raise ApiError(f"Request timed out after {self.timeout}s. Error: {e}")
        except requests.exceptions.RequestException as e:
            raise ApiError(f"Request failed: {e}")

    def _parse_error_response(self, response: requests.Response) -> str:
        """Parse error message from API response."""
        if response.status_code == 401:
            return (
                "Authentication failed. Check your Home Assistant token. "
                "Ensure it's a valid long-lived access token."
            )
        elif response.status_code == 404:
            return f"Resource not found: {response.url}"
        elif response.status_code == 503:
            return "Home Assistant is unavailable or starting up."

        # Try to extract error message from JSON response
        try:
            error_data = response.json()
            if "message" in error_data:
                return error_data["message"]
        except ValueError:
            pass

        return f"API error: {response.status_code} {response.reason}"

    def test_connection(self) -> bool:
        """Test connection to Home Assistant.

        Returns:
            True if connection successful

        Raises:
            ApiError: On connection failure
        """
        result = self._make_request("GET", "/api/")
        logger.info(f"Connected to Home Assistant: {result.get('message', 'OK')}")
        return True

    def get_states(self) -> List[EntityState]:
        """Get all entity states.

        Returns:
            List of entity states
        """
        data = self._make_request("GET", "/api/states")
        return [EntityState(**item) for item in data]

    def get_state(self, entity_id: str) -> EntityState:
        """Get state of a specific entity.

        Args:
            entity_id: Entity ID (e.g., light.kitchen)

        Returns:
            Entity state

        Raises:
            ApiError: If entity not found
        """
        endpoint = f"/api/states/{entity_id}"
        data = self._make_request("GET", endpoint)

        if not data:
            raise ApiError(f"Entity not found: {entity_id}", status_code=404)

        return EntityState(**data)

    def call_service(
        self,
        domain: str,
        service: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call a Home Assistant service.

        Args:
            domain: Service domain (e.g., light, switch)
            service: Service name (e.g., turn_on, turn_off)
            data: Service data (including entity_id)

        Returns:
            Service call response
        """
        endpoint = f"/api/services/{domain}/{service}"
        service_data = data or {}

        logger.info(f"Calling service: {domain}.{service} with data: {service_data}")
        return self._make_request("POST", endpoint, json_data=service_data)

    def call_service_for_entity(
        self,
        entity_id: str,
        service: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call a service for a specific entity.

        Args:
            entity_id: Target entity ID
            service: Service name (e.g., turn_on)
            data: Additional service data

        Returns:
            Service call response
        """
        domain = entity_id.split(".", 1)[0]
        service_data = data or {}
        service_data["entity_id"] = entity_id

        return self.call_service(domain, service, service_data)
