"""Train a player-equivalent pixel policy with Stable-Baselines3."""

from __future__ import annotations

import argparse
import io
import multiprocessing
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rl.artifacts import (  # noqa: E402
    read_verified_indexed_artifact,
    sha256_file,
    write_artifact_index,
)
from rl.history import (  # noqa: E402
    NAMED_HISTORY_LAYOUTS,
    HistoryDescriptor,
    contiguous_history,
    history_for_layout,
)
from rl.manifest import (  # noqa: E402
    TrainingManifest,
    collect_runtime_snapshot,
    collect_source_snapshot,
    create_training_manifest,
    read_training_manifest_bytes,
    sha256_hex,
    validate_training_manifest,
    write_training_manifest,
)
from rl.protocol import (  # noqa: E402
    DEFAULT_FIXED_TICKS,
    DEFAULT_MAX_EPISODE_STEPS,
    FAST_RENDER_PROFILE,
    RENDER_PROFILES,
    RewardMode,
    TaskSpec,
    protocol_fingerprint,
)
from rl.training import (  # noqa: E402
    DEFAULT_ALGORITHM,
    DEFAULT_FRAME_STACK,
    SUPPORTED_ALGORITHMS,
    build_training_callbacks,
    build_vector_env,
    compute_content_fingerprint,
    compute_training_fingerprint,
    load_model,
    make_model,
    model_manifest_hyperparameters,
    require_rl_dependencies,
    resolve_render_profile,
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
        description="Train a policy from the same pixels and controls used by a player."
    )
    parser.add_argument("--total-timesteps", type=_positive_int, default=1_000_000)
    parser.add_argument("--seed", type=_non_negative_int, default=42)
    parser.add_argument(
        "--eval-seed",
        type=_non_negative_int,
        help="separate evaluation seed (default: training seed + 10000)",
    )
    parser.add_argument("--n-envs", type=_positive_int, default=8)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--algorithm", choices=SUPPORTED_ALGORITHMS)
    parser.add_argument(
        "--render-profile",
        choices=[profile.name for profile in RENDER_PROFILES],
        default=FAST_RENDER_PROFILE.name,
    )
    parser.add_argument(
        "--fixed-ticks", type=_positive_int, default=DEFAULT_FIXED_TICKS
    )
    parser.add_argument(
        "--reward-mode",
        choices=[mode.value for mode in RewardMode],
        default=RewardMode.DELIVERIES.value,
    )
    history_group = parser.add_mutually_exclusive_group()
    history_group.add_argument(
        "--frame-stack",
        type=_positive_int,
        help="contiguous observation frames (default: 8 for fresh runs)",
    )
    history_group.add_argument(
        "--history-layout",
        choices=NAMED_HISTORY_LAYOUTS,
        help="reviewed multiscale observation-history layout",
    )
    parser.add_argument(
        "--max-episode-steps",
        type=_positive_int,
        default=DEFAULT_MAX_EPISODE_STEPS,
    )
    parser.add_argument("--checkpoint-every", type=_positive_int, default=100_000)
    parser.add_argument("--eval-every", type=_positive_int, default=100_000)
    parser.add_argument("--eval-episodes", type=_positive_int, default=5)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--resume", type=Path, help="model zip to continue training")
    parser.add_argument(
        "--resume-manifest",
        type=Path,
        help="manifest for --resume (default: next to model)",
    )
    parser.add_argument(
        "--allow-content-drift",
        action="store_true",
        help="explicitly allow resuming on changed game content",
    )
    parser.add_argument(
        "--allow-training-drift",
        action="store_true",
        help="explicitly allow resuming with changed trainer/model source",
    )
    parser.add_argument(
        "--allow-runtime-drift",
        action="store_true",
        help="explicitly allow resuming with changed compatibility dependencies",
    )
    return parser


