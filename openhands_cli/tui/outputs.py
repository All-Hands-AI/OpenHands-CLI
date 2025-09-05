import asyncio
import contextlib
import datetime
import html
import json
import re
import sys
import threading
import time
from typing import Generator

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.application import Application
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML, FormattedText, StyleAndTextTuples
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.widgets import Frame, TextArea

from openhands import __version__
from openhands_cli.pt_style import (
    COLOR_AGENT_BLUE,
    COLOR_GOLD,
    COLOR_GREY,
    get_cli_style,
)
from openhands.core.config import OpenHandsConfig
from openhands.core.schema import AgentState
from openhands.events import EventSource, EventStream
from openhands.events.action import (
    Action,
    ActionConfirmationStatus,
    ActionSecurityRisk,
    ChangeAgentStateAction,
    CmdRunAction,
    MCPAction,
    MessageAction,
    TaskTrackingAction,
)
from openhands.events.event import Event
from openhands.events.observation import (
    AgentStateChangedObservation,
    CmdOutputObservation,
    ErrorObservation,
    FileEditObservation,
    FileReadObservation,
    MCPObservation,
    TaskTrackingObservation,
)
from openhands.llm.metrics import Metrics
from openhands.mcp.error_collector import mcp_error_collector

from openhands.sdk.event import (
    ActionEvent
)

from openhands.sdk import Conversation


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
    # Create simple command frame
    command_text = f'$ {event.action}'

    container = Frame(
        TextArea(
            text=command_text,
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title='Command',
        style='ansiblue',
    )
    print_formatted_text('')
    print_container(container)


def display_event(event: Event, conversation: Conversation) -> None:
    global streaming_output_text_area
    with print_lock:
        if isinstance(event, ActionEvent):
            # For CmdRunAction, display thought first, then command
            if hasattr(event, 'thought') and event.thought:
                display_thought_if_new(event.thought)

            display_action(event)
       
        elif isinstance(event, Action):
            # For other actions, display thoughts normally
            if hasattr(event, 'thought') and event.thought:
                display_thought_if_new(event.thought)
            if hasattr(event, 'final_thought') and event.final_thought:
                # Display final thoughts with agent styling
                display_message(event.final_thought, is_agent_message=True)

        if isinstance(event, MessageAction):
            if event.source == EventSource.AGENT:
                # Display agent messages with styling and markdown rendering
                display_thought_if_new(event.content, is_agent_message=True)
        elif isinstance(event, CmdOutputObservation):
            display_command_output(event.content)
        elif isinstance(event, FileEditObservation):
            display_file_edit(event)
        elif isinstance(event, FileReadObservation):
            display_file_read(event)
        elif isinstance(event, MCPObservation):
            display_mcp_observation(event)
        elif isinstance(event, TaskTrackingObservation):
            display_task_tracking_observation(event)
        elif isinstance(event, AgentStateChangedObservation):
            display_agent_state_change_message(event.agent_state)
        elif isinstance(event, ErrorObservation):
            display_error(event.content)


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


def display_file_edit(event: FileEditObservation) -> None:
    container = Frame(
        TextArea(
            text=event.visualize_diff(n_context_lines=4),
            read_only=True,
            wrap_lines=True,
            lexer=CustomDiffLexer(),
        ),
        title='File Edit',
        style=f'fg:{COLOR_GREY}',
    )
    print_formatted_text('')
    print_container(container)


def display_file_read(event: FileReadObservation) -> None:
    content = event.content.replace('\t', ' ')
    container = Frame(
        TextArea(
            text=content,
            read_only=True,
            style=COLOR_GREY,
            wrap_lines=True,
        ),
        title='File Read',
        style=f'fg:{COLOR_GREY}',
    )
    print_formatted_text('')
    print_container(container)


