# GM-10b dedicated-RNG weekly offer generator — implementation diff

Source: offers.py (NEW: OfferKind/Offer/generate_offers), mediator.py (current_offers + read-only per-week RNG derivation _offer_rng_for_current_week + generation at the boundary hold + clear on resolve), config.py (OFFERS_PER_WEEK), menu_screens.py (draw_offer_screen renders the offer labels), main.py (passes current_offers). Tests: test_gm10b_offers.py (NEW: determinism/frozen-sequence/Continue-exact/inertness/gating/render/import-safety, hardened for the impl-review folds) + test_gm10a_calendar.py (run_game harness fix + offers-wiring test). Docs: D-042, README, GAME_RULES, ARCHITECTURE, PROGRESS.

## Production source
```diff
diff --git a/src/config.py b/src/config.py
index 49d47ed..6b43979 100644
--- a/src/config.py
+++ b/src/config.py
@@ -92,6 +92,12 @@ carriage_passengers_per_row = 3
 # and the tutorial leave it off, so weeks never pause a headless sim.
 WEEK_LENGTH_STEPS = 1200

+# weekly offers (GM-10b / D-042): how many DISTINCT upgrade offers the week
+# boundary presents. A provisional balance default -- GM-11 may tune it. On the
+# open CLASSIC map (no tunnel budget) the candidate pool is 3 kinds, so a value
+# above 3 would silently clamp there (see offers.generate_offers).
+OFFERS_PER_WEEK = 2
+
 # path
 path_unlock_milestones = [0, 90, 300, 650]
 num_paths = len(path_unlock_milestones)
diff --git a/src/main.py b/src/main.py
index 7bdcc4d..ff65087 100644
--- a/src/main.py
+++ b/src/main.py
@@ -429,8 +429,13 @@ def run_game(
                 if overlay is not None:
                     draw_tutorial_overlay(game_surface, *overlay)
             elif state == AppScreen.OFFER:
-                # The week-boundary modal over the frozen game frame (GM-10a).
-                draw_offer_screen(game_surface, controller.mediator.week_index)
+                # The week-boundary modal over the frozen game frame (GM-10a); the
+                # week's upgrade offers are previewed read-only (GM-10b).
+                draw_offer_screen(
+                    game_surface,
+                    controller.mediator.week_index,
+                    controller.mediator.current_offers,
+                )
         window_surface.fill(screen_color)
         target_size = (viewport.width, viewport.height)
         if viewport.width > 0 and viewport.height > 0:
diff --git a/src/mediator.py b/src/mediator.py
index 4d9ace8..042b648 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -1,11 +1,14 @@
 from __future__ import annotations

+import hashlib
+import random
 from typing import Dict, List

 import pygame

 from carriage_management import CarriageManagement
 from config import (
+    OFFERS_PER_WEEK,
     WEEK_LENGTH_STEPS,
     game_over_button_height,
     game_over_button_spacing,
@@ -47,6 +50,7 @@ from graph.graph_algo import bfs, build_station_nodes_dict
 from graph.node import Node
 from input_coordinator import InputCoordinator
 from maps import CLASSIC, MapDefinition
+from offers import Offer, generate_offers
 from passenger_flow import PassengerFlow
 from path_handles import PathEditSelection
 from path_lifecycle import PathLifecycle
@@ -166,6 +170,11 @@ class Mediator:
         # (they would soft-lock a driver that cannot resolve the offer). Only the
         # human PLAYING shell (main.run_game's build_game/build_from) sets this True.
         self.week_calendar = False
+        # GM-10b (D-042): the upgrade offers generated for the current held week
+        # boundary; empty except while an offer is pending. Transient (NOT persisted)
+        # -- offers are re-derived Continue-exact from the already-persisted RNG state
+        # (see _offer_rng_for_current_week), so no new save/checkpoint bytes.
+        self.current_offers: tuple[Offer, ...] = ()
         self.game_speed_multiplier = 1
         self.unlocked_num_paths = self.get_unlocked_num_paths()
         self.unlocked_num_stations = self.get_unlocked_num_stations()
@@ -699,10 +708,24 @@ class Mediator:
         return _WEEK_REASON in self._pause_reason_store(_WEEK_REASON)

     def resolve_week_boundary(self) -> None:
-        # Continue past a week boundary. In GM-10a this just releases the pause;
-        # GM-10b applies the chosen offer here before releasing.
+        # Continue past a week boundary: clear the week's offers and release the
+        # pause. GM-10b generates offers (below); GM-10c will APPLY the chosen one
+        # here, BEFORE clearing, and GM-10h reconciles applied-offer persistence.
+        self.current_offers = ()
         self.release_pause_reason(_WEEK_REASON)

+    def _offer_rng_for_current_week(self) -> random.Random:
+        # GM-10b (D-042): a dedicated per-week offer RNG, derived READ-ONLY from the
+        # already-persisted gameplay RNG state + week_index. `getstate()` consumes no
+        # draws, so the station-spawn stream is byte-untouched; and because that state
+        # is restored exactly on Continue (README "resumes exactly"), the SAME week's
+        # offers reproduce after save/load with NO new persisted state (persistence
+        # proper is GM-10h). repr() of the int-tuple state + sha256 is deterministic
+        # and cross-process stable -- never the PYTHONHASHSEED-salted builtin hash().
+        state = self.context.python_random.getstate()
+        digest = hashlib.sha256(repr((self.week_index, state)).encode()).digest()
+        return random.Random(int.from_bytes(digest[:8], "big"))
+
     def set_paused(self, paused: bool) -> None:
         self._input.set_paused(self, paused)

@@ -774,6 +797,15 @@ class Mediator:
         if not self.week_calendar or self.is_game_over:
             return
         if old_steps // WEEK_LENGTH_STEPS < self.steps // WEEK_LENGTH_STEPS:
+            # GM-10b (D-042): generate the week's offers BEFORE holding, so they are
+            # ready when the modal opens. Read-only derivation (no gameplay draws),
+            # gated by the same calendar/crossing/not-game-over guards as the hold,
+            # so RL/headless/tutorial never generate and current_offers stays ().
+            self.current_offers = generate_offers(
+                self._offer_rng_for_current_week(),
+                count=OFFERS_PER_WEEK,
+                tunnels_bounded=self.num_tunnels is not None,
+            )
             self.hold_pause_reason(_WEEK_REASON)

     def _drain_and_settle_queued_returns(self) -> None:
diff --git a/src/ui/menu_screens.py b/src/ui/menu_screens.py
index 64a2b4e..1b95872 100644
--- a/src/ui/menu_screens.py
+++ b/src/ui/menu_screens.py
@@ -7,6 +7,8 @@ touch gameplay state or game RNG.

 from __future__ import annotations

+from collections.abc import Sequence
+
 import pygame

 from config import (
@@ -20,6 +22,7 @@ from config import (
     game_over_hint_font_size,
     game_over_text_color,
 )
+from offers import Offer

 _TITLE_HEADING = "MINI METRO"
 _PAUSE_HEADING = "PAUSED"
@@ -28,6 +31,8 @@ _BEST_INDICATOR_TEXT = "NEW BEST"
 _HEADING_FONT_SIZE = 96
 _TUTORIAL_SUBLINE_FONT_SIZE = 26
 _HEADING_GAP = 60
+# Gap between the GM-10b offer preview panel and the Continue button below it.
+_OFFER_GAP = 24
 # Settings rows carry value labels ("Reduced Motion: On"), so they use a wider
 # button than the menu stacks; centering is on the screen midline regardless.
 _SETTINGS_BUTTON_WIDTH = 620
@@ -198,18 +203,47 @@ def offer_menu_layout(width: int, height: int) -> dict[str, pygame.Rect]:
     return _stacked_buttons(width, ("continue",), height // 2)


-def draw_offer_screen(surface: pygame.Surface, week_index: int) -> None:
-    """Paint the deterministic week-boundary modal: a banner + Continue (GM-10a)."""
+def draw_offer_screen(
+    surface: pygame.Surface, week_index: int, offers: Sequence[Offer]
+) -> None:
+    """Paint the deterministic week-boundary modal (GM-10a + GM-10b).
+
+    A banner, the week's upgrade offers previewed read-only (GM-10b -- choosing is
+    GM-10c), and Continue. The offer labels sit on an opaque panel painted in the
+    same call, so repeated frame draws over existing chrome stay byte-identical
+    (the module-wide convention shared with _draw_button/_draw_heading).
+    """

     width, height = surface.get_size()
     layout = offer_menu_layout(width, height)
+    continue_rect = layout["continue"]
+    font = _font(font_name, game_over_hint_font_size)
+    rendered = [
+        font.render(offer.label, True, game_over_text_color) for offer in offers
+    ]
+    line_height = max((text.get_height() for text in rendered), default=0) + 12
+    block_height = line_height * len(rendered)
+    offers_bottom = continue_rect.top - _OFFER_GAP
+    offers_top = offers_bottom - block_height
     _draw_heading(
-        surface,
-        width,
-        layout["continue"].top - _HEADING_GAP,
-        f"Week {week_index} complete",
+        surface, width, offers_top - _HEADING_GAP, f"Week {week_index} complete"
     )
-    _draw_button(surface, layout["continue"], "Continue")
+    if rendered:
+        panel_width = max(text.get_width() for text in rendered) + 60
+        panel = pygame.Rect(0, 0, panel_width, block_height + 12)
+        panel.center = (width // 2, offers_top + block_height // 2)
+        pygame.draw.rect(surface, game_over_button_color, panel, border_radius=10)
+        pygame.draw.rect(
+            surface,
+            game_over_button_border_color,
+            panel,
+            game_over_button_border_width,
+            border_radius=10,
+        )
+        for index, text in enumerate(rendered):
+            centre_y = offers_top + line_height * index + line_height // 2
+            surface.blit(text, text.get_rect(center=(width // 2, centre_y)))
+    _draw_button(surface, continue_rect, "Continue")


 def draw_tutorial_overlay(
diff --git a/src/offers.py b/src/offers.py
new file mode 100644
index 0000000..6ddbea5
--- a/src/offers.py
+++ b/src/offers.py
@@ -0,0 +1,88 @@
+"""Weekly upgrade offers (GM-10b / D-042).
+
+At each GM-10a week boundary the interactive game presents a small SET of upgrade
+offers. This module owns the OFFER DATA MODEL and a PURE, deterministic generator;
+it deliberately imports only the standard library (no pygame/mediator/entity/config)
+so it stays import-safe on every headless/RL path with no import cycle.
+
+GM-10b generates offers only; APPLYING a chosen offer is GM-10c, the per-kind
+effects are GM-10d-g, and replay/persistence reconciliation is GM-10h. The offer
+RNG is supplied by the caller (the mediator derives a per-week `random.Random`
+read-only from the already-persisted gameplay RNG state, so offers are
+Continue-exact without any new persisted state); this module never seeds itself.
+"""
+
+from __future__ import annotations
+
+import random
+from dataclasses import dataclass
+from enum import Enum
+
+
+class OfferKind(Enum):
+    """The kinds of upgrade a week boundary can offer (effects land in GM-10d-g)."""
+
+    NEW_LINE = "new_line"
+    LOCOMOTIVE = "locomotive"
+    CARRIAGE = "carriage"
+    TUNNEL = "tunnel"
+
+
+_KIND_LABELS: dict[OfferKind, str] = {
+    OfferKind.NEW_LINE: "New Line",
+    OfferKind.LOCOMOTIVE: "+1 Locomotive",
+    OfferKind.CARRIAGE: "+1 Carriage",
+    OfferKind.TUNNEL: "+1 Tunnel",
+}
+
+
+@dataclass(frozen=True)
+class Offer:
+    """One immutable upgrade offer: its kind and the human label to display."""
+
+    kind: OfferKind
+    label: str
+
+
+def describe(kind: OfferKind) -> Offer:
+    """The canonical Offer for a kind (its fixed display label)."""
+
+    return Offer(kind=kind, label=_KIND_LABELS[kind])
+
+
+# EXPLICITLY-ORDERED candidate pools so `random.sample` draws deterministically for
+# a given RNG state. TUNNEL is offered only on a map with a finite tunnel budget
+# (a bounded map); on the open CLASSIC map (unbounded, `num_tunnels is None`) a
+# tunnel grant is meaningless, so it is excluded.
+_BOUNDED_POOL: tuple[OfferKind, ...] = (
+    OfferKind.NEW_LINE,
+    OfferKind.LOCOMOTIVE,
+    OfferKind.CARRIAGE,
+    OfferKind.TUNNEL,
+)
+_CLASSIC_POOL: tuple[OfferKind, ...] = (
+    OfferKind.NEW_LINE,
+    OfferKind.LOCOMOTIVE,
+    OfferKind.CARRIAGE,
+)
+
+
+def generate_offers(
+    rng: random.Random, *, count: int, tunnels_bounded: bool
+) -> tuple[Offer, ...]:
+    """Draw ``count`` DISTINCT upgrade offers from the map-appropriate pool.
+
+    Pure and deterministic: the ONLY randomness consumer is ``rng`` (the caller
+    owns seeding). ``tunnels_bounded`` selects the pool -- the four kinds on a
+    finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map.
+    """
+
+    if count < 1:
+        raise ValueError(f"count must be a positive number of offers, got {count!r}")
+    pool = _BOUNDED_POOL if tunnels_bounded else _CLASSIC_POOL
+    # `sample` gives DISTINCT kinds (never "+1 Locomotive" twice). The min() clamps
+    # a count larger than the pool -- a SILENT cap: harmless at OFFERS_PER_WEEK=2
+    # over the 3-kind CLASSIC pool, but a future count > pool would yield fewer
+    # offers on CLASSIC. Fine for now; revisit if OFFERS_PER_WEEK grows past 3.
+    drawn = rng.sample(pool, min(count, len(pool)))
+    return tuple(describe(kind) for kind in drawn)
```

