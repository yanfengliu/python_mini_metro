"""Dependency-light contracts for matched RL resource profiling."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from rl.history import (
    DECISION_HISTORY_LAYOUT,
    EIGHT_MULTISCALE_HISTORY_LAYOUT,
    TEN_MULTISCALE_HISTORY_LAYOUT,
    HistoryDescriptor,
    contiguous_history,
    history_for_layout,
)

BASELINE_CANDIDATE = "8-contiguous"
EIGHT_MULTISCALE_CANDIDATE = "8-multiscale"
TWELVE_MULTISCALE_CANDIDATE = "12-multiscale"
TEN_MULTISCALE_CANDIDATE = "10-multiscale"
PRIMARY_CAMPAIGN = "primary"
FALLBACK_CAMPAIGN = "fallback"

RECURRENT_BATCH_SIZE = 64
RECURRENT_EPOCHS = 4
HISTORICAL_WORKING_SET_CAP_BYTES = 4_197_256_790

PRIMARY_CANDIDATES: Mapping[str, HistoryDescriptor] = MappingProxyType(
    {
        BASELINE_CANDIDATE: contiguous_history(8),
        EIGHT_MULTISCALE_CANDIDATE: history_for_layout(EIGHT_MULTISCALE_HISTORY_LAYOUT),
        TWELVE_MULTISCALE_CANDIDATE: history_for_layout(DECISION_HISTORY_LAYOUT),
    }
)
FALLBACK_CANDIDATES: Mapping[str, HistoryDescriptor] = MappingProxyType(
    {
        BASELINE_CANDIDATE: contiguous_history(8),
        TEN_MULTISCALE_CANDIDATE: history_for_layout(TEN_MULTISCALE_HISTORY_LAYOUT),
    }
)

MAC_ASSUMPTIONS = (
    "one valid observation row",
    "multiply-accumulate pairs only; bias, normalization, activations, pooling, "
    "distributions, padding, and backward work excluded",
    "one shared MiniMetroCNN pass",
    "separate one-step actor and critic LSTMs",
    "separate 256-to-64-to-64 actor and critic MLPs",
    "64-feature action and value heads",
)
MAC_FORMULAS: Mapping[str, str] = MappingProxyType(
    {
        "conv2d": "output_height * output_width * out_channels * (in_channels / groups) * kernel_height * kernel_width",
        "linear": "in_features * out_features",
        "lstm": "directions * 4 * hidden_size * (layer_input_size + hidden_size) per layer",
    }
)

__all__ = (
    "BASELINE_CANDIDATE",
    "EIGHT_MULTISCALE_CANDIDATE",
    "FALLBACK_CAMPAIGN",
    "FALLBACK_CANDIDATES",
    "HISTORICAL_WORKING_SET_CAP_BYTES",
    "InferenceMacEstimate",
    "MAC_ASSUMPTIONS",
    "MAC_FORMULAS",
    "PRIMARY_CAMPAIGN",
    "PRIMARY_CANDIDATES",
    "ProfileRepeat",
    "PromotionDecision",
    "RECURRENT_BATCH_SIZE",
    "RECURRENT_EPOCHS",
    "StorageEstimate",
    "TEN_MULTISCALE_CANDIDATE",
    "TWELVE_MULTISCALE_CANDIDATE",
    "conv2d_macs",
    "conv2d_output_size",
    "counterbalanced_schedule",
    "estimate_inference_macs",
    "estimate_storage",
    "evaluate_promotion",
    "linear_macs",
    "lstm_macs",
)


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _nonnegative_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def counterbalanced_schedule(
    candidates: Sequence[str],
    *,
    repeats: int,
) -> tuple[tuple[str, ...], ...]:
    """Return complete deterministic cycles with exact position balance."""

    repeats = _positive_int(repeats, "repeats")
    if repeats < 3:
        raise ValueError("repeats must be at least three")
    names = tuple(candidates)
    if not names:
        raise ValueError("candidates must not be empty")
    if any(not isinstance(name, str) or not name for name in names):
        raise TypeError("candidate names must be non-empty strings")
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be unique")
    if repeats % len(names) != 0:
        raise ValueError("repeats must contain complete candidate cycles")
    return tuple(
        names[index % len(names) :] + names[: index % len(names)]
        for index in range(repeats)
    )


@dataclass(frozen=True, slots=True)
class StorageEstimate:
    single_frame_bytes: int
    rollout_observations_bytes: int
    history_ring_bytes: int
    one_step_output_bytes: int
    nominal_minibatch_uint8_bytes: int
    nominal_minibatch_float32_bytes: int


def estimate_storage(
    history: HistoryDescriptor,
    *,
    n_envs: int = 8,
    n_steps: int = 128,
    channels_per_frame: int = 3,
    height: int = 108,
    width: int = 192,
    batch_size: int = RECURRENT_BATCH_SIZE,
) -> StorageEstimate:
    """Calculate exact uint8 storage and nominal unpadded float32 input bytes."""

    if not isinstance(history, HistoryDescriptor):
        raise TypeError("history must be a HistoryDescriptor")
    dimensions = {
        "n_envs": n_envs,
        "n_steps": n_steps,
        "channels_per_frame": channels_per_frame,
        "height": height,
        "width": width,
        "batch_size": batch_size,
    }
    for name, value in dimensions.items():
        _positive_int(value, name)
    single_frame = channels_per_frame * height * width
    output_row = history.frame_stack * single_frame
    return StorageEstimate(
        single_frame_bytes=single_frame,
        rollout_observations_bytes=n_steps * n_envs * output_row,
        history_ring_bytes=n_envs * (max(history.offsets) + 1) * single_frame,
        one_step_output_bytes=n_envs * output_row,
        nominal_minibatch_uint8_bytes=batch_size * output_row,
        nominal_minibatch_float32_bytes=batch_size * output_row * 4,
    )


@dataclass(frozen=True, slots=True)
class ProfileRepeat:
    candidate: str
    repeat: int
    peak_working_set_bytes: int
    end_to_end_fps: float
    valid: bool
    batch_size: int
    n_epochs: int

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, str) or not self.candidate:
            raise TypeError("candidate must be a non-empty string")
        _nonnegative_int(self.repeat, "repeat")
        _positive_int(self.peak_working_set_bytes, "peak_working_set_bytes")
        if isinstance(self.end_to_end_fps, bool) or not isinstance(
            self.end_to_end_fps, (int, float)
        ):
            raise TypeError("end_to_end_fps must be numeric")
        if not math.isfinite(self.end_to_end_fps) or self.end_to_end_fps <= 0:
            raise ValueError("end_to_end_fps must be positive and finite")
        if not isinstance(self.valid, bool):
            raise TypeError("valid must be boolean")
        _positive_int(self.batch_size, "batch_size")
        _positive_int(self.n_epochs, "n_epochs")


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    campaign: str
    target: str
    eligible: bool
    complete: bool
    all_valid: bool
    settings_match: bool
    baseline_median_peak_bytes: float | None
    target_median_peak_bytes: float | None
    baseline_median_fps: float | None
    target_median_fps: float | None
    relative_memory_passed: bool
    historical_memory_passed: bool
    throughput_passed: bool
    promoted: bool
    reasons: tuple[str, ...]


def _campaign_contract(
    campaign: str,
) -> tuple[Mapping[str, HistoryDescriptor], str]:
    if campaign == PRIMARY_CAMPAIGN:
        return PRIMARY_CANDIDATES, TWELVE_MULTISCALE_CANDIDATE
    if campaign == FALLBACK_CAMPAIGN:
        return FALLBACK_CANDIDATES, TEN_MULTISCALE_CANDIDATE
    raise ValueError(f"unsupported campaign: {campaign!r}")


def _median_for(
    samples: Sequence[ProfileRepeat],
    candidate: str,
    attribute: str,
) -> float | None:
    values = [
        getattr(sample, attribute)
        for sample in samples
        if sample.candidate == candidate
    ]
    return float(statistics.median(values)) if values else None


def evaluate_promotion(
    samples: Sequence[ProfileRepeat],
    *,
    campaign: str,
    target: str | None = None,
    expected_repeats: int = 3,
) -> PromotionDecision:
    """Evaluate one complete primary or fallback campaign without side effects."""

    candidates, eligible_target = _campaign_contract(campaign)
    expected_repeats = _positive_int(expected_repeats, "expected_repeats")
    if expected_repeats < 3:
        raise ValueError("expected_repeats must be at least three")
    if expected_repeats % len(candidates) != 0:
        raise ValueError("expected_repeats must contain complete candidate cycles")
    target = eligible_target if target is None else target
    if not isinstance(target, str) or not target:
        raise TypeError("target must be a non-empty string")
    rows = tuple(samples)
    if any(not isinstance(sample, ProfileRepeat) for sample in rows):
        raise TypeError("samples must contain ProfileRepeat values")

    expected_keys = {
        (candidate, repeat)
        for candidate in candidates
        for repeat in range(expected_repeats)
    }
    counts = Counter((sample.candidate, sample.repeat) for sample in rows)
    complete = set(counts) == expected_keys and all(
        count == 1 for count in counts.values()
    )
    all_valid = complete and all(sample.valid for sample in rows)
    settings_match = complete and all(
        sample.batch_size == RECURRENT_BATCH_SIZE
        and sample.n_epochs == RECURRENT_EPOCHS
        for sample in rows
    )
    eligible = target == eligible_target

    baseline_peak = _median_for(rows, BASELINE_CANDIDATE, "peak_working_set_bytes")
    target_peak = _median_for(rows, target, "peak_working_set_bytes")
    baseline_fps = _median_for(rows, BASELINE_CANDIDATE, "end_to_end_fps")
    target_fps = _median_for(rows, target, "end_to_end_fps")
    relative_memory_passed = (
        baseline_peak is not None
        and target_peak is not None
        and target_peak * 4 <= baseline_peak * 5
    )
    historical_memory_passed = (
        target_peak is not None and target_peak < HISTORICAL_WORKING_SET_CAP_BYTES
    )
    throughput_passed = (
        baseline_fps is not None
        and target_fps is not None
        and target_fps * 4 >= baseline_fps * 3
    )
    gates = (
        eligible,
        complete,
        all_valid,
        settings_match,
        relative_memory_passed,
        historical_memory_passed,
        throughput_passed,
    )
    reason_names = (
        "target-ineligible",
        "campaign-incomplete",
        "repeat-invalid",
        "settings-mismatch",
        "relative-memory-failed",
        "historical-memory-failed",
        "throughput-failed",
    )
    return PromotionDecision(
        campaign=campaign,
        target=target,
        eligible=eligible,
        complete=complete,
        all_valid=all_valid,
        settings_match=settings_match,
        baseline_median_peak_bytes=baseline_peak,
        target_median_peak_bytes=target_peak,
        baseline_median_fps=baseline_fps,
        target_median_fps=target_fps,
        relative_memory_passed=relative_memory_passed,
        historical_memory_passed=historical_memory_passed,
        throughput_passed=throughput_passed,
        promoted=all(gates),
        reasons=tuple(name for name, passed in zip(reason_names, gates) if not passed),
    )


def conv2d_output_size(
    input_size: int,
    *,
    kernel: int,
    stride: int = 1,
    padding: int = 0,
) -> int:
    """Return one spatial output dimension for a dilation-one convolution."""

    input_size = _positive_int(input_size, "input_size")
    kernel = _positive_int(kernel, "kernel")
    stride = _positive_int(stride, "stride")
    padding = _nonnegative_int(padding, "padding")
    output = (input_size + 2 * padding - kernel) // stride + 1
    if output <= 0:
        raise ValueError("convolution output size must be positive")
    return output


def conv2d_macs(
    *,
    in_channels: int,
    out_channels: int,
    output_height: int,
    output_width: int,
    kernel_height: int,
    kernel_width: int,
) -> int:
    """Count dense Conv2d multiply-accumulate pairs, excluding bias."""

    values = (
        _positive_int(in_channels, "in_channels"),
        _positive_int(out_channels, "out_channels"),
        _positive_int(output_height, "output_height"),
        _positive_int(output_width, "output_width"),
        _positive_int(kernel_height, "kernel_height"),
        _positive_int(kernel_width, "kernel_width"),
    )
    return math.prod(values)


def linear_macs(in_features: int, out_features: int) -> int:
    """Count dense Linear multiply-accumulate pairs, excluding bias."""

    return _positive_int(in_features, "in_features") * _positive_int(
        out_features, "out_features"
    )


def lstm_macs(input_size: int, hidden_size: int) -> int:
    """Count one single-layer, one-timestep LSTM forward, excluding bias."""

    input_size = _positive_int(input_size, "input_size")
    hidden_size = _positive_int(hidden_size, "hidden_size")
    return 4 * hidden_size * (input_size + hidden_size)


@dataclass(frozen=True, slots=True)
class InferenceMacEstimate:
    cnn_convolutions: int
    cnn_projection: int
    actor_lstm: int
    critic_lstm: int
    actor_mlp: int
    critic_mlp: int
    action_head: int
    value_head: int

    @property
    def total(self) -> int:
        return sum(
            (
                self.cnn_convolutions,
                self.cnn_projection,
                self.actor_lstm,
                self.critic_lstm,
                self.actor_mlp,
                self.critic_mlp,
                self.action_head,
                self.value_head,
            )
        )


def estimate_inference_macs(history: HistoryDescriptor) -> InferenceMacEstimate:
    """Estimate the live recurrent policy's inference MACs for one valid row."""

    if not isinstance(history, HistoryDescriptor):
        raise TypeError("history must be a HistoryDescriptor")
    height, width = 108, 192
    first_height = conv2d_output_size(height, kernel=8, stride=4, padding=2)
    first_width = conv2d_output_size(width, kernel=8, stride=4, padding=2)
    second_height = conv2d_output_size(first_height, kernel=4, stride=2, padding=1)
    second_width = conv2d_output_size(first_width, kernel=4, stride=2, padding=1)
    third_height = conv2d_output_size(second_height, kernel=3, stride=2, padding=1)
    third_width = conv2d_output_size(second_width, kernel=3, stride=2, padding=1)
    convolution_macs = sum(
        (
            conv2d_macs(
                in_channels=history.frame_stack * 3,
                out_channels=32,
                output_height=first_height,
                output_width=first_width,
                kernel_height=8,
                kernel_width=8,
            ),
            conv2d_macs(
                in_channels=32,
                out_channels=64,
                output_height=second_height,
                output_width=second_width,
                kernel_height=4,
                kernel_width=4,
            ),
            conv2d_macs(
                in_channels=64,
                out_channels=64,
                output_height=third_height,
                output_width=third_width,
                kernel_height=3,
                kernel_width=3,
            ),
        )
    )
    recurrent_macs = lstm_macs(256, 256)
    mlp_macs = linear_macs(256, 64) + linear_macs(64, 64)
    return InferenceMacEstimate(
        cnn_convolutions=convolution_macs,
        cnn_projection=linear_macs(64 * 3 * 5, 256),
        actor_lstm=recurrent_macs,
        critic_lstm=recurrent_macs,
        actor_mlp=mlp_macs,
        critic_mlp=mlp_macs,
        action_head=linear_macs(64, 8 + 192 + 108),
        value_head=linear_macs(64, 1),
    )
