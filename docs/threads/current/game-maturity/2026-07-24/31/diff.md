# GM-10h fleet/tunnel upgrade persistence (save-schema v3) — implementation diff

Source: save_schema.py (v3 constants + `_TOP_LEVEL_KEYS_V3` + `_validate_tunnel_bonus` + the {V2,V3} map gate), save_game.py (`_require_valid_upgrade_state` run FIRST + the `tunnelBonus` key + docstrings), save_load.py (version-gated `_require_running_config` relaxation + restore `tunnel_bonus` + load-time reachability reject), mediator.py (`tunnel_bonus` attr + `num_tunnels` folds it), crossings.py (`within_tunnel_budget` folds the bonus -- the load-bearing trap), main.py (mid-offer comment -> GM-10i). Tests: test_gm10h_persistence.py (NEW, 16 tests) + the three save contract tests repointed to v3. New fixture: scripts/fixtures/save-v3-classic.json (15501 bytes, the additive v2->v3 upgrade; not inlined). Docs: D-045, README, ARCHITECTURE, PROGRESS, D-041 reconciliation.

## Production source
```diff
diff --git a/src/crossings.py b/src/crossings.py
index d5de868..99634eb 100644
--- a/src/crossings.py
+++ b/src/crossings.py
@@ -121,6 +121,12 @@ def within_tunnel_budget(
     num_tunnels = getattr(map_definition, "tunnel_budget", None)
     if num_tunnels is None:
         return True
+    # GM-10h: this gate reads the map budget DIRECTLY (not mediator.num_tunnels), so a
+    # persisted TUNNEL upgrade must be folded in HERE too, or the bonus would show in
+    # the observation/legality yet never let the player build the extra crossing. On an
+    # unbounded map (budget None, above) the bonus is moot -- a nonzero one is rejected
+    # at save/load. getattr keeps this import-safe for a host without the field.
+    num_tunnels += getattr(host, "tunnel_bonus", 0)
     rivers = getattr(map_definition, "rivers", ())
     if not rivers:
         return True
diff --git a/src/main.py b/src/main.py
index a6595ed..d5a1acf 100644
--- a/src/main.py
+++ b/src/main.py
@@ -332,7 +332,8 @@ def run_game(
                     # Closing mid-offer (GM-10a): resolve the week with NO choice (the
                     # no-arg forced resolve -- the player did not pick an offer) and
                     # autosave the resumed game, so Continue reloads past the boundary.
-                    # Mid-offer / applied-offer persistence proper is GM-10h.
+                    # Applied-offer (fleet/tunnel) persistence is GM-10h; persisting a
+                    # PENDING offer so a mid-offer Continue re-presents it is GM-10i.
                     controller.mediator.resolve_week_boundary()
                     write_autosave(controller.mediator)
                 elif controller.state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU):
diff --git a/src/mediator.py b/src/mediator.py
index 3dcf1ac..1bfb424 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -173,6 +173,11 @@ class Mediator:
         # -- offers are re-derived Continue-exact from the already-persisted RNG state
         # (see _offer_rng_for_current_week), so no new save/checkpoint bytes.
         self.current_offers: tuple[Offer, ...] = ()
+        # GM-10h (D-045): persisted +N on the map's tunnel budget from a TUNNEL weekly
+        # upgrade (GM-10g). 0 until an upgrade is applied; folded into num_tunnels only
+        # on a bounded map. num_metros/num_carriages are the analogous fleet totals
+        # (already stored above), grown directly by a locomotive/carriage upgrade.
+        self.tunnel_bonus = 0
         # GM-10a-d: the week-boundary hold + offer generate/apply logic (D-023 facade).
         self._weekly = WeeklyOffers()
         self.game_speed_multiplier = 1
@@ -268,14 +273,19 @@ class Mediator:

     @property
     def num_tunnels(self) -> int | None:
-        """The map's river-crossing budget (GM-09c); None = unbounded (CLASSIC).
+        """The map's river-crossing budget (GM-09c) plus any persisted `tunnel_bonus`
+        from a TUNNEL weekly upgrade (GM-10h); None = unbounded (CLASSIC).

         DERIVED live from `map_definition` — not a cached field — so it always
         agrees with `consumed_tunnels` (which reads `map_definition.rivers`) even if
-        the map is swapped; a stale cached copy would fail open (review Codex).
-        """
+        the map is swapped; a stale cached copy would fail open (review Codex). On an
+        unbounded map the bonus is IGNORED (stays None); a nonzero bonus there is
+        unreachable and rejected at save/load (GM-10h)."""

-        return self.map_definition.tunnel_budget
+        budget = self.map_definition.tunnel_budget
+        if budget is None:
+            return None
+        return budget + getattr(self, "tunnel_bonus", 0)

     @property
     def consumed_tunnels(self) -> int:
diff --git a/src/save_game.py b/src/save_game.py
index 7560570..010ef39 100644
--- a/src/save_game.py
+++ b/src/save_game.py
@@ -1,10 +1,11 @@
 """GM-07b saver: pure quiescent-boundary state capture and atomic saves.

 serialize_game reads live state through attributes only (never through
-mutating getters), rejects mid-gesture boundaries, and returns a strict
-schema-v2 document (v2 adds the map identity; GM-09f); save_game writes its canonical ASCII bytes through a
-save-local mkstemp -> fsync -> os.replace atomic writer, so a failed
-save leaves the destination untouched and no temporary file behind.
+mutating getters), rejects mid-gesture boundaries + a desynced/forged upgrade
+state, and returns a strict schema-v3 document (v2 adds the map identity, GM-09f;
+v3 adds the tunnel-upgrade bonus, GM-10h); save_game writes its canonical ASCII
+bytes through a save-local mkstemp -> fsync -> os.replace atomic writer, so a
+failed save leaves the destination untouched and no temporary file behind.
 """

 from __future__ import annotations
@@ -14,6 +15,8 @@ import tempfile
 from pathlib import Path as FilesystemPath
 from typing import Any

+from config import num_carriages as config_num_carriages
+from config import num_metros as config_num_metros
 from recursive_checkpoint_schema import safe_checkpoint_value
 from save_load import _require_legal_map_state, deserialize_game, load_game
 from save_schema import (
@@ -73,8 +76,9 @@ def _require_quiescent(mediator: Any) -> None:
         raise ValueError("cannot save during a path redraw gesture")
     if mediator.path_edit_selection is not None:
         raise ValueError("cannot save during a path edit selection")
-    # GM-10a (D-041): a pending week-boundary offer is a transient, unresolved
-    # choice that GM-10a does not persist (deferred to GM-10h). validate_save
+    # GM-10a: a pending week-boundary offer is a transient, unresolved choice that is
+    # not persisted (persisting a PENDING offer for a mid-offer Continue is GM-10i;
+    # GM-10h persists only APPLIED fleet/tunnel upgrades). validate_save
     # already rejects a "week" pause reason before any file I/O; this gives the
     # clearer, actionable error at the save boundary. Defensive getattr keeps
     # non-Mediator save shapes (which never hold "week") working.
@@ -99,6 +103,35 @@ def _require_canonical_fleet(mediator: Any) -> None:
             raise ValueError("cannot save a Metro whose path binding disagrees")


+def _require_valid_upgrade_state(mediator: Any) -> None:
+    # GM-10h (D-045): reject a desynced/forged upgrade state HERE, before the atomic
+    # write can replace a valid autosave with an unloadable one (load-time rejection is
+    # too late -- the bad bytes already clobbered the save). num_metros/num_carriages
+    # are fleet TOTALS an upgrade only GROWS, so they must be >= the running config; the
+    # tunnel bonus is a nonnegative int, and is reachable (nonzero) only on a bounded
+    # map -- an unbounded map (CLASSIC) ignores it, so a nonzero one there is forged.
+    if mediator.num_metros < config_num_metros:
+        raise ValueError(
+            f"cannot save a fleet below the running config: numMetros "
+            f"{mediator.num_metros} < {config_num_metros}"
+        )
+    if mediator.num_carriages < config_num_carriages:
+        raise ValueError(
+            f"cannot save a fleet below the running config: numCarriages "
+            f"{mediator.num_carriages} < {config_num_carriages}"
+        )
+    tunnel_bonus = getattr(mediator, "tunnel_bonus", 0)
+    if type(tunnel_bonus) is not int or tunnel_bonus < 0:
+        raise ValueError(
+            f"cannot save a non-nonnegative-int tunnel bonus: {tunnel_bonus!r}"
+        )
+    if tunnel_bonus and mediator.map_definition.tunnel_budget is None:
+        raise ValueError(
+            "cannot save a nonzero tunnel bonus on an unbounded-tunnel map "
+            f"({mediator.map_definition.map_id}): the bonus is unreachable"
+        )
+
+
 def _station_records(mediator: Any) -> list[dict[str, Any]]:
     active_count = len(mediator.stations)
     prefix = mediator.all_stations[:active_count]
@@ -235,9 +268,11 @@ def _spawn_timer_records(mediator: Any) -> list[list[Any]]:


 def serialize_game(mediator: Any) -> dict[str, Any]:
-    """Capture one strict v2 save document (adds the map identity) without mutating
-    the Mediator."""
+    """Capture one strict v3 save document (map identity + tunnel-upgrade bonus)
+    without mutating the Mediator; rejects a below-config fleet or an unreachable
+    tunnel bonus BEFORE the atomic write (GM-10h)."""

+    _require_valid_upgrade_state(mediator)
     map_id, map_definition_version = _require_serializable_map(mediator)
     _require_quiescent(mediator)
     _require_canonical_fleet(mediator)
@@ -269,6 +304,7 @@ def serialize_game(mediator: Any) -> dict[str, Any]:
         "stationUnlockMilestones": list(mediator.station_unlock_milestones),
         "numMetros": mediator.num_metros,
         "numCarriages": mediator.num_carriages,
+        "tunnelBonus": getattr(mediator, "tunnel_bonus", 0),
         "stations": _station_records(mediator),
         "passengers": _passenger_records(mediator),
         "paths": _path_records(mediator),
diff --git a/src/save_load.py b/src/save_load.py
index c721fa6..b2e251b 100644
--- a/src/save_load.py
+++ b/src/save_load.py
@@ -30,7 +30,7 @@ from geometry.type import ShapeType
 from graph.node import Node
 from mediator import Mediator
 from recursive_checkpoint_schema import safe_checkpoint_value
-from save_schema import validate_save
+from save_schema import SAVE_SCHEMA_VERSION_V3, validate_save
 from travel_plan import TravelPlan
 from utils import get_shape_from_type

@@ -42,15 +42,26 @@ def _fail(message: str) -> None:


 def _require_running_config(document: dict[str, Any]) -> None:
-    # v1 strictly rejects config divergence; a relaxation is a future
-    # schema version's explicit business (D-026).
-    pairs = (
-        ("numPaths", config_num_paths),
+    # numPaths (the total line SLOTS) is pinned for EVERY version -- a NEW_LINE upgrade
+    # grows purchased_num_paths, not the ceiling. GM-10h (D-045): v1/v2 strictly reject
+    # any fleet divergence (no upgrade mechanism existed, so numMetros != config is
+    # corrupt), but v3 may carry a GROWN fleet from a locomotive/carriage upgrade, so
+    # numMetros/numCarriages need only be >= config (a total an upgrade only grows; the
+    # serialize-time guard already rejected a below-config total before writing). The
+    # bonus keys do NOT exist -- the fleet total IS the state -- so there is no v1/v2
+    # KeyError. A further relaxation is a future schema version's business (D-026).
+    if document["numPaths"] != config_num_paths:
+        _fail("numPaths disagrees with the running config")
+    is_v3 = document["schemaVersion"] == SAVE_SCHEMA_VERSION_V3
+    for key, expected in (
         ("numMetros", config_num_metros),
         ("numCarriages", config_num_carriages),
-    )
-    for key, expected in pairs:
-        if document[key] != expected:
+    ):
+        actual = document[key]
+        if is_v3:
+            if actual < expected:
+                _fail(f"{key} is below the running config")
+        elif actual != expected:
             _fail(f"{key} disagrees with the running config")


@@ -115,6 +126,11 @@ def _restore_scalars(mediator: Mediator, document: dict[str, Any]) -> None:
     mediator.unlocked_num_stations = document["unlockedNumStations"]
     mediator.num_metros = document["numMetros"]
     mediator.num_carriages = document["numCarriages"]
+    # GM-10h: v3 persists the TUNNEL-upgrade bonus; a v1/v2 doc has no such key, so
+    # default on ABSENCE. (For this field `.get(...,0)` and `x or 0` happen to agree --
+    # 0 is the only falsy valid value -- but `.get` is the clearer form and follows the
+    # GM-09f rule that a real falsy persisted value must not be coerced by `or DEFAULT`.)
+    mediator.tunnel_bonus = document.get("tunnelBonus", 0)
     mediator.time_ms = document["timeMs"]
     mediator.steps = document["steps"]
     mediator.game_speed_multiplier = document["gameSpeedMultiplier"]
@@ -327,6 +343,15 @@ def _require_legal_map_state(mediator: Any, map_def: Any) -> None:
             f"map {map_def.map_id!r}: {mediator.consumed_tunnels} river crossings "
             f"exceed the map's tunnel budget of {num_tunnels}"
         )
+    # GM-10h: a nonzero TUNNEL bonus is REACHABLE only on a bounded map (CLASSIC never
+    # offers TUNNEL and ignores the bonus); reject a forged v3 doc that carries one on
+    # an unbounded map -- matches the serialize-time guard so both save surfaces agree.
+    tunnel_bonus = getattr(mediator, "tunnel_bonus", 0)
+    if tunnel_bonus and map_def.tunnel_budget is None:
+        raise ValueError(
+            f"map {map_def.map_id!r}: a nonzero tunnel bonus ({tunnel_bonus}) is "
+            "unreachable on an unbounded-tunnel map"
+        )


 def deserialize_game(document: Any) -> Mediator:
diff --git a/src/save_schema.py b/src/save_schema.py
index 4087f75..4bca7b9 100644
--- a/src/save_schema.py
+++ b/src/save_schema.py
@@ -42,8 +42,20 @@ SAVE_SCHEMA_VERSION_V1 = 1
 # and `rulesVersion` are STABLE across v1/v2 -- only `schemaVersion` and the two map
 # keys change (D-038).
 SAVE_SCHEMA_VERSION_V2 = 2
-SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V2
-SUPPORTED_SAVE_SCHEMA_VERSIONS = {SAVE_SCHEMA_VERSION_V1, SAVE_SCHEMA_VERSION_V2}
+# GM-10h (D-045): v3 is a strict SUPERSET of v2 -- it adds one additive key,
+# `tunnelBonus` (a persisted +N on the map's tunnel budget from a TUNNEL weekly
+# upgrade), and v3-gates a RELAXATION of the fleet running-config pin so a
+# locomotive/carriage upgrade (`numMetros`/`numCarriages` grown ABOVE the config
+# total) can load. A v1/v2 document (no `tunnelBonus`) still loads with a 0 bonus,
+# so the byte-frozen `save-v1.json`/`save-v2-classic.json` stay valid. New saves
+# are v3. `stateContract`/`rulesVersion` STABLE across v1/v2/v3.
+SAVE_SCHEMA_VERSION_V3 = 3
+SAVE_SCHEMA_VERSION = SAVE_SCHEMA_VERSION_V3
+SUPPORTED_SAVE_SCHEMA_VERSIONS = {
+    SAVE_SCHEMA_VERSION_V1,
+    SAVE_SCHEMA_VERSION_V2,
+    SAVE_SCHEMA_VERSION_V3,
+}
 SAVE_STATE_CONTRACT = "mini-metro-save-v1"
 SAVE_RULES_VERSION = "rules-v1"

@@ -71,9 +83,16 @@ _TOP_LEVEL_KEYS_V1 = frozenset(
 # them both fail closed.
 _MAP_IDENTITY_KEYS = frozenset({"mapId", "mapDefinitionVersion"})
 _TOP_LEVEL_KEYS_V2 = _TOP_LEVEL_KEYS_V1 | _MAP_IDENTITY_KEYS
+# GM-10h: v3 adds exactly `tunnelBonus`; the exact-key set is chosen by the
+# document's schemaVersion, so a v1/v2 doc carrying `tunnelBonus` OR a v3 doc
+# missing it both fail closed.
+_TUNNEL_BONUS_KEY = frozenset({"tunnelBonus"})
+_TOP_LEVEL_KEYS_V3 = _TOP_LEVEL_KEYS_V2 | _TUNNEL_BONUS_KEY


 def _top_level_keys_for(version: int) -> frozenset[str]:
+    if version == SAVE_SCHEMA_VERSION_V3:
+        return _TOP_LEVEL_KEYS_V3
     if version == SAVE_SCHEMA_VERSION_V2:
         return _TOP_LEVEL_KEYS_V2
     return _TOP_LEVEL_KEYS_V1
@@ -125,6 +144,14 @@ def _validate_map_identity(document: dict[str, Any]) -> None:
     _positive_int(document["mapDefinitionVersion"], "mapDefinitionVersion")


+def _validate_tunnel_bonus(document: dict[str, Any]) -> None:
+    """Validate the v3 `tunnelBonus` (GM-10h): a nonnegative non-bool int -- the
+    persisted +N on the map's tunnel budget from a TUNNEL weekly upgrade. Map-aware
+    reachability (a nonzero bonus is legal only on a bounded map) is enforced at load
+    by `save_load._require_legal_map_state`, which has the resolved map."""
+    _nonnegative_int(document["tunnelBonus"], "tunnelBonus")
+
+
 def _validate_scalars(document: dict[str, Any]) -> None:
     _nonnegative_int(document["timeMs"], "timeMs")
     _nonnegative_int(document["steps"], "steps")
@@ -276,8 +303,13 @@ def validate_save(document: Any) -> None:
     version = _read_schema_version(coerced)
     _exact_keys(coerced, _top_level_keys_for(version), "document")
     _validate_header(coerced)
-    if version == SAVE_SCHEMA_VERSION_V2:
+    # GM-10h: v3 is a superset of v2 and STILL carries the map identity keys, so the
+    # map-identity check must run for BOTH v2 and v3 (a `== V2` would stop validating
+    # a v3 save's map).
+    if version in (SAVE_SCHEMA_VERSION_V2, SAVE_SCHEMA_VERSION_V3):
         _validate_map_identity(coerced)
+    if version == SAVE_SCHEMA_VERSION_V3:
+        _validate_tunnel_bonus(coerced)
     _validate_scalars(coerced)
     _validate_progression(coerced)
     registry: set[str] = set()
```

