
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
