"""GM-10h contract: fleet/tunnel upgrade-bonus persistence (save/Continue) (D-045).

A weekly LOCOMOTIVE/CARRIAGE upgrade grows `num_metros`/`num_carriages` (fleet TOTALS);
a TUNNEL upgrade adds a persisted `tunnel_bonus` to the map budget. GM-10h makes these
survive save/load via an additive save-schema v3:
- v3 adds one key, `tunnelBonus`; the fleet is persisted as its GROWN totals (no bonus
  field), and the running-config pin is v3-relaxed to `>= config`.
- `serialize_game` rejects a desynced/forged upgrade state BEFORE the atomic write, so a
  bad state can never clobber a valid autosave (load-time rejection is too late).
- `within_tunnel_budget` folds the bonus, so a tunnel upgrade actually UNBLOCKS a crossing.
- v1/v2 saves stay byte-frozen and load with a 0 bonus. The effects (GM-10e/f/g) are still
  stubs; these tests drive DIRECTLY-SET grown state.
"""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import num_carriages as CONFIG_NUM_CARRIAGES
from config import num_metros as CONFIG_NUM_METROS
from crossings import within_tunnel_budget
from env import MiniMetroEnv
from geometry.point import Point
from maps import resolve_map
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from rl.player_env import PlayerPixelEnv
from save_game import serialize_game
from save_load import deserialize_game

pygame.init()

_FIXTURES = os.path.dirname(os.path.realpath(__file__)) + "/../scripts/fixtures"


def _played(seed=0, map_definition=None):
    kwargs = {"seed": seed}
    if map_definition is not None:
        kwargs["map_definition"] = map_definition
    m = Mediator(**kwargs)
    for _ in range(200):
        m.increment_time(17)
    return m


class TestGM10hFleetPersistence(unittest.TestCase):
    def test_grown_fleet_round_trips(self):
        m = _played()
        m.num_metros = CONFIG_NUM_METROS + 1
        m.num_carriages = CONFIG_NUM_CARRIAGES + 2
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(loaded.num_metros, CONFIG_NUM_METROS + 1)
        self.assertEqual(loaded.num_carriages, CONFIG_NUM_CARRIAGES + 2)

    def test_serialize_rejects_a_fleet_below_config_before_writing(self):
        # BLOCKER-1: a below-config total is corrupt; serialize must reject it BEFORE
        # the atomic write, or it would clobber a valid autosave with an unloadable one.
        m = _played()
        m.num_metros = CONFIG_NUM_METROS - 1
        with self.assertRaisesRegex(ValueError, "below the running config"):
            serialize_game(m)

    def test_a_forged_high_fleet_total_loads_authoritatively(self):
        # DECISION (D-045): fleet totals are authoritative editable state -- a forged
        # high total loads (like a forged `deliveries`/`score`), matching the threat
        # model. The relaxed v3 pin accepts numMetros >= config.
        m = _played()
        m.num_metros = 99
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(loaded.num_metros, 99)


class TestGM10hTunnelPersistence(unittest.TestCase):
    def test_tunnel_bonus_round_trips_and_grows_num_tunnels(self):
        r = _played(map_definition=resolve_map("river", 1))
        r.tunnel_bonus = 2
        self.assertEqual(r.num_tunnels, 3 + 2, "num_tunnels folds the bonus")
        loaded = deserialize_game(serialize_game(r))
        self.assertEqual(loaded.tunnel_bonus, 2)
        self.assertEqual(loaded.num_tunnels, 5)

    def test_the_bonus_unblocks_a_real_over_budget_crossing(self):
        # The LOAD-BEARING trap: within_tunnel_budget reads the map budget DIRECTLY, so
        # the bonus must be folded THERE. A candidate crossing RIVER 4x is over budget 3
        # but fits budget 3+2. Proves the bonus UNBLOCKS the crossing, not just the count.
        river = resolve_map("river", 1)
        band = river.rivers[0]
        y = (band[1] + band[3]) / 2
        left, right = band[0] - 100, band[2] + 100

        def stn(x):
            return SimpleNamespace(position=Point(x, y))

        route = [stn(left), stn(right), stn(left), stn(right), stn(left)]  # 4 crossings
        no_bonus = SimpleNamespace(map_definition=river, paths=(), tunnel_bonus=0)
        bonus = SimpleNamespace(map_definition=river, paths=(), tunnel_bonus=2)
        self.assertFalse(
            within_tunnel_budget(no_bonus, route, False), "4 crossings > budget 3"
        )
        self.assertTrue(
            within_tunnel_budget(bonus, route, False), "bonus 2 lifts the budget to 5"
        )

    def test_serialize_and_load_reject_a_tunnel_bonus_on_an_unbounded_map(self):
        # A nonzero bonus is unreachable on CLASSIC (never offers TUNNEL; num_tunnels
        # stays None). Both save surfaces reject it.
        c = _played()
        c.tunnel_bonus = 1
        self.assertIsNone(c.num_tunnels, "the bonus is ignored on an unbounded map")
        with self.assertRaisesRegex(ValueError, "unbounded-tunnel map"):
            serialize_game(c)


