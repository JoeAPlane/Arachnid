from math import isclose
import sys

import pytest
from PySide6.QtCore import QPointF, QRectF

from arachnid.navigation import CORNER_LENGTH, FOOT_CONTACT, Edge, WindowRoute

SURFACE = QRectF(400, 300, 440, 360)
ALLOWED = QRectF(88, 88, 1300, 700)


def test_top_route_follows_move_and_resize_and_turns_inside_top():
    route = WindowRoute.near(SURFACE, ALLOWED, QPointF(600, 260), facing=1)
    assert route.edge is Edge.TOP
    assert route.pose().center == QPointF(600, 257)
    assert route.follow(QRectF(420, 310, 250, 360), ALLOWED)
    assert route.pose().center == QPointF(598, 267)
    route.advance(12)
    assert route.pose().facing == -1
    assert route.pose().center.x() == 586
    assert not route.follow(QRectF(420, 15, 250, 360), ALLOWED)


@pytest.mark.parametrize("side", [-1, 1])
def test_side_climb_turns_onto_top_with_continuous_foot_contact(side):
    wall = SURFACE.left() if side < 0 else SURFACE.right()
    contact = wall + side * FOOT_CONTACT
    route = WindowRoute.near(SURFACE, ALLOWED, QPointF(contact + side * 2, 450),
                             facing=-side, travel=4)
    assert route.edge is Edge.SIDE
    assert route.pose().angle == side * 90
    route.advance(150)
    assert route.edge is Edge.CORNER
    assert route.pose().center == QPointF(contact, 300)
    route.advance(CORNER_LENGTH / 2)
    pose = route.pose()
    assert pose.angle == side * 45
    assert isclose((pose.center - QPointF(wall, 300)).manhattanLength(), 2**0.5 * FOOT_CONTACT)
    route.advance(CORNER_LENGTH / 2 + 10)
    assert route.edge is Edge.TOP
    assert route.pose().center == QPointF(wall - side * 10, 257)
    assert route.pose().facing == -side


def test_ineligible_side_and_window_leave_no_route():
    assert WindowRoute.near(SURFACE, ALLOWED, QPointF(355, 450), facing=-1, travel=4) is None
    assert WindowRoute.near(QRectF(400, 300, 125, 300), ALLOWED, QPointF(470, 257), 1) is None
    route = WindowRoute.near(SURFACE, ALLOWED, QPointF(357, 450), 1)
    assert not route.follow(QRectF(400, 300, 440, 85), ALLOWED)


@pytest.mark.parametrize("side", [-1, 1])
def test_lower_wall_to_underside_keeps_the_corner_within_reach(side):
    wall = SURFACE.left() if side < 0 else SURFACE.right()
    start = QPointF(wall + side * FOOT_CONTACT, SURFACE.bottom() - 60)
    route = WindowRoute.near(SURFACE, ALLOWED, start, -side)
    assert route.pose().facing == side
    route.advance(60)
    assert route.edge is Edge.CORNER
    corner = QPointF(wall, SURFACE.bottom())
    for fraction in range(1, 8):
        route.advance(CORNER_LENGTH / 8)
        pose = route.pose()
        assert pose.angle == pytest.approx(side * (90 + 90 * fraction / 8))
        offset = pose.center - corner
        assert QPointF.dotProduct(offset, offset) == pytest.approx(FOOT_CONTACT**2)
    route.advance(CORNER_LENGTH / 8 + 12)
    assert route.edge is Edge.BOTTOM and route.pose().facing == side
    assert route.pose().center == QPointF(wall - side * 12, SURFACE.bottom() + FOOT_CONTACT)
    # The same drop climbs when there is room only above the window.
    fallback = WindowRoute.near(SURFACE, QRectF(88, 88, 1300, 600), start, -side)
    fallback.advance(10)
    assert fallback.pose().center == start - QPointF(0, 10)
    assert WindowRoute.near(SURFACE, QRectF(700, 100, -300, 500), QPointF(600, 257), 1) is None


def test_underside_walk_moves_in_screen_direction_and_follows_bottom_edge():
    route = WindowRoute.near(SURFACE, ALLOWED, QPointF(600, 703), facing=1)
    assert route is not None and route.edge is Edge.BOTTOM
    assert route.pose().angle == 180 and route.pose().facing == -1
    route.advance(30)
    assert route.pose().center == QPointF(630, 703)
    route.reverse()
    route.advance(10)
    assert route.pose().center == QPointF(620, 703)
    assert route.pose().facing == 1
    assert route.follow(QRectF(420, 300, 440, 380), ALLOWED)
    assert route.pose().center == QPointF(640, 723)
    assert not route.follow(QRectF(420, 300, 440, 500), ALLOWED)


def test_window_route_uses_scaled_foot_contact():
    contact = FOOT_CONTACT * 1.5
    route = WindowRoute.near(SURFACE, ALLOWED, QPointF(600, SURFACE.top() - contact), 1, scale=1.5)
    assert route.pose().center.y() == pytest.approx(SURFACE.top() - contact)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows geometry")
def test_fullscreen_uses_physical_monitor_bounds_with_negative_origin():
    from arachnid.windows import WindowBounds, covers_monitor

    monitor = WindowBounds(-1920, 0, 0, 1080)
    assert covers_monitor(WindowBounds(-1919, 1, -1, 1079), monitor)
    assert not covers_monitor(WindowBounds(-1920, 0, 0, 1039), monitor)
    assert not covers_monitor(WindowBounds(0, 0, 1920, 1080), monitor)
