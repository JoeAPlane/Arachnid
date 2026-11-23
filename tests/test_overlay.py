from math import hypot, pi
import sys
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, QSettings, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from arachnid.behavior import Activity
from arachnid.overlay import Overlay
from arachnid.settings import Preferences

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows Qt integration")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def overlay(app, monkeypatch, tmp_path):
    monkeypatch.setattr(QCursor, "pos", lambda: QPoint(-10000, -10000))
    store = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    pet = Overlay(speed=110, paused=True, store=store)
    pet.show()
    try:
        QTest.qWait(60)
        yield pet
    finally:
        pet.close()
        app.processEvents()


def test_pausing_resuming_and_bouncing_at_work_area_edge(app, overlay):
    area = app.primaryScreen().availableGeometry()
    right = area.x() + area.width() - overlay.width()
    overlay._place(QPoint(right - 1, area.center().y()), app.primaryScreen())
    initial = overlay.pos()
    QTest.qWait(60)
    assert overlay.pos() == initial

    overlay._pause_action.trigger()
    QTest.qWait(145)
    assert overlay.x() < initial.x()
    assert overlay.y() == initial.y()
    assert area.contains(overlay.frameGeometry())
    assert overlay._puppet.facing == -1
    assert overlay._puppet.blend > 0
    overlay._pause_action.trigger()
    stopped = overlay.pos()
    assert overlay._puppet.blend > 0
    QTest.qWait(200)
    assert overlay.pos() == stopped
    assert overlay._puppet.blend == 0


def test_qt_click_pets_the_companion_and_press_suspends_motion(overlay):
    viewport = overlay.viewport()
    center = viewport.rect().center()
    overlay._pause_action.trigger()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=center)
    held = overlay.pos()
    QTest.qWait(60)
    assert overlay.pos() == held
    assert overlay._puppet.blend == 0
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=center)
    assert overlay._puppet._pet_progress < 1
    assert overlay._behavior.activity is Activity.REACTING
    QTest.qWait(100)
    assert overlay.pos() == held
    overlay._behavior.remaining = 0
    QTest.qWait(260)
    assert overlay._behavior.activity is Activity.WANDERING
    assert overlay.pos() != held


@pytest.mark.parametrize("birdseye", [False, True])
@pytest.mark.parametrize("finish", ["graphite", "neon"])
def test_walking_and_pickup_poses_fit_inside_the_transparent_overlay(overlay, birdseye, finish):
    overlay._puppet.set_finish(finish)
    overlay._puppet.set_birdseye(birdseye)
    width, height = overlay.width(), overlay.height()
    for step in range(48):
        overlay._puppet.phase = step / 48
        overlay._puppet.blend = 1
        overlay._puppet.angle = 360 * step / 48 if birdseye else (0, -90, -45, 45, 90, 180)[step % 6]
        overlay._puppet._held = step >= 24
        overlay._puppet._carry_progress = (step % 24) / 24
        frame = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            overlay.scene().render(painter)
        finally:
            painter.end()
        assert all(frame.pixelColor(x, y).alpha() == 0
                   for x in range(width) for y in (0, height - 1))
        assert all(frame.pixelColor(x, y).alpha() == 0
                   for y in range(height) for x in (0, width - 1))


def test_second_press_of_double_click_can_begin_a_drag(overlay):
    viewport = overlay.viewport()
    center = viewport.rect().center()
    QTest.mouseDClick(viewport, Qt.MouseButton.LeftButton, pos=center)
    try:
        assert overlay._press is not None
    finally:
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=center)


def test_carry_settles_after_release_and_supports_a_quick_regrab(overlay):
    pet = overlay._puppet
    pet.set_held(True)
    assert pet._suspension() == 0
    pet._carry_animation.setCurrentTime(100)
    sag = pet._suspension()
    assert 0 < sag < 1 and pet._struggle() == 0
    pet.set_held(False)
    assert pet._suspension() == pytest.approx(sag)
    pet._carry_animation.setCurrentTime(60)
    compression = pet._suspension()
    assert 0 < compression < sag and pet._landing() < 0
    pet.set_held(True)
    assert pet._suspension() == pytest.approx(compression)
    pet.set_held(False)
    pet._carry_animation.setCurrentTime(pet._carry_animation.duration())
    assert pet._suspension() == pet._landing() == 0


