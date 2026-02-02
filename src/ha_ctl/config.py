"""Configuration management for moltbot-ha."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# Handle tomli/tomllib based on Python version
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


class ServerConfig(BaseModel):
    """Home Assistant server configuration."""

    url: str
    token: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL starts with http:// or https://."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")


class SafetyConfig(BaseModel):
    """Safety and security configuration."""

    level: int = Field(default=3, ge=0, le=3)
    critical_domains: List[str] = Field(
        default_factory=lambda: ["lock", "alarm_control_panel", "cover"]
    )
    blocked_entities: List[str] = Field(default_factory=list)
    allowed_entities: List[str] = Field(default_factory=list)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    enabled: bool = True
    path: str = "~/.config/moltbot-ha/actions.log"
    level: str = "INFO"

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper


class Config(BaseModel):
    """Main configuration model."""

    server: ServerConfig
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def get_config_path() -> Path:
    """Get the configuration file path."""
    # Check env var first
    if env_path := os.getenv("HA_CTL_CONFIG"):
        return Path(env_path).expanduser()

    # Default location
    return Path("~/.config/moltbot-ha/config.toml").expanduser()


def load_config() -> Config:
    """Load configuration from file and environment variables.

    Priority:
    1. Environment variables (highest)
    2. Config file
    3. Defaults (lowest)

    Returns:
        Config: Loaded configuration

    Raises:
        FileNotFoundError: If config file doesn't exist and required env vars are missing
        ValueError: If configuration is invalid
    """
    config_path = get_config_path()

    # Start with defaults
    config_dict = {
        "server": {},
        "safety": {},
        "logging": {},
    }

    # Load from file if exists
    if config_path.exists():
        if tomllib is None:
            raise RuntimeError(
                "tomli library is required for Python < 3.11. Install with: pip install tomli"
            )
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)
            # Merge file config
            for section in ["server", "safety", "logging"]:
                if section in file_config:
                    config_dict[section].update(file_config[section])

    # Override with environment variables (highest priority)
    if ha_url := os.getenv("HA_URL"):
        config_dict["server"]["url"] = ha_url

    if ha_token := os.getenv("HA_TOKEN"):
        config_dict["server"]["token"] = ha_token

    # Validate we have required fields
    if "url" not in config_dict["server"]:
        raise ValueError(
            "Home Assistant URL not configured. "
            "Set HA_URL environment variable or configure in config file."
        )

    if "token" not in config_dict["server"] or not config_dict["server"]["token"]:
        raise ValueError(
            "Home Assistant token not configured. "
            "Set HA_TOKEN environment variable or configure in config file."
        )

    # Parse and validate with Pydantic
    return Config(**config_dict)


def init_config(force: bool = False) -> Path:
    """Initialize configuration by copying example to config location.

    Args:
        force: Overwrite existing config file

    Returns:
        Path: Path to created config file

    Raises:
        FileExistsError: If config already exists and force=False
    """
    config_path = get_config_path()

    if config_path.exists() and not force:
        raise FileExistsError(f"Configuration already exists at {config_path}")

    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Find example config (relative to this file)
    example_path = Path(__file__).parent / "config.example.toml"

    if not example_path.exists():
        raise FileNotFoundError(f"Example config not found at {example_path}")

    # Copy example to config location
    import shutil

    shutil.copy(example_path, config_path)

    return config_path
