"""GM-09a2 red contract: versioned task-descriptor identity (D-033).

The load-bearing invariant: a map-ABSENT `TaskSpec` descriptor is BYTE-IDENTICAL
to the pre-map code (so every genuine pre-map manifest keeps its exact
fingerprint), while a map-BOUND spec gains `mapId`/`mapDefinitionVersion` +
`descriptorVersion:2` and a distinct fingerprint. Presence of the map keys IS the
version signal — no key is added to the legacy descriptor. The committed real
legacy manifest fixture reconstructs to its exact hash through the CLI path.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl import protocol
from rl.manifest_schema import TrainingManifest
from rl.training import task_spec_from_manifest

_LEGACY_FINGERPRINT = "c2ef342f9cedfc3b7292ec2517ec7ccca7b2dcf9b49811c6dec529c25e73933e"
_LEGACY_KEYS = frozenset(
    {
        "protocol_id",
        "protocol_version",
        "protocol_fingerprint",
        "render_profile",
        "fixed_ticks",
        "reward_mode",
        "action_space",
        "observation_space",
        "episode",
    }
)
_FIXTURE = (
    os.path.dirname(os.path.realpath(__file__))
    + "/../scripts/fixtures/legacy-training-manifest-v1.json"
)


def _ref_spec(**overrides):
    params = dict(
        render_profile="fast",
        fixed_ticks=6,
        reward_mode="deliveries",
        max_episode_steps=4,
    )
    params.update(overrides)
    return protocol.TaskSpec(**params)


class TestGM09a2LegacyByteCompat(unittest.TestCase):
    def test_map_absent_descriptor_is_byte_identical_and_keeps_the_legacy_hash(self):
        spec = _ref_spec()  # no map fields -> legacy
        descriptor = protocol.task_descriptor(spec)
        self.assertEqual(
            frozenset(descriptor), _LEGACY_KEYS, "a map-absent descriptor adds no keys"
        )
        self.assertEqual(
            protocol.task_fingerprint(spec),
            _LEGACY_FINGERPRINT,
            "the map-absent reference spec must keep its exact pre-map fingerprint",
        )

    def test_bare_taskspec_is_map_absent(self):
        spec = protocol.TaskSpec()
        self.assertIsNone(spec.map_id)
        self.assertNotIn("mapId", protocol.task_descriptor(spec))

    def test_real_legacy_manifest_reconstructs_to_its_exact_hash(self):
        # Codex-2: the real fixture lives in git-ignored /output/; a sanitized copy
        # is committed so CI can run the highest-risk regression.
        with open(_FIXTURE, encoding="utf-8") as handle:
            raw = json.load(handle)
        self.assertEqual(raw["schema"], "mini-metro-training-manifest-v1")
        self.assertEqual(raw["taskFingerprint"], _LEGACY_FINGERPRINT)
        manifest = TrainingManifest.from_dict(raw)
        spec = task_spec_from_manifest(manifest)
        self.assertIsNone(spec.map_id, "a v1 manifest reconstructs a map-LESS spec")
        self.assertEqual(
            spec.fingerprint(),
            _LEGACY_FINGERPRINT,
            "a genuine pre-map manifest must still reconstruct its exact hash",
        )


class TestGM09a2MapBoundDescriptor(unittest.TestCase):
    def test_map_bound_descriptor_adds_the_keys_and_a_version(self):
        descriptor = protocol.task_descriptor(
            _ref_spec(map_id="classic", map_definition_version=1)
        )
        self.assertEqual(descriptor["mapId"], "classic")
        self.assertEqual(descriptor["mapDefinitionVersion"], 1)
        self.assertEqual(
            descriptor["descriptorVersion"], 2, "map-bound is descriptor v2"
        )

    def test_map_bound_fingerprint_differs_from_legacy(self):
        legacy = protocol.task_fingerprint(_ref_spec())
        bound = protocol.task_fingerprint(
            _ref_spec(map_id="classic", map_definition_version=1)
        )
        self.assertNotEqual(bound, legacy)

    def test_map_id_and_version_are_part_of_identity(self):
        a = protocol.task_fingerprint(
            _ref_spec(map_id="classic", map_definition_version=1)
        )
        b = protocol.task_fingerprint(
            _ref_spec(map_id="river", map_definition_version=1)
        )
        c = protocol.task_fingerprint(
            _ref_spec(map_id="classic", map_definition_version=2)
        )
        self.assertNotEqual(a, b, "the map id is part of identity")
        self.assertNotEqual(a, c, "the map version is part of identity")


class TestGM09a2TaskSpecInvariants(unittest.TestCase):
    def test_both_none_is_legacy_ok(self):
        spec = _ref_spec()
        self.assertIsNone(spec.map_id)
        self.assertIsNone(spec.map_definition_version)

    def test_partial_map_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            _ref_spec(map_id="classic")
        with self.assertRaises(ValueError):
            _ref_spec(map_definition_version=1)

    def test_empty_or_non_ascii_map_id_is_rejected(self):
        with self.assertRaises(ValueError):
            _ref_spec(map_id="", map_definition_version=1)
        with self.assertRaises(ValueError):
            _ref_spec(map_id="rivière", map_definition_version=1)

    def test_non_positive_or_bool_version_is_rejected(self):
        with self.assertRaises(ValueError):
            _ref_spec(map_id="classic", map_definition_version=0)
        with self.assertRaises(ValueError):
            _ref_spec(map_id="classic", map_definition_version=True)

    def test_whitespace_map_id_is_rejected(self):
        # Defense-in-depth (review harness NIT): a map id is an identifier slug.
        for bad in (" ", "\t", "a b", "classic\n"):
            with self.assertRaises(ValueError):
                _ref_spec(map_id=bad, map_definition_version=1)


if __name__ == "__main__":
    unittest.main()
