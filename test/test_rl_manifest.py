import json
import os
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from importlib import metadata
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.manifest import (
    CROSS_CONTENT_TAG,
    CROSS_RUNTIME_TAG,
    CROSS_TRAINING_TAG,
    TRAINING_MANIFEST_SCHEMA,
    ManifestCompatibilityError,
    RuntimeSnapshot,
    SourceSnapshot,
    canonical_json_bytes,
    collect_runtime_snapshot,
    collect_source_snapshot,
    create_training_manifest,
    load_training_manifest,
    read_training_manifest_bytes,
    runtime_compatibility_differences,
    sha256_hex,
    validate_training_manifest,
    write_training_manifest,
)
from rl.provenance import COMPATIBILITY_PACKAGE_NAMES, DEFAULT_PACKAGE_NAMES


def make_manifest(**overrides):
    values = {
        "protocol_fingerprint": "protocol-a",
        "task_fingerprint": "task-a",
        "content_fingerprint": "content-a",
        "training_fingerprint": "training-a",
        "algorithm": "ppo",
        "status": "complete",
        "render_profile": "player-rgb-320x180-v1",
        "fixed_ticks": 6,
        "reward_mode": "score-delta-v1",
        "max_episode_steps": 36_000,
        "frame_stack": 4,
        "seed": 42,
        "n_envs": 8,
        "timesteps": 1_000_000,
        "hyperparameters": {
            "batch_size": 256,
            "schedule": {"name": "linear", "milestones": [0.5, 0.25]},
        },
        "runtime": RuntimeSnapshot(
            python_version="3.13.10",
            platform_name="Windows-test",
            package_versions={"gymnasium": None, "stable-baselines3": "2.9.0"},
        ),
        "source": SourceSnapshot(
            git_revision="abc123", dirty_paths=("z.py", "a.py", "a.py")
        ),
        "command": ["python", "scripts/train_rl.py", "--seed", "42"],
        "artifacts": {
            "final_model": "models/final.zip",
            "tensorboard": "tensorboard/",
        },
        "artifact_index_sha256": "a" * 64,
    }
    values.update(overrides)
    return create_training_manifest(**values)


