"""Immutable, dependency-light provenance for RL training artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeAlias

from rl.provenance import (
    DEFAULT_PACKAGE_NAMES,
    RuntimeSnapshot,
    SourceSnapshot,
    collect_runtime_snapshot,
    collect_source_snapshot,
    runtime_compatibility_differences,
)

TRAINING_MANIFEST_SCHEMA = "mini-metro-training-manifest-v1"
CROSS_CONTENT_TAG = "cross-content-evaluation"
CROSS_RUNTIME_TAG = "cross-runtime-evaluation"
CROSS_TRAINING_TAG = "cross-training-implementation"

JsonScalar: TypeAlias = None | bool | int | float | str
FrozenJson: TypeAlias = (
    JsonScalar | tuple["FrozenJson", ...] | Mapping[str, "FrozenJson"]
)


class ManifestCompatibilityError(ValueError):
    """A saved training run cannot be used with the requested environment."""


def _require_nonempty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_sha256(value: object, name: str) -> str:
    text = _require_nonempty(value, name)
    if len(text) != 64 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return text


def _freeze_json(value: Any, name: str = "value") -> FrozenJson:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} numbers must be finite")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, FrozenJson] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError(f"{name} keys must be strings")
            frozen[key] = _freeze_json(value[key], f"{name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, f"{name}[{index}]") for index, item in enumerate(value)
        )
    raise TypeError(f"{name} contains unsupported value {type(value).__name__}")


def _thaw_json(value: FrozenJson) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _require_exact_keys(
    document: Mapping[str, Any], expected: set[str], name: str
) -> None:
    actual = set(document)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"invalid {name} keys: missing={missing}, unknown={unknown}")


@dataclass(frozen=True, slots=True)
class TrainingManifest:
    schema: str
    protocol_fingerprint: str
    task_fingerprint: str
    content_fingerprint: str
    training_fingerprint: str
    algorithm: str
    status: str
    render_profile: str
    fixed_ticks: int
    reward_mode: str
    max_episode_steps: int
    frame_stack: int
    seed: int
    n_envs: int
    timesteps: int
    hyperparameters: Mapping[str, FrozenJson]
    runtime: RuntimeSnapshot
    source: SourceSnapshot
    command: tuple[str, ...]
    artifacts: Mapping[str, str]
    artifact_index_sha256: str
    parent_manifest_sha256: str | None = None
    parent_model_sha256: str | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.schema != TRAINING_MANIFEST_SCHEMA:
            raise ValueError(f"unsupported training manifest schema: {self.schema!r}")
        for name in (
            "protocol_fingerprint",
            "task_fingerprint",
            "content_fingerprint",
            "training_fingerprint",
            "algorithm",
            "render_profile",
            "reward_mode",
        ):
            _require_nonempty(getattr(self, name), name)
        if self.status not in {"running", "complete"}:
            raise ValueError("status must be 'running' or 'complete'")
        object.__setattr__(
            self,
            "artifact_index_sha256",
            _require_sha256(self.artifact_index_sha256, "artifact_index_sha256"),
        )
        for name in ("parent_manifest_sha256", "parent_model_sha256"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _require_sha256(value, name))

        for name in (
            "fixed_ticks",
            "max_episode_steps",
            "frame_stack",
            "n_envs",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("seed", "timesteps"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

        frozen_hyperparameters = _freeze_json(self.hyperparameters, "hyperparameters")
        if not isinstance(frozen_hyperparameters, Mapping):
            raise TypeError("hyperparameters must be an object")
        object.__setattr__(self, "hyperparameters", frozen_hyperparameters)

        command = tuple(self.command)
        if not command:
            raise ValueError("command must not be empty")
        for argument in command:
            _require_nonempty(argument, "command argument")
        object.__setattr__(self, "command", command)

        artifact_paths: dict[str, str] = {}
        for name in sorted(self.artifacts):
            _require_nonempty(name, "artifact name")
            artifact_paths[name] = _require_nonempty(
                self.artifacts[name], f"artifact path for {name}"
            )
        object.__setattr__(self, "artifacts", MappingProxyType(artifact_paths))

        tags = tuple(sorted({_require_nonempty(tag, "tag") for tag in self.tags}))
        object.__setattr__(self, "tags", tags)

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "artifactIndexSha256": self.artifact_index_sha256,
            "artifacts": dict(self.artifacts),
            "command": list(self.command),
            "contentFingerprint": self.content_fingerprint,
            "fixedTicks": self.fixed_ticks,
            "frameStack": self.frame_stack,
            "hyperparameters": _thaw_json(self.hyperparameters),
            "maxEpisodeSteps": self.max_episode_steps,
            "nEnvs": self.n_envs,
            "parentManifestSha256": self.parent_manifest_sha256,
            "parentModelSha256": self.parent_model_sha256,
            "protocolFingerprint": self.protocol_fingerprint,
            "renderProfile": self.render_profile,
            "rewardMode": self.reward_mode,
            "runtime": self.runtime.to_dict(),
            "schema": self.schema,
            "seed": self.seed,
            "source": self.source.to_dict(),
            "status": self.status,
            "tags": list(self.tags),
            "taskFingerprint": self.task_fingerprint,
            "timesteps": self.timesteps,
            "trainingFingerprint": self.training_fingerprint,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> TrainingManifest:
        expected = {
            "algorithm",
            "artifactIndexSha256",
            "artifacts",
            "command",
            "contentFingerprint",
            "fixedTicks",
            "frameStack",
            "hyperparameters",
            "maxEpisodeSteps",
            "nEnvs",
            "parentManifestSha256",
            "parentModelSha256",
            "protocolFingerprint",
            "renderProfile",
            "rewardMode",
            "runtime",
            "schema",
            "seed",
            "source",
            "status",
            "tags",
            "taskFingerprint",
            "timesteps",
            "trainingFingerprint",
        }
        _require_exact_keys(document, expected, "training manifest")
        runtime = document["runtime"]
        source = document["source"]
        hyperparameters = document["hyperparameters"]
        artifacts = document["artifacts"]
        for value, name in (
            (runtime, "runtime"),
            (source, "source"),
            (hyperparameters, "hyperparameters"),
            (artifacts, "artifacts"),
        ):
            if not isinstance(value, Mapping):
                raise TypeError(f"manifest {name} must be an object")
        for key in ("command", "tags"):
            if not isinstance(document[key], list):
                raise TypeError(f"manifest {key} must be an array")
        return cls(
            schema=document["schema"],
            protocol_fingerprint=document["protocolFingerprint"],
            task_fingerprint=document["taskFingerprint"],
            content_fingerprint=document["contentFingerprint"],
            training_fingerprint=document["trainingFingerprint"],
            algorithm=document["algorithm"],
            status=document["status"],
            render_profile=document["renderProfile"],
            fixed_ticks=document["fixedTicks"],
            reward_mode=document["rewardMode"],
            max_episode_steps=document["maxEpisodeSteps"],
            frame_stack=document["frameStack"],
            seed=document["seed"],
            n_envs=document["nEnvs"],
            timesteps=document["timesteps"],
            hyperparameters=hyperparameters,
            runtime=RuntimeSnapshot.from_dict(runtime),
            source=SourceSnapshot.from_dict(source),
            command=tuple(document["command"]),
            artifacts=artifacts,
            artifact_index_sha256=document["artifactIndexSha256"],
            parent_manifest_sha256=document["parentManifestSha256"],
            parent_model_sha256=document["parentModelSha256"],
            tags=tuple(document["tags"]),
        )


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
    frame_stack: int,
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
) -> TrainingManifest:
    """Build a complete immutable training manifest from explicit run inputs."""

    return TrainingManifest(
        schema=TRAINING_MANIFEST_SCHEMA,
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
        frame_stack=frame_stack,
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
        expected_content_fingerprint=expected_content_fingerprint,
        allow_content_drift=allow_content_drift,
        expected_training_fingerprint=expected_training_fingerprint,
        allow_training_drift=allow_training_drift,
        expected_runtime=expected_runtime,
        allow_runtime_drift=allow_runtime_drift,
    )
