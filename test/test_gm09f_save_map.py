"""GM-09f contract: the save-schema v2 map field (D-038).

A v2 save records the map IDENTITY (`mapId`/`mapDefinitionVersion`) and reconstructs
terrain from the registry on load, so a non-Classic game round-trips. A v1 document
(no map keys) still loads by synthesizing `classic@1`, keeping `save-v1.json` valid.
Serialization + load are fail-closed on TWO axes: the map_definition must EQUAL its
registered definition (a forged/drifted map is rejected), and the state must be LEGAL
under that map (stations on land, crossings within budget). Tunnel counts stay derived.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from maps import CLASSIC, DELTA, LAKE, RIVER, MapDefinition
from mediator import Mediator
from save_game import serialize_game
from save_load import deserialize_game
from save_schema import canonical_save_bytes, validate_save

pygame.init()


def _river_crossing_mediator():
    """A RIVER game with one committed river-crossing line (quiescent, canonical).

    Uses the default single unlocked path -- no override -- so the serialized
    progression invariants (unlockedNumPaths vs purchasedNumPaths) stay consistent.
    """
    m = Mediator(seed=0, map_definition=RIVER)
    # seed=0 RIVER: station 2 = left bank, 0 = right bank -> a crossing line.
    m.create_path_from_station_indices([2, 0])
    return m


def _as_v1(document):
    """A v1 document: drop the v2 map keys AND the v3 tunnelBonus (GM-10h), and set
    schemaVersion 1 (old save shape). A fresh serialize is v3, so all three added keys
    must be stripped or the v1 exact-key set rejects the doc for the wrong reason."""
    v1 = copy.deepcopy(document)
    v1["schemaVersion"] = 1
    del v1["mapId"]
    del v1["mapDefinitionVersion"]
    del v1["tunnelBonus"]
    return v1


class TestGM09fRoundTrip(unittest.TestCase):
    def test_v2_round_trip_preserves_each_map(self):
        for name, map_def in (
            ("classic", CLASSIC),
            ("river", RIVER),
            ("delta", DELTA),
            ("lake", LAKE),
        ):
            document = serialize_game(Mediator(seed=0, map_definition=map_def))
            self.assertEqual(document["schemaVersion"], 3)
            self.assertEqual(document["mapId"], name)
            self.assertEqual(document["mapDefinitionVersion"], 1)
            validate_save(document)
            self.assertEqual(deserialize_game(document).map_definition, map_def)

    def test_default_mediator_serializes_as_classic(self):
        document = serialize_game(Mediator(seed=0))  # no map_definition -> CLASSIC
        self.assertEqual(document["mapId"], "classic")
        self.assertEqual(deserialize_game(document).map_definition, CLASSIC)

    def test_v2_canonical_bytes_are_idempotent(self):
        first = canonical_save_bytes(
            serialize_game(Mediator(seed=0, map_definition=DELTA))
        )
        again = canonical_save_bytes(
            serialize_game(deserialize_game(json.loads(first)))
        )
        self.assertEqual(first, again)


class TestGM09fBackwardCompat(unittest.TestCase):
    def test_a_v1_document_loads_as_classic(self):
        # A v1 save (no map identity) synthesizes classic@1 -- the old load behavior.
        v1 = _as_v1(serialize_game(Mediator(seed=0)))
        validate_save(v1)
        self.assertEqual(deserialize_game(v1).map_definition, CLASSIC)

    def test_v1_document_with_map_keys_is_rejected(self):
        forged = serialize_game(Mediator(seed=0))
        forged["schemaVersion"] = 1  # v1 header, but keeps the v2 map keys
        with self.assertRaises(ValueError):
            validate_save(forged)

    def test_v2_document_without_map_keys_is_rejected(self):
        missing = serialize_game(Mediator(seed=0))
        del missing["mapId"]  # v2 header but missing a required map key
        with self.assertRaises(ValueError):
            validate_save(missing)


class TestGM09fFailClosedLoad(unittest.TestCase):
    def test_load_rejects_an_unknown_map_id(self):
        document = serialize_game(Mediator(seed=0))
        document["mapId"] = "atlantis"
        with self.assertRaisesRegex(ValueError, "atlantis"):
            deserialize_game(document)

    def test_load_rejects_an_unsupported_map_version(self):
        document = serialize_game(Mediator(seed=0))
        document["mapDefinitionVersion"] = 99
        with self.assertRaisesRegex(ValueError, "99"):
            deserialize_game(document)


class TestGM09fMapIdentityShape(unittest.TestCase):
    """`validate_save` pins the v2 `mapId` SHAPE -- a non-empty ASCII string with no
    whitespace, a true mirror of `rl.manifest_schema._validate_map_identity`. Registry
    ids already satisfy this, so these guard only hand-forged documents (review: harness
    + Codex both flagged the missing ASCII/whitespace check against D-038's contract)."""

    def _document_with_map_id(self, map_id):
        document = serialize_game(Mediator(seed=0))
        document["mapId"] = map_id
        return document

    def test_validate_rejects_a_non_ascii_map_id(self):
        with self.assertRaisesRegex(ValueError, "ASCII"):
            validate_save(self._document_with_map_id("rivér"))

    def test_validate_rejects_a_whitespace_bearing_map_id(self):
        with self.assertRaisesRegex(ValueError, "whitespace"):
            validate_save(self._document_with_map_id("river "))

    def test_validate_rejects_an_empty_map_id(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            validate_save(self._document_with_map_id(""))

    def test_validate_rejects_a_non_string_map_id(self):
        with self.assertRaisesRegex(ValueError, "must be a string"):
            validate_save(self._document_with_map_id(123))


class TestGM09fStructuralGuard(unittest.TestCase):
    def _forge(self, map_id, **overrides):
        base = dict(
            map_id=map_id,
            map_definition_version=1,
            shape_types=CLASSIC.shape_types,
            unique_shape_types=CLASSIC.unique_shape_types,
            unique_spawn_start_index=CLASSIC.unique_spawn_start_index,
            unique_spawn_chance=CLASSIC.unique_spawn_chance,
        )
        base.update(overrides)
        return MapDefinition(**base)

    def test_serialize_rejects_a_forged_classic_with_terrain(self):
        # A classic id carrying terrain would persist as classic@1 and reload as the
        # real terrain-free CLASSIC -- the structural guard rejects it.
        m = Mediator(seed=0)
        m.map_definition = self._forge("classic", rivers=((5.0, 0.0, 6.0, 10.0),))
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_forged_river_without_terrain(self):
        # A river id WITHOUT the real river terrain: rejected (would reload as real RIVER).
        m = Mediator(seed=0)
        m.map_definition = self._forge("river")  # no rivers/spawn_regions
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_forged_delta_without_terrain(self):
        # Same guard for the delta id (would reload as the real two-channel DELTA).
        m = Mediator(seed=0)
        m.map_definition = self._forge("delta")  # no channels/spawn_regions
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_forged_lake_without_terrain(self):
        # Same guard for the lake id (would reload as the real bounded-lake LAKE).
        m = Mediator(seed=0)
        m.map_definition = self._forge("lake")  # no lake rect/spawn_regions
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)

    def test_serialize_rejects_a_falsey_map_definition(self):
        # A FALSEY MapDefinition (a subclass whose __bool__ is False) carrying classic@1
        # identity must NOT be silently coerced to CLASSIC by an `or CLASSIC` default:
        # it is not the registered CLASSIC object, so the structural guard rejects it.
        # Regression for the fail-open the `is None` default closes (review Codex).
        class _FalseyMap(MapDefinition):
            def __bool__(self) -> bool:
                return False

        falsey = _FalseyMap(
            **{f.name: getattr(CLASSIC, f.name) for f in dataclasses.fields(CLASSIC)}
        )
        self.assertFalse(bool(falsey))  # the trap: truthiness is False
        self.assertNotEqual(falsey, CLASSIC)  # but it is NOT the registered CLASSIC
        m = Mediator(seed=0)
        m.map_definition = falsey
        with self.assertRaisesRegex(ValueError, "does not match the registered"):
            serialize_game(m)


class TestGM09fStateLegality(unittest.TestCase):
    def test_serialize_rejects_a_state_illegal_under_its_map(self):
        # CLASSIC stations relabeled river@1 sit in the water -> rejected on serialize.
        m = Mediator(seed=0)
        m.map_definition = RIVER
        with self.assertRaisesRegex(ValueError, "not on the map's land"):
            serialize_game(m)

    def test_load_rejects_a_forged_off_land_document(self):
        # A hand-forged v2 doc: a CLASSIC game's state relabeled river@1. It validates
        # structurally but its stations are in the water -> rejected on LOAD.
        document = serialize_game(Mediator(seed=0))
        document["mapId"] = "river"
        validate_save(document)  # schema-valid (well-typed identity)
        with self.assertRaisesRegex(ValueError, "not on the map's land"):
            deserialize_game(document)

    def test_legality_gate_refuses_an_over_budget_reconstruction(self):
        # The creation gate (within_tunnel_budget) means normal play can never build an
        # over-budget state, so this drives the load-side defense-in-depth branch directly
        # (as the impl review verified): consumed crossings above the map budget are
        # refused after reconstruction, a corrupt-doc safety net. RIVER has spawn_regions
        # so the (empty) station pool is scanned first, then the budget check fires.
        from save_load import _require_legal_map_state

        over_budget = SimpleNamespace(
            all_stations=[], num_tunnels=RIVER.tunnel_budget, consumed_tunnels=99
        )
        with self.assertRaisesRegex(ValueError, "exceed the map's tunnel budget"):
            _require_legal_map_state(over_budget, RIVER)


class TestGM09fDerivedTunnelState(unittest.TestCase):
    def test_a_river_crossing_survives_the_round_trip(self):
        # Tunnel counts are DERIVED, not persisted: a saved river-crossing game reloads
        # with the same consumed/available, reconstructed from map_definition + paths.
        mediator = _river_crossing_mediator()
        self.assertEqual(mediator.consumed_tunnels, 1)
        document = serialize_game(mediator)
        loaded = deserialize_game(document)
        self.assertEqual(loaded.map_definition, RIVER)
        self.assertEqual(loaded.consumed_tunnels, 1)
        self.assertEqual(loaded.available_tunnels, 2)


if __name__ == "__main__":
    unittest.main()
