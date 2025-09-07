#!/usr/bin/env python3
"""
Tests for pause functionality in OpenHands CLI.

This test suite covers the pause/resume behavior in different modes:
1. Pausing in confirmation mode
2. Pausing when not in confirmation mode
3. Keyboard interrupt during confirmation mode
4. Resume functionality from main input page
5. Resume with confirmation mode after pausing before seeing confirmation options
"""

import time
from unittest.mock import MagicMock, patch

from openhands.sdk import Conversation, Message, TextContent
from prompt_toolkit.input.defaults import create_pipe_input

from openhands_cli.agent_chat import (
    ConversationRunner,
    UserConfirmation,
    ask_user_confirmation,
)
from openhands_cli.listeners.pause_listener import PauseListener, pause_listener


class TestPauseListener:
    """Test suite for PauseListener class."""

    def test_pause_listener_stop(self) -> None:
        """Test PauseListener stop functionality."""
        mock_callback = MagicMock()
        listener = PauseListener(on_pause=mock_callback)

        listener.start()

        # Initially not paused
        assert not listener.is_paused()
        assert listener.is_alive()

        # Stop the listener
        listener.stop()

        # Listner was shutdown not paused
        assert not listener.is_paused()
        assert listener.is_stopped()

    def test_pause_listener_context_manager(self) -> None:
        """Test pause_listener context manager."""
        mock_conversation = MagicMock(spec=Conversation)

        with create_pipe_input() as pipe:
            with pause_listener(mock_conversation, pipe) as listener:
                assert isinstance(listener, PauseListener)
                assert listener.on_pause == mock_conversation.pause
                # Listener should be started (daemon thread)
                assert listener.is_alive()
                assert not listener.is_paused()
                pipe.send_text("\x10")  # Ctrl-P
                time.sleep(0.1)
                assert listener.is_paused()

            assert listener.is_stopped()
            assert not listener.is_alive()