def test_observation_freezes_during_drag_and_manual_pause(app, overlay, monkeypatch):
    center = overlay.frameGeometry().center()
    monkeypatch.setattr(QCursor, "pos", lambda: center + QPoint(100, -10))
    overlay._pause_action.trigger()
    QTest.qWait(200)
    assert overlay._behavior.activity is Activity.OBSERVING
    assert overlay._puppet._gaze[0] > 0
    QTest.qWait(150)  # Allow the brief autonomous brake to finish.
    assert not overlay._timer.isActive()

    viewport = overlay.viewport()
    start = viewport.rect().center()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
    old_pos = overlay.pos()
    old_time = overlay._behavior.remaining
    delta = QPoint(-100, 0)
    moved = QMouseEvent(
        QEvent.Type.MouseMove, QPointF(start + delta), QPointF(center + delta),
        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    app.sendEvent(viewport, moved)
    assert overlay._dragging
    assert overlay._puppet._held
    assert overlay.pos() != old_pos
    drop_position = center + delta - overlay._drag_offset
    gap = overlay.pos() - drop_position
    assert 0 < hypot(gap.x(), gap.y()) <= 27
    QTest.qWait(180)
    assert overlay._behavior.remaining == old_time
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=viewport.mapFromGlobal(center + delta))
    assert overlay.pos() == drop_position
    assert not overlay._puppet._held
    assert not overlay._drag_timer.isActive()
    assert overlay._behavior.activity is Activity.OBSERVING
    assert overlay._behavior_timer.isActive()

    overlay._pause_action.trigger()
    monkeypatch.setattr(QCursor, "pos", lambda: QPoint(-10000, -10000))
    QTest.qWait(180)
    assert overlay._behavior.remaining == old_time
    overlay._pause_action.trigger()
    QTest.qWait(200)
    assert overlay._behavior.activity is Activity.WANDERING


def test_fullscreen_switch_preserves_manual_pause(app, overlay):
    from arachnid.windows import ForegroundWindow, WindowBounds

    bounds = WindowBounds(0, 0, 1920, 1080)
    overlay.set_foreground(ForegroundWindow((1, 2), bounds, bounds, True, False))
    assert not overlay.isVisible()
    overlay.set_foreground(None)
    assert overlay.isVisible()
    assert not overlay._timer.isActive()
    assert not overlay._behavior_timer.isActive()


def test_tray_controls_work_while_hidden_and_preserve_fullscreen_policy(overlay):
    from arachnid.windows import ForegroundWindow, WindowBounds

    overlay.install_tray()
    assert not overlay._tray.icon().isNull()
    visibility, pause, rest, settings, _, quit_app = overlay._tray.contextMenu().actions()
    assert (pause, rest, settings, visibility, quit_app) == tuple(overlay._menu.actions())

    visibility.trigger()
    assert visibility.text() == "Show Arachnid"
    assert not overlay.isVisible()
    pause.trigger()
    assert pause.text() == "Pause"
    rest.trigger()
    assert rest.text() == "Wake Up"
    settings.trigger()
    assert overlay._settings_dialog.isVisible()
    overlay._settings_dialog.reject()
    assert not overlay._behavior_timer.isActive()

    bounds = WindowBounds(0, 0, 1920, 1080)
    fullscreen = ForegroundWindow((1, 2), bounds, bounds, True, False)
    overlay.set_foreground(fullscreen)
    assert not settings.isEnabled()
    overlay.set_foreground(None)
    assert settings.isEnabled()
    assert not overlay.isVisible()
    overlay.set_foreground(fullscreen)
    visibility.trigger()
    assert not overlay.isVisible()
    overlay.set_foreground(None)
    assert overlay.isVisible()
    assert overlay._behavior.activity is Activity.SLEEPING
    rest.trigger()
    assert overlay._behavior_timer.isActive()

    visibility.trigger()
    rest.trigger()
    quit_app.trigger()
    assert not overlay._tray.isVisible()


