from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.artifacts import sha256_file, write_artifact_index
from rl.manifest import (
    CROSS_RUNTIME_TAG,
    CROSS_TRAINING_TAG,
    ManifestCompatibilityError,
    RuntimeSnapshot,
    SourceSnapshot,
    collect_runtime_snapshot,
    create_training_manifest,
    write_training_manifest,
)
from rl.protocol import FAST_RENDER_PROFILE, RewardMode, TaskSpec, protocol_fingerprint
from rl.training import (
    build_vector_env,
    compute_content_fingerprint,
    make_ppo,
    ppo_manifest_hyperparameters,
)

RL_DEPS_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("gymnasium", "sb3_contrib", "stable_baselines3", "torch")
)


def load_evaluate_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_rl.py"
    spec = importlib.util.spec_from_file_location(
        "mini_metro_evaluate_rl_legacy_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(
    RL_DEPS_AVAILABLE,
    "Gymnasium, sb3-contrib, Stable-Baselines3, and Torch are optional",
)
class TestLegacyPpoCompatibility(unittest.TestCase):
    def test_pre_recurrent_ppo_artifact_requires_both_drift_opt_ins(self):
        module = load_evaluate_script()
        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 1)
        current_runtime = collect_runtime_snapshot()
        old_packages = dict(current_runtime.package_versions)
        old_packages.pop("sb3-contrib")
        old_runtime = RuntimeSnapshot(
            current_runtime.python_version,
            current_runtime.platform_name,
            old_packages,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "pre-recurrent-ppo"
            run_dir.mkdir()
            model_path = run_dir / "final_model.zip"
            env = build_vector_env(spec, n_envs=1, seed=7, frame_stack=4)
            try:
                model = make_ppo(
                    env,
                    seed=7,
                    device="cpu",
                    n_envs=1,
                    n_steps=2,
                    n_epochs=1,
                    features_dim=32,
                )
                model.save(model_path)
            finally:
                env.close()

            index_path = write_artifact_index(run_dir, "artifact-index.json")
            manifest = create_training_manifest(
                protocol_fingerprint=protocol_fingerprint(),
                task_fingerprint=spec.fingerprint(),
                content_fingerprint=compute_content_fingerprint(module.REPO_ROOT),
                training_fingerprint="pre-recurrent-training-source",
                algorithm="ppo",
                status="complete",
                render_profile=spec.render_profile.name,
                fixed_ticks=spec.fixed_ticks,
                reward_mode=spec.reward_mode.value,
                max_episode_steps=spec.max_episode_steps,
                frame_stack=4,
                seed=7,
                n_envs=1,
                timesteps=0,
                hyperparameters={
                    **ppo_manifest_hyperparameters(
                        n_envs=1,
                        n_steps=2,
                        n_epochs=1,
                        features_dim=32,
                    ),
                    "eval_seed": 107,
                },
                runtime=old_runtime,
                source=SourceSnapshot(None, ()),
                command=("python", "scripts/train_rl.py"),
                artifacts={
                    "artifact_index": "artifact-index.json",
                    "final_model": "final_model.zip",
                },
                artifact_index_sha256=sha256_file(index_path),
            )
            manifest_path = write_training_manifest(run_dir, manifest)
            base_arguments = [
                str(model_path),
                "--manifest",
                str(manifest_path),
                "--episodes",
                "1",
                "--device",
                "cpu",
            ]

            with self.assertRaisesRegex(ManifestCompatibilityError, "training"):
                module.run(module.build_parser().parse_args(base_arguments))
            with self.assertRaisesRegex(ManifestCompatibilityError, "runtime"):
                module.run(
                    module.build_parser().parse_args(
                        [*base_arguments, "--allow-training-drift"]
                    )
                )
            with self.assertRaisesRegex(ManifestCompatibilityError, "training"):
                module.run(
                    module.build_parser().parse_args(
                        [*base_arguments, "--allow-runtime-drift"]
                    )
                )

            result_path = module.run(
                module.build_parser().parse_args(
                    [
                        *base_arguments,
                        "--allow-training-drift",
                        "--allow-runtime-drift",
                    ]
                )
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))

        self.assertEqual(result["algorithm"], "ppo")
        self.assertEqual(
            set(result["compatibilityTags"]),
            {CROSS_RUNTIME_TAG, CROSS_TRAINING_TAG},
        )
        self.assertIs(result["deliveriesRightCensored"], True)


if __name__ == "__main__":
    unittest.main()
