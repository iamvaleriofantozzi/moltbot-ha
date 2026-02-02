"""Data models for Home Assistant API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field


class EntityState(BaseModel):
    """Represents a Home Assistant entity state."""

    entity_id: str
    state: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    last_changed: datetime
    last_updated: datetime
    context: Dict[str, Any] = Field(default_factory=dict)

    @property
    def domain(self) -> str:
        """Extract domain from entity_id (e.g., 'light' from 'light.kitchen')."""
        return self.entity_id.split(".", 1)[0]

    @property
    def friendly_name(self) -> str:
        """Get friendly name from attributes, fallback to entity_id."""
        return self.attributes.get("friendly_name", self.entity_id)


class ServiceCall(BaseModel):
    """Represents a Home Assistant service call."""

    domain: str
    service: str
    entity_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_entity_and_service(
        cls, entity_id: str, service: str, data: Optional[Dict[str, Any]] = None
    ) -> "ServiceCall":
        """Create a ServiceCall from entity_id and service name."""
        domain = entity_id.split(".", 1)[0]
        call_data = data or {}
        call_data["entity_id"] = entity_id
        return cls(domain=domain, service=service, data=call_data)

    @classmethod
    def parse_service_string(cls, service_string: str) -> Tuple[str, str]:
        """Parse 'domain.service' string into (domain, service)."""
        if "." not in service_string:
            raise ValueError(f"Invalid service format: {service_string}. Expected 'domain.service'")
        domain, service = service_string.split(".", 1)
        return domain, service


class ApiError(Exception):
    """Custom exception for Home Assistant API errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class CriticalActionError(Exception):
    """Exception raised when a critical action requires user confirmation."""

    def __init__(self, entity_id: str, action: str):
        self.entity_id = entity_id
        self.action = action
        message = (
            f"⚠️  CRITICAL ACTION REQUIRES CONFIRMATION\n\n"
            f"Action: {action} on {entity_id}\n\n"
            f"This is a critical operation that requires explicit user approval.\n"
            f"Ask the user for confirmation (e.g., 'Do you want to proceed?').\n"
            f"If the user confirms (e.g., says 'Yes', 'OK', 'Confirm'), retry with --force flag.\n\n"
            f"Example: moltbot-ha {action} {entity_id} --force"
        )
        super().__init__(message)
