"""Safety checks for critical Home Assistant actions."""

from __future__ import annotations

import fnmatch
import logging
from typing import List, Optional

from .config import Config, SafetyConfig
from .models import CriticalActionError

logger = logging.getLogger(__name__)


def check_action(
    entity_id: str,
    action: str,
    config: Optional[SafetyConfig] = None,
    force: bool = False,
) -> None:
    """Check if an action on an entity is allowed based on safety configuration.

    Args:
        entity_id: Target entity ID
        action: Action name (e.g., turn_on, turn_off, toggle)
        config: Safety configuration. If None, uses default (level 3)
        force: Whether --force flag was provided

    Raises:
        CriticalActionError: If action requires user confirmation
        PermissionError: If entity is blocked
    """
    # Use default safety config if not provided
    if config is None:
        config = SafetyConfig()

    # Safety level 0: no checks
    if config.level == 0:
        logger.debug(f"Safety level 0: allowing {action} on {entity_id}")
        return

    # Check blocked entities (always enforced, even with --force)
    if is_blocked(entity_id, config.blocked_entities):
        logger.error(f"BLOCKED: {action} on {entity_id} (entity in blocked list)")
        raise PermissionError(
            f"❌ Entity {entity_id} is BLOCKED in configuration.\n"
            f"This entity cannot be controlled via moltbot-ha for safety reasons.\n"
            f"Remove from blocked_entities in config to allow."
        )

    # Check allowlist if configured
    if config.allowed_entities and not is_allowed(entity_id, config.allowed_entities):
        logger.error(f"DENIED: {action} on {entity_id} (not in allowlist)")
        raise PermissionError(
            f"❌ Entity {entity_id} is not in the allowlist.\n"
            f"Add to allowed_entities in config to allow access."
        )

    # Extract domain from entity_id
    domain = entity_id.split(".", 1)[0]

    # Safety level 3: check critical domains
    if config.level >= 3 and domain in config.critical_domains:
        if not force:
            logger.warning(f"CRITICAL: {action} on {entity_id} requires confirmation")
            raise CriticalActionError(entity_id, action)
        else:
            logger.warning(f"FORCED: {action} on {entity_id} (critical domain, using --force)")

    # Safety level 2: all write operations require confirmation
    if config.level >= 2 and action in ["turn_on", "turn_off", "toggle", "set"]:
        if not force:
            logger.info(f"CONFIRM: {action} on {entity_id} (safety level 2)")
            raise CriticalActionError(entity_id, action)

    # Action allowed
    logger.debug(f"ALLOWED: {action} on {entity_id}")


def is_blocked(entity_id: str, blocked_list: List[str]) -> bool:
    """Check if entity is in blocked list (supports wildcards).

    Args:
        entity_id: Entity ID to check
        blocked_list: List of blocked patterns

    Returns:
        True if entity is blocked
    """
    for pattern in blocked_list:
        if fnmatch.fnmatch(entity_id, pattern):
            return True
    return False


def is_allowed(entity_id: str, allowed_list: List[str]) -> bool:
    """Check if entity is in allowed list (supports wildcards).

    Args:
        entity_id: Entity ID to check
        allowed_list: List of allowed patterns

    Returns:
        True if entity is allowed
    """
    if not allowed_list:
        return True  # Empty allowlist means everything is allowed

    for pattern in allowed_list:
        if fnmatch.fnmatch(entity_id, pattern):
            return True
    return False


def get_domain(entity_id: str) -> str:
    """Extract domain from entity ID.

    Args:
        entity_id: Entity ID (e.g., light.kitchen)

    Returns:
        Domain (e.g., light)
    """
    return entity_id.split(".", 1)[0]
