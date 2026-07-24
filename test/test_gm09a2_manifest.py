"""GM-09a2: training-manifest v3 (map identity) + the CLI resume-inherit.

v3 is a v2 superset that adds `mapId`/`mapDefinitionVersion`; v1/v2 stay
map-free and exact-key-valid. The CLI must INHERIT the map identity from a
resumed manifest (never force a --map default), so a genuine pre-map run still
resumes (review MAJOR-1).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl import protocol
from rl.history import contiguous_history
from rl.manifest import create_training_manifest
from rl.manifest_schema import (
    TRAINING_MANIFEST_SCHEMA,
    TRAINING_MANIFEST_SCHEMA_V1,
    TRAINING_MANIFEST_SCHEMA_V3,
    TrainingManifest,
)


def _manifest(*, map_id=None, map_definition_version=None):
    spec = protocol.TaskSpec(
        render_profile="fast",
        fixed_ticks=6,
        reward_mode="deliveries",
        max_episode_steps=4,
        map_id=map_id,
        map_definition_version=map_definition_version,
    )
    return create_training_manifest(
        protocol_fingerprint=protocol.protocol_fingerprint(),
        task_fingerprint=spec.fingerprint(),
        content_fingerprint="a" * 64,
        training_fingerprint="b" * 64,
        algorithm="recurrent_ppo",
        status="complete",
        render_profile="fast",
        fixed_ticks=6,
        reward_mode="deliveries",
        max_episode_steps=4,
        history=contiguous_history(8),
        seed=42,
        n_envs=2,
        timesteps=256,
        hyperparameters={},
        command=["python"],
        artifacts={"artifact_index": "i.json"},
        artifact_index_sha256="c" * 64,
        map_id=map_id,
        map_definition_version=map_definition_version,
    )


class TestGM09a2ManifestV3(unittest.TestCase):
    def test_map_bound_manifest_is_v3_and_round_trips(self):
        manifest = _manifest(map_id="classic", map_definition_version=1)
        self.assertEqual(manifest.schema, TRAINING_MANIFEST_SCHEMA_V3)
        document = manifest.to_dict()
        self.assertEqual(document["mapId"], "classic")
        self.assertEqual(document["mapDefinitionVersion"], 1)
        self.assertIn("history", document, "v3 keeps the v2 history block")
        restored = TrainingManifest.from_dict(document)
        self.assertEqual(restored.schema, TRAINING_MANIFEST_SCHEMA_V3)
        self.assertEqual(restored.map_id, "classic")
        self.assertEqual(restored.map_definition_version, 1)

    def test_map_free_manifest_is_v2_without_map_keys(self):
        manifest = _manifest()
        self.assertEqual(manifest.schema, TRAINING_MANIFEST_SCHEMA)
        document = manifest.to_dict()
        self.assertNotIn("mapId", document)
        self.assertNotIn("mapDefinitionVersion", document)

    def test_v2_document_with_map_keys_is_rejected(self):
        document = _manifest().to_dict()
        document["mapId"] = "classic"
        document["mapDefinitionVersion"] = 1
        with self.assertRaises(ValueError):
            TrainingManifest.from_dict(document)  # unknown keys for v2

    def test_v3_document_without_map_keys_is_rejected(self):
        document = _manifest(map_id="classic", map_definition_version=1).to_dict()
        del document["mapId"]
        with self.assertRaises(ValueError):
            TrainingManifest.from_dict(document)  # missing keys for v3

    def test_post_init_keeps_schema_and_map_in_lockstep(self):
        base = _manifest()
        # v1/v2 must not carry map identity.
        with self.assertRaises(ValueError):
            TrainingManifest.from_dict(
                {**base.to_dict(), "schema": TRAINING_MANIFEST_SCHEMA_V1}
            )
        # A v3 object built without map identity is rejected at construction.
        bound = _manifest(map_id="classic", map_definition_version=1)
        with self.assertRaises(ValueError):
            TrainingManifest(
                **{
                    **_dataclass_kwargs(bound),
                    "map_id": None,
                    "map_definition_version": None,
                }
            )


def _dataclass_kwargs(manifest):
    from dataclasses import fields

    return {f.name: getattr(manifest, f.name) for f in fields(manifest)}


def _load_train_module():
    path = os.path.dirname(os.path.realpath(__file__)) + "/../scripts/train_rl.py"
    spec = importlib.util.spec_from_file_location("train_rl_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestGM09a2FactoryIntegrity(unittest.TestCase):
    """Review Codex-1/2: the factory must not mint a contradictory or
    unsupported-map manifest that only fails later, possibly in a worker."""

    def _base_kwargs(self, **overrides):
        kwargs = dict(
            protocol_fingerprint=protocol.protocol_fingerprint(),
            content_fingerprint="a" * 64,
            training_fingerprint="b" * 64,
            algorithm="recurrent_ppo",
            status="complete",
            render_profile="fast",
            fixed_ticks=6,
            reward_mode="deliveries",
            max_episode_steps=4,
            history=contiguous_history(8),
            seed=42,
            n_envs=2,
            timesteps=256,
            hyperparameters={},
            command=["python"],
            artifacts={"artifact_index": "i.json"},
            artifact_index_sha256="c" * 64,
        )
        kwargs.update(overrides)
        return kwargs

    def test_reconstruction_rejects_a_contradictory_task_fingerprint(self):
        # The manifest record is decoupled from the RL protocol (the factory
        # trusts the caller-computed fingerprint, as always), but a contradiction
        # — a v3 classic@1 manifest carrying the LEGACY map-free fingerprint —
        # fails closed on the read path before the task is ever used.
        from rl.training import task_spec_from_manifest

        legacy_fp = protocol.TaskSpec(
            render_profile="fast",
            fixed_ticks=6,
            reward_mode="deliveries",
            max_episode_steps=4,
        ).fingerprint()
        manifest = create_training_manifest(
            **self._base_kwargs(
                task_fingerprint=legacy_fp,
                map_id="classic",
                map_definition_version=1,
            )
        )
        with self.assertRaises(Exception):
            task_spec_from_manifest(manifest)

    def test_factory_rejects_an_unsupported_map_version(self):
        spec2 = protocol.TaskSpec(
            render_profile="fast",
            fixed_ticks=6,
            reward_mode="deliveries",
            max_episode_steps=4,
            map_id="classic",
            map_definition_version=2,
        )
        with self.assertRaises(ValueError):
            create_training_manifest(
                **self._base_kwargs(
                    task_fingerprint=spec2.fingerprint(),
                    map_id="classic",
                    map_definition_version=2,
                )
            )

    def test_reconstruction_rejects_an_unsupported_map_version(self):
        # Bypass the factory: a self-consistent classic@2 document parses, but
        # task_spec_from_manifest must reject the unsupported map at read time.
        from rl.training import task_spec_from_manifest

        document = _manifest(map_id="classic", map_definition_version=1).to_dict()
        document["mapDefinitionVersion"] = 2
        document["taskFingerprint"] = protocol.TaskSpec(
            render_profile="fast",
            fixed_ticks=6,
            reward_mode="deliveries",
            max_episode_steps=4,
            map_id="classic",
            map_definition_version=2,
        ).fingerprint()
        manifest = TrainingManifest.from_dict(document)  # self-consistent, parses
        with self.assertRaises(Exception):
            task_spec_from_manifest(manifest)  # resolve_map rejects classic@2


class TestGM09a2CliResumeInherit(unittest.TestCase):
    def setUp(self):
        self.train = _load_train_module()

    def test_fresh_omitted_map_is_map_free(self):
        self.assertEqual(self.train._resolve_map_identity(None, None), (None, None))

    def test_fresh_named_map_binds_to_current_version(self):
        self.assertEqual(
            self.train._resolve_map_identity("classic", None), ("classic", 1)
        )

    def test_resume_inherits_legacy_map_absence(self):
        # A resumed pre-map manifest -> map-less, so its legacy hash still matches
        # (review MAJOR-1). getattr keeps a manifest without map fields legacy.
        legacy = _manifest()  # v2, map-free
        self.assertEqual(self.train._resolve_map_identity(None, legacy), (None, None))

    def test_resume_inherits_v3_map(self):
        bound = _manifest(map_id="classic", map_definition_version=1)
        self.assertEqual(self.train._resolve_map_identity(None, bound), ("classic", 1))

    def test_resume_with_conflicting_explicit_map_is_rejected(self):
        legacy = _manifest()
        with self.assertRaises(ValueError):
            self.train._resolve_map_identity("classic", legacy)


if __name__ == "__main__":
    unittest.main()
