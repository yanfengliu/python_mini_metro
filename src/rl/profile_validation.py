"""Exact production-worker validation for temporal-history resource campaigns."""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rl.protocol import TaskSpec, protocol_fingerprint
from rl.resource_profile import (
    FALLBACK_CANDIDATES,
    PRIMARY_CANDIDATES,
    estimate_inference_macs,
    estimate_storage,
)
from rl.training import compute_training_fingerprint

WORKER_SCHEMA = "mini-metro-history-profile-worker-v1"

__all__ = ("validate_worker_result",)


def _metadata_matches(
    value: Any,
    *,
    shape: list[int],
    dtype: str,
    byte_count: int,
) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("shape") == shape
        and value.get("dtype") == dtype
        and value.get("bytes") == byte_count
    )


def _positive_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def _rate_matches(value: Any, numerator: int, seconds: Any) -> bool:
    return (
        _positive_number(value)
        and _positive_number(seconds)
        and math.isclose(float(value), numerator / float(seconds), rel_tol=1e-12)
    )


def validate_worker_result(
    candidate: str,
    result: Mapping[str, Any],
    *,
    seed: int,
    torch_threads: int,
    torch_interop_threads: int,
    repo_root: Path,
) -> tuple[str, ...]:
    """Return every production-contract mismatch without trusting result shape."""

    if not isinstance(result, Mapping):
        return ("document",)
    histories = {**PRIMARY_CANDIDATES, **FALLBACK_CANDIDATES}
    history = histories[candidate]
    storage = estimate_storage(history)
    macs = estimate_inference_macs(history)
    channels = history.frame_stack * 3
    errors: list[str] = []

    def require(condition: bool, field: str) -> None:
        if not condition:
            errors.append(field)

    require(result.get("schema") == WORKER_SCHEMA, "schema")
    require(result.get("candidate") == candidate, "candidate")
    require(result.get("history") == history.to_dict(), "history")
    require(
        result.get("historyFingerprint") == history.fingerprint(), "historyFingerprint"
    )
    require(
        result.get("protocolFingerprint") == protocol_fingerprint(),
        "protocolFingerprint",
    )
    require(
        result.get("taskFingerprint") == TaskSpec().fingerprint(), "taskFingerprint"
    )
    require(
        result.get("trainingFingerprint") == compute_training_fingerprint(repo_root),
        "trainingFingerprint",
    )

    workload = result.get("workload")
    expected_workload = {
        "batchSize": 64,
        "device": "cpu",
        "nEnvs": 8,
        "nEpochs": 4,
        "nSteps": 128,
        "scheduleHorizon": 1_000_000,
        "seed": seed,
        "torchInteropThreads": torch_interop_threads,
        "torchThreads": torch_threads,
        "transitionsPerIteration": 1024,
    }
    require(
        isinstance(workload, Mapping)
        and all(workload.get(key) == value for key, value in expected_workload.items()),
        "workload",
    )

    iterations = result.get("iterations")
    iterations_valid = (
        isinstance(iterations, list)
        and len(iterations) == 2
        and all(isinstance(row, Mapping) for row in iterations)
    )
    require(iterations_valid, "iterations")
    measured: Mapping[str, Any] = {}
    if iterations_valid:
        require(
            [row.get("phase") for row in iterations] == ["warmup", "measured"]
            and all(row.get("transitions") == 1024 for row in iterations)
            and all(row.get("epochUpdates") == 4 for row in iterations)
            and all(_positive_number(row.get("learningRate")) for row in iterations)
            and all(
                _positive_number(row.get("collectionSeconds")) for row in iterations
            )
            and all(_positive_number(row.get("trainingSeconds")) for row in iterations),
            "iterations",
        )
        measured = iterations[1]
    require(
        result.get("warmupMaximumValidAges") == [max(history.offsets)] * 8,
        "warmupMaximumValidAges",
    )

    actual_storage = result.get("storage")
    storage_valid = isinstance(actual_storage, Mapping)
    require(storage_valid, "storage")
    if storage_valid:
        require(
            actual_storage.get("historyRingBytes") == storage.history_ring_bytes,
            "historyRingBytes",
        )
        require(
            _metadata_matches(
                actual_storage.get("rolloutBuffer"),
                shape=[128, 8, channels, 108, 192],
                dtype="uint8",
                byte_count=storage.rollout_observations_bytes,
            ),
            "rolloutBuffer",
        )
        require(
            _metadata_matches(
                actual_storage.get("oneStepOutput"),
                shape=[8, channels, 108, 192],
                dtype="uint8",
                byte_count=storage.one_step_output_bytes,
            ),
            "oneStepOutput",
        )

    model = result.get("model")
    model_valid = isinstance(model, Mapping)
    require(model_valid, "model")
    if model_valid:
        require(
            isinstance(model.get("trainableParameters"), int)
            and model["trainableParameters"] > 0,
            "trainableParameters",
        )
        expected_components = {
            "actionHead": macs.action_head,
            "actorLstm": macs.actor_lstm,
            "actorMlp": macs.actor_mlp,
            "cnn": macs.cnn_convolutions + macs.cnn_projection,
            "criticLstm": macs.critic_lstm,
            "criticMlp": macs.critic_mlp,
            "valueHead": macs.value_head,
        }
        dynamic_macs = model.get("inferenceForwardMacs")
        require(
            isinstance(dynamic_macs, Mapping)
            and dynamic_macs.get("components") == expected_components
            and dynamic_macs.get("total") == macs.total,
            "inferenceForwardMacs",
        )

    minibatches = result.get("measuredOptimizerMinibatches")
    normalized = result.get("measuredNormalizedInputs")
    batches_valid = (
        isinstance(minibatches, list)
        and isinstance(normalized, list)
        and len(minibatches) == len(normalized) == 64
    )
    require(batches_valid, "minibatches")
    valid_rows = 0
    padded_rows = 0
    if batches_valid:
        for index, (batch, image) in enumerate(zip(minibatches, normalized)):
            if not isinstance(batch, Mapping):
                errors.append(f"minibatch[{index}]")
                continue
            padded = batch.get("paddedRows")
            valid = batch.get("validRows")
            rows_valid = (
                isinstance(padded, int)
                and isinstance(valid, int)
                and padded >= valid > 0
            )
            require(rows_valid, f"minibatch[{index}].rows")
            if not rows_valid:
                continue
            raw_bytes = padded * channels * 108 * 192
            require(
                _metadata_matches(
                    batch.get("observation"),
                    shape=[padded, channels, 108, 192],
                    dtype="uint8",
                    byte_count=raw_bytes,
                ),
                f"minibatch[{index}].observation",
            )
            require(
                _metadata_matches(
                    batch.get("mask"),
                    shape=[padded],
                    dtype="float32",
                    byte_count=padded * 4,
                ),
                f"minibatch[{index}].mask",
            )
            require(
                _metadata_matches(
                    image,
                    shape=[padded, channels, 108, 192],
                    dtype="float32",
                    byte_count=raw_bytes * 4,
                ),
                f"normalized[{index}]",
            )
            valid_rows += valid
            padded_rows += padded

    rates = result.get("rates")
    rates_valid = isinstance(rates, Mapping)
    require(rates_valid, "rates")
    if rates_valid:
        require(
            valid_rows == rates.get("validOptimizerRows") == 4096, "validOptimizerRows"
        )
        require(
            padded_rows == rates.get("paddedOptimizerRows") and padded_rows >= 4096,
            "paddedOptimizerRows",
        )
        collection_seconds = measured.get("collectionSeconds")
        training_seconds = measured.get("trainingSeconds")
        require(
            _rate_matches(rates.get("collectionFps"), 1024, collection_seconds),
            "collectionFps",
        )
        require(
            _rate_matches(
                rates.get("validOptimizerRowsPerSecond"), 4096, training_seconds
            ),
            "validOptimizerRowsPerSecond",
        )
        require(
            _rate_matches(
                rates.get("paddedOptimizerRowsPerSecond"), padded_rows, training_seconds
            ),
            "paddedOptimizerRowsPerSecond",
        )
        end_to_end_fps = rates.get("endToEndFps")
        if (
            _positive_number(collection_seconds)
            and _positive_number(training_seconds)
            and _positive_number(end_to_end_fps)
        ):
            require(
                math.isclose(
                    float(end_to_end_fps),
                    1024 / (float(collection_seconds) + float(training_seconds)),
                    rel_tol=1e-12,
                ),
                "endToEndFps",
            )
        else:
            require(False, "endToEndFps")

    window = result.get("measurementWindow")
    require(
        isinstance(window, Mapping)
        and isinstance(window.get("startPerfCounterNs"), int)
        and isinstance(window.get("endPerfCounterNs"), int)
        and 0 < window["startPerfCounterNs"] < window["endPerfCounterNs"],
        "measurementWindow",
    )
    return tuple(errors)
