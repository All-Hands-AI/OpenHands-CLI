#!/usr/bin/env python3
"""
Confirmation mode functionality for OpenHands CLI.
Provides user confirmation prompts for potentially risky actions.
"""

import asyncio
from typing import Dict, Any

from prompt_toolkit import Application, print_formatted_text
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Frame

from openhands_cli.security import ActionSecurityRisk, security_analyzer
from openhands_cli.pt_style import get_cli_style


class ConfirmationMode:
    """Manages confirmation mode settings and behavior."""
    
    def __init__(self):
        self.always_confirm = False  # Always confirm all actions
        self.auto_highrisk_confirm = False  # Auto-confirm LOW/MEDIUM, ask for HIGH
        self.never_confirm = False  # Never ask for confirmation
    
    def should_confirm(self, risk: ActionSecurityRisk) -> bool:
        """Determine if an action should require confirmation."""
        if self.never_confirm:
            return False
        
        if self.always_confirm:
            return True
        
        if self.auto_highrisk_confirm:
            return risk == ActionSecurityRisk.HIGH
        
        # Default behavior: confirm MEDIUM and HIGH risk actions
        return risk in [ActionSecurityRisk.MEDIUM, ActionSecurityRisk.HIGH]
    
    def set_mode(self, mode: str) -> None:
        """Set the confirmation mode based on user choice."""
        self.always_confirm = False
        self.auto_highrisk_confirm = False
        self.never_confirm = False
        
        if mode == "always":
            self.always_confirm = True
        elif mode == "auto_highrisk":
            self.auto_highrisk_confirm = True
        elif mode == "never":
            self.never_confirm = True


class UserCancelledError(Exception):
    """Raised when the user cancels an operation."""
    pass


def cli_confirm(
    question: str = "Are you sure?",
    choices: list[str] | None = None,
    initial_selection: int = 0,
    security_risk: ActionSecurityRisk = ActionSecurityRisk.UNKNOWN,
) -> int:
    """Display a confirmation prompt with the given question and choices.
    
    Returns the index of the selected choice.
    """
    if choices is None:
        choices = ["Yes", "No"]
    
    selected = [initial_selection]  # Using list to allow modification in closure
    
    def get_choice_text() -> list:
        # Use red styling for HIGH risk questions
        question_style = (
            "class:risk-high"
            if security_risk == ActionSecurityRisk.HIGH
            else "class:question"
        )
        
        return [
            (question_style, f"{question}\n\n"),
        ] + [
            (
                "class:selected" if i == selected[0] else "class:unselected",
                f'{">" if i == selected[0] else " "} {choice}\n',
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
    
    # Create layout with risk-based styling
    content_window = Window(
        FormattedTextControl(get_choice_text),
        always_hide_cursor=True,
        height=Dimension(max=8),  # Limit height to prevent screen takeover
    )
    
    # Add frame for HIGH risk commands
    if security_risk == ActionSecurityRisk.HIGH:
        layout = Layout(
            HSplit([
                Frame(
                    content_window,
                    title="HIGH RISK",
                    style="fg:#FF0000 bold",  # Red color for HIGH risk
                )
            ])
        )
    else:
        layout = Layout(HSplit([content_window]))
    
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=get_cli_style(),
        full_screen=False,
    )
    
    return app.run()


async def read_confirmation_input(security_risk: ActionSecurityRisk) -> str:
    """Read user confirmation input with appropriate choices based on risk level."""
    try:
        if security_risk == ActionSecurityRisk.HIGH:
            question = "HIGH RISK command detected.\nReview carefully before proceeding.\n\nChoose an option:"
            choices = [
                "Yes, proceed (HIGH RISK - Use with caution)",
                "No (and allow to enter instructions)",
                "Always proceed (don't ask again - NOT RECOMMENDED)",
            ]
            choice_mapping = {0: "yes", 1: "no", 2: "always"}
        else:
            question = "Choose an option:"
            choices = [
                "Yes, proceed",
                "No (and allow to enter instructions)",
                "Auto-confirm action with LOW/MEDIUM risk, ask for HIGH risk",
                "Always proceed (don't ask again)",
            ]
            choice_mapping = {0: "yes", 1: "no", 2: "auto_highrisk", 3: "always"}
        
        # Run the confirmation dialog in a thread to keep the event loop responsive
        index = await asyncio.to_thread(
            cli_confirm, question, choices, 0, security_risk
        )
        
        return choice_mapping.get(index, "no")
    
    except (KeyboardInterrupt, EOFError, UserCancelledError):
        return "no"


def analyze_action_risk(action_type: str, action_data: Dict[str, Any]) -> ActionSecurityRisk:
    """Analyze an action and return its security risk level."""
    return security_analyzer.analyze_action(action_type, action_data)


def display_risk_warning(risk: ActionSecurityRisk, action_description: str) -> None:
    """Display a warning message about the action's risk level."""
    if risk == ActionSecurityRisk.HIGH:
        print_formatted_text(
            HTML(f"<red>⚠️  HIGH RISK ACTION: {action_description}</red>")
        )
    elif risk == ActionSecurityRisk.MEDIUM:
        print_formatted_text(
            HTML(f"<yellow>⚠️  MEDIUM RISK ACTION: {action_description}</yellow>")
        )
    else:
        print_formatted_text(
            HTML(f"<green>ℹ️  LOW RISK ACTION: {action_description}</green>")
        )


# Global confirmation mode instance
confirmation_mode = ConfirmationMode()