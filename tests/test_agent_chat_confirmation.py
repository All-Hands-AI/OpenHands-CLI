#!/usr/bin/env python3
"""
Tests for agent chat confirmation integration.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from openhands_cli.agent_chat import (
    confirm_action_if_needed,
    display_confirmation_help,
    handle_confirmation_command,
)
from openhands_cli.confirmation import confirmation_mode
from openhands_cli.security import ActionSecurityRisk


class TestConfirmActionIfNeeded:
    """Test the confirm_action_if_needed function."""
    
    def setup_method(self):
        """Reset confirmation mode before each test."""
        confirmation_mode.set_mode("default")
    
    @pytest.mark.asyncio
    async def test_low_risk_action_no_confirmation(self):
        """Test that low-risk actions don't require confirmation in default mode."""
        action_data = {"command": "ls -la"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        assert result is True
    
    @pytest.mark.asyncio
    @patch('openhands_cli.agent_chat.read_confirmation_input')
    async def test_high_risk_action_requires_confirmation(self, mock_read_confirmation):
        """Test that high-risk actions require confirmation."""
        mock_read_confirmation.return_value = "yes"
        
        action_data = {"command": "rm -rf /"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
        mock_read_confirmation.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('openhands_cli.agent_chat.read_confirmation_input')
    async def test_user_denies_action(self, mock_read_confirmation):
        """Test handling when user denies an action."""
        mock_read_confirmation.return_value = "no"
        
        action_data = {"command": "rm -rf /"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is False
        mock_read_confirmation.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('openhands_cli.agent_chat.read_confirmation_input')
    async def test_user_chooses_always_confirm(self, mock_read_confirmation):
        """Test handling when user chooses always confirm mode."""
        mock_read_confirmation.return_value = "always"
        
        action_data = {"command": "rm -rf /"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
        assert confirmation_mode.never_confirm is True
        mock_read_confirmation.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('openhands_cli.agent_chat.read_confirmation_input')
    async def test_user_chooses_auto_highrisk(self, mock_read_confirmation):
        """Test handling when user chooses auto high-risk mode."""
        mock_read_confirmation.return_value = "auto_highrisk"
        
        action_data = {"command": "sudo apt install package"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
        assert confirmation_mode.auto_highrisk_confirm is True
        mock_read_confirmation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_never_confirm_mode(self):
        """Test that never confirm mode skips all confirmations."""
        confirmation_mode.set_mode("never")
        
        action_data = {"command": "rm -rf /"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch('openhands_cli.agent_chat.read_confirmation_input')
    async def test_always_confirm_mode(self, mock_read_confirmation):
        """Test that always confirm mode requires confirmation for all actions."""
        confirmation_mode.set_mode("always")
        mock_read_confirmation.return_value = "yes"
        
        action_data = {"command": "ls -la"}  # Low-risk command
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
        mock_read_confirmation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_auto_highrisk_mode_low_risk(self):
        """Test that auto high-risk mode doesn't confirm low-risk actions."""
        confirmation_mode.set_mode("auto_highrisk")
        
        action_data = {"command": "ls -la"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch('openhands_cli.agent_chat.read_confirmation_input')
    async def test_auto_highrisk_mode_high_risk(self, mock_read_confirmation):
        """Test that auto high-risk mode confirms high-risk actions."""
        confirmation_mode.set_mode("auto_highrisk")
        mock_read_confirmation.return_value = "yes"
        
        action_data = {"command": "rm -rf /"}
        result = await confirm_action_if_needed("execute_bash", action_data)
        
        assert result is True
        mock_read_confirmation.assert_called_once()


class TestConfirmationCommands:
    """Test confirmation command handling."""
    
    def setup_method(self):
        """Reset confirmation mode before each test."""
        confirmation_mode.set_mode("default")
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_display_confirmation_help(self, mock_print):
        """Test that confirmation help is displayed correctly."""
        display_confirmation_help()
        
        # Should have multiple print calls for the help text
        assert mock_print.call_count > 5
        
        # Check that key commands are mentioned
        help_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "/confirm status" in help_text
        assert "/confirm default" in help_text
        assert "/confirm auto" in help_text
        assert "/confirm always" in help_text
        assert "/confirm never" in help_text
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_handle_confirmation_status(self, mock_print):
        """Test handling of confirmation status command."""
        handle_confirmation_command("/confirm status")
        
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "default" in call_text.lower()
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_handle_confirmation_set_default(self, mock_print):
        """Test setting confirmation mode to default."""
        handle_confirmation_command("/confirm default")
        
        assert not confirmation_mode.always_confirm
        assert not confirmation_mode.auto_highrisk_confirm
        assert not confirmation_mode.never_confirm
        
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "default" in call_text.lower()
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_handle_confirmation_set_auto(self, mock_print):
        """Test setting confirmation mode to auto high-risk."""
        handle_confirmation_command("/confirm auto")
        
        assert confirmation_mode.auto_highrisk_confirm is True
        assert confirmation_mode.always_confirm is False
        assert confirmation_mode.never_confirm is False
        
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "auto-confirm" in call_text.lower()
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_handle_confirmation_set_always(self, mock_print):
        """Test setting confirmation mode to always."""
        handle_confirmation_command("/confirm always")
        
        assert confirmation_mode.always_confirm is True
        assert confirmation_mode.auto_highrisk_confirm is False
        assert confirmation_mode.never_confirm is False
        
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "always confirm" in call_text.lower()
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_handle_confirmation_set_never(self, mock_print):
        """Test setting confirmation mode to never."""
        handle_confirmation_command("/confirm never")
        
        assert confirmation_mode.never_confirm is True
        assert confirmation_mode.always_confirm is False
        assert confirmation_mode.auto_highrisk_confirm is False
        
        mock_print.assert_called_once()
        call_text = str(mock_print.call_args[0][0])
        assert "disabled" in call_text.lower()
    
    @patch('openhands_cli.agent_chat.print_formatted_text')
    def test_handle_confirmation_invalid_command(self, mock_print):
        """Test handling of invalid confirmation commands."""
        handle_confirmation_command("/confirm invalid")
        
        # Should print error and help
        assert mock_print.call_count > 1
        
        # Check that error message is shown
        error_call = mock_print.call_args_list[0]
        error_text = str(error_call[0][0])
        assert "unknown" in error_text.lower()
    
    @patch('openhands_cli.agent_chat.display_confirmation_help')
    def test_handle_confirmation_no_subcommand(self, mock_help):
        """Test handling of confirmation command without subcommand."""
        handle_confirmation_command("/confirm")
        
        mock_help.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])