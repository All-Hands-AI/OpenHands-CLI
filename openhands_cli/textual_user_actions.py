"""
Textual-based user action handlers to replace prompt_toolkit implementations.
"""

from typing import TYPE_CHECKING

from openhands.sdk.event import ActionEvent
from openhands_cli.textual_dialogs import ConfirmationDialog, TextInputDialog
from openhands_cli.user_actions.types import ConfirmationResult, UserConfirmation


if TYPE_CHECKING:
    from textual.app import App


async def ask_user_confirmation_textual(
    app: "App",
    pending_actions: list[ActionEvent],
    is_risky_only: bool = False,
) -> ConfirmationResult:
    """Ask user for confirmation using Textual dialogs."""

    # Build the confirmation message
    if len(pending_actions) == 1:
        action = pending_actions[0]
        question = f"The agent wants to execute:\n\n{action.action}\n\nDo you want to allow this?"
    else:
        question = f"The agent wants to execute {len(pending_actions)} actions:\n\n"
        for i, action in enumerate(pending_actions[:3], 1):  # Show first 3
            question += f"{i}. {action.action}\n"
        if len(pending_actions) > 3:
            question += f"... and {len(pending_actions) - 3} more\n"
        question += "\nDo you want to allow these actions?"

    # Define choices based on confirmation mode
    if is_risky_only:
        choices = [
            "Accept",
            "Reject",
            "Accept All (Disable Confirmation)",
            "Security Mode (Only High Risk)",
            "Defer (Pause)",
        ]
    else:
        choices = ["Accept", "Reject", "Disable Confirmation", "Defer (Pause)"]

    # Show confirmation dialog
    dialog = ConfirmationDialog(question, choices, initial_selection=0)
    choice_index = await app.push_screen_wait(dialog)

    if choice_index is False or choice_index == -1:
        # Escaped or cancelled
        return ConfirmationResult(
            decision=UserConfirmation.DEFER,
            reason="User cancelled confirmation",
            policy_change=None,
        )

    # Map choice to result
    if is_risky_only:
        if choice_index == 0:  # Accept
            return ConfirmationResult(
                decision=UserConfirmation.ACCEPT, reason=None, policy_change=None
            )
        elif choice_index == 1:  # Reject
            reason_dialog = TextInputDialog(
                "Please provide a reason for rejection (optional):",
                placeholder="Reason for rejection...",
            )
            reason = await app.push_screen_wait(reason_dialog)
            return ConfirmationResult(
                decision=UserConfirmation.REJECT,
                reason=reason or "User rejected the action",
                policy_change=None,
            )
        elif choice_index == 2:  # Accept All (Disable Confirmation)
            from openhands.sdk.security.confirmation_policy import NeverConfirm

            return ConfirmationResult(
                decision=UserConfirmation.ACCEPT,
                reason=None,
                policy_change=NeverConfirm(),
            )
        elif choice_index == 3:  # Security Mode
            from openhands.sdk.security.confirmation_policy import ConfirmRisky

            return ConfirmationResult(
                decision=UserConfirmation.ACCEPT,
                reason=None,
                policy_change=ConfirmRisky(),
            )
        else:  # Defer
            return ConfirmationResult(
                decision=UserConfirmation.DEFER,
                reason="User deferred confirmation",
                policy_change=None,
            )
    else:
        if choice_index == 0:  # Accept
            return ConfirmationResult(
                decision=UserConfirmation.ACCEPT, reason=None, policy_change=None
            )
        elif choice_index == 1:  # Reject
            reason_dialog = TextInputDialog(
                "Please provide a reason for rejection (optional):",
                placeholder="Reason for rejection...",
            )
            reason = await app.push_screen_wait(reason_dialog)
            return ConfirmationResult(
                decision=UserConfirmation.REJECT,
                reason=reason or "User rejected the action",
                policy_change=None,
            )
        elif choice_index == 2:  # Disable Confirmation
            from openhands.sdk.security.confirmation_policy import NeverConfirm

            return ConfirmationResult(
                decision=UserConfirmation.ACCEPT,
                reason=None,
                policy_change=NeverConfirm(),
            )
        else:  # Defer
            return ConfirmationResult(
                decision=UserConfirmation.DEFER,
                reason="User deferred confirmation",
                policy_change=None,
            )


async def exit_session_confirmation_textual(app: "App") -> UserConfirmation:
    """Ask user for exit confirmation using Textual dialog."""
    dialog = ConfirmationDialog(
        "Are you sure you want to exit?",
        choices=["Yes", "No"],
        initial_selection=1,  # Default to "No"
    )

    choice_index = await app.push_screen_wait(dialog)

    if choice_index == 0:
        return UserConfirmation.ACCEPT
    else:
        return UserConfirmation.REJECT
