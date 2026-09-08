# GM-10d NEW_LINE offer effect (a free line) + WeeklyOffers extraction — implementation diff

Source: progression.py (grant_free_path: bump purchased_num_paths capped at num_paths, no credit spend), mediator.py (_grant_free_line + NEW_LINE arm + resolve confinement guard; the GM-10a-d week/offer LOGIC factored into the new weekly_offers.py facade so mediator drops 1002->940 lines under the 1000 hard ceiling), weekly_offers.py (NEW: WeeklyOffers facade). Tests: test_gm10d_line.py (NEW) + test_gm10c_choice.py (all-kinds-inert narrowed). Docs: D-044, README, GAME_RULES, ARCHITECTURE, PROGRESS.

## Production source
```diff
diff --git a/src/mediator.py b/src/mediator.py
index 5d06bf4..3dcf1ac 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -1,6 +1,5 @@
 from __future__ import annotations

-import hashlib
 import random
 from typing import Dict, List

@@ -8,7 +7,6 @@ import pygame

 from carriage_management import CarriageManagement
 from config import (
-    OFFERS_PER_WEEK,
     WEEK_LENGTH_STEPS,
     game_over_button_height,
     game_over_button_spacing,
@@ -50,7 +48,7 @@ from graph.graph_algo import bfs, build_station_nodes_dict
 from graph.node import Node
 from input_coordinator import InputCoordinator
 from maps import CLASSIC, MapDefinition
-from offers import Offer, OfferKind, generate_offers
+from offers import Offer
 from passenger_flow import PassengerFlow
 from path_handles import PathEditSelection
 from path_lifecycle import PathLifecycle
@@ -75,14 +73,14 @@ from ui.speed_button import (
     update_speed_button_positions,
 )
 from utils import get_shape_from_type, hue_to_rgb, pick_distinct_hue
+from weekly_offers import WEEK_REASON, WeeklyOffers

 TravelPlans = Dict[Passenger, TravelPlan]

 # "week" (GM-10a / D-041) is the calendar's boundary pause -- held only by the
 # human PLAYING shell (see Mediator.week_calendar) and, unlike "user"/"menu",
 # never cleared by the Space toggle or speed buttons.
-_PAUSE_REASONS = frozenset({"user", "menu", "week"})
-_WEEK_REASON = "week"
+_PAUSE_REASONS = frozenset({"user", "menu", WEEK_REASON})


 def _get_game_renderer_factory():
@@ -175,6 +173,8 @@ class Mediator:
         # -- offers are re-derived Continue-exact from the already-persisted RNG state
         # (see _offer_rng_for_current_week), so no new save/checkpoint bytes.
         self.current_offers: tuple[Offer, ...] = ()
+        # GM-10a-d: the week-boundary hold + offer generate/apply logic (D-023 facade).
+        self._weekly = WeeklyOffers()
         self.game_speed_multiplier = 1
         self.unlocked_num_paths = self.get_unlocked_num_paths()
         self.unlocked_num_stations = self.get_unlocked_num_stations()
@@ -705,46 +705,23 @@ class Mediator:
     @property
     def is_week_boundary_pending(self) -> bool:
         # True while the calendar is paused at a week boundary awaiting a resolve.
-        return _WEEK_REASON in self._pause_reason_store(_WEEK_REASON)
+        return WEEK_REASON in self._pause_reason_store(WEEK_REASON)

+    # The week-boundary hold + offer generate/apply LOGIC lives in the WeeklyOffers
+    # facade (GM-10a-d, D-023); these thin seams keep the public API + the spy points
+    # (a test patching _apply_offer/_grant_free_line/_offer_rng_for_current_week still
+    # intercepts, because the facade invokes them through the host).
     def resolve_week_boundary(self, offer: Offer | None = None) -> None:
-        # Continue past a week boundary: APPLY the chosen offer (GM-10c), then clear
-        # the week's offers and release the pause. A None offer is a forced resolve
-        # with no choice (the window-close path in main.run_game), which applies
-        # nothing. GM-10h reconciles applied-offer persistence across Continue.
-        if offer is not None:
-            self._apply_offer(offer)
-        self.current_offers = ()
-        self.release_pause_reason(_WEEK_REASON)
+        self._weekly.resolve(self, offer)

     def _apply_offer(self, offer: Offer) -> None:
-        # GM-10c dispatches the chosen offer to its per-kind effect. The effects
-        # themselves land in GM-10d-g (line/locomotive/carriage/tunnel) -- each arm
-        # is a no-op here, so GM-10c changes NO game state and is Continue-safe with
-        # no new persisted bytes. A future kind without a handler must fail loud.
-        match offer.kind:
-            case OfferKind.NEW_LINE:
-                pass  # GM-10d: grant a free line (via purchased_num_paths, persisted)
-            case OfferKind.LOCOMOTIVE:
-                pass  # GM-10e: +1 num_metros (needs the _require_running_config pin relaxed / GM-10h)
-            case OfferKind.CARRIAGE:
-                pass  # GM-10f: +1 num_carriages (same pin as locomotives)
-            case OfferKind.TUNNEL:
-                pass  # GM-10g: +1 tunnel budget (needs a persisted bonus / GM-10h)
-            case _:
-                raise ValueError(f"no effect handler for offer kind {offer.kind!r}")
+        self._weekly.apply_offer(self, offer)
+
+    def _grant_free_line(self) -> None:
+        self._weekly.grant_free_line(self)

     def _offer_rng_for_current_week(self) -> random.Random:
-        # GM-10b (D-042): a dedicated per-week offer RNG, derived READ-ONLY from the
-        # already-persisted gameplay RNG state + week_index. `getstate()` consumes no
-        # draws, so the station-spawn stream is byte-untouched; and because that state
-        # is restored exactly on Continue (README "resumes exactly"), the SAME week's
-        # offers reproduce after save/load with NO new persisted state (persistence
-        # proper is GM-10h). repr() of the int-tuple state + sha256 is deterministic
-        # and cross-process stable -- never the PYTHONHASHSEED-salted builtin hash().
-        state = self.context.python_random.getstate()
-        digest = hashlib.sha256(repr((self.week_index, state)).encode()).digest()
-        return random.Random(int.from_bytes(digest[:8], "big"))
+        return self._weekly.offer_rng_for_current_week(self)

     def set_paused(self, paused: bool) -> None:
         self._input.set_paused(self, paused)
@@ -806,27 +783,7 @@ class Mediator:
         self._maybe_hold_week_boundary(old_steps)

     def _maybe_hold_week_boundary(self, old_steps: int) -> None:
-        # GM-10a (D-041): after the COMPLETE tick (post queued-return settlement),
-        # hold the "week" pause if the calendar is enabled and this tick crossed a
-        # NEW week boundary. Placed LAST so the settlement is never interrupted
-        # mid-tick (review MAJOR), and skipped on game over so a terminal tick
-        # promotes to GAME_OVER rather than an offer (review MAJOR). WEEK_LENGTH_STEPS
-        # >> the max speed (4), so at most one boundary crosses per tick; a frozen
-        # tick advances no steps, so a held week never re-triggers. (At speed 4 the
-        # hold lands at e.g. steps=1202, not 1200 -- week_index is identical.)
-        if not self.week_calendar or self.is_game_over:
-            return
-        if old_steps // WEEK_LENGTH_STEPS < self.steps // WEEK_LENGTH_STEPS:
-            # GM-10b (D-042): generate the week's offers BEFORE holding, so they are
-            # ready when the modal opens. Read-only derivation (no gameplay draws),
-            # gated by the same calendar/crossing/not-game-over guards as the hold,
-            # so RL/headless/tutorial never generate and current_offers stays ().
-            self.current_offers = generate_offers(
-                self._offer_rng_for_current_week(),
-                count=OFFERS_PER_WEEK,
-                tunnels_bounded=self.num_tunnels is not None,
-            )
-            self.hold_pause_reason(_WEEK_REASON)
+        self._weekly.maybe_hold_boundary(self, old_steps)

     def _drain_and_settle_queued_returns(self) -> None:
         """Force-alight stranded riders, then settle emptied queued returns.
diff --git a/src/progression.py b/src/progression.py
index 3213775..e5c9594 100644
--- a/src/progression.py
+++ b/src/progression.py
@@ -93,6 +93,18 @@ class NetworkProgression:
         self.line_credits -= price
         self.purchased_num_paths += 1

+    def grant_free_path(self) -> bool:
+        """Grant one line for free (a weekly NEW_LINE offer, GM-10d): unlock the next
+        line without spending credits, capped at ``num_paths``. Returns True if a line
+        was granted, False if already at the cap (a no-op). Mirrors
+        ``record_path_purchase`` minus the credit spend, with the cap the purchase path
+        gets implicitly (a purchase is only offered while below ``num_paths``)."""
+
+        if self.purchased_num_paths >= self.num_paths:
+            return False
+        self.purchased_num_paths += 1
+        return True
+
     def record_delivery(self) -> None:
         """Award one lifetime delivery and one spendable line credit."""

diff --git a/src/weekly_offers.py b/src/weekly_offers.py
new file mode 100644
index 0000000..ca1a356
--- a/src/weekly_offers.py
+++ b/src/weekly_offers.py
@@ -0,0 +1,106 @@
+"""Weekly-calendar boundary + offer lifecycle (GM-10a-d), factored out of Mediator.
+
+A thin facade (like `NetworkProgression`/`PassengerFlow`) that owns the week-boundary
+HOLD and the offer generate/apply LOGIC while reading and writing the host Mediator's
+already-owned state (`steps`, `week_calendar`, `current_offers`, `context`,
+`_progression`) -- so week identity, offers, and the offer RNG stay DERIVED from
+already-persisted state with no new stored fields, exactly as the in-Mediator code did.
+
+The spy-able steps (`_apply_offer`, `_grant_free_line`, `_offer_rng_for_current_week`)
+are invoked through the host, so tests that patch those Mediator methods still
+intercept them, and the mediator keeps them as its public seam.
+"""
+
+from __future__ import annotations
+
+import hashlib
+import random
+
+from config import OFFERS_PER_WEEK, WEEK_LENGTH_STEPS
+from offers import Offer, OfferKind, generate_offers
+
+# The pause reason a held week boundary uses; frozen in Mediator._PAUSE_REASONS and
+# never cleared by the Space/speed toggles (GM-10a).
+WEEK_REASON = "week"
+
+
+class WeeklyOffers:
+    """Own the week-boundary hold + offer generate/apply for a Mediator host."""
+
+    def maybe_hold_boundary(self, host: object, old_steps: int) -> None:
+        # GM-10a (D-041): after the COMPLETE tick (post queued-return settlement),
+        # hold the "week" pause if the calendar is enabled and this tick crossed a
+        # NEW week boundary. Placed LAST in increment_time so settlement is never
+        # interrupted, and skipped on game over so a terminal tick promotes to
+        # GAME_OVER rather than an offer. WEEK_LENGTH_STEPS >> the max speed (4), so
+        # at most one boundary crosses per tick; a frozen tick advances no steps, so a
+        # held week never re-triggers (at speed 4 the hold lands at e.g. steps=1202).
+        if not host.week_calendar or host.is_game_over:
+            return
+        if old_steps // WEEK_LENGTH_STEPS < host.steps // WEEK_LENGTH_STEPS:
+            # GM-10b (D-042): generate the week's offers BEFORE holding, so they are
+            # ready when the modal opens. Read-only derivation (no gameplay draws),
+            # gated by the same calendar/crossing/not-game-over guards as the hold, so
+            # RL/headless/tutorial never generate and current_offers stays ().
+            host.current_offers = generate_offers(
+                host._offer_rng_for_current_week(),
+                count=OFFERS_PER_WEEK,
+                tunnels_bounded=host.num_tunnels is not None,
+            )
+            host.hold_pause_reason(WEEK_REASON)
+
+    def resolve(self, host: object, offer: Offer | None) -> None:
+        # Continue past a week boundary: APPLY the chosen offer (GM-10c), then clear
+        # the week's offers and release the pause. A None offer is a forced resolve
+        # with no choice (the window-close path in main.run_game). An offer is CONFINED
+        # to a genuine pending choice (review MAJOR): only one currently presented at a
+        # held boundary can be applied, so no out-of-band call (e.g. a headless
+        # MiniMetroEnv with no calendar) can grant an upgrade and bypass the weekly
+        # economy. GM-10h reconciles applied-offer persistence across Continue.
+        if offer is not None:
+            if not (host.is_week_boundary_pending and offer in host.current_offers):
+                raise ValueError(
+                    "cannot apply an offer that is not a currently-presented "
+                    "week-boundary choice: applicable only when it is one of "
+                    f"current_offers at a held boundary (got {offer!r}, "
+                    f"pending={host.is_week_boundary_pending})"
+                )
+            host._apply_offer(offer)
+        host.current_offers = ()
+        host.release_pause_reason(WEEK_REASON)
+
+    def apply_offer(self, host: object, offer: Offer) -> None:
+        # Dispatch the chosen offer to its per-kind effect. NEW_LINE grants a free line
+        # (GM-10d); the locomotive/carriage/tunnel arms are still no-op stubs
+        # (GM-10e/f/g) -- their effects need GM-10h persistence, so they change no state
+        # yet. A future kind without a handler must fail loud.
+        match offer.kind:
+            case OfferKind.NEW_LINE:
+                host._grant_free_line()  # GM-10d
+            case OfferKind.LOCOMOTIVE:
+                pass  # GM-10e: +1 num_metros (needs _require_running_config relaxed / GM-10h)
+            case OfferKind.CARRIAGE:
+                pass  # GM-10f: +1 num_carriages (same pin as locomotives)
+            case OfferKind.TUNNEL:
+                pass  # GM-10g: +1 tunnel budget (needs a persisted bonus / GM-10h)
+            case _:
+                raise ValueError(f"no effect handler for offer kind {offer.kind!r}")
+
+    def grant_free_line(self, host: object) -> None:
+        # GM-10d: the NEW_LINE effect -- unlock the next line for free (no credit spend),
+        # capped at num_paths. Mirrors the purchase flow's cache refresh
+        # (record_path_purchase -> update_unlocked_num_paths). purchased_num_paths is
+        # already persisted, so this is Continue-safe with no schema change (D-044).
+        if host._progression.grant_free_path():
+            host.update_unlocked_num_paths()
+
+    def offer_rng_for_current_week(self, host: object) -> random.Random:
+        # GM-10b (D-042): a dedicated per-week offer RNG, derived READ-ONLY from the
+        # already-persisted gameplay RNG state + week_index. getstate() consumes no
+        # draws, so the station-spawn stream is byte-untouched; and because that state
+        # is restored exactly on Continue, the SAME week's offers reproduce after
+        # save/load with NO new persisted state. repr() of the int-tuple state + sha256
+        # is deterministic and cross-process stable -- never the salted builtin hash().
+        state = host.context.python_random.getstate()
+        digest = hashlib.sha256(repr((host.week_index, state)).encode()).digest()
+        return random.Random(int.from_bytes(digest[:8], "big"))
```