class TestPauseFunctionality:
    """Test suite for pause functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create mock conversation
        self.mock_conversation = MagicMock(spec=Conversation)
        self.mock_conversation.state = MagicMock()
        self.mock_conversation.state.agent_paused = False
        self.mock_conversation.state.agent_finished = False
        self.mock_conversation.state.agent_waiting_for_confirmation = False
        self.mock_conversation.state.confirmation_mode = False

        # Create conversation runner
        self.runner = ConversationRunner(self.mock_conversation)

    def test_pause_in_confirmation_mode_returns_to_main_input(self):
        """Test case 1: If you pause in confirmation mode then you aren't shown
        the confirmation selection, you simply return to the main input page."""

        # Set up confirmation mode
        self.runner.set_confirmation_mode(True)
        self.mock_conversation.state.agent_waiting_for_confirmation = False

        # Mock the pause listener to simulate pause during confirmation
        with patch("openhands_cli.agent_chat.pause_listener") as mock_pause_listener:
            mock_listener = MagicMock()
            mock_listener.is_paused.return_value = True  # Simulate pause occurred
            mock_pause_listener.return_value.__enter__.return_value = mock_listener

            # Mock conversation.run to simulate agent execution
            self.mock_conversation.run.return_value = None

            # Process a message which should trigger confirmation mode
            message = Message(role="user", content=[TextContent(text="test message")])

            # This should return early due to pause, without showing confirmation
            self.runner.process_message(message)

            # Verify conversation.run was called (agent started)
            self.mock_conversation.run.assert_called_once()

            # Verify pause listener was used
            mock_pause_listener.assert_called_once_with(self.mock_conversation)
            assert 1 == 2

            # Verify no confirmation handling occurred (would be in _handle_confirmation_request)
            # Since we paused, we shouldn't reach confirmation handling

    def test_pause_when_not_in_confirmation_mode_wraps_up_and_returns(self):
        """Test case 2: If you pause when not in confirmation mode, your agent step
        wraps up and returns to the main input page."""

        # Set up non-confirmation mode
        self.runner.set_confirmation_mode(False)

        # Mock the pause listener to simulate pause
        with patch("openhands_cli.agent_chat.pause_listener") as mock_pause_listener:
            mock_listener = MagicMock()
            mock_listener.is_paused.return_value = False  # Initially not paused
            mock_pause_listener.return_value.__enter__.return_value = mock_listener

            # Mock conversation.run to simulate agent execution completing
            self.mock_conversation.run.return_value = None

            # Process a message
            from openhands.sdk import Message, TextContent

            message = Message(role="user", content=[TextContent(text="test message")])

            self.runner.process_message(message)

            # Verify conversation.run was called
            self.mock_conversation.run.assert_called_once()

            # Verify pause listener was used
            mock_pause_listener.assert_called_once_with(self.mock_conversation)

            # Verify message was sent to conversation
            self.mock_conversation.send_message.assert_called_once_with(message)

    @patch("openhands_cli.agent_chat.ask_user_confirmation")
    def test_keyboard_interrupt_during_confirmation_pauses_agent(
        self, mock_ask_confirmation
    ):
        """Test case 3: If you keyboard interrupt during confirmation mode,
        it will pause the agent and return to the main input page."""

        # Set up confirmation mode with pending actions
        self.runner.set_confirmation_mode(True)
        self.mock_conversation.state.agent_waiting_for_confirmation = True

        # Mock ask_user_confirmation to simulate KeyboardInterrupt
        mock_ask_confirmation.return_value = UserConfirmation.DEFER

        # Mock get_unmatched_actions to return some pending actions
        with patch(
            "openhands_cli.agent_chat.get_unmatched_actions"
        ) as mock_get_actions:
            mock_action = MagicMock()
            mock_action.tool_name = "bash"
            mock_action.action = "test command"
            mock_get_actions.return_value = [mock_action]

            # Mock pause listener
            with patch(
                "openhands_cli.agent_chat.pause_listener"
            ) as mock_pause_listener:
                mock_listener = MagicMock()
                mock_listener.is_paused.return_value = False
                mock_pause_listener.return_value.__enter__.return_value = mock_listener

                # This should handle the confirmation request and defer (pause)
                result = self.runner._handle_confirmation_request()

                # Verify the result is DEFER (pause)
                assert result == UserConfirmation.DEFER

                # Verify conversation.pause was called
                self.mock_conversation.pause.assert_called_once()

                # Verify ask_user_confirmation was called
                mock_ask_confirmation.assert_called_once()

    def test_resume_or_any_message_from_main_input_resumes_agent(self):
        """Test case 4: If you try resume or any message from the main input page,
        it will resume the agent."""

        # Set up paused state
        self.mock_conversation.state.agent_paused = True

        # Test with /resume command
        Message(role="user", content=[TextContent(text="/resume")])

        with patch("openhands_cli.agent_chat.pause_listener") as mock_pause_listener:
            mock_listener = MagicMock()
            mock_listener.is_paused.return_value = False
            mock_pause_listener.return_value.__enter__.return_value = mock_listener

            # Process resume message (None message simulates /resume command)
            self.runner.process_message(None)

            # Verify conversation.run was called to resume
            self.mock_conversation.run.assert_called_once()

        # Reset mocks
        self.mock_conversation.reset_mock()

        # Test with any other message
        any_message = Message(
            role="user", content=[TextContent(text="please continue")]
        )

        with patch("openhands_cli.agent_chat.pause_listener") as mock_pause_listener:
            mock_listener = MagicMock()
            mock_listener.is_paused.return_value = False
            mock_pause_listener.return_value.__enter__.return_value = mock_listener

            # Process any message
            self.runner.process_message(any_message)

            # Verify message was sent and conversation resumed
            self.mock_conversation.send_message.assert_called_once_with(any_message)
            self.mock_conversation.run.assert_called_once()

    @patch("openhands_cli.agent_chat.ask_user_confirmation")
    def test_resume_with_confirmation_mode_shows_confirmation_options(
        self, mock_ask_confirmation
    ):
        """Test case 5: If you try resume or any message from the main input page
        with confirmation mode, and the user had paused before seeing the confirmation
        selection for the action, it will resume and show the confirmation options."""

        # Set up confirmation mode with agent waiting for confirmation
        self.runner.set_confirmation_mode(True)
        self.mock_conversation.state.agent_paused = True
        self.mock_conversation.state.agent_waiting_for_confirmation = True

        # Mock ask_user_confirmation to return ACCEPT
        mock_ask_confirmation.return_value = UserConfirmation.ACCEPT

        # Mock get_unmatched_actions to return pending actions
        with patch(
            "openhands_cli.agent_chat.get_unmatched_actions"
        ) as mock_get_actions:
            mock_action = MagicMock()
            mock_action.tool_name = "bash"
            mock_action.action = "test command"
            mock_get_actions.return_value = [mock_action]

            # Mock pause listener
            with patch(
                "openhands_cli.agent_chat.pause_listener"
            ) as mock_pause_listener:
                mock_listener = MagicMock()
                mock_listener.is_paused.return_value = False
                mock_pause_listener.return_value.__enter__.return_value = mock_listener

                # Mock conversation.run to simulate completion after confirmation
                self.mock_conversation.state.agent_finished = True

                # Process a resume message
                from openhands.sdk import Message, TextContent

                message = Message(
                    role="user", content=[TextContent(text="please continue")]
                )

                self.runner.process_message(message)

                # Verify confirmation was shown
                mock_ask_confirmation.assert_called_once()

                # Verify message was sent
                self.mock_conversation.send_message.assert_called_once_with(message)

                # Verify conversation.run was called
                self.mock_conversation.run.assert_called()


class TestAskUserConfirmation:
    """Test suite for ask_user_confirmation function."""

    def test_keyboard_interrupt_returns_defer(self):
        """Test that KeyboardInterrupt during confirmation returns DEFER."""
        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "test command"

        with patch("openhands_cli.agent_chat.PromptSession") as mock_prompt_session:
            mock_session = MagicMock()
            mock_session.prompt.side_effect = KeyboardInterrupt()
            mock_prompt_session.return_value = mock_session

            result = ask_user_confirmation([mock_action])

            assert result == UserConfirmation.DEFER

    def test_eof_error_returns_defer(self):
        """Test that EOFError during confirmation returns DEFER."""
        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "test command"

        with patch("openhands_cli.agent_chat.PromptSession") as mock_prompt_session:
            mock_session = MagicMock()
            mock_session.prompt.side_effect = EOFError()
            mock_prompt_session.return_value = mock_session

            result = ask_user_confirmation([mock_action])

            assert result == UserConfirmation.DEFER


class TestConversationRunnerPauseIntegration:
    """Integration tests for ConversationRunner pause functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_conversation = MagicMock(spec=Conversation)
        self.mock_conversation.state = MagicMock()
        self.mock_conversation.state.agent_paused = False
        self.mock_conversation.state.agent_finished = False
        self.mock_conversation.state.agent_waiting_for_confirmation = False
        self.mock_conversation.state.confirmation_mode = False

        self.runner = ConversationRunner(self.mock_conversation)

    def test_pause_during_run_without_confirmation_stops_execution(self):
        """Test that pausing during run without confirmation mode stops execution."""

        with patch("openhands_cli.agent_chat.pause_listener") as mock_pause_listener:
            mock_listener = MagicMock()
            # Simulate pause occurring during execution
            mock_listener.is_paused.return_value = False  # Not paused initially
            mock_pause_listener.return_value.__enter__.return_value = mock_listener

            # Mock conversation.run
            self.mock_conversation.run.return_value = None
            message = Message(role="user", content=[TextContent(text="test")])

            self.runner.process_message(message)

            # Verify pause listener was used
            mock_pause_listener.assert_called_once_with(self.mock_conversation)

            # Verify conversation.run was called
            self.mock_conversation.run.assert_called_once()

    def test_pause_during_confirmation_mode_breaks_loop(self):
        """Test that pausing during confirmation mode breaks the execution loop."""

        self.runner.set_confirmation_mode(True)

        with patch("openhands_cli.agent_chat.pause_listener") as mock_pause_listener:
            mock_listener = MagicMock()
            # Simulate pause occurring
            mock_listener.is_paused.return_value = True
            mock_pause_listener.return_value.__enter__.return_value = mock_listener

            # Mock conversation.run
            self.mock_conversation.run.return_value = None

            from openhands.sdk import Message, TextContent

            message = Message(role="user", content=[TextContent(text="test")])

            self.runner.process_message(message)

            # Verify pause listener was used
            mock_pause_listener.assert_called_with(self.mock_conversation)

            # Verify conversation.run was called
            self.mock_conversation.run.assert_called()
