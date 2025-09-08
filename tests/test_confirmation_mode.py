#!/usr/bin/env python3
"""
Tests for confirmation mode functionality in OpenHands CLI.
"""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from openhands_cli.setup import setup_agent
from openhands_cli.user_actions.confirmation import ask_user_confirmation
from openhands_cli.user_actions.types import UserConfirmation


class TestConfirmationMode:
    """Test suite for confirmation mode functionality."""

    def test_setup_agent_creates_conversation(self) -> None:
        """Test that setup_agent creates a conversation successfully."""
        with patch.dict(os.environ, {"LITELLM_API_KEY": "test-key"}):
            with (
                patch("openhands_cli.setup.LLM"),
                patch("openhands_cli.setup.Agent"),
                patch("openhands_cli.setup.Conversation") as mock_conversation,
                patch("openhands_cli.setup.BashExecutor"),
                patch("openhands_cli.setup.FileEditorExecutor"),
            ):
                mock_conv_instance = MagicMock()
                mock_conversation.return_value = mock_conv_instance

                result = setup_agent()

                # Verify conversation was created and returned
                assert result == mock_conv_instance
                mock_conversation.assert_called_once()

    def test_conversation_runner_set_confirmation_mode(self) -> None:
        """Test that ConversationRunner can set confirmation mode."""
        from openhands_cli.runner import ConversationRunner

        mock_conversation = MagicMock()
        runner = ConversationRunner(mock_conversation)

        # Test enabling confirmation mode
        runner.set_confirmation_mode(True)
        assert runner.confirmation_mode is True
        mock_conversation.set_confirmation_mode.assert_called_with(True)

        # Test disabling confirmation mode
        runner.set_confirmation_mode(False)
        assert runner.confirmation_mode is False
        mock_conversation.set_confirmation_mode.assert_called_with(False)

    def test_conversation_runner_initial_state(self) -> None:
        """Test that ConversationRunner starts with confirmation mode disabled."""
        from openhands_cli.runner import ConversationRunner

        mock_conversation = MagicMock()
        runner = ConversationRunner(mock_conversation)

        # Verify initial state
        assert runner.confirmation_mode is False

    def test_setup_agent_without_api_key(self) -> None:
        """Test that setup_agent raises exception when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with (
                patch("openhands_cli.setup.print_formatted_text"),
                pytest.raises(Exception, match="No API key found"),
            ):
                setup_agent()

    def test_ask_user_confirmation_empty_actions(self) -> None:
        """Test that ask_user_confirmation returns ACCEPT for empty actions list."""
        result = ask_user_confirmation([])
        assert result == UserConfirmation.ACCEPT

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_yes(self, mock_prompt_session: Any) -> None:
        """Test that ask_user_confirmation returns ACCEPT when user says yes."""
        mock_session = MagicMock()
        mock_session.prompt.return_value = "yes"
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "ls -la"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.ACCEPT

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_no(self, mock_prompt_session: Any) -> None:
        """Test that ask_user_confirmation returns REJECT when user says no."""
        mock_session = MagicMock()
        mock_session.prompt.return_value = "no"
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "rm -rf /"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.REJECT

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_y_shorthand(self, mock_prompt_session: Any) -> None:
        """Test that ask_user_confirmation accepts 'y' as yes."""
        mock_session = MagicMock()
        mock_session.prompt.return_value = "y"
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "echo hello"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.ACCEPT

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_n_shorthand(self, mock_prompt_session: Any) -> None:
        """Test that ask_user_confirmation accepts 'n' as no."""
        mock_session = MagicMock()
        mock_session.prompt.return_value = "n"
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "dangerous command"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.REJECT

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_invalid_then_yes(
        self, mock_prompt_session: Any
    ) -> None:
        """Test that ask_user_confirmation handles invalid input then accepts yes."""
        mock_session = MagicMock()
        mock_session.prompt.side_effect = ["invalid", "maybe", "yes"]
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "echo test"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.ACCEPT
        assert mock_session.prompt.call_count == 3

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_keyboard_interrupt(
        self, mock_prompt_session: Any
    ) -> None:
        """Test that ask_user_confirmation handles KeyboardInterrupt gracefully."""
        mock_session = MagicMock()
        mock_session.prompt.side_effect = KeyboardInterrupt()
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "echo test"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.DEFER

    @patch("openhands_cli.user_actions.confirmation.PromptSession")
    def test_ask_user_confirmation_eof_error(self, mock_prompt_session: Any) -> None:
        """Test that ask_user_confirmation handles EOFError gracefully."""
        mock_session = MagicMock()
        mock_session.prompt.side_effect = EOFError()
        mock_prompt_session.return_value = mock_session

        mock_action = MagicMock()
        mock_action.tool_name = "bash"
        mock_action.action = "echo test"

        result = ask_user_confirmation([mock_action])
        assert result == UserConfirmation.DEFER

    def test_ask_user_confirmation_multiple_actions(self) -> None:
        """Test that ask_user_confirmation displays multiple actions correctly."""
        with (
            patch(
                "openhands_cli.user_actions.confirmation.PromptSession"
            ) as mock_prompt_session,
            patch(
                "openhands_cli.user_actions.confirmation.print_formatted_text"
            ) as mock_print,
        ):
            mock_session = MagicMock()
            mock_session.prompt.return_value = "yes"
            mock_prompt_session.return_value = mock_session

            mock_action1 = MagicMock()
            mock_action1.tool_name = "bash"
            mock_action1.action = "ls -la"

            mock_action2 = MagicMock()
            mock_action2.tool_name = "str_replace_editor"
            mock_action2.action = "create file.txt"

            result = ask_user_confirmation([mock_action1, mock_action2])
            assert result == UserConfirmation.ACCEPT

            # Verify that both actions were displayed
            assert (
                mock_print.call_count >= 3
            )  # Header + 2 actions + at least approval message
