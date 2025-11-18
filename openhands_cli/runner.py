import threading

from prompt_toolkit import HTML, print_formatted_text

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
from openhands_cli.user_actions import ask_user_confirmation
from openhands_cli.user_actions.types import UserConfirmation


class ConversationRunner:
    """Handles the conversation state machine logic cleanly."""

    def __init__(self, conversation: BaseConversation):
        self.conversation = conversation
        self._running = False
        self._run_thread = None

    @property
    def is_confirmation_mode_active(self):
        return self.conversation.is_confirmation_mode_active

    @property
    def is_running(self):
        """Check if the agent is currently running."""
        return self._running

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

    def _start_listener(self) -> None:
        self.listener = PauseListener(on_pause=self.conversation.pause)
        self.listener.start()

    def _print_run_status(self) -> None:
        print_formatted_text("")
        if (
            self.conversation.state.execution_status
            == ConversationExecutionStatus.PAUSED
        ):
            print_formatted_text(
                HTML(
                    "<yellow>Resuming paused conversation...</yellow>"
                    "<grey> (Press Ctrl-P to pause)</grey>"
                )
            )

        else:
            print_formatted_text(
                HTML(
                    "<yellow>Agent running...</yellow>"
                    "<grey> (Press Ctrl-P to pause)</grey>"
                )
            )
        print_formatted_text("")

    def send_message_while_running(self, message: Message) -> None:
        """Send a message to the conversation while the agent is running.

        This allows users to send additional messages without interrupting
        the current agent execution.

        Args:
            message: The user message to send
        """
        if not self._running:
            raise RuntimeError("Agent is not currently running")

        print_formatted_text(HTML("<green>📨 Message sent to running agent</green>"))
        self.conversation.send_message(message)

    def process_message(self, message: Message | None) -> None:
        """Process a user message through the conversation.

        Args:
            message: The user message to process
        """

        self._print_run_status()

        # Send message to conversation
        if message:
            self.conversation.send_message(message)

        # Start agent execution in a separate thread
        self._running = True
        self._run_thread = threading.Thread(target=self._run_agent_thread, daemon=True)
        self._run_thread.start()

        # Display status that agent is now running and accepting messages
        from openhands_cli.tui.tui import display_agent_running_status

        display_agent_running_status()

    def _run_agent_thread(self) -> None:
        """Run the agent in a separate thread."""
        try:
            if self.is_confirmation_mode_active:
                self._run_with_confirmation()
            else:
                self._run_without_confirmation()
        finally:
            self._running = False
            self._run_thread = None
            # Notify that agent has finished
            print_formatted_text(
                HTML(
                    "<green>✅ Agent finished. You can now use commands again.</green>"
                )
            )

    def _run_without_confirmation(self) -> None:
        with pause_listener(self.conversation):
            self.conversation.run()

    def _run_with_confirmation(self) -> None:
        # If agent was paused, resume with confirmation request
        if (
            self.conversation.state.execution_status
            == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
        ):
            user_confirmation = self._handle_confirmation_request()
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
                user_confirmation = self._handle_confirmation_request()
                if user_confirmation == UserConfirmation.DEFER:
                    return

            else:
                raise Exception("Infinite loop")

    def _handle_confirmation_request(self) -> UserConfirmation:
        """Handle confirmation request from user.

        Returns:
            UserConfirmation indicating the user's choice
        """

        pending_actions = ConversationState.get_unmatched_actions(
            self.conversation.state.events
        )
        if not pending_actions:
            return UserConfirmation.ACCEPT

        result = ask_user_confirmation(
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
            print_formatted_text(
                HTML(
                    "<yellow>Confirmation mode disabled. Agent will proceed "
                    "without asking.</yellow>"
                )
            )

            # Remove security analyzer when policy is never confirm
            self.toggle_confirmation_mode()
            return decision

        if isinstance(policy_change, ConfirmRisky):
            print_formatted_text(
                HTML(
                    "<yellow>Security-based confirmation enabled. "
                    "LOW/MEDIUM risk actions will auto-confirm, HIGH risk actions "
                    "will ask for confirmation.</yellow>"
                )
            )

            # Keep security analyzer, change existing policy
            self.set_confirmation_policy(policy_change)
            return decision

        # Accept action without changing existing policies
        assert decision == UserConfirmation.ACCEPT
        return decision
