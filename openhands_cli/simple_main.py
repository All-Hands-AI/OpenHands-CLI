#!/usr/bin/env python3
"""
Simple main entry point for OpenHands CLI.
This is a simplified version that demonstrates the TUI functionality.
"""

import sys
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from openhands_cli.pt_style import get_cli_style
from openhands_cli import __version__

DEFAULT_STYLE=get_cli_style()

def display_banner(session_id: str) -> None:
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

    print_formatted_text(HTML(f'<grey>OpenHands CLI v{__version__}</grey>'))

    print_formatted_text('')
    print_formatted_text(HTML(f'<grey>Initialized conversation {session_id}</grey>'))
    print_formatted_text('')


def main():
    """Main entry point for the OpenHands CLI."""
    print_formatted_text(HTML('<gold>OpenHands CLI</gold>'))
    print_formatted_text(HTML('<grey>Terminal User Interface for OpenHands AI Agent</grey>'))
    print()
    
    print("🚀 Welcome to OpenHands CLI!")
    print("This is a simplified version of the OpenHands Terminal User Interface.")
    print()
    print("Available features:")
    print("  • Terminal User Interface (TUI) components")
    print("  • Prompt Toolkit integration")
    print("  • Agent SDK integration")
    print()
    print("To use the full functionality, ensure you have:")
    print("  1. OpenHands agent SDK properly configured")
    print("  2. Required environment variables set")
    print("  3. Proper authentication tokens")
    print()
    
    # For now, just show that the CLI is working
    try:
        display_banner(session_id='setup')
    except ImportError as e:
        print(f"Note: Full TUI functionality requires additional setup: {e}")
    
    print("CLI setup complete! 🎉")
    return 0

if __name__ == "__main__":
    sys.exit(main())