from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, call, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import rl.training as rl_training
from rl.history import (
    DECISION_HISTORY_LAYOUT,
    EIGHT_MULTISCALE_HISTORY_LAYOUT,
    contiguous_history,
    default_history,
    history_for_layout,
)
from rl.protocol import FAST_RENDER_PROFILE, RewardMode, TaskSpec
from rl.provenance import RuntimeSnapshot, SourceSnapshot


def load_script(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}_rl.py"
    spec = importlib.util.spec_from_file_location(
        f"mini_metro_{name}_rl_history_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeVectorEnv:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestHistoryCliResolution(unittest.TestCase):
    def test_vector_builder_rejects_two_history_sources_before_startup(self):
        spec = TaskSpec(FAST_RENDER_PROFILE, 1, RewardMode.DELIVERIES, 1)
        with patch.object(
            rl_training,
            "require_rl_dependencies",
            side_effect=AssertionError("dependencies must not be touched"),
        ):
            with self.assertRaisesRegex(ValueError, "cannot be combined"):
                rl_training.build_vector_env(
                    spec,
                    n_envs=1,
                    seed=1,
                    history=contiguous_history(4),
                    frame_stack=4,
                )

    def test_parser_and_resolver_produce_one_exact_history_descriptor(self) -> None:
        module = load_script("train")
        named = history_for_layout(DECISION_HISTORY_LAYOUT)

        self.assertIsNone(
            module._requested_history(frame_stack=None, history_layout=None)
        )
        self.assertEqual(
            module._requested_history(frame_stack=13, history_layout=None),
            contiguous_history(13),
        )
        self.assertEqual(
            module._requested_history(
                frame_stack=None,
                history_layout=DECISION_HISTORY_LAYOUT,
            ),
            named,
        )
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            module._requested_history(
                frame_stack=12,
                history_layout=DECISION_HISTORY_LAYOUT,
            )

        parser = module.build_parser()
        invalid_arguments = (
            (
                "--frame-stack",
                "12",
                "--history-layout",
                DECISION_HISTORY_LAYOUT,
            ),
            ("--history-layout", "unreviewed-history-v1"),
        )
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                    parser.parse_args(arguments)

        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm=None,
                requested_history=None,
                resume_manifest=None,
            ),
            ("recurrent_ppo", default_history()),
        )
        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm="ppo",
                requested_history=None,
                resume_manifest=None,
            ),
            ("ppo", contiguous_history(8)),
        )
        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm="ppo",
                requested_history=named,
                resume_manifest=None,
            ),
            ("ppo", named),
        )

    def test_resume_inherits_exact_history_and_rejects_semantic_mismatch(self) -> None:
        module = load_script("train")
        saved = history_for_layout(DECISION_HISTORY_LAYOUT)
        resume_manifest = SimpleNamespace(algorithm="ppo", history=saved)

        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm=None,
                requested_history=None,
                resume_manifest=resume_manifest,
            ),
            ("ppo", saved),
        )
        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm=None,
                requested_history=saved,
                resume_manifest=resume_manifest,
            ),
            ("ppo", saved),
        )
        with self.assertRaisesRegex(ValueError, "algorithm mismatch"):
            module._resolve_algorithm_and_history(
                requested_algorithm="recurrent_ppo",
                requested_history=None,
                resume_manifest=resume_manifest,
            )
        with self.assertRaisesRegex(ValueError, "history mismatch"):
            module._resolve_algorithm_and_history(
                requested_algorithm=None,
                requested_history=contiguous_history(12),
                resume_manifest=resume_manifest,
            )

        legacy = SimpleNamespace(algorithm="ppo", history=contiguous_history(13))
        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm=None,
                requested_history=None,
                resume_manifest=legacy,
            ),
            ("ppo", contiguous_history(13)),
        )
        self.assertEqual(
            module._resolve_algorithm_and_history(
                requested_algorithm=None,
                requested_history=contiguous_history(13),
                resume_manifest=legacy,
            ),
            ("ppo", contiguous_history(13)),
        )

    def test_resume_history_mismatch_fails_before_validation_or_artifact_open(self):
        module = load_script("train")
        saved = history_for_layout(DECISION_HISTORY_LAYOUT)
        raw_manifest = SimpleNamespace(algorithm="recurrent_ppo", history=saved)
        runtime = RuntimeSnapshot("3.13", "test", {})
        source = SourceSnapshot(None, ())
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model = root / "model.zip"
            manifest = root / "training-manifest.json"
            model.write_bytes(b"model")
            manifest.write_bytes(b"manifest")
            args = module.build_parser().parse_args(
                [
                    "--resume",
                    str(model),
                    "--resume-manifest",
                    str(manifest),
                    "--frame-stack",
                    "12",
                    "--run-dir",
                    str(root / "run"),
                ]
            )
            with (
                patch.object(module, "require_rl_dependencies"),
                patch.object(module, "compute_content_fingerprint", return_value="c"),
                patch.object(module, "compute_training_fingerprint", return_value="t"),
                patch.object(module, "collect_runtime_snapshot", return_value=runtime),
                patch.object(module, "collect_source_snapshot", return_value=source),
                patch.object(
                    module,
                    "read_training_manifest_bytes",
                    return_value=raw_manifest,
                ),
                patch.object(module, "validate_training_manifest") as validate,
                patch.object(module, "read_verified_indexed_artifact") as verify,
            ):
                with self.assertRaisesRegex(ValueError, "history mismatch"):
                    module.run(args)

        validate.assert_not_called()
        verify.assert_not_called()

    def test_fresh_default_and_named_history_reach_both_vector_environments(
        self,
    ) -> None:
        module = load_script("train")
        runtime = RuntimeSnapshot("3.13", "test", {})
        source = SourceSnapshot(None, ())
        cases = (
            ((), default_history()),
            (
                ("--history-layout", EIGHT_MULTISCALE_HISTORY_LAYOUT),
                history_for_layout(EIGHT_MULTISCALE_HISTORY_LAYOUT),
            ),
        )
        for selectors, history in cases:
            with (
                self.subTest(selectors=selectors),
                tempfile.TemporaryDirectory() as temp_dir,
            ):
                started = FakeVectorEnv()
                args = module.build_parser().parse_args(
                    [*selectors, "--run-dir", str(Path(temp_dir) / "run")]
                )
                with (
                    patch.object(module, "require_rl_dependencies"),
                    patch.object(
                        module, "compute_content_fingerprint", return_value="c"
                    ),
                    patch.object(
                        module, "compute_training_fingerprint", return_value="t"
                    ),
                    patch.object(
                        module, "collect_runtime_snapshot", return_value=runtime
                    ),
                    patch.object(
                        module, "collect_source_snapshot", return_value=source
                    ),
                    patch.object(
                        module,
                        "build_vector_env",
                        side_effect=[started, RuntimeError("stop after both builds")],
                    ) as build,
                ):
                    with self.assertRaisesRegex(RuntimeError, "both builds"):
                        module.run(args)

                self.assertEqual(
                    build.call_args_list,
                    [
                        call(ANY, n_envs=8, seed=42, history=history),
                        call(ANY, n_envs=1, seed=10_042, history=history),
                    ],
                )
                self.assertTrue(started.closed)

    def test_evaluation_authenticates_then_builds_exact_manifest_history(self):
        module = load_script("evaluate")
        history = history_for_layout(DECISION_HISTORY_LAYOUT)
        task = SimpleNamespace(fingerprint=lambda: "task")
        manifest = SimpleNamespace(
            algorithm="recurrent_ppo",
            artifacts={"artifact_index": "artifact-index.json"},
            history=history,
            hyperparameters={"eval_seed": 107},
            seed=7,
        )
        runtime = RuntimeSnapshot("3.13", "test", {})
        events: list[str] = []
        env = FakeVectorEnv()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model = root / "model.zip"
            manifest_path = root / "training-manifest.json"
            model.write_bytes(b"model")
            manifest_path.write_bytes(b"manifest")
            args = module.build_parser().parse_args(
                [str(model), "--manifest", str(manifest_path)]
            )
            verified = SimpleNamespace(
                content=b"model",
                index_path=root / "artifact-index.json",
                indexed_paths=(),
            )

            def verify(*args, **kwargs):
                events.append("verify")
                return verified

            def build(*args, **kwargs):
                events.append("build")
                return env

            def evaluate(*args, **kwargs):
                events.append("evaluate")
                raise RuntimeError("stop after evaluation dispatch")

            with (
                patch.object(module, "require_rl_dependencies"),
                patch.object(
                    module, "read_training_manifest_bytes", return_value=manifest
                ),
                patch.object(module, "task_spec_from_manifest", return_value=task),
                patch.object(module, "compute_content_fingerprint", return_value="c"),
                patch.object(module, "compute_training_fingerprint", return_value="t"),
                patch.object(module, "collect_runtime_snapshot", return_value=runtime),
                patch.object(
                    module, "validate_training_manifest", return_value=manifest
                ),
                patch.object(
                    module, "read_verified_indexed_artifact", side_effect=verify
                ),
                patch.object(module, "_validate_output_path", return_value=root / "e"),
                patch.object(module, "build_vector_env", side_effect=build) as builder,
                patch.object(module, "load_model", return_value=object()),
                patch.object(module, "evaluate_vector_policy", side_effect=evaluate),
            ):
                with self.assertRaisesRegex(RuntimeError, "evaluation dispatch"):
                    module.run(args)

        self.assertEqual(events, ["verify", "build", "evaluate"])
        builder.assert_called_once_with(task, n_envs=1, seed=107, history=history)
        self.assertTrue(env.closed)


if __name__ == "__main__":
    unittest.main()
