"""Autonomous decisions in active time, independent of Qt and window geometry."""

from enum import Enum, auto
from random import Random


class Activity(Enum):
    WANDERING = auto()
    OBSERVING = auto()
    RESTING = auto()
    SLEEPING = auto()
    REACTING = auto()

    @property
    def resting(self) -> bool:
        return self in (Activity.RESTING, Activity.SLEEPING)


class Behavior:
    OBSERVE_NEAR = 155
    OBSERVE_FAR = 215

    def __init__(self, rng: Random | None = None) -> None:
        self._random = rng if rng is not None else Random()
        self.activity = Activity.WANDERING
        self.remaining = self._random.uniform(3.5, 6.5)
        self._observe_cooldown = 0.0

    def react_to_click(self) -> None:
        if self.activity is Activity.SLEEPING:
            return
        self.activity = Activity.REACTING
        self.remaining = 0.85

    def sleep(self) -> None:
        self.activity = Activity.SLEEPING
        self.remaining = 0.0

    def wake(self) -> None:
        self._start_walking()
        self._observe_cooldown = 2.0

    def update(self, elapsed: float, cursor_distance: float | None) -> bool:
        """Advance the decision timer and return whether to reverse the next walk."""
        if self.activity is Activity.SLEEPING:
            return False
        self.remaining -= elapsed
        self._observe_cooldown = max(0, self._observe_cooldown - elapsed)

        if self.activity is Activity.WANDERING:
            if (cursor_distance is not None and cursor_distance <= self.OBSERVE_NEAR
                    and self._observe_cooldown == 0):
                self.activity = Activity.OBSERVING
                self.remaining = self._random.uniform(3.0, 4.5)
            elif self.remaining <= 0:
                self.activity = Activity.RESTING
                self.remaining = self._random.uniform(1.5, 3.0)
            return False

        if self.activity is Activity.OBSERVING:
            cursor_left = cursor_distance is None or cursor_distance >= self.OBSERVE_FAR
            if cursor_left or self.remaining <= 0:
                self._observe_cooldown = 4.0
                return self._start_walking()
        elif self.remaining <= 0:
            if self.activity is Activity.REACTING:
                self._observe_cooldown = 2.0
            return self._start_walking()
        return False

    def _start_walking(self) -> bool:
        self.activity = Activity.WANDERING
        self.remaining = self._random.uniform(3.5, 6.5)
        return self._random.random() < 0.4
