import asyncio
import sys
import time

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML, FormattedText

from openhands_cli import __version__
from openhands_cli.pt_style import COLOR_GOLD
from openhands_cli.tui.commands import DEFAULT_STYLE


def display_runtime_initialization_message() -> None:
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
