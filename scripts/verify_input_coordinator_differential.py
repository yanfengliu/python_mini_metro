from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import input_coordinator_differential_actions as action_cases
import input_coordinator_differential_input as input_cases
import input_coordinator_differential_support as support

BASELINE_REF = "7ff9d9c4e0cee91898d84ce29c13641201f6ac83"
SCENARIO_VERSION = "gm03f-input-coordinator-v2"
ARTIFACT_NAME = "input-coordinator-differential.json"
SUMMARY_NAME = "input-coordinator-differential-summary.json"
EXPECTED_CASE_COUNT = 3
EXPECTED_RECORD_COUNT = 11
EXPECTED_EVENT_COUNT = 57


def _verifier_sources() -> tuple[Path, ...]:
    return tuple(
        Path(module.__file__).resolve()
        for module in (
            sys.modules[__name__],
            action_cases,
            input_cases,
            support,
        )
    )


def _assert_module_origins(source_root: Path) -> dict[str, str]:
    source_names = {path.stem for path in source_root.glob("*.py")}
    source_names.update(
        path.name
        for path in source_root.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    )
    origins: dict[str, str] = {}
    for name, module in sorted(sys.modules.items()):
        if name.split(".", 1)[0] not in source_names:
            continue
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            continue
        resolved = Path(module_file).resolve()
        if not resolved.is_relative_to(source_root):
            raise RuntimeError(
                f"target module {name} loaded from {resolved}, not {source_root}"
            )
        origins[name] = resolved.relative_to(source_root).as_posix()
    required = {
        "config",
        "event.event",
        "event.keyboard",
        "event.mouse",
        "event.type",
        "mediator",
        "passenger_flow",
        "path_lifecycle",
        "progression",
        "ui.button",
        "ui.path_button",
        "ui.speed_button",
    }
    if (source_root / "input_coordinator.py").is_file():
        required.add("input_coordinator")
    missing = sorted(required.difference(origins))
    if missing:
        raise RuntimeError(f"target modules were not loaded: {', '.join(missing)}")
    return {name: origins[name] for name in sorted(required)}


def _emit_target(source_root: Path, output: Path) -> None:
    source_root = source_root.resolve()
    sys.path.insert(0, str(source_root))
    import mediator as mediator_module

    if not Path(mediator_module.__file__).resolve().is_relative_to(source_root):
        raise RuntimeError("mediator did not load from the requested source root")
    cases = [
        input_cases.run_input_case(),
        action_cases.run_progression_case(),
        action_cases.run_action_case(),
    ]
    case_count = len(cases)
    record_count = sum(len(case["records"]) for case in cases)
    event_count = sum(len(case["events"]) for case in cases)
    _assert_module_origins(source_root)
    result = {
        "caseCount": case_count,
        "cases": cases,
        "eventCount": event_count,
        "recordCount": record_count,
        "scenarioVersion": SCENARIO_VERSION,
        "schemaVersion": 1,
    }
    actual = (case_count, record_count, event_count)
    expected = (EXPECTED_CASE_COUNT, EXPECTED_RECORD_COUNT, EXPECTED_EVENT_COUNT)
    if actual != expected:
        raise AssertionError(
            "scenario case/record/event cardinality changed: "
            f"expected {expected}, got {actual}"
        )
    output.write_bytes(support.json_bytes(result))


def _run_child(script: Path, root: Path, output: Path) -> dict[str, Any]:
    source_root = root / "src"
    sources = _verifier_sources()
    runtime_pre = support.runtime_tree_sha256(source_root)
    verifier_pre = support.source_hashes(sources)
    environment = os.environ.copy()
    environment.update(
        {
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "SDL_AUDIODRIVER": "dummy",
            "SDL_VIDEODRIVER": "dummy",
        }
    )
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--emit-target",
            str(source_root),
            "--emit-output",
            str(output),
        ],
        check=True,
        cwd=root,
        env=environment,
    )
    runtime_post = support.runtime_tree_sha256(source_root)
    verifier_post = support.source_hashes(sources)
    if runtime_pre != runtime_post:
        raise RuntimeError(f"runtime source drifted while capturing {root}")
    if verifier_pre != verifier_post:
        raise RuntimeError("verifier/support sources drifted while capturing a target")
    return {
        "runtime": {"post": runtime_post, "pre": runtime_pre},
        "verifierSources": {
            name: {"post": verifier_post[name], "pre": verifier_pre[name]}
            for name in sorted(verifier_pre)
        },
    }


