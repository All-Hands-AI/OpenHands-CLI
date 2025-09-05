from prompt_toolkit import HTML, print_formatted_text

from openhands_cli import __version__
from openhands_cli.tui import DEFAULT_STYLE


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
