"""
MCP (Model Context Protocol) UI functionality for OpenHands CLI.
Provides interactive configuration and management of MCP settings.
"""

from typing import cast

from prompt_toolkit import print_formatted_text, prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear

from openhands_cli.pt_style import get_cli_style
from openhands_cli.user_actions import UserConfirmation, ask_mcp_configuration_choice
from openhands_cli.user_actions.utils import cli_confirm

DEFAULT_STYLE = get_cli_style()

# MCP configuration options (for display purposes)
MCP_OPTIONS = {
    "1": "Configure MCP Server",
    "2": "Manage Server Connections",
    "3": "View Server Status",
    "4": "Test Connection",
    "5": "Import/Export Configuration",
    "6": "Advanced Settings",
    "back": "Return to main menu",
}


def display_mcp_banner() -> None:
    """Display MCP configuration banner."""
    print_formatted_text("")
    print_formatted_text(HTML("<gold>🔧 MCP Configuration</gold>"))
    print_formatted_text(HTML("<grey>Model Context Protocol Settings</grey>"))
    print_formatted_text("")


def display_mcp_menu() -> None:
    """Display the main MCP configuration menu."""
    display_mcp_banner()

    print_formatted_text(HTML("<white>Available options:</white>"))
    print_formatted_text("")

    for option, description in MCP_OPTIONS.items():
        if option == "back":
            print_formatted_text("")
            print_formatted_text(HTML(f"  <yellow>{option}</yellow> - {description}"))
        else:
            print_formatted_text(HTML(f"  <white>{option}</white> - {description}"))

    print_formatted_text("")
    print_formatted_text(HTML("<grey>Tips:</grey>"))
    print_formatted_text("  • Type the option number and press Enter")
    print_formatted_text("  • Use Tab for auto-completion")
    print_formatted_text("  • Type 'back' to return to main menu")
    print_formatted_text("")


def _display_server_config_header() -> None:
    """Display the server configuration header."""
    print_formatted_text("")
    print_formatted_text(HTML("<gold>🔧 Add MCP Server</gold>"))
    print_formatted_text(
        HTML("<grey>Configure a new Model Context Protocol server</grey>")
    )
    print_formatted_text("")


def _display_error(message: str) -> None:
    """Display an error message."""
    print_formatted_text(HTML(f"<red>✗ {message}</red>"))


def _display_warning(message: str) -> None:
    """Display a warning message."""
    print_formatted_text(HTML(f"<yellow>⚠ Warning: {message}</yellow>"))


def _display_success_message(
    server_name: str, command: str, args: list[str], env: dict[str, str]
) -> None:
    """Display success message with server configuration details."""
    print_formatted_text("")
    print_formatted_text(
        HTML(f"<green>✓ Successfully added MCP server '{server_name}'</green>")
    )
    print_formatted_text("")
    print_formatted_text(HTML("<white>Server configuration:</white>"))
    print_formatted_text(f"  Name: {server_name}")
    print_formatted_text(f"  Command: {command}")
    if args:
        print_formatted_text(f"  Arguments: {', '.join(args)}")
    if env:
        print_formatted_text(
            f"  Environment: {', '.join(f'{k}={v}' for k, v in env.items())}"
        )
    print_formatted_text("")
    print_formatted_text(
        HTML("<grey>Note: Restart the agent to load tools from this server</grey>")
    )


def _prompt_server_name() -> str:
    """Prompt for server name with instructions."""
    print_formatted_text(HTML("<white>Server name (unique identifier):</white>"))
    return cast(str, prompt("Name: ", style=DEFAULT_STYLE)).strip()


def _prompt_command() -> str:
    """Prompt for server command with examples."""
    print_formatted_text("")
    print_formatted_text(HTML("<white>Command to run the server:</white>"))
    print_formatted_text(
        HTML("<grey>Examples: 'uvx', 'python', 'node', '/path/to/executable'</grey>")
    )
    return cast(str, prompt("Command: ", style=DEFAULT_STYLE)).strip()


def _prompt_arguments() -> list[str]:
    """Prompt for server arguments and parse them."""
    print_formatted_text("")
    print_formatted_text(HTML("<white>Arguments (optional, comma-separated):</white>"))
    print_formatted_text(
        HTML("<grey>Examples: 'mcp-server-fetch', '--port 8080', 'server.js'</grey>")
    )
    args_input = cast(str, prompt("Arguments: ", style=DEFAULT_STYLE)).strip()

    if not args_input:
        return []

    return [arg.strip() for arg in args_input.split(",") if arg.strip()]


def _prompt_environment() -> dict[str, str]:
    """Prompt for environment variables and parse them."""
    print_formatted_text("")
    print_formatted_text(
        HTML(
            "<white>Environment variables (optional, KEY=VALUE format, comma-separated):</white>"
        )
    )
    print_formatted_text(HTML("<grey>Examples: 'API_KEY=secret', 'PORT=8080'</grey>"))
    env_input = cast(str, prompt("Environment: ", style=DEFAULT_STYLE)).strip()

    if not env_input:
        return {}

    env = {}
    try:
        for env_pair in env_input.split(","):
            env_pair = env_pair.strip()
            if "=" in env_pair:
                key, value = env_pair.split("=", 1)
                env[key.strip()] = value.strip()
    except Exception as e:
        _display_warning(f"Could not parse environment variables: {e}")
        return {}

    return env