## Tests
```diff
diff --git a/test/test_gm10c_choice.py b/test/test_gm10c_choice.py
index 048f6de..60f3e3b 100644
--- a/test/test_gm10c_choice.py
+++ b/test/test_gm10c_choice.py
@@ -215,12 +215,14 @@ class TestGM10cApplyOffer(unittest.TestCase):
         self.assertEqual(m.current_offers, ())
         self.assertFalse(m.is_week_boundary_pending)

-    def test_applying_each_offer_is_state_inert(self):
-        # GM-10c is a no-op dispatch: applying a kind must change NO game state and no
-        # serialized byte (effects are GM-10d-g). review MAJOR: check PER-KIND on a
-        # FRESH mediator (so compensating cross-kind mutations cannot cancel) and over
-        # runtime state beyond the save doc. A real effect on any kind turns red.
-        for kind in OfferKind:
+    def test_applying_a_stub_offer_kind_is_state_inert(self):
+        # The still-STUB kinds (GM-10e/f/g: locomotive/carriage/tunnel) must change NO
+        # game state and no serialized byte. review MAJOR: check PER-KIND on a FRESH
+        # mediator (so compensating cross-kind mutations cannot cancel) and over runtime
+        # state beyond the save doc. (NEW_LINE now grants a line -- GM-10d, tested in
+        # test_gm10d_line.py.) A real effect on a stub kind turns red.
+        stub_kinds = (OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE, OfferKind.TUNNEL)
+        for kind in stub_kinds:
             m = Mediator(seed=0)
             for _ in range(300):
                 m.increment_time(17)
diff --git a/test/test_gm10d_line.py b/test/test_gm10d_line.py
new file mode 100644
index 0000000..dea435c
--- a/test/test_gm10d_line.py
+++ b/test/test_gm10d_line.py
@@ -0,0 +1,168 @@
+"""GM-10d contract: the NEW_LINE offer effect -- a free line (D-044).
+
+Picking the NEW_LINE week-boundary offer unlocks the next metro line for free (no
+credit spend), capped at num_paths. It is the FIRST real per-kind offer effect;
+locomotive/carriage/tunnel stay stub no-ops (GM-10e/f/g). The grant flows through
+the already-persisted purchased_num_paths, so it is Continue-exact with no schema
+change (D-043/D-044); RL/headless never reach it (offers gated to the human shell).
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import unittest
+
+sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
+
+import pygame
+
+from config import num_paths, path_unlock_milestones
+from mediator import Mediator
+from offers import OfferKind, describe
+from progression import NetworkProgression
+from save_game import serialize_game
+from save_load import deserialize_game
+
+pygame.init()
+
+
+def _fresh_progression():
+    return NetworkProgression(
+        num_paths=num_paths,
+        path_unlock_milestones=path_unlock_milestones,
+        num_stations=20,
+        initial_num_stations=3,
+        station_unlock_milestones=[10, 30, 50],
+    )
+
+
+class TestGM10dGrantFreePath(unittest.TestCase):
+    def test_grant_unlocks_the_next_line_without_spending_credits(self):
+        p = _fresh_progression()
+        p.line_credits = 5
+        self.assertEqual(p.purchased_num_paths, 1)
+        self.assertTrue(p.grant_free_path(), "a line was granted")
+        self.assertEqual(p.purchased_num_paths, 2)
+        self.assertEqual(p.get_unlocked_num_paths(), 2)
+        self.assertEqual(p.line_credits, 5, "a grant spends NO credits")
+
+    def test_grant_caps_at_num_paths(self):
+        p = _fresh_progression()
+        granted = 0
+        while p.grant_free_path():
+            granted += 1
+        self.assertEqual(p.purchased_num_paths, num_paths, "capped at num_paths")
+        self.assertEqual(granted, num_paths - 1, "started at 1, granted up to the cap")
+        self.assertFalse(p.grant_free_path(), "a grant at the cap is a no-op")
+        self.assertEqual(p.purchased_num_paths, num_paths)
+
+    def test_grant_at_or_above_cap_is_a_noop(self):
+        # review MAJOR: pin the `>=` cap, not `==`. A loaded save can legitimately hold
+        # purchased_num_paths ABOVE num_paths (the schema clamps unlocked, not
+        # purchased -- get_unlocked_num_paths mins it down), and an `==` guard would
+        # grant AGAIN from such a state. Both `== num_paths` and `> num_paths` no-op.
+        p = _fresh_progression()
+        for excess in (0, 1, 3):
+            p.purchased_num_paths = num_paths + excess
+            self.assertFalse(
+                p.grant_free_path(), f"no-op at purchased={num_paths + excess}"
+            )
+            self.assertEqual(p.purchased_num_paths, num_paths + excess, "unchanged")
+
+
+class TestGM10dApplyNewLine(unittest.TestCase):
+    def _pending_game(self):
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        while not m.is_week_boundary_pending:
+            m.increment_time(17)
+        return m
+
+    def test_choosing_new_line_unlocks_a_line_and_refreshes_caches(self):
+        m = self._pending_game()
+        offer = describe(OfferKind.NEW_LINE)
+        # Present NEW_LINE explicitly (RNG-independent + satisfies the confinement
+        # guard: only a currently-offered choice can be applied).
+        m.current_offers = (offer, describe(OfferKind.LOCOMOTIVE))
+        before_unlocked = m.unlocked_num_paths
+        before_credits = m.line_credits
+        m.resolve_week_boundary(offer)
+        self.assertEqual(m.unlocked_num_paths, before_unlocked + 1, "a line unlocked")
+        self.assertEqual(m.purchased_num_paths, before_unlocked + 1)
+        self.assertEqual(m.line_credits, before_credits, "no credit spend")
+        self.assertEqual(m.current_offers, (), "offers cleared")
+        self.assertFalse(m.is_week_boundary_pending, "pause released")
+        # The newly-unlocked path button is no longer locked (cache refreshed).
+        self.assertFalse(
+            m.path_buttons[before_unlocked].is_locked, "new line's button unlocked"
+        )
+
+    def test_grant_starts_the_unlock_blink(self):
+        # review MINOR: the grant must refresh via update_unlocked_num_paths so the
+        # newly-unlocked button BLINKS (as a purchase does). A mutant that eagerly
+        # bumps unlocked_num_paths inside grant_free_path would suppress the blink.
+        m = Mediator(seed=0)
+        button = m.path_buttons[1]
+        self.assertFalse(button.is_unlock_blink_active(m.time_ms))
+        m._grant_free_line()
+        self.assertTrue(
+            button.is_unlock_blink_active(m.time_ms), "the free line's button blinks"
+        )
+
+    def test_new_line_grant_is_continue_exact(self):
+        m = Mediator(seed=0)
+        m._grant_free_line()  # purchased 1 -> 2
+        self.assertEqual(m.purchased_num_paths, 2)
+        self.assertEqual(m.unlocked_num_paths, 2)
+        doc = serialize_game(m)
+        self.assertEqual(doc["purchasedNumPaths"], 2)
+        self.assertEqual(
+            doc["numPaths"], num_paths, "the total is unchanged (pin holds)"
+        )
+        loaded = deserialize_game(doc)  # must not raise (_require_running_config OK)
+        self.assertEqual(loaded.purchased_num_paths, 2, "purchased reproduced")
+        self.assertEqual(loaded.unlocked_num_paths, 2, "unlocked reproduced")
+
+    def test_grant_free_line_at_the_cap_is_a_noop(self):
+        m = Mediator(seed=0)
+        for _ in range(num_paths):  # drive purchased_num_paths to the cap
+            m._grant_free_line()
+        self.assertEqual(m.purchased_num_paths, num_paths)
+        before = serialize_game(m)
+        m._grant_free_line()  # nothing left to grant
+        self.assertEqual(m.purchased_num_paths, num_paths, "still capped")
+        self.assertEqual(serialize_game(m), before, "a maxed grant moves no save byte")
+
+    def test_resolve_rejects_an_offer_that_was_not_presented(self):
+        # review MAJOR: an offer is applicable only when it is a currently-presented
+        # choice at a held boundary -- otherwise a headless/out-of-band call could
+        # grant an upgrade and bypass the weekly economy.
+        offered = describe(OfferKind.NEW_LINE)
+        # (a) no pending boundary at all (a fresh headless-style game).
+        m = Mediator(seed=0)
+        self.assertFalse(m.is_week_boundary_pending)
+        with self.assertRaisesRegex(ValueError, "currently-presented"):
+            m.resolve_week_boundary(offered)
+        self.assertEqual(m.purchased_num_paths, 1, "no line granted out of boundary")
+        # (b) a pending boundary that offered DIFFERENT kinds.
+        p = self._pending_game()
+        p.current_offers = (describe(OfferKind.CARRIAGE),)  # NEW_LINE not offered
+        with self.assertRaisesRegex(ValueError, "currently-presented"):
+            p.resolve_week_boundary(offered)
+        self.assertTrue(p.is_week_boundary_pending, "rejected -- boundary still held")
+
+    def test_the_other_offer_kinds_still_grant_nothing(self):
+        # LOCOMOTIVE/CARRIAGE/TUNNEL are GM-10e/f/g -- still no-op, so they do not
+        # unlock a line (only NEW_LINE does).
+        for kind in (OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE, OfferKind.TUNNEL):
+            m = Mediator(seed=0)
+            before = m.unlocked_num_paths
+            m._apply_offer(describe(kind))
+            self.assertEqual(
+                m.unlocked_num_paths, before, f"{kind.name} unlocked no line"
+            )
+
+
+if __name__ == "__main__":
+    unittest.main()
```

