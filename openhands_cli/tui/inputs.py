import asyncio
import contextlib
from collections.abc import Generator
from typing import Any

from openhands.sdk import Conversation
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.application import Application
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.patch_stdout import patch_stdout

from openhands_cli.tui.commands import COMMANDS, DEFAULT_STYLE

pause_task: asyncio.Task | None = None  # No more than one pause task


class CommandCompleter(Completer):
    """Custom completer for commands."""

    def __init__(self, agent_paused: str) -> None:
        super().__init__()
        self.agent_paused = agent_paused

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Generator[Completion, None, None]:
        text = document.text_before_cursor.lstrip()
        if text.startswith("/"):
            available_commands = dict(COMMANDS)
            if not self.agent_paused:
                available_commands.pop("/resume", None)

            for command, description in available_commands.items():
                if command.startswith(text):
                    yield Completion(
                        command,
                        start_position=-len(text),
                        display_meta=description,
                        style="bg:ansidarkgray fg:gold",
                    )


def create_prompt_session() -> PromptSession[str]:
    """Creates a prompt session with VI mode enabled if specified in the config."""
    return PromptSession(style=DEFAULT_STYLE, vi_mode=False)


async def read_prompt_input(agent_state: str, multiline: bool = False) -> str:
    try:
        prompt_session = create_prompt_session()
        prompt_session.completer = (
            CommandCompleter(agent_state) if not multiline else None
        )

        if multiline:
            kb = KeyBindings()

            @kb.add("c-d")
            def _(event: KeyPressEvent) -> None:
                event.current_buffer.validate_and_handle()

            with patch_stdout():
                print_formatted_text("")
                message = await prompt_session.prompt_async(
                    HTML(
                        "<gold>Enter your message and press Ctrl-D to finish:</gold>\n"
                    ),
                    multiline=True,
                    key_bindings=kb,
                )
        else:
            with patch_stdout():
                print_formatted_text("")
                message = await prompt_session.prompt_async(
                    HTML("<gold>> </gold>"),
                )
        return message if message is not None else ""
    except (KeyboardInterrupt, EOFError):
        return "/exit"


async def read_confirmation_input() -> str:
    try:
        question = "Choose an option:"
        choices = [
            "Yes, proceed",
            "No (and allow to enter instructions)",
            "Auto-confirm action with LOW/MEDIUM risk, ask for HIGH risk",
            "Always proceed (don't ask again)",
        ]
        choice_mapping = {0: "yes", 1: "no", 2: "auto_highrisk", 3: "always"}

        # keep the outer coroutine responsive by using asyncio.to_thread which puts the blocking call app.run() of cli_confirm() in a separate thread
        index = await asyncio.to_thread(cli_confirm, question, choices, 0)

        return choice_mapping.get(index, "no")

    except (KeyboardInterrupt, EOFError):
        return "no"


def start_pause_listener(
    loop: asyncio.AbstractEventLoop,
    done_event: asyncio.Event,
    conversation: Conversation,
) -> None:
    global pause_task
    if pause_task is None or pause_task.done():
        pause_task = loop.create_task(
            process_agent_pause(done_event, conversation)
        )  # Create a task to track agent pause requests from the user


async def stop_pause_listener() -> None:
    global pause_task
    if pause_task and not pause_task.done():
        pause_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pause_task
        await asyncio.sleep(0)
    pause_task = None


async def process_agent_pause(done: asyncio.Event, conversation: Conversation) -> None:
    input = create_input()

    def keys_ready() -> None:
        for key_press in input.read_keys():
            if (
                key_press.key == Keys.ControlP
                or key_press.key == Keys.ControlC
                or key_press.key == Keys.ControlD
            ):
                print_formatted_text("")
                print_formatted_text(HTML("<gold>Pausing the agent...</gold>"))
                # TODO: implement pause conversation
                print_formatted_text(conversation.state.agent_finished)
                # conversation.pause()
                done.set()

    try:
        with input.raw_mode():
            with input.attach(keys_ready):
                await done.wait()
    finally:
        input.close()


def cli_confirm(
    question: str = "Are you sure?",
    choices: list[str] | None = None,
    initial_selection: int = 0,
) -> Any:
    """Display a confirmation prompt with the given question and choices.

    Returns the index of the selected choice.
    """
    if choices is None:
        choices = ["Yes", "No"]
    selected = [initial_selection]  # Using list to allow modification in closure

    def get_choice_text() -> list:
        # Use red styling for HIGH risk questions
        question_style = "class:question"

        return [
            (question_style, f"{question}\n\n"),
        ] + [
            (
                "class:selected" if i == selected[0] else "class:unselected",
                f"{'> ' if i == selected[0] else '  '}{choice}\n",
            )
            for i, choice in enumerate(choices)
        ]

    kb = KeyBindings()

    @kb.add("up")
    def _handle_up(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] - 1) % len(choices)

    @kb.add("down")
    def _handle_down(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] + 1) % len(choices)

    @kb.add("enter")
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

    return app.run(in_thread=True)


def kb_cancel() -> KeyBindings:
    """Custom key bindings to handle ESC as a user cancellation."""
    bindings = KeyBindings()

    @bindings.add("escape")
    def _(event: KeyPressEvent) -> None:
        event.app.exit(exception=UserCancelledError, style="class:aborting")

    return bindings


class UserCancelledError(Exception):
    """Raised when the user cancels an operation via key binding."""

    pass