def _resolve_baseline(candidate_root: Path, baseline_ref: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={candidate_root.as_posix()}",
            "-C",
            str(candidate_root),
            "rev-parse",
            "--verify",
            f"{baseline_ref}^{{commit}}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _verify(args: argparse.Namespace) -> None:
    candidate_root = args.candidate_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    baseline_commit = _resolve_baseline(candidate_root, args.baseline_ref)
    expected_bytes = args.expected.read_bytes() if args.expected else None
    with tempfile.TemporaryDirectory(prefix="gm03f-input-coordinator-") as temporary:
        temporary_root = Path(temporary)
        archive = temporary_root / "baseline.tar"
        baseline_root = temporary_root / "baseline"
        baseline_root.mkdir()
        subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={candidate_root.as_posix()}",
                "-C",
                str(candidate_root),
                "archive",
                "--format=tar",
                "--output",
                str(archive),
                baseline_commit,
            ],
            check=True,
        )
        with tarfile.open(archive, "r") as baseline_tar:
            baseline_tar.extractall(baseline_root, filter="data")
        baseline_output = temporary_root / "baseline.json"
        candidate_output = temporary_root / "candidate.json"
        baseline_hashes = _run_child(script, baseline_root, baseline_output)
        candidate_hashes = _run_child(script, candidate_root, candidate_output)
        baseline_bytes = baseline_output.read_bytes()
        candidate_bytes = candidate_output.read_bytes()

    baseline_digest = support.sha256(baseline_bytes)
    candidate_digest = support.sha256(candidate_bytes)
    equal = baseline_bytes == candidate_bytes and baseline_digest == candidate_digest
    expected_digest = None if expected_bytes is None else support.sha256(expected_bytes)
    expected_equal = expected_bytes is None or (
        expected_bytes == candidate_bytes and expected_digest == candidate_digest
    )
    artifact_path = output_dir / ARTIFACT_NAME
    artifact_path.write_bytes(candidate_bytes)
    summary = {
        "artifact": {
            "bytes": len(candidate_bytes),
            "path": ARTIFACT_NAME,
            "sha256": candidate_digest,
        },
        "baselineCommit": baseline_commit,
        "baselineRef": args.baseline_ref,
        "caseCount": EXPECTED_CASE_COUNT,
        "eventCount": EXPECTED_EVENT_COUNT,
        "expected": (
            None
            if expected_bytes is None
            else {
                "bytes": len(expected_bytes),
                "equal": expected_equal,
                "sha256": expected_digest,
            }
        ),
        "recordCount": EXPECTED_RECORD_COUNT,
        "results": {
            "baseline": {"bytes": len(baseline_bytes), "sha256": baseline_digest},
            "candidate": {
                "bytes": len(candidate_bytes),
                "sha256": candidate_digest,
            },
            "equal": equal,
        },
        "sourceHashes": {
            "baseline": baseline_hashes,
            "candidate": candidate_hashes,
        },
        "scenarioVersion": SCENARIO_VERSION,
        "schemaVersion": 1,
    }
    (output_dir / SUMMARY_NAME).write_bytes(support.json_bytes(summary))
    if not equal:
        raise SystemExit("baseline and candidate input-coordinator evidence differ")
    if not expected_equal:
        raise SystemExit("candidate input-coordinator evidence differs from --expected")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the GM-03f input-coordinator differential against its "
            "GM-03e baseline."
        )
    )
    parser.add_argument("--baseline-ref", default=BASELINE_REF)
    parser.add_argument("--candidate-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--emit-target", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--emit-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.emit_target is not None:
        if args.emit_output is None:
            parser.error("--emit-output is required with --emit-target")
    elif args.output_dir is None:
        parser.error("--output-dir is required")
    return args


def main() -> None:
    args = _parse_args()
    if args.emit_target is not None:
        _emit_target(args.emit_target, args.emit_output)
    else:
        _verify(args)


if __name__ == "__main__":
    main()