def handle_mcp_server_config() -> None:
    """Handle MCP server configuration - add new MCP servers."""
    from openhands_cli.mcp import mcp_session

    _display_server_config_header()

    try:
        # Get server configuration from user
        server_name = _prompt_server_name()
        if not server_name:
            _display_error("Server name cannot be empty")
            return

        if mcp_session.get_server(server_name):
            _display_error(f"Server '{server_name}' already exists")
            return

        command = _prompt_command()
        if not command:
            _display_error("Command cannot be empty")
            return

        args = _prompt_arguments()
        env = _prompt_environment()

        # Add the server
        success = mcp_session.add_server(server_name, command, args, env)

        if success:
            _display_success_message(server_name, command, args, env)
        else:
            _display_error(f"Failed to add server '{server_name}'")

    except KeyboardInterrupt:
        print_formatted_text(HTML("\n<grey>Server configuration cancelled</grey>"))
    except Exception as e:
        _display_error(f"Error configuring server: {e}")


def handle_server_connections() -> None:
    """Handle server connection management (no-op placeholder)."""
    print_formatted_text("")
    print_formatted_text(HTML("<yellow>🔗 Server Connection Management</yellow>"))
    print_formatted_text(HTML("<grey>This feature is coming soon...</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>Future functionality will include:</grey>"))
    print_formatted_text("  • View active connections")
    print_formatted_text("  • Connect/disconnect servers")
    print_formatted_text("  • Monitor connection health")
    print_formatted_text("  • Manage connection pools")
    print_formatted_text("")


def handle_server_status() -> None:
    """Handle server status display (no-op placeholder)."""
    print_formatted_text("")
    print_formatted_text(HTML("<yellow>📊 Server Status</yellow>"))
    print_formatted_text(HTML("<grey>This feature is coming soon...</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>Future functionality will include:</grey>"))
    print_formatted_text("  • Server health monitoring")
    print_formatted_text("  • Connection statistics")
    print_formatted_text("  • Performance metrics")
    print_formatted_text("  • Error logs and diagnostics")
    print_formatted_text("")


def handle_test_connection() -> None:
    """Handle connection testing (no-op placeholder)."""
    print_formatted_text("")
    print_formatted_text(HTML("<yellow>🧪 Connection Test</yellow>"))
    print_formatted_text(HTML("<grey>This feature is coming soon...</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>Future functionality will include:</grey>"))
    print_formatted_text("  • Test server connectivity")
    print_formatted_text("  • Validate authentication")
    print_formatted_text("  • Check protocol compatibility")
    print_formatted_text("  • Measure response times")
    print_formatted_text("")


def handle_import_export() -> None:
    """Handle configuration import/export (no-op placeholder)."""
    print_formatted_text("")
    print_formatted_text(HTML("<yellow>📁 Import/Export Configuration</yellow>"))
    print_formatted_text(HTML("<grey>This feature is coming soon...</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>Future functionality will include:</grey>"))
    print_formatted_text("  • Export current configuration")
    print_formatted_text("  • Import configuration from file")
    print_formatted_text("  • Backup/restore settings")
    print_formatted_text("  • Share configurations")
    print_formatted_text("")


def handle_advanced_settings() -> None:
    """Handle advanced MCP settings (no-op placeholder)."""
    print_formatted_text("")
    print_formatted_text(HTML("<yellow>⚙️ Advanced Settings</yellow>"))
    print_formatted_text(HTML("<grey>This feature is coming soon...</grey>"))
    print_formatted_text("")
    print_formatted_text(HTML("<grey>Future functionality will include:</grey>"))
    print_formatted_text("  • Protocol version settings")
    print_formatted_text("  • Timeout configurations")
    print_formatted_text("  • Logging preferences")
    print_formatted_text("  • Security settings")
    print_formatted_text("")


def run_mcp_configuration() -> None:
    """Run the interactive MCP configuration interface."""
    while True:
        try:
            display_mcp_menu()

            # Get user choice using standardized action pattern
            confirmation, option_number = ask_mcp_configuration_choice()

            # Handle user choice based on confirmation result
            if confirmation == UserConfirmation.DEFER:
                # User chose to go back or cancelled
                break
            elif confirmation == UserConfirmation.ACCEPT:
                # Handle the selected option (1-based indexing)
                if option_number == 1:
                    handle_mcp_server_config()
                elif option_number == 2:
                    handle_server_connections()
                elif option_number == 3:
                    handle_server_status()
                elif option_number == 4:
                    handle_test_connection()
                elif option_number == 5:
                    handle_import_export()
                elif option_number == 6:
                    handle_advanced_settings()

            # Wait for user to continue using standardized pattern
            continue_options = ["Continue"]
            try:
                cli_confirm(
                    question="Press Enter to continue...",
                    choices=continue_options,
                    initial_selection=0,
                    escapable=False,
                )
            except KeyboardInterrupt:
                # User pressed Ctrl+C during continue prompt, exit gracefully
                print_formatted_text(HTML("<grey>Returning to main menu...</grey>"))
                break
            clear()

        except (KeyboardInterrupt, EOFError):
            print_formatted_text(HTML("\n<grey>Returning to main menu...</grey>"))
            break
