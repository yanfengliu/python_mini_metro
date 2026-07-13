"""Fresh-process worker for matched RL temporal-history resource profiles."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
RESULT_SCHEMA = "mini-metro-history-profile-worker-v1"
PRODUCTION_SCHEDULE_HORIZON = 1_000_000


@dataclass(frozen=True, slots=True)
class ProfileWorkload:
    n_envs: int = 8
    n_steps: int = 128
    n_epochs: int = 4
    schedule_horizon: int = PRODUCTION_SCHEDULE_HORIZON
    seed: int = 42
    device: str = "cpu"
    torch_threads: int | None = None
    torch_interop_threads: int | None = None

    def __post_init__(self) -> None:
        for name in ("n_envs", "n_steps", "n_epochs", "schedule_horizon"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, int)
            or self.seed < 0
        ):
            raise ValueError("seed must be a non-negative integer")
        for name in ("torch_threads", "torch_interop_threads"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                raise ValueError(f"{name} must be a positive integer or None")
        if self.device != "cpu":
            raise ValueError("resource profiles require device='cpu'")
        if self.schedule_horizon <= 2 * self.n_envs * self.n_steps:
            raise ValueError("schedule_horizon must exceed both profiled iterations")


def release_preimport_handshake(
    *,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    pid: int | None = None,
) -> None:
    ready = {"event": "ready", "pid": os.getpid() if pid is None else pid}
    output_stream.write(f"{json.dumps(ready, separators=(',', ':'), sort_keys=True)}\n")
    output_stream.flush()
    if input_stream.readline() != "START\n":
        raise RuntimeError("pre-import handshake requires exact 'START\\n'")


def write_result_atomic(path: Path, result: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(
        result,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    try:
        temporary.write_text(f"{payload}\n", encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def resolve_candidate(candidate: str) -> Any:
    _activate_repo_imports()
    from rl.history import (
        DECISION_HISTORY_LAYOUT,
        EIGHT_MULTISCALE_HISTORY_LAYOUT,
        TEN_MULTISCALE_HISTORY_LAYOUT,
        contiguous_history,
        history_for_layout,
    )

    if candidate == "8-contiguous":
        return contiguous_history(8)
    layouts = {
        "8-multiscale": EIGHT_MULTISCALE_HISTORY_LAYOUT,
        "12-multiscale": DECISION_HISTORY_LAYOUT,
        "10-multiscale": TEN_MULTISCALE_HISTORY_LAYOUT,
    }
    try:
        return history_for_layout(layouts[candidate])
    except KeyError as error:
        raise ValueError(f"unsupported profile candidate: {candidate!r}") from error


def _activate_repo_imports() -> None:
    source = str(SRC_ROOT)
    if source not in sys.path:
        sys.path.insert(0, source)


def _array_metadata(value: Any) -> dict[str, Any]:
    shape = [int(dimension) for dimension in value.shape]
    dtype = str(value.dtype).removeprefix("torch.")
    if hasattr(value, "element_size"):
        byte_count = int(value.numel() * value.element_size())
    else:
        byte_count = int(value.nbytes)
    return {"bytes": byte_count, "dtype": dtype, "shape": shape}


def _linear_macs(module: Any) -> int:
    return sum(
        int(layer.in_features) * int(layer.out_features)
        for layer in module.modules()
        if layer.__class__.__name__ == "Linear"
    )


def _lstm_macs(module: Any) -> int:
    directions = 2 if module.bidirectional else 1
    total = 0
    for layer_index in range(int(module.num_layers)):
        layer_input = (
            int(module.input_size)
            if layer_index == 0
            else int(module.hidden_size) * directions
        )
        total += (
            directions
            * 4
            * int(module.hidden_size)
            * (layer_input + int(module.hidden_size))
        )
    return total


def estimate_inference_forward_macs(model: Any) -> dict[str, Any]:
    policy = model.policy
    if not bool(policy.share_features_extractor):
        raise RuntimeError("MAC contract requires one shared feature extractor")
    channels, height, width = (int(value) for value in model.observation_space.shape)
    cnn_macs = 0
    for layer in policy.features_extractor.encoder:
        if layer.__class__.__name__ == "Conv2d":
            kernel_h, kernel_w = (int(value) for value in layer.kernel_size)
            stride_h, stride_w = (int(value) for value in layer.stride)
            pad_h, pad_w = (int(value) for value in layer.padding)
            dilation_h, dilation_w = (int(value) for value in layer.dilation)
            height = (
                height + 2 * pad_h - dilation_h * (kernel_h - 1) - 1
            ) // stride_h + 1
            width = (
                width + 2 * pad_w - dilation_w * (kernel_w - 1) - 1
            ) // stride_w + 1
            cnn_macs += (
                height
                * width
                * int(layer.out_channels)
                * (channels // int(layer.groups))
                * kernel_h
                * kernel_w
            )
            channels = int(layer.out_channels)
    cnn_macs += _linear_macs(policy.features_extractor.projection)
    components = {
        "actionHead": _linear_macs(policy.action_net),
        "actorLstm": _lstm_macs(policy.lstm_actor),
        "actorMlp": _linear_macs(policy.mlp_extractor.policy_net),
        "cnn": cnn_macs,
        "criticLstm": _lstm_macs(policy.lstm_critic),
        "criticMlp": _linear_macs(policy.mlp_extractor.value_net),
        "valueHead": _linear_macs(policy.value_net),
    }
    return {
        "assumptions": [
            "one valid observation row; multiply-accumulates only",
            "one shared CNN actor/critic feature pass",
            "LSTM uses 4*hidden*(input+hidden) per layer and direction",
            "bias, activations, normalization, recurrent padding, and backward excluded",
        ],
        "components": components,
        "inputShape": [int(value) for value in model.observation_space.shape],
        "total": sum(components.values()),
    }


def _instrument_measured_train(
    model: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any]:
    minibatches: list[dict[str, Any]] = []
    normalized_inputs: list[dict[str, Any]] = []
    buffer = model.rollout_buffer
    original_get = buffer.get

    def measured_get(batch_size: int | None = None) -> Any:
        for sample in original_get(batch_size):
            observation = sample.observations
            valid_rows = int((sample.mask > 1e-8).sum().item())
            minibatches.append(
                {
                    "mask": _array_metadata(sample.mask),
                    "observation": _array_metadata(observation),
                    "paddedRows": int(observation.shape[0]),
                    "validRows": valid_rows,
                }
            )
            yield sample

    def capture_normalized(_module: Any, inputs: tuple[Any, ...]) -> None:
        metadata = _array_metadata(inputs[0])
        metadata["boundary"] = "policy-preprocessed-normalized-image"
        normalized_inputs.append(metadata)

    buffer.get = measured_get
    hook = model.policy.features_extractor.register_forward_pre_hook(capture_normalized)

    def restore() -> None:
        hook.remove()
        buffer.get = original_get

    return minibatches, normalized_inputs, restore


def _learning_rate(model: Any) -> float:
    rates = {float(group["lr"]) for group in model.policy.optimizer.param_groups}
    if len(rates) != 1:
        raise RuntimeError(f"inconsistent optimizer learning rates: {sorted(rates)}")
    return rates.pop()


def _drive_two_updates(
    model: Any, env: Any, workload: ProfileWorkload
) -> dict[str, Any]:
    transitions_per_iteration = workload.n_envs * workload.n_steps
    setup_started = time.perf_counter()
    total_timesteps, callback = model._setup_learn(
        workload.schedule_horizon,
        callback=None,
        reset_num_timesteps=True,
        tb_log_name="resource-profile",
        progress_bar=False,
    )
    learn_setup_seconds = time.perf_counter() - setup_started
    one_step_output = _array_metadata(model._last_obs)
    iterations: list[dict[str, Any]] = []
    minibatches: list[dict[str, Any]] = []
    normalized_inputs: list[dict[str, Any]] = []
    warmup_ages: tuple[int, ...] = ()
    measurement_start_ns = 0
    measurement_end_ns = 0
    callback.on_training_start({}, {})
    try:
        for iteration_index, phase in enumerate(("warmup", "measured")):
            if phase == "measured":
                measurement_start_ns = time.perf_counter_ns()
            before = int(model.num_timesteps)
            collection_started = time.perf_counter()
            completed = model.collect_rollouts(
                env,
                callback,
                model.rollout_buffer,
                n_rollout_steps=workload.n_steps,
            )
            collection_seconds = time.perf_counter() - collection_started
            transitions = int(model.num_timesteps) - before
            if not completed or transitions != transitions_per_iteration:
                raise RuntimeError(
                    "profile collection did not complete exactly: "
                    f"completed={completed}, transitions={transitions}"
                )
            if iteration_index == 0:
                warmup_ages = env.maximum_valid_ages
            model._update_current_progress_remaining(
                model.num_timesteps, total_timesteps
            )
            restore = None
            if phase == "measured":
                minibatches, normalized_inputs, restore = _instrument_measured_train(
                    model
                )
            updates_before = int(model._n_updates)
            training_started = time.perf_counter()
            try:
                model.train()
            finally:
                training_seconds = time.perf_counter() - training_started
                if restore is not None:
                    restore()
            epoch_updates = int(model._n_updates) - updates_before
            if epoch_updates != workload.n_epochs:
                raise RuntimeError(
                    "profile training stopped before every epoch: "
                    f"expected={workload.n_epochs}, actual={epoch_updates}"
                )
            learning_rate = _learning_rate(model)
            if learning_rate <= 0:
                raise RuntimeError("profile update learning rate must remain positive")
            iterations.append(
                {
                    "collectionSeconds": collection_seconds,
                    "epochUpdates": epoch_updates,
                    "learningRate": learning_rate,
                    "phase": phase,
                    "trainingSeconds": training_seconds,
                    "transitions": transitions,
                }
            )
            if phase == "measured":
                measurement_end_ns = time.perf_counter_ns()
    finally:
        callback.on_training_end()
    return {
        "iterations": iterations,
        "learnSetupSeconds": learn_setup_seconds,
        "measurementWindow": {
            "endPerfCounterNs": measurement_end_ns,
            "startPerfCounterNs": measurement_start_ns,
        },
        "measuredNormalizedInputs": normalized_inputs,
        "measuredOptimizerMinibatches": minibatches,
        "oneStepOutput": one_step_output,
        "warmupMaximumValidAges": list(warmup_ages),
    }


def run_profile(
    *, history: Any, candidate: str, workload: ProfileWorkload
) -> dict[str, Any]:
    _activate_repo_imports()
    import torch

    from rl.protocol import TaskSpec, protocol_fingerprint
    from rl.training import (
        adjusted_batch_size,
        build_vector_env,
        compute_training_fingerprint,
        make_model,
    )

    if workload.torch_threads is not None:
        torch.set_num_threads(workload.torch_threads)
    if workload.torch_interop_threads is not None:
        torch.set_num_interop_threads(workload.torch_interop_threads)
    spec = TaskSpec()
    environment_started = time.perf_counter()
    env = build_vector_env(
        spec,
        n_envs=workload.n_envs,
        seed=workload.seed,
        history=history,
    )
    environment_setup_seconds = time.perf_counter() - environment_started
    try:
        model_started = time.perf_counter()
        model = make_model(
            env,
            seed=workload.seed,
            n_envs=workload.n_envs,
            device=workload.device,
            n_steps=workload.n_steps,
            n_epochs=workload.n_epochs,
        )
        model_setup_seconds = time.perf_counter() - model_started
        expected_batch_size = adjusted_batch_size(
            workload.n_envs * workload.n_steps, 64
        )
        if int(model.batch_size) != expected_batch_size:
            raise RuntimeError(
                f"unexpected recurrent batch size: {model.batch_size} != {expected_batch_size}"
            )
        if int(model.n_epochs) != workload.n_epochs:
            raise RuntimeError("model epoch count differs from profile workload")
        rollout_metadata = _array_metadata(model.rollout_buffer.observations)
        driven = _drive_two_updates(model, env, workload)
        expected_age = max(history.offsets)
        if driven["warmupMaximumValidAges"] != [expected_age] * workload.n_envs:
            raise RuntimeError(
                "warm-up did not populate the full history: "
                f"expected={expected_age}, actual={driven['warmupMaximumValidAges']}"
            )
        minibatches = driven["measuredOptimizerMinibatches"]
        normalized = driven["measuredNormalizedInputs"]
        if len(minibatches) != len(normalized):
            raise RuntimeError("raw and normalized minibatch captures disagree")
        valid_rows = sum(int(row["validRows"]) for row in minibatches)
        padded_rows = sum(int(row["paddedRows"]) for row in minibatches)
        expected_valid_rows = workload.n_envs * workload.n_steps * workload.n_epochs
        if valid_rows != expected_valid_rows:
            raise RuntimeError(
                f"optimizer valid-row mismatch: {valid_rows} != {expected_valid_rows}"
            )
        measured = driven["iterations"][1]
        collection_seconds = float(measured["collectionSeconds"])
        training_seconds = float(measured["trainingSeconds"])
        transitions = workload.n_envs * workload.n_steps
        return {
            "candidate": candidate,
            "expectedMaximumValidAge": expected_age,
            "history": history.to_dict(),
            "historyFingerprint": history.fingerprint(),
            "iterations": driven["iterations"],
            "measurementWindow": driven["measurementWindow"],
            "measuredNormalizedInputs": normalized,
            "measuredOptimizerMinibatches": minibatches,
            "model": {
                "inferenceForwardMacs": estimate_inference_forward_macs(model),
                "trainableParameters": sum(
                    int(parameter.numel())
                    for parameter in model.policy.parameters()
                    if parameter.requires_grad
                ),
            },
            "protocolFingerprint": protocol_fingerprint(),
            "rates": {
                "collectionFps": transitions / collection_seconds,
                "endToEndFps": transitions / (collection_seconds + training_seconds),
                "paddedOptimizerRows": padded_rows,
                "paddedOptimizerRowsPerSecond": padded_rows / training_seconds,
                "validOptimizerRows": valid_rows,
                "validOptimizerRowsPerSecond": valid_rows / training_seconds,
            },
            "schema": RESULT_SCHEMA,
            "setup": {
                "environmentSeconds": environment_setup_seconds,
                "learnSeconds": driven["learnSetupSeconds"],
                "modelSeconds": model_setup_seconds,
            },
            "storage": {
                "historyRingBytes": int(env.history_buffer_nbytes),
                "oneStepOutput": driven["oneStepOutput"],
                "rolloutBuffer": rollout_metadata,
            },
            "taskFingerprint": spec.fingerprint(),
            "trainingFingerprint": compute_training_fingerprint(REPO_ROOT),
            "warmupMaximumValidAges": driven["warmupMaximumValidAges"],
            "workload": {
                "batchSize": int(model.batch_size),
                "device": workload.device,
                "nEnvs": workload.n_envs,
                "nEpochs": workload.n_epochs,
                "nSteps": workload.n_steps,
                "scheduleHorizon": workload.schedule_horizon,
                "seed": workload.seed,
                "torchInteropThreads": workload.torch_interop_threads,
                "torchThreads": workload.torch_threads,
                "transitionsPerIteration": transitions,
            },
        }
    finally:
        env.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate",
        required=True,
        choices=("8-contiguous", "8-multiscale", "12-multiscale", "10-multiscale"),
    )
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--torch-threads", required=True, type=int)
    parser.add_argument("--torch-interop-threads", required=True, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    release_preimport_handshake()
    history = resolve_candidate(args.candidate)
    result = run_profile(
        history=history,
        candidate=args.candidate,
        workload=ProfileWorkload(
            seed=args.seed,
            torch_threads=args.torch_threads,
            torch_interop_threads=args.torch_interop_threads,
        ),
    )
    write_result_atomic(args.result, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
