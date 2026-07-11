from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.artifacts import (
    ArtifactIntegrityError,
    read_verified_indexed_artifact,
    sha256_file,
    verify_indexed_artifact,
    write_artifact_index,
)
from test.test_rl_manifest import make_manifest


class TestArtifactIntegrity(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run_dir = Path(self.temporary.name) / "run"
        self.run_dir.mkdir()
        self.model = self.run_dir / "checkpoint.zip"
        self.model.write_bytes(b"model-v1")
        self.index = write_artifact_index(self.run_dir)
        self.manifest = make_manifest(
            artifacts={"artifact_index": "artifacts.json"},
            artifact_index_sha256=sha256_file(self.index),
        )
        self.manifest_path = self.run_dir / "training-manifest.json"

    def test_verifies_exact_indexed_model_bytes(self) -> None:
        metadata = verify_indexed_artifact(
            self.model,
            manifest=self.manifest,
            manifest_path=self.manifest_path,
        )

        self.assertEqual(metadata["path"], "checkpoint.zip")
        self.assertEqual(metadata["sha256"], sha256_file(self.model))

        verified = read_verified_indexed_artifact(
            self.model,
            manifest=self.manifest,
            manifest_path=self.manifest_path,
        )
        self.assertEqual(verified.metadata, metadata)
        self.assertEqual(verified.content, b"model-v1")
        self.assertEqual(verified.path, self.model.resolve())
        self.assertEqual(verified.index_path, self.index.resolve())
        self.assertEqual(verified.indexed_paths, (self.model.resolve(),))

        self.model.write_bytes(b"model-v2")
        self.assertEqual(verified.content, b"model-v1")

    def test_hashes_and_parses_one_exact_index_snapshot(self) -> None:
        original_read_bytes = Path.read_bytes
        reads: dict[Path, int] = {}

        def tracked_read_bytes(path: Path) -> bytes:
            resolved = path.resolve()
            reads[resolved] = reads.get(resolved, 0) + 1
            if resolved == self.index.resolve() and reads[resolved] > 1:
                return b"{}\n"
            return original_read_bytes(path)

        with patch.object(Path, "read_bytes", tracked_read_bytes):
            verified = read_verified_indexed_artifact(
                self.model,
                manifest=self.manifest,
                manifest_path=self.manifest_path,
            )

        self.assertEqual(verified.content, b"model-v1")
        self.assertEqual(reads[self.index.resolve()], 1)
        self.assertEqual(reads[self.model.resolve()], 1)

    def test_rejects_tampered_model_or_index(self) -> None:
        self.model.write_bytes(b"model-v2")
        with self.assertRaises(ArtifactIntegrityError):
            verify_indexed_artifact(
                self.model,
                manifest=self.manifest,
                manifest_path=self.manifest_path,
            )

        self.model.write_bytes(b"model-v1")
        self.index.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ArtifactIntegrityError, "index SHA-256"):
            verify_indexed_artifact(
                self.model,
                manifest=self.manifest,
                manifest_path=self.manifest_path,
            )

    def test_rejects_model_outside_authenticated_run(self) -> None:
        outside = self.run_dir.parent / "outside.zip"
        outside.write_bytes(b"model-v1")

        with self.assertRaisesRegex(ArtifactIntegrityError, "outside"):
            verify_indexed_artifact(
                outside,
                manifest=self.manifest,
                manifest_path=self.manifest_path,
            )

    def test_new_versioned_index_does_not_invalidate_last_manifest(self) -> None:
        first_index = write_artifact_index(self.run_dir, "artifact-indexes/0-0.json")
        old_manifest = make_manifest(
            artifacts={"artifact_index": "artifact-indexes/0-0.json"},
            artifact_index_sha256=sha256_file(first_index),
        )

        self.model.write_bytes(b"model-v2")
        write_artifact_index(self.run_dir, "artifact-indexes/10-1.json")

        self.model.write_bytes(b"model-v1")
        metadata = verify_indexed_artifact(
            self.model,
            manifest=old_manifest,
            manifest_path=self.manifest_path,
        )
        self.assertEqual(metadata["sha256"], sha256_file(self.model))


if __name__ == "__main__":
    unittest.main()
