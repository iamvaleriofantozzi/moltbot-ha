"""Logging setup for moltbot-ha."""

import logging
import sys
from pathlib import Path
from typing import List, Optional

from .config import LoggingConfig


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """Setup logging based on configuration.

    Args:
        config: Logging configuration. If None, uses default console logging.
    """
    # Default to INFO level console logging
    if config is None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[logging.StreamHandler(sys.stderr)],
        )
        return

    # Parse log level
    log_level = getattr(logging, config.level, logging.INFO)

    # Setup formatters
    detailed_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    simple_formatter = logging.Formatter("%(message)s")

    # Setup handlers
    handlers: List[logging.Handler] = []

    # File handler if enabled
    if config.enabled:
        log_path = Path(config.path).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(detailed_formatter)
        handlers.append(file_handler)

    # Console handler (always present for CLI output)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # Only warnings/errors to console
    console_handler.setFormatter(simple_formatter)
    handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def log_action(entity_id: str, action: str, forced: bool = False, allowed: bool = True) -> None:
    """Log an action taken on an entity.

    Args:
        entity_id: Target entity ID
        action: Action name (e.g., turn_on, turn_off)
        forced: Whether --force flag was used
        allowed: Whether action was allowed
    """
    logger = logging.getLogger(__name__)

    status = "ALLOWED" if allowed else "DENIED"
    force_flag = " [FORCED]" if forced else ""

    log_message = f"{status}: {action} on {entity_id}{force_flag}"

    if allowed:
        if forced:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    else:
        logger.error(log_message)
