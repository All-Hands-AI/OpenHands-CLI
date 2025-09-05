import asyncio
import sys
import threading
import time
from collections.abc import Generator

from prompt_toolkit import print_formatted_text
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML, FormattedText, StyleAndTextTuples
from prompt_toolkit.lexers import Lexer

from openhands_cli import __version__
from openhands_cli.pt_style import COLOR_GOLD, get_cli_style

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


class CustomDiffLexer(Lexer):
    """Custom lexer for the specific diff format."""

    def lex_document(self, document: Document) -> StyleAndTextTuples:
        lines = document.lines

        def get_line(lineno: int) -> StyleAndTextTuples:
            line = lines[lineno]
            if line.startswith("+"):
                return [("ansigreen", line)]
            elif line.startswith("-"):
                return [("ansired", line)]
            elif line.startswith("[") or line.startswith("("):
                # Style for metadata lines like [Existing file...] or (content...)
                return [("bold", line)]
            else:
                # Default style for other lines
                return [("", line)]

        return get_line


# CLI initialization and startup display functions
def display_runtime_initialization_message(runtime: str) -> None:
    print_formatted_text("")
    print_formatted_text(HTML("<grey>⚙️ Starting local runtime...</grey>"))
    print_formatted_text("")


def display_initialization_animation(text: str, is_loaded: asyncio.Event) -> None:
    ANIMATION_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    i = 0
    while not is_loaded.is_set():
        sys.stdout.write("\n")
        sys.stdout.write(
            f"\033[s\033[J\033[38;2;255;215;0m[{ANIMATION_FRAMES[i % len(ANIMATION_FRAMES)]}] {text}\033[0m\033[u\033[1A"
        )
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1

    sys.stdout.write("\r" + " " * (len(text) + 10) + "\r")
    sys.stdout.flush()


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


def display_welcome_message(message: str = "") -> None:
    print_formatted_text(
        HTML("<gold>Let's start building!</gold>\n"), style=DEFAULT_STYLE
    )

    if message:
        print_formatted_text(
            HTML(f"{message} <grey>Type /help for help</grey>"),
            style=DEFAULT_STYLE,
        )
    else:
        print_formatted_text(
            HTML("What do you want to build? <grey>Type /help for help</grey>"),
            style=DEFAULT_STYLE,
        )


def display_initial_user_prompt(prompt: str) -> None:
    print_formatted_text(
        FormattedText(
            [
                ("", "\n"),
                (COLOR_GOLD, "> "),
                ("", prompt),
            ]
        )
    )


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


# Interactive command output display functions
def display_help() -> None:
    # Version header and introduction
    print_formatted_text(
        HTML(
            f"\n<grey>OpenHands CLI v{__version__}</grey>\n"
            "<gold>OpenHands CLI lets you interact with the OpenHands agent from the command line.</gold>\n"
        )
    )

    # Usage examples
    print_formatted_text("Things that you can try:")
    print_formatted_text(
        HTML(
            "• Ask questions about the codebase <grey>> How does main.py work?</grey>\n"
            "• Edit files or add new features <grey>> Add a new function to ...</grey>\n"
            "• Find and fix issues <grey>> Fix the type error in ...</grey>\n"
        )
    )

    # Tips section
    print_formatted_text(
        "Some tips to get the most out of OpenHands:\n"
        "• Be as specific as possible about the desired outcome or the problem to be solved.\n"
        "• Provide context, including relevant file paths and line numbers if available.\n"
        "• Break large tasks into smaller, manageable prompts.\n"
        "• Include relevant error messages or logs.\n"
        "• Specify the programming language or framework, if not obvious.\n"
    )

    # Commands section
    print_formatted_text(HTML("Interactive commands:"))
    commands_html = ""
    for command, description in COMMANDS.items():
        commands_html += f"<gold><b>{command}</b></gold> - <grey>{description}</grey>\n"
    print_formatted_text(HTML(commands_html))

    # Footer
    print_formatted_text(
        HTML(
            "<grey>Learn more at: https://docs.all-hands.dev/usage/getting-started</grey>"
        )
    )


def display_agent_running_message() -> None:
    print_formatted_text("")
    print_formatted_text(
        HTML("<gold>Agent running...</gold> <grey>(Press Ctrl-P to pause)</grey>")
    )
