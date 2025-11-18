"""
Pinned Input TUI - A terminal user interface with a fixed input box at the bottom.

This module provides a full-screen TUI where:
- The input box is always pinned to the bottom of the screen with a border
- The output area scrolls above the input box
- Input remains available even when the agent is running
- Non-blocking input handling allows continuous agent output
"""

import threading
from collections import deque
from collections.abc import Callable

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import HSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Box

from openhands_cli.pt_style import get_cli_style
from openhands_cli.tui.tui import CommandCompleter


class PinnedInputTUI:
    """A TUI with a pinned input box at the bottom and scrollable output above."""

    def __init__(
        self,
        on_input: Callable[[str], None] | None = None,
        completer: Completer | None = None,
        agent_running: bool = False,
    ):
        """Initialize the pinned input TUI.

        Args:
            on_input: Callback function called when user submits input
            completer: Optional completer for tab completion
            agent_running: Whether the agent is currently running
        """
        self.on_input = on_input or (lambda _x: None)
        self.completer = completer or CommandCompleter()
        self.agent_running = agent_running

        # Output buffer to store all messages as tuples (style, text)
        self.output_lines: deque[tuple[str, str]] = deque(maxlen=1000)
        self.output_lock = threading.Lock()

        # Input buffer
        self.input_buffer = Buffer(
            completer=self.completer,
            multiline=True,
        )

        # Create the application
        self.app = self._create_application()

    def _create_application(self) -> Application:
        """Create the prompt_toolkit Application with pinned input layout."""

        # Key bindings
        kb = KeyBindings()

        @kb.add("enter")
        def _handle_enter(_event: KeyPressEvent) -> None:
            """Handle Enter key - submit input."""
            text = self.input_buffer.text.strip()
            if text:
                # Clear the input buffer
                self.input_buffer.text = ""
                # Call the input handler
                self.on_input(text)

        @kb.add("c-c")
        def _handle_ctrl_c(event: KeyPressEvent) -> None:
            """Handle Ctrl+C - exit or pause agent."""
            if self.agent_running:
                # If agent is running, this should pause it
                # We'll handle this in the callback
                self.on_input("__CTRL_C__")
            else:
                # Exit the application
                event.app.exit(exception=KeyboardInterrupt())

        @kb.add("c-d")
        def _handle_ctrl_d(event: KeyPressEvent) -> None:
            """Handle Ctrl+D - exit."""
            event.app.exit(exception=EOFError())

        @kb.add("\\", "enter")
        def _handle_backslash_enter(_event: KeyPressEvent) -> None:
            """Handle \\+Enter - insert newline."""
            self.input_buffer.insert_text("\n")

        # Create layout
        layout = self._create_layout()

        return Application(
            layout=layout,
            key_bindings=kb,
            style=get_cli_style(),
            full_screen=True,
            mouse_support=True,
        )

    def _create_layout(self) -> Layout:
        """Create the layout with output area and pinned input box."""

        def get_output_content():
            """Get the current output content."""
            with self.output_lock:
                return list(self.output_lines)

        # Output window (scrollable)
        output_window = Window(
            content=FormattedTextControl(
                text=get_output_content,
                focusable=False,
            ),
            always_hide_cursor=True,
        )

        # Input prompt
        input_prompt = Window(
            content=FormattedTextControl(
                text=self._get_input_prompt,
                focusable=False,
            ),
            height=Dimension.exact(1),
            align=WindowAlign.LEFT,
        )

        # Input window
        input_window = Window(
            content=BufferControl(
                buffer=self.input_buffer,
                focusable=True,
            ),
            height=Dimension(min=1, max=5),  # Allow multiline but limit height
        )

        # Input area with border
        input_area = Box(
            HSplit(
                [
                    input_prompt,
                    input_window,
                ]
            ),
            padding=1,
        )

        # Main layout
        root_container = HSplit(
            [
                output_window,  # Takes remaining space
                input_area,  # Fixed at bottom
            ]
        )

        return Layout(root_container, focused_element=input_window)

    def _get_input_prompt(self) -> FormattedText:
        """Get the input prompt text based on current state."""
        if self.agent_running:
            return HTML("<gold>📤 Message to agent:</gold>")
        else:
            return HTML("<gold>💬 Your input:</gold>")

    def add_output(self, text: str | FormattedText, style: str = "") -> None:
        """Add text to the output area.

        Args:
            text: Text to add (can be string or FormattedText)
            style: Optional style to apply to the text
        """
        with self.output_lock:
            if isinstance(text, str):
                self.output_lines.append((style, text + "\n"))
            else:
                # Convert HTML or other formatted text to list of tuples
                if hasattr(text, "__pt_formatted_text__"):
                    formatted_text = text.__pt_formatted_text__()
                    self.output_lines.extend(formatted_text)
                else:
                    self.output_lines.append(("", str(text) + "\n"))

        # Refresh the application if it's running
        if self.app and hasattr(self.app, "invalidate"):
            self.app.invalidate()

    def add_html_output(self, html: str) -> None:
        """Add HTML-formatted text to the output area."""
        formatted_text = HTML(html)
        self.add_output(formatted_text)

    def set_agent_running(self, running: bool) -> None:
        """Update the agent running state."""
        self.agent_running = running
        if self.app and hasattr(self.app, "invalidate"):
            self.app.invalidate()

    def clear_output(self) -> None:
        """Clear the output area."""
        with self.output_lock:
            self.output_lines.clear()
        if self.app and hasattr(self.app, "invalidate"):
            self.app.invalidate()

    def run(self) -> None:
        """Run the TUI application."""
        try:
            self.app.run()
        except (KeyboardInterrupt, EOFError):
            # Clean exit
            pass

    def exit(self) -> None:
        """Exit the TUI application."""
        if self.app:
            self.app.exit()


class ThreadSafePinnedInputTUI(PinnedInputTUI):
    """Thread-safe version of PinnedInputTUI for use with agent threads."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running = False
        self._app_thread = None

    def start_in_thread(self) -> None:
        """Start the TUI in a separate thread."""
        if self._running:
            return

        self._running = True
        self._app_thread = threading.Thread(target=self._run_app, daemon=True)
        self._app_thread.start()

    def _run_app(self) -> None:
        """Run the app in a thread."""
        try:
            self.run()
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the TUI."""
        self._running = False
        self.exit()
        if self._app_thread and self._app_thread.is_alive():
            self._app_thread.join(timeout=1.0)

    def is_running(self) -> bool:
        """Check if the TUI is running."""
        return self._running
