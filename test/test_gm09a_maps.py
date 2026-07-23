"""GM-09a red contract: the ``Classic`` map abstraction (D-032).

Two things at once:

* NEW API (red until implemented): a data-only immutable ``MapDefinition``, the
  ``CLASSIC`` definition, a version-aware ``resolve_map`` lookup, the
  ``get_random_stations`` map-parameterization, and a save fail-closed guard.
* BEHAVIOR-PRESERVATION (regression locks, green now → must stay green): the
  Classic map must reproduce the pre-change deterministic construction AND
  trajectory byte-for-byte. The fingerprints below were captured from the
  pre-change code and are PYTHONHASHSEED-stable (ID-free station projection +
  path colors + both RNG states + a stepped trajectory — station and color
  draws share one ``python_random`` stream, so an off-by-one anywhere shifts
  these).
"""

from __future__ import annotations

import hashlib
import importlib
import os
import subprocess
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import (
    screen_height,
    screen_width,
    station_shape_type_list,
    station_unique_shape_type_list,
    station_unique_spawn_chance,
    station_unique_spawn_start_index,
)
from game_session import GameSession
from mediator import Mediator
from rendering.game_renderer import GameRenderer

# Pre-change fingerprints (captured from the current code; PYTHONHASHSEED-stable).
_CONSTRUCT_FP = {0: "f6d2bee9a40b4ba1", 1: "b7ca00b3088be0ec"}
_TRAJ_FP = {0: "b98dcd7043a525d7", 1: "53f13c55d4e5b448"}

MODULE = "maps"


def _module(tc):
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        tc.fail(f"GM-09a product module missing: {MODULE} ({error})")


def _sym(tc, name):
    value = getattr(_module(tc), name, None)
    tc.assertIsNotNone(value, f"GM-09a product symbol missing: {MODULE}.{name}")
    return value


def _sha(obj) -> str:
    return hashlib.sha256(repr(obj).encode()).hexdigest()[:16]


def _construct_fp(m) -> str:
    stations = [
        (type(s.shape).__name__, round(s.position.left, 4), round(s.position.top, 4))
        for s in m.all_stations
    ]
    colors = list(m.path_colors.keys())
    return _sha(
        (
            stations,
            colors,
            _sha(m.context.python_random.getstate()),
            _sha(m.context.numpy_random.bit_generator.state),
        )
    )


def _traj_fp(m, surface) -> str:
    renderer = GameRenderer()
    session = GameSession(m, step_observer=renderer)
    session.prepare_layout(surface)
    for _ in range(300):
        session.advance(16)
    traj = (
        m.deliveries,
        m.steps,
        len(m.passengers),
        [len(st.passengers) for st in m.stations],
        _sha(m.context.python_random.getstate()),
    )
    return _sha(traj)


class TestGM09aDeterminismParity(unittest.TestCase):
    """Load-bearing: the Classic map must not perturb any RNG draw."""

    def test_construction_matches_pre_change(self):
        for seed, fp in _CONSTRUCT_FP.items():
            self.assertEqual(
                _construct_fp(Mediator(seed=seed)),
                fp,
                f"seed {seed} construction (stations/colors/RNG) changed vs pre-change",
            )

    def test_trajectory_matches_pre_change(self):
        surface = pygame.Surface((screen_width, screen_height))
        for seed, fp in _TRAJ_FP.items():
            self.assertEqual(
                _traj_fp(Mediator(seed=seed), surface),
                fp,
                f"seed {seed} 300-step trajectory changed vs pre-change",
            )

    def test_fingerprinted_seeds_exercise_the_unique_shape_path(self):
        # The regression lock only proves what its seeds exercise. Assert that a
        # fingerprinted seed actually reaches the unique-shape spawn branch (idx >=
        # start, chance hit), so a future config change that stopped it would fail
        # HERE loudly rather than silently weakening the byte-identity proof
        # (review NIT). (seed 1 additionally exercises the pool-retry loop.)
        unique_names = {"Diamond", "Pentagon", "Star"}
        seen_unique = any(
            type(s.shape).__name__ in unique_names
            for seed in _CONSTRUCT_FP
            for s in Mediator(seed=seed).all_stations
        )
        self.assertTrue(
            seen_unique, "no fingerprinted seed reaches the unique-shape path"
        )


