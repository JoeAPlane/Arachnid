"""Read-only discovery of visible top-level Windows application windows."""

import ctypes
import logging
import os
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum, auto
from time import monotonic

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass(frozen=True)
class WindowBounds:
    """Visible frame bounds in physical desktop pixels, right/bottom exclusive."""

    left: int
    top: int
    right: int
    bottom: int


type WindowKey = tuple[int, int]  # (HWND, process ID)
type WindowSnapshot = dict[WindowKey, WindowBounds]


@dataclass(frozen=True)
class ForegroundWindow:
    key: WindowKey
    bounds: WindowBounds
    monitor: WindowBounds
    fullscreen: bool
    navigable: bool


class _ForegroundState(Enum):
    OWN_WINDOW = auto()


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD), ("monitor", wintypes.RECT),
        ("work", wintypes.RECT), ("flags", wintypes.DWORD),
    ]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_dwmapi = ctypes.WinDLL("dwmapi")
_enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_event_proc = ctypes.WINFUNCTYPE(
    None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND, wintypes.LONG,
    wintypes.LONG, wintypes.DWORD, wintypes.DWORD
)


def _bind(dll, name, result, *args):
    function = getattr(dll, name)
    function.restype = result
    function.argtypes = args
    return function


_enum = _bind(_user32, "EnumWindows", wintypes.BOOL, _enum_proc, wintypes.LPARAM)
_visible = _bind(_user32, "IsWindowVisible", wintypes.BOOL, wintypes.HWND)
_minimized = _bind(_user32, "IsIconic", wintypes.BOOL, wintypes.HWND)
_maximized = _bind(_user32, "IsZoomed", wintypes.BOOL, wintypes.HWND)
_shell = _bind(_user32, "GetShellWindow", wintypes.HWND)
_style = _bind(_user32, "GetWindowLongW", wintypes.LONG, wintypes.HWND, ctypes.c_int)
_title_length = _bind(_user32, "GetWindowTextLengthW", ctypes.c_int, wintypes.HWND)
_class_name = _bind(
    _user32, "GetClassNameW", ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
)
_process_id = _bind(
    _user32, "GetWindowThreadProcessId", wintypes.DWORD,
    wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
)
_rect = _bind(
    _user32, "GetWindowRect", wintypes.BOOL, wintypes.HWND, ctypes.POINTER(wintypes.RECT)
)
_monitor = _bind(
    _user32, "MonitorFromRect", wintypes.HMONITOR,
    ctypes.POINTER(wintypes.RECT), wintypes.DWORD
)
_monitor_info = _bind(
    _user32, "GetMonitorInfoW", wintypes.BOOL,
    wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo)
)
_foreground = _bind(_user32, "GetForegroundWindow", wintypes.HWND)
_hook_foreground = _bind(
    _user32, "SetWinEventHook", wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
    wintypes.HMODULE, _event_proc, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD
)
_unhook_foreground = _bind(_user32, "UnhookWinEvent", wintypes.BOOL, wintypes.HANDLE)
_dwm_attr = _bind(
    _dwmapi, "DwmGetWindowAttribute", wintypes.LONG,
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD
)

_GWL_EXSTYLE = -20
_GWL_STYLE = -16
_WS_EX_TOOLWINDOW = 0x80
_WS_CAPTION = 0x00C00000
_DWMWA_EXTENDED_FRAME_BOUNDS = 9
_DWMWA_CLOAKED = 14
_MONITOR_DEFAULTTONULL = 0
_EVENT_SYSTEM_FOREGROUND = 3
_WINEVENT_OUTOFCONTEXT = 0
_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def _bounds(rect: wintypes.RECT) -> WindowBounds:
    return WindowBounds(rect.left, rect.top, rect.right, rect.bottom)


