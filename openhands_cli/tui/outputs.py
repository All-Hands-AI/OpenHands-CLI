import html
import re
import sys
import threading

# Ensure we use the agent-sdk openhands package, not the main OpenHands package
# Remove the main OpenHands code path if it exists
if "/openhands/code" in sys.path:
    sys.path.remove("/openhands/code")

from openhands.sdk import Conversation
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    EventType,
    MessageEvent,
    ObservationEvent,
)
from openhands.tools import (
    ExecuteBashAction,
    ExecuteBashObservation,
    StrReplaceEditorAction,
    StrReplaceEditorObservation,
)
from prompt_toolkit import print_formatted_text
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML, FormattedText, StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.widgets import Frame, TextArea

from openhands_cli.pt_style import (
    COLOR_AGENT_BLUE,
    COLOR_GREY,
)

print_lock = threading.Lock()

# Track recent thoughts to prevent duplicate display
recent_thoughts: list[str] = []
MAX_RECENT_THOUGHTS = 5

streaming_output_text_area: TextArea | None = None




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


def _render_basic_markdown(text: str | None) -> str | None:
    """Render a very small subset of markdown directly to prompt_toolkit HTML.

    Supported:
    - Bold: **text** -> <b>text</b>
    - Underline: __text__ -> <u>text</u>

    Any existing HTML in input is escaped to avoid injection into the renderer.
    If input is None, return None.
    """
    if text is None:
        return None
    if text == '':
        return ''

    safe = html.escape(text)
    # Bold: greedy within a line, non-overlapping
    safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
    # Underline: double underscore
    safe = re.sub(r'__(.+?)__', r'<u>\1</u>', safe)
    return safe


def display_message(message: str, is_agent_message: bool = False) -> None:
    """Display a message in the terminal with markdown rendering.

    Args:
        message: The message to display
        is_agent_message: If True, apply agent styling (blue color)
    """
    message = message.strip()

    if message:
        # Add spacing before the message
        print_formatted_text('')

        try:
            # Render only basic markdown (bold/underline), escaping any HTML
            html_content = _render_basic_markdown(message)

            if is_agent_message:
                # Use prompt_toolkit's HTML renderer with the agent color
                print_formatted_text(
                    HTML(f'<style fg="{COLOR_AGENT_BLUE}">{html_content}</style>')
                )
            else:
                # Regular message display with HTML rendering but default color
                print_formatted_text(HTML(html_content))
        except Exception as e:
            # If HTML rendering fails, fall back to plain text
            print(f'Warning: HTML rendering failed: {str(e)}', file=sys.stderr)
            if is_agent_message:
                print_formatted_text(
                    FormattedText([('fg:' + COLOR_AGENT_BLUE, message)])
                )
            else:
                print_formatted_text(message)


def display_thought_if_new(thought: str, is_agent_message: bool = False) -> None:
    """Display a thought only if it hasn't been displayed recently.

    Args:
        thought: The thought to display
        is_agent_message: If True, apply agent styling and markdown rendering
    """
    global recent_thoughts
    if thought and thought.strip():
        # Check if this thought was recently displayed
        if thought not in recent_thoughts:
            display_message(thought, is_agent_message=is_agent_message)
            recent_thoughts.append(thought)
            # Keep only the most recent thoughts
            if len(recent_thoughts) > MAX_RECENT_THOUGHTS:
                recent_thoughts.pop(0)


