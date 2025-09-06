import threading
import typing

from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys


class PauseListener(threading.Thread):
    """Background key listener that triggers pause on Ctrl-P.

    Starts and stops around agent run() loops to avoid interfering with user prompts.
    """

    def __init__(self, on_pause: typing.Callable, confirmation_mode: bool = False):
        super().__init__(daemon=True)
        self.on_pause = on_pause
        self._stop_event = threading.Event()
        self._input = create_input()
        self.confirmation_mode = confirmation_mode

    def _detect_pause_key_presses(self) -> bool:
        pause_detected = False

        for key_press in self._input.read_keys():
            pause_detected = pause_detected or key_press.key == Keys.ControlP
            pause_detected = pause_detected or key_press.key == Keys.ControlC
            pause_detected = pause_detected or key_press.key == Keys.ControlD

        return pause_detected

    def _execute_pause(self) -> None:
        self._stop_event.set()
        print_formatted_text(HTML(""))
        print_formatted_text(
            HTML("<gold>Pausing agent once step is completed...</gold>")
        )
        try:
            self.on_pause()
        except Exception:
            pass

    def run(self) -> None:
        try:
            with self._input.raw_mode():
                while not self._stop_event.is_set():
                    if self._detect_pause_key_presses():
                        self._execute_pause()
        finally:
            try:
                self._input.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop_event.set()
