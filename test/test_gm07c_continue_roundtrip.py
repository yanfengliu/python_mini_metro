"""GM-07c red contract: the autosave -> Continue path is byte-faithful.

End-to-end over the real ``MiniMetroEnv``/``Mediator``/``save_game`` pipeline:
play a real game, drive a controller to the pause menu (which autosaves to a
private temporary file through the real ``save_game``), then Continue from a
fresh controller and assert the resumed game is ``canonical_checkpoint``
byte-identical to the saved boundary and stays in lockstep with a never-exited
control. A game-over promotion deletes the file, so Continue is unavailable.

The autosave file is always a per-test ``tempfile.TemporaryDirectory``; the
suite never reads, writes, or deletes a developer's real ``saves`` tree.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width
from env import MiniMetroEnv
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from save_game import load_game, save_game

_LOCKSTEP_DT_MS = 250


def _symbol(testcase, module_name, name):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-07c product module is missing: {module_name} ({error})")
    value = getattr(module, name, None)
    testcase.assertIsNotNone(
        value, f"GM-07c product symbol is missing: {module_name}.{name}"
    )
    return value


def _screen(testcase, name):
    states = _symbol(testcase, "app_controller", "AppScreen")
    testcase.assertTrue(
        hasattr(states, name), f"GM-07c AppScreen member is missing: {name}"
    )
    return getattr(states, name)


def _continue_controller(testcase, build_game, *, start_state, build_from, autosave):
    controller_type = _symbol(testcase, "app_controller", "AppController")
    parameters = inspect.signature(controller_type).parameters
    for name in ("build_from", "autosave"):
        testcase.assertIn(
            name,
            parameters,
            f"GM-07c: AppController.__init__ must accept an optional {name!r} seam",
        )
    return controller_type(
        build_game,
        start_state=start_state,
        build_from=build_from,
        autosave=autosave,
    )


def _continue_center(testcase):
    layout = _symbol(testcase, "ui.menu_screens", "title_layout")(
        screen_width, screen_height
    )
    testcase.assertIn("continue", layout, "title_layout must expose a 'continue' rect")
    center = pygame.Rect(layout["continue"]).center
    return Point(int(center[0]), int(center[1]))


def _press(controller, key):
    controller.handle_event(KeyboardEvent(KeyboardEventType.KEY_UP, key))


def _click(controller, point):
    controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, point))


def _canonical_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _checkpoint_bytes(env):
    return _canonical_bytes(canonical_checkpoint(env))


def _apply(env, action):
    _, _, _, info = env.step(action, dt_ms=0)
    if not info["action_ok"]:
        raise AssertionError(f"scenario action was rejected: {action!r}")


def _line_env(seed, dt_ms=_LOCKSTEP_DT_MS):
    env = MiniMetroEnv(dt_ms=dt_ms)
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    _apply(env, {"type": "attach_carriage", "path_index": 0})
    for _ in range(40):
        env.step({"type": "noop"})
    return env


def _wrap(loaded, control):
    wrapped = MiniMetroEnv(dt_ms=control.dt_ms_default, reward_mode=control.reward_mode)
    wrapped.mediator = loaded
    wrapped.last_deliveries = control.last_deliveries
    wrapped.last_line_credits = control.last_line_credits
    wrapped.last_score = control.last_score
    return wrapped


class _RecSession:
    def __init__(self, mediator):
        self.mediator = mediator

    def dispatch(self, event):
        pass


class _FileAutosave:
    """A real seam that routes save/delete/peek/load through a private file."""

    def __init__(self, path):
        self.path = Path(path)

    def save(self, mediator):
        save_game(mediator, self.path)

    def delete(self):
        self.path.unlink(missing_ok=True)

    def peek(self):
        return self.path.exists()

    def load(self):
        return load_game(self.path)


def _title_build_game(map_id="classic", mediator=None):
    subject = Mediator(seed=0) if mediator is None else mediator
    return subject, SimpleNamespace(), _RecSession(subject)


def _identity_build_from(mediator):
    return mediator, SimpleNamespace(), _RecSession(mediator)


class TestGM07cContinueRoundtrip(unittest.TestCase):
    def _play_and_autosave(self, seed, autosave):
        env = _line_env(seed)
        controller = _continue_controller(
            self,
            lambda map_id="classic": (
                env.mediator,
                SimpleNamespace(),
                _RecSession(env.mediator),
            ),
            start_state=_screen(self, "PLAYING"),
            build_from=_identity_build_from,
            autosave=autosave,
        )
        _press(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, _screen(self, "PAUSE_MENU"))
        self.assertTrue(autosave.peek(), "menu entry must autosave the boundary")
        return env, controller

    def test_autosave_file_roundtrips_to_the_saved_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            autosave = _FileAutosave(Path(directory) / "autosave.json")
            env, _controller = self._play_and_autosave(7411, autosave)
            boundary = _checkpoint_bytes(env)
            loaded = _wrap(load_game(autosave.path), env)
            self.assertEqual(
                _checkpoint_bytes(loaded),
                boundary,
                "the autosave file must reload checkpoint-identical to the boundary",
            )

    def test_continue_resumes_in_lockstep_with_a_never_exited_control(self):
        with tempfile.TemporaryDirectory() as directory:
            autosave = _FileAutosave(Path(directory) / "autosave.json")
            env, _controller = self._play_and_autosave(7412, autosave)

            resumer = _continue_controller(
                self,
                _title_build_game,
                start_state=_screen(self, "TITLE"),
                build_from=_identity_build_from,
                autosave=autosave,
            )
            _click(resumer, _continue_center(self))
            self.assertEqual(resumer.state, _screen(self, "PLAYING"))
            continued = _wrap(resumer.mediator, env)

            # The never-exited control resumes by releasing the menu reason;
            # the continued game released it inside Continue.
            env.mediator.release_pause_reason("menu")
            self.assertEqual(
                _checkpoint_bytes(continued),
                _checkpoint_bytes(env),
                "the continued game matches the control at the resume boundary",
            )
            for tick in range(8):
                env.step({"type": "noop"}, dt_ms=_LOCKSTEP_DT_MS)
                continued.step({"type": "noop"}, dt_ms=_LOCKSTEP_DT_MS)
                self.assertEqual(
                    _checkpoint_bytes(continued),
                    _checkpoint_bytes(env),
                    f"the continued game diverged from the control at tick {tick}",
                )

    def test_game_over_delete_makes_continue_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            autosave = _FileAutosave(Path(directory) / "autosave.json")
            env, controller = self._play_and_autosave(7413, autosave)
            _press(controller, pygame.K_ESCAPE)  # resume to PLAYING
            self.assertEqual(controller.state, _screen(self, "PLAYING"))

            env.mediator.is_game_over = True
            _press(controller, pygame.K_SPACE)  # promotion deletes the autosave
            self.assertEqual(controller.state, _screen(self, "GAME_OVER"))
            self.assertFalse(autosave.peek(), "game over must delete the autosave")

            resumer = _continue_controller(
                self,
                _title_build_game,
                start_state=_screen(self, "TITLE"),
                build_from=_identity_build_from,
                autosave=autosave,
            )
            before = resumer.mediator
            _click(resumer, _continue_center(self))
            self.assertEqual(resumer.state, _screen(self, "TITLE"))
            self.assertIs(
                resumer.mediator, before, "a deleted autosave leaves Continue inert"
            )


if __name__ == "__main__":
    unittest.main()
