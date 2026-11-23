"""Pointer momentum and single-display throw simulation in Qt logical pixels."""

from collections import deque
from dataclasses import dataclass
from math import exp, hypot, isfinite

# Time in seconds, speed in logical pixels per second.
HISTORY = 0.084
MIN_SAMPLE_TIME = 0.028
STALE_AFTER = 0.050
THROW_SPEED = 580.0
MAX_RELEASE_SPEED = 1680.0

GRAVITY = 1750.0
AIR_DRAG = 0.8                    # Horizontal damping per second.
WALL_RESTITUTION = 0.32
CEILING_RESTITUTION = 0.22
BOUNCE_SPEED = 520.0
FLOOR_RESTITUTION = 0.18
MAX_BOUNCE_SPEED = 175.0
MAX_STEP = 1 / 120
MAX_ELAPSED = 0.100
RECOVERY_TIME = 0.36


class CursorHistory:
    """Short-lived in-memory input samples, recorded only during a grab."""

    def __init__(self) -> None:
        self._samples: deque[tuple[float, float, float]] = deque(maxlen=256)
        self._anchor = (0.0, 0.0)
        self._last_motion: float | None = None
        self._previous_motion: float | None = None

    def clear(self) -> None:
        self._samples.clear()
        self._last_motion = self._previous_motion = None

    def add(self, timestamp: float, x: float, y: float) -> None:
        if not all(map(isfinite, (timestamp, x, y))):
            return
        samples = self._samples
        if samples and timestamp < samples[-1][0]:
            return
        if not samples or (len(samples) == 1 and timestamp == samples[0][0]):
            self._anchor = x, y
        elif timestamp > samples[-1][0] and hypot(x - self._anchor[0], y - self._anchor[1]) >= 3:
            self._anchor = x, y
            self._previous_motion = self._last_motion
            self._last_motion = timestamp
        if samples and timestamp == samples[-1][0]:
            samples.pop()
        samples.append((timestamp, x, y))
        while len(samples) > 2 and samples[1][0] <= timestamp - HISTORY:
            samples.popleft()

    def release(self) -> tuple[float, float] | None:
        # A single reported jump is insufficient evidence of a flick.
        if self._last_motion is None or self._previous_motion is None:
            return None
        end, x, y = self._samples[-1]
        start = max(end - HISTORY, self._samples[0][0])
        duration = end - start
        if (duration < MIN_SAMPLE_TIME or end - self._last_motion > STALE_AFTER
                or self._previous_motion < start):
            return None

        # Fit five equally spaced positions instead of giving high-polling
        # segments extra weight. Recent positions get more influence.
        first = self._at(start)
        if hypot(x - first[0], y - first[1]) < 13:
            return None
        points = [first, *(self._at(start + i * duration / 4) for i in range(1, 4)), (x, y)]
        # Weighted least squares with weights 1..5 and sample indices 0..4.
        weights = (-8, -10, -6, 4, 20)
        vx = sum(w * point[0] for w, point in zip(weights, points)) * 4 / (70 * duration)
        vy = sum(w * point[1] for w, point in zip(weights, points)) * 4 / (70 * duration)
        speed = hypot(vx, vy)
        if speed < THROW_SPEED:
            return None
        scale = min(1.0, MAX_RELEASE_SPEED / speed)
        return vx * scale, vy * scale

    def _at(self, target: float) -> tuple[float, float]:
        samples = iter(self._samples)
        before, x, y = next(samples)
        for after, next_x, next_y in samples:
            if after >= target:
                blend = (target - before) / (after - before)
                return x + (next_x - x) * blend, y + (next_y - y) * blend
            before, x, y = after, next_x, next_y
        return x, y


@dataclass(slots=True, frozen=True)
class ThrowBounds:
    left: float
    top: float
    right: float
    floor: float
    roam_left: float
    roam_right: float


@dataclass(slots=True)
class ThrowMotion:
    x: float
    y: float
    vx: float
    vy: float
    bounds: ThrowBounds
    initial_angle: float = 0.0
    initial_tuck: float = 0.0
    initial_kick: float = 0.0
    age: float = 0.0
    impact: float = 0.0
    impact_age: float = 0.0
    bounced: bool = False
    recovery: float | None = None
    recovery_start: float = 0.0
    recovery_end: float = 0.0

    def contain(self) -> None:
        limits = self.bounds
        self.x = min(max(self.x, limits.left), limits.right)
        self.y = min(max(self.y, limits.top), limits.floor)

    def resize(self, bounds: ThrowBounds) -> None:
        self.bounds = bounds
        self.contain()
        if self.recovery is not None:
            self.y = bounds.floor
            self.recovery_start = min(max(self.recovery_start, bounds.left), bounds.right)
            self.recovery_end = min(max(self.recovery_end, bounds.roam_left), bounds.roam_right)

    def advance(self, elapsed: float) -> bool:
        """Update flight or recovery. Return True once the creature can walk."""
        if not isfinite(elapsed) or elapsed <= 0:
            return False
        remaining = min(MAX_ELAPSED, elapsed)
        while remaining > 1e-9:
            dt = min(MAX_STEP, remaining)
            remaining -= dt
            self.age += dt
            self.impact_age += dt
            if self.recovery is not None:
                self.recovery = min(RECOVERY_TIME, self.recovery + dt)
                eased = 1 - (1 - self.recovery / RECOVERY_TIME)**3
                self.x = self.recovery_start + (self.recovery_end - self.recovery_start) * eased
                if self.recovery >= RECOVERY_TIME - 1e-9:
                    return True
            else:
                self._fly(dt)
        return False

    def _fly(self, dt: float) -> None:
        limits = self.bounds
        damping = exp(-AIR_DRAG * dt)
        self.x += self.vx * (1 - damping) / AIR_DRAG
        self.vx *= damping
        self.y += (self.vy + GRAVITY * dt / 2) * dt
        self.vy += GRAVITY * dt
        if self.x < limits.left or self.x > limits.right:
            self.x = min(max(self.x, limits.left), limits.right)
            self.vx *= -WALL_RESTITUTION if limits.right > limits.left else 0.0
        if self.y < limits.top:
            self.y = limits.top
            self.vy = abs(self.vy) * CEILING_RESTITUTION
        elif self.y >= limits.floor and self.vy >= 0:
            self.y = limits.floor
            self._land()

    def _land(self) -> None:
        strength = min(1.0, self.vy / 1050)
        if strength > self.impact or self.impact_age > 0.25:
            self.impact = strength
            self.impact_age = 0.0
        self.vx *= 0.42
        if not self.bounced and self.vy >= BOUNCE_SPEED and self.bounds.floor > self.bounds.top + 2:
            self.bounced = True
            self.vy = -min(self.vy * FLOOR_RESTITUTION, MAX_BOUNCE_SPEED)
        else:
            self.recovery = 0.0
            self.recovery_start = self.x
            slide = min(22.0, max(-22.0, self.vx * 0.09))
            self.recovery_end = min(max(self.x + slide, self.bounds.roam_left), self.bounds.roam_right)
            self.vx = self.vy = 0.0