## Tests
```diff
diff --git a/test/test_gm10a_calendar.py b/test/test_gm10a_calendar.py
index 388b507..7d1bb3b 100644
--- a/test/test_gm10a_calendar.py
+++ b/test/test_gm10a_calendar.py
@@ -386,6 +386,7 @@ class _LoopMediator:
         self._pending = pending
         self.week_index = week_index
         self.week_calendar = None  # build_game/build_from set this on construction
+        self.current_offers = ()  # GM-10b: run loop reads this for the OFFER render
         self.map_definition = SimpleNamespace(
             map_id="classic", map_definition_version=1
         )
@@ -406,16 +407,20 @@ class _LoopMediator:
         pass


-def _drive_run_game(frames_events, *, max_frames, start_state=None, pending=False):
+def _drive_run_game(
+    frames_events, *, max_frames, start_state=None, pending=False, offers=()
+):
     """Run ``main.run_game`` over the pumped frames; return the captured harness."""

     captured = {}
     offer_draws = []
+    offer_renders = []
     autosaves = []
     real_app_controller = main.AppController

     def build_mediator(map_definition=None):
         mediator = _LoopMediator(pending=pending)
+        mediator.current_offers = offers
         captured["mediator"] = mediator
         return mediator

@@ -438,7 +443,10 @@ def _drive_run_game(frames_events, *, max_frames, start_state=None, pending=Fals
         patch("main.AppController", side_effect=make_controller),
         patch(
             "main.draw_offer_screen",
-            side_effect=lambda surface, week_index: offer_draws.append(week_index),
+            side_effect=lambda surface, week_index, rendered_offers: (
+                offer_draws.append(week_index),
+                offer_renders.append(rendered_offers),
+            ),
         ),
         patch("main.draw_title_screen", side_effect=lambda *a, **k: None),
         patch("main.write_autosave", side_effect=lambda m: autosaves.append(m)),
@@ -465,6 +473,7 @@ def _drive_run_game(frames_events, *, max_frames, start_state=None, pending=Fals
         mediator=captured.get("mediator"),
         controller=captured.get("controller"),
         offer_draws=offer_draws,
+        offer_renders=offer_renders,
         autosaves=autosaves,
         exited=exited["raised"],
     )
@@ -524,6 +533,25 @@ class TestGM10aRunLoopOffer(unittest.TestCase):
         self.assertEqual(cancels[0].event_type, MouseEventType.MOUSE_UP)
         self.assertEqual((cancels[0].position.left, cancels[0].position.top), (-1, -1))

+    def test_run_loop_forwards_the_mediators_real_offers_to_the_modal(self):
+        # GM-10b (review MAJOR): main must pass the mediator's LIVE current_offers into
+        # draw_offer_screen, not a placeholder -- replacing it with () would render an
+        # empty modal yet pass a spy that ignores the argument. Sentinel tuple pins it.
+        sentinel = ("offer-a", "offer-b")
+        harness = _drive_run_game(
+            [[]],
+            max_frames=1,
+            start_state=AppScreen.PLAYING,
+            pending=True,
+            offers=sentinel,
+        )
+        self.assertEqual(harness.controller.state, AppScreen.OFFER)
+        self.assertEqual(
+            harness.offer_renders,
+            [sentinel],
+            "the run loop forwarded the mediator's real current_offers",
+        )
+
     def test_closing_mid_offer_resolves_the_week_and_autosaves(self):
         # review MAJOR: a window-close WHILE the offer is up (frame 0 promotes, frame
         # 1 delivers QUIT with state already OFFER) resolves the week and autosaves
diff --git a/test/test_gm10b_offers.py b/test/test_gm10b_offers.py
new file mode 100644
index 0000000..a8cada3
--- a/test/test_gm10b_offers.py
+++ b/test/test_gm10b_offers.py
@@ -0,0 +1,372 @@
+"""GM-10b contract: the dedicated-RNG weekly offer generator (D-042).
+
+At each GM-10a week boundary the interactive game generates a deterministic SET of
+upgrade offers (data only -- applying a choice is GM-10c, per-kind effects GM-10d-g,
+replay/persistence reconciliation GM-10h). The offer RNG is a per-week `random.Random`
+derived READ-ONLY from the already-persisted gameplay RNG state + week_index, so:
+- offers are CONTINUE-EXACT (reproduce after save/load) with NO new persisted state;
+- generation is gameplay-INERT (consumes zero gameplay draws);
+- offers are gated to the human shell (calendar OFF => never generated for RL/headless).
+"""
+
+from __future__ import annotations
+
+import os
+import random
+import subprocess
+import sys
+import unittest
+
+sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
+
+import numpy as np
+import pygame
+
+from config import (
+    OFFERS_PER_WEEK,
+    WEEK_LENGTH_STEPS,
+    game_over_text_color,
+    screen_height,
+    screen_width,
+)
+from env import MiniMetroEnv
+from maps import resolve_map
+from mediator import Mediator
+from offers import Offer, OfferKind, describe, generate_offers
+from rl.player_env import PlayerPixelEnv
+from save_game import serialize_game
+from save_load import deserialize_game
+from ui.menu_screens import draw_offer_screen
+
+pygame.init()
+
+_SRC = os.path.dirname(os.path.realpath(__file__)) + "/../src"
+
+# Frozen seed-0 offer sequences, pinned as literals (never a runtime capture) so a
+# change to the generator, POOL ORDER, or derivation turns them red. CLASSIC (3-kind
+# pool) and RIVER (4-kind pool incl. TUNNEL -- week 3 here) lock BOTH pool orderings
+# behaviorally (review MINOR: a bounded-pool reorder must not survive the suite).
+# The exact values are implicitly coupled to CPython 3.13's `random.sample`; the repo
+# pins py313, so a Python bump would require re-pinning these literals.
+_SEED0_SEQUENCE = (
+    ("CARRIAGE", "NEW_LINE"),
+    ("NEW_LINE", "CARRIAGE"),
+    ("LOCOMOTIVE", "CARRIAGE"),
+    ("NEW_LINE", "CARRIAGE"),
+)
+_RIVER_SEED0_SEQUENCE = (
+    ("LOCOMOTIVE", "NEW_LINE"),
+    ("NEW_LINE", "CARRIAGE"),
+    ("NEW_LINE", "TUNNEL"),
+    ("LOCOMOTIVE", "CARRIAGE"),
+    ("CARRIAGE", "LOCOMOTIVE"),
+)
+
+
+def _played(seed, *, calendar=True, map_definition=None):
+    kwargs = {"seed": seed}
+    if map_definition is not None:
+        kwargs = {"seed": seed, "map_definition": map_definition}
+    m = Mediator(**kwargs)
+    m.week_calendar = calendar
+    path = m.create_path_from_station_indices([0, 1, 2])
+    m.assign_locomotive(path)
+    return m
+
+
+def _collect_offer_kinds(m, weeks):
+    out = []
+    while m.week_index < weeks and not m.is_game_over:
+        m.increment_time(17)
+        if m.is_week_boundary_pending:
+            out.append(tuple(o.kind.name for o in m.current_offers))
+            m.resolve_week_boundary()
+    return out
+
+
+def _step_to_first_boundary(m):
+    guard = 0
+    while not m.is_week_boundary_pending and guard < WEEK_LENGTH_STEPS * 2:
+        m.increment_time(17)
+        guard += 1
+    return m
+
+
+class TestGM10bGenerator(unittest.TestCase):
+    def test_generate_offers_is_distinct_and_deterministic(self):
+        a = generate_offers(random.Random(5), count=2, tunnels_bounded=True)
+        b = generate_offers(random.Random(5), count=2, tunnels_bounded=True)
+        self.assertEqual(a, b, "same RNG state -> same offers")
+        self.assertEqual(len(a), 2)
+        self.assertEqual(len({o.kind for o in a}), 2, "offers are DISTINCT kinds")
+        self.assertTrue(all(isinstance(o, Offer) for o in a))
+
+    def test_tunnel_excluded_on_unbounded_included_on_bounded(self):
+        # Over many draws, an unbounded (CLASSIC) pool NEVER offers TUNNEL; a bounded
+        # pool CAN. Pin the exact pool membership, not just one draw.
+        classic_kinds = set()
+        bounded_kinds = set()
+        for s in range(200):
+            classic_kinds |= {
+                o.kind
+                for o in generate_offers(
+                    random.Random(s), count=3, tunnels_bounded=False
+                )
+            }
+            bounded_kinds |= {
+                o.kind
+                for o in generate_offers(
+                    random.Random(s), count=4, tunnels_bounded=True
+                )
+            }
+        self.assertNotIn(
+            OfferKind.TUNNEL, classic_kinds, "no tunnel on an unbounded map"
+        )
+        self.assertEqual(
+            classic_kinds,
+            {OfferKind.NEW_LINE, OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE},
+        )
+        self.assertIn(
+            OfferKind.TUNNEL, bounded_kinds, "tunnel offered on a bounded map"
+        )
+        self.assertEqual(len(bounded_kinds), 4)
+
+    def test_labels_are_the_canonical_text(self):
+        self.assertEqual(describe(OfferKind.NEW_LINE).label, "New Line")
+        self.assertEqual(describe(OfferKind.LOCOMOTIVE).label, "+1 Locomotive")
+        self.assertEqual(describe(OfferKind.CARRIAGE).label, "+1 Carriage")
+        self.assertEqual(describe(OfferKind.TUNNEL).label, "+1 Tunnel")
+
+    def test_count_below_one_raises_named_error(self):
+        # review MINOR: cover zero AND negative -- `< 1` (not `== 0`) must guard both;
+        # a negative that slipped through would hit random.sample's generic error.
+        for bad in (0, -1, -5):
+            with self.assertRaisesRegex(ValueError, "positive number of offers"):
+                generate_offers(random.Random(0), count=bad, tunnels_bounded=True)
+
+    def test_count_above_pool_clamps_silently(self):
+        # Documented silent cap: count=9 over the 3-kind CLASSIC pool yields 3.
+        drawn = generate_offers(random.Random(0), count=9, tunnels_bounded=False)
+        self.assertEqual(len(drawn), 3)
+        self.assertEqual(len({o.kind for o in drawn}), 3)
+
+
+class TestGM10bMediatorOffers(unittest.TestCase):
+    def test_offers_generated_at_the_boundary_and_frozen_sequence(self):
+        self.assertEqual(_collect_offer_kinds(_played(0), 4), list(_SEED0_SEQUENCE))
+
+    def test_same_seed_same_offers(self):
+        self.assertEqual(
+            _collect_offer_kinds(_played(3), 3), _collect_offer_kinds(_played(3), 3)
+        )
+
+    def test_derivation_depends_on_week_index(self):
+        # review NIT: isolate week_index -- with the SAME python_random state, two
+        # different week_index values must yield DIFFERENT offer seeds. (A weaker
+        # "weeks differ" check passes even if week_index were dropped, since the
+        # gameplay state already moves each week.)
+        m = _played(0)
+        for _ in range(300):
+            m.increment_time(17)
+        state = m.context.python_random.getstate()
+        seeds = set()
+        original = m.steps
+        for wk_steps in (0, WEEK_LENGTH_STEPS, WEEK_LENGTH_STEPS * 5):
+            m.steps = wk_steps  # week_index is steps-derived
+            m.context.python_random.setstate(state)  # hold the gameplay state fixed
+            seeds.add(m._offer_rng_for_current_week().random())
+        m.steps = original
+        self.assertEqual(len(seeds), 3, "the seed varies with week_index alone")
+
+    def test_default_count_is_offers_per_week(self):
+        offers = _step_to_first_boundary(_played(0)).current_offers
+        self.assertEqual(len(offers), OFFERS_PER_WEEK)
+
+    def test_resolve_clears_the_offers(self):
+        m = _step_to_first_boundary(_played(0))
+        self.assertTrue(m.current_offers, "offers present while pending")
+        m.resolve_week_boundary()
+        self.assertEqual(m.current_offers, ())
+
+    def test_generation_consumes_zero_gameplay_draws(self):
+        # review MAJOR-3 (direct): deriving + generating offers must NOT advance
+        # EITHER gameplay stream -- both python_random AND numpy_random are persistence
+        # state that later station positions/colors consume, so a stray numpy draw
+        # here would silently shift the game (and survive a python-only check).
+        m = _played(0)
+        for _ in range(500):
+            m.increment_time(17)
+        before_py = m.context.python_random.getstate()
+        before_np = m.context.numpy_random.bit_generator.state
+        offers = generate_offers(
+            m._offer_rng_for_current_week(),
+            count=OFFERS_PER_WEEK,
+            tunnels_bounded=False,
+        )
+        self.assertEqual(
+            m.context.python_random.getstate(),
+            before_py,
+            "no python_random draw stolen",
+        )
+        self.assertEqual(
+            m.context.numpy_random.bit_generator.state,
+            before_np,
+            "no numpy_random draw stolen",
+        )
+        self.assertEqual(len(offers), OFFERS_PER_WEEK)
+
+    def test_calendar_on_has_identical_gameplay_state_to_off(self):
+        # The calendar+offer path leaves gameplay byte-identical to a calendar-OFF
+        # control at the same step (generation is inert; the hold just freezes).
+        on = _step_to_first_boundary(_played(0, calendar=True))
+        target = on.steps
+        off = _played(0, calendar=False)
+        while off.steps < target and not off.is_game_over:
+            off.increment_time(17)
+        self.assertEqual(off.steps, target)
+        self.assertEqual(
+            on.context.python_random.getstate(), off.context.python_random.getstate()
+        )
+        self.assertEqual(
+            on.context.numpy_random.bit_generator.state,
+            off.context.numpy_random.bit_generator.state,
+        )
+        self.assertEqual(on.deliveries, off.deliveries)
+
+    def test_offers_are_continue_exact_across_save_load(self):
+        # review BLOCKER fix: offers reproduce EXACTLY after a mid-game save/load
+        # (README "Continue resumes exactly"), because they derive from the restored
+        # gameplay RNG state -- no new persisted state. Cover a NON-ZERO seed too
+        # (review MAJOR): deserialize builds a temporary Mediator(seed=0) before
+        # restoring RNG, so a derivation accidentally salted by the CONSTRUCTOR seed
+        # would stay exact for seed 0 yet DIVERGE for seed 3 -- this catches that.
+        for seed in (0, 3):
+            straight = _collect_offer_kinds(_played(seed), 3)
+
+            mid = _played(seed)
+            while mid.steps < 2500 and not mid.is_game_over:
+                mid.increment_time(17)
+                if mid.is_week_boundary_pending:
+                    mid.resolve_week_boundary()
+            self.assertFalse(mid.is_week_boundary_pending, "save off a boundary")
+            loaded = deserialize_game(serialize_game(mid))
+            loaded.week_calendar = True
+            continued = []
+            while loaded.week_index < 3 and not loaded.is_game_over:
+                loaded.increment_time(17)
+                if loaded.is_week_boundary_pending:
+                    continued.append(tuple(o.kind.name for o in loaded.current_offers))
+                    loaded.resolve_week_boundary()
+            # The straight run's weeks that fall AFTER the save point must match.
+            self.assertEqual(
+                straight[-len(continued) :],
+                continued,
+                f"offers Continue-exact for seed {seed}",
+            )
+            self.assertTrue(continued, f"seed {seed} reached a post-save boundary")
+
+    def test_river_pool_frozen_sequence_locks_bounded_order(self):
+        # review MINOR: the BOUNDED (4-kind) pool order must be locked behaviorally,
+        # not just by set membership -- a LOCOMOTIVE<->CARRIAGE swap in _BOUNDED_POOL
+        # must turn this red. Week 3 draws TUNNEL, so the tunnel kind is exercised.
+        m = _played(0, map_definition=resolve_map("river", 1))
+        self.assertEqual(m.num_tunnels, 3)
+        self.assertEqual(_collect_offer_kinds(m, 5), list(_RIVER_SEED0_SEQUENCE))
+
+    def test_no_save_bytes_added(self):
+        # GM-10b persists nothing: a serialized doc has no offer keys and the rng
+        # block is unchanged (python + numpy only).
+        m = _played(0)
+        for _ in range(300):
+            m.increment_time(17)
+        doc = serialize_game(m)
+        self.assertNotIn("offers", doc)
+        self.assertNotIn("currentOffers", doc)
+        self.assertEqual(set(doc["rng"].keys()), {"python", "numpy"})
+
+
+class TestGM10bRLGatedOff(unittest.TestCase):
+    def test_headless_env_never_generates_offers(self):
+        env = MiniMetroEnv()
+        env.reset(seed=0)
+        for _ in range(WEEK_LENGTH_STEPS + 60):
+            env.mediator.step_time(17)
+        self.assertEqual(env.mediator.current_offers, (), "RL never generates offers")
+        self.assertFalse(env.mediator.week_calendar)
+
+    def test_pixel_env_never_generates_offers(self):
+        env = PlayerPixelEnv()
+        env.reset(seed=0)
+        m = env._mediator
+        for _ in range(WEEK_LENGTH_STEPS + 60):
+            m.step_time(17)
+        self.assertEqual(m.current_offers, (), "the pixel env never generates offers")
+
+
+class TestGM10bModalRender(unittest.TestCase):
+    def _frame(self, offers, week_index=3):
+        surface = pygame.Surface((screen_width, screen_height))
+        surface.fill((0, 0, 0))
+        draw_offer_screen(surface, week_index, offers)
+        return pygame.image.tobytes(surface, "RGB")
+
+    def _text_pixels(self, offers):
+        surface = pygame.Surface((screen_width, screen_height))
+        surface.fill((0, 0, 0))
+        draw_offer_screen(surface, 3, offers)
+        arr = pygame.surfarray.array3d(surface)
+        return int(np.count_nonzero((arr == game_over_text_color).all(axis=2)))
+
+    def test_offers_change_the_frame_and_each_label_contributes(self):
+        two = (describe(OfferKind.NEW_LINE), describe(OfferKind.LOCOMOTIVE))
+        one = (describe(OfferKind.NEW_LINE),)
+        none = self._frame(())
+        self.assertNotEqual(self._frame(one), none, "the first label renders")
+        self.assertNotEqual(
+            self._frame(two), self._frame(one), "the second label renders"
+        )
+
+    def test_label_glyphs_are_actually_painted_not_just_the_panel(self):
+        # review MAJOR: offer COUNT alone moves the panel/heading geometry, so a
+        # "frame changed" check passes even if NO label glyph is blitted. Count the
+        # TEXT-color pixels: offers must add glyph pixels BEYOND the heading+Continue
+        # text a no-offer frame already has. Removing the label blit turns this red.
+        two = (describe(OfferKind.NEW_LINE), describe(OfferKind.LOCOMOTIVE))
+        self.assertGreater(
+            self._text_pixels(two),
+            self._text_pixels(()),
+            "the offer label glyphs paint text pixels the panel alone does not",
+        )
+
+    def test_render_is_byte_stable_on_repeat(self):
+        offers = (describe(OfferKind.NEW_LINE), describe(OfferKind.CARRIAGE))
+        first = self._frame(offers)
+        self.assertEqual(self._frame(offers), first, "a fresh redraw is identical")
+        # Idempotent over EXISTING chrome too (opaque panel convention): drawing again
+        # onto the SAME surface leaves it byte-identical.
+        surface = pygame.Surface((screen_width, screen_height))
+        surface.fill((0, 0, 0))
+        draw_offer_screen(surface, 3, offers)
+        draw_offer_screen(surface, 3, offers)
+        self.assertEqual(pygame.image.tobytes(surface, "RGB"), first)
+
+
+class TestGM10bImportSafety(unittest.TestCase):
+    def test_offers_module_imports_without_pygame(self):
+        # review MINOR: actually VERIFY the import-safety contract -- assert pygame
+        # was NOT pulled in (a bare `import offers; print(...)` would pass even if
+        # offers imported pygame).
+        code = (
+            "import sys; sys.path.insert(0, r'%s'); import offers; "
+            "assert 'pygame' not in sys.modules, 'offers must stay pygame-free'; "
+            "print(offers.OfferKind.NEW_LINE.value)" % _SRC
+        )
+        result = subprocess.run(
+            [sys.executable, "-c", code], capture_output=True, text=True
+        )
+        self.assertEqual(result.returncode, 0, result.stderr)
+        self.assertEqual(result.stdout.strip(), "new_line")
+
+
+if __name__ == "__main__":
+    unittest.main()
```