class TestTrainingManifest(unittest.TestCase):
    def test_creation_freezes_nested_data_and_sorts_source_paths(self):
        manifest = make_manifest()

        self.assertEqual(manifest.schema, TRAINING_MANIFEST_SCHEMA)
        self.assertEqual(manifest.status, "complete")
        self.assertEqual(manifest.fixed_ticks, 6)
        self.assertEqual(manifest.max_episode_steps, 36_000)
        self.assertEqual(manifest.training_fingerprint, "training-a")
        self.assertEqual(manifest.artifact_index_sha256, "a" * 64)
        self.assertEqual(manifest.source.dirty_paths, ("a.py", "z.py"))
        self.assertEqual(
            manifest.hyperparameters["schedule"]["milestones"], (0.5, 0.25)
        )
        with self.assertRaises(TypeError):
            manifest.hyperparameters["batch_size"] = 64
        with self.assertRaises(TypeError):
            manifest.runtime.package_versions["gymnasium"] = "1.3.0"
        with self.assertRaises(FrozenInstanceError):
            manifest.seed = 7

    def test_runtime_collection_records_missing_packages(self):
        def package_version(name):
            if name == "present":
                return "1.2.3"
            raise metadata.PackageNotFoundError(name)

        with patch("rl.provenance.metadata.version", side_effect=package_version):
            runtime = collect_runtime_snapshot(("missing", "present"))

        self.assertEqual(
            dict(runtime.package_versions), {"missing": None, "present": "1.2.3"}
        )
        self.assertTrue(runtime.python_version)
        self.assertTrue(runtime.platform_name)

    def test_runtime_contract_tracks_gameplay_geometry_and_ids(self):
        self.assertIn("shapely", DEFAULT_PACKAGE_NAMES)
        self.assertIn("shortuuid", DEFAULT_PACKAGE_NAMES)
        self.assertIn("sb3-contrib", DEFAULT_PACKAGE_NAMES)
        self.assertIn("shapely", COMPATIBILITY_PACKAGE_NAMES)
        self.assertIn("shortuuid", COMPATIBILITY_PACKAGE_NAMES)
        self.assertIn("sb3-contrib", COMPATIBILITY_PACKAGE_NAMES)

        saved = RuntimeSnapshot(
            "3.13.10",
            "Windows-test",
            {"shapely": "2.1.1", "shortuuid": "1.0.12"},
        )
        current = RuntimeSnapshot(
            "3.13.10",
            "Windows-test",
            {"shapely": "2.1.2", "shortuuid": "1.0.13"},
        )
        self.assertEqual(
            runtime_compatibility_differences(saved, current),
            (
                "shapely saved='2.1.1' current='2.1.2'",
                "shortuuid saved='1.0.12' current='1.0.13'",
            ),
        )

    def test_runtime_contract_detects_recurrent_policy_dependency_drift(self):
        saved = RuntimeSnapshot(
            "3.13.10",
            "Windows-test",
            {"sb3-contrib": "2.7.0"},
        )
        current = RuntimeSnapshot(
            "3.13.10",
            "Windows-test",
            {"sb3-contrib": "2.8.0"},
        )

        self.assertEqual(
            runtime_compatibility_differences(saved, current),
            ("sb3-contrib saved='2.7.0' current='2.8.0'",),
        )

    def test_source_collection_records_revision_and_sorted_dirty_paths(self):
        status = "?? z.py\0 M a.py\0R  renamed.py\0old.py\0"
        with patch("rl.provenance._git_output", side_effect=["abc123\n", status]):
            source = collect_source_snapshot("repo")

        self.assertEqual(source.git_revision, "abc123")
        self.assertEqual(source.dirty_paths, ("a.py", "old.py", "renamed.py", "z.py"))

    def test_rejects_noncanonical_hyperparameters(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            make_manifest(hyperparameters={"learning_rate": float("nan")})

    def test_rejects_invalid_episode_horizon(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    make_manifest(max_episode_steps=value)

    def test_rejects_invalid_artifact_and_parent_hashes(self):
        for field in (
            "artifact_index_sha256",
            "parent_manifest_sha256",
            "parent_model_sha256",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    make_manifest(**{field: "not-a-sha256"})

        resumed = make_manifest(
            parent_manifest_sha256="b" * 64,
            parent_model_sha256="c" * 64,
        )
        self.assertEqual(resumed.parent_manifest_sha256, "b" * 64)
        self.assertEqual(resumed.parent_model_sha256, "c" * 64)

    def test_rejects_unknown_run_status(self):
        with self.assertRaisesRegex(ValueError, "status"):
            make_manifest(status="finished")


class TestManifestPersistence(unittest.TestCase):
    def test_exact_manifest_bytes_are_parsed_and_validated_once(self):
        manifest = make_manifest()
        payload = canonical_json_bytes(manifest)

        parsed = read_training_manifest_bytes(payload)
        validated = validate_training_manifest(
            parsed,
            expected_protocol_fingerprint="protocol-a",
            expected_task_fingerprint="task-a",
            expected_content_fingerprint="content-a",
        )

        self.assertEqual(validated, manifest)
        self.assertEqual(sha256_hex(payload), sha256_hex(canonical_json_bytes(parsed)))

    def test_atomic_writer_emits_stable_canonical_json(self):
        manifest = make_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run"
            path = write_training_manifest(run_dir, manifest)
            first = path.read_bytes()
            write_training_manifest(run_dir, manifest)

            self.assertEqual(path.name, "training-manifest.json")
            self.assertEqual(first, path.read_bytes())
            self.assertTrue(first.endswith(b"\n"))
            self.assertEqual(json.loads(first), manifest.to_dict())
            self.assertEqual(list(run_dir.glob("*.tmp")), [])

    def test_loader_enforces_protocol_task_and_content_compatibility(self):
        manifest = make_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_training_manifest(temp_dir, manifest)

            with self.assertRaisesRegex(ManifestCompatibilityError, "protocol"):
                load_training_manifest(
                    path,
                    expected_protocol_fingerprint="protocol-b",
                    expected_task_fingerprint="task-a",
                    expected_content_fingerprint="content-a",
                    allow_content_drift=True,
                )
            with self.assertRaisesRegex(ManifestCompatibilityError, "task"):
                load_training_manifest(
                    path,
                    expected_protocol_fingerprint="protocol-a",
                    expected_task_fingerprint="task-b",
                    expected_content_fingerprint="content-a",
                )
            with self.assertRaisesRegex(ManifestCompatibilityError, "content"):
                load_training_manifest(
                    path,
                    expected_protocol_fingerprint="protocol-a",
                    expected_task_fingerprint="task-a",
                    expected_content_fingerprint="content-b",
                )

            loaded = load_training_manifest(
                path,
                expected_protocol_fingerprint="protocol-a",
                expected_task_fingerprint="task-a",
                expected_content_fingerprint="content-b",
                allow_content_drift=True,
            )

        self.assertIn(CROSS_CONTENT_TAG, loaded.tags)
        self.assertEqual(loaded.content_fingerprint, "content-a")
        self.assertNotIn(CROSS_CONTENT_TAG, manifest.tags)

    def test_loader_requires_explicit_training_and_runtime_drift(self):
        manifest = make_manifest()
        current_runtime = RuntimeSnapshot(
            python_version="3.13.11",
            platform_name="another-platform",
            package_versions={"gymnasium": "1.3.0", "stable-baselines3": "2.9.0"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_training_manifest(temp_dir, manifest)
            with self.assertRaisesRegex(ManifestCompatibilityError, "training"):
                load_training_manifest(
                    path,
                    expected_protocol_fingerprint="protocol-a",
                    expected_task_fingerprint="task-a",
                    expected_training_fingerprint="training-b",
                )
            with self.assertRaisesRegex(ManifestCompatibilityError, "runtime"):
                load_training_manifest(
                    path,
                    expected_protocol_fingerprint="protocol-a",
                    expected_task_fingerprint="task-a",
                    expected_runtime=current_runtime,
                )
            loaded = load_training_manifest(
                path,
                expected_protocol_fingerprint="protocol-a",
                expected_task_fingerprint="task-a",
                expected_training_fingerprint="training-b",
                allow_training_drift=True,
                expected_runtime=current_runtime,
                allow_runtime_drift=True,
            )

        self.assertIn(CROSS_TRAINING_TAG, loaded.tags)
        self.assertIn(CROSS_RUNTIME_TAG, loaded.tags)
        self.assertEqual(
            runtime_compatibility_differences(manifest.runtime, current_runtime),
            (
                "platform saved='Windows-test' current='another-platform'",
                "gymnasium saved=None current='1.3.0'",
            ),
        )

    def test_sha256_accepts_text_and_bytes(self):
        expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        self.assertEqual(sha256_hex("abc"), expected)
        self.assertEqual(sha256_hex(b"abc"), expected)


if __name__ == "__main__":
    unittest.main()
