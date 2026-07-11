"""Atomic, hash-bound RL artifact persistence and verification."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from rl.manifest import TrainingManifest

ARTIFACT_INDEX_SCHEMA = "mini-metro-artifacts-v1"


class ArtifactIntegrityError(ValueError):
    """An artifact or its authenticated index does not match the manifest."""


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    """One authenticated artifact captured as immutable bytes."""

    path: Path
    index_path: Path
    indexed_paths: tuple[Path, ...]
    metadata: Mapping[str, Any]
    content: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_artifact_metadata(
    path: str | Path, *, relative_to: str | Path
) -> dict[str, Any]:
    artifact = Path(path)
    root = Path(relative_to)
    return {
        "path": artifact.relative_to(root).as_posix(),
        "sha256": sha256_file(artifact),
        "sizeBytes": artifact.stat().st_size,
    }


def write_json_atomic(path: str | Path, document: Mapping[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def write_artifact_index(
    run_dir: str | Path, destination_name: str = "artifacts.json"
) -> Path:
    """Atomically index every completed run file except manifest metadata itself."""

    root = Path(run_dir)
    destination = root / destination_name
    excluded = {destination.resolve(), (root / "training-manifest.json").resolve()}
    index_history = (root / "artifact-indexes").resolve()
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() not in excluded
        and index_history not in path.resolve().parents
    ]
    document = {
        "schema": ARTIFACT_INDEX_SCHEMA,
        "files": {
            path.relative_to(root).as_posix(): file_artifact_metadata(
                path, relative_to=root
            )
            for path in sorted(files)
        },
    }
    return write_json_atomic(destination, document)


def _read_index(payload: bytes) -> Mapping[str, Any]:
    document = json.loads(payload)
    if not isinstance(document, Mapping):
        raise ArtifactIntegrityError("artifact index must be a JSON object")
    if set(document) != {"schema", "files"}:
        raise ArtifactIntegrityError("artifact index has invalid keys")
    if document["schema"] != ARTIFACT_INDEX_SCHEMA:
        raise ArtifactIntegrityError("artifact index schema mismatch")
    files = document["files"]
    if not isinstance(files, Mapping):
        raise ArtifactIntegrityError("artifact index files must be an object")
    return files


def read_verified_indexed_artifact(
    artifact_path: str | Path,
    *,
    manifest: TrainingManifest,
    manifest_path: str | Path,
) -> VerifiedArtifact:
    """Verify and capture one exact in-run artifact and its index snapshot."""

    manifest_file = Path(manifest_path).resolve()
    run_root = manifest_file.parent
    index_relative = manifest.artifacts.get("artifact_index")
    if index_relative is None:
        raise ArtifactIntegrityError("manifest has no artifact_index path")
    index_path = (run_root / index_relative).resolve()
    try:
        index_path.relative_to(run_root)
    except ValueError as error:
        raise ArtifactIntegrityError(
            "artifact index escapes the run directory"
        ) from error
    if not index_path.is_file():
        raise ArtifactIntegrityError(f"artifact index does not exist: {index_path}")
    index_payload = index_path.read_bytes()
    if hashlib.sha256(index_payload).hexdigest() != manifest.artifact_index_sha256:
        raise ArtifactIntegrityError("artifact index SHA-256 does not match manifest")
    files = _read_index(index_payload)
    indexed_paths: list[Path] = []
    for indexed_relative in files:
        if not isinstance(indexed_relative, str) or not indexed_relative:
            raise ArtifactIntegrityError(
                "artifact index paths must be non-empty strings"
            )
        indexed_path = (run_root / indexed_relative).resolve()
        try:
            indexed_path.relative_to(run_root)
        except ValueError as error:
            raise ArtifactIntegrityError(
                "indexed artifact escapes the run directory"
            ) from error
        indexed_paths.append(indexed_path)

    selected = Path(artifact_path).resolve()
    try:
        relative = selected.relative_to(run_root).as_posix()
    except ValueError as error:
        raise ArtifactIntegrityError(
            "selected artifact is outside the run directory"
        ) from error
    metadata = files.get(relative)
    if not isinstance(metadata, Mapping):
        raise ArtifactIntegrityError(f"artifact is not indexed: {relative}")
    if set(metadata) != {"path", "sha256", "sizeBytes"}:
        raise ArtifactIntegrityError("artifact metadata has invalid keys")
    if metadata["path"] != relative:
        raise ArtifactIntegrityError("artifact metadata path mismatch")
    if not selected.is_file():
        raise ArtifactIntegrityError(f"artifact does not exist: {selected}")
    content = selected.read_bytes()
    if metadata["sizeBytes"] != len(content):
        raise ArtifactIntegrityError("artifact size does not match index")
    if metadata["sha256"] != hashlib.sha256(content).hexdigest():
        raise ArtifactIntegrityError("artifact SHA-256 does not match index")
    return VerifiedArtifact(
        path=selected,
        index_path=index_path,
        indexed_paths=tuple(sorted(indexed_paths)),
        metadata=metadata,
        content=content,
    )


def verify_indexed_artifact(
    artifact_path: str | Path,
    *,
    manifest: TrainingManifest,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Verify an indexed artifact and return its portable metadata."""

    verified = read_verified_indexed_artifact(
        artifact_path,
        manifest=manifest,
        manifest_path=manifest_path,
    )
    return dict(verified.metadata)
