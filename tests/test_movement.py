import pytest

from arachnid.__main__ import _speed
from arachnid.movement import advance, clamp_origin


@pytest.mark.parametrize(
    ("origin", "area_origin", "area_length", "window_length", "expected"),
    [(400, 0, 500, 84, 400), (800, 0, 500, 84, 416),
     (-900, -800, 500, 84, -800), (82, 20, 30, 84, 20)],
)
def test_clamp_to_work_area(origin, area_origin, area_length, window_length, expected):
    assert clamp_origin(origin, area_origin, area_length, window_length) == expected


@pytest.mark.parametrize(
    ("position", "velocity", "elapsed", "edges", "expected"),
    [(25, 20, 0.025, (0, 100), (25.5, 20)),
     (95, 20, 1, (0, 100), (85, -20)),
     (-95, -20, 0.5, (-100, 0), (-95, 20)),
     (80, 20, 1, (0, 100), (100, -20)),
     (5, 20, 15, (0, 100), (95, -20)),
     (25, 20, 1, (5, 5), (5, 20))],
)
def test_horizontal_motion(position, velocity, elapsed, edges, expected):
    assert advance(position, velocity, elapsed, *edges) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["0", "601", "nan", "inf", "fast"])
def test_invalid_speed(text):
    from argparse import ArgumentTypeError

    with pytest.raises(ArgumentTypeError):
        _speed(text)


def test_speed_accepts_fractional_values():
    assert _speed("110.5") == 110.5
