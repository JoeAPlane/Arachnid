"""An inside route around the active screen's unobstructed physical edges."""

from dataclasses import dataclass
from enum import Enum, auto
from math import cos, pi, radians, sin

from PySide6.QtCore import QPointF, QRectF

from .navigation import FOOT_CONTACT

TURN_RADIUS = 28
BODY_CLEARANCE = 76
ATTACH_TIME = 0.45


class DesktopEdge(Enum):
    SIDE = auto()
    CORNER = auto()
    CEILING = auto()


def smooth(progress: float) -> float:
    progress = max(0, min(progress, 1))
    return progress * progress * (3 - 2 * progress)


@dataclass(frozen=True)
class DesktopPose:
    center: QPointF
    angle: float
    facing: int
    edge: DesktopEdge


@dataclass(frozen=True)
class DesktopTrack:
    area: QRectF
    side: int
    contact: float
    radius: float
    bottom: float
    high: float
    ceiling_width: float
    through: bool

    @classmethod
    def from_screen(cls, physical: QRectF, work: QRectF, side: int, scale: float) -> "DesktopTrack | None":
        area = physical.intersected(work)
        contact = FOOT_CONTACT * scale
        radius = TURN_RADIUS * scale
        clearance = BODY_CLEARANCE * scale
        if side not in (-1, 1) or not area.isValid() or scale <= 0:
            return None
        if area.width() < 2 * clearance + 16 * scale:
            return None
        if cls._wall(area, side) != cls._wall(physical, side):
            return None
        other_open = cls._wall(area, -side) == cls._wall(physical, -side)
        top_open = area.top() == physical.top()
        high = area.top() + (max(contact + radius, clearance) if not top_open else contact + radius)
        bottom = area.bottom() - clearance
        ceiling_width = area.width() - 2 * (contact + radius) if top_open else 0.0
        if top_open and not other_open:
            ceiling_width -= max(0.0, clearance - contact - radius)
        if bottom - high < 24 * scale:
            return None
        return cls(area, side, contact, radius, bottom, high, ceiling_width,
                   top_open and other_open)

    @staticmethod
    def _wall(rect: QRectF, side: int) -> float:
        return rect.left() if side < 0 else rect.right()

    @property
    def wall_length(self) -> float:
        return self.bottom - self.high

    @property
    def turn_length(self) -> float:
        return pi * self.radius / 2

    @property
    def length(self) -> float:
        if not self.ceiling_width:
            return self.wall_length
        top = self.wall_length + self.turn_length + self.ceiling_width
        return top + self.turn_length + self.wall_length if self.through else top

    def at(self, distance: float, direction: int = 1) -> DesktopPose:
        d = min(self.length, max(0, distance))
        edge = DesktopEdge.SIDE
        first_turn_end = self.wall_length + self.turn_length
        ceiling_end = first_turn_end + self.ceiling_width
        second_turn_end = ceiling_end + self.turn_length
        if d <= self.wall_length:
            x, y, angle = self.contact, self.bottom - d, 90
        elif d < first_turn_end:
            phase = (d - self.wall_length) / self.radius
            x = self.contact + self.radius * (1 - cos(phase))
            y = self.high - self.radius * sin(phase)
            angle = 90 + 90 * smooth(phase / (pi / 2))
            edge = DesktopEdge.CORNER
        elif d <= ceiling_end:
            x = self.contact + self.radius + (d - first_turn_end)
            y = self.high - self.radius
            angle = 180
            edge = DesktopEdge.CEILING
        elif d < second_turn_end:
            phase = (d - ceiling_end) / self.radius
            x = self.area.width() - self.contact - self.radius * (1 - sin(phase))
            y = self.high - self.radius * cos(phase)
            angle = 180 + 90 * smooth(phase / (pi / 2))
            edge = DesktopEdge.CORNER
        else:
            x = self.area.width() - self.contact
            y = min(self.bottom, self.high + (d - second_turn_end))
            angle = 270
        center = QPointF(self._wall(self.area, self.side) - self.side * x, y)
        return DesktopPose(center, -self.side * angle, self.side * direction, edge)

    def attach_at(self, center: QPointF) -> float:
        return min(self.wall_length, max(0.0, self.bottom - center.y()))


@dataclass
class DesktopRoute:
    track: DesktopTrack
    distance: float
    direction: int = 1
    finished: bool = False

    def advance(self, distance: float) -> None:
        if self.finished or distance <= 0:
            return
        self.distance += self.direction * distance
        if self.distance <= 0:
            self.distance = 0
            self.finished = True
        elif self.distance >= self.track.length:
            if self.track.through:
                self.distance = self.track.length
                self.finished = True
            else:
                # Retrace an obstructed route once, then detach at its base.
                self.distance = max(0.0, 2 * self.track.length - self.distance)
                self.direction = -1
                self.finished = self.distance == 0

    def pose(self) -> DesktopPose:
        return self.track.at(self.distance, self.direction)


@dataclass(frozen=True)
class SurfaceContact:
    """Work-area bounds measured from the painted pivot, in rig coordinates."""

    left: float
    top: float
    right: float
    bottom: float
    strength: float

    @classmethod
    def from_area(cls, area: QRectF, center: QPointF, scale: float,
                  strength: float = 1.0) -> "SurfaceContact":
        # Leave room for the rounded end caps on the foot links.
        padding = 5.0
        return cls((area.left() - center.x()) / scale + padding,
                   (area.top() - center.y()) / scale + padding,
                   (area.right() - center.x()) / scale - padding,
                   (area.bottom() - center.y()) / scale - padding, strength)

    def leg_projector(self, angle: float, width: float):
        """Keep link endpoints inside the work area and project planted feet."""
        c, s = cos(radians(angle)), sin(radians(angle))

        def to_world(x, y):
            return c * x * width - s * y, s * x * width + c * y

        def to_local(x, y):
            return (c * x + s * y) / width, -s * x + c * y

        def inside(point, inset=0.0):
            x, y = to_world(*point)
            return to_local(max(self.left + inset, min(x, self.right - inset)),
                            max(self.top + inset, min(y, self.bottom - inset)))

        def planted(foot):
            x, y = to_world(foot[0], 0)
            # Take the first physical surface along the leg's down axis.
            tx = ((self.left if s > 0 else self.right) - x) / -s if abs(s) > 1e-6 else float("inf")
            ty = ((self.bottom if c > 0 else self.top) - y) / c if abs(c) > 1e-6 else float("inf")
            floor = min(60.0, max(18.0, min(tx, ty)))
            depth = foot[1] + (floor - FOOT_CONTACT) * self.strength
            return inside((foot[0], depth))

        return inside, planted
