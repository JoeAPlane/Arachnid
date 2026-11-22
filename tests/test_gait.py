from math import dist

import pytest

from arachnid.gait import CYCLE_DISTANCE, STANCE, foot_at, knee_at


def test_stance_cancels_window_translation():
    for phase in (0.0, 0.2, STANCE):
        x, y = foot_at(phase, rest_x=20, floor=40, blend=1)
        assert CYCLE_DISTANCE * phase + x == pytest.approx(34)
        assert y == 40


def test_swing_lifts_and_returns_to_the_start_of_stance():
    center_of_swing = (STANCE + 1) / 2
    assert foot_at(center_of_swing, 20, 40, 1) == pytest.approx((20, 29))
    assert foot_at(1, 20, 40, 1) == foot_at(0, 20, 40, 1)
    assert foot_at(center_of_swing, 20, 40, 0) == (20, 40)


@pytest.mark.parametrize("transition", [0, STANCE])
def test_horizontal_velocity_matches_each_side_of_a_gait_transition(transition):
    epsilon = 1e-5
    before = foot_at(transition - epsilon, 0, 0, 1)[0]
    at = foot_at(transition, 0, 0, 1)[0]
    after = foot_at(transition + epsilon, 0, 0, 1)[0]
    assert (at - before) / epsilon == pytest.approx((after - at) / epsilon, abs=0.02)


@pytest.mark.parametrize("bend", [-1, 1])
def test_knee_preserves_each_link_length(bend):
    hip, foot = (0, 0), (20, 33)
    knee = knee_at(hip, foot, 25, 29, bend)
    assert dist(hip, knee) == pytest.approx(25)
    assert dist(foot, knee) == pytest.approx(29)
