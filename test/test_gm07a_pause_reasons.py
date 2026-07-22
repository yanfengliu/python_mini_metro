"""GM-07a red contract: the Mediator pause-reason model behind ``is_paused``."""

from __future__ import annotations

import inspect
import json
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from env import MiniMetroEnv
from event.keyboard import KeyboardEvent
from event.type import KeyboardEventType
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint

USER = "user"
MENU = "menu"


def _require(testcase: unittest.TestCase, host: object, name: str):
    testcase.assertTrue(
        hasattr(host, name),
        f"GM-07a product attribute is missing: {type(host).__name__}.{name}",
    )
    return getattr(host, name)


def _reason_api(testcase: unittest.TestCase, host: object):
    hold = _require(testcase, host, "hold_pause_reason")
    release = _require(testcase, host, "release_pause_reason")
    return hold, release


def _read_paused(testcase: unittest.TestCase, host: object) -> bool:
    try:
        value = host.is_paused
    except AttributeError:
        testcase.fail(
            "GM-07a: the is_paused getter must report False on a bare Mediator "
            "with no reason store"
        )
    testcase.assertIs(type(value), bool, "is_paused must project an exact bool")
    return value


def _space(mediator: Mediator) -> None:
    mediator.react_keyboard_event(
        KeyboardEvent(KeyboardEventType.KEY_UP, pygame.K_SPACE)
    )