## Docs
```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index 37b27e5..0c9eb4a 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -381,6 +381,7 @@ python_mini_metro/
 - GM-10a (D-041) opens GM-10 with the simulation CALENDAR. `config.WEEK_LENGTH_STEPS` defines a "week" in sim steps; `Mediator.increment_time`, after the COMPLETE tick (post queued-return settlement), holds a new `"week"` pause reason when `mediator.week_calendar` is on, the tick crossed a new boundary, and the run is not game over. `"week"` joins `_PAUSE_REASONS` (frozen by the existing gate; never cleared by Space/speed); `week_index` is a `steps`-derived property and `resolve_week_boundary()` releases the pause. The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it, so RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, and frame-limited/headless runs never pause — the calendar branch is never taken off the human path, so no `env.py`/checkpoint/save change and no determinism risk. The human shell adds `AppScreen.OFFER`: `AppController.reconcile_week_boundary()` (per-frame AFTER `reconcile_game_over`, so a terminal tick wins; cancelling any armed gesture via the pinned letterbox-cancel before switching) promotes a pending boundary to a modal whose armed Continue (`menu_screens.offer_menu_layout`/`draw_offer_screen`) resolves the week; `main` renders it over the frozen frame, resolves-then-autosaves on a mid-offer window close, and consumes the offer frame's audio silently; `save_game._require_quiescent` blocks saving while a boundary is pending. Persistence + the RL observation/offer are deferred to GM-10h/GM-10b.
 - GM-10b (D-042) adds the weekly OFFER GENERATOR. A new dependency-light `src/offers.py` (stdlib-only — `enum`/`dataclasses`/`random`, no pygame/mediator, so it is import-safe on every headless/RL path) owns the data model (`OfferKind`, frozen `Offer`, `describe`) and a PURE `generate_offers(rng, *, count, tunnels_bounded)` that draws `count` DISTINCT kinds via `rng.sample` from an explicitly-ordered pool — the four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map. `config.OFFERS_PER_WEEK` (2) sets the count. When `Mediator._maybe_hold_week_boundary` fires (same calendar/crossing/not-game-over gate as the hold), it stores `self.current_offers` from `generate_offers`; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel (byte-stable on repeat). The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr, cross-process stable) — a deliberate design choice (dual-plan-reviewed): reading the state consumes no gameplay draws (station spawns stay byte-identical) AND, because that gameplay RNG state is already restored exactly on Continue, the same week's offers reproduce byte-exact after save/load with NO new persisted state. So GM-10b adds ZERO save/checkpoint/observation bytes (the `rng` block, exact-key save validation, checkpoint schema, and every frozen fixture are untouched) and never runs off the human path. Applying a choice is GM-10c, per-kind effects GM-10d–g, and applied-offer/replay persistence GM-10h (which must not trail GM-10c). (Adding `offers.py` and editing the runtime `src` files rotates the LIVE RL content fingerprint — `compute_content_fingerprint` hashes all of `src/**` — so a pre-GM-10b manifest fails strict resume/eval by default; EXPECTED and correct for fresh runs, no frozen fixture is repinned since `EXPECTED_LF_TRAINING` pins only `TRAINING_SOURCE_PATHS`, which excludes these files.)
 - GM-10c (D-043) makes the offers SELECTABLE. `menu_screens.offer_menu_layout(width, height, count)` now returns one button rect per offer (keys `offer_0..offer_{count-1}`); `draw_offer_screen` paints each offer as a button. `AppController._handle_offer` arms a button on mouse-down and, on a matching mouse-up (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to `Mediator._apply_offer(offer)` (a `match offer.kind` over `OfferKind`, raising a named `ValueError` on an unknown kind) then clears `current_offers` and releases the pause; `None` is a forced resolve with no choice (the `main.run_game` window-close path, unchanged). The per-kind arms are NO-OP stubs in GM-10c — choosing changes NO game state, so it is Continue-safe with ZERO new persisted bytes (the state-inertness is test-locked against the full `serialize_game` doc). The real effects are GM-10d–g: a NEW_LINE grant can flow through the already-persisted `purchased_num_paths` (Continue-safe standalone), while the LOCOMOTIVE/CARRIAGE grants hit `save_load._require_running_config` (which pins `numMetros`/`numCarriages` to config) and the TUNNEL grant needs a persisted bonus, so those must land with GM-10h.
+- GM-10d (D-044) fills the FIRST per-kind offer effect: `OfferKind.NEW_LINE` grants a free line. `NetworkProgression.grant_free_path()` bumps `purchased_num_paths` by one (capped at `num_paths`, returning whether it granted) — `record_path_purchase` MINUS the `line_credits` spend; `Mediator._grant_free_line` calls it and, on a grant, `update_unlocked_num_paths()` to refresh the derived `unlocked_num_paths` + path-button lock states (the exact purchase-flow cache refresh). The `_apply_offer` NEW_LINE arm now calls it (the locomotive/carriage/tunnel arms stay no-op — GM-10e/f/g). Because `purchased_num_paths` is already persisted and `_require_running_config` pins the TOTAL `numPaths` (unchanged), a granted line is Continue-exact with NO save/checkpoint-schema change (proven by round-trip); at the `num_paths` cap the grant is a state-inert no-op. Known limitation (deferred as GM-11 balance): a NEW_LINE offer generated when already at the cap is a wasted pick — excluding it from the pool would couple `generate_offers` to `purchased_num_paths`. `resolve_week_boundary(offer)` CONFINES application to a genuine pending choice — it raises unless the offer is one of `current_offers` at a held boundary — so no out-of-band call (a headless `MiniMetroEnv` with no calendar, a fabricated offer, or an offer the week did not present) can grant an upgrade and bypass the weekly economy. The GM-10a–d week-boundary hold + offer generate/apply LOGIC is factored into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023 — the mediator crossed the 1000-line hard ceiling; the facade reads/writes the host mediator's already-owned state — `steps`/`week_calendar`/`current_offers`/`context`/`_progression` — with no new fields, and invokes the spy-able seams `_apply_offer`/`_grant_free_line`/`_offer_rng_for_current_week` through the host, so the mediator keeps its public API); `mediator.py` drops to 940 lines and delegates.
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
diff --git a/GAME_RULES.md b/GAME_RULES.md
index 1eeaeb1..200f323 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -158,7 +158,7 @@ This document summarizes the game rules currently implemented in code.
   - ESC: exit (game-over screen).
 - The pause menu holds its own pause reason: opening it while SPACE-paused keeps both, and resuming from the menu releases only the menu hold, so the game stays paused until SPACE (or a speed button) clears the user pause. Speed-button selections still clear only the user pause and never the menu hold; the keyboard speed keys only set the speed and never unpause.
 - Weekly calendar (interactive play only): every fixed span of simulation time (a "week") the game pauses at a week boundary and shows a modal; choosing one of that week's offers (below) resolves the week, and the sim carries on from exactly where it froze with no time backlog. This pause is its own reason — SPACE and the speed buttons cannot dismiss it, and saving is blocked until you resolve the week (closing the window mid-week resolves it with no choice and resumes the game past the boundary). The calendar is a human-play feature: headless, RL, tutorial, and frame-limited runs never pause for a week. (GM-10a lays the calendar; GM-10b generates the offers; GM-10c makes them selectable.)
-- Weekly offers (interactive play only): the week-boundary modal previews a seeded SET of `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers, drawn from a pool of New Line, +1 Locomotive, +1 Carriage, and +1 Tunnel — the tunnel offer appears only on maps with a finite tunnel budget (never on open CLASSIC, which is unbounded). The offers are fully deterministic: they are generated from a dedicated per-week random stream derived from the game's own RNG state and the week number, so they consume no gameplay randomness (station spawns are byte-identical whether or not offers are generated) and reproduce EXACTLY when you Continue a saved game. GM-10b generated the offers; GM-10c makes them SELECTABLE — the modal shows one button per offer, and an armed click (a press and release on the same button, so a stale gameplay release cannot choose) picks that offer, resolves the week, and resumes. The choice is dispatched to a per-kind effect; the effects each kind grants (line/locomotive/carriage/tunnel) are being added incrementally in later units, and closing the window mid-offer resolves with no choice.
+- Weekly offers (interactive play only): the week-boundary modal previews a seeded SET of `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers, drawn from a pool of New Line, +1 Locomotive, +1 Carriage, and +1 Tunnel — the tunnel offer appears only on maps with a finite tunnel budget (never on open CLASSIC, which is unbounded). The offers are fully deterministic: they are generated from a dedicated per-week random stream derived from the game's own RNG state and the week number, so they consume no gameplay randomness (station spawns are byte-identical whether or not offers are generated) and reproduce EXACTLY when you Continue a saved game. GM-10b generated the offers; GM-10c makes them SELECTABLE — the modal shows one button per offer, and an armed click (a press and release on the same button, so a stale gameplay release cannot choose) picks that offer, resolves the week, and resumes. The choice is dispatched to a per-kind effect. New Line (GM-10d) unlocks your next metro line for FREE — it bumps `purchased_num_paths` by one (no line-credit spend), capped at the map's line count `num_paths`, exactly as buying a line would but without the cost; at the cap it is a no-op. Because `purchased_num_paths` is already saved, a granted line survives Continue exactly. The remaining effects (+1 Locomotive / +1 Carriage / +1 Tunnel) are being added incrementally; closing the window mid-offer resolves with no choice.
 - Autosave: opening the pause menu and Exit to Title each write a single autosave to `saves/autosave.json`, and closing the window mid-run keeps it, so the title screen's Continue reloads the game exactly where you left off (releasing the menu pause, honoring a held SPACE pause). Reaching game over deletes the autosave, so a finished run cannot be Continued; every autosave is best-effort and never blocks play or exit.
 - Tutorial: a coached playthrough reached from the title screen. It runs a real seeded game with on-screen prompts that walk through drawing a line, rerouting it, adding a train, delivering a passenger, overload pressure, pausing, and changing speed; each lesson advances when you actually perform it (overload advances after a few seconds of watching). Press Esc to skip or leave at any point. The tutorial game never ends (so a first-timer cannot lose mid-lesson) and never autosaves or records a high score. It is presentation only and changes no game rules or balance.
 - Settings: a Settings screen, reached from the title or pause menu (Back returns to whichever opened it, and opening it from the pause menu keeps the game paused), toggles fullscreen, steps the master/music/SFX volumes in 25% increments, and toggles reduced motion. Settings persist to `saves/settings.json` and survive restart; fullscreen applies to the live window and reduced motion holds the passenger-warning, station-unlock, and path-button blinks steady while suppressing the snap-blip rings (the master and SFX volumes scale the procedural audio cues). Settings are presentation-only and change no game balance; a missing or corrupt settings file falls back to the defaults and never blocks play.
diff --git a/PROGRESS.md b/PROGRESS.md
index dfa0755..42e2c03 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -183,3 +183,4 @@
 - Opened GM-10 with GM-10a, the simulation CALENDAR (D-041) -- the foundation for weekly progression. A "week" is `config.WEEK_LENGTH_STEPS` (1200 ≈ 20s at 1x); `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement), holds a new `"week"` pause reason when the calendar is enabled, a new boundary crossed (`old//W < steps//W`), and not game over. `"week"` joins `_PAUSE_REASONS` (never cleared by Space/speed); `week_index` is `steps`-derived (no new persisted scalar); `resolve_week_boundary()` releases it. The calendar is OPT-IN, default OFF -- only INTERACTIVE `main.run_game` (build_game/build_from, gated on `max_frames is None`) enables it, so RL/tutorial/headless never pause. The human shell adds `AppScreen.OFFER`: `reconcile_week_boundary()` (per-frame AFTER game-over reconcile, cancelling any gesture) promotes to a modal whose armed Continue resolves the week; window-close mid-offer resolves+autosaves; offer-frame audio consumed silently; saving blocked while pending. HIGH-RISK -> DUAL plan review, both REVISE (harness 1 BLOCKER; Codex 2 BLOCKER + 4 MAJOR with reproduced counterexamples). GATING to the human shell resolved the BLOCKERs structurally: my first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` drives via `advance_exact` and the tutorial is a third direct-Mediator shell -- all would soft-lock at step 1200; gating (week_calendar default OFF) means the branch is never taken off the human path (no env.py/checkpoint/save change, no determinism risk). Codex also refuted my "pause is trajectory-invariant" probe (it bypassed the FixedStepClock cadence) -- gating moots it. The hold-after-full-tick (settlement), terminal precedence, gesture-cancel+arming, and window-close edges were all folded with pinned regressions. The DUAL impl review then confirmed the production code CORRECT on both lanes, with all findings TEST-STRENGTH: Codex mutation-proved six survivors the harness rated shippable (an exact-landing-only hold, a hold-before-settlement, a dropped not-game-over guard, a truthy-not-`is True` OFFER guard, a wrong letterbox-cancel event, and a missing run-loop OFFER promotion/QUIT path), each now pinned (a genuine-crossing speed-4 test, a queued-settlement-parity test, a live-Mock `is True` test, an exact-cancel-event assertion, and real-`run_game` gating + OFFER-loop integration tests). Full `py313` suite green (1507 tests). GM-10b (dedicated-RNG offers) opens next.
 - Continued GM-10 with GM-10b, the dedicated-RNG weekly OFFER GENERATOR (D-042). A new stdlib-only `src/offers.py` (`OfferKind`/`Offer`/pure `generate_offers`) draws `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers from a map-appropriate pool (New Line / +1 Locomotive / +1 Carriage, plus +1 Tunnel only on a finite-tunnel map); `Mediator._maybe_hold_week_boundary` stores `current_offers` at the hold and `resolve_week_boundary` clears them; `draw_offer_screen` previews the labels read-only. The offer RNG is a dedicated per-week `random.Random` derived READ-ONLY from `python_random.getstate()` + `week_index` — a DUAL-PLAN-REVIEW pivot: Codex BLOCKED the first plan (a persisted `spawn(3)` stream deferred to GM-10h would RESET on Continue and diverge, violating README's "Continue resumes exactly"), so offers are instead derived from the already-persisted gameplay RNG state, making them Continue-EXACT with ZERO new save/checkpoint/observation bytes and gameplay-INERT (getstate consumes no draws — station spawns stay byte-identical, every frozen fixture untouched). Gated to the human shell like the calendar, so RL/headless/tutorial never generate (`current_offers` stays `()`). Empirically pre-validated (cadence ~4-6 weeks/game; separate-stream inertness; spawn byte-compat; Continue-exactness of the boundary python-state — all proven before planning). Dual plan review (harness REVISE + Codex BLOCK → the stateless pivot) + dual impl review folded. Applying a choice is GM-10c, per-kind effects GM-10d-g, applied-offer persistence GM-10h (which must not trail GM-10c). Full `py313` suite green (1527 tests).
 - Continued GM-10 with GM-10c, the week-boundary CHOICE CONTROLS (D-043). The GM-10b read-only preview becomes interactive: `menu_screens.offer_menu_layout(width, height, count)` returns one button per offer (`offer_0..offer_{count-1}`), `draw_offer_screen` paints them, and `AppController._handle_offer` arms a button on press and, on a matching release (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to a new `_apply_offer` (`match offer.kind`, named `ValueError` on an unknown kind) then clears + releases; `None` is the window-close forced resolve (unchanged). The per-kind arms are NO-OP stubs — choosing changes NO game state, so GM-10c is Continue-safe with ZERO new persisted bytes (locked by a test asserting every kind leaves the full `serialize_game` doc byte-identical). The real effects are GM-10d-g: NEW_LINE can ride the already-persisted `purchased_num_paths` (Continue-safe standalone), while LOCOMOTIVE/CARRIAGE hit `_require_running_config` and TUNNEL needs a persisted bonus, so those land with GM-10h. Full `py313` suite green (1540 tests).
+- Continued GM-10 with GM-10d, the FIRST real per-kind offer effect (D-044): choosing NEW_LINE unlocks a free line. `NetworkProgression.grant_free_path()` bumps `purchased_num_paths` (capped at `num_paths`, no `line_credits` spend — `record_path_purchase` minus the cost); `Mediator._grant_free_line` calls it and refreshes the derived caches via `update_unlocked_num_paths()` (the exact purchase-flow refresh), wired into the `_apply_offer` NEW_LINE arm (locomotive/carriage/tunnel stay no-op — GM-10e/f/g). Empirically proven Continue-safe standalone (probe: grant → purchased 1→2, unlocked 1→2, credits unchanged; serialize→deserialize reproduces both; `numPaths` unchanged so `_require_running_config` holds), so NO save/checkpoint-schema change and GM-10d precedes GM-10h. The GM-10c all-kinds-inert test narrowed to the three still-stub kinds. Known limitation (GM-11 balance): a NEW_LINE offer at the line cap is a wasted no-op pick. Dual impl review (harness SHIP + Codex FIX-FIRST → production correct by BOTH; folded 4 gaps — Codex caught a robustness MAJOR (resolve now CONFINES application to a currently-presented pending choice, so no out-of-band/headless call can grant an upgrade and bypass the economy) + a mutation-weak cap `>=` (an above-cap test now pins it) + an unpinned unlock-blink + a stale comment). The GM-10a-d week/offer LOGIC was factored into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023) because `mediator.py` crossed the 1000-line hard ceiling; the extraction is behavior-preserving (mediator 940 lines; all offer tests green). Full `py313` suite green (1550 tests).
diff --git a/README.md b/README.md
index a38a8cd..7f2c89e 100644
--- a/README.md
+++ b/README.md
@@ -66,7 +66,7 @@ Set `PYTHON` to a specific interpreter path when `python` is not the intended ex
 * Opening the pause menu autosaves your game to `saves/autosave.json`; Exit to Title rewrites the same save before leaving, and closing the window mid-run keeps it, so Continue on the title screen resumes exactly where you left off. Reaching game over deletes the autosave, so a finished run cannot be Continued.
 * Finishing a run records its lifetime deliveries to a high-score leaderboard at `saves/highscores.json` (ranked and capped per map and rules version); a new best shows a compact indicator on the game-over screen.
 * Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
-* Every week of play the game pauses at a week boundary and shows a modal with that week's upgrade offers (a seeded pick of New Line / +1 Locomotive / +1 Carriage / +1 Tunnel — tunnel offers appear only on maps with a tunnel budget), one clickable button each; click one to choose it and resume (the sim carries on with no time backlog). The offers are deterministic and reproduce exactly on Continue. Choosing an offer resolves the week (the modal only closes when you pick one); the upgrade each kind grants is being added incrementally. This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week or generate offers.
+* Every week of play the game pauses at a week boundary and shows a modal with that week's upgrade offers (a seeded pick of New Line / +1 Locomotive / +1 Carriage / +1 Tunnel — tunnel offers appear only on maps with a tunnel budget), one clickable button each; click one to choose it and resume (the sim carries on with no time backlog). The offers are deterministic and reproduce exactly on Continue. Choosing New Line unlocks your next metro line for free (up to the map's line limit); the other upgrades (+1 Locomotive / +1 Carriage / +1 Tunnel) are being added incrementally. This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week or generate offers.
 * The top-left HUD shows lifetime passengers delivered, currently spendable line credits, unassigned locomotives, and unassigned carriages as separate values.
 * Each filled grey circle at the bottom is an unused unlocked metro line slot.
 * Hold an assigned colored circle, drag through the replacement station order, and release on the final station to redraw that line; the selected circle is outlined and an invalid repeated-station draft turns red.
diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index 72718b1..b08e3ee 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -269,3 +269,11 @@ Reason: a design PIVOT forced by the dual plan review (harness REVISE, Codex BLO
 Decision: GM-10c makes the week-boundary offers SELECTABLE. `menu_screens.offer_menu_layout` gains a `count` param and returns one button rect per offer (`offer_0..offer_{count-1}`); `draw_offer_screen` paints each offer as a button. `AppController._handle_offer` arms a button on mouse-down and, on a matching mouse-up (the GM-10a arming discipline — a stale gameplay release cannot choose), resolves with the chosen offer. `Mediator.resolve_week_boundary(offer=None)` gains the optional chosen offer: it calls `_apply_offer(offer)` (a `match offer.kind` over `OfferKind`, raising a named `ValueError` on an unknown kind), then clears `current_offers` and releases the pause; `offer=None` is a forced resolve with no choice (the `main.run_game` window-close path, unchanged and backward-compatible). In GM-10c every per-kind arm is a NO-OP stub, so choosing changes NO game state and adds ZERO new persisted bytes (Continue-safe; state-inertness is test-locked against the full `serialize_game` doc). The per-kind EFFECTS are GM-10d-g; applied-offer/replay persistence is GM-10h.

 Reason: keep the roadmap's clean split (controls in GM-10c, effects in GM-10d-g, persistence in GM-10h) rather than fold an effect in early — a no-op dispatch is fully testable via the control flow (arming, routing offer_i→current_offers[i], resume, window-close-no-apply) and the state-inertness lock, and it keeps the D-042 ordering constraint vacuously satisfied (GM-10c persists nothing). REFINEMENT of that constraint discovered here (from the `_require_running_config` pin, Explore): the constraint bites per-EFFECT, not on GM-10c itself — GM-10d's NEW_LINE grant can flow through the already-persisted `purchased_num_paths` and is Continue-safe standalone, but GM-10e/f (LOCOMOTIVE/CARRIAGE via `num_metros`/`num_carriages`, pinned by `save_load._require_running_config` to config values) and GM-10g (TUNNEL, needs a persisted bonus over the immutable `map_definition.tunnel_budget`) MUST land with GM-10h. The chosen offer is passed as an argument (not stored) so there is no throwaway mediator state; the additive `offer=None` default keeps every existing `resolve_week_boundary()` caller (window-close, tests) valid. GM-10d (line upgrade — the first, Continue-safe effect) opens next.
+
+## D-044
+
+Decision: GM-10d fills the FIRST per-kind offer effect — `OfferKind.NEW_LINE` grants a free line. `NetworkProgression.grant_free_path() -> bool` bumps `purchased_num_paths` by one, capped at `num_paths` (returns False and no-ops at the cap) — exactly `record_path_purchase` MINUS the `line_credits -= price` spend. `Mediator._grant_free_line` calls it and, only on a grant, `update_unlocked_num_paths()` to refresh the derived `unlocked_num_paths` cache and the path-button lock states — the identical cache refresh the purchase flow does. The `_apply_offer` `case OfferKind.NEW_LINE` arm calls `_grant_free_line`; the LOCOMOTIVE/CARRIAGE/TUNNEL arms stay no-op stubs (GM-10e/f/g). The GM-10c all-kinds-inert test narrows to the three still-stub kinds; NEW_LINE gets its own effect suite.
+
+Reason: NEW_LINE is the one effect that is Continue-safe STANDALONE (D-043), so it can precede GM-10h — proven empirically before implementing (probe this session): a grant takes `purchased_num_paths` 1→2 and `unlocked_num_paths` 1→2 with `line_credits` unchanged; `serialize_game`→`deserialize_game` reproduces both; and the save still loads because `_require_running_config` pins the TOTAL `numPaths` (4, unchanged), not `purchasedNumPaths` (already a save field). So GM-10d adds NO save/checkpoint-schema change and NO new persisted bytes. The grant reuses the domain owner (`NetworkProgression`) for the counter+cap and the mediator's existing `update_unlocked_num_paths` for the cache refresh, rather than duplicating either — a free line is precisely a bought line without the bill. KNOWN LIMITATION (deferred to GM-11 balance, documented in ARCHITECTURE): a NEW_LINE offer GENERATED when the player is already at `num_paths` lines is a wasted no-op pick; excluding it from the pool would couple `generate_offers` to `purchased_num_paths`, and it is rare (4 lines is late-game). GM-10e (locomotive upgrade) opens next; it and GM-10f (carriage) bump `num_metros`/`num_carriages`, which `_require_running_config` pins to config, so they must land with GM-10h's persistence relaxation.
+
+Two impl-review folds landed with GM-10d. (1) `resolve_week_boundary(offer)` now CONFINES application to a genuine pending choice — it raises unless `offer` is one of `current_offers` at a held boundary (`is_week_boundary_pending`) — so the public mediator method cannot be driven out-of-band (a headless `MiniMetroEnv` with no calendar, a fabricated offer, or a kind the week did not present) to grant an upgrade and bypass the weekly economy (Codex MAJOR; the normal `_handle_offer` path always passes a `current_offers[index]` at a held boundary, so it is unaffected). (2) The GM-10a–d week-boundary hold + offer generate/apply LOGIC was FACTORED OUT of `Mediator` into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023): the addition pushed `mediator.py` past the 1000-line HARD ceiling (test-enforced), and the fleet canon is "split rather than grow god-objects." The facade is stateless — it reads/writes the host mediator's already-owned state (`steps`/`week_calendar`/`current_offers`/`context`/`_progression`) with no new fields, and invokes the spy-able seams (`_apply_offer`/`_grant_free_line`/`_offer_rng_for_current_week`) through the host so a test patching those still intercepts and the mediator keeps its public API. The extraction is behavior-preserving (`mediator.py` 940 lines; every offer/calendar test green), verified by the full suite rather than re-review since it relocates already-reviewed logic without changing behavior.
```
