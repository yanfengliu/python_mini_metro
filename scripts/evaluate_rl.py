"""Evaluate a saved player-equivalent PPO run against its strict manifest."""

from __future__ import annotations

import argparse
import io
import multiprocessing
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rl.artifacts import (  # noqa: E402
    read_verified_indexed_artifact,
    write_json_atomic,
)
from rl.evaluation import evaluate_vector_policy  # noqa: E402
from rl.manifest import (  # noqa: E402
    RuntimeSnapshot,
    collect_runtime_snapshot,
    read_training_manifest_bytes,
    sha256_hex,
    validate_training_manifest,
)
from rl.protocol import protocol_fingerprint  # noqa: E402
from rl.provenance import runtime_compatibility_differences  # noqa: E402
from rl.training import (  # noqa: E402
    build_vector_env,
    compute_content_fingerprint,
    compute_training_fingerprint,
    load_ppo_model,
    require_rl_dependencies,
    task_spec_from_manifest,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a manifest-compatible Mini Metro PPO model."
    )
    parser.add_argument("model", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--episodes", type=_positive_int, default=10)
    parser.add_argument("--seed", type=_non_negative_int)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-content-drift",
        action="store_true",
        help="evaluate changed content and tag the result explicitly",
    )
    parser.add_argument(
        "--allow-training-drift",
        action="store_true",
        help="evaluate with changed trainer/model source and tag the result",
    )
    parser.add_argument(
        "--allow-runtime-drift",
        action="store_true",
        help="evaluate with changed compatibility dependencies and tag the result",
    )
    return parser


def _find_manifest(model_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    for parent in model_path.parents:
        candidate = parent / "training-manifest.json"
        if candidate.exists():
            return candidate
    return model_path.parent / "training-manifest.json"


def _resolve_evaluation_seed(manifest, explicit_seed: int | None) -> int:
    if explicit_seed is not None:
        return explicit_seed
    candidate = manifest.hyperparameters.get("eval_seed", manifest.seed + 10_000)
    if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate < 0:
        raise ValueError("manifest eval_seed must be a non-negative integer")
    return candidate


def _validate_output_path(
    output_path: str | Path,
    protected_paths: tuple[str | Path, ...],
) -> Path:
    resolved = Path(output_path).resolve()
    protected = {Path(path).resolve() for path in protected_paths}
    if resolved in protected:
        raise ValueError(
            f"evaluation output would overwrite authenticated input: {resolved}"
        )
    return resolved


def _ensure_evaluation_state_stable(
    *,
    expected_content: str,
    expected_training: str,
    expected_runtime: RuntimeSnapshot,
) -> None:
    final_content = compute_content_fingerprint(REPO_ROOT)
    if final_content != expected_content:
        raise RuntimeError("environment content changed during evaluation")
    final_training = compute_training_fingerprint(REPO_ROOT)
    if final_training != expected_training:
        raise RuntimeError("training source changed during evaluation")
    final_runtime = collect_runtime_snapshot()
    runtime_differences = runtime_compatibility_differences(
        expected_runtime,
        final_runtime,
    )
    if runtime_differences:
        raise RuntimeError(
            "runtime changed during evaluation: " + "; ".join(runtime_differences)
        )


def run(args: argparse.Namespace) -> Path:
    require_rl_dependencies()
    model_path = args.model.resolve()
    if not model_path.exists() and model_path.suffix != ".zip":
        model_path = model_path.with_suffix(".zip")
    if not model_path.is_file():
        raise ValueError(f"model does not exist: {model_path}")
    manifest_path = _find_manifest(model_path, args.manifest)
    manifest_payload = manifest_path.read_bytes()
    raw_manifest = read_training_manifest_bytes(manifest_payload)
    spec = task_spec_from_manifest(raw_manifest)
    current_content = compute_content_fingerprint(REPO_ROOT)
    current_training = compute_training_fingerprint(REPO_ROOT)
    current_runtime = collect_runtime_snapshot()
    manifest = validate_training_manifest(
        raw_manifest,
        expected_protocol_fingerprint=protocol_fingerprint(),
        expected_task_fingerprint=spec.fingerprint(),
        expected_content_fingerprint=current_content,
        allow_content_drift=args.allow_content_drift,
        expected_training_fingerprint=current_training,
        allow_training_drift=args.allow_training_drift,
        expected_runtime=current_runtime,
        allow_runtime_drift=args.allow_runtime_drift,
    )
    if manifest.algorithm != "ppo":
        raise ValueError("training manifest algorithm must be 'ppo'")
    verified_model = read_verified_indexed_artifact(
        model_path,
        manifest=manifest,
        manifest_path=manifest_path,
    )

    evaluation_seed = _resolve_evaluation_seed(manifest, args.seed)
    output_path = _validate_output_path(
        args.output or (model_path.parent / "evaluation.json"),
        (
            manifest_path,
            verified_model.index_path,
            *verified_model.indexed_paths,
        ),
    )
    env = build_vector_env(
        spec,
        n_envs=1,
        seed=evaluation_seed,
        frame_stack=manifest.frame_stack,
    )
    try:
        model = load_ppo_model(
            io.BytesIO(verified_model.content),
            env=env,
            seed=evaluation_seed,
            device=args.device,
        )
        episode_metrics = evaluate_vector_policy(
            model, env, episodes=args.episodes, deterministic=True
        )
    finally:
        env.close()

    _ensure_evaluation_state_stable(
        expected_content=current_content,
        expected_training=current_training,
        expected_runtime=current_runtime,
    )

    rewards = [item.reward for item in episode_metrics]
    lengths = [item.length for item in episode_metrics]
    deliveries = [item.deliveries for item in episode_metrics]
    display_scores = [item.display_score for item in episode_metrics]
    result = {
        "schema": "mini-metro-evaluation-v1",
        "algorithm": manifest.algorithm,
        "artifactIndex": {
            "path": manifest.artifacts["artifact_index"],
            "sha256": manifest.artifact_index_sha256,
        },
        "compatibilityTags": list(manifest.tags),
        "currentContentFingerprint": current_content,
        "currentTrainingFingerprint": current_training,
        "currentRuntime": current_runtime.to_dict(),
        "deterministic": True,
        "episodeLengths": lengths,
        "episodeMetrics": [item.to_dict() for item in episode_metrics],
        "episodeRewards": rewards,
        "episodes": args.episodes,
        "manifest": str(manifest_path),
        "manifestSha256": sha256_hex(manifest_payload),
        "meanEpisodeLength": statistics.fmean(lengths),
        "meanDeliveries": statistics.fmean(deliveries),
        "meanDisplayScore": statistics.fmean(display_scores),
        "meanReward": statistics.fmean(rewards),
        "model": dict(verified_model.metadata),
        "protocolFingerprint": manifest.protocol_fingerprint,
        "savedContentFingerprint": manifest.content_fingerprint,
        "runtimeDifferences": list(
            runtime_compatibility_differences(manifest.runtime, current_runtime)
        ),
        "seed": evaluation_seed,
        "stdReward": statistics.pstdev(rewards),
        "taskFingerprint": manifest.task_fingerprint,
        "trainingStatus": manifest.status,
    }
    return write_json_atomic(output_path, result)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result_path = run(args)
    except (RuntimeError, ValueError, OSError) as error:
        parser.error(str(error))
    print(f"evaluation result: {result_path}")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
