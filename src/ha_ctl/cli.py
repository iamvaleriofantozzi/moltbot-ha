"""Main CLI application for moltbot-ha."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .client import HomeAssistantClient
from .config import Config, init_config, load_config
from .logger import log_action, setup_logging
from .models import ApiError, CriticalActionError
from .safety import check_action

app = typer.Typer(
    name="moltbot-ha",
    help="Home Assistant control CLI for Moltbot agents",
    add_completion=False,
)

console = Console()

# Global config for access in commands
_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get loaded configuration."""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
        setup_logging(_global_config.logging)
    return _global_config


def get_client() -> HomeAssistantClient:
    """Get configured Home Assistant client.

    Returns:
        Configured client instance

    Raises:
        typer.Exit: If configuration is invalid
    """
    try:
        config = get_config()
        return HomeAssistantClient(config.server.url, config.server.token)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print(
            "\n[yellow]Hint:[/yellow] Run 'moltbot-ha config init' to create a config file",
        )
        raise typer.Exit(1)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"moltbot-ha version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Home Assistant control CLI."""
    pass


@app.command()
def test() -> None:
    """Test connection to Home Assistant."""
    try:
        client = get_client()
        client.test_connection()
        console.print("[green]✓[/green] Connected to Home Assistant successfully")
    except ApiError as e:
        console.print(f"[red]✗[/red] Connection failed: {e}")
        raise typer.Exit(1)


# ============================================================================
# LIST COMMAND
# ============================================================================