class TestGM09aMapDefinition(unittest.TestCase):
    def test_classic_identity_and_version(self):
        classic = _sym(self, "CLASSIC")
        self.assertEqual(classic.map_id, "classic")
        self.assertEqual(classic.map_definition_version, 1)

    def test_classic_shape_params_equal_config_as_tuples(self):
        classic = _sym(self, "CLASSIC")
        # Ordered TUPLES (a frozen dataclass over the live mutable config lists is
        # not actually immutable — review), value-equal to the current config.
        self.assertEqual(tuple(classic.shape_types), tuple(station_shape_type_list))
        self.assertEqual(
            tuple(classic.unique_shape_types), tuple(station_unique_shape_type_list)
        )
        self.assertIsInstance(classic.shape_types, tuple)
        self.assertIsInstance(classic.unique_shape_types, tuple)
        self.assertEqual(
            classic.unique_spawn_start_index, station_unique_spawn_start_index
        )
        self.assertEqual(classic.unique_spawn_chance, station_unique_spawn_chance)

    def test_map_definition_is_immutable(self):
        classic = _sym(self, "CLASSIC")
        with self.assertRaises(Exception):
            classic.map_id = "river"  # frozen


class TestGM09aResolveMap(unittest.TestCase):
    def test_resolve_classic_pair_returns_classic(self):
        resolve = _sym(self, "resolve_map")
        classic = _sym(self, "CLASSIC")
        self.assertIs(resolve("classic", 1), classic)

    def test_resolve_unknown_id_raises_a_named_error(self):
        resolve = _sym(self, "resolve_map")
        with self.assertRaises(Exception) as ctx:
            resolve("atlantis", 1)
        self.assertIn("atlantis", str(ctx.exception), "the bad map id is named")

    def test_resolve_wrong_version_raises_a_named_error(self):
        resolve = _sym(self, "resolve_map")
        with self.assertRaises(Exception) as ctx:
            resolve("classic", 2)
        msg = str(ctx.exception)
        self.assertIn("classic", msg)
        self.assertIn("2", msg, "the unsupported version is named")


class TestGM09aStationParameterization(unittest.TestCase):
    def test_explicit_classic_params_equal_the_config_defaults(self):
        from entity.get_entity import get_random_stations
        from simulation_context import SimulationContext

        classic = _sym(self, "CLASSIC")

        def project(stations):
            return [
                (
                    type(s.shape).__name__,
                    round(s.position.left, 4),
                    round(s.position.top, 4),
                )
                for s in stations
            ]

        default = project(get_random_stations(20, context=SimulationContext(7)))
        explicit = project(
            get_random_stations(
                20,
                context=SimulationContext(7),
                shape_types=classic.shape_types,
                unique_shape_types=classic.unique_shape_types,
                unique_spawn_start_index=classic.unique_spawn_start_index,
                unique_spawn_chance=classic.unique_spawn_chance,
            )
        )
        self.assertEqual(default, explicit, "Classic params reproduce the default draw")


class TestGM09aImportSafety(unittest.TestCase):
    def test_maps_pulls_no_gameplay_or_pygame(self):
        # maps.py must be data-only (review Codex-8): importing it must NOT pull
        # pygame, mediator, or the entity graph, so it stays import-safe for RL.
        code = (
            "import sys; sys.path.insert(0, 'src'); import maps; "
            "bad=[m for m in ('pygame','mediator','entity.station','entity.metro') "
            "if m in sys.modules]; "
            "print('LEAK' if bad else 'CLEAN', bad)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.realpath(__file__)) + "/..",
        )
        self.assertIn(
            "CLEAN",
            result.stdout,
            f"maps leaked imports: {result.stdout}{result.stderr}",
        )


class TestGM09aSaveGuard(unittest.TestCase):
    def test_serialize_rejects_a_non_classic_map(self):
        # Fail-closed (review Codex-7): until the save schema carries map identity,
        # a save-capable Mediator must be serializable ONLY as classic@1, so a
        # future non-Classic map can never be silently written as Classic.
        from save_game import serialize_game

        map_def_cls = _sym(self, "MapDefinition")
        classic = _sym(self, "CLASSIC")
        m = Mediator(seed=0)
        # Classic serializes fine.
        serialize_game(m)
        # A non-Classic definition must be rejected with a clear, named error.
        m.map_definition = map_def_cls(
            map_id="river",
            map_definition_version=1,
            shape_types=classic.shape_types,
            unique_shape_types=classic.unique_shape_types,
            unique_spawn_start_index=classic.unique_spawn_start_index,
            unique_spawn_chance=classic.unique_spawn_chance,
        )
        with self.assertRaises(Exception) as ctx:
            serialize_game(m)
        self.assertIn("river", str(ctx.exception), "the offending map id is named")


if __name__ == "__main__":
    unittest.main()
