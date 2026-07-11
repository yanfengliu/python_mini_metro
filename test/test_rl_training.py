import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.artifacts import write_artifact_index
from rl.evaluation import evaluate_vector_policy
from rl.manifest import RuntimeSnapshot, SourceSnapshot, create_training_manifest
from rl.protocol import FAST_RENDER_PROFILE, RewardMode, TaskSpec, protocol_fingerprint
from rl.training import (
    PPO_DEFAULTS,
    adjusted_batch_size,
    build_training_callbacks,
    build_vector_env,
    compute_content_fingerprint,
    compute_training_fingerprint,
    load_ppo_model,
    make_ppo,
    ppo_manifest_hyperparameters,
    select_base_vec_env_class,
    task_spec_from_manifest,
)

RL_DEPS_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("gymnasium", "stable_baselines3", "torch")
)


class TestTrainingConfiguration(unittest.TestCase):
    def test_ppo_defaults_and_batch_size_are_stable(self):
        self.assertEqual(PPO_DEFAULTS["n_steps"], 128)
        self.assertEqual(PPO_DEFAULTS["n_epochs"], 4)
        self.assertEqual(PPO_DEFAULTS["learning_rate"], 2.5e-4)
        self.assertEqual(PPO_DEFAULTS["gamma"], 0.999)
        self.assertEqual(PPO_DEFAULTS["gae_lambda"], 0.95)
        self.assertEqual(PPO_DEFAULTS["clip_range"], 0.1)
        self.assertEqual(PPO_DEFAULTS["ent_coef"], 0.01)
        self.assertEqual(PPO_DEFAULTS["vf_coef"], 0.5)
        self.assertEqual(PPO_DEFAULTS["max_grad_norm"], 0.5)
        self.assertEqual(adjusted_batch_size(128 * 8), 256)
        self.assertEqual(adjusted_batch_size(6), 6)

        recorded = ppo_manifest_hyperparameters(n_envs=8)
        self.assertEqual(recorded["batch_size"], 256)
        self.assertEqual(recorded["learning_rate_schedule"], "linear")
        self.assertEqual(recorded["policy"], "CnnPolicy")
        self.assertEqual(recorded["features_extractor"], "MiniMetroCNN")

    def test_manifest_reconstructs_the_exact_task(self):
        spec = TaskSpec(FAST_RENDER_PROFILE, 6, RewardMode.DELIVERIES)
        manifest = create_training_manifest(
            protocol_fingerprint=protocol_fingerprint(),
            task_fingerprint=spec.fingerprint(),
            content_fingerprint="content",
            training_fingerprint="training",
            algorithm="ppo",
            status="complete",
            render_profile=spec.render_profile.name,
            fixed_ticks=spec.fixed_ticks,
            reward_mode=spec.reward_mode.value,
            max_episode_steps=spec.max_episode_steps,
            frame_stack=4,
            seed=42,
            n_envs=1,
            timesteps=4,
            hyperparameters=ppo_manifest_hyperparameters(n_envs=1, n_steps=4),
            runtime=RuntimeSnapshot("3.13", "test", {}),
            source=SourceSnapshot(None, ()),
            command=("train",),
            artifacts={"final_model": "final_model.zip"},
            artifact_index_sha256="a" * 64,
        )

        reconstructed = task_spec_from_manifest(manifest)

        self.assertEqual(reconstructed, spec)

    def test_content_fingerprint_excludes_training_tooling_and_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src" / "rl").mkdir(parents=True)
            (root / "src" / "game.py").write_text("GAME = 1\n", encoding="utf-8")
            (root / "src" / "rl" / "protocol.py").write_text(
                "PROTOCOL = 1\n", encoding="utf-8"
            )
            (root / "src" / "rl" / "player_env.py").write_text(
                "ENV = 1\n", encoding="utf-8"
            )
            training_path = root / "src" / "rl" / "training.py"
            training_path.write_text("TRAINING = 1\n", encoding="utf-8")
            requirements_path = root / "requirements-rl.txt"
            requirements_path.write_text("tool==1\n", encoding="utf-8")
            baseline = compute_content_fingerprint(root)

            training_path.write_text("TRAINING = 2\n", encoding="utf-8")
            requirements_path.write_text("tool==2\n", encoding="utf-8")
            self.assertEqual(compute_content_fingerprint(root), baseline)

            (root / "src" / "rl" / "player_env.py").write_text(
                "ENV = 2\n", encoding="utf-8"
            )
            environment_changed = compute_content_fingerprint(root)
            self.assertNotEqual(environment_changed, baseline)

            (root / "assets").mkdir()
            (root / "assets" / "station.png").write_bytes(b"pixels")
            assets_changed = compute_content_fingerprint(root)
            self.assertNotEqual(assets_changed, environment_changed)

            (root / "content").mkdir()
            (root / "content" / "stations.json").write_text("{}\n", encoding="utf-8")
            self.assertNotEqual(compute_content_fingerprint(root), assets_changed)

    def test_training_fingerprint_tracks_trainer_and_dependency_inputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in (
                "environment.yml",
                "requirements-locked.txt",
                "requirements-rl-locked.txt",
                "requirements-rl.txt",
                "requirements.txt",
                "scripts/evaluate_rl.py",
                "scripts/train_rl.py",
                "src/rl/artifacts.py",
                "src/rl/evaluation.py",
                "src/rl/manifest.py",
                "src/rl/model.py",
                "src/rl/provenance.py",
                "src/rl/training.py",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{relative}\n", encoding="utf-8")
            baseline = compute_training_fingerprint(root)

            (root / "requirements-rl-locked.txt").write_text(
                "changed lock\n",
                encoding="utf-8",
            )
            self.assertNotEqual(compute_training_fingerprint(root), baseline)
            (root / "requirements-rl-locked.txt").write_text(
                "requirements-rl-locked.txt\n",
                encoding="utf-8",
            )
            (root / "src" / "rl" / "model.py").write_text("changed\n", encoding="utf-8")
            self.assertNotEqual(compute_training_fingerprint(root), baseline)

    def test_artifact_index_is_atomic_and_hashed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            model = run_dir / "model.zip"
            model.write_bytes(b"model")

            index_path = write_artifact_index(run_dir)
            document = json.loads(index_path.read_text(encoding="utf-8"))

            self.assertEqual(document["schema"], "mini-metro-artifacts-v1")
            self.assertEqual(document["files"]["model.zip"]["sizeBytes"], 5)
            self.assertEqual(list(run_dir.glob("*.tmp")), [])


@unittest.skipUnless(
    RL_DEPS_AVAILABLE, "Gymnasium, Stable-Baselines3, and Torch are optional"
)
class TestStableBaselinesTraining(unittest.TestCase):
    def test_compact_cnn_has_the_requested_output_shape(self):
        import gymnasium as gym
        import torch

        from rl.model import MiniMetroCNN

        space = gym.spaces.Box(low=0, high=255, shape=(12, 108, 192), dtype="uint8")
        extractor = MiniMetroCNN(space, features_dim=64)

        output = extractor(torch.zeros((2, 12, 108, 192), dtype=torch.float32))

        self.assertEqual(tuple(output.shape), (2, 64))
        self.assertLess(sum(p.numel() for p in extractor.parameters()), 1_000_000)

    def test_vector_env_is_seeded_and_wrapped_in_the_required_order(self):
        from stable_baselines3.common.vec_env import (
            DummyVecEnv,
            SubprocVecEnv,
            VecFrameStack,
            VecMonitor,
        )

        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 2)
        first = build_vector_env(spec, n_envs=1, seed=123, frame_stack=4)
        second = build_vector_env(spec, n_envs=1, seed=123, frame_stack=4)
        try:
            first_observation = first.reset()
            second_observation = second.reset()
            self.assertTrue((first_observation == second_observation).all())
            self.assertEqual(first_observation.shape, (1, 12, 108, 192))
            self.assertIsInstance(first, VecFrameStack)
            self.assertIsInstance(first.venv, VecMonitor)
            self.assertIsInstance(first.venv.venv, DummyVecEnv)
            self.assertIs(select_base_vec_env_class(2), SubprocVecEnv)
        finally:
            first.close()
            second.close()

    def test_short_learn_save_load_predict_round_trip(self):
        from stable_baselines3 import PPO

        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 4)
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
            model.learn(total_timesteps=4)
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = Path(temp_dir) / "model.zip"
                model.save(model_path)
                loaded = PPO.load(model_path, env=env, device="cpu")
                observation = env.reset()
                action, _ = loaded.predict(observation, deterministic=True)
                next_observation, _, _, _ = env.step(action)

            self.assertEqual(next_observation.shape, (1, 12, 108, 192))
        finally:
            env.close()

    def test_loaded_model_uses_requested_seed_and_in_memory_bytes(self):
        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 1)
        training_env = build_vector_env(spec, n_envs=1, seed=7, frame_stack=4)
        evaluation_env = build_vector_env(spec, n_envs=1, seed=99, frame_stack=4)
        try:
            model = make_ppo(
                training_env,
                seed=7,
                device="cpu",
                n_envs=1,
                n_steps=2,
                n_epochs=1,
                features_dim=32,
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = Path(temp_dir) / "model.zip"
                model.save(model_path)
                model_bytes = model_path.read_bytes()
                model_path.write_bytes(b"tampered-after-verification")
                loaded = load_ppo_model(
                    io.BytesIO(model_bytes),
                    env=evaluation_env,
                    device="cpu",
                    seed=99,
                )
                metrics = evaluate_vector_policy(
                    loaded,
                    evaluation_env,
                    episodes=1,
                )

            self.assertEqual(loaded.seed, 99)
            self.assertEqual(metrics[0].seed, 99)
        finally:
            evaluation_env.close()
            training_env.close()

    def test_training_evaluations_replay_the_recorded_seed_suite(self):
        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 1)
        training_env = build_vector_env(spec, n_envs=1, seed=7, frame_stack=4)
        evaluation_env = build_vector_env(spec, n_envs=1, seed=123, frame_stack=4)
        try:
            model = make_ppo(
                training_env,
                seed=7,
                device="cpu",
                n_envs=1,
                n_steps=2,
                n_epochs=1,
                features_dim=32,
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                callbacks = build_training_callbacks(
                    temp_dir,
                    eval_env=evaluation_env,
                    eval_seed=123,
                    n_envs=1,
                    checkpoint_every=2,
                    eval_every=2,
                    eval_episodes=2,
                )
                with patch.object(
                    evaluation_env,
                    "seed",
                    wraps=evaluation_env.seed,
                ) as seed:
                    model.learn(total_timesteps=4, callback=callbacks)

            self.assertEqual(seed.call_args_list, [unittest.mock.call(123)] * 2)
        finally:
            evaluation_env.close()
            training_env.close()


if __name__ == "__main__":
    unittest.main()
