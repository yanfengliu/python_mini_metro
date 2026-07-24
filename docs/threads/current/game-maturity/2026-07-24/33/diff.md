# GM-10i — diff (src + tests, post-impl-review)

The final save-schema v4 change + tests, after the dual impl-review folds (the load-symmetric serialize guard, the added test-strength cases). The two new fixtures (`scripts/fixtures/save-v4-classic.json`, `save-v4-river-pending.json`) and the new `test/test_gm10i_pending.py` are working-tree files (not in this tracked diff).

```diff
diff --git a/src/main.py b/src/main.py
index d5a1acf..15e9de6 100644
--- a/src/main.py
+++ b/src/main.py
@@ -329,12 +329,11 @@ def run_game(
                 # boundary, drop a finished run's save, and touch nothing on the
                 # title screen (nor for a non-game controller).
                 if controller.state is AppScreen.OFFER:
-                    # Closing mid-offer (GM-10a): resolve the week with NO choice (the
-                    # no-arg forced resolve -- the player did not pick an offer) and
-                    # autosave the resumed game, so Continue reloads past the boundary.
-                    # Applied-offer (fleet/tunnel) persistence is GM-10h; persisting a
-                    # PENDING offer so a mid-offer Continue re-presents it is GM-10i.
-                    controller.mediator.resolve_week_boundary()
+                    # Closing mid-offer (GM-10i, D-047): PERSIST the pending boundary (the
+                    # "week" pause + the shown offers via save-schema v4) WITHOUT resolving,
+                    # so Continue reloads INTO the modal re-presenting the SAME offers. (The
+                    # GM-10a behavior force-resolved with no choice; the offers are now
+                    # savable, so a player who closes mid-offer keeps the choice.)
                     write_autosave(controller.mediator)
                 elif controller.state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU):
                     if controller.mediator.is_game_over:
diff --git a/src/mediator.py b/src/mediator.py
index 1bfb424..9cef703 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -169,9 +169,10 @@ class Mediator:
         # human PLAYING shell (main.run_game's build_game/build_from) sets this True.
         self.week_calendar = False
         # GM-10b (D-042): the upgrade offers generated for the current held week
-        # boundary; empty except while an offer is pending. Transient (NOT persisted)
-        # -- offers are re-derived Continue-exact from the already-persisted RNG state
-        # (see _offer_rng_for_current_week), so no new save/checkpoint bytes.
+        # boundary; empty except while an offer is pending. GM-10i (D-047) PERSISTS them
+        # (a save-schema-v4 `pendingOffers` key) while a boundary is held, so a mid-offer
+        # Continue re-presents the SAME offers; a non-pending game stores an empty list and
+        # RL/headless (no calendar) never holds a boundary, so no checkpoint bytes change.
         self.current_offers: tuple[Offer, ...] = ()
         # GM-10h (D-045): persisted +N on the map's tunnel budget from a TUNNEL weekly
         # upgrade (GM-10g). 0 until an upgrade is applied; folded into num_tunnels only
diff --git a/src/save_game.py b/src/save_game.py
index 010ef39..6779a1a 100644
--- a/src/save_game.py
+++ b/src/save_game.py
@@ -1,9 +1,10 @@
 """GM-07b saver: pure quiescent-boundary state capture and atomic saves.

 serialize_game reads live state through attributes only (never through
-mutating getters), rejects mid-gesture boundaries + a desynced/forged upgrade
-state, and returns a strict schema-v3 document (v2 adds the map identity, GM-09f;
-v3 adds the tunnel-upgrade bonus, GM-10h); save_game writes its canonical ASCII
+mutating getters), rejects mid-gesture boundaries + a below-config/forged upgrade
+state, and returns a strict schema-v4 document (v2 adds the map identity, GM-09f;
+v3 the tunnel-upgrade bonus, GM-10h; v4 a held week boundary's pendingOffers,
+GM-10i); save_game writes its canonical ASCII
 bytes through a save-local mkstemp -> fsync -> os.replace atomic writer, so a
 failed save leaves the destination untouched and no temporary file behind.
 """
@@ -17,6 +18,7 @@ from typing import Any

 from config import num_carriages as config_num_carriages
 from config import num_metros as config_num_metros
+from offers import OfferKind
 from recursive_checkpoint_schema import safe_checkpoint_value
 from save_load import _require_legal_map_state, deserialize_game, load_game
 from save_schema import (
@@ -76,16 +78,11 @@ def _require_quiescent(mediator: Any) -> None:
         raise ValueError("cannot save during a path redraw gesture")
     if mediator.path_edit_selection is not None:
         raise ValueError("cannot save during a path edit selection")
-    # GM-10a: a pending week-boundary offer is a transient, unresolved choice that is
-    # not persisted (persisting a PENDING offer for a mid-offer Continue is GM-10i;
-    # GM-10h persists only APPLIED fleet/tunnel upgrades). validate_save
-    # already rejects a "week" pause reason before any file I/O; this gives the
-    # clearer, actionable error at the save boundary. Defensive getattr keeps
-    # non-Mediator save shapes (which never hold "week") working.
-    if getattr(mediator, "is_week_boundary_pending", False):
-        raise ValueError(
-            "cannot save while a week-boundary offer is pending; resolve it first"
-        )
+    # GM-10i (D-047): a PENDING week-boundary offer is now SAVED (the "week" pause + the
+    # `pendingOffers` kinds), so a mid-offer Continue re-enters the modal. A path GESTURE
+    # still cannot be mid-save -- but at a held boundary the modal has cancelled any
+    # gesture, so the checks above pass; the pending offers' element types + pool legality
+    # are enforced by `_require_valid_pending_offers` before the atomic write.


 def _require_canonical_fleet(mediator: Any) -> None:
@@ -132,6 +129,38 @@ def _require_valid_upgrade_state(mediator: Any) -> None:
         )


+def _require_valid_pending_offers(mediator: Any) -> None:
+    # GM-10i (D-047): a held week boundary persists its SHOWN offers (`current_offers`),
+    # restored VERBATIM on load. The offers are deliberately NOT re-derived at serialize
+    # either: the derivation inputs (WEEK_LENGTH_STEPS/OFFERS_PER_WEEK/the pool) are
+    # provisional (GM-11), so a state LOADED under old rules must stay RE-SAVABLE -- a
+    # serialize-time `== canonical` check would make a valid loaded pending state
+    # un-rewritable across a balance change (Codex impl review BLOCKER). We reject only what
+    # LOAD would reject, before the atomic write, so serialize never clobbers a valid
+    # autosave with an unloadable one. `validate_save` (run at the end of serialize) already
+    # enforces the distinct/known kinds and the pendingOffers<->"week" consistency; the two
+    # invariants it can't see -- it lacks the resolved map and the live objects -- are the
+    # element types and pool legality (a TUNNEL offer is legal only on a bounded map),
+    # checked HERE with actionable errors (fleet error-message rule).
+    offers = getattr(mediator, "current_offers", ())
+    if not isinstance(offers, tuple):
+        raise ValueError(
+            f"current_offers must be a tuple of Offers, got {type(offers).__name__}"
+        )
+    bounded = mediator.map_definition.tunnel_budget is not None
+    for index, offer in enumerate(offers):
+        kind = getattr(offer, "kind", None)
+        if not isinstance(kind, OfferKind):
+            raise ValueError(
+                f"current_offers[{index}] is not a valid Offer (kind={kind!r})"
+            )
+        if kind is OfferKind.TUNNEL and not bounded:
+            raise ValueError(
+                "cannot save a TUNNEL offer on the unbounded-tunnel map "
+                f"{mediator.map_definition.map_id!r}: its offer pool excludes TUNNEL"
+            )
+
+
 def _station_records(mediator: Any) -> list[dict[str, Any]]:
     active_count = len(mediator.stations)
     prefix = mediator.all_stations[:active_count]
@@ -268,11 +297,13 @@ def _spawn_timer_records(mediator: Any) -> list[list[Any]]:


 def serialize_game(mediator: Any) -> dict[str, Any]:
-    """Capture one strict v3 save document (map identity + tunnel-upgrade bonus)
-    without mutating the Mediator; rejects a below-config fleet or an unreachable
-    tunnel bonus BEFORE the atomic write (GM-10h)."""
+    """Capture one strict v4 save document (map identity + tunnel-upgrade bonus + a held
+    week boundary's pendingOffers) without mutating the Mediator; rejects a below-config
+    fleet, an unreachable tunnel bonus, or a pool-illegal/malformed pending offer BEFORE
+    the atomic write (GM-10h/GM-10i)."""

     _require_valid_upgrade_state(mediator)
+    _require_valid_pending_offers(mediator)
     map_id, map_definition_version = _require_serializable_map(mediator)
     _require_quiescent(mediator)
     _require_canonical_fleet(mediator)
@@ -305,6 +336,11 @@ def serialize_game(mediator: Any) -> dict[str, Any]:
         "numMetros": mediator.num_metros,
         "numCarriages": mediator.num_carriages,
         "tunnelBonus": getattr(mediator, "tunnel_bonus", 0),
+        # GM-10i: the ORDERED kinds of a HELD week-boundary offer ([] when not pending);
+        # restored verbatim on load so a mid-offer Continue re-presents the SAME offers.
+        "pendingOffers": [
+            offer.kind.value for offer in getattr(mediator, "current_offers", ())
+        ],
         "stations": _station_records(mediator),
         "passengers": _passenger_records(mediator),
         "paths": _path_records(mediator),
diff --git a/src/save_load.py b/src/save_load.py
index b2e251b..80f6693 100644
--- a/src/save_load.py
+++ b/src/save_load.py
@@ -30,7 +30,11 @@ from geometry.type import ShapeType
 from graph.node import Node
 from mediator import Mediator
 from recursive_checkpoint_schema import safe_checkpoint_value
-from save_schema import SAVE_SCHEMA_VERSION_V3, validate_save
+from save_schema import (
+    SAVE_SCHEMA_VERSION_V3,
+    SAVE_SCHEMA_VERSION_V4,
+    validate_save,
+)
 from travel_plan import TravelPlan
 from utils import get_shape_from_type

@@ -52,13 +56,20 @@ def _require_running_config(document: dict[str, Any]) -> None:
     # KeyError. A further relaxation is a future schema version's business (D-026).
     if document["numPaths"] != config_num_paths:
         _fail("numPaths disagrees with the running config")
-    is_v3 = document["schemaVersion"] == SAVE_SCHEMA_VERSION_V3
+    # GM-10h relaxed the fleet pin for v3; GM-10i (D-047) EXTENDS it to v4 -- the grown
+    # fleet is a v3-and-later capability, so a v4 mid-offer save made AFTER a locomotive/
+    # carriage upgrade (numMetros/numCarriages ABOVE config) must load, not be rejected by
+    # the legacy exact-equality branch.
+    grown_fleet_ok = document["schemaVersion"] in (
+        SAVE_SCHEMA_VERSION_V3,
+        SAVE_SCHEMA_VERSION_V4,
+    )
     for key, expected in (
         ("numMetros", config_num_metros),
         ("numCarriages", config_num_carriages),
     ):
         actual = document[key]
-        if is_v3:
+        if grown_fleet_ok:
             if actual < expected:
                 _fail(f"{key} is below the running config")
         elif actual != expected:
@@ -355,7 +366,12 @@ def _require_legal_map_state(mediator: Any, map_def: Any) -> None:


 def deserialize_game(document: Any) -> Mediator:
-    """Reconstruct one Mediator from a validated v1 or v2 save document (GM-09f)."""
+    """Reconstruct one Mediator from a validated v1/v2/v3/v4 save document.
+
+    v2 adds the map identity (GM-09f), v3 the fleet/tunnel upgrade totals (GM-10h), and
+    v4 a HELD week-boundary offer (GM-10i) -- restored so a mid-offer Continue re-enters
+    the modal. Older shapes load unchanged (synthesizing classic@1 / a 0 bonus / no
+    pending boundary), so the byte-frozen fixtures stay valid."""

     from maps import resolve_map

@@ -383,9 +399,38 @@ def deserialize_game(document: Any) -> Mediator:
     _restore_buttons(mediator, coerced)
     # The reconstructed state must be legal under its own map (rejects a forged save).
     _require_legal_map_state(mediator, map_definition)
+    _restore_pending_offers(mediator, coerced, map_definition)
     return mediator


+def _restore_pending_offers(
+    mediator: Mediator, document: dict[str, Any], map_def: Any
+) -> None:
+    # GM-10i (D-047): restore a HELD week boundary's offers VERBATIM from `pendingOffers`
+    # (never re-derived -- the derivation inputs WEEK_LENGTH_STEPS/OFFERS_PER_WEEK/pool are
+    # provisional balance defaults (GM-11), so a re-derive could diverge from what the save
+    # actually showed). The schema already pinned each kind valid+distinct and non-empty
+    # exactly when a "week" boundary is held (and not on a finished game). The one map-aware
+    # check needs the resolved map: a TUNNEL offer is impossible on an unbounded map (its
+    # pool excludes it), so reject it fail-closed like the map-legality guard.
+    from offers import OfferKind, describe
+
+    kinds = document.get("pendingOffers", ())
+    if not kinds:
+        return
+    bounded = map_def.tunnel_budget is not None
+    restored = []
+    for value in kinds:
+        kind = OfferKind(value)
+        if kind is OfferKind.TUNNEL and not bounded:
+            raise ValueError(
+                f"cannot load a TUNNEL offer on the unbounded map {map_def.map_id!r}: "
+                "its offer pool excludes TUNNEL"
+            )
+        restored.append(describe(kind))
+    mediator.current_offers = tuple(restored)
+
+
 def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
     # Default json.loads collapses duplicate keys before exact-key
     # validation ever sees them; strict loading rejects every level.
diff --git a/src/save_schema.py b/src/save_schema.py
index 4bca7b9..38f3bd7 100644
--- a/src/save_schema.py
+++ b/src/save_schema.py
@@ -12,6 +12,7 @@ from __future__ import annotations
 import json
 from typing import Any

+from offers import OfferKind
 from recursive_checkpoint_schema import safe_checkpoint_value
 from save_schema_records import (
     _array,
@@ -50,16 +51,39 @@ SAVE_SCHEMA_VERSION_V2 = 2
 # so the byte-frozen `save-v1.json`/`save-v2-classic.json` stay valid. New saves
 # are v3. `stateContract`/`rulesVersion` STABLE across v1/v2/v3.
 SAVE_SCHEMA_VERSION_V3 = 3
-SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V3
+# GM-10i (D-047): v4 is a strict SUPERSET of v3 -- it adds one additive key,
+# `pendingOffers` (the ORDERED kinds of a HELD week-boundary offer, so a mid-offer save
+# reloads INTO the modal re-presenting the SAME offers), and v4-gates "week" into the
+# pause vocabulary (only a v4 save may carry a pending boundary). The offers are STORED,
+# not re-derived on load: `WEEK_LENGTH_STEPS`/`OFFERS_PER_WEEK`/the pool are provisional
+# balance defaults (GM-11 may tune them), so a re-derive would diverge across a rules
+# change -- storing the shown kinds keeps a v4 save self-contained. A v1/v2/v3 document
+# (no `pendingOffers`, no "week") still loads, so the byte-frozen fixtures stay valid.
+# New saves are v4. `stateContract`/`rulesVersion` STABLE across v1/v2/v3/v4.
+SAVE_SCHEMA_VERSION_V4 = 4
+SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V4
 SUPPORTED_SAVE_SCHEMA_VERSIONS = {
     SAVE_SCHEMA_VERSION_V1,
     SAVE_SCHEMA_VERSION_V2,
     SAVE_SCHEMA_VERSION_V3,
+    SAVE_SCHEMA_VERSION_V4,
 }
 SAVE_STATE_CONTRACT = "mini-metro-save-v1"
 SAVE_RULES_VERSION = "rules-v1"

+# GM-10i: "week" (a held boundary) is a v4-ONLY pause reason -- v1/v2/v3 never carry it,
+# so the frozen fixtures' validation is unchanged and older code (max v3) rejects a v4
+# save wholesale. `_pause_reason_vocabulary_for` selects by version.
 _PAUSE_REASON_VOCABULARY = frozenset({"menu", "user"})
+_PAUSE_REASON_VOCABULARY_V4 = _PAUSE_REASON_VOCABULARY | {"week"}
+
+
+def _pause_reason_vocabulary_for(version: int) -> frozenset[str]:
+    if version == SAVE_SCHEMA_VERSION_V4:
+        return _PAUSE_REASON_VOCABULARY_V4
+    return _PAUSE_REASON_VOCABULARY
+
+
 _GAME_SPEED_MULTIPLIERS = frozenset({1, 2, 4})
 _PYTHON_RNG_VERSION = 3
 _PYTHON_RNG_WORDS = 625
@@ -88,9 +112,18 @@ _TOP_LEVEL_KEYS_V2 = _TOP_LEVEL_KEYS_V1 | _MAP_IDENTITY_KEYS
 # missing it both fail closed.
 _TUNNEL_BONUS_KEY = frozenset({"tunnelBonus"})
 _TOP_LEVEL_KEYS_V3 = _TOP_LEVEL_KEYS_V2 | _TUNNEL_BONUS_KEY
+# GM-10i: v4 adds exactly `pendingOffers`; a v1/v2/v3 doc carrying it OR a v4 doc missing
+# it both fail closed via the version-selected exact-key set.
+_PENDING_OFFERS_KEY = frozenset({"pendingOffers"})
+_TOP_LEVEL_KEYS_V4 = _TOP_LEVEL_KEYS_V3 | _PENDING_OFFERS_KEY
+# The valid `pendingOffers` element strings, mirrored from the single OfferKind source
+# (offers.py is stdlib-only, so importing it keeps save_schema import-safe).
+_OFFER_KIND_VALUES = frozenset(kind.value for kind in OfferKind)


 def _top_level_keys_for(version: int) -> frozenset[str]:
+    if version == SAVE_SCHEMA_VERSION_V4:
+        return _TOP_LEVEL_KEYS_V4
     if version == SAVE_SCHEMA_VERSION_V3:
         return _TOP_LEVEL_KEYS_V3
     if version == SAVE_SCHEMA_VERSION_V2:
@@ -152,7 +185,37 @@ def _validate_tunnel_bonus(document: dict[str, Any]) -> None:
     _nonnegative_int(document["tunnelBonus"], "tunnelBonus")


-def _validate_scalars(document: dict[str, Any]) -> None:
+def _validate_pending_offers(document: dict[str, Any]) -> None:
+    """Validate the v4 `pendingOffers` (GM-10i): the ORDERED kinds of a HELD week-boundary
+    offer. Each is a known OfferKind value; they are pairwise DISTINCT (`generate_offers`
+    draws distinct kinds); and the list is NON-EMPTY exactly when a "week" boundary is held
+    (`"week" in pauseReasons`). The count is NOT pinned to `OFFERS_PER_WEEK` -- that is a
+    provisional balance default (GM-11), and a stored tuple is what was SHOWN, so a v4 save
+    made under a different count stays valid. Map-pool legality (TUNNEL only on a bounded
+    map) needs the resolved map and is enforced at load by `save_load`."""
+    kinds = _array(document["pendingOffers"], "pendingOffers")
+    seen: set[str] = set()
+    for index, kind in enumerate(kinds):
+        value = _string(kind, f"pendingOffers[{index}]")
+        if value not in _OFFER_KIND_VALUES:
+            _fail(f"pendingOffers[{index}]", "is not a known offer kind")
+        if value in seen:
+            _fail(f"pendingOffers[{index}]", "duplicates an earlier offer kind")
+        seen.add(value)
+    week_held = "week" in _array(document["pauseReasons"], "pauseReasons")
+    if bool(kinds) != week_held:
+        _fail(
+            "pendingOffers",
+            "must be non-empty exactly when a 'week' boundary is held (pauseReasons)",
+        )
+    if week_held and document["isGameOver"] is True:
+        _fail(
+            "pendingOffers",
+            "a held 'week' boundary is impossible on a finished game (isGameOver)",
+        )
+
+
+def _validate_scalars(document: dict[str, Any], version: int) -> None:
     _nonnegative_int(document["timeMs"], "timeMs")
     _nonnegative_int(document["steps"], "steps")
     speed = _int(document["gameSpeedMultiplier"], "gameSpeedMultiplier")
@@ -168,8 +231,9 @@ def _validate_scalars(document: dict[str, Any]) -> None:
     _nonnegative_int(document["numMetros"], "numMetros")
     _nonnegative_int(document["numCarriages"], "numCarriages")
     reasons = _array(document["pauseReasons"], "pauseReasons")
+    vocabulary = _pause_reason_vocabulary_for(version)
     for index, reason in enumerate(reasons):
-        if _string(reason, f"pauseReasons[{index}]") not in _PAUSE_REASON_VOCABULARY:
+        if _string(reason, f"pauseReasons[{index}]") not in vocabulary:
             _fail(f"pauseReasons[{index}]", "is not a known pause reason")
     if any(left >= right for left, right in zip(reasons, reasons[1:])):
         _fail("pauseReasons", "must be strictly sorted without duplicates")
@@ -306,11 +370,19 @@ def validate_save(document: Any) -> None:
     # GM-10h: v3 is a superset of v2 and STILL carries the map identity keys, so the
     # map-identity check must run for BOTH v2 and v3 (a `== V2` would stop validating
     # a v3 save's map).
-    if version in (SAVE_SCHEMA_VERSION_V2, SAVE_SCHEMA_VERSION_V3):
+    # GM-10i: each additive capability is gated by an EXPLICIT version set that every new
+    # superset version joins (a v4 doc still carries the v2 map keys + the v3 tunnel bonus).
+    if version in (
+        SAVE_SCHEMA_VERSION_V2,
+        SAVE_SCHEMA_VERSION_V3,
+        SAVE_SCHEMA_VERSION_V4,
+    ):
         _validate_map_identity(coerced)
-    if version == SAVE_SCHEMA_VERSION_V3:
+    if version in (SAVE_SCHEMA_VERSION_V3, SAVE_SCHEMA_VERSION_V4):
         _validate_tunnel_bonus(coerced)
-    _validate_scalars(coerced)
+    _validate_scalars(coerced, version)
+    if version == SAVE_SCHEMA_VERSION_V4:
+        _validate_pending_offers(coerced)
     _validate_progression(coerced)
     registry: set[str] = set()
     stations = validate_station_records(coerced, registry)
diff --git a/src/weekly_offers.py b/src/weekly_offers.py
index dc3a4ef..13d7415 100644
--- a/src/weekly_offers.py
+++ b/src/weekly_offers.py
@@ -42,19 +42,30 @@ class WeeklyOffers:
             # ready when the modal opens. Read-only derivation (no gameplay draws),
             # gated by the same calendar/crossing/not-game-over guards as the hold, so
             # RL/headless/tutorial never generate and current_offers stays ().
-            host.current_offers = generate_offers(
-                host._offer_rng_for_current_week(),
-                count=OFFERS_PER_WEEK,
-                tunnels_bounded=host.num_tunnels is not None,
-            )
+            host.current_offers = self.derive_current_offers(host)
             host.hold_pause_reason(WEEK_REASON)

+    def derive_current_offers(self, host: object) -> tuple[Offer, ...]:
+        # GM-10b: the current week's offers -- read-only derivation from the
+        # already-persisted RNG state + week_index, consuming no gameplay draws. The hold
+        # (above) calls it to populate `current_offers` when a boundary is first crossed. On
+        # a mid-offer Continue the STORED offers are restored VERBATIM (GM-10i persists them
+        # rather than re-deriving, since WEEK_LENGTH_STEPS/OFFERS_PER_WEEK/the pool are
+        # provisional GM-11 defaults), so this is NOT re-run at load or serialize.
+        return generate_offers(
+            host._offer_rng_for_current_week(),
+            count=OFFERS_PER_WEEK,
+            tunnels_bounded=host.num_tunnels is not None,
+        )
+
     def resolve(self, host: object, offer: Offer | None) -> None:
         # Continue past a week boundary: APPLY the chosen offer (GM-10c), then clear
-        # the week's offers and release the pause. A None offer is a forced resolve
-        # with no choice (the window-close path in main.run_game). An offer is CONFINED
-        # to a genuine pending choice (review MAJOR): only one currently presented at a
-        # held boundary can be applied, so no out-of-band call (e.g. a headless
+        # the week's offers and release the pause. A None offer resolves with NO choice
+        # (available as API + exercised by tests). NOTE: GM-10i changed the mid-offer
+        # window-close to PERSIST the pending boundary (save-schema v4) rather than
+        # force-resolve, so `main.run_game` no longer calls this None path. An offer is
+        # CONFINED to a genuine pending choice (review MAJOR): only one currently presented
+        # at a held boundary can be applied, so no out-of-band call (e.g. a headless
         # MiniMetroEnv with no calendar) can grant an upgrade and bypass the weekly
         # economy. GM-10h reconciles applied-offer persistence across Continue.
         if offer is not None:
diff --git a/test/test_gm07b_save_determinism.py b/test/test_gm07b_save_determinism.py
index 5e005a2..a5c4235 100644
--- a/test/test_gm07b_save_determinism.py
+++ b/test/test_gm07b_save_determinism.py
@@ -33,6 +33,11 @@ FIXTURE_V2_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v2-classic.json"
 # + the sorted-inserted additive `tunnelBonus: 0`. A v1 OR v2 save now re-saves as
 # exactly these v3 bytes (the current version), and this v3 fixture is self-idempotent.
 FIXTURE_V3_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v3-classic.json"
+# GM-10i: the DETERMINISTIC v3->v4 upgrade -- identical bytes except schemaVersion 4
+# + the sorted-inserted additive `pendingOffers: []` (this classic fixture is NOT at a
+# boundary). A v1/v2/v3 save now re-saves as exactly these v4 bytes (the current
+# version), and this v4 fixture is self-idempotent on re-save.
+FIXTURE_V4_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v4-classic.json"
 SAVE_GAME_MODULE = "save_game"
 SAVE_SCHEMA_MODULE = "save_schema"
 # Modules only `main` may import: the save/load stack plus the main-owned
@@ -69,6 +74,12 @@ EXPECTED_SAVE_V3_BYTE_LENGTH: int | None = 15501
 EXPECTED_SAVE_V3_SHA256: str | None = (
     "50d7d2c4390db42b4b3ee013bdf8f79ba5c72d0e6b5c0231a289920bdf6400df"
 )
+# GM-10i: the frozen v4-classic upgrade bytes (save-v3-classic.json + additive
+# "pendingOffers":[]). This is now the LATEST version a re-save of v1/v2/v3/v4 produces.
+EXPECTED_SAVE_V4_BYTE_LENGTH: int | None = 15520
+EXPECTED_SAVE_V4_SHA256: str | None = (
+    "4148551f7fef8d428e2a66f3841d509915a3fe604e272aa2402898d716c3d0e8"
+)

 _WORKER = """\
 import hashlib
@@ -288,11 +299,11 @@ class TestGM07bFreshProcessIdentity(unittest.TestCase):
             )
             self.assertEqual(first_save, second_save)
             self.assertEqual(save_a.read_bytes(), save_b.read_bytes())
-            # GM-10h: re-saving the frozen v1 save UPGRADES it to the CURRENT version
-            # (v3) deterministically, so both hash-seed workers emit exactly the frozen
-            # save-v3-classic bytes (hash-seed independence proven against the pinned
+            # GM-10i: re-saving the frozen v1 save UPGRADES it to the CURRENT version
+            # (v4) deterministically, so both hash-seed workers emit exactly the frozen
+            # save-v4-classic bytes (hash-seed independence proven against the pinned
             # upgrade, not v1).
-            self.assertEqual(save_a.read_bytes(), FIXTURE_V3_PATH.read_bytes())
+            self.assertEqual(save_a.read_bytes(), FIXTURE_V4_PATH.read_bytes())

             first_replay = self._run_worker(worker, "replay", save_a, environment_one)
             second_replay = self._run_worker(worker, "replay", save_a, environment_two)
@@ -387,6 +398,17 @@ class TestGM07bFrozenFixture(unittest.TestCase):
         self.assertEqual(len(payload), EXPECTED_SAVE_V3_BYTE_LENGTH)
         self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V3_SHA256)

+    def test_frozen_save_v4_classic_fixture_bytes_are_pinned(self):
+        # GM-10i: the v4-classic upgrade fixture is byte-frozen (LF, no CR), so the
+        # v3->v4 additive-key upgrade (`pendingOffers: []`) the idempotence/cross-process
+        # tests pin can never silently drift. This is now the CURRENT-version re-save.
+        self.assertTrue(FIXTURE_V4_PATH.exists(), "save-v4-classic.json is missing")
+        payload = FIXTURE_V4_PATH.read_bytes()
+        self.assertNotIn(b"\r", payload)
+        self.assertTrue(payload.endswith(b"\n"))
+        self.assertEqual(len(payload), EXPECTED_SAVE_V4_BYTE_LENGTH)
+        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V4_SHA256)
+
     def test_frozen_fixture_matches_the_freeze_recipe_and_loads(self):
         self.assertTrue(
             FIXTURE_PATH.exists(),
@@ -405,17 +427,20 @@ class TestGM07bFrozenFixture(unittest.TestCase):
         self.assertEqual(loaded.time_ms, 2_000)
         self.assertEqual(len(loaded.paths), 1)
         self.assertEqual(len(loaded.metros[0].carriages), 1)
-        # GM-10h: loading the frozen v1 save and re-saving it now UPGRADES it to the
-        # CURRENT version (v3) -- a deterministic additive-keys transform -- so the
-        # re-save equals the frozen save-v3-classic.json byte-for-byte. v2 ALSO upgrades
-        # to v3, and v3 is self-idempotent on re-save (v1->v3, v2->v3, v3->v3).
-        v3_payload = FIXTURE_V3_PATH.read_bytes()
-        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), v3_payload)
+        # GM-10i: loading the frozen v1 save and re-saving it now UPGRADES it to the
+        # CURRENT version (v4) -- a deterministic additive-keys transform -- so the
+        # re-save equals the frozen save-v4-classic.json byte-for-byte. v2/v3 ALSO upgrade
+        # to v4, and v4 is self-idempotent on re-save (v1->v4, v2->v4, v3->v4, v4->v4).
+        v4_payload = FIXTURE_V4_PATH.read_bytes()
+        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), v4_payload)
+        self.assertEqual(
+            canonical_save_bytes(serialize_game(load_game(FIXTURE_V2_PATH))), v4_payload
+        )
         self.assertEqual(
-            canonical_save_bytes(serialize_game(load_game(FIXTURE_V2_PATH))), v3_payload
+            canonical_save_bytes(serialize_game(load_game(FIXTURE_V3_PATH))), v4_payload
         )
         self.assertEqual(
-            canonical_save_bytes(serialize_game(load_game(FIXTURE_V3_PATH))), v3_payload
+            canonical_save_bytes(serialize_game(load_game(FIXTURE_V4_PATH))), v4_payload
         )
         # The freeze recipe regenerates the same STATE modulo entity IDs:
         # compare through the UUID-free checkpoint oracle instead of bytes.
diff --git a/test/test_gm07b_save_schema.py b/test/test_gm07b_save_schema.py
index 31a8a2f..f4d4aba 100644
--- a/test/test_gm07b_save_schema.py
+++ b/test/test_gm07b_save_schema.py
@@ -30,7 +30,8 @@ TOP_LEVEL_KEYS = frozenset(
     passengerMaxWaitTimeMs overduePassengerThreshold deliveries lineCredits
     purchasedNumPaths unlockedNumPaths unlockedNumStations numPaths numStations
     initialNumStations pathPurchasePrices pathUnlockMilestones
-    stationUnlockMilestones numMetros numCarriages tunnelBonus stations passengers
+    stationUnlockMilestones numMetros numCarriages tunnelBonus pendingOffers
+    stations passengers
     paths metros travelPlans pathColors pathToColor spawnTimers pathButtons rng""".split()
 )
 STATION_KEYS = frozenset(
@@ -157,23 +158,26 @@ class TestGM07bSaveSchemaVersioning(unittest.TestCase):
             ("SAVE_SCHEMA_VERSION_V1", 1),
             ("SAVE_SCHEMA_VERSION_V2", 2),
             ("SAVE_SCHEMA_VERSION_V3", 3),
-            ("SAVE_SCHEMA_VERSION", 3),
-            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1, 2, 3}),
-            # stateContract + rulesVersion are STABLE across v1/v2/v3 (GM-09f/GM-10h).
+            ("SAVE_SCHEMA_VERSION_V4", 4),
+            ("SAVE_SCHEMA_VERSION", 4),
+            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1, 2, 3, 4}),
+            # stateContract + rulesVersion are STABLE across v1/v2/v3/v4 (GM-09f/h/10i).
             ("SAVE_STATE_CONTRACT", "mini-metro-save-v1"),
             ("SAVE_RULES_VERSION", "rules-v1"),
         ):
             self.assertEqual(getattr(schema, name, None), expected, name)
         validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
         _, document = _document(self)
-        self.assertEqual(document["schemaVersion"], 3)
+        self.assertEqual(document["schemaVersion"], 4)
         self.assertEqual(document["stateContract"], "mini-metro-save-v1")
         self.assertEqual(document["rulesVersion"], "rules-v1")
-        # A freshly serialized game is v3 and carries the map identity (classic@1)
-        # plus the additive tunnelBonus (0 with no upgrade applied; GM-10h).
+        # A freshly serialized game is v4 and carries the map identity (classic@1), the
+        # additive tunnelBonus (0 with no upgrade), and the additive pendingOffers ([]
+        # with no held boundary; GM-10i).
         self.assertEqual(document["mapId"], "classic")
         self.assertEqual(document["mapDefinitionVersion"], 1)
         self.assertEqual(document["tunnelBonus"], 0)
+        self.assertEqual(document["pendingOffers"], [])
         self.assertIsNone(validate_save(document))

     def test_schema_version_and_pinned_literal_strictness(self):
@@ -182,8 +186,8 @@ class TestGM07bSaveSchemaVersioning(unittest.TestCase):
         mutations = {
             "bool-true schemaVersion": _setter((), "schemaVersion", True),
             "bool-false schemaVersion": _setter((), "schemaVersion", False),
-            # 3 is now SUPPORTED (v3, GM-10h); 4 is the forward version to reject.
-            "forward schemaVersion": _setter((), "schemaVersion", 4),
+            # 4 is now SUPPORTED (v4, GM-10i); 5 is the forward version to reject.
+            "forward schemaVersion": _setter((), "schemaVersion", 5),
             "zero schemaVersion": _setter((), "schemaVersion", 0),
             "string schemaVersion": _setter((), "schemaVersion", "1"),
             "float schemaVersion": _setter((), "schemaVersion", 1.0),
diff --git a/test/test_gm09f_save_map.py b/test/test_gm09f_save_map.py
index 53eed40..b77dbc0 100644
--- a/test/test_gm09f_save_map.py
+++ b/test/test_gm09f_save_map.py
@@ -44,14 +44,16 @@ def _river_crossing_mediator():


 def _as_v1(document):
-    """A v1 document: drop the v2 map keys AND the v3 tunnelBonus (GM-10h), and set
-    schemaVersion 1 (old save shape). A fresh serialize is v3, so all three added keys
+    """A v1 document: drop the v2 map keys, the v3 tunnelBonus (GM-10h), AND the v4
+    pendingOffers (GM-10i), and set schemaVersion 1 (old save shape). A fresh serialize
+    is v4, so all four added keys
     must be stripped or the v1 exact-key set rejects the doc for the wrong reason."""
     v1 = copy.deepcopy(document)
     v1["schemaVersion"] = 1
     del v1["mapId"]
     del v1["mapDefinitionVersion"]
     del v1["tunnelBonus"]
+    del v1["pendingOffers"]
     return v1


@@ -64,7 +66,7 @@ class TestGM09fRoundTrip(unittest.TestCase):
             ("lake", LAKE),
         ):
             document = serialize_game(Mediator(seed=0, map_definition=map_def))
-            self.assertEqual(document["schemaVersion"], 3)
+            self.assertEqual(document["schemaVersion"], 4)
             self.assertEqual(document["mapId"], name)
             self.assertEqual(document["mapDefinitionVersion"], 1)
             validate_save(document)
diff --git a/test/test_gm10a_calendar.py b/test/test_gm10a_calendar.py
index 6c211c1..104d660 100644
--- a/test/test_gm10a_calendar.py
+++ b/test/test_gm10a_calendar.py
@@ -309,16 +309,17 @@ class TestGM10aOfferArming(unittest.TestCase):


 class TestGM10aSaveBlock(unittest.TestCase):
-    def test_saving_is_blocked_while_a_week_boundary_is_pending(self):
+    def test_saving_at_a_pending_week_boundary_now_persists_it(self):
+        # GM-10i (D-047) REVERSED the GM-10a save block: a mid-offer save now PERSISTS the
+        # pending boundary (schema v4) so a Continue re-enters the modal, instead of being
+        # rejected. The saved doc carries the "week" pause + the shown offers.
         m = Mediator(seed=0)
         m.week_calendar = True
         _step_to_boundary(m)
         self.assertTrue(m.is_week_boundary_pending)
-        with self.assertRaisesRegex(ValueError, "week-boundary offer is pending"):
-            serialize_game(m)
-        # Resolving lets the save proceed.
-        m.resolve_week_boundary()
-        self.assertIsInstance(serialize_game(m), dict)
+        doc = serialize_game(m)
+        self.assertIn("week", doc["pauseReasons"])
+        self.assertEqual(doc["pendingOffers"], [o.kind.value for o in m.current_offers])


 class TestGM10aRLUnaffected(unittest.TestCase):
@@ -561,10 +562,11 @@ class TestGM10aRunLoopOffer(unittest.TestCase):
             "the run loop forwarded the mediator's real current_offers",
         )

-    def test_closing_mid_offer_resolves_the_week_and_autosaves(self):
-        # review MAJOR: a window-close WHILE the offer is up (frame 0 promotes, frame
-        # 1 delivers QUIT with state already OFFER) resolves the week and autosaves
-        # the resumed game, so Continue reloads PAST the boundary (GM-10a).
+    def test_closing_mid_offer_persists_the_pending_boundary(self):
+        # GM-10i (D-047): a window-close WHILE the offer is up (frame 0 promotes, frame 1
+        # delivers QUIT with state already OFFER) now PERSISTS the pending boundary WITHOUT
+        # resolving, so Continue reloads INTO the modal re-presenting the offers. (GM-10a
+        # force-resolved with no choice, reloading PAST the boundary.)
         harness = _drive_run_game(
             [[], [_quit_event()]],
             max_frames=None,
@@ -572,9 +574,11 @@ class TestGM10aRunLoopOffer(unittest.TestCase):
             pending=True,
         )
         self.assertTrue(harness.exited, "QUIT raised SystemExit")
-        self.assertEqual(harness.mediator.resolved, 1, "closing resolved the week")
         self.assertEqual(
-            harness.autosaves, [harness.mediator], "the resumed game was autosaved"
+            harness.mediator.resolved, 0, "closing did NOT resolve the week"
+        )
+        self.assertEqual(
+            harness.autosaves, [harness.mediator], "the pending game was autosaved"
         )

     def test_no_offer_no_autosave_on_a_plain_title_quit(self):
diff --git a/test/test_gm10h_persistence.py b/test/test_gm10h_persistence.py
index 0fad4e9..b001536 100644
--- a/test/test_gm10h_persistence.py
+++ b/test/test_gm10h_persistence.py
@@ -119,10 +119,13 @@ class TestGM10hTunnelPersistence(unittest.TestCase):


 class TestGM10hSchemaAndBackwardCompat(unittest.TestCase):
-    def test_fresh_save_is_v3_with_a_zero_bonus(self):
+    def test_fresh_save_is_v4_with_a_zero_bonus(self):
+        # GM-10i bumped the current version to v4; a fresh (non-boundary) save carries a
+        # zero tunnel bonus AND an empty pendingOffers.
         doc = serialize_game(_played())
-        self.assertEqual(doc["schemaVersion"], 3)
+        self.assertEqual(doc["schemaVersion"], 4)
         self.assertEqual(doc["tunnelBonus"], 0)
+        self.assertEqual(doc["pendingOffers"], [])

     def test_v1_and_v2_fixtures_deserialize_with_a_zero_bonus(self):
         # review MINOR-5: DESERIALIZE (runs _require_running_config), not just validate.
@@ -137,6 +140,8 @@ class TestGM10hSchemaAndBackwardCompat(unittest.TestCase):
         from save_schema import validate_save

         doc = serialize_game(_played())
+        doc["schemaVersion"] = 3  # native v3 (down-convert: a fresh save is now v4)
+        del doc["pendingOffers"]
         del doc["tunnelBonus"]  # a v3 doc MUST carry it
         with self.assertRaises(ValueError):
             validate_save(doc)
@@ -146,6 +151,7 @@ class TestGM10hSchemaAndBackwardCompat(unittest.TestCase):

         doc = serialize_game(_played())
         doc["schemaVersion"] = 2  # a v2 doc must NOT carry tunnelBonus
+        del doc["pendingOffers"]  # strip the v4 key so tunnelBonus is the sole fault
         with self.assertRaises(ValueError):
             validate_save(doc)

@@ -153,6 +159,8 @@ class TestGM10hSchemaAndBackwardCompat(unittest.TestCase):
         from save_schema import validate_save

         doc = serialize_game(_played())
+        doc["schemaVersion"] = 3  # native v3 (down-convert)
+        del doc["pendingOffers"]
         doc["mapId"] = "river "  # forged: whitespace -- must still be rejected on v3
         with self.assertRaises(ValueError):
             validate_save(doc)
```