## Tests
```diff
diff --git a/test/test_gm07b_save_determinism.py b/test/test_gm07b_save_determinism.py
index e50e5f0..5e005a2 100644
--- a/test/test_gm07b_save_determinism.py
+++ b/test/test_gm07b_save_determinism.py
@@ -29,6 +29,10 @@ FIXTURE_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v1.json"
 # re-saves as exactly these bytes (the upgrade is pinned), and this v2 fixture is
 # self-idempotent on re-save.
 FIXTURE_V2_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v2-classic.json"
+# GM-10h: the DETERMINISTIC v2->v3 upgrade -- identical bytes except schemaVersion 3
+# + the sorted-inserted additive `tunnelBonus: 0`. A v1 OR v2 save now re-saves as
+# exactly these v3 bytes (the current version), and this v3 fixture is self-idempotent.
+FIXTURE_V3_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v3-classic.json"
 SAVE_GAME_MODULE = "save_game"
 SAVE_SCHEMA_MODULE = "save_schema"
 # Modules only `main` may import: the save/load stack plus the main-owned
@@ -59,6 +63,12 @@ EXPECTED_SAVE_V2_BYTE_LENGTH: int | None = 15485
 EXPECTED_SAVE_V2_SHA256: str | None = (
     "60f2bc16c39610b8822288ebf08eea214cb2d0f54c9ac0208113a0892badbd84"
 )
+# GM-10h: the frozen v3-classic upgrade bytes (save-v2-classic.json + additive
+# "tunnelBonus":0). This is now the LATEST version a re-save of v1/v2/v3 produces.
+EXPECTED_SAVE_V3_BYTE_LENGTH: int | None = 15501
+EXPECTED_SAVE_V3_SHA256: str | None = (
+    "50d7d2c4390db42b4b3ee013bdf8f79ba5c72d0e6b5c0231a289920bdf6400df"
+)

 _WORKER = """\
 import hashlib
@@ -278,10 +288,11 @@ class TestGM07bFreshProcessIdentity(unittest.TestCase):
             )
             self.assertEqual(first_save, second_save)
             self.assertEqual(save_a.read_bytes(), save_b.read_bytes())
-            # GM-09f: re-saving the frozen v1 save UPGRADES it to v2 deterministically,
-            # so both hash-seed workers emit exactly the frozen save-v2-classic bytes
-            # (hash-seed independence proven against the pinned upgrade, not v1).
-            self.assertEqual(save_a.read_bytes(), FIXTURE_V2_PATH.read_bytes())
+            # GM-10h: re-saving the frozen v1 save UPGRADES it to the CURRENT version
+            # (v3) deterministically, so both hash-seed workers emit exactly the frozen
+            # save-v3-classic bytes (hash-seed independence proven against the pinned
+            # upgrade, not v1).
+            self.assertEqual(save_a.read_bytes(), FIXTURE_V3_PATH.read_bytes())

             first_replay = self._run_worker(worker, "replay", save_a, environment_one)
             second_replay = self._run_worker(worker, "replay", save_a, environment_two)
@@ -365,6 +376,17 @@ class TestGM07bFrozenFixture(unittest.TestCase):
         self.assertEqual(len(payload), EXPECTED_SAVE_V2_BYTE_LENGTH)
         self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V2_SHA256)

+    def test_frozen_save_v3_classic_fixture_bytes_are_pinned(self):
+        # GM-10h: the v3-classic upgrade fixture is byte-frozen (LF, no CR), so the
+        # v2->v3 additive-key upgrade the idempotence/cross-process tests pin can never
+        # silently drift.
+        self.assertTrue(FIXTURE_V3_PATH.exists(), "save-v3-classic.json is missing")
+        payload = FIXTURE_V3_PATH.read_bytes()
+        self.assertNotIn(b"\r", payload)
+        self.assertTrue(payload.endswith(b"\n"))
+        self.assertEqual(len(payload), EXPECTED_SAVE_V3_BYTE_LENGTH)
+        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V3_SHA256)
+
     def test_frozen_fixture_matches_the_freeze_recipe_and_loads(self):
         self.assertTrue(
             FIXTURE_PATH.exists(),
@@ -383,14 +405,17 @@ class TestGM07bFrozenFixture(unittest.TestCase):
         self.assertEqual(loaded.time_ms, 2_000)
         self.assertEqual(len(loaded.paths), 1)
         self.assertEqual(len(loaded.metros[0].carriages), 1)
-        # GM-09f: loading the frozen v1 save and re-saving it now UPGRADES it to v2 --
-        # a deterministic header-only transform -- so the re-save equals the frozen
-        # save-v2-classic.json byte-for-byte (the upgrade is pinned), and that v2
-        # fixture is self-idempotent on re-save.
-        v2_payload = FIXTURE_V2_PATH.read_bytes()
-        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), v2_payload)
+        # GM-10h: loading the frozen v1 save and re-saving it now UPGRADES it to the
+        # CURRENT version (v3) -- a deterministic additive-keys transform -- so the
+        # re-save equals the frozen save-v3-classic.json byte-for-byte. v2 ALSO upgrades
+        # to v3, and v3 is self-idempotent on re-save (v1->v3, v2->v3, v3->v3).
+        v3_payload = FIXTURE_V3_PATH.read_bytes()
+        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), v3_payload)
+        self.assertEqual(
+            canonical_save_bytes(serialize_game(load_game(FIXTURE_V2_PATH))), v3_payload
+        )
         self.assertEqual(
-            canonical_save_bytes(serialize_game(load_game(FIXTURE_V2_PATH))), v2_payload
+            canonical_save_bytes(serialize_game(load_game(FIXTURE_V3_PATH))), v3_payload
         )
         # The freeze recipe regenerates the same STATE modulo entity IDs:
         # compare through the UUID-free checkpoint oracle instead of bytes.
diff --git a/test/test_gm07b_save_schema.py b/test/test_gm07b_save_schema.py
index 3d581b9..31a8a2f 100644
--- a/test/test_gm07b_save_schema.py
+++ b/test/test_gm07b_save_schema.py
@@ -30,8 +30,8 @@ TOP_LEVEL_KEYS = frozenset(
     passengerMaxWaitTimeMs overduePassengerThreshold deliveries lineCredits
     purchasedNumPaths unlockedNumPaths unlockedNumStations numPaths numStations
     initialNumStations pathPurchasePrices pathUnlockMilestones
-    stationUnlockMilestones numMetros numCarriages stations passengers paths
-    metros travelPlans pathColors pathToColor spawnTimers pathButtons rng""".split()
+    stationUnlockMilestones numMetros numCarriages tunnelBonus stations passengers
+    paths metros travelPlans pathColors pathToColor spawnTimers pathButtons rng""".split()
 )
 STATION_KEYS = frozenset(
     """id position shapeType active capacity waitingPassengerIds
@@ -156,21 +156,24 @@ class TestGM07bSaveSchemaVersioning(unittest.TestCase):
         for name, expected in (
             ("SAVE_SCHEMA_VERSION_V1", 1),
             ("SAVE_SCHEMA_VERSION_V2", 2),
-            ("SAVE_SCHEMA_VERSION", 2),
-            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1, 2}),
-            # stateContract + rulesVersion are STABLE across v1/v2 (GM-09f).
+            ("SAVE_SCHEMA_VERSION_V3", 3),
+            ("SAVE_SCHEMA_VERSION", 3),
+            ("SUPPORTED_SAVE_SCHEMA_VERSIONS", {1, 2, 3}),
+            # stateContract + rulesVersion are STABLE across v1/v2/v3 (GM-09f/GM-10h).
             ("SAVE_STATE_CONTRACT", "mini-metro-save-v1"),
             ("SAVE_RULES_VERSION", "rules-v1"),
         ):
             self.assertEqual(getattr(schema, name, None), expected, name)
         validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
         _, document = _document(self)
-        self.assertEqual(document["schemaVersion"], 2)
+        self.assertEqual(document["schemaVersion"], 3)
         self.assertEqual(document["stateContract"], "mini-metro-save-v1")
         self.assertEqual(document["rulesVersion"], "rules-v1")
-        # A freshly serialized game is v2 and carries the map identity (classic@1).
+        # A freshly serialized game is v3 and carries the map identity (classic@1)
+        # plus the additive tunnelBonus (0 with no upgrade applied; GM-10h).
         self.assertEqual(document["mapId"], "classic")
         self.assertEqual(document["mapDefinitionVersion"], 1)
+        self.assertEqual(document["tunnelBonus"], 0)
         self.assertIsNone(validate_save(document))

     def test_schema_version_and_pinned_literal_strictness(self):
@@ -179,8 +182,8 @@ class TestGM07bSaveSchemaVersioning(unittest.TestCase):
         mutations = {
             "bool-true schemaVersion": _setter((), "schemaVersion", True),
             "bool-false schemaVersion": _setter((), "schemaVersion", False),
-            # 2 is now SUPPORTED (v2); 3 is the forward version that must be rejected.
-            "forward schemaVersion": _setter((), "schemaVersion", 3),
+            # 3 is now SUPPORTED (v3, GM-10h); 4 is the forward version to reject.
+            "forward schemaVersion": _setter((), "schemaVersion", 4),
             "zero schemaVersion": _setter((), "schemaVersion", 0),
             "string schemaVersion": _setter((), "schemaVersion", "1"),
             "float schemaVersion": _setter((), "schemaVersion", 1.0),
@@ -310,6 +313,10 @@ class TestGM07bSaveSchemaValues(unittest.TestCase):
             "bool overdueThreshold": _setter((), "overduePassengerThreshold", True),
             "bool deliveries": _setter((), "deliveries", True),
             "bool numMetros": _setter((), "numMetros", True),
+            # GM-10h: the v3 tunnelBonus is a nonnegative non-bool int.
+            "bool tunnelBonus": _setter((), "tunnelBonus", True),
+            "negative tunnelBonus": _setter((), "tunnelBonus", -1),
+            "float tunnelBonus": _setter((), "tunnelBonus", 1.0),
             "int isGameOver": _setter((), "isGameOver", 1),
             "string steps": _setter((), "steps", "3"),
             "float timeMs": _setter((), "timeMs", 1.5),
diff --git a/test/test_gm09f_save_map.py b/test/test_gm09f_save_map.py
index 15a1989..53eed40 100644
--- a/test/test_gm09f_save_map.py
+++ b/test/test_gm09f_save_map.py
@@ -44,11 +44,14 @@ def _river_crossing_mediator():


 def _as_v1(document):
-    """A v1 document: drop the v2 map keys and set schemaVersion 1 (old save shape)."""
+    """A v1 document: drop the v2 map keys AND the v3 tunnelBonus (GM-10h), and set
+    schemaVersion 1 (old save shape). A fresh serialize is v3, so all three added keys
+    must be stripped or the v1 exact-key set rejects the doc for the wrong reason."""
     v1 = copy.deepcopy(document)
     v1["schemaVersion"] = 1
     del v1["mapId"]
     del v1["mapDefinitionVersion"]
+    del v1["tunnelBonus"]
     return v1


@@ -61,7 +64,7 @@ class TestGM09fRoundTrip(unittest.TestCase):
             ("lake", LAKE),
         ):
             document = serialize_game(Mediator(seed=0, map_definition=map_def))
-            self.assertEqual(document["schemaVersion"], 2)
+            self.assertEqual(document["schemaVersion"], 3)
             self.assertEqual(document["mapId"], name)
             self.assertEqual(document["mapDefinitionVersion"], 1)
             validate_save(document)
diff --git a/test/test_gm10h_persistence.py b/test/test_gm10h_persistence.py
new file mode 100644
index 0000000..0fad4e9
--- a/test/test_gm10h_persistence.py
+++ b/test/test_gm10h_persistence.py
@@ -0,0 +1,227 @@
+"""GM-10h contract: fleet/tunnel upgrade-bonus persistence (save/Continue) (D-045).
+
+A weekly LOCOMOTIVE/CARRIAGE upgrade grows `num_metros`/`num_carriages` (fleet TOTALS);
+a TUNNEL upgrade adds a persisted `tunnel_bonus` to the map budget. GM-10h makes these
+survive save/load via an additive save-schema v3:
+- v3 adds one key, `tunnelBonus`; the fleet is persisted as its GROWN totals (no bonus
+  field), and the running-config pin is v3-relaxed to `>= config`.
+- `serialize_game` rejects a desynced/forged upgrade state BEFORE the atomic write, so a
+  bad state can never clobber a valid autosave (load-time rejection is too late).
+- `within_tunnel_budget` folds the bonus, so a tunnel upgrade actually UNBLOCKS a crossing.
+- v1/v2 saves stay byte-frozen and load with a 0 bonus. The effects (GM-10e/f/g) are still
+  stubs; these tests drive DIRECTLY-SET grown state.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import unittest
+from types import SimpleNamespace
+
+sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
+
+import pygame
+
+from config import num_carriages as CONFIG_NUM_CARRIAGES
+from config import num_metros as CONFIG_NUM_METROS
+from crossings import within_tunnel_budget
+from env import MiniMetroEnv
+from geometry.point import Point
+from maps import resolve_map
+from mediator import Mediator
+from recursive_checkpoint import canonical_checkpoint
+from rl.player_env import PlayerPixelEnv
+from save_game import serialize_game
+from save_load import deserialize_game
+
+pygame.init()
+
+_FIXTURES = os.path.dirname(os.path.realpath(__file__)) + "/../scripts/fixtures"
+
+
+def _played(seed=0, map_definition=None):
+    kwargs = {"seed": seed}
+    if map_definition is not None:
+        kwargs["map_definition"] = map_definition
+    m = Mediator(**kwargs)
+    for _ in range(200):
+        m.increment_time(17)
+    return m
+
+
+class TestGM10hFleetPersistence(unittest.TestCase):
+    def test_grown_fleet_round_trips(self):
+        m = _played()
+        m.num_metros = CONFIG_NUM_METROS + 1
+        m.num_carriages = CONFIG_NUM_CARRIAGES + 2
+        loaded = deserialize_game(serialize_game(m))
+        self.assertEqual(loaded.num_metros, CONFIG_NUM_METROS + 1)
+        self.assertEqual(loaded.num_carriages, CONFIG_NUM_CARRIAGES + 2)
+
+    def test_serialize_rejects_a_fleet_below_config_before_writing(self):
+        # BLOCKER-1: a below-config total is corrupt; serialize must reject it BEFORE
+        # the atomic write, or it would clobber a valid autosave with an unloadable one.
+        m = _played()
+        m.num_metros = CONFIG_NUM_METROS - 1
+        with self.assertRaisesRegex(ValueError, "below the running config"):
+            serialize_game(m)
+
+    def test_a_forged_high_fleet_total_loads_authoritatively(self):
+        # DECISION (D-045): fleet totals are authoritative editable state -- a forged
+        # high total loads (like a forged `deliveries`/`score`), matching the threat
+        # model. The relaxed v3 pin accepts numMetros >= config.
+        m = _played()
+        m.num_metros = 99
+        loaded = deserialize_game(serialize_game(m))
+        self.assertEqual(loaded.num_metros, 99)
+
+
+class TestGM10hTunnelPersistence(unittest.TestCase):
+    def test_tunnel_bonus_round_trips_and_grows_num_tunnels(self):
+        r = _played(map_definition=resolve_map("river", 1))
+        r.tunnel_bonus = 2
+        self.assertEqual(r.num_tunnels, 3 + 2, "num_tunnels folds the bonus")
+        loaded = deserialize_game(serialize_game(r))
+        self.assertEqual(loaded.tunnel_bonus, 2)
+        self.assertEqual(loaded.num_tunnels, 5)
+
+    def test_the_bonus_unblocks_a_real_over_budget_crossing(self):
+        # The LOAD-BEARING trap: within_tunnel_budget reads the map budget DIRECTLY, so
+        # the bonus must be folded THERE. A candidate crossing RIVER 4x is over budget 3
+        # but fits budget 3+2. Proves the bonus UNBLOCKS the crossing, not just the count.
+        river = resolve_map("river", 1)
+        band = river.rivers[0]
+        y = (band[1] + band[3]) / 2
+        left, right = band[0] - 100, band[2] + 100
+
+        def stn(x):
+            return SimpleNamespace(position=Point(x, y))
+
+        route = [stn(left), stn(right), stn(left), stn(right), stn(left)]  # 4 crossings
+        no_bonus = SimpleNamespace(map_definition=river, paths=(), tunnel_bonus=0)
+        bonus = SimpleNamespace(map_definition=river, paths=(), tunnel_bonus=2)
+        self.assertFalse(
+            within_tunnel_budget(no_bonus, route, False), "4 crossings > budget 3"
+        )
+        self.assertTrue(
+            within_tunnel_budget(bonus, route, False), "bonus 2 lifts the budget to 5"
+        )
+
+    def test_serialize_and_load_reject_a_tunnel_bonus_on_an_unbounded_map(self):
+        # A nonzero bonus is unreachable on CLASSIC (never offers TUNNEL; num_tunnels
+        # stays None). Both save surfaces reject it.
+        c = _played()
+        c.tunnel_bonus = 1
+        self.assertIsNone(c.num_tunnels, "the bonus is ignored on an unbounded map")
+        with self.assertRaisesRegex(ValueError, "unbounded-tunnel map"):
+            serialize_game(c)
+
+
+class TestGM10hSchemaAndBackwardCompat(unittest.TestCase):
+    def test_fresh_save_is_v3_with_a_zero_bonus(self):
+        doc = serialize_game(_played())
+        self.assertEqual(doc["schemaVersion"], 3)
+        self.assertEqual(doc["tunnelBonus"], 0)
+
+    def test_v1_and_v2_fixtures_deserialize_with_a_zero_bonus(self):
+        # review MINOR-5: DESERIALIZE (runs _require_running_config), not just validate.
+        for name in ("save-v1.json", "save-v2-classic.json"):
+            from save_game import load_game
+
+            loaded = load_game(f"{_FIXTURES}/{name}")
+            self.assertEqual(loaded.tunnel_bonus, 0, f"{name} loads a 0 bonus")
+            self.assertEqual(loaded.num_metros, CONFIG_NUM_METROS)
+
+    def test_a_v3_document_missing_the_bonus_key_is_rejected(self):
+        from save_schema import validate_save
+
+        doc = serialize_game(_played())
+        del doc["tunnelBonus"]  # a v3 doc MUST carry it
+        with self.assertRaises(ValueError):
+            validate_save(doc)
+
+    def test_a_v2_document_carrying_the_bonus_key_is_rejected(self):
+        from save_schema import validate_save
+
+        doc = serialize_game(_played())
+        doc["schemaVersion"] = 2  # a v2 doc must NOT carry tunnelBonus
+        with self.assertRaises(ValueError):
+            validate_save(doc)
+
+    def test_the_map_identity_gate_still_fires_on_a_v3_document(self):
+        from save_schema import validate_save
+
+        doc = serialize_game(_played())
+        doc["mapId"] = "river "  # forged: whitespace -- must still be rejected on v3
+        with self.assertRaises(ValueError):
+            validate_save(doc)
+
+
+class TestGM10hStateLegality(unittest.TestCase):
+    def test_load_legality_uses_the_bonus_aware_budget(self):
+        # review MINOR: _require_legal_map_state must compare consumed crossings against
+        # the BONUS-AWARE num_tunnels, not the raw map budget. A synthetic host whose
+        # consumed count falls in (budget, budget+bonus] is legal WITH the bonus, and a
+        # raw-budget mutant would wrongly reject it. (A full committed-crossing round-trip
+        # needs many delivery-unlocked stations; it lands with the TUNNEL effect in
+        # GM-10g -- D-045. This pins the load-legality math now.)
+        from save_load import _require_legal_map_state
+
+        river = resolve_map("river", 1)  # budget 3
+        legal = SimpleNamespace(
+            num_tunnels=5, consumed_tunnels=4, all_stations=[], tunnel_bonus=2
+        )
+        _require_legal_map_state(
+            legal, river
+        )  # 4 <= 5: no raise (raw budget 3 rejects)
+        over = SimpleNamespace(
+            num_tunnels=5, consumed_tunnels=6, all_stations=[], tunnel_bonus=2
+        )
+        with self.assertRaisesRegex(ValueError, "exceed the map's tunnel budget"):
+            _require_legal_map_state(over, river)
+
+    def test_load_rejects_a_forged_tunnel_bonus_on_an_unbounded_map(self):
+        # A forged v3 doc bypasses the serialize-time guard, so the post-LOAD legality
+        # check (_require_legal_map_state) must ALSO reject a nonzero bonus on an
+        # unbounded (CLASSIC) map -- both save surfaces agree.
+        doc = serialize_game(_played())  # CLASSIC, tunnelBonus 0, valid
+        doc["tunnelBonus"] = 3  # forge a nonzero bonus on an unbounded map
+        with self.assertRaisesRegex(ValueError, "unreachable on an unbounded"):
+            deserialize_game(doc)
+
+
+class TestGM10hRLUnaffected(unittest.TestCase):
+    def test_headless_env_keeps_config_fleet_and_zero_bonus(self):
+        env = MiniMetroEnv()
+        env.reset(seed=0)
+        for _ in range(1200 + 60):
+            env.mediator.step_time(17)
+        self.assertEqual(env.mediator.num_metros, CONFIG_NUM_METROS)
+        self.assertEqual(env.mediator.num_carriages, CONFIG_NUM_CARRIAGES)
+        self.assertEqual(env.mediator.tunnel_bonus, 0)
+
+    def test_pixel_env_keeps_a_zero_bonus(self):
+        env = PlayerPixelEnv()
+        env.reset(seed=0)
+        self.assertEqual(env._mediator.tunnel_bonus, 0)
+
+    def test_the_checkpoint_carries_no_bonus_and_config_fleet(self):
+        # No checkpoint schema change (BLOCKER-2 scoping): a bonus is absorbed into the
+        # fleet totals and the RL path never applies an offer, so the checkpoint has no
+        # tunnel/bonus key and records the config fleet.
+        import json
+
+        env = MiniMetroEnv()
+        env.reset(seed=0)
+        checkpoint = canonical_checkpoint(env)
+        # No tunnel/bonus state anywhere in the canonical checkpoint (it drops the
+        # tunnels observation block, and the RL path never applies an offer).
+        self.assertNotIn("tunnel", json.dumps(checkpoint).lower())
+        self.assertEqual(
+            checkpoint["progression"]["limits"]["num_metros"], CONFIG_NUM_METROS
+        )
+
+
+if __name__ == "__main__":
+    unittest.main()
```

