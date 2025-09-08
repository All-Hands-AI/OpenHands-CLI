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
from unittest.mock import MagicMock

from openhands.sdk import LLM, Agent, Conversation
from prompt_toolkit.input.defaults import create_pipe_input

from openhands_cli.listeners.pause_listener import PauseListener, pause_listener


def create_test_conversation() -> Conversation:
    """Create a real conversation with mocked LLM for testing."""
    # Create a mock LLM that returns simple responses
    mock_llm = MagicMock(spec=LLM)
    mock_llm.model = "test-model"  # Add the missing model attribute
    mock_llm.completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Test response"))]
    )

    # Create a real agent with the mocked LLM
    agent = Agent(llm=mock_llm, tools=[])

    # Create a real conversation
    conversation = Conversation(agent=agent)

    return conversation


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
