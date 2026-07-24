"""GM-10e/f/g contract: the fleet/tunnel weekly-upgrade EFFECTS.

The last three per-kind offer arms, filled on the GM-10h (D-045) persistence
infrastructure. Choosing LOCOMOTIVE/CARRIAGE/TUNNEL grows `num_metros`/
`num_carriages`/`tunnel_bonus` by one; the derived readouts update for free and the
grown state persists via save-schema v3 (Continue-exact) with no further schema
work. TUNNEL is offered only on a bounded map, so its bonus is always reachable.
"""

from __future__ import annotations

import os
import random
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
from offers import OfferKind, describe, generate_offers
from save_game import serialize_game
from save_load import deserialize_game

pygame.init()


def _at_boundary(seed=0, map_definition=None):
    kwargs = {"seed": seed}
    if map_definition is not None:
        kwargs["map_definition"] = map_definition
    m = Mediator(**kwargs)
    m.week_calendar = True
    guard = 0
    while not m.is_week_boundary_pending and guard < 5000:
        m.increment_time(17)
        guard += 1
    return m


def _choose(mediator, kind):
    # Present the kind explicitly (RNG-independent) + satisfy the confinement guard,
    # then resolve with it -- the full human apply path.
    offer = describe(kind)
    mediator.current_offers = (offer,)
    mediator.resolve_week_boundary(offer)


def _unserved_path(mediator, indices=(0, 1)):
    # A completed but unassigned path on a fresh mediator, so fleet/carriage capacity is
    # spent only by our explicit assignments (mirrors test_gm06b's helper).
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()
    path = mediator.create_path_from_station_indices(list(indices))
    if path is None:
        raise AssertionError("test setup could not create a path")
    for metro in tuple(path.metros):
        while metro in mediator.metros:
            mediator.metros.remove(metro)
    path.metros.clear()
    return path


class TestGM10eLocomotive(unittest.TestCase):
    def test_choosing_locomotive_grows_the_fleet_and_persists(self):
        m = _at_boundary()
        _choose(m, OfferKind.LOCOMOTIVE)
        self.assertEqual(m.num_metros, CONFIG_NUM_METROS + 1)
        self.assertEqual(
            m.available_locomotives, CONFIG_NUM_METROS + 1, "one more unassigned loco"
        )
        # CONTAINMENT: it touches ONLY the fleet total, not carriages or the tunnel bonus.
        self.assertEqual(m.num_carriages, CONFIG_NUM_CARRIAGES, "carriages untouched")
        self.assertEqual(m.tunnel_bonus, 0, "tunnel bonus untouched")
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(loaded.num_metros, CONFIG_NUM_METROS + 1, "Continue-exact")


class TestGM10fCarriage(unittest.TestCase):
    def test_choosing_carriage_grows_the_fleet_and_persists(self):
        m = _at_boundary()
        _choose(m, OfferKind.CARRIAGE)
        self.assertEqual(m.num_carriages, CONFIG_NUM_CARRIAGES + 1)
        self.assertEqual(m.available_carriages, CONFIG_NUM_CARRIAGES + 1)
        self.assertEqual(m.num_metros, CONFIG_NUM_METROS, "fleet locos untouched")
        self.assertEqual(m.tunnel_bonus, 0, "tunnel bonus untouched")
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(
            loaded.num_carriages, CONFIG_NUM_CARRIAGES + 1, "Continue-exact"
        )


class TestGM10gTunnel(unittest.TestCase):
    def test_choosing_tunnel_on_a_bounded_map_grows_the_budget_and_persists(self):
        r = _at_boundary(map_definition=resolve_map("river", 1))
        before_available = r.available_tunnels  # remaining budget the UI shows
        _choose(r, OfferKind.TUNNEL)
        self.assertEqual(r.tunnel_bonus, 1)
        self.assertEqual(r.num_tunnels, 3 + 1, "budget 3 + the bonus")
        # review MINOR: the derived REMAINING readout must honor the bonus too -- a
        # readout that folded num_tunnels but not the bonus would leave this unchanged.
        self.assertEqual(
            r.available_tunnels, before_available + 1, "one more tunnel available"
        )
        self.assertEqual(r.num_metros, CONFIG_NUM_METROS, "fleet untouched")
        self.assertEqual(r.num_carriages, CONFIG_NUM_CARRIAGES, "carriages untouched")
        loaded = deserialize_game(serialize_game(r))
        self.assertEqual(loaded.tunnel_bonus, 1)
        self.assertEqual(loaded.num_tunnels, 4, "Continue-exact")

    def test_the_applied_tunnel_bonus_unblocks_a_real_crossing(self):
        # The full apply->persist->UNBLOCK path on the real mediator: after a TUNNEL
        # upgrade, a route crossing RIVER 4x (over the base budget 3) now fits budget 4.
        r = _at_boundary(map_definition=resolve_map("river", 1))
        _choose(r, OfferKind.TUNNEL)  # tunnel_bonus 1 -> num_tunnels 4
        band = r.map_definition.rivers[0]
        yy = (band[1] + band[3]) / 2
        left, right = band[0] - 100, band[2] + 100

        def stn(x):
            return SimpleNamespace(position=Point(x, yy))

        route = [stn(left), stn(right), stn(left), stn(right), stn(left)]  # 4 crossings
        self.assertTrue(
            within_tunnel_budget(r, route, False),
            "the applied +1 tunnel lifts the real gate's budget to 4",
        )


