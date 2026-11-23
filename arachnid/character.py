"""Draw and animate the articulated ARACHNID character."""

from math import cos, pi, radians, sin

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPointF, QRectF, Qt, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QLinearGradient, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsObject

from .appearance import DEFAULT_FINISH, FINISHES
from .behavior import Activity
from .desktop_edges import SurfaceContact
from .gait import CYCLE_DISTANCE, foot_at, knee_at
from .navigation import FOOT_CONTACT

type Point = tuple[float, float]

_INK = QColor("#101820")
_FAR = QColor("#44596a")
_STEEL = QColor("#7893a2")
_LIGHT_STEEL = QColor("#a6c1c8")
_WHITE = QColor("#e8fbff")
_GUNMETAL = QColor("#263542")
_SEAM = QColor("#344654")
_LENS = QColor("#183141")
_SHADOW = QColor("#19232e")


def _polygon(*vertices: Point) -> QPainterPath:
    shape = QPainterPath(QPointF(*vertices[0]))
    for vertex in vertices[1:]:
        shape.lineTo(QPointF(*vertex))
    shape.closeSubpath()
    return shape


def _metal(top: str, bottom: str, y1: int, y2: int) -> QLinearGradient:
    gradient = QLinearGradient(0, y1, 0, y2)
    gradient.setColorAt(0, QColor(top))
    gradient.setColorAt(1, QColor(bottom))
    return gradient


_HULL = _polygon((-40, -5), (-30, -15), (-17, -20), (10, -20), (24, -15), (32, -7),
                 (29, 10), (15, 16), (-24, 15), (-38, 8))
_ARMOR = _polygon((-34, -7), (-26, -14), (-16, -17), (10, -17), (22, -12),
                  (25, -6), (15, 0), (-23, 4), (-32, 0))
_SIDE_PANEL = _polygon((-32, 5), (-22, 7), (14, 3), (21, 6), (13, 12), (-23, 13), (-32, 10))
_VISOR = _polygon((23, -7), (28, -14), (37, -14), (46, -6), (45, 4), (39, 10),
                  (30, 11), (24, 7))
_VISOR_BROW = _polygon((26, -8), (29, -12), (37, -12), (43, -7), (39, -7), (36, -10), (30, -10))
_TIP = _polygon((-3, -5), (5, -4), (9, 1), (5, 6), (-3, 4))
_HULL_METAL = _metal("#495e72", "#202c3c", -20, 16)
_SIDE_METAL = _metal("#4c6472", "#21313d", 4, 13)
_VISOR_METAL = _metal("#6b8490", "#203242", -14, 11)
_TOP_SHELL = _polygon((-40, -11), (-27, -22), (11, -23), (28, -16), (34, -10),
                      (34, 10), (28, 16), (11, 23), (-27, 22), (-40, 11))
_TOP_ARMOR = _polygon((-34, -10), (-24, -17), (12, -18), (25, -11), (25, 11),
                      (12, 18), (-24, 17), (-34, 10))
_TOP_VISOR = _polygon((26, -12), (40, -14), (48, -8), (48, 8), (40, 14), (26, 12))

_NEON_FRAME = QColor("#161820")
_NEON_EDGE = QColor("#62564a")
_NEON_WEAR = QColor("#fff39b")
_NEON_CABLE = QColor("#ff367b")
_NEON_HULL = _polygon((-43, -6), (-36, -16), (-20, -21), (11, -20), (19, -15),
                      (36, -16), (51, -8), (49, 8), (36, 14), (16, 12), (8, 17),
                      (-25, 16), (-39, 10))
_NEON_PLATE = _polygon((-37, -8), (-31, -15), (-20, -19), (9, -18), (20, -12),
                       (16, -5), (3, -3), (0, 1), (-26, 3), (-35, -1))
_NEON_TOP = _polygon((-43, -10), (-32, -21), (-11, -24), (17, -20), (24, -16),
                     (43, -17), (50, -10), (50, 10), (43, 17), (24, 16),
                     (10, 23), (-17, 24), (-35, 18), (-43, 10))
_NEON_TOP_PLATE = _polygon((-34, -10), (-26, -17), (-10, -20), (12, -17), (22, -10),
                           (17, -4), (21, 8), (11, 16), (-17, 20), (-31, 13), (-35, 3))
