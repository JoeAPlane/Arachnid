from math import ceil
from time import perf_counter

import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, QSettings
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

from arachnid.behavior import Activity, Behavior
from arachnid.gait import CYCLE_DISTANCE, foot_at, knee_at
from arachnid.movement import angle_delta, ramp_speed
from arachnid.navigation import Edge, WindowRoute
from arachnid.overlay import Overlay


@pytest.fixture
def pet(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QCursor, "pos", lambda: QPoint(-10000, -10000))
    store = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    overlay = Overlay(110, True, store, desktop_preview=True)
    overlay.show()
    app.processEvents()
    try:
        yield overlay
    finally:
        overlay.close()
        app.processEvents()


def test_ramp_integrates_a_partial_frame_and_angle_uses_short_path():
    assert ramp_speed(0.8, 1, 0.2, 0.5) == pytest.approx((1.0, 0.19))
    assert ramp_speed(0.6, 0, 0.2, 0.1) == pytest.approx((0.0, 0.018))
    assert angle_delta(270, 0) == 90
    assert angle_delta(-179, 179) == -2


@pytest.mark.parametrize("scale", (0.7, 1.0, 1.5))
def test_stance_cancels_world_travel_at_each_scale(scale):
    travel = 3.0
    before = foot_at(0.2, 20, 41, 1)
    after = foot_at(0.2 + travel / (scale * CYCLE_DISTANCE), 20, 41, 1)
    assert after[1] == before[1]
    assert (after[0] - before[0]) * scale == pytest.approx(-travel)
    assert knee_at((2, 4), (2, 4), 20, 20, 1) == (2, -16)


def test_planting_keeps_stride_and_phase_when_a_swung_foot_settles(pet):
    rig = pet._puppet
    rig.walk(CYCLE_DISTANCE * 0.8, 1)
    phase = rig.phase
    before = foot_at(phase, 20, 41, rig.blend, stride=rig._stride_blend)
    rig.stand()
    rig._settling.setCurrentTime(rig._settling.duration())
    after = foot_at(rig.phase, 20, 41, rig.blend, stride=rig._stride_blend)
    assert rig.phase == phase
    assert after[0] == before[0] and before[1] < after[1] == 41
    rig.walk(3, 1)
    assert rig.phase == pytest.approx((phase + 3 / CYCLE_DISTANCE) % 1)


def test_tail_follows_turn_and_eases_to_rest(pet):
    rig = pet._puppet
    rig.walk(2, 1, 0)
    for angle in range(5, 55, 5):
        rig.walk(2, 1, angle)
    assert -0.18 < rig._tail_lag < 0
    previous = rig._tail_lag
    rig.stand()
    assert rig._tail_lag == previous
    rig._tail_settling.setCurrentTime(130)
    assert previous < rig._tail_lag < 0
    rig._tail_settling.setCurrentTime(260)
    assert rig._tail_lag == 0


def test_idle_motion_is_infrequent_finite_and_releases_on_resume(pet):
    behavior = Behavior()
    assert not behavior.idle_shift_ready(20)
    behavior.activity = Activity.OBSERVING
    assert not behavior.idle_shift_ready(1, stationary=False)
    assert behavior.idle_shift_ready(0.1)
    assert not behavior.idle_shift_ready(10)
    behavior.sleep()
    assert not behavior.idle_shift_ready(30)
    rig = pet._puppet
    rig.idle_shift()
    rig._idle.setCurrentTime(450)
    assert 0 < rig._idle_amount <= 1
    rig.walk(2, 1)
    rig._idle.setCurrentTime(115)
    assert rig._idle_amount == pytest.approx(0)
    assert rig._idle.loopCount() == 1


def test_observation_coasts_briefly_but_manual_pause_stops_immediately(pet):
    screen = pet._current_screen()
    work = screen.availableGeometry()
    pet._place(QPoint(work.x() + 140, work.y() + 140), screen)
    pet._toggle_pause()
    pet._speed_scale = 1.0
    pet._behavior.activity = Activity.OBSERVING
    pet._sync_timers()
    start = pet._x
    assert pet._braking and pet._timer.isActive()
    for _ in range(14):
        pet._last_tick = perf_counter() - 0.016
        pet._step()
    assert 2 < pet._x - start < 10
    assert not pet._timer.isActive()
    pet._behavior.wake()
    pet._sync_timers()
    pet._speed_scale = 0.8
    pet._toggle_pause()
    assert not pet._braking and not pet._timer.isActive() and pet._speed_scale == 0


def test_window_mount_and_interrupted_rotation_retarget_from_current_pose(pet, monkeypatch):
    screen = pet._current_screen()
    area = screen.availableGeometry()
    bounds = QRectF(area.x() + 300, area.y() + 220, 350, 240)
    monkeypatch.setattr(pet, "_surface", lambda current: bounds)
    pet._place(QPoint(round(bounds.left() - 43 - pet.width()/2),
                      round(bounds.top() + 50 - pet.height()/2)), screen)
    assert pet._try_window()
    assert pet._route.edge is Edge.SIDE and pet._puppet.angle == 0
    pet._window_mount.setCurrentTime(85)
    before = pet._puppet.angle
    assert -90 < before < 0
    pet._leave_window()
    assert pet._puppet.angle == pytest.approx(before)
    pet._puppet._level.setCurrentTime(100)
    assert before < pet._puppet.angle < 0
    pet._puppet._level.setCurrentTime(190)
    assert pet._puppet.angle == 0 and pet._route is None


def test_repeated_arch_traversal_and_midclimb_reversal_recover_upright(pet):
    screen = pet._current_screen()
    for side in (-1, 1, -1, 1):
        pet._preview_edge(side)
        pet._step_desktop(screen, 12, 0.5)
        route = pet._desktop_route
        assert route is not None
        route.distance = route.track.wall_length * 0.75
        pet._speed_scale = .72
        pet._reverse_desktop()
        for _ in range(16):
            pet._last_tick = perf_counter() - 0.016
            pet._step()
        assert route.direction == -1 and not pet._desktop_reverse_pending
        pet._reverse_desktop()
        for _ in range(16):
            pet._last_tick = perf_counter() - 0.016
            pet._step()
        assert route.direction == 1
        for _ in range(ceil(route.track.length / 45) + 6):
            pet._step_desktop(screen, 45, 0.1)
            if pet._desktop_route is None:
                break
        assert pet._desktop_route is None and pet._puppet.angle == 0
        assert screen.availableGeometry().contains(pet.frameGeometry())


def test_sleep_and_quick_wake_blend_optics_from_the_current_posture(pet):
    rig = pet._puppet
    pet._toggle_rest()
    assert rig._optic_opening() == 1
    rig._posture_transition.setCurrentTime(130)
    opening = rig._optic_opening()
    assert 0 < opening < 1
    pet._toggle_rest()
    assert rig._optic_opening() == opening
    rig._posture_transition.setCurrentTime(220)
    assert rig._optic_opening() == 1
    pet._toggle_rest()
    rig._posture_transition.setCurrentTime(220)
    assert rig._optic_opening() == 0 and rig._rest_shade() == 1