def test_window_close_hides_and_tray_click_reopens(overlay, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon

    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    overlay.install_tray()
    assert not overlay.close()
    assert not overlay.isVisible()
    assert overlay._tray.isVisible()
    overlay._tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
    assert overlay.isVisible()
    overlay._quit_action.trigger()
    assert not overlay._tray.isVisible()


def test_full_window_scan_timer_runs_only_for_diagnostics(app):
    from arachnid.windows import WindowMonitor

    quiet = WindowMonitor(app, watch=False)
    diagnostic = WindowMonitor(app, watch=True)
    try:
        assert not quiet._timer.isActive()
        assert diagnostic._timer.isActive()
    finally:
        quiet.stop()
        diagnostic.stop()


def test_transient_focus_loss_does_not_resume_fullscreen(overlay, monkeypatch):
    from arachnid import windows

    bounds = windows.WindowBounds(0, 0, 1920, 1080)
    fullscreen = windows.ForegroundWindow((1, 2), bounds, bounds, True, False)
    monitor = windows.WindowMonitor(overlay, watch=False)
    monitor.foreground_changed.connect(overlay.set_foreground)
    sample = fullscreen
    now = 10.0
    monkeypatch.setattr(windows, "_sample_foreground", lambda: sample)
    monkeypatch.setattr(windows, "monotonic", lambda: now)

    monitor.refresh_foreground()
    assert not overlay.isVisible()
    sample = None
    monitor.refresh_foreground()
    now += 0.1
    monitor.refresh_foreground()
    assert not overlay.isVisible()
    sample = fullscreen
    monitor.refresh_foreground()
    sample = None
    now += 0.1
    monitor.refresh_foreground()
    assert not overlay.isVisible()
    now += 0.16
    monitor.refresh_foreground()
    assert overlay.isVisible()
    assert not overlay._timer.isActive()


def test_own_settings_focus_preserves_foreground_but_desktop_clears_it(overlay, monkeypatch):
    from arachnid import windows

    monitor_bounds = windows.WindowBounds(0, 0, 1920, 1080)
    bounds = windows.WindowBounds(300, 280, 1200, 850)
    external = windows.ForegroundWindow((1, 2), bounds, monitor_bounds, False, True)
    monitor = windows.WindowMonitor(overlay, watch=False)
    monitor.foreground_changed.connect(overlay.set_foreground)
    sample = external
    monkeypatch.setattr(windows, "_sample_foreground", lambda: sample)

    monitor.refresh_foreground()
    overlay._open_settings()
    sample = windows._ForegroundState.OWN_WINDOW
    monitor.refresh_foreground()
    assert overlay._foreground == external
    sample = None
    monitor.refresh_foreground()
    assert overlay._foreground is None
    overlay._settings_dialog.reject()


def test_removed_display_rehomes_companion_to_nearest_work_area(overlay, monkeypatch):
    primary = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1920, 1040))
    nearby = SimpleNamespace(availableGeometry=lambda: QRect(-1400, 60, 1000, 700))
    pose = QRect(-1700, 500, overlay.width(), overlay.height())
    moves = []
    monkeypatch.setattr(QGuiApplication, "primaryScreen", lambda: primary)
    monkeypatch.setattr(QGuiApplication, "screens", lambda: [primary, nearby])
    monkeypatch.setattr(QGuiApplication, "screenAt", lambda _: None)
    monkeypatch.setattr(overlay, "frameGeometry", lambda: pose)
    monkeypatch.setattr(overlay, "pos", lambda: pose.topLeft())
    monkeypatch.setattr(overlay, "move", lambda x, y: moves.append((x, y)))

    overlay._keep_visible()
    assert moves == [(-1400, 500)]
    assert not overlay._timer.isActive()


def test_display_gap_suspends_and_restores_active_timers(overlay, monkeypatch):
    screen = QGuiApplication.primaryScreen()
    overlay._pause_action.trigger()
    assert overlay._timer.isActive()

    monkeypatch.setattr(QGuiApplication, "primaryScreen", lambda: None)
    monkeypatch.setattr(QGuiApplication, "screenAt", lambda _: None)
    monkeypatch.setattr(QGuiApplication, "screens", lambda: [])
    overlay._keep_visible()
    assert not overlay._timer.isActive()
    assert not overlay._behavior_timer.isActive()

    monkeypatch.setattr(QGuiApplication, "primaryScreen", lambda: screen)
    monkeypatch.setattr(QGuiApplication, "screenAt", lambda _: screen)
    overlay._keep_visible()
    assert overlay._timer.isActive()
    assert overlay._behavior_timer.isActive()