_NEON_LENS = _polygon((-14, -4), (-9, -7), (10, -7), (14, -3), (13, 4),
                      (10, 6), (-10, 6), (-14, 2))
_NEON_VISOR_SEGMENTS = (
    _polygon((-11, -1), (-8, -3), (-5, -3), (-6, 2), (-11, 2)),
    _polygon((-3, -3), (3, -3), (2, 2), (-4, 2)),
    _polygon((5, -3), (10, -3), (12, -1), (9, 2), (4, 2)),
)

# (hip, resting foot X, knee bend); each bank has rear, middle, and front legs.
_FAR_LEGS = (((-24, -1), -46, 1), ((-3, -1), -8, 1), ((20, -1), 43, -1))
_NEAR_LEGS = (((-23, 8), -56, 1), ((0, 11), -1, -1), ((21, 8), 54, -1))
_TAIL_LINKS = ((-13, -5), (-11, -11), (-3, -13), (7, -10), (10, -2))
_TOP_TAIL_LINKS = ((-10, 0), (-10, 0), (-9, 4), (-5, 7), (-1, 8))
_TOP_LEGS = ((-24, -48, 44, 1), (-2, -5, 53, 1), (21, 48, 44, -1))


def _line(painter, start: Point, end: Point, width: float, color: QColor) -> None:
    painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(*start), QPointF(*end))


def _disc(painter, center: Point, radius: float, fill: QColor) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(fill)
    painter.drawEllipse(QPointF(*center), radius, radius)


def _between(start: Point, end: Point, amount: float) -> Point:
    return (start[0] + (end[0] - start[0]) * amount, start[1] + (end[1] - start[1]) * amount)


