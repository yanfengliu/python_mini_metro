# GM-10e/f/g — diff (code + tests)

The three filled offer arms + their tests. Docs (README/GAME_RULES/ARCHITECTURE/PROGRESS/DECISIONS) omitted here.

```diff
diff --git a/src/weekly_offers.py b/src/weekly_offers.py
index ca1a356..dc3a4ef 100644
--- a/src/weekly_offers.py
+++ b/src/weekly_offers.py
@@ -70,19 +70,23 @@ class WeeklyOffers:
         host.release_pause_reason(WEEK_REASON)

     def apply_offer(self, host: object, offer: Offer) -> None:
-        # Dispatch the chosen offer to its per-kind effect. NEW_LINE grants a free line
-        # (GM-10d); the locomotive/carriage/tunnel arms are still no-op stubs
-        # (GM-10e/f/g) -- their effects need GM-10h persistence, so they change no state
-        # yet. A future kind without a handler must fail loud.
+        # Dispatch the chosen offer to its per-kind effect. Each grows a fleet/tunnel
+        # quantity by one; the derived readouts (available_locomotives/available_carriages/
+        # num_tunnels/available_tunnels) update for free (no cache to refresh, unlike
+        # NEW_LINE's button locks), and all four persist via the GM-10h save-schema v3
+        # (D-045: grown fleet TOTALS + tunnel_bonus). A future kind without a handler
+        # must fail loud.
         match offer.kind:
             case OfferKind.NEW_LINE:
                 host._grant_free_line()  # GM-10d
             case OfferKind.LOCOMOTIVE:
-                pass  # GM-10e: +1 num_metros (needs _require_running_config relaxed / GM-10h)
+                host.num_metros += 1  # GM-10e
             case OfferKind.CARRIAGE:
-                pass  # GM-10f: +1 num_carriages (same pin as locomotives)
+                host.num_carriages += 1  # GM-10f
             case OfferKind.TUNNEL:
-                pass  # GM-10g: +1 tunnel budget (needs a persisted bonus / GM-10h)
+                # GM-10g: TUNNEL is offered only on a bounded map (the pool excludes it
+                # on CLASSIC), so the bonus is always reachable when this arm runs.
+                host.tunnel_bonus += 1
             case _:
                 raise ValueError(f"no effect handler for offer kind {offer.kind!r}")

diff --git a/test/test_gm10c_choice.py b/test/test_gm10c_choice.py
index 60f3e3b..9baa181 100644
--- a/test/test_gm10c_choice.py
+++ b/test/test_gm10c_choice.py
@@ -3,9 +3,10 @@
 The GM-10b read-only offer preview becomes interactive: the modal shows one button
 per offer; an armed down->up on a button chooses that offer, and
 `Mediator.resolve_week_boundary(offer)` applies it (via a per-kind dispatch) then
-clears + releases the week pause. The per-kind EFFECTS are GM-10d-g -- in GM-10c the
-dispatch arms are no-op stubs, so choosing changes NO game state and is Continue-safe
-with no new persisted bytes.
+clears + releases the week pause. This file pins the CONTROLS (arming, routing
+offer_i -> current_offers[i], the confinement guard, apply->clear->release order);
+the per-kind EFFECTS themselves are GM-10d-g (tested in test_gm10d_line.py and
+test_gm10efg_effects.py).
 """

 from __future__ import annotations
@@ -27,34 +28,10 @@ from event.type import MouseEventType
 from geometry.point import Point
 from mediator import Mediator
 from offers import OfferKind, describe
-from save_game import serialize_game
 from ui.menu_screens import draw_offer_screen, offer_menu_layout

 pygame.init()

-_INERT_ATTRS = (
-    "deliveries",
-    "line_credits",
-    "num_metros",
-    "num_carriages",
-    "available_locomotives",
-    "available_carriages",
-    "purchased_num_paths",
-    "unlocked_num_paths",
-    "unlocked_num_stations",
-    "num_tunnels",
-    "consumed_tunnels",
-    # non-serialized RUNTIME state (review MAJOR: not in serialize_game, so a save-doc
-    # check alone would miss a mutation touching these):
-    "current_offers",
-    "week_calendar",
-    "is_paused",
-    "is_game_over",
-    "steps",
-    "time_ms",
-    "game_speed_multiplier",
-)
-

 class _ChoiceSession:
     def __init__(self):
@@ -215,25 +192,9 @@ class TestGM10cApplyOffer(unittest.TestCase):
         self.assertEqual(m.current_offers, ())
         self.assertFalse(m.is_week_boundary_pending)

-    def test_applying_a_stub_offer_kind_is_state_inert(self):
-        # The still-STUB kinds (GM-10e/f/g: locomotive/carriage/tunnel) must change NO
-        # game state and no serialized byte. review MAJOR: check PER-KIND on a FRESH
-        # mediator (so compensating cross-kind mutations cannot cancel) and over runtime
-        # state beyond the save doc. (NEW_LINE now grants a line -- GM-10d, tested in
-        # test_gm10d_line.py.) A real effect on a stub kind turns red.
-        stub_kinds = (OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE, OfferKind.TUNNEL)
-        for kind in stub_kinds:
-            m = Mediator(seed=0)
-            for _ in range(300):
-                m.increment_time(17)
-            before = {attr: getattr(m, attr) for attr in _INERT_ATTRS}
-            before_doc = serialize_game(m)
-            m._apply_offer(describe(kind))
-            after = {attr: getattr(m, attr) for attr in _INERT_ATTRS}
-            self.assertEqual(after, before, f"{kind.name} apply moved runtime state")
-            self.assertEqual(
-                serialize_game(m), before_doc, f"{kind.name} apply moved a save byte"
-            )
+    # (The GM-10c-era "the stub kinds are state-inert" test was RETIRED in GM-10e/f/g,
+    # which filled the LOCOMOTIVE/CARRIAGE/TUNNEL arms -- no kind is a no-op stub now.
+    # Each effect's growth + CONTAINMENT is pinned in test_gm10efg_effects.py.)

     def test_apply_offer_handles_every_kind(self):
         m = Mediator(seed=0)
diff --git a/test/test_gm10d_line.py b/test/test_gm10d_line.py
index dea435c..3d2993d 100644
--- a/test/test_gm10d_line.py
+++ b/test/test_gm10d_line.py
@@ -2,9 +2,10 @@

 Picking the NEW_LINE week-boundary offer unlocks the next metro line for free (no
 credit spend), capped at num_paths. It is the FIRST real per-kind offer effect;
-locomotive/carriage/tunnel stay stub no-ops (GM-10e/f/g). The grant flows through
-the already-persisted purchased_num_paths, so it is Continue-exact with no schema
-change (D-043/D-044); RL/headless never reach it (offers gated to the human shell).
+locomotive/carriage/tunnel later grow the fleet/tunnel budget instead (GM-10e/f/g),
+so only NEW_LINE unlocks a line. The grant flows through the already-persisted
+purchased_num_paths, so it is Continue-exact with no schema change (D-043/D-044);
+RL/headless never reach it (offers gated to the human shell).
 """

 from __future__ import annotations
@@ -152,9 +153,10 @@ class TestGM10dApplyNewLine(unittest.TestCase):
             p.resolve_week_boundary(offered)
         self.assertTrue(p.is_week_boundary_pending, "rejected -- boundary still held")

-    def test_the_other_offer_kinds_still_grant_nothing(self):
-        # LOCOMOTIVE/CARRIAGE/TUNNEL are GM-10e/f/g -- still no-op, so they do not
-        # unlock a line (only NEW_LINE does).
+    def test_non_line_offer_kinds_do_not_unlock_a_line(self):
+        # LOCOMOTIVE/CARRIAGE/TUNNEL grow the fleet/tunnel budget (GM-10e/f/g), NOT the
+        # line count -- only NEW_LINE unlocks a line. (Their own growth+containment is
+        # pinned in test_gm10efg_effects.py.)
         for kind in (OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE, OfferKind.TUNNEL):
             m = Mediator(seed=0)
             before = m.unlocked_num_paths
```

## New file: test/test_gm10efg_effects.py
```python
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
```
