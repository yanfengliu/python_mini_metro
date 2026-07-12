from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import rl.training as rl_training
from rl.evaluation import EpisodeMetrics
from rl.provenance import RuntimeSnapshot, SourceSnapshot


def load_train_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "train_rl.py"
    spec = importlib.util.spec_from_file_location("mini_metro_train_rl_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evaluate_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_rl.py"
    spec = importlib.util.spec_from_file_location("mini_metro_evaluate_rl_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeVectorEnv:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestTrainingCliLifecycle(unittest.TestCase):
    def test_unknown_algorithm_dispatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported algorithm"):
            rl_training.model_manifest_hyperparameters("unknown", n_envs=1)

    def test_partial_vector_construction_closes_started_workers(self) -> None:
        module = load_train_script()
        started = FakeVectorEnv()
        with tempfile.TemporaryDirectory() as temp_dir:
            args = module.build_parser().parse_args(
                ["--run-dir", str(Path(temp_dir) / "run"), "--n-envs", "2"]
            )
            patches = (
                patch.object(module, "require_rl_dependencies"),
                patch.object(module, "compute_content_fingerprint", return_value="c"),
                patch.object(module, "compute_training_fingerprint", return_value="t"),
                patch.object(
                    module,
                    "collect_runtime_snapshot",
                    return_value=RuntimeSnapshot("3.13", "test", {}),
                ),
                patch.object(
                    module,
                    "collect_source_snapshot",
                    return_value=SourceSnapshot(None, ()),
                ),
                patch.object(
                    module,
                    "build_vector_env",
                    side_effect=[started, RuntimeError("eval startup failed")],
                ),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
                with self.assertRaisesRegex(RuntimeError, "eval startup failed"):
                    module.run(args)

        self.assertTrue(started.closed)


class TestEvaluationCliSafety(unittest.TestCase):
    def test_objective_metadata_matches_the_saved_reward_contract(self) -> None:
        module = load_evaluate_script()

        self.assertEqual(
            module._objective_metadata("deliveries"),
            (
                "maximize total passengers delivered before game end",
                "meanDeliveries",
            ),
        )
        self.assertEqual(
            module._objective_metadata("display_score_delta"),
            ("maximize configured episodic reward", "meanReward"),
        )

    def test_termination_summary_distinguishes_complete_and_censored_deliveries(
        self,
    ) -> None:
        module = load_evaluate_script()
        metrics = (
            EpisodeMetrics(10.0, 100, 10, 10, 1, "game_over"),
            EpisodeMetrics(12.0, 120, 12, 12, 2, "horizon"),
            EpisodeMetrics(14.0, 120, 14, 14, 3, "horizon"),
        )

        self.assertEqual(
            module._summarize_terminations(metrics),
            {
                "deliveriesRightCensored": True,
                "gameOverEpisodes": 1,
                "gameOverRate": 1 / 3,
                "horizonTruncatedEpisodes": 2,
                "horizonTruncationRate": 2 / 3,
                "meanDeliveriesAmongGameOverEpisodes": 10.0,
                "otherTerminationEpisodes": 0,
                "terminationMetadataComplete": True,
            },
        )

        complete = module._summarize_terminations(
            (EpisodeMetrics(7.0, 70, 7, 7, 4, "game_over"),)
        )
        self.assertIs(complete["deliveriesRightCensored"], False)
        self.assertEqual(complete["meanDeliveriesAmongGameOverEpisodes"], 7.0)

        self.assertIn(
            "partial returns",
            module._primary_metric_interpretation("meanReward", censored=True),
        )
        self.assertIn(
            "mean final game-over delivery total",
            module._primary_metric_interpretation(
                "meanDeliveries",
                censored=False,
                termination_metadata_complete=True,
            ),
        )

        unknown = module._summarize_terminations(
            (EpisodeMetrics(3.0, 30, 3, 3, 5, None),)
        )
        self.assertEqual(unknown["otherTerminationEpisodes"], 1)
        self.assertIs(unknown["terminationMetadataComplete"], False)
        self.assertIn(
            "indeterminate",
            module._primary_metric_interpretation(
                "meanDeliveries",
                censored=False,
                termination_metadata_complete=False,
            ),
        )

    def test_default_seed_comes_from_manifest_and_explicit_seed_wins(self) -> None:
        module = load_evaluate_script()
        manifest = SimpleNamespace(
            seed=7,
            hyperparameters={"eval_seed": 10_007},
        )

        self.assertEqual(module._resolve_evaluation_seed(manifest, None), 10_007)
        self.assertEqual(module._resolve_evaluation_seed(manifest, 123), 123)
        manifest.hyperparameters = {"eval_seed": True}
        with self.assertRaisesRegex(ValueError, "eval_seed"):
            module._resolve_evaluation_seed(manifest, None)

    def test_output_cannot_overwrite_authenticated_inputs(self) -> None:
        module = load_evaluate_script()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model = root / "model.zip"
            manifest = root / "training-manifest.json"
            index = root / "artifact-index.json"
            protected = (model, manifest, index)
            for path in protected:
                path.write_bytes(b"input")
            for path in protected:
                with self.subTest(path=path):
                    with self.assertRaisesRegex(ValueError, "overwrite"):
                        module._validate_output_path(path, protected)

            output = root / "evaluation.json"
            self.assertEqual(
                module._validate_output_path(output, protected),
                output.resolve(),
            )

    def test_evaluation_rejects_source_drift_before_writing_results(self) -> None:
        module = load_evaluate_script()
        runtime = RuntimeSnapshot("3.13", "test", {"gymnasium": "1.3.0"})
        with patch.object(
            module,
            "compute_content_fingerprint",
            return_value="changed-content",
        ):
            with self.assertRaisesRegex(RuntimeError, "content changed"):
                module._ensure_evaluation_state_stable(
                    expected_content="content",
                    expected_training="training",
                    expected_runtime=runtime,
                )


if __name__ == "__main__":
    unittest.main()