def _happy_eye(painter, x: float, y: float, width: float, close: float, accent: QColor) -> None:
    painter.setPen(QPen(accent, 1.4 + (1 - close) * 2.4,
                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    eye = QPainterPath(QPointF(x - width, y + close))
    eye.quadTo(x, y - 4 * close, x + width, y + close)
    painter.drawPath(eye)


class MechanicalPuppet(QGraphicsObject):
    intro_finished = Signal()
    WIDTH = 176
    HEIGHT = 176

    def __init__(self, finish: str = DEFAULT_FINISH) -> None:
        super().__init__()
        self.facing = 1
        self.angle = 0.0
        self.phase = 0.0
        self.blend = 0.0
        self._hovered = False
        self._pet_progress = 1.0
        self._intro_progress = 1.0
        self._curled_sleep = False
        self._curl = 0.0
        self._activity = Activity.WANDERING
        self._waking = False
        self._gaze = (0, 0)
        self._posture = 0.0
        self._target_posture = 0.0
        self._turn_from = 1
        self._turn_progress = 1.0
        self._light_pulse = 0.0
        self._birdseye = False
        self._desktop_contact: SurfaceContact | None = None
        self._held = False
        self._carry_from = 0.0
        self._drag_tilt = 0.0
        self._carry_progress = 1.0
        self._settling = self._animation(160, self._set_blend)
        self._posture_transition = self._animation(220, self._set_posture)
        self._turning = self._animation(180, self._set_turn_progress)
        self._pulse = self._animation(300, self._set_light_pulse)
        self._intro = self._animation(2600, self._set_intro_progress)
        self._intro.setEasingCurve(QEasingCurve.Type.Linear)
        self._intro.setStartValue(0.0)
        self._intro.setEndValue(1.0)
        self._intro.finished.connect(self.intro_finished)
        self._petting = self._animation(1050, self._set_pet_progress)
        self._petting.setStartValue(0.0)
        self._petting.setEndValue(1.0)
        self._curl_animation = self._animation(520, self._set_curl)
        self._carry_animation = self._animation(700, self._set_carry_progress)
        self._carry_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._carry_animation.setStartValue(0.0)
        self._carry_animation.setEndValue(1.0)
        self._turning.setStartValue(0.0)
        self._turning.setEndValue(1.0)
        self._pulse.setStartValue(1.0)
        self._pulse.setEndValue(0.0)
        self._settling.setEndValue(0.0)
        self.finish_animations()
        self.set_finish(finish)
        self.setPos(self.WIDTH / 2, self.HEIGHT / 2)

    def _animation(self, duration, setter) -> QVariantAnimation:
        animation = QVariantAnimation(self)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        animation.valueChanged.connect(setter)
        return animation

    def _set_blend(self, value: float) -> None:
        self.blend = value
        if value == 0:
            self.phase = 0.0
        self.update()

    def _set_posture(self, value: float) -> None:
        self._posture = value
        self.update()

    def _set_turn_progress(self, value: float) -> None:
        self._turn_progress = value
        self.update()

    def _set_light_pulse(self, value: float) -> None:
        self._light_pulse = value
        self.update()

    def _set_carry_progress(self, value: float) -> None:
        self._carry_progress = value
        self.update()

    def set_held(self, held: bool) -> None:
        if self._held == held:
            return
        self._carry_from = self._suspension()
        self._held = held
        self._carry_animation.stop()
        self._carry_animation.setDuration(840 if held else 330)
        self._set_carry_progress(0.0)
        self._carry_animation.start()

    def _suspension(self) -> float:
        # The chassis sags first, then the legs start their short struggle.
        t = min(1.0, self._carry_progress * (4.5 if self._held else 2.3))
        return self._carry_from + (float(self._held) - self._carry_from) * t * t * (3 - 2 * t)

    def set_drag_lag(self, dx: float) -> None:
        self._drag_tilt = -dx * 0.32
        self.update()

    def set_desktop_contact(self, contact: SurfaceContact | None) -> None:
        if self._desktop_contact != contact:
            self._desktop_contact = contact
            self.update()

    def set_birdseye(self, enabled: bool) -> None:
        if self._birdseye != enabled:
            self._birdseye = enabled
            self.angle = 0.0
            self._turning.stop()
            self._set_turn_progress(1.0)

    def set_finish(self, finish: str) -> None:
        palette = FINISHES[finish]
        self._neon = finish == "neon"
        self._armor = _metal(*palette.armor, -17, 4)
        self._trim = QColor(palette.trim)
        self._links = QColor(palette.links)
        self._optic = QColor(palette.optic)
        self.update()

    def flash(self) -> None:
        self._pulse.stop()
        self._set_light_pulse(1.0)
        self._pulse.start()

    def boundingRect(self) -> QRectF:
        return QRectF(-self.WIDTH / 2, -self.HEIGHT / 2, self.WIDTH, self.HEIGHT)

    def set_appearance(self, hovered: bool) -> None:
        self._hovered = hovered
        self.update()

    def _set_pet_progress(self, value: float) -> None:
        self._pet_progress = value
        self.update()

    def pet(self) -> None:
        self._petting.stop()
        self._set_pet_progress(0.0)
        self._petting.start()

    def _eye_closure(self) -> float:
        t = self._pet_progress
        return max(0.0, min(t * 6, 1.0, (1 - t) * 4))

    def _set_curl(self, value: float) -> None:
        self._curl = value
        self.update()

    def set_curled_sleep(self, enabled: bool) -> None:
        self._curled_sleep = enabled
        self._update_curl()

    def _curl_target(self) -> float:
        return float(self._curled_sleep and self._activity is Activity.SLEEPING)

    def _update_curl(self) -> None:
        target = self._curl_target()
        if self._curl_animation.state() == QAbstractAnimation.State.Running:
            if self._curl_animation.endValue() == target:
                return
            self._curl_animation.stop()
        if target != self._curl:
            self._curl_animation.setStartValue(self._curl)
            self._curl_animation.setEndValue(target)
            self._curl_animation.start()

    def set_activity(self, activity: Activity, gaze: tuple[int, int] = (0, 0)) -> None:
        if activity is not self._activity:
            self._waking = self._activity.resting and not activity.resting
            self._target_posture = {
                Activity.RESTING: -5.5, Activity.SLEEPING: -7.0,
                Activity.OBSERVING: -1.5, Activity.REACTING: 1.5,
            }.get(activity, 0.0)
            self._posture_transition.stop()
            self._posture_transition.setStartValue(self._posture)
            self._posture_transition.setEndValue(self._target_posture)
            self._posture_transition.start()
        if (activity, gaze) != (self._activity, self._gaze):
            self._activity = activity
            self._gaze = gaze
            self._update_curl()
            self.update()

    def walk(self, distance: float, direction: int, angle: float = 0) -> None:
        if not distance and direction == self.facing and angle == self.angle:
            return
        if direction != self.facing:
            self._turn_from = self._drawn_facing()
            self.facing = direction
            self._turning.stop()
            if self._turn_from != direction:
                self._set_turn_progress(0.0)
                self._turning.start()
            else:
                self._set_turn_progress(1.0)
        if distance:
            self._settling.stop()
        self.angle = angle
        self.phase = (self.phase + distance / CYCLE_DISTANCE) % 1
        self.blend = min(1.0, self.blend + distance / 14)
        self.update()

    def stand(self, *, immediate: bool = False) -> None:
        if immediate:
            self._settling.stop()
            if self.blend:
                self._set_blend(0.0)
        elif self.blend and self._settling.state() == QAbstractAnimation.State.Stopped:
            self._settling.setStartValue(self.blend)
            self._settling.start()

    def finish_animations(self) -> None:
        self.skip_intro()
        self.stand(immediate=True)
        self._turning.stop()
        self._posture_transition.stop()
        self._pulse.stop()
        self._petting.stop()
        self._set_pet_progress(1.0)
        self._curl_animation.stop()
        self._set_curl(self._curl_target())
        self._carry_animation.stop()
        self._held = False
        self._carry_from = self._drag_tilt = 0.0
        self._set_carry_progress(1.0)
        self._set_turn_progress(1.0)
        self._set_posture(self._target_posture)
        self._set_light_pulse(0.0)

    def _drawn_facing(self) -> int:
        return self._turn_from if self._turn_progress < 0.5 else self.facing

    @property
    def entering(self) -> bool:
        return self._intro.state() == QAbstractAnimation.State.Running

    def start_intro(self) -> None:
        self._set_intro_progress(0.0)
        self._intro.start()

    def skip_intro(self) -> None:
        if self.entering:
            self._intro.stop()
            self._set_intro_progress(1.0)
            self.intro_finished.emit()
        elif self._intro_progress < 1:
            self._set_intro_progress(1.0)

    def _set_intro_progress(self, progress: float) -> None:
        self._intro_progress = progress
        self.update()

    def _paint_intro(self, painter, progress: float) -> None:
        opening = max(0.0, min(1.0, (progress - 0.12) / 0.29))
        emerge = max(0.0, min(1.0, (progress - 0.37) / 0.54))
        seal = max(0.0, (progress - 0.79) / 0.21)
        glow = min(progress * 10, 1.0) * (1 - seal)
        seam = -40.0
        height = 52 * min(progress * 5 + 0.1, 1.0) * (1 - seal)
        width = (0.9 + 11 * opening) * (1 - seal)
        tear = _polygon((seam, -height), (seam + width, -height * 0.34),
                        (seam + 0.65 * width, -6), (seam + width, height * 0.31),
                        (seam, height), (seam - width, height * 0.28),
                        (seam - 0.64 * width, 3), (seam - width, -height * 0.32))
        painter.save()
        painter.setOpacity(glow)
        for stroke, color in ((9, "#382252"), (5, "#693589"), (2, "#d089ff")):
            painter.setPen(QPen(QColor(color), stroke))
            painter.setBrush(QColor("#140e22"))
            painter.drawPath(tear)
        for x, y in ((-6, -39), (5, -25), (17, 29), (-15, 19)):
            _disc(painter, (seam + x * (0.5 + opening), y * (1 - seal)), 1.3, QColor("#d9b0ff"))
        painter.restore()

        if 0.10 < progress < 0.47:
            painter.save()
            painter.setOpacity(min((progress - 0.10) * 14, (0.47 - progress) * 12, 1))
            for side in (-1, 1):
                self._paint_leg(painter, (seam - 3, 0), (seam + 12 + width, side * 13),
                                (seam + width, side * (9 + 21 * opening)), side < 0, toe=3)
            painter.restore()

        if emerge:
            painter.save()
            painter.setClipRect(QRectF(seam - 48 * seal, -88, 176, 176))
            travel = emerge * emerge * (3 - 2 * emerge)
            painter.translate(-93 * (1 - travel), 0)
            # Render a distance-driven gait without advancing the live behavior.
            phase, blend = self.phase, self.blend
            self.phase = (93 * travel / CYCLE_DISTANCE) % 1
            self.blend = min(1.0, (1 - emerge) * 5)
            try:
                self._paint_puppet(painter)
            finally:
                self.phase, self.blend = phase, blend
                painter.restore()

    def paint(self, painter, option, widget=None) -> None:
        if self._intro_progress < 1:
            self._paint_intro(painter, self._intro_progress)
        else:
            self._paint_puppet(painter)

    def _paint_puppet(self, painter) -> None:
        painter.save()
        affection = sin(pi * self._pet_progress) if self._pet_progress < 1 else 0.0
        if affection:
            heart = QColor("#ff86a8")
            heart.setAlphaF(min(1.0, affection * 1.7))
            y = -56 - 13 * self._pet_progress
            _disc(painter, (-3, y), 3.8, heart)
            _disc(painter, (3, y), 3.8, heart)
            painter.drawPath(_polygon((-6.5, y + 1), (6.5, y + 1), (0, y + 8)))
        wiggle = self._struggle() + affection * 0.58 * sin(5 * pi * self._pet_progress)
        contact = self._desktop_contact
        angle = self.angle
        if contact is None:
            angle += self._drag_tilt * self._suspension() + 5 * wiggle
        painter.rotate(angle)
        accent = self._optic
        if self._activity.resting:
            accent = accent.darker(235 if self._activity is Activity.SLEEPING else 200)
        if self._birdseye:
            self._paint_overhead(painter, accent, wiggle)
            painter.restore()
            return
        drawn_facing = self._drawn_facing()
        turn_width = 1 - 0.42 * sin(pi * self._turn_progress)
        painter.scale(drawn_facing * turn_width, 1)
        bob = self._posture + self.blend * (1 - cos(4 * pi * self.phase))
        bob += self._landing() - 6 * self._suspension() - 5 * affection - 7 * self._curl
        projection = None if contact is None else contact.leg_projector(angle, drawn_facing * turn_width)
        self._paint_legs(painter, far=True, bob=bob, wiggle=wiggle, projection=projection)
        self._paint_tail(painter, bob, accent, wiggle)
        painter.save()
        painter.translate(0, -bob)
        self._paint_body(painter, accent, drawn_facing)
        painter.restore()
        self._paint_legs(painter, far=False, bob=bob, wiggle=wiggle, projection=projection)
        painter.restore()

    def _struggle(self) -> float:
        if not self._held:
            return 0.0
        progress = max(0.0, (self._carry_progress - 0.14) / 0.86)
        strength = 0.18 if self._activity is Activity.SLEEPING else 1.0
        return strength * (1 - progress) * sin(progress * 7 * pi)

    def _landing(self) -> float:
        if self._held:
            return 0.0
        progress = self._carry_progress
        return -8 * self._carry_from * sin(2.5 * pi * progress) * (1 - progress)**2

    def _paint_legs(self, painter, *, far: bool, bob: float, wiggle: float, projection=None) -> None:
        legs = _FAR_LEGS if far else _NEAR_LEGS
        tuck = self._suspension()
        floor = 28 if far else 41
        if self._desktop_contact is not None:
            floor += (FOOT_CONTACT - floor) * self._desktop_contact.strength
            wiggle *= 1 - self._desktop_contact.strength
        upper, lower = (25, 29) if far else (29, 35)
        for index, ((hip_x, hip_y), foot_x, bend) in enumerate(legs):
            # Far-front, far-rear, and near-middle form one tripod.
            tripod = (index + int(far)) % 2
            phase = self.phase + 0.5 * tripod
            hip = (hip_x, hip_y - bob)
            foot = foot_at(phase, foot_x, floor, self.blend)
            kick = (1 - 2 * tripod) * wiggle
            foot = (foot[0] * (1 - 0.16 * tuck) + 10 * kick, foot[1] + 5 * tuck + 6 * kick)
            curl = self._curl
            toe_tip = None
            if projection is not None:
                inside, planted = projection
                curl *= 1 - self._desktop_contact.strength
            foot = _between(foot, (hip_x * 0.9, floor - (1 if far else 4)), curl)
            if projection is not None:
                foot = planted(foot)
                toe_tip = inside((foot[0] + 4, foot[1]))
            knee = knee_at(hip, foot, upper, lower, bend)
            if projection is not None:
                knee = inside(knee, 3.0)
            self._paint_leg(painter, hip, knee, foot, far, toe=4, toe_tip=toe_tip)

    def _paint_leg(self, painter, hip, knee, foot, far: bool, toe: float, *, toe_tip=None) -> None:
        link = _FAR if far else self._links
        joint = _STEEL if far else _LIGHT_STEEL
        _line(painter, hip, knee, 9 if far else 11, _INK)
        _line(painter, knee, foot, 7 if far else 8, _INK)
        _line(painter, hip, knee, 5 if far else 7, link)
        _line(painter, knee, foot, 3.5 if far else 4, link)
        _line(painter, foot, toe_tip if toe_tip is not None else (foot[0] + toe, foot[1]), 4, _INK)
        if not far:
            _line(painter, _between(hip, knee, 0.24), _between(hip, knee, 0.73), 2, self._trim)
            _line(painter, _between(knee, foot, 0.22), _between(knee, foot, 0.78), 1.5, _LIGHT_STEEL)
        _disc(painter, knee, 4.5 if far else 5.5, _INK)
        _disc(painter, knee, 2.4 if far else 3.5, joint)
        if not far:
            _disc(painter, knee, 1.4, _GUNMETAL)
        _disc(painter, hip, 4 if far else 5, _INK)
        _disc(painter, hip, 2 if far else 2.5, joint)

    def _paint_tail(self, painter, bob: float, accent: QColor, wiggle: float) -> None:
        sway = sin(2 * pi * self.phase) * self.blend + wiggle * 1.5
        droop = min(0, self._posture) * 0.04
        droop -= 0.18 * self._suspension()
        start = (-30.0, 0.0 if self._birdseye else -5.0 - bob)
        links = _TOP_TAIL_LINKS if self._birdseye else _TAIL_LINKS
        curled_links = ((-9, -8), (3, -12), (13, -7), (14, -1), (11, 4)) if self._birdseye else (
            (-8, -9), (3, -13), (11, -8), (13, -1), (11, 5),
        )
        for index, (dx, dy) in enumerate(links):
            dx, dy = _between((dx, dy), curled_links[index], self._curl)
            angle = droop + sway * index * 0.055
            end = (start[0] + dx * cos(angle) - dy * sin(angle),
                   start[1] + dx * sin(angle) + dy * cos(angle))
            _line(painter, start, end, 12 - index, _INK)
            _line(painter, start, end, 8 - index, self._links)
            _line(painter, _between(start, end, 0.28), _between(start, end, 0.66), 1.5, self._trim)
            _disc(painter, end, 3.1 - 0.25 * index, _FAR)
            start = end
        painter.save()
        painter.translate(*start)
        painter.setPen(QPen(_INK, 2))
        painter.setBrush(_LIGHT_STEEL)
        painter.drawPath(_TIP)
        _disc(painter, (4, 0.5), 2.2, accent)
        painter.restore()

    def _paint_overhead(self, painter, accent: QColor, wiggle: float) -> None:
        self._paint_tail(painter, 0.0, accent, wiggle)
        resting_tuck = 1 + min(0, self._posture) * 0.023
        tuck = resting_tuck + (0.76 - resting_tuck) * self._suspension()
        tuck -= 0.37 * self._curl
        for bank, side in enumerate((-1, 1)):
            for index, (hip_x, foot_x, spread, bend) in enumerate(_TOP_LEGS):
                tripod = (index + bank) % 2
                hip = (hip_x, side * 14)
                x, lift = foot_at(self.phase + tripod * 0.5, foot_x, 0.0, self.blend)
                kick = (1 - 2 * tripod) * wiggle
                foot = (x * tuck + 8 * kick, side * (spread * tuck + lift * 0.65 + kick * 5))
                knee = knee_at(hip, foot, 25, 33, side * bend)
                self._paint_leg(painter, hip, knee, foot, far=False, toe=0)

        scale = 1 - 0.03 * self._suspension() + self._landing() * 0.012
        painter.scale(scale, scale)
        if self._neon:
            self._paint_neon(painter, accent, overhead=True)
            return
        rim = _WHITE if self._hovered else _INK
        painter.setPen(QPen(rim, 2))
        painter.setBrush(_HULL_METAL)
        painter.drawPath(_TOP_SHELL)
        painter.setPen(QPen(_INK, 1.3))
        painter.setBrush(self._armor)
        painter.drawPath(_TOP_ARMOR)
        for side in (-1, 1):
            _line(painter, (-25, side * 15), (11, side * 16), 1.1, self._trim)
            for x in (-19, -13, -7):
                _line(painter, (x, side * 7), (x + 4, side * 11), 2.2, _SEAM)
            _disc(painter, (16, side * 11), 1.65, accent)
        _line(painter, (-25, 0), (15, 0), 1.25, _SEAM)
        painter.setPen(QPen(rim, 1.5))
        painter.setBrush(_VISOR_METAL)
        painter.drawPath(_TOP_VISOR)
        gaze_x, gaze_y = self._gaze
        angle = radians(self.angle)
        look_x = 0.35 * (gaze_x * cos(angle) + gaze_y * sin(angle))
        look_y = 0.35 * (gaze_y * cos(angle) - gaze_x * sin(angle))
        for side in (-1, 1):
            eye = (39, side * 6)
            _disc(painter, eye, 5.3, _SHADOW)
            if self._pet_progress < 1 and not self._held and self._activity is not Activity.SLEEPING:
                painter.save()
                painter.translate(*eye)
                painter.rotate(-90)
                _happy_eye(painter, 0, 0, 2.7, self._eye_closure(), accent)
                painter.restore()
            elif self._activity.resting:
                _line(painter, (38, eye[1] - 2), (38, eye[1] + 2), 1.2, accent)
            elif self._held:
                _line(painter, (36, eye[1] - side * 2.6), (41, eye[1] + side * 2.6), 2, accent)
            else:
                light = _WHITE if self._light_pulse > 0.45 or self._activity is Activity.REACTING else accent
                _disc(painter, (39.5 + look_x, eye[1] + look_y), 3.15, light)
                _disc(painter, (40.5 + look_x, eye[1] + look_y - 0.8), 1.1, _WHITE)

    def _paint_body(self, painter, accent: QColor, drawn_facing: int) -> None:
        if self._neon:
            self._paint_neon(painter, accent, overhead=False)
            return
        rim = _WHITE if self._hovered else _INK
        painter.setPen(QPen(rim, 2))
        painter.setBrush(_HULL_METAL)
        painter.drawPath(_HULL)
        painter.setPen(QPen(_INK, 1.25))
        painter.setBrush(self._armor)
        painter.drawPath(_ARMOR)
        _line(painter, (-27, -12), (-16, -16), 1.0, self._trim)
        _line(painter, (-16, -16), (8, -16), 1.0, self._trim)
        for x in (-23, -17, -11, -5):
            _line(painter, (x, -5), (x + 4, -9), 2.9, _SEAM)
            _line(painter, (x + 0.5, -5.5), (x + 4, -9), 1.25, _INK)
        for x, y in ((-26, -8), (12, -11), (16, -4)):
            _disc(painter, (x, y), 1.6, self._trim)
            _disc(painter, (x, y), 0.65, _SEAM)
        painter.setPen(QPen(_INK, 1.3))
        painter.setBrush(_SIDE_METAL)
        painter.drawPath(_SIDE_PANEL)
        for x in (-28, -23, -18):
            _line(painter, (x, 8), (x + 2, 8), 1.65, accent)
        _line(painter, (-11, 8), (10, 6), 1.05, _STEEL)

        gx, gy = self._gaze
        painter.save()
        painter.translate(24, 0)
        painter.rotate(gy * 1.7)
        painter.translate(-24, 0)
        painter.setPen(QPen(rim, 1.5))
        painter.setBrush(_VISOR_METAL)
        painter.drawPath(_VISOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._trim)
        painter.drawPath(_VISOR_BROW)
        _disc(painter, (35, -2), 7.4, _SHADOW)
        _disc(painter, (35, -2), 6.3, _LENS)
        if self._light_pulse and self._pet_progress >= 1:
            pulse = QColor(accent)
            pulse.setAlphaF(self._light_pulse)
            painter.setPen(QPen(pulse, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            radius = 4.6 + (1 - self._light_pulse) * 1.9
            painter.drawEllipse(QPointF(35, -2), radius, radius)
        if self._pet_progress < 1 and not self._held and self._activity is not Activity.SLEEPING:
            _happy_eye(painter, 35, -2, 3.8, self._eye_closure(), accent)
        elif self._activity.resting:
            _line(painter, (32, -1), (38, -1), 1.8, accent)
        elif self._held:
            _line(painter, (32, -3), (38, -1), 2.1, accent)
            _line(painter, (33, 3), (37, 2.6), 1.0, self._trim)
        elif self._activity is Activity.REACTING:
            _disc(painter, (35, -2), 4.9, accent)
            _disc(painter, (35, -2), 3.2, _WHITE)
        else:
            eye = (35 + gx * drawn_facing * 0.75, -2 + gy * 0.4)
            radius = 3.4 if self._activity is Activity.OBSERVING else 4.5
            _disc(painter, eye, radius, accent)
            _disc(painter, (eye[0] + 1, eye[1] - 1.5), 1.4, _WHITE)
        _disc(painter, (28, 4), 1.45, accent)
        painter.restore()

    def _paint_neon(self, painter, accent: QColor, *, overhead: bool) -> None:
        painter.setPen(QPen(_WHITE if self._hovered else _INK, 2))
        painter.setBrush(_NEON_FRAME)
        painter.drawPath(_NEON_TOP if overhead else _NEON_HULL)
        painter.setPen(QPen(_NEON_EDGE, 1))
        painter.setBrush(self._armor)
        painter.drawPath(_NEON_TOP_PLATE if overhead else _NEON_PLATE)
        _line(painter, (-30, -12), (-21, -16), 1, _NEON_WEAR)
        _line(painter, (-20, -16), (-10, -16), 0.8, _NEON_WEAR)

        for x in (-25, -19, -13):
            _line(painter, (x, -5), (x + 4, -10), 2.5, _NEON_FRAME)
        for x, y in ((-6, -11), (-1, -8), (10, -11), (13, -5)):
            _line(painter, (x, y), (x + 2, y - 0.6), 0.8, _NEON_EDGE)
        for x, y in ((-31, -5), (8, -14), (13, 6 if overhead else -4)):
            _disc(painter, (x, y), 1.7, _NEON_FRAME)
            _line(painter, (x - 0.6, y + 0.3), (x + 0.6, y - 0.3), 0.7, _NEON_WEAR)

        # The cables run under the broken edge of the armor to the visor mount.
        if overhead:
            cable_start, bend, cable_end = (-31, 13), (-22, 19), (23, 12)
        else:
            cable_start, bend, cable_end = (-35, 3), (-24, 11), (25, 6)
        for offset, color in ((0, _NEON_CABLE), (3, self._trim)):
            x, y = cable_start
            joint_x, joint_y = bend
            end_x, end_y = cable_end
            joint = (joint_x, joint_y + offset)
            _line(painter, (x, y + offset), joint, 1.4, color)
            _line(painter, joint, (end_x, end_y + offset), 1.4, color)
        _line(painter, (bend[0] + 8, bend[1] - 1), (bend[0] + 9, bend[1] + 3), 2, _NEON_EDGE)

        painter.save()
        painter.translate(37, 0 if overhead else -5)
        if overhead:
            painter.rotate(-90)
        painter.setPen(QPen(_NEON_EDGE, 1.4))
        painter.setBrush(_LENS)
        painter.drawPath(_NEON_LENS)
        painter.setClipPath(_NEON_LENS)

        wake = 1.0
        if self._waking and self._posture_transition.state() == QAbstractAnimation.State.Running:
            wake = self._posture_transition.currentTime() / self._posture_transition.duration()
        pickup = self._carry_progress * 2.5 if self._held else 1.0
        glitch = min(wake, pickup)
        if self._pet_progress < 1 and not self._held and self._activity is not Activity.SLEEPING:
            for eye_x in (-6, 6):
                _happy_eye(painter, eye_x, 0, 3.9, self._eye_closure(), accent)
        elif glitch < 1:
            phase = int(glitch * 6)
            _line(painter, (-12, -2), (-4 + phase, -2), 1.5, accent)
            _line(painter, (0, 2), (12, 2), 1.25, _NEON_CABLE if phase % 2 else accent)
            _disc(painter, (9 - phase, -3.5), 1.05, _WHITE)
        elif self._activity.resting:
            _line(painter, (-3, 1), (3, 1), 1.35, accent)
        elif self._held:
            _line(painter, (-10, -2), (-4, 1), 1.8, accent)
            _line(painter, (4, 1), (10, -2), 1.8, accent)
            _line(painter, (-2, 3), (2, 3), 1.1, _NEON_CABLE)
        else:
            light = _WHITE if self._light_pulse > 0.45 else accent
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(light)
            for segment in _NEON_VISOR_SEGMENTS:
                painter.drawPath(segment)
        painter.restore()
