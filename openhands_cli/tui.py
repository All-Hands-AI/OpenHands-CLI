from collections.abc import Generator

from prompt_toolkit import print_formatted_text
from prompt_toolkit.application import Application
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.widgets import Frame, Label, RadioList, TextArea

from openhands_cli import __version__
from openhands_cli.pt_style import get_cli_style

DEFAULT_STYLE = get_cli_style()

# Available commands with descriptions
COMMANDS = {
    "/exit": "Exit the application",
    "/help": "Display available commands",
    "/clear": "Clear the screen",
    "/status": "Display conversation details",
    "/confirm": "Toggle confirmation mode on/off",
    "/new": "Create a new conversation",
}


class CommandCompleter(Completer):
    """Custom completer for commands with interactive dropdown."""

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Generator[Completion, None, None]:
        text = document.text_before_cursor.lstrip()
        if text.startswith("/"):
            for command, description in COMMANDS.items():
                if command.startswith(text):
                    yield Completion(
                        command,
                        start_position=-len(text),
                        display_meta=description,
                        style="bg:ansidarkgray fg:gold",
                    )


# --------- UI helpers for parity with OpenHands CLI ---------


def build_command_frame(command: str) -> Frame:
    """Build a purple-framed box for a command."""
    text = f"$ {command}".rstrip()
    area = TextArea(text=text, read_only=True, wrap_lines=True, style="cmdbox")
    return Frame(area, title="Command", style="cmdtitle")


def build_output_frame(output: str) -> Frame:
    """Build a gray-framed box for command output."""
    area = TextArea(
        text=output.rstrip("\n"), read_only=True, wrap_lines=True, style="outbox"
    )
    return Frame(area, title="Command Output", style="outtitle")


def display_command_box(command: str) -> None:
    print_formatted_text("")
    print_container(build_command_frame(command))


def display_output_box(output: str) -> None:
    print_formatted_text("")
    print_container(build_output_frame(output))


# --------- Confirmation dropdown using prompt_toolkit Application ---------


def build_confirmation_app(
    options: list[tuple[str, str]], title: str = "Choose an option:"
) -> Application:
    """Build an Application presenting a radio-list dropdown.

    Args:
        options: List of (key, label) pairs
        title: Title label

    Returns:
        prompt_toolkit Application that returns the selected key on exit
    """
    radio = RadioList(options)

    def _accept(_) -> None:  # type: ignore[no-untyped-def]
        app.exit(result=radio.current_value)

    # Use a minimal layout with a label and radio list
    root_container = HSplit(
        [
            Window(height=1, char="\n"),
            Label(title),
            radio,
        ]
    )
    app = Application(
        layout=Layout(root_container),
        key_bindings=None,
        mouse_support=True,
        full_screen=False,
        style=DEFAULT_STYLE,
    )
    # Bind Enter to accept
    radio.control.key_bindings.add("enter")(_accept)  # type: ignore[attr-defined]
    return app


def confirm_dropdown() -> str:
    """Show confirmation dropdown and return the selected key.

    Returns one of: 'yes', 'no', 'always'
    """
    options: list[tuple[str, str]] = [
        ("yes", "Yes, proceed"),
        ("no", "No (and allow to enter instructions)"),
        ("always", "Always proceed (don't ask again)"),
    ]
    app = build_confirmation_app(options)
    return app.run()  # type: ignore[no-any-return]


# --------- Existing banners and help ---------


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