## Docs
```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index 853a65c..a62cb80 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -379,6 +379,7 @@ python_mini_metro/
 - GM-09f2 (D-039) is the second GM-09f sub-unit: the high-score leaderboard records the MAP identity. Both game-over surfaces now hand the recorder the LIVE mediator (the controller seam passes `self.mediator`, and `main.run_game`'s promotion closure drops its old `SimpleNamespace(deliveries=...)` wrapper), so `main.record_highscore` reads `mediator.map_definition.{map_id, map_definition_version}` (direct, fail-SAFE: a missing map records nothing rather than mislabelling — no `or classic`) instead of hardcoding `classic`. `highscores` bumps to schema **v2** keyed by the full `(map, mapDefinitionVersion, rulesVersion)` identity via one shared `_identity` helper (sort + cap + rank), with the `map` grammar tightened to the save's mapId. A legacy v1 board is NOT migrated — it starts empty — because its classic labels are not provably accurate. This lands BEFORE the in-game menu (GM-09f3) so the recorder is already map-aware when non-Classic maps become selectable; `highscores` stays gameplay-free (no `maps` import) and in the persistence isolation set.
 - GM-09f3 (D-040) COMPLETES GM-09f with the in-game MAP MENU. `AppController` gains `current_map_id` (default `classic`), cycled by an appended title control `map` (`title_layout` appends the `"map"` key so the prior title rects stay byte-identical; `draw_title_screen` gains a `current_map_id` param and paints a `Map: {Name}` button; `main.run_game` threads `controller.current_map_id` into it). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]`: `main.run_game`'s `build_game(map_id)` resolves `maps.map_by_id(map_id)` into `Mediator(map_definition=…)` (every downstream layer was already map-aware, GM-09a–f2). NEW GAME / ENTER build `current_map_id`; RESTART (pause + game-over) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id` via `_restart_current_game` (so restarting a Continued River game gives River even when the picker sits on Lake); Continue installs the SAVED map and never consults the picker; the tutorial stays Classic. Only `main`+`app_controller`+`menu_screens` change; the headless/agent/recursive/RL entries construct `Mediator(map_definition=…)` directly and never meet the title picker.
 - GM-10a (D-041) opens GM-10 with the simulation CALENDAR. `config.WEEK_LENGTH_STEPS` defines a "week" in sim steps; `Mediator.increment_time`, after the COMPLETE tick (post queued-return settlement), holds a new `"week"` pause reason when `mediator.week_calendar` is on, the tick crossed a new boundary, and the run is not game over. `"week"` joins `_PAUSE_REASONS` (frozen by the existing gate; never cleared by Space/speed); `week_index` is a `steps`-derived property and `resolve_week_boundary()` releases the pause. The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it, so RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, and frame-limited/headless runs never pause — the calendar branch is never taken off the human path, so no `env.py`/checkpoint/save change and no determinism risk. The human shell adds `AppScreen.OFFER`: `AppController.reconcile_week_boundary()` (per-frame AFTER `reconcile_game_over`, so a terminal tick wins; cancelling any armed gesture via the pinned letterbox-cancel before switching) promotes a pending boundary to a modal whose armed Continue (`menu_screens.offer_menu_layout`/`draw_offer_screen`) resolves the week; `main` renders it over the frozen frame, resolves-then-autosaves on a mid-offer window close, and consumes the offer frame's audio silently; `save_game._require_quiescent` blocks saving while a boundary is pending. Persistence + the RL observation/offer are deferred to GM-10h/GM-10b.
