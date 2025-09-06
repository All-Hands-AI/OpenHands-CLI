#!/usr/bin/env python3
"""
Tests for resume functionality in OpenHands CLI.
"""

from unittest.mock import MagicMock, patch

from openhands_cli.agent_chat import ConversationRunner


class TestResumeFunctionality:
    """Test suite for resume functionality."""

    def test_conversation_runner_resume_when_paused(self) -> None:
        """Test that ConversationRunner.resume_conversation works when paused."""
        # Create mock conversation and agent
        mock_conversation = MagicMock()
        mock_agent = MagicMock()

        # Set up paused state
        mock_conversation.state.agent_paused = True
        mock_conversation.state.agent_finished = False
        mock_conversation.state.agent_waiting_for_confirmation = False

        # Create runner
        runner = ConversationRunner(mock_conversation, mock_agent)

        # Test resume
        result = runner.resume_conversation()

        # Verify resume was successful
        assert result is True
        # Verify conversation.run() was called during resume
        mock_conversation.run.assert_called()

    def test_conversation_runner_resume_when_not_paused(self) -> None:
        """Test that ConversationRunner.resume_conversation returns False when not paused."""
        # Create mock conversation and agent
        mock_conversation = MagicMock()
        mock_agent = MagicMock()

        # Set up non-paused state
        mock_conversation.state.agent_paused = False
        mock_conversation.state.agent_finished = True
        mock_conversation.state.agent_waiting_for_confirmation = False

        # Create runner
        runner = ConversationRunner(mock_conversation, mock_agent)

        # Test resume
        result = runner.resume_conversation()

        # Verify resume was not performed
        assert result is False
        # Verify conversation.run() was not called
        mock_conversation.run.assert_not_called()

    def test_conversation_runner_resume_with_exception(self) -> None:
        """Test that ConversationRunner.resume_conversation handles exceptions gracefully."""
        # Create mock conversation and agent
        mock_conversation = MagicMock()
        mock_agent = MagicMock()

        # Set up paused state
        mock_conversation.state.agent_paused = True
        mock_conversation.state.agent_finished = False
        mock_conversation.state.agent_waiting_for_confirmation = False

        # Create runner
        runner = ConversationRunner(mock_conversation, mock_agent)

        # Mock the _run_until_completion_or_confirmation method to raise an exception
        with patch.object(
            runner,
            "_run_until_completion_or_confirmation",
            side_effect=Exception("Test exception"),
        ):
            with patch("openhands_cli.agent_chat.print_formatted_text"):
                result = runner.resume_conversation()

        # Verify resume failed gracefully
        assert result is False
