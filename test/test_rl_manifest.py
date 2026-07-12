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

from rl.history import (
    DECISION_HISTORY_LAYOUT,
    contiguous_history,
    history_for_layout,
)
from rl.manifest import (
    CROSS_CONTENT_TAG,
    CROSS_RUNTIME_TAG,
    CROSS_TRAINING_TAG,
    TRAINING_MANIFEST_SCHEMA,
    TRAINING_MANIFEST_SCHEMA_V1,
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
        "history": contiguous_history(4),
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


LEGACY_V1_MANIFEST_BYTES = (
    b'{"algorithm":"ppo","artifactIndexSha256":'
    b'"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    b'"artifacts":{"final_model":"models/final.zip",'
    b'"tensorboard":"tensorboard/"},"command":["python",'
    b'"scripts/train_rl.py","--seed","42"],"contentFingerprint":"content-a",'
    b'"fixedTicks":6,"frameStack":4,"hyperparameters":{"batch_size":256,'
    b'"schedule":{"milestones":[0.5,0.25],"name":"linear"}},'
    b'"maxEpisodeSteps":36000,"nEnvs":8,"parentManifestSha256":null,'
    b'"parentModelSha256":null,"protocolFingerprint":"protocol-a",'
    b'"renderProfile":"player-rgb-320x180-v1",'
    b'"rewardMode":"score-delta-v1","runtime":{"packageVersions":'
    b'{"gymnasium":null,"stable-baselines3":"2.9.0"},'
    b'"platform":"Windows-test","pythonVersion":"3.13.10"},'
    b'"schema":"mini-metro-training-manifest-v1","seed":42,"source":'
    b'{"dirtyPaths":["a.py","z.py"],"gitRevision":"abc123"},'
    b'"status":"complete","tags":[],"taskFingerprint":"task-a",'
    b'"timesteps":1000000,"trainingFingerprint":"training-a"}\n'
)


class TestTrainingManifest(unittest.TestCase):
    def test_creation_freezes_nested_data_and_sorts_source_paths(self):
        manifest = make_manifest()

        self.assertEqual(manifest.schema, TRAINING_MANIFEST_SCHEMA)
        self.assertEqual(manifest.status, "complete")
        self.assertEqual(manifest.fixed_ticks, 6)
        self.assertEqual(manifest.max_episode_steps, 36_000)
        self.assertEqual(manifest.frame_stack, 4)
        self.assertEqual(manifest.history, contiguous_history(4))
        self.assertEqual(manifest.history_fingerprint, manifest.history.fingerprint())
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

    def test_factory_derives_history_summary_and_rejects_old_dual_source(self):
        manifest = make_manifest(history=history_for_layout(DECISION_HISTORY_LAYOUT))

        self.assertEqual(manifest.frame_stack, 12)
        self.assertEqual(
            manifest.history_fingerprint,
            history_for_layout(DECISION_HISTORY_LAYOUT).fingerprint(),
        )
        with self.assertRaises(TypeError):
            make_manifest(frame_stack=12)


class TestManifestPersistence(unittest.TestCase):
    def test_v2_requires_exact_authenticated_history(self):
        manifest = make_manifest()
        document = manifest.to_dict()
        self.assertEqual(document["schema"], TRAINING_MANIFEST_SCHEMA)
        self.assertEqual(document["frameStack"], 4)
        self.assertEqual(document["history"], contiguous_history(4).to_dict())
        self.assertEqual(
            document["historyFingerprint"], contiguous_history(4).fingerprint()
        )

        malformed = []
        wrong_digest = dict(document)
        wrong_digest["historyFingerprint"] = "b" * 64
        malformed.append(wrong_digest)
        short_digest = dict(document)
        short_digest["historyFingerprint"] = "not-a-sha256"
        malformed.append(short_digest)
        uppercase_digest = dict(document)
        uppercase_digest["historyFingerprint"] = "A" * 64
        malformed.append(uppercase_digest)
        missing_top_level = dict(document)
        missing_top_level.pop("history")
        malformed.append(missing_top_level)
        unknown_top_level = dict(document)
        unknown_top_level["future"] = True
        malformed.append(unknown_top_level)
        wrong_stack = dict(document)
        wrong_stack["frameStack"] = 8
        malformed.append(wrong_stack)
        wrong_semantics = dict(document)
        wrong_semantics["history"] = {
            **document["history"],
            "sampleOrder": "newest-to-oldest",
        }
        malformed.append(wrong_semantics)
        unknown_nested = dict(document)
        unknown_nested["history"] = {**document["history"], "future": True}
        malformed.append(unknown_nested)

        for candidate in malformed:
            with self.subTest(candidate=candidate):
                payload = json.dumps(candidate).encode("utf-8")
                with self.assertRaises((TypeError, ValueError)):
                    read_training_manifest_bytes(payload)

    def test_literal_v1_bytes_round_trip_and_normalize_arbitrary_stacks(self):
        legacy = read_training_manifest_bytes(LEGACY_V1_MANIFEST_BYTES)

        self.assertEqual(legacy.schema, TRAINING_MANIFEST_SCHEMA_V1)
        self.assertEqual(legacy.frame_stack, 4)
        self.assertEqual(legacy.history, contiguous_history(4))
        self.assertEqual(legacy.history_fingerprint, legacy.history.fingerprint())
        self.assertEqual(canonical_json_bytes(legacy), LEGACY_V1_MANIFEST_BYTES)
        self.assertEqual(
            sha256_hex(canonical_json_bytes(legacy)),
            sha256_hex(LEGACY_V1_MANIFEST_BYTES),
        )

        for frame_stack in (1, 4, 8, 13):
            with self.subTest(frame_stack=frame_stack):
                document = json.loads(LEGACY_V1_MANIFEST_BYTES)
                document["frameStack"] = frame_stack
                parsed = read_training_manifest_bytes(json.dumps(document).encode())
                self.assertEqual(parsed.history, contiguous_history(frame_stack))

        injected = json.loads(LEGACY_V1_MANIFEST_BYTES)
        injected["history"] = contiguous_history(4).to_dict()
        injected["historyFingerprint"] = contiguous_history(4).fingerprint()
        with self.assertRaises(ValueError):
            read_training_manifest_bytes(json.dumps(injected).encode())

    def test_history_compatibility_is_separate_from_task_identity(self):
        manifest = make_manifest(history=contiguous_history(12))
        multiscale = history_for_layout(DECISION_HISTORY_LAYOUT)
        self.assertEqual(manifest.frame_stack, multiscale.frame_stack)

        with self.assertRaisesRegex(ManifestCompatibilityError, "history"):
            validate_training_manifest(
                manifest,
                expected_protocol_fingerprint="protocol-a",
                expected_task_fingerprint="task-a",
                expected_history_fingerprint=multiscale.fingerprint(),
            )
        validated = validate_training_manifest(
            manifest,
            expected_protocol_fingerprint="protocol-a",
            expected_task_fingerprint="task-a",
            expected_history_fingerprint=contiguous_history(12).fingerprint(),
        )
        self.assertEqual(validated.task_fingerprint, "task-a")

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
