from prompt_toolkit.widgets import Frame

from openhands_cli.tui import build_command_frame, build_output_frame


def test_build_command_frame_type():
    frame = build_command_frame("echo hi")
    assert isinstance(frame, Frame)


def test_build_output_frame_type():
    frame = build_output_frame("hello")
    assert isinstance(frame, Frame)