def display_action(event: ActionEvent) -> None:
    # Handle different action types
    if isinstance(event.action, ExecuteBashAction):
        # Create simple command frame for bash commands
        command_text = f'$ {event.action.command}'
        title = 'Command'
    elif isinstance(event.action, StrReplaceEditorAction):
        # Create frame for file editor commands
        if event.action.command == 'view':
            command_text = f'View: {event.action.path}'
        elif event.action.command == 'create':
            command_text = f'Create: {event.action.path}'
        elif event.action.command == 'str_replace':
            command_text = f'Edit: {event.action.path}'
        elif event.action.command == 'insert':
            command_text = f'Insert: {event.action.path} (line {event.action.insert_line})'
        elif event.action.command == 'undo_edit':
            command_text = f'Undo: {event.action.path}'
        else:
            command_text = f'{event.action.command}: {event.action.path}'
        title = 'File Editor'
    else:
        # Generic action display
        command_text = f'{event.tool_name}: {str(event.action)}'
        title = 'Action'

    container = Frame(
        TextArea(
            text=command_text,
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title=title,
        style='ansiblue',
    )
    print_formatted_text('')
    print_container(container)


def display_event(event: EventType, conversation: Conversation) -> None:
    global streaming_output_text_area
    with print_lock:
        if isinstance(event, ActionEvent):
            # Display agent thoughts first
            if event.thought:
                for thought_content in event.thought:
                    display_thought_if_new(thought_content.text, is_agent_message=True)

            # Display the action
            display_action(event)

        elif isinstance(event, ObservationEvent):
            # Handle different observation types based on tool name
            if event.tool_name == 'execute_bash' and isinstance(event.observation, ExecuteBashObservation):
                display_command_output(event.observation.output)
            elif event.tool_name == 'str_replace_editor' and isinstance(event.observation, StrReplaceEditorObservation):
                if event.observation.path and event.observation.old_content != event.observation.new_content:
                    # File was edited, show diff-like output
                    display_file_edit_observation(event.observation)
                else:
                    # File was viewed or created, show content
                    display_file_read_observation(event.observation)
            else:
                # Generic observation display
                display_generic_observation(event.observation)

        elif isinstance(event, MessageEvent):
            # Display messages from agent or user
            if event.source == 'agent':
                # Extract text content from the message
                text_parts = []
                for content in event.llm_message.content:
                    if hasattr(content, 'text'):
                        text_parts.append(content.text)
                if text_parts:
                    message_text = ' '.join(text_parts)
                    display_message(message_text, is_agent_message=True)
            elif event.source == 'user':
                # Extract text content from user message
                text_parts = []
                for content in event.llm_message.content:
                    if hasattr(content, 'text'):
                        text_parts.append(content.text)
                if text_parts:
                    message_text = ' '.join(text_parts)
                    display_message(message_text, is_agent_message=False)

        elif isinstance(event, AgentErrorEvent):
            display_error(event.error)


def display_error(error: str) -> None:
    error = error.strip()

    if error:
        container = Frame(
            TextArea(
                text=error,
                read_only=True,
                style='ansired',
                wrap_lines=True,
            ),
            title='Error',
            style='ansired',
        )
        print_formatted_text('')
        print_container(container)





def display_command_output(output: str) -> None:
    lines = output.split('\n')
    formatted_lines = []
    for line in lines:
        if line.startswith('[Python Interpreter') or line.startswith('openhands@'):
            # TODO: clean this up once we clean up terminal output
            continue
        formatted_lines.append(line)
        formatted_lines.append('\n')

    # Remove the last newline if it exists
    if formatted_lines:
        formatted_lines.pop()

    container = Frame(
        TextArea(
            text=''.join(formatted_lines),
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title='Command Output',
        style=f'fg:{COLOR_GREY}',
    )
    print_formatted_text('')
    print_container(container)





def display_file_edit_observation(observation: StrReplaceEditorObservation) -> None:
    """Display file edit observation with diff-like output."""
    if observation.error:
        display_error(observation.error)
        return

    # Create a simple diff-like display
    if observation.old_content and observation.new_content:
        # Show the file path and operation
        title = f'File Edit: {observation.path}'
        content = observation.output
    else:
        title = 'File Edit'
        content = observation.output

    container = Frame(
        TextArea(
            text=content,
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title=title,
        style=f'fg:{COLOR_GREY}',
    )
    print_formatted_text('')
    print_container(container)


def display_file_read_observation(observation: StrReplaceEditorObservation) -> None:
    """Display file read observation."""
    if observation.error:
        display_error(observation.error)
        return

    title = f'File View: {observation.path}' if observation.path else 'File View'
    content = observation.output

    container = Frame(
        TextArea(
            text=content,
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title=title,
        style=f'fg:{COLOR_GREY}',
    )
    print_formatted_text('')
    print_container(container)


def display_generic_observation(observation) -> None:
    """Display generic observation."""
    if hasattr(observation, 'agent_observation'):
        content = observation.agent_observation
    elif hasattr(observation, 'output'):
        content = observation.output
    else:
        content = str(observation)

    container = Frame(
        TextArea(
            text=content,
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title='Observation',
        style=f'fg:{COLOR_GREY}',
    )
    print_formatted_text('')
    print_container(container)


