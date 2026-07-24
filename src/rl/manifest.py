"""Atomic provenance persistence and compatibility for RL artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from maps import resolve_map
from rl.history import HistoryDescriptor
from rl.manifest_schema import (
    SUPPORTED_TRAINING_MANIFEST_SCHEMAS,
    TRAINING_MANIFEST_SCHEMA,
    TRAINING_MANIFEST_SCHEMA_V1,
    TRAINING_MANIFEST_SCHEMA_V3,
    TrainingManifest,
)
from rl.provenance import (
    DEFAULT_PACKAGE_NAMES,
    RuntimeSnapshot,
    SourceSnapshot,
    collect_runtime_snapshot,
    collect_source_snapshot,
    runtime_compatibility_differences,
)

CROSS_CONTENT_TAG = "cross-content-evaluation"
CROSS_RUNTIME_TAG = "cross-runtime-evaluation"
CROSS_TRAINING_TAG = "cross-training-implementation"

__all__ = (
    "CROSS_CONTENT_TAG",
    "CROSS_RUNTIME_TAG",
    "CROSS_TRAINING_TAG",
    "ManifestCompatibilityError",
    "SUPPORTED_TRAINING_MANIFEST_SCHEMAS",
    "TRAINING_MANIFEST_SCHEMA",
    "TRAINING_MANIFEST_SCHEMA_V1",
    "TrainingManifest",
    "canonical_json_bytes",
    "collect_runtime_snapshot",
    "collect_source_snapshot",
    "create_training_manifest",
    "load_training_manifest",
    "read_training_manifest",
    "read_training_manifest_bytes",
    "runtime_compatibility_differences",
    "sha256_hex",
    "validate_training_manifest",
    "write_training_manifest",
)


class ManifestCompatibilityError(ValueError):
    """A saved training run cannot be used with the requested environment."""


def create_training_manifest(
    *,
    protocol_fingerprint: str,
    task_fingerprint: str,
    content_fingerprint: str,
    training_fingerprint: str,
    algorithm: str,
    status: str,
    render_profile: str,
    fixed_ticks: int,
    reward_mode: str,
    max_episode_steps: int,
    history: HistoryDescriptor,
    seed: int,
    n_envs: int,
    timesteps: int,
    hyperparameters: Mapping[str, Any],
    command: Sequence[str],
    artifacts: Mapping[str, str],
    artifact_index_sha256: str,
    runtime: RuntimeSnapshot | None = None,
    source: SourceSnapshot | None = None,
    repo_root: str | Path = ".",
    package_names: Sequence[str] = DEFAULT_PACKAGE_NAMES,
    tags: Sequence[str] = (),
    parent_manifest_sha256: str | None = None,
    parent_model_sha256: str | None = None,
    map_id: str | None = None,
    map_definition_version: int | None = None,
) -> TrainingManifest:
    """Build a complete immutable manifest from explicit run inputs.

    Writes a map-free v2 manifest by default; a map-bound task (``map_id`` set)
    writes a v3 manifest carrying the map identity. The ``__post_init__``
    invariant keeps the schema version and the map keys in lockstep.
    """

    if not isinstance(history, HistoryDescriptor):
        raise TypeError("history must be a HistoryDescriptor")
    schema = (
        TRAINING_MANIFEST_SCHEMA_V3 if map_id is not None else TRAINING_MANIFEST_SCHEMA
    )
    # Fail-closed on an UNSUPPORTED map at creation (review Codex-2): a non-null
    # map must resolve to a registered definition, so a run can never persist a
    # manifest naming a map the registry does not have. (The task_fingerprint is
    # caller-computed and cross-checked against the task fields on the read path
    # in task_spec_from_manifest, as it has always been — the factory does not
    # recompute it, keeping the manifest record decoupled from the RL protocol.)
    if map_id is not None:
        resolve_map(map_id, map_definition_version)
    return TrainingManifest(
        schema=schema,
        protocol_fingerprint=protocol_fingerprint,
        task_fingerprint=task_fingerprint,
        content_fingerprint=content_fingerprint,
        training_fingerprint=training_fingerprint,
        algorithm=algorithm,
        status=status,
        render_profile=render_profile,
        fixed_ticks=fixed_ticks,
        reward_mode=reward_mode,
        max_episode_steps=max_episode_steps,
        frame_stack=history.frame_stack,
        history=history,
        history_fingerprint=history.fingerprint(),
        seed=seed,
        n_envs=n_envs,
        timesteps=timesteps,
        hyperparameters=hyperparameters,
        runtime=runtime or collect_runtime_snapshot(package_names),
        source=source or collect_source_snapshot(repo_root),
        command=tuple(command),
        artifacts=artifacts,
        artifact_index_sha256=artifact_index_sha256,
        parent_manifest_sha256=parent_manifest_sha256,
        parent_model_sha256=parent_model_sha256,
        tags=tuple(tags),
        map_id=map_id,
        map_definition_version=map_definition_version,
    )


def canonical_json_bytes(manifest: TrainingManifest) -> bytes:
    encoded = json.dumps(
        manifest.to_dict(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{encoded}\n".encode("utf-8")


def sha256_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def write_training_manifest(run_dir: str | Path, manifest: TrainingManifest) -> Path:
    """Atomically write canonical JSON in the run directory."""

    directory = Path(run_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "training-manifest.json"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=directory, prefix=".training-manifest.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(canonical_json_bytes(manifest))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return destination


def read_training_manifest_bytes(payload: bytes) -> TrainingManifest:
    if not isinstance(payload, bytes):
        raise TypeError("training manifest payload must be bytes")
    document = json.loads(payload)
    if not isinstance(document, Mapping):
        raise TypeError("training manifest must be a JSON object")
    return TrainingManifest.from_dict(document)


def read_training_manifest(path: str | Path) -> TrainingManifest:
    return read_training_manifest_bytes(Path(path).read_bytes())


def validate_training_manifest(
    manifest: TrainingManifest,
    *,
    expected_protocol_fingerprint: str,
    expected_task_fingerprint: str,
    expected_history_fingerprint: str | None = None,
    expected_content_fingerprint: str | None = None,
    allow_content_drift: bool = False,
    expected_training_fingerprint: str | None = None,
    allow_training_drift: bool = False,
    expected_runtime: RuntimeSnapshot | None = None,
    allow_runtime_drift: bool = False,
) -> TrainingManifest:
    """Validate one parsed run, allowing only explicit, tagged drift."""

    if manifest.protocol_fingerprint != expected_protocol_fingerprint:
        raise ManifestCompatibilityError(
            "protocol fingerprint mismatch: "
            f"saved={manifest.protocol_fingerprint!r}, "
            f"expected={expected_protocol_fingerprint!r}"
        )
    if manifest.task_fingerprint != expected_task_fingerprint:
        raise ManifestCompatibilityError(
            "task fingerprint mismatch: "
            f"saved={manifest.task_fingerprint!r}, "
            f"expected={expected_task_fingerprint!r}"
        )
    if (
        expected_history_fingerprint is not None
        and manifest.history_fingerprint != expected_history_fingerprint
    ):
        raise ManifestCompatibilityError(
            "history fingerprint mismatch: "
            f"saved={manifest.history_fingerprint!r}, "
            f"expected={expected_history_fingerprint!r}"
        )
    if (
        expected_content_fingerprint is not None
        and manifest.content_fingerprint != expected_content_fingerprint
    ):
        if not allow_content_drift:
            raise ManifestCompatibilityError(
                "content fingerprint mismatch: "
                f"saved={manifest.content_fingerprint!r}, "
                f"expected={expected_content_fingerprint!r}; "
                "pass allow_content_drift=True to evaluate across content"
            )
        manifest = replace(manifest, tags=(*manifest.tags, CROSS_CONTENT_TAG))
    if (
        expected_training_fingerprint is not None
        and manifest.training_fingerprint != expected_training_fingerprint
    ):
        if not allow_training_drift:
            raise ManifestCompatibilityError(
                "training fingerprint mismatch: "
                f"saved={manifest.training_fingerprint!r}, "
                f"expected={expected_training_fingerprint!r}; "
                "pass allow_training_drift=True to opt in"
            )
        manifest = replace(manifest, tags=(*manifest.tags, CROSS_TRAINING_TAG))
    if expected_runtime is not None:
        differences = runtime_compatibility_differences(
            manifest.runtime, expected_runtime
        )
        if differences and not allow_runtime_drift:
            raise ManifestCompatibilityError(
                "runtime mismatch: "
                + "; ".join(differences)
                + "; pass allow_runtime_drift=True to opt in"
            )
        if differences:
            manifest = replace(manifest, tags=(*manifest.tags, CROSS_RUNTIME_TAG))
    return manifest


def load_training_manifest(
    path: str | Path,
    *,
    expected_protocol_fingerprint: str,
    expected_task_fingerprint: str,
    expected_history_fingerprint: str | None = None,
    expected_content_fingerprint: str | None = None,
    allow_content_drift: bool = False,
    expected_training_fingerprint: str | None = None,
    allow_training_drift: bool = False,
    expected_runtime: RuntimeSnapshot | None = None,
    allow_runtime_drift: bool = False,
) -> TrainingManifest:
    """Load and validate one compatible manifest file snapshot."""

    return validate_training_manifest(
        read_training_manifest(path),
        expected_protocol_fingerprint=expected_protocol_fingerprint,
        expected_task_fingerprint=expected_task_fingerprint,
        expected_history_fingerprint=expected_history_fingerprint,
        expected_content_fingerprint=expected_content_fingerprint,
        allow_content_drift=allow_content_drift,
        expected_training_fingerprint=expected_training_fingerprint,
        allow_training_drift=allow_training_drift,
        expected_runtime=expected_runtime,
        allow_runtime_drift=allow_runtime_drift,
    )
