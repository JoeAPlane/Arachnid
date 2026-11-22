"""Launch with python -m arachnid."""

import argparse
import logging
import signal
import sys
from pathlib import Path

from . import __version__


def _speed(text: str) -> float:
    try:
        speed = float(text)
    except ValueError:
        speed = 0
    if not 1 <= speed <= 600:
        raise argparse.ArgumentTypeError("speed must be a number from 1 to 600")
    return speed


def main() -> int:
    parser = argparse.ArgumentParser(description="Arachnid desktop companion")
    parser.add_argument("--version", action="version", version=f"Arachnid {__version__}")
    parser.add_argument(
        "--speed", type=_speed, default=110,
        help="horizontal speed in logical pixels per second (default: 110)"
    )
    parser.add_argument("--paused", action="store_true", help="start with motion paused")
    parser.add_argument("--watch-windows", action="store_true", help="log window bounds changes")
    parser.add_argument(
        "--settings-file", type=Path, metavar="PATH",
        help="use a separate INI file for preferences instead of the Windows profile"
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Arachnid requires Windows")

    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .instance import Instance
    from .overlay import Overlay
    from .windows import WindowMonitor

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Arachnid")
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("assets") / "arachnid.ico")))
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    store = QSettings("ARACHNID", "Desktop Companion")
    if args.settings_file is not None:
        store = QSettings(str(args.settings_file.resolve()), QSettings.Format.IniFormat)
    instance = Instance(store.fileName(), app)
    try:
        if not instance.start():
            return 0
    except RuntimeError as error:
        QMessageBox.warning(None, "Arachnid", str(error))
        return 1
    overlay = Overlay(args.speed, args.paused, store=store, startup=not args.paused)
    overlay.install_tray()
    instance.reopen.connect(overlay.reopen)
    monitor = WindowMonitor(app, args.watch_windows)
    if args.watch_windows:
        monitor.refresh()
    monitor.foreground_changed.connect(overlay.set_foreground)
    monitor.start_foreground()

    # WindowMonitor's timer returns control to Python even while motion is paused.
    previous = signal.signal(signal.SIGINT, lambda *_: app.quit())
    try:
        if not overlay.fullscreen_suppressed:
            overlay.show()
        return app.exec()
    finally:
        monitor.stop()
        instance.close()
        signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    raise SystemExit(main())
