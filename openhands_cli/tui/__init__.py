"""TUI (Terminal User Interface) module for OpenHands CLI.

This module provides a modular TUI architecture with separate components for:
- Command definitions and handling
- Auto-completion functionality
- Display functions (banners, help, menus)
- Styling and formatting
- Specialized UI modules (MCP, etc.)
"""

# Import main TUI components for backward compatibility
from .commands import COMMANDS
from .completers import CommandCompleter
from .display import DEFAULT_STYLE, display_banner, display_help, display_welcome

__all__ = [
    "COMMANDS",
    "CommandCompleter",
    "DEFAULT_STYLE",
    "display_banner",
    "display_help",
    "display_welcome",
]
