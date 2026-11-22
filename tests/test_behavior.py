from random import Random

from arachnid.behavior import Activity, Behavior


def test_walking_bouts_include_rest_and_can_change_direction():
    behavior = Behavior(Random(2))
    behavior.update(behavior.remaining, None)
    assert behavior.activity is Activity.RESTING
    behavior.update(1, 0)
    assert behavior.activity is Activity.RESTING
    assert behavior.update(behavior.remaining, 0)
    assert behavior.activity is Activity.WANDERING


def test_observation_uses_separate_enter_and_leave_distances():
    behavior = Behavior(Random(4))
    behavior.update(0.1, Behavior.OBSERVE_NEAR + 1)
    assert behavior.activity is Activity.WANDERING
    behavior.update(0.1, Behavior.OBSERVE_NEAR)
    assert behavior.activity is Activity.OBSERVING
    behavior.update(0.1, Behavior.OBSERVE_FAR - 1)
    assert behavior.activity is Activity.OBSERVING
    behavior.update(0.1, Behavior.OBSERVE_FAR)
    assert behavior.activity is Activity.WANDERING


def test_observation_ends_even_if_the_cursor_stays_nearby():
    behavior = Behavior(Random(1))
    behavior.update(0.1, 50)
    behavior.update(behavior.remaining, 50)
    assert behavior.activity is Activity.WANDERING
    behavior.update(0.1, 50)
    assert behavior.activity is Activity.WANDERING


def test_click_interrupts_rest_and_restarts_reaction():
    behavior = Behavior(Random(6))
    behavior.update(behavior.remaining, None)
    behavior.react_to_click()
    behavior.update(0.75, 0)
    assert behavior.activity is Activity.REACTING
    behavior.react_to_click()
    behavior.update(0.75, 0)
    assert behavior.activity is Activity.REACTING
    behavior.update(0.2, 0)
    behavior.update(0.1, 0)
    assert behavior.activity is Activity.WANDERING
