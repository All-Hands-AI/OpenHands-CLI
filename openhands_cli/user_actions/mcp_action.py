from prompt_toolkit import HTML, print_formatted_text

from openhands_cli.user_actions.types import UserConfirmation
from openhands_cli.user_actions.utils import cli_confirm


def ask_mcp_configuration_choice() -> tuple[UserConfirmation, int]:
    """Ask user to select an MCP configuration option.

    Returns:
        Tuple of (UserConfirmation, option_number) where:
        - UserConfirmation.ACCEPT with option_number (1-6) for valid selections
        - UserConfirmation.DEFER when user chooses to go back or cancels
    """

    # MCP configuration options
    options = [
        "Configure MCP Server",
        "Manage Server Connections",
        "View Server Status",
        "Test Connection",
        "Import/Export Configuration",
        "Advanced Settings",
        "Return to main menu",
    ]

    try:
        choice_index = cli_confirm(
            question="Select an MCP configuration option:",
            choices=options,
            escapable=True,
        )
    except (EOFError, KeyboardInterrupt):
        print_formatted_text(HTML("\n<grey>Returning to main menu...</grey>"))
        return UserConfirmation.DEFER, 0

    # If user selected "Return to main menu" (last option)
    if choice_index == len(options) - 1:
        return UserConfirmation.DEFER, 0

    # Return ACCEPT with the option number (1-based indexing)
    return UserConfirmation.ACCEPT, choice_index + 1
