"""Opt-in native input check. The test briefly moves the real mouse pointer."""

import ctypes
import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from ctypes import wintypes
from time import perf_counter

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from arachnid.behavior import Activity
from arachnid.gait import CYCLE_DISTANCE
from arachnid.navigation import FOOT_CONTACT, Edge
from arachnid.overlay import Overlay

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or os.environ.get("ARACHNID_DESKTOP_TEST") != "1",
    reason="requires an unlocked Windows desktop and opt-in to real pointer input",
)

_TARGET = """
import sys
from PySide6.QtWidgets import QApplication, QPushButton

app = QApplication([])
button = QPushButton("ARACHNID click-through test target")
button.setWindowTitle(sys.argv[1])
button.clicked.connect(lambda: print("received click", flush=True))
button.resize(420, 280)
if len(sys.argv) > 2 and sys.argv[2] == "fullscreen":
    button.showFullScreen()
else:
    button.show()
raise SystemExit(app.exec())
"""


def wait_for(predicate, duration_ms=2500):
    deadline = perf_counter() + duration_ms / 1000
    while perf_counter() < deadline:
        result = predicate()
        if result:
            return result
        QTest.qWait(15)
    assert predicate(), "Expected desktop event did not occur"


def focus_fixture(hwnd):
    """Acquire foreground focus without sending input to an unrelated window."""
    from arachnid.windows import _bind, _foreground, _rect, _style, _user32

    activate = _bind(_user32, "SetForegroundWindow", wintypes.BOOL, wintypes.HWND)
    activate(hwnd)
    QTest.qWait(100)
    if _foreground() == hwnd:
        return

    position = _bind(
        _user32, "SetWindowPos", wintypes.BOOL, wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
    )
    hit = _bind(_user32, "WindowFromPoint", wintypes.HWND, wintypes.POINT)
    get_cursor = _bind(_user32, "GetCursorPos", wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
    set_cursor = _bind(_user32, "SetCursorPos", wintypes.BOOL, ctypes.c_int, ctypes.c_int)
    mouse = _bind(
        _user32, "mouse_event", None,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.WPARAM,
    )
    keep_geometry = 0x0013  # SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    was_topmost = bool(_style(hwnd, -20) & 0x8)  # GWL_EXSTYLE / WS_EX_TOPMOST
    assert position(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, keep_geometry)
    try:
        box = wintypes.RECT()
        assert _rect(hwnd, ctypes.byref(box))
        point = wintypes.POINT(box.left + (box.right - box.left) * 3 // 4,
                               box.top + (box.bottom - box.top) * 3 // 4)

        def focus_with_click():
            if _foreground() == hwnd:
                return True
            if hit(point) != hwnd:
                return False
            assert set_cursor(point.x, point.y)
            actual = wintypes.POINT()
            assert get_cursor(ctypes.byref(actual))
            if hit(actual) != hwnd:
                return False
            mouse(0x0002, 0, 0, 0, 0)
            mouse(0x0004, 0, 0, 0, 0)
            QTest.qWait(85)
            return _foreground() == hwnd

        wait_for(focus_with_click)
    finally:
        if not was_topmost:
            position(hwnd, wintypes.HWND(-2), 0, 0, 0, 0, keep_geometry)


def test_native_input_and_window_awareness(tmp_path, caplog):
    from arachnid.windows import WindowMonitor, _bind, _process_id, _rect, _user32, scan_windows

    find_window = _bind(
        _user32, "FindWindowW", wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR
    )
    window_at = _bind(_user32, "WindowFromPoint", wintypes.HWND, wintypes.POINT)
    get_cursor = _bind(_user32, "GetCursorPos", wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
    set_cursor = _bind(_user32, "SetCursorPos", wintypes.BOOL, ctypes.c_int, ctypes.c_int)
    mouse_event = _bind(
        _user32, "mouse_event", None,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.WPARAM,
    )
    position_window = _bind(
        _user32, "SetWindowPos", wintypes.BOOL, wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
    )
    show_window = _bind(_user32, "ShowWindow", wintypes.BOOL, wintypes.HWND, ctypes.c_int)
    post_message = _bind(
        _user32, "PostMessageW", wintypes.BOOL, wintypes.HWND, wintypes.UINT,
        wintypes.WPARAM, wintypes.LPARAM,
    )
    release_capture = _bind(_user32, "ReleaseCapture", wintypes.BOOL)

    def rect(hwnd):
        bounds = wintypes.RECT()
        assert _rect(hwnd, ctypes.byref(bounds))
        return bounds

    def point_on(widget, local):
        bounds = rect(int(widget.winId()))
        scale = widget.devicePixelRatioF()
        return wintypes.POINT(bounds.left + round(local.x() * scale),
                              bounds.top + round(local.y() * scale))

    def physical_move(point):
        deadline = perf_counter() + 1.0
        while True:
            assert set_cursor(point.x, point.y)
            QTest.qWait(35)
            actual = cursor_position()
            if abs(actual.x - point.x) <= 3 and abs(actual.y - point.y) <= 3:
                return
            if perf_counter() >= deadline:
                pytest.fail(f"The pointer moved away from ({point.x}, {point.y}) to ({actual.x}, {actual.y})")

    def cursor_position():
        actual = wintypes.POINT()
        assert get_cursor(ctypes.byref(actual))
        return actual

    def mouse(flag):
        mouse_event(flag, 0, 0, 0, 0)
        QTest.qWait(35)

    def click(expected, down=0x0002, up=0x0004):
        assert window_at(cursor_position()) == expected
        try:
            mouse(down)
        finally:
            mouse(up)

    def select_menu_action(action):
        menu = overlay._menu
        point = point_on(menu, menu.actionGeometry(action).center())
        physical_move(point)
        assert menu.actionAt(menu.mapFromGlobal(overlay.cursor().pos())) == action
        wait_for(lambda: menu.activeAction() == action)
        click(int(menu.winId()))

    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "windows"
    saved_cursor = wintypes.POINT()
    assert get_cursor(ctypes.byref(saved_cursor))
    store = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    overlay = Overlay(speed=110, paused=True, store=store)
    output = tmp_path / "target.log"
    title = f"ARACHNID input test {os.getpid()}"
    with output.open("w") as log:
        target = subprocess.Popen([sys.executable, "-u", "-c", _TARGET, title], stdout=log)
        try:
            target_hwnd = wait_for(lambda: find_window(None, title))
            target_pid = wintypes.DWORD()
            assert _process_id(target_hwnd, ctypes.byref(target_pid))
            key = (target_hwnd, target_pid.value)
            pet_hwnd = int(overlay.winId())
            anchor = rect(pet_hwnd)
            topmost = wintypes.HWND(-1)  # HWND_TOPMOST
            assert position_window(
                target_hwnd, topmost, anchor.left - 100, anchor.top - 90, 420, 360, 0
            )
            focus_fixture(target_hwnd)
            overlay.show()
            overlay.raise_()
            base = rect(pet_hwnd)
            caplog.set_level(logging.INFO)
            monitor = WindowMonitor(overlay, watch=True)
            monitor.refresh()
            assert key in monitor.windows
            assert "found" in caplog.text
            assert all(hwnd != pet_hwnd for hwnd, _ in scan_windows())
            old_bounds = monitor.windows[key]

            center = point_on(overlay, overlay.rect().center())
            transparent = point_on(overlay, QPoint(2, 2))
            # The first native paint can complete after the HWND becomes visible.
            wait_for(
                lambda: window_at(center) == pet_hwnd and window_at(transparent) == target_hwnd
            )
            # A formerly painted foot position must regain native click-through.
            front_toe = point_on(overlay, QPoint(overlay.width() // 2 + 68,
                                                overlay.height() // 2 + 41))
            overlay._puppet.walk(CYCLE_DISTANCE, 1)
            wait_for(lambda: window_at(front_toe) == pet_hwnd)
            overlay._puppet.walk(CYCLE_DISTANCE / 2, 1)
            wait_for(lambda: window_at(front_toe) == target_hwnd)
            overlay._puppet.stand()

            physical_move(transparent)
            click(target_hwnd)
            wait_for(lambda: "received click" in output.read_text())

            # The fixture is topmost too, so activating it can restack the pair.
            overlay.raise_()
            wait_for(lambda: window_at(center) == pet_hwnd)
            physical_move(center)
            assert window_at(cursor_position()) == pet_hwnd
            wait_for(lambda: overlay._hovered)
            click(pet_hwnd)
            wait_for(lambda: overlay._puppet._pet_progress < 1)

            drag_from = center
            physical_move(drag_from)
            assert window_at(cursor_position()) == pet_hwnd
            old_position = overlay.pos()
            try:
                mouse(0x0002)  # MOUSEEVENTF_LEFTDOWN
                # One large move leaves the old painted shape before the release.
                physical_move(wintypes.POINT(drag_from.x + 105, drag_from.y + 65))
                wait_for(lambda: overlay.pos() != old_position)
            finally:
                mouse(0x0004)  # MOUSEEVENTF_LEFTUP
            assert not overlay._dragging
            assert overlay.pos() != old_position

            center = point_on(overlay, overlay.rect().center())
            physical_move(center)
            assert window_at(cursor_position()) == pet_hwnd
            try:
                mouse(0x0002)
                assert overlay._press is not None
                # Simulate the OS reclaiming mouse capture mid-interaction.
                assert release_capture()
                wait_for(lambda: overlay._press is None, duration_ms=500)
            finally:
                mouse(0x0004)

            assert position_window(target_hwnd, None, base.left - 90, base.top - 75, 460, 400, 0)
            wait_for(lambda: monitor.windows.get(key) not in (None, old_bounds))
            changed = monitor.windows[key]
            assert changed.left != old_bounds.left and changed.top != old_bounds.top
            assert changed.right - changed.left > old_bounds.right - old_bounds.left
            assert changed.bottom - changed.top > old_bounds.bottom - old_bounds.top
            assert "moved/resized" in caplog.text
            show_window(target_hwnd, 6)  # SW_MINIMIZE
            wait_for(lambda: key not in monitor.windows)
            assert "gone" in caplog.text
            show_window(target_hwnd, 9)  # SW_RESTORE
            wait_for(lambda: key in monitor.windows)
            # Keep the controlled foreground window in place while using the pointer.
            focus_fixture(target_hwnd)
            overlay.raise_()

            local_center = overlay.rect().center()
            physical_move(point_on(overlay, local_center - QPoint(120, 0)))
            overlay._pause_action.trigger()
            wait_for(lambda: overlay._behavior.activity is Activity.OBSERVING)
            assert overlay._puppet._gaze[0] < 0
            assert not overlay._timer.isActive()
            physical_move(point_on(overlay, local_center - QPoint(260, 0)))
            wait_for(lambda: overlay._behavior.activity is Activity.WANDERING)
            assert overlay._timer.isActive()
            overlay._pause_action.trigger()

            center = point_on(overlay, overlay.rect().center())
            physical_move(center)
            click(pet_hwnd, down=0x0008, up=0x0010)
            wait_for(overlay._menu.isVisible)
            select_menu_action(overlay._menu.actions()[-2])
            wait_for(lambda: overlay._settings_dialog and overlay._settings_dialog.isVisible())
            overlay._settings_dialog.reject()

            physical_move(center)
            click(pet_hwnd, down=0x0008, up=0x0010)
            wait_for(overlay._menu.isVisible)
            select_menu_action(overlay._menu.actions()[-1])
            wait_for(lambda: not overlay.isVisible())
            assert post_message(target_hwnd, 0x0010, 0, 0)  # WM_CLOSE
            assert target.wait(5) == 0
            wait_for(lambda: key not in monitor.windows)
        finally:
            overlay.close()
            app.processEvents()
            set_cursor(saved_cursor.x, saved_cursor.y)
            if target.poll() is None:
                hwnd = find_window(None, title)
                if hwnd:
                    post_message(hwnd, 0x0010, 0, 0)
                else:
                    target.terminate()
                target.wait(5)


def test_native_navigation_and_foreground_fullscreen(monkeypatch, tmp_path):
    from arachnid.windows import WindowMonitor, _bind, _user32

    find = _bind(_user32, "FindWindowW", wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR)
    show = _bind(_user32, "ShowWindow", wintypes.BOOL, wintypes.HWND, ctypes.c_int)
    position = _bind(
        _user32, "SetWindowPos", wintypes.BOOL, wintypes.HWND, wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
    )
    post = _bind(
        _user32, "PostMessageW", wintypes.BOOL, wintypes.HWND, wintypes.UINT,
        wintypes.WPARAM, wintypes.LPARAM,
    )
    visible = _bind(_user32, "IsWindowVisible", wintypes.BOOL, wintypes.HWND)
    get_cursor = _bind(_user32, "GetCursorPos", wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
    set_cursor = _bind(_user32, "SetCursorPos", wintypes.BOOL, ctypes.c_int, ctypes.c_int)

    @contextmanager
    def target(mode):
        title = f"ARACHNID {mode} fixture {os.getpid()}"
        child = subprocess.Popen([sys.executable, "-u", "-c", _TARGET, title, mode])
        try:
            yield wait_for(lambda: find(None, title))
        finally:
            hwnd = find(None, title)
            if hwnd:
                assert post(hwnd, 0x10, 0, 0)  # WM_CLOSE
            assert child.wait(5) == 0

    app = QApplication.instance() or QApplication([])
    store = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    overlay = Overlay(speed=460, paused=True, store=store)
    monitor = WindowMonitor(overlay, watch=False)
    monitor.foreground_changed.connect(overlay.set_foreground)
    screen = app.primaryScreen()
    work = screen.availableGeometry()
    scale = screen.devicePixelRatio()
    origin = screen.geometry().topLeft()

    def move_target(hwnd, x, y, w, h):
        assert position(
            hwnd, None, origin.x() + round((x - origin.x()) * scale),
            origin.y() + round((y - origin.y()) * scale),
            round(w * scale), round(h * scale), 0,
        )

    def place_at(center):
        overlay._place(center - QPoint(overlay.width() // 2, overlay.height() // 2), screen)

    def current_target(hwnd):
        return monitor.foreground and monitor.foreground.key[0] == hwnd

    def focus_target(hwnd):
        focus_fixture(hwnd)
        wait_for(lambda: current_target(hwnd))

    saved_cursor = wintypes.POINT()
    assert get_cursor(ctypes.byref(saved_cursor))
    # Keep the behavior state on walking so this test isolates the route.
    monkeypatch.setattr(QCursor, "pos", lambda: QPoint(-10000, -10000))
    monitor.start_foreground()
    overlay.show()
    try:
        with target("windowed") as hwnd:
            x, y = work.x() + 310, work.y() + 245
            move_target(hwnd, x, y, 385, 320)
            focus_target(hwnd)
            original_bounds = monitor.foreground.bounds
            show(hwnd, 3)  # SW_MAXIMIZE
            wait_for(lambda: current_target(hwnd) and monitor.foreground.bounds != original_bounds)
            assert monitor.foreground.navigable and not overlay.fullscreen_suppressed
            assert visible(int(overlay.winId()))
            show(hwnd, 9)  # SW_RESTORE
            wait_for(lambda: current_target(hwnd) and monitor.foreground.bounds == original_bounds)
            surface = overlay._surface(screen)
            assert surface is not None
            perch = QPoint(round(surface.center().x()), round(surface.top() - FOOT_CONTACT))
            place_at(perch - QPoint(0, 45))
            viewport = overlay.viewport()
            local = viewport.rect().center()
            QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=local)
            # Move the painted body's center onto the top edge before release.
            global_drop = viewport.mapToGlobal(local) + QPoint(0, 45)
            app.sendEvent(viewport, QMouseEvent(
                QEvent.Type.MouseMove, QPointF(local + QPoint(0, 45)), QPointF(global_drop),
                Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
            ))
            app.sendEvent(viewport, QMouseEvent(
                QEvent.Type.MouseButtonRelease, QPointF(viewport.mapFromGlobal(global_drop)),
                QPointF(global_drop), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            ))
            assert overlay._route and overlay._route.edge is Edge.TOP
            before = overlay.pos()
            move_target(hwnd, x + 35, y + 25, 300, 270)
            wait_for(lambda: overlay.pos() != before)
            assert overlay.pos() - before == QPoint(35, 25)

            show(hwnd, 6)  # SW_MINIMIZE
            wait_for(lambda: overlay._route is None)
            assert work.contains(overlay.frameGeometry())
            show(hwnd, 9)  # SW_RESTORE
            focus_target(hwnd)
            surface = overlay._surface(screen)
            place_at(QPoint(round(surface.left() - FOOT_CONTACT - 3), round(surface.top() + 70)))
            overlay._pause_action.trigger()
            wait_for(lambda: overlay._route and overlay._route.edge is Edge.SIDE)
            assert overlay._puppet.angle == -90
            wait_for(lambda: overlay._route and overlay._route.edge is Edge.CORNER)
            wait_for(lambda: overlay._route and overlay._route.edge is Edge.TOP)
            assert overlay._puppet.angle == 0

            overlay._open_settings()
            assert overlay._settings_dialog.isVisible()
            with target("fullscreen") as full:
                focus_target(full)
                wait_for(lambda: current_target(full) and overlay.fullscreen_suppressed)
                assert monitor.foreground.fullscreen and not monitor.foreground.navigable
                assert not visible(int(overlay.winId()))
                assert overlay._route is None
                assert overlay._settings_dialog is None
                assert not overlay._behavior_timer.isActive()
                assert not overlay._timer.isActive()
                remaining = overlay._behavior.remaining
                QTest.qWait(230)
                assert overlay._behavior.remaining == remaining

            focus_target(hwnd)
            wait_for(lambda: current_target(hwnd) and overlay.isVisible())
            assert visible(int(overlay.winId()))
            assert overlay._behavior_timer.isActive()
            overlay._pause_action.trigger()
            surface = overlay._surface(screen)
            place_at(QPoint(round(surface.center().x()), round(surface.top() - FOOT_CONTACT)))
            assert overlay._try_window()
        wait_for(lambda: overlay._route is None)
        assert work.contains(overlay.frameGeometry())
    finally:
        monitor.stop()
        overlay.close()
        app.processEvents()
        set_cursor(saved_cursor.x, saved_cursor.y)
