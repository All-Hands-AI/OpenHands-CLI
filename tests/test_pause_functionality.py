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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from openhands.sdk import Conversation
from prompt_toolkit.input.defaults import create_pipe_input

from openhands_cli.listeners.pause_listener import PauseListener, pause_listener
from openhands_cli.runner import ConversationRunner
from openhands_cli.user_actions.types import UserConfirmation


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


class TestConversationRunnerPause:
    def _setup_conversation_mock(
        self,
        agent_paused: bool = False,
        agent_waiting_for_confirmation: bool = False,
        agent_finished: bool = False,
    ) -> MagicMock:
        convo = MagicMock()
        convo.state = SimpleNamespace(
            agent_paused=agent_paused,
            agent_waiting_for_confirmation=agent_waiting_for_confirmation,
            agent_finished=agent_finished,
            events=[],
        )
        return convo

    @pytest.mark.parametrize("paused", [False, True])
    def test_non_confirmation_mode_runs_once(self, paused: bool) -> None:
        """
        1. Confirmation mode is not on
        2. Process message resumes paused conversation or continues running conversation
        """
        convo = self._setup_conversation_mock(
            agent_paused=paused,
            agent_waiting_for_confirmation=False,
            agent_finished=False,
        )
        cr = ConversationRunner(convo)
        cr.set_confirmation_mode(False)

        with patch.object(convo, "run") as run_mock:
            cr.process_message(message=None)

        run_mock.assert_called_once()

    @pytest.mark.parametrize(
        "confirmation, agent_paused, agent_finished, expected_run_calls",
        [
            # Case 1: Agent paused & waiting; user DEFERS -> early return, no run()
            (UserConfirmation.DEFER, True, False, 0),
            # Case 2: Agent waiting; user ACCEPTS -> run() once, break (finished=True)
            (UserConfirmation.ACCEPT, False, True, 1),
        ],
    )
    def test_confirmation_mode_waiting_and_user_decision_controls_run(
        self,
        confirmation: UserConfirmation,
        agent_paused: bool,
        agent_finished: bool,
        expected_run_calls: int,
    ) -> None:
        """
        1. Agent may be paused but is waiting for consent on actions
        2. If paused, we should have asked for confirmation on action
        3. If not paused, we should still ask for confirmation on actions
        4. If deferred no run call to agent should be made
        5. If accepted, run call to agent should be made

        """
        convo = self._setup_conversation_mock(
            agent_paused=agent_paused,
            agent_waiting_for_confirmation=True,
            agent_finished=agent_finished,
        )
        cr = ConversationRunner(convo)
        cr.set_confirmation_mode(True)

        with (
            patch.object(cr, "_handle_confirmation_request", return_value=confirmation),
            patch.object(convo, "run") as run_mock,
        ):
            cr.process_message(message=None)

        assert run_mock.call_count == expected_run_calls

    def test_confirmation_mode_not_waiting__runs_once_when_finished_true(self) -> None:
        """
        1. Agent was not waiting
        2. Agent finished without any actions
        3. Conversation should finished without asking user for instructions
        """
        convo = self._setup_conversation_mock(
            agent_paused=True,
            agent_waiting_for_confirmation=False,
            agent_finished=True,
        )
        cr = ConversationRunner(convo)
        cr.set_confirmation_mode(True)

        with (
            patch.object(cr, "_handle_confirmation_request") as _mock_h,
            patch.object(convo, "run") as run_mock,
        ):
            cr.process_message(message=None)

        # No confirmation was needed up front; we still expect exactly one run.
        run_mock.assert_called_once()
        _mock_h.assert_not_called()
