"""Geometry and Windows overlay integration for the physical-edge route."""

from time import perf_counter
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSettings, Qt
from PySide6.QtGui import QCursor, QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from arachnid.behavior import Activity
from arachnid.character import MechanicalPuppet
from arachnid.desktop_edges import DesktopEdge, DesktopRoute, DesktopTrack, SurfaceContact
from arachnid.navigation import Edge, WindowRoute
from arachnid.overlay import Overlay


PHYSICAL = QRectF(-120, 40, 1100, 780)
WORK = PHYSICAL.adjusted(0, 0, 0, -43)


@pytest.mark.parametrize("side", [-1, 1])
@pytest.mark.parametrize("scale", [0.7, 1, 1.5])
def test_climb_and_ceiling_track_is_continuous_and_stays_inside(side, scale):
    track = DesktopTrack.from_screen(PHYSICAL, WORK, side, scale)
    assert track is not None
    base = track.at(0)
    assert base.center.x() == pytest.approx(
        WORK.left() + track.contact if side < 0 else WORK.right() - track.contact)
    assert track.at(30).center.y() == base.center.y() - 30
    assert base.angle == -90 * side and base.facing == side
    end = track.at(track.length)
    assert end.center.y() == pytest.approx(base.center.y())
    assert end.center.x() != base.center.x()
    assert track.at(track.length - 30).center.y() == end.center.y() - 30

    boundaries = (track.wall_length, track.wall_length + track.turn_length,
                  track.wall_length + track.turn_length + track.ceiling_width,
                  track.length - track.wall_length)
    for distance in boundaries:
        before, after = track.at(distance - 0.001), track.at(distance + 0.001)
        assert (before.center - after.center).manhattanLength() < 0.003
        assert abs(before.angle - after.angle) < 0.01
    corner = track.at(track.wall_length + track.turn_length / 2)
    assert corner.edge is DesktopEdge.CORNER
    assert abs(corner.angle) == pytest.approx(135)
    ceiling = track.at(track.length / 2)
    assert ceiling.edge is DesktopEdge.CEILING and abs(ceiling.angle) == 180
    assert ceiling.center.y() == WORK.top() + track.contact
    for step in range(201):
        assert WORK.contains(track.at(track.length * step / 200).center)


def test_reverse_and_terminal_detachment_do_not_loop():
    track = DesktopTrack.from_screen(PHYSICAL, WORK, -1, 1)
    route = DesktopRoute(track, 160, direction=-1)
    initial = route.pose()
    route.advance(50)
    assert route.pose().facing == 1
    assert route.pose().center.y() == initial.center.y() + 50
    route.advance(500)
    assert route.distance == 0 and route.finished
    route.advance(500)
    assert route.distance == 0
    across = DesktopRoute(track, 10)
    across.advance(track.length * 2)
    assert across.finished and across.distance == track.length


def test_taskbars_block_only_occupied_physical_edges_and_small_screens_decline():
    left_bar = WORK.adjusted(55, 0, 0, 0)
    assert DesktopTrack.from_screen(PHYSICAL, left_bar, -1, 1) is None
    opposite_blocked = DesktopTrack.from_screen(PHYSICAL, left_bar, 1, 1)
    assert not opposite_blocked.through
    assert opposite_blocked.at(opposite_blocked.length).edge is DesktopEdge.CEILING
    top_bar = WORK.adjusted(0, 36, 0, 0)
    track = DesktopTrack.from_screen(PHYSICAL, top_bar, 1, 1)
    assert track.at(track.length).edge is DesktopEdge.SIDE
    route = DesktopRoute(track, 0)
    route.advance(track.length + 10)
    assert route.direction == -1
    assert not route.finished
    assert route.distance == track.length - 10
    route.advance(track.length)
    assert route.finished and route.distance == 0
    tiny = QRectF(0, 0, 210, 120)
    assert DesktopTrack.from_screen(tiny, tiny, -1, 1.5) is None


@pytest.mark.parametrize("angle,bounds", [
    (90, (-40, -120, 800, 700)),
    (270, (-800, -120, 40, 700)),
    (180, (-400, -40, 400, 700)),
])
def test_projection_keeps_stance_on_wall_and_swing_inward(angle, bounds):
    contact = SurfaceContact(*bounds, 1)
    _, project = contact.leg_projector(angle, 1)
    assert project((16, 43)) == pytest.approx((16, 40))
    assert project((16, 34)) == pytest.approx((16, 31))


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


def attach(pet, side):
    pet._preview_edge(side)
    screen = pet._current_screen()
    pet._step_desktop(screen, 15, 0.5)
    assert pet._desktop_route is not None
    assert pet._desktop_transfer is None
    return screen