def _default_run_dir(seed: int, algorithm: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return REPO_ROOT / "output" / "rl" / f"{algorithm}-{timestamp}-seed-{seed}"


def _requested_history(
    *,
    frame_stack: int | None,
    history_layout: str | None,
) -> HistoryDescriptor | None:
    if frame_stack is not None and history_layout is not None:
        raise ValueError("frame_stack and history_layout cannot be combined")
    if history_layout is not None:
        return history_for_layout(history_layout)
    if frame_stack is not None:
        return contiguous_history(frame_stack)
    return None


def _resolve_algorithm_and_history(
    *,
    requested_algorithm: str | None,
    requested_history: HistoryDescriptor | None,
    resume_manifest: TrainingManifest | None,
) -> tuple[str, HistoryDescriptor]:
    """Resolve fresh defaults or require resume settings to match the artifact."""

    if resume_manifest is None:
        algorithm = requested_algorithm or DEFAULT_ALGORITHM
        if algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"unsupported algorithm: {algorithm!r}")
        history = requested_history or contiguous_history(DEFAULT_FRAME_STACK)
        return algorithm, history

    saved_algorithm = resume_manifest.algorithm
    if saved_algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"unsupported algorithm in resume manifest: {saved_algorithm!r}"
        )
    if requested_algorithm is not None and requested_algorithm != saved_algorithm:
        raise ValueError(
            "resume algorithm mismatch: "
            f"saved={saved_algorithm}, requested={requested_algorithm}"
        )
    saved_history = resume_manifest.history
    if (
        requested_history is not None
        and requested_history.fingerprint() != saved_history.fingerprint()
    ):
        raise ValueError(
            "resume history mismatch: "
            f"saved={saved_history.layout!r}, requested={requested_history.layout!r}"
        )
    return saved_algorithm, saved_history