def test_first_tick_after_long_sleep_preserves_walk_and_behavior_time(overlay, monkeypatch):
    from arachnid import overlay as overlay_module

    overlay._pause_action.trigger()
    overlay._behavior.remaining = 4.0
    overlay._last_decision = overlay._last_tick = 100.0
    monkeypatch.setattr(overlay_module, "perf_counter", lambda: 3700.0)
    before = overlay.pos()
    overlay._advance_behavior()
    overlay._step()
    assert overlay._behavior.remaining == pytest.approx(3.75)
    assert (overlay.pos() - before).manhattanLength() <= 6


def test_negative_origin_surface_rejects_stale_scaled_monitor(overlay):
    from arachnid.windows import ForegroundWindow, WindowBounds

    monitor = WindowBounds(-1920, 120, 0, 1200)
    bounds = WindowBounds(-1710, 420, -1110, 960)
    overlay.set_foreground(ForegroundWindow((1, 2), bounds, monitor, False, True))
    geometry = QRect(-1920, 120, 1280, 720)
    screen = SimpleNamespace(geometry=lambda: geometry, devicePixelRatio=lambda: 1.5)
    assert overlay._surface(screen) == QRectF(-1780, 320, 400, 360)
    geometry.setHeight(690)
    assert overlay._surface(screen) is None


def test_drop_uses_release_display_after_last_move(overlay, monkeypatch):
    # Qt leaves the left monitor's physical origin in place while scaling its size.
    left = SimpleNamespace(availableGeometry=lambda: QRect(-1920, 120, 1280, 720))
    right = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1920, 1040))
    monkeypatch.setattr(QGuiApplication, "screenAt", lambda p: left if p.x() < 0 else right)
    placed = []
    monkeypatch.setattr(overlay, "_place", lambda p, screen: placed.append((p, screen)))
    overlay._press = QPoint(100, 280)
    overlay._dragging = True
    overlay._drag_offset = QPoint(30, 20)
    overlay._drag_cursor = QPoint(60, 300)
    release = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(30, 20), QPointF(-800, 340),
                          Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    overlay.mouseReleaseEvent(release)
    assert placed == [(QPoint(-830, 320), left)]


def test_display_removal_ends_drag_on_disconnected_screen(overlay, monkeypatch):
    overlay._press = QPoint(-900, 300)
    overlay._drag_cursor = QPoint(-850, 310)
    overlay._dragging = True
    overlay._drag_timer.start()
    monkeypatch.setattr(QGuiApplication, "screenAt", lambda _: None)
    overlay._keep_visible()
    assert overlay._press is None
    assert not overlay._drag_timer.isActive()


def test_settings_preview_cancels_and_save_updates_the_live_overlay(overlay, monkeypatch):
    from arachnid import overlay as overlay_module

    clicks = []
    monkeypatch.setattr(overlay_module, "play_click", lambda: clicks.append("servo"))
    overlay._pause_action.trigger()
    overlay._open_settings()
    dialog = overlay._settings_dialog
    assert dialog.isVisible()
    assert not overlay._timer.isActive()
    assert not overlay._behavior_timer.isActive()
    dialog._finish.setCurrentIndex(dialog._finish.findData("foundry"))
    dialog.reject()
    assert Preferences.load(overlay._store) == Preferences()

    overlay._open_settings()
    dialog = overlay._settings_dialog
    dialog._finish.setCurrentIndex(dialog._finish.findData("glacier"))
    dialog._effects.setChecked(False)
    dialog._sound.setChecked(True)
    dialog.accept()

    reopened = QSettings(overlay._store.fileName(), QSettings.Format.IniFormat)
    assert Preferences.load(reopened) == Preferences("glacier", effects=False, sound=True)
    assert overlay._puppet._optic == QColor("#8bdcfd")
    assert overlay._timer.isActive()
    QTest.mouseClick(overlay.viewport(), Qt.MouseButton.LeftButton, pos=overlay.viewport().rect().center())
    assert clicks == ["servo"]
    assert overlay._puppet._light_pulse == 0


