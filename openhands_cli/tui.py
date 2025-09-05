import asyncio
import threading

from openhands_cli.pt_style import get_cli_style

DEFAULT_STYLE = get_cli_style()

# Available commands with descriptions
COMMANDS = {
    "/exit": "Exit the application",
    "/help": "Display available commands",
    "/status": "Display conversation details",
    "/new": "Create a new conversation",
}

print_lock = threading.Lock()

pause_task: asyncio.Task | None = None  # No more than one pause task
