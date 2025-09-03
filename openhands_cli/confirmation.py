#!/usr/bin/env python3
"""
Confirmation mode functionality for OpenHands CLI.
Provides user confirmation prompts before executing commands.
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from prompt_toolkit import Application, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout

from openhands_cli.pt_style import get_cli_style


class ConfirmationMode:
    """Manages confirmation mode settings and behavior."""

    def __init__(self) -> None:
        self.enabled = True  # Whether confirmation is enabled

    def should_confirm(self) -> bool:
        """Determine if actions should require confirmation."""
        return self.enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable confirmation mode."""
        self.enabled = enabled


class UserCancelledError(Exception):
    """Raised when the user cancels an operation."""

    pass


def cli_confirm(
    question: str = "Are you sure?",
    choices: list[str] | None = None,
    initial_selection: int = 0,
) -> int:
    """Display a confirmation prompt with the given question and choices.

    Returns the index of the selected choice.
    """
    if choices is None:
        choices = ["Yes", "No"]

    selected = [initial_selection]  # Using list to allow modification in closure

    def get_choice_text() -> list:
        return [
            ("class:question", f"{question}\n\n"),
        ] + [
            (
                "class:selected" if i == selected[0] else "class:unselected",
                f"{'>' if i == selected[0] else ' '} {choice}\n",
            )
            for i, choice in enumerate(choices)
        ]

    kb = KeyBindings()

    @kb.add("up")
    def _handle_up(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] - 1) % len(choices)

    @kb.add("k")  # Vi-style up
    def _handle_k(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] - 1) % len(choices)

    @kb.add("down")
    def _handle_down(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] + 1) % len(choices)

    @kb.add("j")  # Vi-style down
    def _handle_j(event: KeyPressEvent) -> None:
        selected[0] = (selected[0] + 1) % len(choices)

    @kb.add("enter")
    def _handle_enter(event: KeyPressEvent) -> None:
        event.app.exit(result=selected[0])

    @kb.add("escape")
    def _handle_escape(event: KeyPressEvent) -> None:
        event.app.exit(exception=UserCancelledError())

    @kb.add("c-c")
    def _handle_ctrl_c(event: KeyPressEvent) -> None:
        event.app.exit(exception=UserCancelledError())

    # Create layout
    content_window = Window(
        FormattedTextControl(get_choice_text),
        always_hide_cursor=True,
        height=Dimension(max=8),  # Limit height to prevent screen takeover
    )

    layout = Layout(HSplit([content_window]))

    app: Application[int] = Application(
        layout=layout,
        key_bindings=kb,
        style=get_cli_style(),
        full_screen=False,
    )

    return cast(int, app.run())


async def read_confirmation_input() -> str:
    """Read user confirmation input."""
    try:
        question = "The agent wants to execute a command. Do you want to proceed?"
        choices = [
            "Yes, proceed",
            "No (and allow to enter instructions)",
            "Always proceed (don't ask again)",
        ]
        choice_mapping = {0: "yes", 1: "no", 2: "always"}

        # Run the confirmation dialog in a thread to keep the event loop responsive
        index = await asyncio.to_thread(cli_confirm, question, choices, 0)

        return choice_mapping.get(index, "no")

    except (KeyboardInterrupt, EOFError, UserCancelledError):
        return "no"


def display_action_info(action_type: str, action_data: dict[str, Any]) -> None:
    """Display information about the action to be executed."""
    if action_type == "execute_bash":
        command = action_data.get("command", "Unknown command")
        print_formatted_text(HTML(f"<yellow>Command to execute: {command}</yellow>"))
    elif action_type == "str_replace_editor":
        command = action_data.get("command", "unknown")
        path = action_data.get("path", "unknown file")
        print_formatted_text(
            HTML(f"<yellow>File operation: {command} on {path}</yellow>")
        )
    else:
        print_formatted_text(HTML(f"<yellow>Action: {action_type}</yellow>"))


# Global confirmation mode instance
confirmation_mode = ConfirmationMode()