class TestGM10efgContainment(unittest.TestCase):
    def test_each_effect_changes_only_its_own_save_field(self):
        # review LOW: pin containment against the FULL serialize_game doc, not just the
        # other two upgrade quantities -- an arm that ALSO bumped line_credits/deliveries/
        # etc. would survive the per-test containment checks. Apply each kind directly and
        # assert the save doc differs in EXACTLY the one expected key.
        cases = (
            (OfferKind.LOCOMOTIVE, "numMetros", None),
            (OfferKind.CARRIAGE, "numCarriages", None),
            (OfferKind.TUNNEL, "tunnelBonus", resolve_map("river", 1)),
        )
        for kind, changed_key, map_def in cases:
            kwargs = {"seed": 0}
            if map_def is not None:
                kwargs["map_definition"] = map_def
            m = Mediator(**kwargs)
            for _ in range(200):
                m.increment_time(17)
            before = serialize_game(m)
            m._apply_offer(describe(kind))
            after = serialize_game(m)
            diff = {k for k in after if before[k] != after[k]}
            self.assertEqual(
                diff, {changed_key}, f"{kind.name} touched only {changed_key}"
            )


class TestGM10efgSlotUsable(unittest.TestCase):
    # review MAJOR: prove the grown total unlocks a genuinely USABLE slot -- a bigger
    # derived count alone would still pass if a consumer clamped assignment/attachment to
    # the original config. Exhaust config capacity, upgrade, then consume exactly one more
    # through the real fleet/carriage paths.
    def test_the_grown_locomotive_total_is_really_assignable(self):
        m = Mediator(seed=6205)
        path = _unserved_path(m)
        for _ in range(CONFIG_NUM_METROS):
            self.assertTrue(m.assign_locomotive(path))
        self.assertEqual(m.available_locomotives, 0)
        self.assertFalse(m.assign_locomotive(path), "fleet exhausted at config")
        m._apply_offer(describe(OfferKind.LOCOMOTIVE))
        self.assertEqual(m.available_locomotives, 1, "the upgrade freed one slot")
        self.assertTrue(
            m.assign_locomotive(path), "the grown total is really assignable"
        )
        self.assertFalse(m.assign_locomotive(path), "and only one more")

    def test_the_grown_carriage_total_is_really_attachable(self):
        m = Mediator(seed=6206)
        path = _unserved_path(m)
        self.assertTrue(m.assign_locomotive(path))  # a metro to attach carriages to
        for _ in range(CONFIG_NUM_CARRIAGES):
            self.assertTrue(m.attach_carriage(path))
        self.assertEqual(m.available_carriages, 0)
        self.assertFalse(m.attach_carriage(path), "carriages exhausted at config")
        m._apply_offer(describe(OfferKind.CARRIAGE))
        self.assertEqual(m.available_carriages, 1, "the upgrade freed one carriage")
        self.assertTrue(m.attach_carriage(path), "the grown total is really attachable")
        self.assertFalse(m.attach_carriage(path), "and only one more")


class TestGM10efgUnbounded(unittest.TestCase):
    def test_tunnel_is_never_offered_on_an_unbounded_map(self):
        # The pool excludes TUNNEL on CLASSIC (num_tunnels is None), so the TUNNEL arm
        # never runs there -- the reason `tunnel_bonus += 1` needs no bounded-map guard.
        kinds = set()
        for s in range(300):
            kinds |= {
                o.kind
                for o in generate_offers(
                    random.Random(s), count=3, tunnels_bounded=False
                )
            }
        self.assertNotIn(OfferKind.TUNNEL, kinds, "CLASSIC never offers TUNNEL")


class TestGM10efgRLUnaffected(unittest.TestCase):
    def test_headless_env_never_applies_an_effect(self):
        env = MiniMetroEnv()
        env.reset(seed=0)
        for _ in range(1200 + 60):
            env.mediator.step_time(17)
        self.assertEqual(env.mediator.num_metros, CONFIG_NUM_METROS)
        self.assertEqual(env.mediator.num_carriages, CONFIG_NUM_CARRIAGES)
        self.assertEqual(env.mediator.tunnel_bonus, 0)


if __name__ == "__main__":
    unittest.main()