@app.command()
def list(
    domain: Optional[str] = typer.Argument(None, help="Filter by domain (e.g., light, switch)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all entities or filter by domain."""
    try:
        client = get_client()
        states = client.get_states()

        # Filter by domain if specified
        if domain:
            states = [s for s in states if s.domain == domain]

        if not states:
            if domain:
                console.print(f"[yellow]No entities found for domain: {domain}[/yellow]")
            else:
                console.print("[yellow]No entities found[/yellow]")
            return

        # JSON output
        if json_output:
            data = [
                {
                    "entity_id": s.entity_id,
                    "state": s.state,
                    "friendly_name": s.friendly_name,
                    "attributes": s.attributes,
                }
                for s in states
            ]
            console.print(json.dumps(data, indent=2))
            return

        # Table output
        table = Table(title=f"Entities{f' ({domain})' if domain else ''}")
        table.add_column("Entity ID", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Friendly Name", style="yellow")

        for state in states:
            table.add_row(state.entity_id, state.state, state.friendly_name)

        console.print(table)

    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ============================================================================
# STATE COMMAND
# ============================================================================


@app.command()
def state(
    entity_id: str = typer.Argument(..., help="Entity ID (e.g., light.kitchen)"),
) -> None:
    """Get state of a specific entity."""
    try:
        client = get_client()
        entity_state = client.get_state(entity_id)

        # Output as JSON for easy parsing
        output = {
            "entity_id": entity_state.entity_id,
            "state": entity_state.state,
            "attributes": entity_state.attributes,
            "last_changed": entity_state.last_changed.isoformat(),
            "last_updated": entity_state.last_updated.isoformat(),
        }
        console.print(json.dumps(output, indent=2))

    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ============================================================================
# ON/OFF/TOGGLE COMMANDS
# ============================================================================


@app.command()
def on(
    entity_id: str = typer.Argument(..., help="Entity ID to turn on"),
    force: bool = typer.Option(False, "--force", help="Force action (skip confirmation)"),
) -> None:
    """Turn on an entity."""
    try:
        config = get_config()
        client = get_client()

        # Safety check
        check_action(entity_id, "turn_on", config.safety, force)

        # Execute
        client.call_service_for_entity(entity_id, "turn_on")

        # Log
        log_action(entity_id, "turn_on", forced=force, allowed=True)

        console.print(f"[green]✓[/green] {entity_id} turned on")

    except CriticalActionError as e:
        console.print(str(e))
        raise typer.Exit(1)
    except PermissionError as e:
        console.print(str(e))
        log_action(entity_id, "turn_on", forced=force, allowed=False)
        raise typer.Exit(1)
    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def off(
    entity_id: str = typer.Argument(..., help="Entity ID to turn off"),
    force: bool = typer.Option(False, "--force", help="Force action (skip confirmation)"),
) -> None:
    """Turn off an entity."""
    try:
        config = get_config()
        client = get_client()

        # Safety check
        check_action(entity_id, "turn_off", config.safety, force)

        # Execute
        client.call_service_for_entity(entity_id, "turn_off")

        # Log
        log_action(entity_id, "turn_off", forced=force, allowed=True)

        console.print(f"[green]✓[/green] {entity_id} turned off")

    except CriticalActionError as e:
        console.print(str(e))
        raise typer.Exit(1)
    except PermissionError as e:
        console.print(str(e))
        log_action(entity_id, "turn_off", forced=force, allowed=False)
        raise typer.Exit(1)
    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def toggle(
    entity_id: str = typer.Argument(..., help="Entity ID to toggle"),
    force: bool = typer.Option(False, "--force", help="Force action (skip confirmation)"),
) -> None:
    """Toggle an entity on/off."""
    try:
        config = get_config()
        client = get_client()

        # Safety check
        check_action(entity_id, "toggle", config.safety, force)

        # Execute
        client.call_service_for_entity(entity_id, "toggle")

        # Log
        log_action(entity_id, "toggle", forced=force, allowed=True)

        console.print(f"[green]✓[/green] {entity_id} toggled")

    except CriticalActionError as e:
        console.print(str(e))
        raise typer.Exit(1)
    except PermissionError as e:
        console.print(str(e))
        log_action(entity_id, "toggle", forced=force, allowed=False)
        raise typer.Exit(1)
    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ============================================================================
# SET COMMAND
# ============================================================================


@app.command()
def set(
    entity_id: str = typer.Argument(..., help="Entity ID"),
    attributes: List[str] = typer.Argument(..., help="Attributes as key=value pairs"),
    force: bool = typer.Option(False, "--force", help="Force action (skip confirmation)"),
) -> None:
    """Set attributes on an entity (e.g., brightness, color)."""
    try:
        config = get_config()
        client = get_client()

        # Parse attributes
        data = {"entity_id": entity_id}
        for attr_str in attributes:
            if "=" not in attr_str:
                console.print(f"[red]Error:[/red] Invalid attribute format: {attr_str}")
                console.print("[yellow]Expected format:[/yellow] key=value")
                raise typer.Exit(1)

            key, value = attr_str.split("=", 1)

            # Try to parse as number or boolean
            if value.lower() in ("true", "yes", "on"):
                parsed_value = True
            elif value.lower() in ("false", "no", "off"):
                parsed_value = False
            else:
                try:
                    # Try int
                    parsed_value = int(value)
                except ValueError:
                    try:
                        # Try float
                        parsed_value = float(value)
                    except ValueError:
                        # Keep as string
                        parsed_value = value

            data[key] = parsed_value

        # Safety check
        check_action(entity_id, "set", config.safety, force)

        # Execute (use turn_on service with attributes)
        domain = entity_id.split(".", 1)[0]
        client.call_service(domain, "turn_on", data)

        # Log
        log_action(entity_id, "set", forced=force, allowed=True)

        console.print(f"[green]✓[/green] {entity_id} updated")

    except CriticalActionError as e:
        console.print(str(e))
        raise typer.Exit(1)
    except PermissionError as e:
        console.print(str(e))
        log_action(entity_id, "set", forced=force, allowed=False)
        raise typer.Exit(1)
    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ============================================================================
# CALL COMMAND
# ============================================================================


@app.command()
def call(
    service: str = typer.Argument(..., help="Service to call (format: domain.service)"),
    params: List[str] = typer.Argument(None, help="Service parameters as key=value pairs"),
    json_data: Optional[str] = typer.Option(None, "--json", help="Service data as JSON string"),
    force: bool = typer.Option(False, "--force", help="Force action (skip confirmation)"),
) -> None:
    """Call any Home Assistant service."""
    try:
        config = get_config()
        client = get_client()

        # Parse service
        if "." not in service:
            console.print(f"[red]Error:[/red] Invalid service format: {service}")
            console.print("[yellow]Expected format:[/yellow] domain.service")
            raise typer.Exit(1)

        domain, service_name = service.split(".", 1)

        # Parse data
        if json_data:
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error:[/red] Invalid JSON: {e}")
                raise typer.Exit(1)
        else:
            data = {}
            if params:
                for param_str in params:
                    if "=" not in param_str:
                        console.print(
                            f"[red]Error:[/red] Invalid parameter format: {param_str}",
                        )
                        raise typer.Exit(1)

                    key, value = param_str.split("=", 1)

                    # Parse value
                    if value.lower() in ("true", "yes"):
                        parsed_value = True
                    elif value.lower() in ("false", "no"):
                        parsed_value = False
                    else:
                        try:
                            parsed_value = int(value)
                        except ValueError:
                            try:
                                parsed_value = float(value)
                            except ValueError:
                                parsed_value = value

                    data[key] = parsed_value

        # Safety check if entity_id present
        if "entity_id" in data and not force:
            entity_id = data["entity_id"]
            check_action(entity_id, service_name, config.safety, force)

        # Execute
        client.call_service(domain, service_name, data)

        console.print(f"[green]✓[/green] Service {service} called successfully")

    except CriticalActionError as e:
        console.print(str(e))
        raise typer.Exit(1)
    except PermissionError as e:
        console.print(str(e))
        raise typer.Exit(1)
    except ApiError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ============================================================================
# CONFIG COMMAND
# ============================================================================

config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Initialize configuration file from template."""
    try:
        config_path = init_config(force=force)
        console.print(f"[green]✓[/green] Configuration created at: {config_path}")
        console.print("\n[yellow]Next steps:[/yellow]")
        console.print("1. Edit the config file and set your Home Assistant URL")
        console.print("2. Set HA_TOKEN environment variable or add token to config")
        console.print("3. Run 'moltbot-ha test' to verify connection")
    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[yellow]Use --force to overwrite[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@config_app.command("show")
def config_show() -> None:
    """Show current configuration (token masked)."""
    try:
        config = get_config()

        # Build display dict with masked token
        config_display = {
            "server": {
                "url": config.server.url,
                "token": "***" + (config.server.token[-4:] if config.server.token else ""),
            },
            "safety": {
                "level": config.safety.level,
                "critical_domains": config.safety.critical_domains,
                "blocked_entities": config.safety.blocked_entities,
                "allowed_entities": config.safety.allowed_entities,
            },
            "logging": {
                "enabled": config.logging.enabled,
                "path": config.logging.path,
                "level": config.logging.level,
            },
        }

        console.print(json.dumps(config_display, indent=2))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def test() -> None:
    """Test connection to Home Assistant."""
    try:
        client = get_client()
        client.test_connection()
        console.print("[green]✓[/green] Connected to Home Assistant successfully")
    except ApiError as e:
        console.print(f"[red]✗[/red] Connection failed: {e}")
        raise typer.Exit(1)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Home Assistant control CLI."""
    pass


if __name__ == "__main__":
    app()