class TestGM07aPauseReasonModel(unittest.TestCase):
    def test_public_pause_facade_signatures_are_frozen(self):
        # regression guard: green at baseline (mirrors the input-contract pins).
        expected = {
            "set_paused": "(self, paused: 'bool') -> 'None'",
            "apply_action": "(self, action: 'object') -> 'bool'",
        }
        self.assertEqual(
            {
                name: str(inspect.signature(getattr(Mediator, name)))
                for name in expected
            },
            expected,
        )

    def test_is_paused_projects_an_exact_bool_while_reasons_are_held(self):
        mediator = Mediator(seed=7001)
        self.assertIs(_read_paused(self, mediator), False)
        hold, release = _reason_api(self, mediator)
        hold(MENU)
        self.assertIs(_read_paused(self, mediator), True)
        hold(USER)
        self.assertIs(_read_paused(self, mediator), True)
        release(MENU)
        self.assertIs(_read_paused(self, mediator), True)
        release(USER)
        self.assertIs(_read_paused(self, mediator), False)
        mediator.is_paused = True
        self.assertIs(_read_paused(self, mediator), True)
        mediator.is_paused = False
        self.assertIs(_read_paused(self, mediator), False)

    def test_bare_mediator_getter_reports_false_without_a_store(self):
        bare = Mediator.__new__(Mediator)
        self.assertIs(_read_paused(self, bare), False)
        self.assertIs(_read_paused(self, bare), False)

    def test_bare_mediator_setter_creates_a_per_instance_store(self):
        bare = Mediator.__new__(Mediator)
        bare.is_paused = True
        self.assertIs(_read_paused(self, bare), True)
        hold, release = _reason_api(self, bare)
        hold(MENU)
        bare.is_paused = False
        self.assertIs(
            _read_paused(self, bare),
            True,
            "the boolean setter must clear only the user reason",
        )
        release(MENU)
        self.assertIs(_read_paused(self, bare), False)

    def test_bare_mediators_share_no_class_level_reason_state(self):
        first = Mediator.__new__(Mediator)
        second = Mediator.__new__(Mediator)
        hold_first, release_first = _reason_api(self, first)
        hold_first(MENU)
        self.assertIs(_read_paused(self, first), True)
        self.assertIs(
            _read_paused(self, second),
            False,
            "a hold on one instance must never leak into another",
        )
        second.is_paused = True
        release_first(MENU)
        self.assertIs(_read_paused(self, first), False)
        self.assertIs(_read_paused(self, second), True)

    def test_hold_is_idempotent_and_release_of_non_held_reason_is_a_no_op(self):
        mediator = Mediator(seed=7006)
        hold, release = _reason_api(self, mediator)
        release(MENU)
        self.assertIs(_read_paused(self, mediator), False)
        hold(MENU)
        hold(MENU)
        release(MENU)
        self.assertIs(
            _read_paused(self, mediator),
            False,
            "holding twice must not turn the reason store into a counter",
        )
        hold(USER)
        release(MENU)
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "releasing a non-held reason must leave other reasons intact",
        )
        release(USER)
        self.assertIs(_read_paused(self, mediator), False)

    def test_unknown_pause_reasons_are_rejected_with_value_error(self):
        mediator = Mediator(seed=7007)
        hold, release = _reason_api(self, mediator)
        for reason in ("settings", "USER", "Menu", ""):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError):
                    hold(reason)
                with self.assertRaises(ValueError):
                    release(reason)
        self.assertIs(_read_paused(self, mediator), False)

    def test_user_and_menu_reasons_compose_and_release_independently(self):
        mediator = Mediator(seed=7008)
        hold, release = _reason_api(self, mediator)
        mediator.set_paused(True)
        hold(MENU)
        self.assertIs(_read_paused(self, mediator), True)
        release(MENU)
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "a menu release must leave the user pause in place",
        )
        hold(MENU)
        mediator.is_paused = False
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "a user clear must leave the menu hold in place",
        )
        mediator.set_paused(False)
        self.assertIs(_read_paused(self, mediator), True)
        release(MENU)
        self.assertIs(_read_paused(self, mediator), False)

    def test_space_toggle_routes_through_the_user_reason_and_never_clears_menu(self):
        mediator = Mediator(seed=7009)
        _space(mediator)
        self.assertIs(_read_paused(self, mediator), True)
        _space(mediator)
        self.assertIs(_read_paused(self, mediator), False)
        hold, release = _reason_api(self, mediator)
        hold(MENU)
        _space(mediator)
        self.assertIs(_read_paused(self, mediator), True)
        _space(mediator)
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "the space toggle must never clear the menu hold",
        )
        _space(mediator)
        release(MENU)
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "space must toggle the user reason, not the aggregated bool",
        )
        _space(mediator)
        self.assertIs(_read_paused(self, mediator), False)

    def test_structured_pause_and_resume_touch_only_the_user_reason(self):
        mediator = Mediator(seed=7010)
        self.assertTrue(mediator.apply_action({"type": "pause"}))
        self.assertIs(_read_paused(self, mediator), True)
        self.assertTrue(mediator.apply_action({"type": "resume"}))
        self.assertIs(_read_paused(self, mediator), False)
        hold, release = _reason_api(self, mediator)
        hold(MENU)
        self.assertTrue(mediator.apply_action({"type": "resume"}))
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "a structured resume must not clear the menu hold",
        )
        self.assertTrue(mediator.apply_action({"type": "pause"}))
        release(MENU)
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "a structured pause must hold the user reason",
        )
        self.assertTrue(mediator.apply_action({"type": "resume"}))
        self.assertIs(_read_paused(self, mediator), False)

    def test_speed_actions_clear_the_user_reason_but_never_the_menu_hold(self):
        mediator = Mediator(seed=7011)
        mediator.apply_speed_action("pause")
        self.assertIs(_read_paused(self, mediator), True)
        mediator.apply_speed_action("speed_1")
        self.assertIs(_read_paused(self, mediator), False)
        self.assertEqual(mediator.game_speed_multiplier, 1)
        hold, release = _reason_api(self, mediator)
        mediator.set_paused(True)
        hold(MENU)
        mediator.apply_speed_action("speed_2")
        self.assertEqual(mediator.game_speed_multiplier, 2)
        self.assertIs(
            _read_paused(self, mediator),
            True,
            "a speed selection must never clear the menu hold",
        )
        release(MENU)
        self.assertIs(
            _read_paused(self, mediator),
            False,
            "the speed selection must already have cleared the user reason",
        )

    def test_legacy_boolean_pause_surface_keeps_its_semantics(self):
        # regression guard: green at baseline (the bool facade every consumer reads).
        mediator = Mediator(seed=7012)
        mediator.is_paused = True
        self.assertIs(mediator.is_paused, True)
        mediator.set_paused(False)
        self.assertIs(mediator.is_paused, False)
        _space(mediator)
        self.assertIs(mediator.is_paused, True)
        _space(mediator)
        self.assertIs(mediator.is_paused, False)
        mediator.apply_speed_action("pause")
        self.assertIs(mediator.is_paused, True)
        mediator.apply_speed_action("speed_1")
        self.assertIs(mediator.is_paused, False)
        self.assertTrue(mediator.apply_action({"type": "pause"}))
        self.assertIs(mediator.is_paused, True)
        self.assertTrue(mediator.apply_action({"type": "resume"}))
        self.assertIs(mediator.is_paused, False)
        self.assertIs(type(mediator.is_paused), bool)

    def test_checkpoints_are_byte_identical_across_hold_release_cycles(self):
        env = MiniMetroEnv()
        env.reset(seed=7013)
        hold, release = _reason_api(self, env.mediator)
        before = canonical_checkpoint(env)
        before_bytes = json.dumps(before, sort_keys=True)
        hold(MENU)
        release(MENU)
        after = canonical_checkpoint(env)
        self.assertEqual(after, before)
        self.assertEqual(json.dumps(after, sort_keys=True), before_bytes)
        env.mediator.set_paused(True)
        paused_before = canonical_checkpoint(env)
        hold(MENU)
        release(MENU)
        paused_after = canonical_checkpoint(env)
        self.assertEqual(paused_after, paused_before)
        self.assertEqual(
            json.dumps(paused_after, sort_keys=True),
            json.dumps(paused_before, sort_keys=True),
        )

    def test_observation_projection_stays_bool_through_reason_transitions(self):
        env = MiniMetroEnv()
        env.reset(seed=7014)
        hold, release = _reason_api(self, env.mediator)

        def observed() -> bool:
            value = env.observe()["structured"]["is_paused"]
            self.assertIs(type(value), bool)
            return value

        self.assertIs(observed(), False)
        hold(MENU)
        self.assertIs(observed(), True)
        env.mediator.set_paused(True)
        self.assertIs(observed(), True)
        release(MENU)
        self.assertIs(observed(), True)
        env.mediator.set_paused(False)
        self.assertIs(observed(), False)


if __name__ == "__main__":
    unittest.main()
