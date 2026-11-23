"""Distance-driven alternating tripod gait for the prototype."""

from math import hypot, pi, sin, sqrt

STANCE = 0.62
STRIDE = 28.0
CYCLE_DISTANCE = STRIDE / STANCE


def foot_at(phase: float, rest_x: float, floor: float, blend: float,
            *, stride: float | None = None) -> tuple[float, float]:
    """Sweep back at walking speed on the ground and lift on the return."""
    phase %= 1
    if phase < STANCE:
        offset = STRIDE * (0.5 - phase / STANCE)
        lift = 0.0
    else:
        swing = (phase - STANCE) / (1 - STANCE)
        progress = swing**2 * (3 - 2 * swing)
        # Match the stance sweep velocity at lift-off and touchdown.
        tangent = -(1 - STANCE) / STANCE
        offset = STRIDE * (progress - 0.5 + tangent * swing * (1 - swing) * (1 - 2 * swing))
        lift = 11 * sin(pi * swing) ** 2
    return rest_x + offset * (blend if stride is None else stride), floor - lift * blend


def knee_at(
    hip: tuple[float, float],
    foot: tuple[float, float],
    upper: float,
    lower: float,
    bend: int,
) -> tuple[float, float]:
    """Find the joint of a two-link leg on the chosen side of the hip-foot line."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    distance = hypot(dx, dy)
    if distance < 1e-6:
        return hip[0], hip[1] - upper * bend
    along = (upper**2 - lower**2 + distance**2) / (2 * distance)
    height = sqrt(max(0, upper**2 - along**2)) * bend
    return (
        hip[0] + (along * dx - height * dy) / distance,
        hip[1] + (along * dy + height * dx) / distance,
    )