def _visible_frame(hwnd: int) -> wintypes.RECT | None:
    cloaked = wintypes.DWORD()
    if (_dwm_attr(hwnd, _DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0
            and cloaked.value):
        return None
    rect = wintypes.RECT()
    if _dwm_attr(hwnd, _DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
        if not _rect(hwnd, ctypes.byref(rect)):
            return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect


def _shell_class(hwnd: int, buffer) -> bool:
    return not _class_name(hwnd, buffer, len(buffer)) or buffer.value in _SHELL_CLASSES


def _ordinary_window(hwnd: int) -> bool:
    return bool(not _style(hwnd, _GWL_EXSTYLE) & _WS_EX_TOOLWINDOW and _title_length(hwnd))


def covers_monitor(window: WindowBounds, monitor: WindowBounds) -> bool:
    tolerance = 2  # Allow a small difference in the compositor's physical bounds.
    return (
        window.left <= monitor.left + tolerance and window.top <= monitor.top + tolerance
        and window.right >= monitor.right - tolerance
        and window.bottom >= monitor.bottom - tolerance
    )


def _sample_foreground() -> ForegroundWindow | _ForegroundState | None:
    hwnd = _foreground()
    if not hwnd or hwnd == _shell() or not _visible(hwnd) or _minimized(hwnd):
        return None
    pid = wintypes.DWORD()
    if not _process_id(hwnd, ctypes.byref(pid)):
        return None
    if pid.value == os.getpid():
        return _ForegroundState.OWN_WINDOW
    if _shell_class(hwnd, ctypes.create_unicode_buffer(256)):
        return None
    rect = _visible_frame(hwnd)
    if rect is None:
        return None
    monitor = _monitor(ctypes.byref(rect), _MONITOR_DEFAULTTONULL)
    info = _MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not monitor or not _monitor_info(monitor, ctypes.byref(info)):
        return None
    bounds, screen = _bounds(rect), _bounds(info.monitor)
    fullscreen = covers_monitor(bounds, screen)
    if fullscreen and _maximized(hwnd):
        # A normal maximized window can fill the monitor with an auto-hidden taskbar.
        fullscreen = (_style(hwnd, _GWL_STYLE) & _WS_CAPTION) != _WS_CAPTION
    return ForegroundWindow(
        (hwnd, pid.value), bounds, screen, fullscreen,
        navigable=not fullscreen and _ordinary_window(hwnd),
    )


def read_foreground() -> ForegroundWindow | None:
    sample = _sample_foreground()
    return sample if isinstance(sample, ForegroundWindow) else None


def scan_windows() -> WindowSnapshot:
    windows: WindowSnapshot = {}
    shell_window = _shell()
    own_pid = os.getpid()
    class_name = ctypes.create_unicode_buffer(256)

    @_enum_proc
    def collect(hwnd, lparam):
        if hwnd == shell_window or not _visible(hwnd) or _minimized(hwnd):
            return True

        pid = wintypes.DWORD()
        if not _process_id(hwnd, ctypes.byref(pid)) or pid.value == own_pid:
            return True
        if not _ordinary_window(hwnd) or _shell_class(hwnd, class_name):
            return True
        rect = _visible_frame(hwnd)
        if rect is not None and _monitor(ctypes.byref(rect), _MONITOR_DEFAULTTONULL):
            windows[hwnd, pid.value] = _bounds(rect)
        return True

    if not _enum(collect, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return windows


class WindowMonitor(QObject):
    foreground_changed = Signal(object)
    _FULLSCREEN_FOCUS_GRACE = 0.15

    def __init__(self, parent: QObject, watch: bool) -> None:
        super().__init__(parent)
        self.windows: WindowSnapshot = {}
        self._watch = watch
        self._scan_failed = False
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.refresh)
        if watch:
            self._timer.start()
        self.foreground: ForegroundWindow | None = None
        self._missing_since: float | None = None
        self._foreground_timer = QTimer(self)
        self._foreground_timer.setInterval(75)
        self._foreground_timer.timeout.connect(self.refresh_foreground)
        self._focus_refresh = QTimer(self)
        self._focus_refresh.setSingleShot(True)
        self._focus_refresh.timeout.connect(self.refresh_foreground)
        self._focus_callback = _event_proc(self._queue_focus_refresh)
        self._focus_hook = None

    def start_foreground(self) -> None:
        if self._foreground_timer.isActive():
            return
        self._focus_hook = _hook_foreground(
            _EVENT_SYSTEM_FOREGROUND, _EVENT_SYSTEM_FOREGROUND,
            None, self._focus_callback, 0, 0, _WINEVENT_OUTOFCONTEXT,
        )
        self._foreground_timer.start()
        self.refresh_foreground()

    def stop(self) -> None:
        if self._focus_hook:
            _unhook_foreground(self._focus_hook)
            self._focus_hook = None
        self._focus_refresh.stop()
        self._foreground_timer.stop()
        self._timer.stop()
        self._missing_since = None

    def _queue_focus_refresh(self, *_event) -> None:
        self._focus_refresh.start(0)

    def refresh_foreground(self) -> None:
        foreground = _sample_foreground()
        if foreground is _ForegroundState.OWN_WINDOW:
            # Opening our settings or menu preserves the external window snapshot.
            self._missing_since = None
            return
        if foreground is None and self.foreground is not None and self.foreground.fullscreen:
            now = monotonic()
            if self._missing_since is None:
                self._missing_since = now
            if now - self._missing_since < self._FULLSCREEN_FOCUS_GRACE:
                return
        self._missing_since = None
        if foreground != self.foreground:
            self.foreground = foreground
            self.foreground_changed.emit(foreground)

    def refresh(self) -> None:
        try:
            current = scan_windows()
        except OSError as error:
            if not self._scan_failed:
                logging.warning("Unable to scan desktop windows: %s", error)
            self._scan_failed = True
            return

        self._scan_failed = False
        if self._watch:
            for key, bounds in sorted(current.items()):
                old = self.windows.get(key)
                if old is None:
                    logging.info("found %s %s", key, bounds)
                elif bounds != old:
                    logging.info("moved/resized %s %s", key, bounds)
            for key in sorted(self.windows.keys() - current.keys()):
                logging.info("gone %s", key)
        self.windows = current