@pytest.mark.parametrize("side", [-1, 1])
def test_overlay_approach_plants_feet_and_traversal_uses_gait(pet, side):
    pet._preview_edge(side)
    screen = pet._current_screen()
    x, angle = pet.x(), pet._puppet.angle
    pet._step_desktop(screen, 14, 0.2)
    assert pet.x() != x
    assert 0 < abs(pet._puppet.angle) < 90
    pet._step_desktop(screen, 14, 0.3)
    assert abs(pet._puppet.angle) == 90 and angle == 0
    assert pet._puppet._desktop_contact.strength == 1
    y, phase = pet.y(), pet._puppet.phase
    pet._step_desktop(screen, 19, 0.2)
    assert pet.y() < y and pet._puppet.phase != phase
    pet._reverse_desktop()
    pet._step_desktop(screen, 8, 0.1)
    assert pet.y() > y - 19
    pet._detach_desktop()
    pet._step_desktop(screen, 15, 0.5)
    assert pet._desktop_route is None and pet._puppet.angle == 0
    assert screen.availableGeometry().contains(pet.frameGeometry())


def test_desktop_attachment_is_rare_and_never_steals_window_route(pet):
    screen = pet._current_screen()
    work = screen.availableGeometry()
    pet._place(QPoint(work.x() + work.width() - pet.width() - 3, work.center().y()), screen)
    pet._last_tick = perf_counter() - 0.03
    pet._step()
    assert pet._desktop_route is None
    pet._desktop_cooldown = 0
    pet._velocity = 110
    pet._last_tick = perf_counter() - 0.03
    pet._step()
    assert pet._desktop_route is not None and pet._route is None
    assert not pet._try_window(500)
    pet._discard_desktop(screen)
    pet._route = WindowRoute(QRectF(300, 300, 480, 280), Edge.TOP, 140, -1)
    window = pet._route
    assert pet._desktop_track(screen, -1) is None
    pet._preview_edge(-1)
    assert pet._route is window
    pet._route = None


def test_drag_cancels_desktop_route_and_returns_inside_work_area(pet):
    screen = attach(pet, -1)
    view = pet.viewport()
    center = view.rect().center()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=center)
    moved = center + QPoint(125, 18)
    QApplication.sendEvent(view, QMouseEvent(
        QEvent.Type.MouseMove, QPointF(moved), QPointF(view.mapToGlobal(moved)),
        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    ))
    assert pet._dragging
    assert pet._desktop_route is None and pet._puppet._desktop_contact is None
    assert pet._puppet.angle == 0
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=moved)
    assert screen.availableGeometry().contains(pet.frameGeometry())


def test_sleep_fullscreen_and_geometry_changes_preserve_or_clear_attachment(pet, monkeypatch):
    screen = attach(pet, 1)
    pet._toggle_pause()
    pet._toggle_rest()
    center = pet.pos()
    angle = pet._puppet.angle
    assert pet._behavior.activity is Activity.SLEEPING and not pet._timer.isActive()
    assert pet._desktop_route is not None
    pet._toggle_rest()
    assert pet._timer.isActive() and (pet.pos(), pet._puppet.angle) == (center, angle)
    pet.set_foreground(SimpleNamespace(fullscreen=True))
    assert not pet.isVisible() and not pet._timer.isActive()
    pet.set_foreground(None)
    assert pet.isVisible() and pet._desktop_route is not None
    monkeypatch.setattr(pet, "_screen_key", lambda display: ("changed geometry or DPI",))
    pet._keep_visible()
    assert pet._desktop_route is None and pet._puppet.angle == 0
    assert screen.availableGeometry().contains(pet.frameGeometry())


@pytest.mark.parametrize("finish", ("graphite", "neon"))
@pytest.mark.parametrize("scale", (0.7, 1.0, 1.5))
def test_art_stays_inside_physical_boundaries_at_both_corners(pet, finish, scale):
    track = DesktopTrack.from_screen(PHYSICAL, WORK, -1, scale)
    rig = MechanicalPuppet(finish)
    image = QImage(176, 176, QImage.Format.Format_ARGB32)
    corners = (track.wall_length, track.length - track.wall_length - track.turn_length)
    samples = [0, track.length / 2, track.length]
    for corner in corners:
        samples.extend(corner + track.turn_length * step / 8 for step in range(9))
    for direction in (-1, 1):
        for distance in samples:
            pose = track.at(distance, direction)
            rig.set_desktop_contact(SurfaceContact.from_area(WORK, pose.center, scale))
            rig.walk(7, pose.facing, pose.angle)
            rig._turning.stop()
            rig._set_turn_progress(1)
            image.fill(0)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(88, 88)
            rig.paint(painter, None)
            painter.end()
            visible = QRectF(
                88 + (WORK.left() - pose.center.x()) / scale,
                88 + (WORK.top() - pose.center.y()) / scale,
                WORK.width() / scale, WORK.height() / scale,
            )
            pixels = image.constBits()
            stride = image.bytesPerLine()
            left, right = max(0, round(visible.left())), min(176, round(visible.right()))
            top, bottom = max(0, round(visible.top())), min(176, round(visible.bottom()))
            for row in range(176):
                alpha = pixels[row * stride + 3 : (row + 1) * stride : 4].tobytes()
                outside = alpha if not top <= row < bottom else alpha[:left] + alpha[right:]
                assert max(outside, default=0) <= 32, (distance, direction, pose.angle)