+- GM-10b (D-042) adds the weekly OFFER GENERATOR. A new dependency-light `src/offers.py` (stdlib-only — `enum`/`dataclasses`/`random`, no pygame/mediator, so it is import-safe on every headless/RL path) owns the data model (`OfferKind`, frozen `Offer`, `describe`) and a PURE `generate_offers(rng, *, count, tunnels_bounded)` that draws `count` DISTINCT kinds via `rng.sample` from an explicitly-ordered pool — the four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map. `config.OFFERS_PER_WEEK` (2) sets the count. When `Mediator._maybe_hold_week_boundary` fires (same calendar/crossing/not-game-over gate as the hold), it stores `self.current_offers` from `generate_offers`; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel (byte-stable on repeat). The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr, cross-process stable) — a deliberate design choice (dual-plan-reviewed): reading the state consumes no gameplay draws (station spawns stay byte-identical) AND, because that gameplay RNG state is already restored exactly on Continue, the same week's offers reproduce byte-exact after save/load with NO new persisted state. So GM-10b adds ZERO save/checkpoint/observation bytes (the `rng` block, exact-key save validation, checkpoint schema, and every frozen fixture are untouched) and never runs off the human path. Applying a choice is GM-10c, per-kind effects GM-10d–g, and applied-offer/replay persistence GM-10h (which must not trail GM-10c). (Adding `offers.py` and editing the runtime `src` files rotates the LIVE RL content fingerprint — `compute_content_fingerprint` hashes all of `src/**` — so a pre-GM-10b manifest fails strict resume/eval by default; EXPECTED and correct for fresh runs, no frozen fixture is repinned since `EXPECTED_LF_TRAINING` pins only `TRAINING_SOURCE_PATHS`, which excludes these files.)
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
diff --git a/GAME_RULES.md b/GAME_RULES.md
index 0f6a9e1..d60511a 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -158,6 +158,7 @@ This document summarizes the game rules currently implemented in code.
   - ESC: exit (game-over screen).
 - The pause menu holds its own pause reason: opening it while SPACE-paused keeps both, and resuming from the menu releases only the menu hold, so the game stays paused until SPACE (or a speed button) clears the user pause. Speed-button selections still clear only the user pause and never the menu hold; the keyboard speed keys only set the speed and never unpause.
 - Weekly calendar (interactive play only): every fixed span of simulation time (a "week") the game pauses at a week boundary and shows a modal; click Continue to resume, and the sim carries on from exactly where it froze with no time backlog. This pause is its own reason — SPACE and the speed buttons cannot dismiss it, and saving is blocked until you Continue (closing the window mid-week resumes the game past the boundary via Continue). The calendar is a human-play feature: headless, RL, tutorial, and frame-limited runs never pause for a week. (GM-10a lays the calendar; the end-of-week upgrade choice arrives in later units.)
