from math import hypot

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSettings, Qt
from PySide6.QtGui import QImage, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication

from arachnid.behavior import Activity
from arachnid.desktop_edges import DesktopRoute
from arachnid.navigation import Edge, WindowRoute
from arachnid.overlay import Overlay
from arachnid.settings import Preferences, SettingsDialog
from arachnid.throwing import (
    GRAVITY, MAX_ELAPSED, MAX_RELEASE_SPEED, CursorHistory, ThrowBounds, ThrowMotion,
)
from arachnid.windows import ForegroundWindow, WindowBounds


BOX = ThrowBounds(80, 84, 840, 570, 88, 832)


def estimate(vx, vy, step):
    samples = CursorHistory()
    for index in range(round(0.10 / step) + 1):
        elapsed = index * step
        samples.add(10 + elapsed, vx * elapsed, vy * elapsed)
    return samples.release()


@pytest.mark.parametrize("step", [0.001, 0.005, 0.016, 0.032])
def test_release_preserves_direction_at_different_input_rates(step):
    assert estimate(710, -330, step) == pytest.approx((710, -330))
    assert estimate(200, 45, step) is None


def test_release_rejects_jitter_stale_or_invalid_intervals_and_clamps_speed():
    samples = CursorHistory()
    for i in range(100):
        samples.add(i / 1000, 200 + (i % 5) - 2, -150 + (i % 3))
    assert samples.release() is None
    samples.clear()
    samples.add(1, 0, 0)
    samples.add(1, 100, 200)
    samples.add(0.5, -300, 100)
    samples.add(float("nan"), 0, 0)
    assert samples.release() is None
    samples.add(1.04, 260, 280)
    assert samples.release() is None
    samples.add(1.055, 310, 305)
    assert hypot(*samples.release()) == pytest.approx(MAX_RELEASE_SPEED)
    assert samples.release()[1] > 0
    samples.add(1.12, 310, 305)
    assert samples.release() is None