def test_one_rest_action_controls_forced_sleep_and_wake(overlay):
    overlay._pause_action.trigger()
    overlay._rest_action.trigger()
    assert overlay._rest_action.text() == "Wake Up"
    assert overlay._puppet._activity is Activity.SLEEPING
    assert not overlay._timer.isActive()
    assert not overlay._behavior_timer.isActive()
    viewport = overlay.viewport()
    QTest.mouseClick(viewport, Qt.MouseButton.LeftButton, pos=viewport.rect().center())
    assert overlay._behavior.activity is Activity.SLEEPING
    overlay._rest_action.trigger()
    assert overlay._rest_action.text() == "Rest"
    assert overlay._behavior.activity is Activity.WANDERING
    assert overlay._timer.isActive()
    overlay._behavior.remaining = 0
    overlay._advance_behavior()
    assert overlay._rest_action.text() == "Wake Up"
    overlay._rest_action.trigger()
    assert overlay._behavior.activity is Activity.WANDERING


def test_overhead_setting_persists_and_reflects_at_both_work_area_edges(app, overlay):
    overlay._open_settings()
    dialog = overlay._settings_dialog
    dialog._birdseye.setChecked(True)
    dialog.accept()
    store = QSettings(overlay._store.fileName(), QSettings.Format.IniFormat)
    assert Preferences.load(store).birdseye
    assert overlay._puppet._birdseye
    screen = app.primaryScreen()
    area = screen.availableGeometry()
    overlay._place(QPoint(area.x() + area.width() - overlay.width() - 1,
                          area.y() + area.height() - overlay.height() - 1), screen)
    x, y = overlay.x(), overlay.y()
    overlay._heading = pi / 4
    overlay._step_overhead(screen, 0.12, 0.12)
    assert overlay.x() < x and overlay.y() < y
    assert -pi < overlay._heading < -pi / 2
    assert area.contains(overlay.frameGeometry())
    assert not overlay._try_window()


def test_size_setting_scales_live_overlay_and_persists(app, overlay):
    center = overlay.frameGeometry().center()
    overlay._open_settings()
    dialog = overlay._settings_dialog
    dialog._size.setValue(140)
    assert overlay.width() == 176
    dialog.accept()
    assert overlay.width() == overlay.height() == 246
    assert overlay.transform().m11() == pytest.approx(1.4)
    assert overlay.frameGeometry().center() == center
    assert Preferences.load(overlay._store).size == 140
    assert app.primaryScreen().availableGeometry().contains(overlay.frameGeometry())


def test_curled_sleep_setting_animates_into_sleep_and_out_on_wake(overlay):
    pet = overlay._puppet
    overlay._rest_action.trigger()
    assert pet._curl == 0
    overlay._open_settings()
    overlay._settings_dialog._curled_sleep.setChecked(True)
    overlay._settings_dialog.accept()
    assert Preferences.load(overlay._store).curled_sleep
    pet._curl_animation.setCurrentTime(pet._curl_animation.duration() // 2)
    assert 0 < pet._curl < 1
    pet._curl_animation.setCurrentTime(pet._curl_animation.duration())
    assert pet._curl == 1
    overlay._rest_action.trigger()
    pet._curl_animation.setCurrentTime(pet._curl_animation.duration())
    assert pet._curl == 0


def test_petting_eyes_close_and_reopen_even_while_paused(overlay):
    pet = overlay._puppet
    QTest.mouseClick(overlay.viewport(), Qt.MouseButton.LeftButton, pos=overlay.viewport().rect().center())
    pet._petting.setCurrentTime(pet._petting.duration() // 2)
    assert pet._eye_closure() == 1
    pet._petting.setCurrentTime(pet._petting.duration())
    assert pet._eye_closure() == 0


def test_startup_plays_once_and_hiding_cancels_it(app, tmp_path):
    store = QSettings(str(tmp_path / "startup.ini"), QSettings.Format.IniFormat)
    overlay = Overlay(110, False, store=store, startup=True)
    try:
        assert overlay._preferences.finish == "blackout"
        overlay.show()
        assert overlay._puppet.entering
        assert not overlay._timer.isActive()
        overlay.hide()
        assert not overlay._puppet.entering
        overlay.show()
        assert not overlay._puppet.entering
        assert overlay._timer.isActive()
    finally:
        overlay.close()


def test_saved_finish_is_kept_when_default_changes(tmp_path):
    store = QSettings(str(tmp_path / "old.ini"), QSettings.Format.IniFormat)
    store.setValue("appearance/finish", "graphite")
    assert Preferences.load(store).finish == "graphite"


def test_companion_is_painted_when_intro_is_skipped(overlay):
    assert overlay._puppet._intro_progress == 1