class TestGM10hSchemaAndBackwardCompat(unittest.TestCase):
    def test_fresh_save_is_v4_with_a_zero_bonus(self):
        # GM-10i bumped the current version to v4; a fresh (non-boundary) save carries a
        # zero tunnel bonus AND an empty pendingOffers.
        doc = serialize_game(_played())
        self.assertEqual(doc["schemaVersion"], 4)
        self.assertEqual(doc["tunnelBonus"], 0)
        self.assertEqual(doc["pendingOffers"], [])

    def test_v1_and_v2_fixtures_deserialize_with_a_zero_bonus(self):
        # review MINOR-5: DESERIALIZE (runs _require_running_config), not just validate.
        for name in ("save-v1.json", "save-v2-classic.json"):
            from save_game import load_game

            loaded = load_game(f"{_FIXTURES}/{name}")
            self.assertEqual(loaded.tunnel_bonus, 0, f"{name} loads a 0 bonus")
            self.assertEqual(loaded.num_metros, CONFIG_NUM_METROS)

    def test_a_v3_document_missing_the_bonus_key_is_rejected(self):
        from save_schema import validate_save

        doc = serialize_game(_played())
        doc["schemaVersion"] = 3  # native v3 (down-convert: a fresh save is now v4)
        del doc["pendingOffers"]
        del doc["tunnelBonus"]  # a v3 doc MUST carry it
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_a_v2_document_carrying_the_bonus_key_is_rejected(self):
        from save_schema import validate_save

        doc = serialize_game(_played())
        doc["schemaVersion"] = 2  # a v2 doc must NOT carry tunnelBonus
        del doc["pendingOffers"]  # strip the v4 key so tunnelBonus is the sole fault
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_the_map_identity_gate_still_fires_on_a_v3_document(self):
        from save_schema import validate_save

        doc = serialize_game(_played())
        doc["schemaVersion"] = 3  # native v3 (down-convert)
        del doc["pendingOffers"]
        doc["mapId"] = "river "  # forged: whitespace -- must still be rejected on v3
        with self.assertRaises(ValueError):
            validate_save(doc)


class TestGM10hStateLegality(unittest.TestCase):
    def test_load_legality_uses_the_bonus_aware_budget(self):
        # review MINOR: _require_legal_map_state must compare consumed crossings against
        # the BONUS-AWARE num_tunnels, not the raw map budget. A synthetic host whose
        # consumed count falls in (budget, budget+bonus] is legal WITH the bonus, and a
        # raw-budget mutant would wrongly reject it. (A full committed-crossing round-trip
        # needs many delivery-unlocked stations; it lands with the TUNNEL effect in
        # GM-10g -- D-045. This pins the load-legality math now.)
        from save_load import _require_legal_map_state

        river = resolve_map("river", 1)  # budget 3
        legal = SimpleNamespace(
            num_tunnels=5, consumed_tunnels=4, all_stations=[], tunnel_bonus=2
        )
        _require_legal_map_state(
            legal, river
        )  # 4 <= 5: no raise (raw budget 3 rejects)
        over = SimpleNamespace(
            num_tunnels=5, consumed_tunnels=6, all_stations=[], tunnel_bonus=2
        )
        with self.assertRaisesRegex(ValueError, "exceed the map's tunnel budget"):
            _require_legal_map_state(over, river)

    def test_load_rejects_a_forged_tunnel_bonus_on_an_unbounded_map(self):
        # A forged v3 doc bypasses the serialize-time guard, so the post-LOAD legality
        # check (_require_legal_map_state) must ALSO reject a nonzero bonus on an
        # unbounded (CLASSIC) map -- both save surfaces agree.
        doc = serialize_game(_played())  # CLASSIC, tunnelBonus 0, valid
        doc["tunnelBonus"] = 3  # forge a nonzero bonus on an unbounded map
        with self.assertRaisesRegex(ValueError, "unreachable on an unbounded"):
            deserialize_game(doc)


class TestGM10hRLUnaffected(unittest.TestCase):
    def test_headless_env_keeps_config_fleet_and_zero_bonus(self):
        env = MiniMetroEnv()
        env.reset(seed=0)
        for _ in range(1200 + 60):
            env.mediator.step_time(17)
        self.assertEqual(env.mediator.num_metros, CONFIG_NUM_METROS)
        self.assertEqual(env.mediator.num_carriages, CONFIG_NUM_CARRIAGES)
        self.assertEqual(env.mediator.tunnel_bonus, 0)

    def test_pixel_env_keeps_a_zero_bonus(self):
        env = PlayerPixelEnv()
        env.reset(seed=0)
        self.assertEqual(env._mediator.tunnel_bonus, 0)

    def test_the_checkpoint_carries_no_bonus_and_config_fleet(self):
        # No checkpoint schema change (BLOCKER-2 scoping): a bonus is absorbed into the
        # fleet totals and the RL path never applies an offer, so the checkpoint has no
        # tunnel/bonus key and records the config fleet.
        import json

        env = MiniMetroEnv()
        env.reset(seed=0)
        checkpoint = canonical_checkpoint(env)
        # No tunnel/bonus state anywhere in the canonical checkpoint (it drops the
        # tunnels observation block, and the RL path never applies an offer).
        self.assertNotIn("tunnel", json.dumps(checkpoint).lower())
        self.assertEqual(
            checkpoint["progression"]["limits"]["num_metros"], CONFIG_NUM_METROS
        )


if __name__ == "__main__":
    unittest.main()