def test_gravity_and_damping_are_elapsed_time_based():
    states = []
    for frequency in (30, 60, 144):
        motion = ThrowMotion(240, 330, 500, -235, BOX)
        for _ in range(frequency // 3):
            motion.advance(1 / frequency)
        states.append((motion.x, motion.y, motion.vx, motion.vy))
    assert states[0] == pytest.approx(states[1])
    assert states[0] == pytest.approx(states[2])
    assert states[0][0] > 240
    assert states[0][2] < 500
    assert states[0][3] == pytest.approx(-235 + GRAVITY / 3)


def test_frame_stalls_are_bounded():
    stalled = ThrowMotion(350, 300, 800, -300, BOX)
    regular = ThrowMotion(350, 300, 800, -300, BOX)
    stalled.advance(2000)
    regular.advance(MAX_ELAPSED)
    assert stalled == regular
    assert not stalled.advance(-10)
    assert not stalled.advance(float("inf"))
    assert stalled == regular


@pytest.mark.parametrize(("start", "velocity"), [(82, -1650), (838, 1650)])
def test_side_collision_keeps_center_inside_the_body_envelope(start, velocity):
    motion = ThrowMotion(start, 300, velocity, 0, BOX)
    motion.advance(0.016)
    assert BOX.left <= motion.x <= BOX.right
    assert motion.vx * velocity < 0
    assert abs(motion.vx) < abs(velocity) / 2


def test_top_collision_turns_motion_downward():
    motion = ThrowMotion(300, 86, 0, -1500, BOX)
    motion.advance(0.016)
    assert BOX.top <= motion.y < BOX.top + 8
    assert 0 < motion.vy < 400


@pytest.mark.parametrize(("velocity", "bounce"), [(50, False), (1250, True)])
def test_bottom_recovery_has_a_finite_slide_and_at_most_one_bounce(velocity, bounce):
    motion = ThrowMotion(BOX.left, BOX.floor - 0.01, -140, velocity, BOX)
    assert not motion.advance(0.016)
    assert motion.bounced is bounce
    assert motion.impact > 0
    for _ in range(80):
        assert BOX.top <= motion.y <= BOX.floor
        assert BOX.left <= motion.x <= BOX.right
        if motion.advance(0.016):
            break
    else:
        pytest.fail("Throw did not recover")
    assert motion.y == BOX.floor and motion.vx == motion.vy == 0
    assert BOX.roam_left <= motion.x <= BOX.roam_right


@pytest.fixture
def companion(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    clock = [10.0]
    monkeypatch.setattr("arachnid.overlay.perf_counter", lambda: clock[0])
    store = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    pet = Overlay(110, True, store, desktop_preview=True)
    pet.show()
    yield pet, clock
    pet.close()
    app.processEvents()


def point_event(pet, clock, event_type, position, delay=0.0):
    clock[0] += delay
    button = Qt.MouseButton.LeftButton
    down = Qt.MouseButton.NoButton if event_type is QEvent.Type.MouseButtonRelease else button
    changed = Qt.MouseButton.NoButton if event_type is QEvent.Type.MouseMove else button
    view = pet.viewport()
    event = QMouseEvent(event_type, QPointF(view.mapFromGlobal(position)), QPointF(position),
                        changed, down, Qt.KeyboardModifier.NoModifier)
    event.setTimestamp(round(clock[0] * 1000))
    QApplication.sendEvent(view, event)


def drag(companion, *, fast=True, dy=-8):
    pet, clock = companion
    cursor = pet._center().toPoint()
    point_event(pet, clock, QEvent.Type.MouseButtonPress, cursor)
    for _ in range(5):
        cursor += QPoint(18 if fast else 4, dy if fast else 0)
        point_event(pet, clock, QEvent.Type.MouseMove, cursor, 0.016 if fast else 0.04)
    point_event(pet, clock, QEvent.Type.MouseButtonRelease, cursor, 0.003)
    return pet


def tick(companion, steps=1):
    pet, clock = companion
    for _ in range(steps):
        clock[0] += 0.016
        if pet._timer.isActive():
            pet._step()


def test_slow_drop_keeps_original_settle_and_disabled_setting_prevents_fast_throw(companion):
    pet, _ = companion
    drag(companion, fast=False)
    assert not pet._dragging and not pet._puppet._held
    assert pet._throw is None and pet._puppet._throw_pose is None
    assert pet._puppet._carry_animation.duration() == 330
    pet._preferences = Preferences(throwing=False)
    drag(companion)
    assert pet._throw is None and not pet._timer.isActive()


def test_fast_throw_with_recovery_restarts_autonomous_roaming(companion):
    pet, _ = companion
    pet._toggle_pause()
    drag(companion)
    flight = pet._throw
    assert flight is not None and pet._timer.isActive()
    assert not pet._behavior_timer.isActive()
    assert flight.vx > 0 > flight.vy
    start = pet.pos()
    tick(companion, 6)
    assert pet.x() > start.x() and pet.y() < start.y()
    impact_seen = False
    recovered = False
    for _ in range(180):
        tick(companion)
        if pet._throw is None:
            recovered = True
            break
        impact_seen |= pet._puppet._throw_pose.compression > 0
    assert impact_seen and recovered
    assert pet._behavior.activity is Activity.WANDERING and pet._behavior_timer.isActive()
    landed = pet.pos()
    tick(companion, 16)
    assert pet.x() != landed.x()
    assert pet.y() == landed.y()


@pytest.mark.parametrize("interrupt", ["grab", "sleep", "fullscreen"])
def test_throw_interruptions_release_movement_ownership(companion, interrupt):
    pet, clock = companion
    drag(companion)
    start = pet.pos()
    if interrupt == "grab":
        cursor = pet._center().toPoint()
        point_event(pet, clock, QEvent.Type.MouseButtonPress, cursor)
        assert pet._press is not None
    elif interrupt == "sleep":
        pet._toggle_rest()
        assert pet._behavior.activity is Activity.SLEEPING
    else:
        bounds = WindowBounds(0, 0, 800, 600)
        pet.set_foreground(ForegroundWindow((1, 2), bounds, bounds, True, False))
        assert pet.fullscreen_suppressed and not pet.isVisible()
    assert pet._throw is None and pet._puppet._throw_pose is None
    assert not pet._timer.isActive()
    tick(companion, 20)
    assert pet.pos() == start
    if interrupt == "fullscreen":
        pet.set_foreground(None)
        assert pet.isVisible() and pet._throw is None


@pytest.mark.parametrize("route", ["desktop", "window"])
def test_throw_detaches_climbing_and_ignores_window_collisions(companion, route):
    pet, _ = companion
    screen = pet._current_screen()
    if route == "desktop":
        track = pet._desktop_track(screen, -1)
        assert track is not None
        pet._desktop_route = DesktopRoute(track, track.wall_length / 2)
        pet._desktop_screen = screen
        pose = pet._desktop_route.pose()
        pet._paint_desktop_pose(pose, 1, 1, 0.016)
    else:
        bounds = QRectF(200, 130, 420, 400)
        pet._route = WindowRoute(bounds, Edge.SIDE, 150, -1)
    drag(companion)
    assert pet._throw is not None
    assert pet._route is None and pet._desktop_route is None and pet._puppet._desktop_contact is None
    pet._preview_edge(1)
    assert pet._desktop_route is None
    assert not pet._try_window(10)


def test_throw_preference_defaults_on_and_saves_from_settings(companion):
    pet, _ = companion
    assert pet._preferences.throwing
    pet._open_settings()
    dialog = pet._settings_dialog
    assert isinstance(dialog, SettingsDialog) and dialog._throwing.isChecked()
    dialog._throwing.setChecked(False)
    dialog.accept()
    assert not pet._preferences.throwing
    reopened = QSettings(pet._store.fileName(), QSettings.Format.IniFormat)
    assert not Preferences.load(reopened).throwing


@pytest.mark.parametrize(("size", "birdseye"), [(70, False), (150, False), (150, True)])
def test_painted_throw_stays_inside_work_area(companion, size, birdseye):
    pet, _ = companion
    pet._preferences = Preferences(size=size, birdseye=birdseye, finish="safety-ochre")
    pet._resize_pet()
    pet._puppet.set_birdseye(birdseye)
    pet._puppet.set_finish("safety-ochre")
    screen = pet._current_screen()
    area = screen.availableGeometry()
    pet._place(QPoint(area.x() + area.width() - pet.width() - 10, area.y() + 15), screen)
    assert pet._start_throw(1550, -350)
    pet._sync_timers()
    for _ in range(240):
        tick(companion)
        frame = QImage(pet.width(), pet.height(), QImage.Format.Format_ARGB32_Premultiplied)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pet.scene().render(painter)
        painter.end()
        left = pet.x()
        top = pet.y()
        first = max(area.y() + area.height() - top, 0)
        for y in range(first, frame.height()):
            assert not any(frame.pixelColor(x, y).alpha() > 32 for x in range(frame.width()))
        first = max(area.x() + area.width() - left, 0)
        for x in range(first, frame.width()):
            assert not any(frame.pixelColor(x, y).alpha() > 32 for y in range(frame.height()))
        if pet._throw is None:
            break
    assert pet._throw is None


def test_a_returning_grab_can_follow_the_cursor_at_the_landing_height(companion):
    pet, clock = companion
    drag(companion, dy=14)
    for _ in range(180):
        if pet._throw is not None and pet._throw.recovery is not None:
            break
        tick(companion)
    else:
        pytest.fail("Throw did not land")
    cursor = pet._center().toPoint()
    y = pet.y()
    point_event(pet, clock, QEvent.Type.MouseButtonPress, cursor)
    cursor += QPoint(-20, 0)
    point_event(pet, clock, QEvent.Type.MouseMove, cursor, 0.12)
    assert pet._dragging and pet._throw is None and pet.y() == y
    point_event(pet, clock, QEvent.Type.MouseButtonRelease, cursor, 0.12)
    assert pet._throw is None and pet.y() == y


def test_resize_projects_flight_and_recovery_into_new_work_area():
    motion = ThrowMotion(780, 540, 900, 400, BOX)
    smaller = ThrowBounds(50, 70, 450, 380, 72, 425)
    motion.resize(smaller)
    assert (motion.x, motion.y) == (smaller.right, smaller.floor)
    motion.advance(0.04)
    assert motion.recovery is not None
    shifted = ThrowBounds(240, 110, 700, 400, 250, 680)
    old_x = motion.x
    motion.resize(shifted)
    assert (motion.x, motion.y) == (old_x, shifted.floor)
    for _ in range(24):
        if motion.advance(0.016):
            break
    else:
        pytest.fail("Resized throw did not recover")
    assert shifted.roam_left <= motion.x <= shifted.roam_right