## Docs
```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index 0c9eb4a..4a50be7 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -382,6 +382,7 @@ python_mini_metro/
 - GM-10b (D-042) adds the weekly OFFER GENERATOR. A new dependency-light `src/offers.py` (stdlib-only — `enum`/`dataclasses`/`random`, no pygame/mediator, so it is import-safe on every headless/RL path) owns the data model (`OfferKind`, frozen `Offer`, `describe`) and a PURE `generate_offers(rng, *, count, tunnels_bounded)` that draws `count` DISTINCT kinds via `rng.sample` from an explicitly-ordered pool — the four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map. `config.OFFERS_PER_WEEK` (2) sets the count. When `Mediator._maybe_hold_week_boundary` fires (same calendar/crossing/not-game-over gate as the hold), it stores `self.current_offers` from `generate_offers`; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel (byte-stable on repeat). The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr, cross-process stable) — a deliberate design choice (dual-plan-reviewed): reading the state consumes no gameplay draws (station spawns stay byte-identical) AND, because that gameplay RNG state is already restored exactly on Continue, the same week's offers reproduce byte-exact after save/load with NO new persisted state. So GM-10b adds ZERO save/checkpoint/observation bytes (the `rng` block, exact-key save validation, checkpoint schema, and every frozen fixture are untouched) and never runs off the human path. Applying a choice is GM-10c, per-kind effects GM-10d–g, and applied-offer/replay persistence GM-10h (which must not trail GM-10c). (Adding `offers.py` and editing the runtime `src` files rotates the LIVE RL content fingerprint — `compute_content_fingerprint` hashes all of `src/**` — so a pre-GM-10b manifest fails strict resume/eval by default; EXPECTED and correct for fresh runs, no frozen fixture is repinned since `EXPECTED_LF_TRAINING` pins only `TRAINING_SOURCE_PATHS`, which excludes these files.)
 - GM-10c (D-043) makes the offers SELECTABLE. `menu_screens.offer_menu_layout(width, height, count)` now returns one button rect per offer (keys `offer_0..offer_{count-1}`); `draw_offer_screen` paints each offer as a button. `AppController._handle_offer` arms a button on mouse-down and, on a matching mouse-up (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to `Mediator._apply_offer(offer)` (a `match offer.kind` over `OfferKind`, raising a named `ValueError` on an unknown kind) then clears `current_offers` and releases the pause; `None` is a forced resolve with no choice (the `main.run_game` window-close path, unchanged). The per-kind arms are NO-OP stubs in GM-10c — choosing changes NO game state, so it is Continue-safe with ZERO new persisted bytes (the state-inertness is test-locked against the full `serialize_game` doc). The real effects are GM-10d–g: a NEW_LINE grant can flow through the already-persisted `purchased_num_paths` (Continue-safe standalone), while the LOCOMOTIVE/CARRIAGE grants hit `save_load._require_running_config` (which pins `numMetros`/`numCarriages` to config) and the TUNNEL grant needs a persisted bonus, so those must land with GM-10h.
 - GM-10d (D-044) fills the FIRST per-kind offer effect: `OfferKind.NEW_LINE` grants a free line. `NetworkProgression.grant_free_path()` bumps `purchased_num_paths` by one (capped at `num_paths`, returning whether it granted) — `record_path_purchase` MINUS the `line_credits` spend; `Mediator._grant_free_line` calls it and, on a grant, `update_unlocked_num_paths()` to refresh the derived `unlocked_num_paths` + path-button lock states (the exact purchase-flow cache refresh). The `_apply_offer` NEW_LINE arm now calls it (the locomotive/carriage/tunnel arms stay no-op — GM-10e/f/g). Because `purchased_num_paths` is already persisted and `_require_running_config` pins the TOTAL `numPaths` (unchanged), a granted line is Continue-exact with NO save/checkpoint-schema change (proven by round-trip); at the `num_paths` cap the grant is a state-inert no-op. Known limitation (deferred as GM-11 balance): a NEW_LINE offer generated when already at the cap is a wasted pick — excluding it from the pool would couple `generate_offers` to `purchased_num_paths`. `resolve_week_boundary(offer)` CONFINES application to a genuine pending choice — it raises unless the offer is one of `current_offers` at a held boundary — so no out-of-band call (a headless `MiniMetroEnv` with no calendar, a fabricated offer, or an offer the week did not present) can grant an upgrade and bypass the weekly economy. The GM-10a–d week-boundary hold + offer generate/apply LOGIC is factored into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023 — the mediator crossed the 1000-line hard ceiling; the facade reads/writes the host mediator's already-owned state — `steps`/`week_calendar`/`current_offers`/`context`/`_progression` — with no new fields, and invokes the spy-able seams `_apply_offer`/`_grant_free_line`/`_offer_rng_for_current_week` through the host, so the mediator keeps its public API); `mediator.py` drops to 940 lines and delegates.
+- GM-10h (D-045) adds the SAVE/CONTINUE persistence a fleet/tunnel weekly upgrade needs (the prerequisite for the GM-10e/f/g effects), via an additive save-schema **v3**. `save_schema` gains `SAVE_SCHEMA_VERSION_V3 = 3` (`SUPPORTED = {1,2,3}`, current = 3) and ONE additive key `tunnelBonus` (`_TOP_LEVEL_KEYS_V3 = _TOP_LEVEL_KEYS_V2 | {tunnelBonus}`, a version-gated `_validate_tunnel_bonus` nonnegative-int check, and the map-identity gate widened to `version in {V2, V3}`). The FLEET is persisted as its grown TOTALS (no bonus field — `num_metros`/`num_carriages` are already stored attrs that 17 tests + the carriage rollback assign, so they can't be derived): `save_load._require_running_config` keeps `numPaths == config` for all and `numMetros`/`numCarriages == config` for v1/v2 but only `>= config` for v3. The TUNNEL gains a stored `Mediator.tunnel_bonus` (0 until upgraded) folded into the `num_tunnels` property (`None if budget is None else budget + tunnel_bonus`), which fixes `available_tunnels`/the env `tunnels` observation/`_require_legal_map_state` for free; the load-bearing fix is that `crossings.within_tunnel_budget` reads `map_definition.tunnel_budget` DIRECTLY, so the bonus is folded there too (`+ getattr(host, "tunnel_bonus", 0)`) or a bonus would never unblock a real crossing. `save_game.serialize_game` runs a new `_require_valid_upgrade_state` FIRST — a below-config fleet or a nonzero tunnel bonus on an unbounded map is rejected BEFORE the atomic write, so a desynced/forged state can't clobber a valid autosave; restore defaults `tunnelBonus` on absence. v1/v2 fixtures stay byte-frozen; the frozen `scripts/fixtures/save-v3-classic.json` pins the additive v2→v3 upgrade. NO checkpoint-schema change (a bonus is absorbed into the totals; RL never applies an offer, so bonuses stay 0 and the observation/checkpoint bytes are unchanged). A forged high fleet total loads (authoritative editable state, matching the threat model); a nonzero tunnel bonus is legal only on a bounded map. Applied-offer persistence is this unit; PENDING-offer (mid-offer) persistence is GM-10i.
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
diff --git a/PROGRESS.md b/PROGRESS.md
index 42e2c03..85694aa 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -184,3 +184,4 @@
 - Continued GM-10 with GM-10b, the dedicated-RNG weekly OFFER GENERATOR (D-042). A new stdlib-only `src/offers.py` (`OfferKind`/`Offer`/pure `generate_offers`) draws `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers from a map-appropriate pool (New Line / +1 Locomotive / +1 Carriage, plus +1 Tunnel only on a finite-tunnel map); `Mediator._maybe_hold_week_boundary` stores `current_offers` at the hold and `resolve_week_boundary` clears them; `draw_offer_screen` previews the labels read-only. The offer RNG is a dedicated per-week `random.Random` derived READ-ONLY from `python_random.getstate()` + `week_index` — a DUAL-PLAN-REVIEW pivot: Codex BLOCKED the first plan (a persisted `spawn(3)` stream deferred to GM-10h would RESET on Continue and diverge, violating README's "Continue resumes exactly"), so offers are instead derived from the already-persisted gameplay RNG state, making them Continue-EXACT with ZERO new save/checkpoint/observation bytes and gameplay-INERT (getstate consumes no draws — station spawns stay byte-identical, every frozen fixture untouched). Gated to the human shell like the calendar, so RL/headless/tutorial never generate (`current_offers` stays `()`). Empirically pre-validated (cadence ~4-6 weeks/game; separate-stream inertness; spawn byte-compat; Continue-exactness of the boundary python-state — all proven before planning). Dual plan review (harness REVISE + Codex BLOCK → the stateless pivot) + dual impl review folded. Applying a choice is GM-10c, per-kind effects GM-10d-g, applied-offer persistence GM-10h (which must not trail GM-10c). Full `py313` suite green (1527 tests).
 - Continued GM-10 with GM-10c, the week-boundary CHOICE CONTROLS (D-043). The GM-10b read-only preview becomes interactive: `menu_screens.offer_menu_layout(width, height, count)` returns one button per offer (`offer_0..offer_{count-1}`), `draw_offer_screen` paints them, and `AppController._handle_offer` arms a button on press and, on a matching release (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to a new `_apply_offer` (`match offer.kind`, named `ValueError` on an unknown kind) then clears + releases; `None` is the window-close forced resolve (unchanged). The per-kind arms are NO-OP stubs — choosing changes NO game state, so GM-10c is Continue-safe with ZERO new persisted bytes (locked by a test asserting every kind leaves the full `serialize_game` doc byte-identical). The real effects are GM-10d-g: NEW_LINE can ride the already-persisted `purchased_num_paths` (Continue-safe standalone), while LOCOMOTIVE/CARRIAGE hit `_require_running_config` and TUNNEL needs a persisted bonus, so those land with GM-10h. Full `py313` suite green (1540 tests).
 - Continued GM-10 with GM-10d, the FIRST real per-kind offer effect (D-044): choosing NEW_LINE unlocks a free line. `NetworkProgression.grant_free_path()` bumps `purchased_num_paths` (capped at `num_paths`, no `line_credits` spend — `record_path_purchase` minus the cost); `Mediator._grant_free_line` calls it and refreshes the derived caches via `update_unlocked_num_paths()` (the exact purchase-flow refresh), wired into the `_apply_offer` NEW_LINE arm (locomotive/carriage/tunnel stay no-op — GM-10e/f/g). Empirically proven Continue-safe standalone (probe: grant → purchased 1→2, unlocked 1→2, credits unchanged; serialize→deserialize reproduces both; `numPaths` unchanged so `_require_running_config` holds), so NO save/checkpoint-schema change and GM-10d precedes GM-10h. The GM-10c all-kinds-inert test narrowed to the three still-stub kinds. Known limitation (GM-11 balance): a NEW_LINE offer at the line cap is a wasted no-op pick. Dual impl review (harness SHIP + Codex FIX-FIRST → production correct by BOTH; folded 4 gaps — Codex caught a robustness MAJOR (resolve now CONFINES application to a currently-presented pending choice, so no out-of-band/headless call can grant an upgrade and bypass the economy) + a mutation-weak cap `>=` (an above-cap test now pins it) + an unpinned unlock-blink + a stale comment). The GM-10a-d week/offer LOGIC was factored into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023) because `mediator.py` crossed the 1000-line hard ceiling; the extraction is behavior-preserving (mediator 940 lines; all offer tests green). Full `py313` suite green (1550 tests).
+- Continued GM-10 with GM-10h, the fleet/tunnel upgrade-bonus PERSISTENCE (D-045) -- the prerequisite the still-stub GM-10e/f/g effects need, pulled ahead of them because a fleet/tunnel bonus is not Continue-safe today. An additive save-schema `SAVE_SCHEMA_VERSION_V3 = 3` (`SUPPORTED = {1,2,3}`) adds ONE key `tunnelBonus` and v3-relaxes `save_load._require_running_config` so a grown fleet loads: `numPaths == config` always, `numMetros`/`numCarriages == config` for v1/v2 but `>= config` for v3 (the fleet is persisted as its grown TOTALS -- no bonus field -- because 17 tests + the carriage rollback assign `num_metros`/`num_carriages`, so they can't be derived). The tunnel gains a stored `Mediator.tunnel_bonus` folded into `num_tunnels` AND, the load-bearing fix, into `crossings.within_tunnel_budget` (which reads the map budget directly, so a bonus threaded only through `num_tunnels` would show in the observation/legality yet never unblock a crossing). `serialize_game` runs a new `_require_valid_upgrade_state` FIRST so a below-config fleet or a nonzero tunnel bonus on an unbounded map is rejected BEFORE the atomic write (a desynced/forged state can't clobber a valid autosave). v1/v2 fixtures stay byte-frozen; a new frozen `save-v3-classic.json` (15501 bytes) pins the v2->v3 upgrade; the three save contract tests repoint. NO checkpoint change (a bonus absorbs into the totals; RL never applies an offer). HIGH-RISK persistence migration -> DUAL plan review (harness REVISE + Codex ultra BLOCK, 2 BLOCKER + 5 MAJOR) drove a design PIVOT to the simpler relax-pin-not-field design (Codex's own suggestion), resolved the serialize-clobber BLOCKER via the pre-write guard, scoped the checkpoint out, re-homed mid-offer persistence to GM-10i, and rejected a nonzero tunnel bonus on unbounded maps (reachability). Full `py313` suite green (1566 tests). GM-10e (locomotive upgrade -- a trivial `num_metros += 1` arm on this infrastructure) opens next.
diff --git a/README.md b/README.md
index 7f2c89e..29cef23 100644
--- a/README.md
+++ b/README.md
@@ -214,13 +214,13 @@ Any unknown `type`, malformed action payload, or rejected action returns `info["
 ```python
 import save_game

-document = save_game.serialize_game(env.mediator)   # strict schema-v2 dict, never mutates the game
+document = save_game.serialize_game(env.mediator)   # strict schema-v3 dict, never mutates the game
 save_game.save_game(env.mediator, "saves/slot1.save.json")  # atomic canonical write
 mediator = save_game.load_game("saves/slot1.save.json")     # read + validate + reconstruct
 mediator = save_game.deserialize_game(document)             # reconstruct from an in-memory document
 ```

-- Save documents are versioned strict JSON (`save_schema.SAVE_SCHEMA_VERSION == 2`, `stateContract "mini-metro-save-v1"`, `rulesVersion "rules-v1"`). `save_schema.validate_save(document)` rejects unknown/missing keys, wrong scalar types (including bool-as-int), forward versions, malformed or out-of-domain RNG state, ID-grammar violations, path or metro references to locked stations, inconsistent bound-service records, and duplicate or dangling entity references; `load_game` additionally rejects duplicate JSON object keys at every level. Every rejection raises `ValueError`.
+- Save documents are versioned strict JSON (`save_schema.SAVE_SCHEMA_VERSION == 3`, `stateContract "mini-metro-save-v1"`, `rulesVersion "rules-v1"`). `save_schema.validate_save(document)` rejects unknown/missing keys, wrong scalar types (including bool-as-int), forward versions, malformed or out-of-domain RNG state, ID-grammar violations, path or metro references to locked stations, inconsistent bound-service records, and duplicate or dangling entity references; `load_game` additionally rejects duplicate JSON object keys at every level. Every rejection raises `ValueError`.
 - Bytes on disk are the pinned canonical encoding (`save_schema.canonical_save_bytes`: sorted-key, ASCII, compact separators, trailing LF). Saves go through a save-local atomic writer (mkstemp, fsync, `os.replace`), so a failed save leaves an existing destination untouched and no temporary file behind. The default directory name is `config.save_dir_name` (`saves/`, git-ignored); all functions accept explicit paths.
 - Saving is permitted only at a quiescent input boundary: an active path-creation, redraw, or edit gesture raises `ValueError` (a bare pressed mouse button does not block).
 - The human application shell (`src/main.py`) drives one canonical autosave slot at `saves/autosave.json`: it writes on opening the pause menu and on Exit to Title, keeps that save on a mid-run window close, deletes it at game over, and offers Continue on the title screen. Every autosave is best-effort and never blocks play or exit; the isolation-scanned headless, agent, recursive, and RL surfaces gain no save import.
@@ -229,8 +229,9 @@ mediator = save_game.deserialize_game(document)             # reconstruct from a
 - `src/audio.py` adds short, deterministic, procedurally-synthesized sound effects (no external audio files): a distinct tone plays when you complete a delivery, purchase a line, unlock a station, reach game over, or snap a line endpoint, each scaled by the master and SFX volumes. Audio is fail-safe — a missing or unavailable device degrades silently to a no-op backend and never blocks play. It is a main-only feature built solely at the interactive entry point, so headless, agent, recursive, and RL play open no audio device; `audio` joins the isolation scan and only `main` imports it.
 - A loaded game is checkpoint-identical to the saved one, both RNG streams included, and replays the identical seeded trajectory as a never-saved control, in the same process and across fresh processes replaying the same save file. Each metro's bound station-service action (with its fractional boarding timers) persists in the document and restores verbatim — including boundaries where the bound action is legitimately stale after a same-tick cross-metro effect — so post-load service resumes exactly like the never-saved game. Held pause reasons (`user`, `menu`) restore verbatim, so a game saved from the pause menu loads paused; `release_pause_reason("menu")` resumes it.
 - Entity ID strings survive save/load. Path IDs are structured-action selectors: a `path_id` observed before saving keeps selecting the same line against the loaded `Mediator`. Station, metro, carriage, and passenger IDs are stable observation/reference identity only — no structured action currently selects by them. IDs are minted per process, so two independently built games never share IDs (and their save files differ even under the same seed); determinism guarantees apply to reloading and replaying a given save file.
-- A save whose `numPaths`, `numMetros`, or `numCarriages` disagrees with the running config is rejected; any trajectory-affecting balance-config change bumps the save schema version (see D-026). The frozen v1 example lives at `scripts/fixtures/save-v1.json`.
+- A save whose `numPaths` disagrees with the running config is rejected; `numMetros`/`numCarriages` must equal the config on a v1/v2 save but may meet or exceed it on a v3 save (a locomotive/carriage weekly upgrade grows the fleet total, GM-10h; a fresh v3 save still equals the config), and a below-config total is rejected at serialize time before it can clobber a valid autosave. Any trajectory-affecting balance-config change bumps the save schema version (see D-026). The frozen v1 example lives at `scripts/fixtures/save-v1.json`.
 - Save schema v2 (GM-09f, D-038) records the MAP identity. A v2 document adds two additive top-level keys `mapId`/`mapDefinitionVersion`, so a non-Classic map (`river`/`delta`/`lake`) can be saved and loaded; new saves are v2, and `SUPPORTED_SAVE_SCHEMA_VERSIONS = {1, 2}`. A v1 document (no map keys) still loads by synthesizing `classic@1`, so the byte-frozen `save-v1.json` stays valid and loads as Classic; because the v1→v2 upgrade only changes the header, loading a v1 save and re-saving it produces exactly the frozen `scripts/fixtures/save-v2-classic.json` (its byte length + SHA are pinned). Serialization and load are fail-closed on two axes: the map definition must EQUAL its registered definition (a forged/drifted map is rejected — a save records only the map identity and rebuilds terrain from the registry on load), and the state must be LEGAL under that map (every station on the map's land, river crossings within the tunnel budget). Tunnel counts stay derived, so no crossing counter is persisted. Loading an unknown map id or an unsupported map version raises a clear, named error rather than silently falling back to Classic. `stateContract` and `rulesVersion` are unchanged across v1/v2.
+- Save schema v3 (GM-10h, D-045) persists a weekly TUNNEL upgrade. A v3 document adds one additive top-level key `tunnelBonus` (a nonnegative `+N` on the map's river-crossing budget), and v3-relaxes the fleet running-config pin so a locomotive/carriage upgrade's grown `numMetros`/`numCarriages` loads; `SUPPORTED_SAVE_SCHEMA_VERSIONS = {1, 2, 3}` and new saves are v3. A v1/v2 document (no `tunnelBonus`) still loads with a 0 bonus, so `save-v1.json`/`save-v2-classic.json` stay byte-frozen; re-saving either produces the frozen `scripts/fixtures/save-v3-classic.json` (its byte length + SHA are pinned). A nonzero tunnel bonus is legal only on a bounded (river/delta/lake) map — CLASSIC never offers TUNNEL and rejects one on save and load. The tunnel bonus threads into the crossing gate, so an upgrade actually unblocks the extra crossing. Fleet upgrades are persisted as the grown TOTALS (no separate bonus field); `stateContract`/`rulesVersion` stay unchanged.

 # Player-equivalent reinforcement learning

diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index b08e3ee..52c54c8 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -254,7 +254,7 @@ Reason: the save (GM-09f) and high-score (GM-09f2) recorders were deliberately m

 ## D-041

-Decision: GM-10a opens GM-10 (weekly progression) with the simulation CALENDAR — a deterministic week boundary that pauses the sim for an explicit player continue, the foundation the later sub-units (GM-10b offers, GM-10c choice UI, GM-10d-g upgrades, GM-10h persistence) build on. A "week" is `config.WEEK_LENGTH_STEPS` sim steps (provisional 1200 ≈ 20 s at 1×, a GM-11 balance target). `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement — placement matters, review MAJOR), holds a new `"week"` pause reason when the calendar is enabled, this tick crossed a new boundary (`old_steps // W < steps // W`, integer division so 1×/2×/4× never skip), and the run is NOT game over (so a terminal tick promotes to GAME_OVER, review MAJOR). `"week"` joins `_PAUSE_REASONS` and freezes the sim through the existing gate; unlike `"user"`/`"menu"` it is never cleared by the Space toggle or speed buttons. `week_index` is DERIVED from the already-persisted `steps` (no new stored scalar). The human shell promotes a pending boundary to a new `AppScreen.OFFER` modal via `AppController.reconcile_week_boundary()` — run per-frame AFTER `reconcile_game_over`, no-op unless PLAYING/not-terminal, cancelling any armed gameplay gesture through the pinned letterbox-cancel before switching (review MAJOR) — whose armed Continue (down→up on the control) calls `mediator.resolve_week_boundary()` and resumes PLAYING (review MAJOR). Closing the window mid-offer resolves then autosaves (window-close→Continue promise, review MINOR); the offer frame's audio deltas are consumed silently (review MINOR); saving is blocked while a boundary is pending (a clearer error over `validate_save`'s existing vocabulary rejection). The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it; RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, frame-limited/headless smoke runs, and all tests leave it off. NO save-schema and NO checkpoint-schema change; the RL observation of the week and mid-offer persistence are deferred to GM-10b/GM-10h.
+Decision: GM-10a opens GM-10 (weekly progression) with the simulation CALENDAR — a deterministic week boundary that pauses the sim for an explicit player continue, the foundation the later sub-units (GM-10b offers, GM-10c choice UI, GM-10d-g upgrades, GM-10h persistence) build on. A "week" is `config.WEEK_LENGTH_STEPS` sim steps (provisional 1200 ≈ 20 s at 1×, a GM-11 balance target). `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement — placement matters, review MAJOR), holds a new `"week"` pause reason when the calendar is enabled, this tick crossed a new boundary (`old_steps // W < steps // W`, integer division so 1×/2×/4× never skip), and the run is NOT game over (so a terminal tick promotes to GAME_OVER, review MAJOR). `"week"` joins `_PAUSE_REASONS` and freezes the sim through the existing gate; unlike `"user"`/`"menu"` it is never cleared by the Space toggle or speed buttons. `week_index` is DERIVED from the already-persisted `steps` (no new stored scalar). The human shell promotes a pending boundary to a new `AppScreen.OFFER` modal via `AppController.reconcile_week_boundary()` — run per-frame AFTER `reconcile_game_over`, no-op unless PLAYING/not-terminal, cancelling any armed gameplay gesture through the pinned letterbox-cancel before switching (review MAJOR) — whose armed Continue (down→up on the control) calls `mediator.resolve_week_boundary()` and resumes PLAYING (review MAJOR). Closing the window mid-offer resolves then autosaves (window-close→Continue promise, review MINOR); the offer frame's audio deltas are consumed silently (review MINOR); saving is blocked while a boundary is pending (a clearer error over `validate_save`'s existing vocabulary rejection). The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it; RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, frame-limited/headless smoke runs, and all tests leave it off. NO save-schema and NO checkpoint-schema change; the RL observation of the week is deferred to GM-10b and PENDING-offer (mid-offer) persistence to GM-10i (re-homed from GM-10h by D-045, which persists only APPLIED fleet/tunnel upgrades).

 Reason: the DUAL plan review (both REVISE) was decisive — the harness caught a BLOCKER and Codex went far deeper (2 BLOCKER + 4 MAJOR with reproduced live counterexamples). (1) My first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` (the first-class RL boundary) drives via `GameSession.advance_exact` and the tutorial is a third direct-Mediator shell — all would soft-lock permanently at step 1200. GATING the calendar to interactive human play (a `week_calendar` flag, default OFF) resolves every headless shell structurally (the hold never occurs) and removes the `env.py` change entirely. (2) My "a pause is trajectory-invariant" premise was FALSE — my probe used direct `increment_time` (fixed 17 ms) and bypassed the `(17,17,16)` `FixedStepClock` cadence, which a pause resets, so `time_ms` diverges at identical `steps`; but gating keeps the calendar out of every deterministic/RL/exact-tick path, so their trajectory is byte-identical (the branch is never taken), and the cadence reset is PRE-EXISTING behavior shared by the `user`/`menu` pauses on the already-non-deterministic human wall-clock path — so no version bump and no clock fix here. (3) The hold placement, terminal precedence, gesture-cancel/arming, window-close, and audio edges were all reproduced by Codex and folded with pinned regressions. Persistence is deferred because GM-10h owns it and `week_index` rides on `steps`; the RL offer integration is GM-10b/GM-12. `WEEK_LENGTH_STEPS=1200` is a provisional foundation default (fixed, not escalating — escalation is GM-11). GM-10b (deterministic dedicated-RNG offers) opens next.

@@ -277,3 +277,9 @@ Decision: GM-10d fills the FIRST per-kind offer effect — `OfferKind.NEW_LINE`
 Reason: NEW_LINE is the one effect that is Continue-safe STANDALONE (D-043), so it can precede GM-10h — proven empirically before implementing (probe this session): a grant takes `purchased_num_paths` 1→2 and `unlocked_num_paths` 1→2 with `line_credits` unchanged; `serialize_game`→`deserialize_game` reproduces both; and the save still loads because `_require_running_config` pins the TOTAL `numPaths` (4, unchanged), not `purchasedNumPaths` (already a save field). So GM-10d adds NO save/checkpoint-schema change and NO new persisted bytes. The grant reuses the domain owner (`NetworkProgression`) for the counter+cap and the mediator's existing `update_unlocked_num_paths` for the cache refresh, rather than duplicating either — a free line is precisely a bought line without the bill. KNOWN LIMITATION (deferred to GM-11 balance, documented in ARCHITECTURE): a NEW_LINE offer GENERATED when the player is already at `num_paths` lines is a wasted no-op pick; excluding it from the pool would couple `generate_offers` to `purchased_num_paths`, and it is rare (4 lines is late-game). GM-10e (locomotive upgrade) opens next; it and GM-10f (carriage) bump `num_metros`/`num_carriages`, which `_require_running_config` pins to config, so they must land with GM-10h's persistence relaxation.

 Two impl-review folds landed with GM-10d. (1) `resolve_week_boundary(offer)` now CONFINES application to a genuine pending choice — it raises unless `offer` is one of `current_offers` at a held boundary (`is_week_boundary_pending`) — so the public mediator method cannot be driven out-of-band (a headless `MiniMetroEnv` with no calendar, a fabricated offer, or a kind the week did not present) to grant an upgrade and bypass the weekly economy (Codex MAJOR; the normal `_handle_offer` path always passes a `current_offers[index]` at a held boundary, so it is unaffected). (2) The GM-10a–d week-boundary hold + offer generate/apply LOGIC was FACTORED OUT of `Mediator` into a new `src/weekly_offers.py` `WeeklyOffers` facade (D-023): the addition pushed `mediator.py` past the 1000-line HARD ceiling (test-enforced), and the fleet canon is "split rather than grow god-objects." The facade is stateless — it reads/writes the host mediator's already-owned state (`steps`/`week_calendar`/`current_offers`/`context`/`_progression`) with no new fields, and invokes the spy-able seams (`_apply_offer`/`_grant_free_line`/`_offer_rng_for_current_week`) through the host so a test patching those still intercepts and the mediator keeps its public API. The extraction is behavior-preserving (`mediator.py` 940 lines; every offer/calendar test green), verified by the full suite rather than re-review since it relocates already-reviewed logic without changing behavior.
+
+## D-045 — GM-10h: fleet/tunnel upgrade persistence (save/Continue), an additive save-schema v3
+
+Decision: GM-10h adds the SAVE/CONTINUE persistence a weekly fleet/tunnel upgrade needs, so the still-stub GM-10e/f/g effects can land. An additive save-schema **v3** (`SUPPORTED = {1,2,3}`, new saves v3) adds exactly ONE key, `tunnelBonus` (a nonnegative `+N` on the map's river-crossing budget), and v3-RELAXES the fleet running-config pin. The FLEET carries NO bonus key — `num_metros`/`num_carriages` are already stored TOTALS an upgrade only grows, so `_require_running_config` keeps `numPaths == config` and `numMetros`/`numCarriages == config` for v1/v2 but only `>= config` for v3 (a below-config total is corrupt). The TUNNEL has no stored total (`num_tunnels` derives from the immutable `map_definition.tunnel_budget`), so a persisted `tunnel_bonus` mediator attr is the only way; `num_tunnels` becomes `None if budget is None else budget + tunnel_bonus`. The LOAD-BEARING fix: `crossings.within_tunnel_budget` reads `map_definition.tunnel_budget` DIRECTLY (not `mediator.num_tunnels`), so the bonus is folded THERE too — else it would show in the observation/legality yet never unblock a crossing. `serialize_game` runs a new `_require_valid_upgrade_state` FIRST — a below-config fleet or a nonzero tunnel bonus on an unbounded map is rejected BEFORE the atomic write, so a desynced/forged state can never clobber a valid autosave (load-time rejection is too late). Restore defaults `tunnelBonus` on absence (`document.get(..., 0)`, never `x or 0` — a real 0 is falsy). v1/v2 fixtures stay byte-frozen; the new frozen `save-v3-classic.json` (15501 bytes) pins the v2→v3 additive upgrade; `test_gm07b_save_schema`/`test_gm09f_save_map`/`test_gm07b_save_determinism` repoint their contract pins. NO checkpoint-schema change: a bonus is absorbed into the fleet totals, the checkpoint carries no tunnel state, and the RL/replay path never applies an offer (bonuses 0 there), so the observation/checkpoint bytes are unchanged. Editing the runtime `src` files rotates the LIVE RL content fingerprint (expected; `EXPECTED_LF_TRAINING` pins only training sources) — distinct from that byte stability. Applied-offer persistence is GM-10h (this unit); PENDING-offer (mid-offer) persistence is RE-HOMED to a named later unit **GM-10i** (a different mechanism — the pending pause reason + the offer tuple — not the applied-bonus persistence), and the `main.py`/`save_game.py` comments + D-041 are reconciled to say so. GM-10e/f/g (locomotive/carriage/tunnel effects) now ride on this infrastructure; then GM-10h's siblings complete GM-10.
+
+Reason: a design PIVOT forced by the dual plan review (harness REVISE — omitted contract-test surfaces + the `.get` guard; Codex ultra BLOCK — 2 BLOCKER + 5 MAJOR). Codex BLOCKER-1 (`serialize_game` would accept a desynced total/bonus and ATOMICALLY clobber a valid autosave with an unloadable one — load-time rejection is too late) + BLOCKER-3/MAJOR-3 (a `num_carriages_bonus` field would sit OUTSIDE the carriage-rollback contract → desync) both pointed to a SIMPLER design, which Codex itself suggested ("derive fleet bonuses from the stored totals"): DROP the fleet bonus field entirely and just relax the pin. That dissolves the desync, the rollback-contract gap, and the v1/v2 KeyError hazard, and collapses v3 to one key. Codex BLOCKER-2 ("no checkpoint change" contradicts a tunnel checkpoint/replay boundary) is resolved by SCOPING GM-10h to save/Continue and documenting that the tunnel bonus never reaches the RL/replay path. Codex MAJOR-4 (GM-10h silently dropped D-041's mid-offer persistence obligation) → re-homed to GM-10i with the source/decision reconciliation. Codex MAJOR-5 (the validator proves arithmetic, not reachability) → reject a nonzero tunnel bonus on an unbounded map at BOTH save surfaces; fleet totals are AUTHORITATIVE editable state, so a forged high total loads (matching the existing threat model for forged `deliveries`/`score`) — a conscious decision, not an oversight. MAJOR-6/7/8 (omitted tests, doc scope, content fingerprint) all folded. The core migration mirrors the proven GM-09f v1→v2 pattern (two-phase validate, version-selected exact-key set, the `{V2,V3}` map-identity gate, default-on-`is None`/absence). The blast radius drove the stored-total choice: 17 tests + the carriage rollback assign `num_metros`/`num_carriages`, so they cannot become derived properties. GM-10e (locomotive) opens next — a trivial `num_metros += 1` arm on this infrastructure.
```
