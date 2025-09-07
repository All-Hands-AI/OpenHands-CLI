#!/usr/bin/env python3
"""
Tests for confirmation mode functionality in OpenHands CLI.
"""

import os
from typing import Any
from unittest.mock import MagicMock, patch

from openhands_cli.agent_chat import ask_user_confirmation, setup_agent, UserConfirmation


class TestConfirmationMode:
    """Test suite for confirmation mode functionality."""

    def test_confirmation_mode_env_var_true(self) -> None:
        """Test that CONFIRMATION_MODE=true enables confirmation mode."""
        with patch.dict(
            os.environ, {"CONFIRMATION_MODE": "true", "LITELLM_API_KEY": "test-key"}
        ):
            with (
                patch("openhands_cli.agent_chat.LLM"),
                patch("openhands_cli.agent_chat.Agent"),
                patch("openhands_cli.agent_chat.Conversation") as mock_conversation,
                patch("openhands_cli.agent_chat.BashExecutor"),
                patch("openhands_cli.agent_chat.FileEditorExecutor"),
            ):
                mock_conv_instance = MagicMock()
                mock_conversation.return_value = mock_conv_instance

                setup_agent()

                # Verify confirmation mode was enabled
                mock_conv_instance.set_confirmation_mode.assert_called_once_with(True)

    def test_confirmation_mode_env_var_1(self) -> None:
        """Test that CONFIRMATION_MODE=1 enables confirmation mode."""
        with patch.dict(
            os.environ, {"CONFIRMATION_MODE": "1", "LITELLM_API_KEY": "test-key"}
        ):
            with (
                patch("openhands_cli.agent_chat.LLM"),
                patch("openhands_cli.agent_chat.Agent"),
                patch("openhands_cli.agent_chat.Conversation") as mock_conversation,
                patch("openhands_cli.agent_chat.BashExecutor"),
                patch("openhands_cli.agent_chat.FileEditorExecutor"),
            ):
                mock_conv_instance = MagicMock()
                mock_conversation.return_value = mock_conv_instance

                setup_agent()

                # Verify confirmation mode was enabled
                mock_conv_instance.set_confirmation_mode.assert_called_once_with(True)

    def test_confirmation_mode_env_var_false(self) -> None:
        """Test that CONFIRMATION_MODE=false does not enable confirmation mode."""
        with patch.dict(
            os.environ, {"CONFIRMATION_MODE": "false", "LITELLM_API_KEY": "test-key"}
        ):
            with (
                patch("openhands_cli.agent_chat.LLM"),
                patch("openhands_cli.agent_chat.Agent"),
                patch("openhands_cli.agent_chat.Conversation") as mock_conversation,
                patch("openhands_cli.agent_chat.BashExecutor"),
                patch("openhands_cli.agent_chat.FileEditorExecutor"),
            ):
                mock_conv_instance = MagicMock()
                mock_conversation.return_value = mock_conv_instance

                setup_agent()

                # Verify confirmation mode was not enabled
                mock_conv_instance.set_confirmation_mode.assert_not_called()

    def test_confirmation_mode_env_var_not_set(self) -> None:
        """Test that confirmation mode is not enabled when env var is not set."""
        with patch.dict(os.environ, {"LITELLM_API_KEY": "test-key"}, clear=True):
            with (
                patch("openhands_cli.agent_chat.LLM"),
                patch("openhands_cli.agent_chat.Agent"),
                patch("openhands_cli.agent_chat.Conversation") as mock_conversation,
                patch("openhands_cli.agent_chat.BashExecutor"),
                patch("openhands_cli.agent_chat.FileEditorExecutor"),
            ):
                mock_conv_instance = MagicMock()
                mock_conversation.return_value = mock_conv_instance

                setup_agent()

                # Verify confirmation mode was not enabled
                mock_conv_instance.set_confirmation_mode.assert_not_called()

    def test_ask_user_confirmation_empty_actions(self) -> None:
        """Test that ask_user_confirmation returns ACCEPT for empty actions list."""
        result = ask_user_confirmation([])
        assert result == UserConfirmation.ACCEPT

    @patch("openhands_cli.agent_chat.PromptSession")
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

    @patch("openhands_cli.agent_chat.PromptSession")
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

    @patch("openhands_cli.agent_chat.PromptSession")
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

    @patch("openhands_cli.agent_chat.PromptSession")
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

    @patch("openhands_cli.agent_chat.PromptSession")
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

    @patch("openhands_cli.agent_chat.PromptSession")
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

    @patch("openhands_cli.agent_chat.PromptSession")
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
            patch("openhands_cli.agent_chat.PromptSession") as mock_prompt_session,
            patch("openhands_cli.agent_chat.print_formatted_text") as mock_print,
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
