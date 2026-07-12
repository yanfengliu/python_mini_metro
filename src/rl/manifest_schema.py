"""Immutable versioned training-manifest record and JSON schema parsing."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, TypeAlias

from rl.history import HistoryDescriptor, contiguous_history
from rl.provenance import RuntimeSnapshot, SourceSnapshot

TRAINING_MANIFEST_SCHEMA_V1 = "mini-metro-training-manifest-v1"
TRAINING_MANIFEST_SCHEMA = "mini-metro-training-manifest-v2"
SUPPORTED_TRAINING_MANIFEST_SCHEMAS = frozenset(
    {TRAINING_MANIFEST_SCHEMA_V1, TRAINING_MANIFEST_SCHEMA}
)

JsonScalar: TypeAlias = None | bool | int | float | str
FrozenJson: TypeAlias = (
    JsonScalar | tuple["FrozenJson", ...] | Mapping[str, "FrozenJson"]
)

_V1_KEYS = {
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
_V2_KEYS = _V1_KEYS | {"history", "historyFingerprint"}

__all__ = (
    "FrozenJson",
    "SUPPORTED_TRAINING_MANIFEST_SCHEMAS",
    "TRAINING_MANIFEST_SCHEMA",
    "TRAINING_MANIFEST_SCHEMA_V1",
    "TrainingManifest",
)


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
    history: HistoryDescriptor
    history_fingerprint: str
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
        if self.schema not in SUPPORTED_TRAINING_MANIFEST_SCHEMAS:
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

        for name in ("fixed_ticks", "max_episode_steps", "frame_stack", "n_envs"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("seed", "timesteps"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

        if not isinstance(self.history, HistoryDescriptor):
            raise TypeError("history must be a HistoryDescriptor")
        expected_history_fingerprint = self.history.fingerprint()
        history_fingerprint = _require_sha256(
            self.history_fingerprint, "history_fingerprint"
        )
        if history_fingerprint != expected_history_fingerprint:
            raise ValueError("history fingerprint does not match descriptor")
        object.__setattr__(self, "history_fingerprint", history_fingerprint)
        if self.frame_stack != self.history.frame_stack:
            raise ValueError("frame_stack does not match history descriptor")
        if (
            self.schema == TRAINING_MANIFEST_SCHEMA_V1
            and self.history != contiguous_history(self.frame_stack)
        ):
            raise ValueError("manifest v1 history must be contiguous")

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
        document = {
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
        if self.schema == TRAINING_MANIFEST_SCHEMA:
            document["history"] = self.history.to_dict()
            document["historyFingerprint"] = self.history_fingerprint
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> TrainingManifest:
        schema = document.get("schema")
        if schema == TRAINING_MANIFEST_SCHEMA_V1:
            expected_keys = _V1_KEYS
        elif schema == TRAINING_MANIFEST_SCHEMA:
            expected_keys = _V2_KEYS
        else:
            raise ValueError(f"unsupported training manifest schema: {schema!r}")
        _require_exact_keys(document, expected_keys, "training manifest")

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

        if schema == TRAINING_MANIFEST_SCHEMA_V1:
            history = contiguous_history(document["frameStack"])
            history_fingerprint = history.fingerprint()
        else:
            history_document = document["history"]
            if not isinstance(history_document, Mapping):
                raise TypeError("manifest history must be an object")
            history = HistoryDescriptor.from_dict(history_document)
            history_fingerprint = document["historyFingerprint"]

        return cls(
            schema=schema,
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
            history=history,
            history_fingerprint=history_fingerprint,
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
