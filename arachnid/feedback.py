"""Optional asynchronous servo feedback for deliberate clicks."""

import logging
from pathlib import Path

_SERVO = Path(__file__).with_name("assets") / "servo.wav"


def play_click() -> None:
    import winsound

    try:
        winsound.PlaySound(
            str(_SERVO), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
        )
    except RuntimeError:
        logging.warning("Windows could not play the Arachnid click sound.")
