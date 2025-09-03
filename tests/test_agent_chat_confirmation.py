#!/usr/bin/env python3
"""
Tests for agent chat confirmation integration.
"""

from typing import Any
from unittest.mock import patch

import pytest

from openhands_cli.agent_chat import (
    confirm_action_if_needed,
    display_confirmation_help,
    handle_confirmation_command,
)
from openhands_cli.confirmation import confirmation_mode


class TestConfirmActionIfNeeded:
    """Test the confirm_action_if_needed function."""

    def setup_method(self) -> None:
        """Reset confirmation mode before each test."""
        confirmation_mode.set_enabled(True)

    @pytest.mark.asyncio
    async def test_confirmation_disabled_no_prompt(self) -> None:
        """Test that actions proceed without confirmation when disabled."""
        confirmation_mode.set_enabled(False)

        action_data = {"command": "ls -la"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        assert result is True

    @pytest.mark.asyncio
    @patch("openhands_cli.agent_chat.read_confirmation_input")
    async def test_confirmation_enabled_user_says_yes(
        self, mock_read_confirmation: Any
    ) -> None:
        """Test that actions proceed when user confirms."""
        mock_read_confirmation.return_value = "yes"

        action_data = {"command": "ls -la"}
        result = await confirm_action_if_needed("execute_bash", action_data)

        assert result is True
        mock_read_confirmation.assert_called_once()

    @pytest.mark.asyncio
    @patch("openhands_cli.agent_chat.read_confirmation_input")
    async def test_confirmation_enabled_user_says_no(
        self, mock_read_confirmation: Any
    ) -> None:
        """Test that actions are cancelled when user denies."""
        mock_read_confirmation.return_value = "no"

        action_data = {"command": "ls -la"}
        result = await confirm_action_if_needed("execute_bash", action_data)

        assert result is False
        mock_read_confirmation.assert_called_once()

    @pytest.mark.asyncio
    @patch("openhands_cli.agent_chat.read_confirmation_input")
    async def test_user_chooses_always_proceed(
        self, mock_read_confirmation: Any
    ) -> None:
        """Test handling when user chooses always proceed."""
        mock_read_confirmation.return_value = "always"

        action_data = {"command": "ls -la"}
        result = await confirm_action_if_needed("execute_bash", action_data)

        assert result is True
        assert confirmation_mode.enabled is False
        mock_read_confirmation.assert_called_once()


class TestConfirmationCommands:
    """Test confirmation command handling."""

    def setup_method(self) -> None:
        """Reset confirmation mode before each test."""
        confirmation_mode.set_enabled(True)

    @patch("openhands_cli.agent_chat.print_formatted_text")
    def test_display_confirmation_help(self, mock_print: Any) -> None:
        """Test that confirmation help is displayed correctly."""
        display_confirmation_help()

        # Should have multiple print calls for the help text
        assert mock_print.call_count >= 3

        # Check that key commands are mentioned
        help_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "/confirm status" in help_text
        assert "/confirm on" in help_text
        assert "/confirm off" in help_text

    @patch("openhands_cli.agent_chat.print_formatted_text")
    def test_handle_confirmation_status_enabled(self, mock_print: Any) -> None:
        """Test handling of confirmation status command when enabled."""
        confirmation_mode.set_enabled(True)
        handle_confirmation_command("/confirm status")

        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "enabled" in call_text.lower()

    @patch("openhands_cli.agent_chat.print_formatted_text")
    def test_handle_confirmation_status_disabled(self, mock_print: Any) -> None:
        """Test handling of confirmation status command when disabled."""
        confirmation_mode.set_enabled(False)
        handle_confirmation_command("/confirm status")

        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "disabled" in call_text.lower()

    @patch("openhands_cli.agent_chat.print_formatted_text")
    def test_handle_confirmation_set_on(self, mock_print: Any) -> None:
        """Test enabling confirmation mode."""
        confirmation_mode.set_enabled(False)  # Start disabled
        handle_confirmation_command("/confirm on")

        assert confirmation_mode.enabled is True
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "enabled" in call_text.lower()

    @patch("openhands_cli.agent_chat.print_formatted_text")
    def test_handle_confirmation_set_off(self, mock_print: Any) -> None:
        """Test disabling confirmation mode."""
        confirmation_mode.set_enabled(True)  # Start enabled
        handle_confirmation_command("/confirm off")

        assert confirmation_mode.enabled is False
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "disabled" in call_text.lower()

    @patch("openhands_cli.agent_chat.print_formatted_text")
    def test_handle_confirmation_invalid_command(self, mock_print: Any) -> None:
        """Test handling of invalid confirmation commands."""
        handle_confirmation_command("/confirm invalid")

        # Should print error and help
        assert mock_print.call_count > 1

        # Check that error message is shown
        error_call = mock_print.call_args_list[0]
        error_text = str(error_call[0][0])
        assert "unknown" in error_text.lower()

    @patch("openhands_cli.agent_chat.display_confirmation_help")
    def test_handle_confirmation_no_subcommand(self, mock_help: Any) -> None:
        """Test handling of confirmation command without subcommand."""
        handle_confirmation_command("/confirm")

        mock_help.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
