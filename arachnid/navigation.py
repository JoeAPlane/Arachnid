"""Routes along a single window's edges in Qt logical pixels."""

from dataclasses import dataclass
from enum import Enum, auto
from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF

from .movement import advance

FOOT_CONTACT = 43
TOP_MARGIN = 72
SNAP_DISTANCE = 18
CORNER_LENGTH = pi * FOOT_CONTACT / 2


class Edge(Enum):
    SIDE = auto()
    CORNER = auto()
    TOP = auto()
    BOTTOM = auto()


@dataclass(frozen=True)
class EdgePose:
    center: QPointF
    angle: float
    facing: int


class WindowRoute:
    def __init__(self, bounds: QRectF, edge: Edge, offset: float, side: int, scale: float = 1.0) -> None:
        self.bounds = bounds
        self.edge = edge
        self.offset = offset
        self.side = side
        self.facing = -side
        self.descending = False
        self.contact = FOOT_CONTACT * scale
        self.margin = TOP_MARGIN * scale
        self.corner_length = CORNER_LENGTH * scale

    @classmethod
    def near(
        cls, bounds: QRectF, allowed: QRectF, center: QPointF, facing: int,
        travel: float = 0, *, scale: float = 1.0,
    ) -> "WindowRoute | None":
        """Find a surface touched by a drop or the next horizontal step."""
        contact_distance = FOOT_CONTACT * scale
        margin = TOP_MARGIN * scale
        snap = SNAP_DISTANCE * scale
        if bounds.width() < 2 * margin + 8:
            return None
        x = center.x() - bounds.left()
        y = center.y() - bounds.top()
        if margin <= x <= bounds.width() - margin:
            for edge, height in ((Edge.TOP, bounds.top() - contact_distance),
                                 (Edge.BOTTOM, bounds.bottom() + contact_distance)):
                if abs(center.y() - height) <= snap:
                    route = cls(bounds, edge, x, -facing, scale)
                    return route if route.fits(allowed) else None
        if not 0 <= y <= bounds.height():
            return None

        for side, wall in ((-1, bounds.left()), (1, bounds.right())):
            contact = wall + side * contact_distance
            if travel:
                near = facing == -side and 0 <= (contact - center.x()) * facing <= travel
            else:
                near = abs(center.x() - contact) <= snap
            if near:
                route = cls(bounds, Edge.SIDE, y, side, scale)
                if y > bounds.height() / 2:
                    route.descending = True
                    if route.fits(allowed):
                        return route
                    route.descending = False
                if y <= bounds.height() - contact_distance and route.fits(allowed):
                    return route
        return None

    def fits(self, allowed: QRectF) -> bool:
        """Keep the overlay and its intended turn inside the current work area."""
        edge_y = self._horizontal_height()
        if not allowed.isValid() or self.bounds.width() < 2 * self.margin + 8:
            return False
        if not all(allowed.contains(point) for point in (
            self.pose().center,
            QPointF(self.bounds.left() + self.margin, edge_y),
            QPointF(self.bounds.right() - self.margin, edge_y),
        )):
            return False
        if self.edge in (Edge.TOP, Edge.BOTTOM):
            return True
        wall = self.bounds.left() if self.side < 0 else self.bounds.right()
        return allowed.contains(QPointF(wall + self.side * self.contact, edge_y))

    def _horizontal_height(self) -> float:
        if self.edge is Edge.BOTTOM or self.descending:
            return self.bounds.bottom() + self.contact
        return self.bounds.top() - self.contact

    def follow(self, bounds: QRectF, allowed: QRectF) -> bool:
        old_width = self.bounds.width()
        self.bounds = bounds
        if self.edge is Edge.SIDE and self.offset > bounds.height():
            return False
        if self.edge in (Edge.TOP, Edge.BOTTOM):
            if self.offset > old_width - self.margin:
                self.offset = max(0, self.offset + bounds.width() - old_width)
            else:
                self.offset = min(self.offset, bounds.width() - self.margin)
        return self.fits(allowed)

    def reverse(self) -> None:
        if self.edge in (Edge.TOP, Edge.BOTTOM):
            self.facing *= -1

    def advance(self, distance: float) -> None:
        if self.edge is Edge.SIDE:
            to_corner = self.bounds.height() - self.offset if self.descending else self.offset
            if distance < to_corner:
                self.offset += distance if self.descending else -distance
                return
            distance -= to_corner
            self.edge = Edge.CORNER
            self.offset = 0.0

        if self.edge is Edge.CORNER:
            if distance < self.corner_length - self.offset:
                self.offset += distance
                return
            distance -= self.corner_length - self.offset
            self.edge = Edge.BOTTOM if self.descending else Edge.TOP
            self.offset = 0.0 if self.side < 0 else self.bounds.width()

        left, right = self.margin, self.bounds.width() - self.margin
        if self.offset < left:
            step = min(distance, left - self.offset)
            self.offset += step
            distance -= step
            self.facing = 1
        elif self.offset > right:
            step = min(distance, self.offset - right)
            self.offset -= step
            distance -= step
            self.facing = -1
        if distance > 0:
            self.offset, velocity = advance(self.offset, self.facing, distance, left, right)
            self.facing = int(velocity)

    def pose(self) -> EdgePose:
        left, top = self.bounds.left(), self.bounds.top()
        if self.edge is Edge.TOP:
            return EdgePose(QPointF(left + self.offset, top - self.contact), 0, self.facing)
        if self.edge is Edge.BOTTOM:
            return EdgePose(QPointF(left + self.offset, self._horizontal_height()), 180, -self.facing)

        wall = left if self.side < 0 else self.bounds.right()
        if self.edge is Edge.SIDE:
            center = QPointF(wall + self.side * self.contact, top + self.offset)
            return EdgePose(center, 90 * self.side, -self.facing if self.descending else self.facing)

        remaining = 1 - self.offset / self.corner_length
        if self.descending:
            radians = pi * remaining / 2
            center = QPointF(wall + self.side * self.contact * sin(radians),
                             self.bounds.bottom() + self.contact * cos(radians))
            return EdgePose(center, self.side * (180 - 90 * remaining), -self.facing)
        angle = self.side * 90 * remaining
        radians = self.side * pi / 2 * remaining
        center = QPointF(wall + self.contact * sin(radians), top - self.contact * cos(radians))
        return EdgePose(center, angle, self.facing)
