"""Work-area geometry and movement in Qt logical pixels."""

from math import copysign, exp, hypot


def weighted_offset(dx: float, dy: float, elapsed: float) -> tuple[float, float]:
    """Return the gap still trailing a grab, limited to 26 logical pixels."""
    distance = hypot(dx, dy)
    if distance < 0.5:
        return 0.0, 0.0
    scale = min(1.0, 26 / distance) * exp(-elapsed / 0.08)
    return dx * scale, dy * scale


def clamp_origin(
    origin: int, area_origin: int, area_length: int, window_length: int
) -> int:
    last = area_origin + max(0, area_length - window_length)
    return min(max(origin, area_origin), last)


def advance(
    x: float, velocity: float, elapsed: float, left: int, right: int
) -> tuple[float, float]:
    """Reflect at either edge, preserving overshoot and fractional position."""
    width = right - left
    if width <= 0:
        return float(left), velocity

    x = min(max(x, left), right)
    offset = x - left
    phase = offset if velocity > 0 else 2 * width - offset
    phase = (phase + abs(velocity) * elapsed) % (2 * width)
    if phase < width:
        return left + phase, abs(velocity)
    return right - (phase - width), -abs(velocity)


def angle_delta(current: float, target: float) -> float:
    return (target - current + 180) % 360 - 180


def ramp_speed(speed: float, target: float, elapsed: float, duration: float) -> tuple[float, float]:
    """Return the new speed fraction and the integrated moving time."""
    difference = target - speed
    ramp_time = min(elapsed, abs(difference) * duration)
    end = speed + copysign(ramp_time / duration, difference)
    moving_time = (speed + end) * ramp_time / 2 + end * (elapsed - ramp_time)
    return (target if ramp_time < elapsed else end), moving_time