def _resume_manifest_path(model_path: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    candidate = model_path.parent / "training-manifest.json"
    if candidate.exists():
        return candidate
    for parent in model_path.parents:
        candidate = parent / "training-manifest.json"
        if candidate.exists():
            return candidate
    return model_path.parent / "training-manifest.json"


def run(args: argparse.Namespace) -> Path:
    requested_history = _requested_history(
        frame_stack=args.frame_stack,
        history_layout=args.history_layout,
    )
    require_rl_dependencies()
    eval_seed = args.eval_seed if args.eval_seed is not None else args.seed + 10_000
    spec = TaskSpec(
        resolve_render_profile(args.render_profile),
        args.fixed_ticks,
        args.reward_mode,
        args.max_episode_steps,
    )
    content_fingerprint = compute_content_fingerprint(REPO_ROOT)
    training_fingerprint = compute_training_fingerprint(REPO_ROOT)
    runtime_snapshot = collect_runtime_snapshot()
    source_snapshot = collect_source_snapshot(REPO_ROOT)
    resume_manifest = None
    resume_model_path: Path | None = None
    resume_model_content: bytes | None = None
    parent_manifest_sha256 = None
    parent_model_sha256 = None
    tags: tuple[str, ...] = ()

    if args.resume is not None:
        resume_model_path = args.resume.resolve()
        manifest_path = _resume_manifest_path(resume_model_path, args.resume_manifest)
        manifest_payload = manifest_path.read_bytes()
        parsed_resume_manifest = read_training_manifest_bytes(manifest_payload)
        algorithm, history = _resolve_algorithm_and_history(
            requested_algorithm=args.algorithm,
            requested_history=requested_history,
            resume_manifest=parsed_resume_manifest,
        )
        resume_manifest = validate_training_manifest(
            parsed_resume_manifest,
            expected_protocol_fingerprint=protocol_fingerprint(),
            expected_task_fingerprint=spec.fingerprint(),
            expected_history_fingerprint=history.fingerprint(),
            expected_content_fingerprint=content_fingerprint,
            allow_content_drift=args.allow_content_drift,
            expected_training_fingerprint=training_fingerprint,
            allow_training_drift=args.allow_training_drift,
            expected_runtime=runtime_snapshot,
            allow_runtime_drift=args.allow_runtime_drift,
        )
        if task_spec_from_manifest(resume_manifest) != spec:
            raise ValueError("resume manifest task fields do not match requested task")
        verified_parent = read_verified_indexed_artifact(
            resume_model_path,
            manifest=resume_manifest,
            manifest_path=manifest_path,
        )
        parent_manifest_sha256 = sha256_hex(manifest_payload)
        parent_model_sha256 = str(verified_parent.metadata["sha256"])
        resume_model_content = verified_parent.content
        tags = tuple(sorted({*resume_manifest.tags, "resumed-training"}))
    else:
        algorithm, history = _resolve_algorithm_and_history(
            requested_algorithm=args.algorithm,
            requested_history=requested_history,
            resume_manifest=None,
        )
    hyperparameters = (
        dict(resume_manifest.hyperparameters)
        if resume_manifest is not None
        else model_manifest_hyperparameters(algorithm, n_envs=args.n_envs)
    )
    run_dir = (args.run_dir or _default_run_dir(args.seed, algorithm)).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    tensorboard_dir = run_dir / "tensorboard"
    tensorboard_dir.mkdir(parents=True, exist_ok=True)
    train_env = None
    eval_env = None
    try:
        train_env = build_vector_env(
            spec,
            n_envs=args.n_envs,
            seed=args.seed,
            history=history,
        )
        eval_env = build_vector_env(
            spec,
            n_envs=1,
            seed=eval_seed,
            history=history,
        )
        if args.resume is None:
            model = make_model(
                train_env,
                algorithm=algorithm,
                seed=args.seed,
                n_envs=args.n_envs,
                device=args.device,
                tensorboard_log=tensorboard_dir,
                verbose=1,
            )
            reset_num_timesteps = True
        else:
            assert resume_model_path is not None
            assert resume_model_content is not None
            model = load_model(
                io.BytesIO(resume_model_content),
                algorithm=algorithm,
                env=train_env,
                seed=args.seed,
                device=args.device,
            )
            model.tensorboard_log = str(tensorboard_dir)
            reset_num_timesteps = False
        artifacts = {
            "best_models": "best/",
            "checkpoints": "checkpoints/",
            "evaluations": "evaluations/",
            "final_model": "final_model.zip",
            "tensorboard": "tensorboard/",
        }
        recorded_hyperparameters = {
            **hyperparameters,
            "checkpoint_every": args.checkpoint_every,
            "device_requested": args.device,
            "device_resolved": str(model.device),
            "eval_episodes": args.eval_episodes,
            "eval_every": args.eval_every,
            "eval_seed": eval_seed,
            "total_timesteps_requested": args.total_timesteps,
        }
        manifest_generation = 0

        def persist_manifest(status: str) -> Path:
            nonlocal manifest_generation
            if compute_content_fingerprint(REPO_ROOT) != content_fingerprint:
                raise RuntimeError("environment content changed during training")
            if compute_training_fingerprint(REPO_ROOT) != training_fingerprint:
                raise RuntimeError("training source changed during training")
            index_relative = (
                "artifact-indexes/"
                f"{int(model.num_timesteps)}-{manifest_generation}.json"
            )
            manifest_generation += 1
            index_path = write_artifact_index(run_dir, index_relative)
            manifest = create_training_manifest(
                protocol_fingerprint=protocol_fingerprint(),
                task_fingerprint=spec.fingerprint(),
                content_fingerprint=content_fingerprint,
                training_fingerprint=training_fingerprint,
                algorithm=algorithm,
                status=status,
                render_profile=spec.render_profile.name,
                fixed_ticks=spec.fixed_ticks,
                reward_mode=spec.reward_mode.value,
                max_episode_steps=spec.max_episode_steps,
                history=history,
                seed=args.seed,
                n_envs=args.n_envs,
                timesteps=int(model.num_timesteps),
                hyperparameters=recorded_hyperparameters,
                runtime=runtime_snapshot,
                source=source_snapshot,
                command=(sys.executable, *sys.argv),
                artifacts={**artifacts, "artifact_index": index_relative},
                artifact_index_sha256=sha256_file(index_path),
                tags=tags,
                parent_manifest_sha256=parent_manifest_sha256,
                parent_model_sha256=parent_model_sha256,
            )
            return write_training_manifest(run_dir, manifest)

        callbacks = build_training_callbacks(
            run_dir,
            eval_env=eval_env,
            eval_seed=eval_seed,
            n_envs=args.n_envs,
            checkpoint_every=args.checkpoint_every,
            eval_every=args.eval_every,
            eval_episodes=args.eval_episodes,
            algorithm=algorithm,
            after_checkpoint=lambda _timesteps: persist_manifest("running"),
        )
        checkpoint_prefix = f"mini_metro_{algorithm}"
        recovery_model = (
            run_dir
            / "checkpoints"
            / f"{checkpoint_prefix}_{int(model.num_timesteps)}_steps.zip"
        )
        model.save(recovery_model)
        manifest_path = persist_manifest("running")
        model.learn(
            total_timesteps=args.total_timesteps,
            callback=callbacks,
            reset_num_timesteps=reset_num_timesteps,
            tb_log_name=algorithm,
        )
        final_model = run_dir / "final_model.zip"
        model.save(final_model)
        manifest_path = persist_manifest("complete")
    finally:
        if eval_env is not None:
            eval_env.close()
        if train_env is not None:
            train_env.close()
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.resume_manifest is not None and args.resume is None:
        parser.error("--resume-manifest requires --resume")
    try:
        manifest_path = run(args)
    except (RuntimeError, ValueError, OSError) as error:
        parser.error(str(error))
    print(f"training manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
