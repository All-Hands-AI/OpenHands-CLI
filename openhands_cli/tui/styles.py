"""Centralized styling constants for TUI components."""

# Completion styling
COMPLETION_STYLE = "bg:ansidarkgray fg:gold"

# Common HTML color tags for consistent formatting
COLORS = {
    "gold": "gold",
    "grey": "grey",
    "white": "white",
    "green": "green",
    "red": "red",
    "blue": "blue",
}


# Common styling patterns
def format_command(text: str) -> str:
    """Format text as a command."""
    return f"<white>{text}</white>"


def format_description(text: str) -> str:
    """Format text as a description."""
    return f"<grey>{text}</grey>"


def format_header(text: str) -> str:
    """Format text as a header."""
    return f"<gold>{text}</gold>"


def format_success(text: str) -> str:
    """Format text as success message."""
    return f"<green>{text}</green>"


def format_error(text: str) -> str:
    """Format text as error message."""
    return f"<red>{text}</red>"
