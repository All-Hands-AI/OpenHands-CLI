"""Display functions for the OpenHands CLI TUI."""

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear

from openhands_cli import __version__
from openhands_cli.pt_style import get_cli_style

from .commands import COMMANDS

DEFAULT_STYLE = get_cli_style()


def display_banner(session_id: str) -> None:
    """Display the OpenHands CLI banner."""
    print_formatted_text(
        HTML(r"""<gold>
     ___                    _   _                 _
    /  _ \ _ __   ___ _ __ | | | | __ _ _ __   __| |___
    | | | | '_ \ / _ \ '_ \| |_| |/ _` | '_ \ / _` / __|
    | |_| | |_) |  __/ | | |  _  | (_| | | | | (_| \__ \
    \___ /| .__/ \___|_| |_|_| |_|\__,_|_| |_|\__,_|___/
          |_|
    </gold>"""),
        style=DEFAULT_STYLE,
    )

    print_formatted_text(HTML(f"<grey>OpenHands CLI v{__version__}</grey>"))

    print_formatted_text("")
    print_formatted_text(HTML(f"<grey>Initialized conversation {session_id}</grey>"))
    print_formatted_text("")


def display_help() -> None:
    """Display help information about available commands."""
    print_formatted_text("")
    print_formatted_text(HTML("<gold>🤖 OpenHands CLI Help</gold>"))
    print_formatted_text(HTML("<grey>Available commands:</grey>"))
    print_formatted_text("")

    for command, description in COMMANDS.items():
        print_formatted_text(HTML(f"  <white>{command}</white> - {description}"))

    print_formatted_text("")
    print_formatted_text(HTML("<grey>Tips:</grey>"))
    print_formatted_text("  • Type / and press Tab to see command suggestions")
    print_formatted_text("  • Use arrow keys to navigate through suggestions")
    print_formatted_text("  • Press Enter to select a command")
    print_formatted_text("")


def display_welcome(session_id: str = "chat") -> None:
    """Display welcome message."""
    clear()
    display_banner(session_id)
    print_formatted_text(HTML("<gold>Let's start building!</gold>"))
    print_formatted_text(
        HTML(
            "<green>What do you want to build? <grey>Type /help for help</grey></green>"
        )
    )
    print()