+- Weekly offers (interactive play only): the week-boundary modal previews a seeded SET of `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers, drawn from a pool of New Line, +1 Locomotive, +1 Carriage, and +1 Tunnel — the tunnel offer appears only on maps with a finite tunnel budget (never on open CLASSIC, which is unbounded). The offers are fully deterministic: they are generated from a dedicated per-week random stream derived from the game's own RNG state and the week number, so they consume no gameplay randomness (station spawns are byte-identical whether or not offers are generated) and reproduce EXACTLY when you Continue a saved game. GM-10b previews the offers read-only; choosing one to apply arrives in later units (its effect and its cross-Continue persistence with it).
 - Autosave: opening the pause menu and Exit to Title each write a single autosave to `saves/autosave.json`, and closing the window mid-run keeps it, so the title screen's Continue reloads the game exactly where you left off (releasing the menu pause, honoring a held SPACE pause). Reaching game over deletes the autosave, so a finished run cannot be Continued; every autosave is best-effort and never blocks play or exit.
 - Tutorial: a coached playthrough reached from the title screen. It runs a real seeded game with on-screen prompts that walk through drawing a line, rerouting it, adding a train, delivering a passenger, overload pressure, pausing, and changing speed; each lesson advances when you actually perform it (overload advances after a few seconds of watching). Press Esc to skip or leave at any point. The tutorial game never ends (so a first-timer cannot lose mid-lesson) and never autosaves or records a high score. It is presentation only and changes no game rules or balance.
 - Settings: a Settings screen, reached from the title or pause menu (Back returns to whichever opened it, and opening it from the pause menu keeps the game paused), toggles fullscreen, steps the master/music/SFX volumes in 25% increments, and toggles reduced motion. Settings persist to `saves/settings.json` and survive restart; fullscreen applies to the live window and reduced motion holds the passenger-warning, station-unlock, and path-button blinks steady while suppressing the snap-blip rings (the master and SFX volumes scale the procedural audio cues). Settings are presentation-only and change no game balance; a missing or corrupt settings file falls back to the defaults and never blocks play.
diff --git a/PROGRESS.md b/PROGRESS.md
index e7f6d1c..cce089d 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -181,3 +181,4 @@
 - COMPLETED GM-09f with GM-09f3, the in-game MAP MENU (D-040) -- the payoff that lets a human pick `classic`/`river`/`delta`/`lake` from the title. `AppController` gains `current_map_id` (default classic), cycled by an appended title `map` control (`title_layout` appends the key so prior title rects stay byte-identical; `draw_title_screen` gains `current_map_id` and paints a `Map: {Name}` button; `main` threads `controller.current_map_id`). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]` -- `main.run_game`'s `build_game(map_id)` resolves `map_by_id(map_id)` into `Mediator(map_definition=...)` (every downstream layer was already map-aware, GM-09a-f2). NEW GAME / ENTER build the picker; RESTART (pause + game-over) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id` (`_restart_current_game`), so restarting a Continued River game gives River even with the picker on Lake; Continue installs the SAVED map; the tutorial stays Classic. Dual plan review (both REVISE, architecture UPHELD): Codex caught the Restart-switches-map MAJOR the harness rated acceptable, drove the uniform seam arity, the 11-callable fake update (incl. the dangerous `_title_build_game(mediator=None)` positional collision), and the crossing-gate composition test; alphabetical cycle order kept. Editing app_controller/main/menu_screens rotates the live RL content fingerprint (expected; no fixture repin -- `EXPECTED_LF_TRAINING` pins only training sources). Full `py313` suite green (1472 tests, 12 skips); app_controller 424, main 440, menu_screens 297 lines. GM-09 (maps + save/high-score/menu integration) is COMPLETE; GM-10 (weekly progression) opens next.
 - Closed the GM-09c abort-inertness follow-up (`task_384488d0`), fixing the two PRE-EXISTING non-inert traces a cancelled path draft left in `PathLifecycle.abort_path_creation` -- both surfaced by the GM-09c review but deferred there because the obvious fixes broke CLASSIC byte-identity. (1) The transient snap-blips a draft paints as it grows (`add_station_to_path`/`end_path_on_station`) leaked into the canonical checkpoint (serialized raw, pruned only by `increment_time` on expiry), so a headless `MiniMetroEnv` rollout checkpointed a cancelled draft indefinitely; `_paint_creation_snap_blip` now records each painted blip (the tuple `start_snap_blip` actually appends -- `Station.start_snap_blip` now RETURNS it, coupling the receipt to the real append so a non-appending station leaves no phantom) and abort drops exactly those by LAST value-match, which -- since `start_snap_blip` has one caller and only one draft is live -- is provably the draft's own blip even when a removed line's reclaimed-color blip lingers beside it (identity is unusable because `prune_visual_effects` rebuilds the tuples each tick; a color match would erase the survivor). (2) A mid-draft `remove_path` runs `assign_paths_to_buttons`, binding the still-drafting path to a button; abort now detaches that one mapping (`path_to_button.pop` + `PathButton.remove_path` if it still points at the draft) surgically -- NOT a full reassign -- so no colored button points at a removed line. `finish` forgets a committed draft's receipts (no unbounded bookkeeping). Byte-identity is exact and PROVEN by a whole-src HEAD-shadow differential: a drag-then-FINISH (committed line) and the ghost scenario are byte-identical to pre-change HEAD, and only a drag-then-ABORT differs, by exactly the removed draft blips (the button detach is checkpoint-invisible -- `button.path` derefs to `None` either way); `save-v1.json`/`save-v2-classic.json` (which serialize `snapBlips`, empty in the fixtures) and the GM-09a construct/trajectory fingerprints are unmoved. TDD: six red-first tests (fully-inert CLASSIC checkpoint, reclaimed-color collision, an adversarial same-time ordering case that a remove-FIRST would fail, duplicate re-snap, ghost button, no-op-when-unbound guard) plus a component-level abort-detach test; the GM-09c `test_rejected_multistation_creation` was strengthened from RNG-inert to FULLY checkpoint-inert. Triple adversarial review (two harness lanes -- byte-identity + correctness/contract, both HOLD -- and external Codex ultra) because the last three review rounds each caught a byte-identity regression in this exact area; Codex caught a stale-doc regression BOTH harness lanes missed (this ARCHITECTURE.md GM-09c note and the `finish`/`end_path` comments still said abort was "unchanged / left to a follow-up") and drove the receipt-to-append coupling and the commit-time receipt clear. Full `py313` suite green (1484 tests, 12 skips); `path_lifecycle.py` gains three small helpers, no new module.
 - Opened GM-10 with GM-10a, the simulation CALENDAR (D-041) -- the foundation for weekly progression. A "week" is `config.WEEK_LENGTH_STEPS` (1200 ≈ 20s at 1x); `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement), holds a new `"week"` pause reason when the calendar is enabled, a new boundary crossed (`old//W < steps//W`), and not game over. `"week"` joins `_PAUSE_REASONS` (never cleared by Space/speed); `week_index` is `steps`-derived (no new persisted scalar); `resolve_week_boundary()` releases it. The calendar is OPT-IN, default OFF -- only INTERACTIVE `main.run_game` (build_game/build_from, gated on `max_frames is None`) enables it, so RL/tutorial/headless never pause. The human shell adds `AppScreen.OFFER`: `reconcile_week_boundary()` (per-frame AFTER game-over reconcile, cancelling any gesture) promotes to a modal whose armed Continue resolves the week; window-close mid-offer resolves+autosaves; offer-frame audio consumed silently; saving blocked while pending. HIGH-RISK -> DUAL plan review, both REVISE (harness 1 BLOCKER; Codex 2 BLOCKER + 4 MAJOR with reproduced counterexamples). GATING to the human shell resolved the BLOCKERs structurally: my first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` drives via `advance_exact` and the tutorial is a third direct-Mediator shell -- all would soft-lock at step 1200; gating (week_calendar default OFF) means the branch is never taken off the human path (no env.py/checkpoint/save change, no determinism risk). Codex also refuted my "pause is trajectory-invariant" probe (it bypassed the FixedStepClock cadence) -- gating moots it. The hold-after-full-tick (settlement), terminal precedence, gesture-cancel+arming, and window-close edges were all folded with pinned regressions. The DUAL impl review then confirmed the production code CORRECT on both lanes, with all findings TEST-STRENGTH: Codex mutation-proved six survivors the harness rated shippable (an exact-landing-only hold, a hold-before-settlement, a dropped not-game-over guard, a truthy-not-`is True` OFFER guard, a wrong letterbox-cancel event, and a missing run-loop OFFER promotion/QUIT path), each now pinned (a genuine-crossing speed-4 test, a queued-settlement-parity test, a live-Mock `is True` test, an exact-cancel-event assertion, and real-`run_game` gating + OFFER-loop integration tests). Full `py313` suite green (1507 tests). GM-10b (dedicated-RNG offers) opens next.
