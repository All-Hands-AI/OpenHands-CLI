"""
Textual-aware conversation runner that handles confirmations through the UI.
"""

from typing import TYPE_CHECKING

from openhands.sdk import BaseConversation, Message
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)
from openhands.sdk.security.confirmation_policy import (
    AlwaysConfirm,
    ConfirmationPolicyBase,
    ConfirmRisky,
    NeverConfirm,
)
from openhands_cli.listeners.pause_listener import PauseListener, pause_listener
from openhands_cli.setup import setup_conversation
from openhands_cli.textual_user_actions import ask_user_confirmation_textual
from openhands_cli.user_actions.types import UserConfirmation

if TYPE_CHECKING:
    from openhands_cli.textual_app import OpenHandsApp


class TextualConversationRunner:
    """Handles the conversation state machine logic with Textual UI integration."""

    def __init__(self, conversation: BaseConversation, app: "OpenHandsApp"):
        self.conversation = conversation
        self.app = app

    @property
    def is_confirmation_mode_active(self):
        return self.conversation.is_confirmation_mode_active

    def toggle_confirmation_mode(self):
        new_confirmation_mode_state = not self.is_confirmation_mode_active

        self.conversation = setup_conversation(
            self.conversation.id, include_security_analyzer=new_confirmation_mode_state
        )

        if new_confirmation_mode_state:
            # Enable confirmation mode: set AlwaysConfirm policy
            self.set_confirmation_policy(AlwaysConfirm())
        else:
            # Disable confirmation mode: set NeverConfirm policy and remove
            # security analyzer
            self.set_confirmation_policy(NeverConfirm())

    def set_confirmation_policy(
        self, confirmation_policy: ConfirmationPolicyBase
    ) -> None:
        self.conversation.set_confirmation_policy(confirmation_policy)

    def _print_run_status(self) -> None:
        if (
            self.conversation.state.execution_status
            == ConversationExecutionStatus.PAUSED
        ):
            self.app.log_message(
                "[yellow]Resuming paused conversation...[/yellow] "
                "[grey](Press Ctrl-P to pause)[/grey]"
            )
        else:
            self.app.log_message(
                "[yellow]Agent running...[/yellow] "
                "[grey](Press Ctrl-P to pause)[/grey]"
            )

    async def process_message(self, message: Message | None) -> None:
        """Process a user message through the conversation.

        Args:
            message: The user message to process
        """

        self._print_run_status()

        # Send message to conversation
        if message:
            self.conversation.send_message(message)

        if self.is_confirmation_mode_active:
            await self._run_with_confirmation()
        else:
            self._run_without_confirmation()

    def _run_without_confirmation(self) -> None:
        with pause_listener(self.conversation):
            self.conversation.run()

    async def _run_with_confirmation(self) -> None:
        # If agent was paused, resume with confirmation request
        if (
            self.conversation.state.execution_status
            == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
        ):
            user_confirmation = await self._handle_confirmation_request()
            if user_confirmation == UserConfirmation.DEFER:
                return

        while True:
            with pause_listener(self.conversation) as listener:
                self.conversation.run()

                if listener.is_paused():
                    break

            # In confirmation mode, agent either finishes or waits for user confirmation
            if (
                self.conversation.state.execution_status
                == ConversationExecutionStatus.FINISHED
            ):
                break

            elif (
                self.conversation.state.execution_status
                == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
            ):
                user_confirmation = await self._handle_confirmation_request()
                if user_confirmation == UserConfirmation.DEFER:
                    return

            else:
                raise Exception("Infinite loop")

    async def _handle_confirmation_request(self) -> UserConfirmation:
        """Handle confirmation request from user.

        Returns:
            UserConfirmation indicating the user's choice
        """

        pending_actions = ConversationState.get_unmatched_actions(
            self.conversation.state.events
        )
        if not pending_actions:
            return UserConfirmation.ACCEPT

        result = await ask_user_confirmation_textual(
            self.app,
            pending_actions,
            isinstance(self.conversation.state.confirmation_policy, ConfirmRisky),
        )
        decision = result.decision
        policy_change = result.policy_change

        if decision == UserConfirmation.REJECT:
            self.conversation.reject_pending_actions(
                result.reason or "User rejected the actions"
            )
            return decision

        if decision == UserConfirmation.DEFER:
            self.conversation.pause()
            return decision

        if isinstance(policy_change, NeverConfirm):
            self.app.log_message(
                "[yellow]Confirmation mode disabled. Agent will proceed "
                "without asking.[/yellow]"
            )

            # Remove security analyzer when policy is never confirm
            self.toggle_confirmation_mode()
            return decision

        if isinstance(policy_change, ConfirmRisky):
            self.app.log_message(
                "[yellow]Security-based confirmation enabled. "
                "LOW/MEDIUM risk actions will auto-confirm, HIGH risk actions "
                "will ask for confirmation.[/yellow]"
            )

            # Keep security analyzer, change existing policy
            self.set_confirmation_policy(policy_change)
            return decision

        # Accept action without changing existing policies
        assert decision == UserConfirmation.ACCEPT
        return decision