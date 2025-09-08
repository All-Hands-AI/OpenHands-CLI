from prompt_toolkit.application import Application
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from openhands_cli.tui import DEFAULT_STYLE

def cli_confirm(
    question: str = 'Are you sure?',
    choices: list[str] | None = None,
    initial_selection: int = 0,
    header: str | None = None
) -> int:
    """Display a confirmation prompt with the given question and choices.

    Returns the index of the selected choice.
    """
    if choices is None:
        choices = ['Yes', 'No']
    selected = [initial_selection]  # Using list to allow modification in closure

    def get_choice_text() -> list[tuple[str, str]]:
        lines = []

        # Add the question
        lines.append(('class:question', f'{question}\n\n'))

        # Add the choices
        for i, choice in enumerate(choices):
            is_selected = i == selected[0]
            prefix = "> " if is_selected else "  "
            style = 'class:selected' if is_selected else 'class:unselected'
            lines.append((style, f'{prefix}{choice}\n'))

        return lines

    kb = KeyBindings()

    @kb.add('up')
    def _handle_up(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] - 1) % len(choices)



    @kb.add('down')
    def _handle_down(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] + 1) % len(choices)


    @kb.add('enter')
    def _handle_enter(event: KeyPressEvent) -> None:
        event.app.exit(result=selected[0])

    # Create layout with risk-based styling - full width but limited height
    content_window = Window(
        FormattedTextControl(get_choice_text),
        always_hide_cursor=True,
        height=Dimension(max=8),  # Limit height to prevent screen takeover
    )

    
    layout = Layout(HSplit([content_window]))

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=DEFAULT_STYLE,
        full_screen=False,
    )

    return int(app.run(in_thread=True))