+- Continued GM-10 with GM-10b, the dedicated-RNG weekly OFFER GENERATOR (D-042). A new stdlib-only `src/offers.py` (`OfferKind`/`Offer`/pure `generate_offers`) draws `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers from a map-appropriate pool (New Line / +1 Locomotive / +1 Carriage, plus +1 Tunnel only on a finite-tunnel map); `Mediator._maybe_hold_week_boundary` stores `current_offers` at the hold and `resolve_week_boundary` clears them; `draw_offer_screen` previews the labels read-only. The offer RNG is a dedicated per-week `random.Random` derived READ-ONLY from `python_random.getstate()` + `week_index` — a DUAL-PLAN-REVIEW pivot: Codex BLOCKED the first plan (a persisted `spawn(3)` stream deferred to GM-10h would RESET on Continue and diverge, violating README's "Continue resumes exactly"), so offers are instead derived from the already-persisted gameplay RNG state, making them Continue-EXACT with ZERO new save/checkpoint/observation bytes and gameplay-INERT (getstate consumes no draws — station spawns stay byte-identical, every frozen fixture untouched). Gated to the human shell like the calendar, so RL/headless/tutorial never generate (`current_offers` stays `()`). Empirically pre-validated (cadence ~4-6 weeks/game; separate-stream inertness; spawn byte-compat; Continue-exactness of the boundary python-state — all proven before planning). Dual plan review (harness REVISE + Codex BLOCK → the stateless pivot) + dual impl review folded. Applying a choice is GM-10c, per-kind effects GM-10d-g, applied-offer persistence GM-10h (which must not trail GM-10c). Full `py313` suite green (1527 tests).
diff --git a/README.md b/README.md
index 44ef9f8..fb70143 100644
--- a/README.md
+++ b/README.md
@@ -66,7 +66,7 @@ Set `PYTHON` to a specific interpreter path when `python` is not the intended ex
 * Opening the pause menu autosaves your game to `saves/autosave.json`; Exit to Title rewrites the same save before leaving, and closing the window mid-run keeps it, so Continue on the title screen resumes exactly where you left off. Reaching game over deletes the autosave, so a finished run cannot be Continued.
 * Finishing a run records its lifetime deliveries to a high-score leaderboard at `saves/highscores.json` (ranked and capped per map and rules version); a new best shows a compact indicator on the game-over screen.
 * Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
-* Every week of play the game pauses at a week boundary and shows a modal; click Continue to resume (the sim carries on with no time backlog). This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week.
+* Every week of play the game pauses at a week boundary and shows a modal previewing that week's upgrade offers (a seeded pick of New Line / +1 Locomotive / +1 Carriage / +1 Tunnel — tunnel offers appear only on maps with a tunnel budget); click Continue to resume (the sim carries on with no time backlog). The offers are deterministic and reproduce exactly on Continue; choosing one to apply is a later step. This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week or generate offers.
 * The top-left HUD shows lifetime passengers delivered, currently spendable line credits, unassigned locomotives, and unassigned carriages as separate values.
 * Each filled grey circle at the bottom is an unused unlocked metro line slot.
 * Hold an assigned colored circle, drag through the replacement station order, and release on the final station to redraw that line; the selected circle is outlined and an invalid repeated-station draft turns red.
diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index 3d77db1..fa7a8ab 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -257,3 +257,9 @@ Reason: the save (GM-09f) and high-score (GM-09f2) recorders were deliberately m
 Decision: GM-10a opens GM-10 (weekly progression) with the simulation CALENDAR — a deterministic week boundary that pauses the sim for an explicit player continue, the foundation the later sub-units (GM-10b offers, GM-10c choice UI, GM-10d-g upgrades, GM-10h persistence) build on. A "week" is `config.WEEK_LENGTH_STEPS` sim steps (provisional 1200 ≈ 20 s at 1×, a GM-11 balance target). `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement — placement matters, review MAJOR), holds a new `"week"` pause reason when the calendar is enabled, this tick crossed a new boundary (`old_steps // W < steps // W`, integer division so 1×/2×/4× never skip), and the run is NOT game over (so a terminal tick promotes to GAME_OVER, review MAJOR). `"week"` joins `_PAUSE_REASONS` and freezes the sim through the existing gate; unlike `"user"`/`"menu"` it is never cleared by the Space toggle or speed buttons. `week_index` is DERIVED from the already-persisted `steps` (no new stored scalar). The human shell promotes a pending boundary to a new `AppScreen.OFFER` modal via `AppController.reconcile_week_boundary()` — run per-frame AFTER `reconcile_game_over`, no-op unless PLAYING/not-terminal, cancelling any armed gameplay gesture through the pinned letterbox-cancel before switching (review MAJOR) — whose armed Continue (down→up on the control) calls `mediator.resolve_week_boundary()` and resumes PLAYING (review MAJOR). Closing the window mid-offer resolves then autosaves (window-close→Continue promise, review MINOR); the offer frame's audio deltas are consumed silently (review MINOR); saving is blocked while a boundary is pending (a clearer error over `validate_save`'s existing vocabulary rejection). The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it; RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, frame-limited/headless smoke runs, and all tests leave it off. NO save-schema and NO checkpoint-schema change; the RL observation of the week and mid-offer persistence are deferred to GM-10b/GM-10h.

 Reason: the DUAL plan review (both REVISE) was decisive — the harness caught a BLOCKER and Codex went far deeper (2 BLOCKER + 4 MAJOR with reproduced live counterexamples). (1) My first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` (the first-class RL boundary) drives via `GameSession.advance_exact` and the tutorial is a third direct-Mediator shell — all would soft-lock permanently at step 1200. GATING the calendar to interactive human play (a `week_calendar` flag, default OFF) resolves every headless shell structurally (the hold never occurs) and removes the `env.py` change entirely. (2) My "a pause is trajectory-invariant" premise was FALSE — my probe used direct `increment_time` (fixed 17 ms) and bypassed the `(17,17,16)` `FixedStepClock` cadence, which a pause resets, so `time_ms` diverges at identical `steps`; but gating keeps the calendar out of every deterministic/RL/exact-tick path, so their trajectory is byte-identical (the branch is never taken), and the cadence reset is PRE-EXISTING behavior shared by the `user`/`menu` pauses on the already-non-deterministic human wall-clock path — so no version bump and no clock fix here. (3) The hold placement, terminal precedence, gesture-cancel/arming, window-close, and audio edges were all reproduced by Codex and folded with pinned regressions. Persistence is deferred because GM-10h owns it and `week_index` rides on `steps`; the RL offer integration is GM-10b/GM-12. `WEEK_LENGTH_STEPS=1200` is a provisional foundation default (fixed, not escalating — escalation is GM-11). GM-10b (deterministic dedicated-RNG offers) opens next.
+
+## D-042
+
+Decision: GM-10b adds the weekly OFFER GENERATOR — a new stdlib-only `src/offers.py` (`OfferKind`, frozen `Offer`, `describe`, pure `generate_offers(rng, *, count, tunnels_bounded)`) plus mediator/UI wiring. At each held week boundary, `Mediator._maybe_hold_week_boundary` (same calendar/crossing/not-game-over gate as the hold) stores `self.current_offers` = `generate_offers` of `config.OFFERS_PER_WEEK` (2) DISTINCT kinds drawn via `rng.sample` from an explicitly-ordered pool — four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC, `num_tunnels is None`) map; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel. The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr — cross-process stable, never the salted builtin `hash()`). GM-10b adds NO `SimulationContext`/save-schema/checkpoint/observation change: offers are transient (never serialized) and derived from already-persisted state, so they are Continue-EXACT with ZERO new persisted bytes and every frozen fixture is untouched. Gated to the human shell like the calendar (RL/headless/tutorial never generate). Applying a choice is GM-10c, per-kind effects GM-10d–g, applied-offer/replay persistence GM-10h.
+
+Reason: a design PIVOT forced by the dual plan review (harness REVISE, Codex BLOCK). Plan v1 used a persisted dedicated `SeedSequence.spawn(3)` `offer_random` stream with persistence DEFERRED to GM-10h — but Codex proved (verified against `README.md:66` "Continue … resumes exactly") that an unpersisted stream RESETS on load, so the next week's offers would DIVERGE from uninterrupted play. The harness lane had rated the same deferral "clean" — the two-lane disagreement is the review-coverage lesson. Codex's own suggested alternative — "generate statelessly from already-persisted inputs" — is the resolution, and it is STRICTLY simpler: no `SimulationContext` change, no schema migration, and it dissolves the gesture-rollback-snapshot concern (no offer-stream state to roll back). Four premises were empirically proven BEFORE the plan (per the observer-predicate lesson): games last ~4–6 weeks (offers are meaningful), a separate offer stream is gameplay-inert, `spawn` is byte-back-compatible (moot after the pivot), and — the load-bearing one — `python_random.getstate()` at a week boundary is byte-identical after a mid-game save→load (so the derived offers reproduce exactly). ORDERING CONSTRAINT (review MINOR): GM-10c (apply a choice) must NOT ship ahead of GM-10h (applied-offer/replay persistence), or a Continue could inconsistently resurrect/replace an applied choice. `OFFERS_PER_WEEK=2` is a provisional balance default (GM-11 may tune it); a value above the CLASSIC pool size would silently clamp there (documented at the `min` clamp). GM-10c (choice controls) opens next.
```
