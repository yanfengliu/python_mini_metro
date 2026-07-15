from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

BASELINE_REF = "5e6186d8b331207d2a6ec583b7a82f80533f5203"
SCENARIO_VERSION = "gm03d-path-lifecycle-v1"
ARTIFACT_NAME = "lifecycle-differential.json"
SUMMARY_NAME = "lifecycle-differential-summary.json"


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _runtime_tree_sha256(source_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _record(env: Any, label: str, action: dict[str, Any], outcome: Any) -> dict:
    from recursive_checkpoint import canonical_checkpoint

    observation = env.observe()
    return {
        "action": action,
        "checkpoint": canonical_checkpoint(env, observation),
        "label": label,
        "outcome": outcome,
    }


def _step(env: Any, action: dict[str, Any]) -> tuple[dict, dict]:
    observation, reward, done, info = env.step(action)
    return observation, {
        "actionOk": info["action_ok"],
        "done": done,
        "reward": reward,
    }


def _selector_case() -> tuple[list[dict], int]:
    from env import MiniMetroEnv

    env = MiniMetroEnv()
    env.reset(seed=41)
    env.mediator.purchased_num_paths = 3
    env.mediator.update_unlocked_num_paths()
    records = [
        _record(
            env,
            "selectors-initial",
            {"type": "case-start", "seed": 41},
            {"unlockedPaths": env.mediator.unlocked_num_paths},
        )
    ]

    non_loop = {"type": "create_path", "stations": [0, 1, 2], "loop": False}
    _, outcome = _step(env, non_loop)
    if not outcome["actionOk"]:
        raise AssertionError("non-loop creation must succeed")
    records.append(_record(env, "selectors-create-non-loop", non_loop, outcome))

    closed_loop = {
        "type": "create_path",
        "stations": [0, 1, 2, 0],
        "loop": True,
    }
    _, outcome = _step(env, closed_loop)
    if not outcome["actionOk"]:
        raise AssertionError("explicit closed-loop creation must succeed")
    loop_path = env.mediator.paths[1]
    loop_probe = {
        **outcome,
        "isLooped": loop_path.is_looped,
        "snapBlipCounts": [
            len(station.snap_blips) for station in env.mediator.stations[:3]
        ],
        "stationIndices": [
            env.mediator.stations.index(station) for station in loop_path.stations
        ],
    }
    if loop_probe["stationIndices"] != [0, 1, 2]:
        raise AssertionError("closed-loop station de-duplication changed")
    if not loop_probe["isLooped"] or loop_probe["snapBlipCounts"] != [0, 2, 2]:
        raise AssertionError("closed-loop topology or snap effects changed")
    records.append(
        _record(env, "selectors-create-closed-loop", closed_loop, loop_probe)
    )

    abort = {"type": "create_path", "stations": [0, 0], "loop": False}
    _, outcome = _step(env, abort)
    if outcome["actionOk"] or env.mediator.is_creating_path:
        raise AssertionError("single-station path must abort and report rejection")
    records.append(_record(env, "selectors-abort", abort, outcome))

    removed_id = env.mediator.paths[0].id
    remove_by_id = {"type": "remove_path_by_resolved_id", "sourcePathIndex": 0}
    _, outcome = _step(env, {"type": "remove_path", "path_id": removed_id})
    if not outcome["actionOk"]:
        raise AssertionError("ID-selected removal must succeed")
    records.append(_record(env, "selectors-remove-by-id", remove_by_id, outcome))

    remove_by_index = {"type": "remove_path", "path_index": 0}
    _, outcome = _step(env, remove_by_index)
    if not outcome["actionOk"] or env.mediator.paths:
        raise AssertionError("index-selected removal must clear the remaining path")
    records.append(_record(env, "selectors-remove-by-index", remove_by_index, outcome))
    return records, 5


def _cleanup_case() -> tuple[list[dict], int]:
    from entity.passenger import Passenger
    from env import MiniMetroEnv
    from travel_plan import TravelPlan

    env = MiniMetroEnv()
    env.reset(seed=73)
    records = [
        _record(
            env,
            "cleanup-initial",
            {"type": "case-start", "seed": 73},
            {},
        )
    ]

    create = {"type": "create_path", "stations": [0, 1, 2], "loop": False}
    _, create_outcome = _step(env, create)
    if not create_outcome["actionOk"]:
        raise AssertionError("cleanup path creation must succeed")
    mediator = env.mediator
    path = mediator.paths[0]
    metro = path.metros[0]
    button = mediator.path_to_button[path]
    waiting_station = mediator.stations[0]
    destination = mediator.stations[2]
    waiting = Passenger(destination.shape)
    onboard = Passenger(destination.shape)
    waiting_station.add_passenger(waiting)
    metro.add_passenger(onboard)
    mediator.passengers.extend([waiting, onboard])
    for passenger in (waiting, onboard):
        plan = TravelPlan([])
        plan.next_path = path
        mediator.travel_plans[passenger] = plan
    records.append(
        _record(
            env,
            "cleanup-prepared",
            create,
            {
                **create_outcome,
                "onboardPassengerCount": len(metro.passengers),
                "waitingPassengerCount": len(waiting_station.passengers),
            },
        )
    )

    remove = {"type": "remove_path_by_resolved_id", "sourcePathIndex": 0}
    _, remove_outcome = _step(env, {"type": "remove_path", "path_id": path.id})
    probes = {
        **remove_outcome,
        "capturedButtonCleared": button.path is None,
        "detachedMetroRetainsPassenger": onboard in metro.passengers,
        "detachedPathRetainsMetro": metro in path.metros,
        "onboardPassengerGlobal": onboard in mediator.passengers,
        "onboardPassengerPlanned": onboard in mediator.travel_plans,
        "waitingPassengerAtStation": waiting in waiting_station.passengers,
        "waitingPassengerGlobal": waiting in mediator.passengers,
        "waitingPlanReferencesRemovedPath": (
            waiting in mediator.travel_plans
            and mediator.travel_plans[waiting].next_path is path
        ),
    }
    expected = {
        "capturedButtonCleared": True,
        "detachedMetroRetainsPassenger": True,
        "detachedPathRetainsMetro": True,
        "onboardPassengerGlobal": False,
        "onboardPassengerPlanned": False,
        "waitingPassengerAtStation": True,
        "waitingPassengerGlobal": True,
        "waitingPlanReferencesRemovedPath": False,
    }
    for key, value in expected.items():
        if probes[key] is not value:
            raise AssertionError(f"cleanup probe changed: {key}")
    if not remove_outcome["actionOk"]:
        raise AssertionError("cleanup removal must succeed")
    records.append(_record(env, "cleanup-remove-by-id", remove, probes))
    return records, 2


def _emit_target(source_root: Path, output: Path) -> None:
    source_root = source_root.resolve()
    sys.path.insert(0, str(source_root))
    import env as env_module

    if Path(env_module.__file__).resolve().parent != source_root:
        raise RuntimeError(
            "target env module did not load from the requested source root"
        )
    selector_records, selector_actions = _selector_case()
    cleanup_records, cleanup_actions = _cleanup_case()
    result = {
        "actionCount": selector_actions + cleanup_actions,
        "cases": [
            {"name": "selectors", "records": selector_records},
            {"name": "cleanup", "records": cleanup_records},
        ],
        "recordCount": len(selector_records) + len(cleanup_records),
        "scenarioVersion": SCENARIO_VERSION,
        "schemaVersion": 1,
    }
    if result["actionCount"] != 7 or result["recordCount"] != 9:
        raise AssertionError("scenario action/record cardinality changed")
    output.write_bytes(_json_bytes(result))


def _run_child(script: Path, root: Path, output: Path) -> str:
    source_root = root / "src"
    before = _runtime_tree_sha256(source_root)
    environment = os.environ.copy()
    environment.update(
        {
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
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
    after = _runtime_tree_sha256(source_root)
    if before != after:
        raise RuntimeError(f"runtime source drifted while capturing {root}")
    return before


def _verify(args: argparse.Namespace) -> None:
    candidate_root = args.candidate_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="gm03d-path-lifecycle-") as temporary:
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
                args.baseline_ref,
            ],
            check=True,
        )
        with tarfile.open(archive, "r") as baseline_tar:
            baseline_tar.extractall(baseline_root, filter="data")

        baseline_output = temporary_root / "baseline.json"
        candidate_output = temporary_root / "candidate.json"
        baseline_tree = _run_child(script, baseline_root, baseline_output)
        candidate_tree = _run_child(script, candidate_root, candidate_output)
        baseline_bytes = baseline_output.read_bytes()
        candidate_bytes = candidate_output.read_bytes()

    equal = baseline_bytes == candidate_bytes
    expected_bytes = args.expected.read_bytes() if args.expected else None
    expected_equal = expected_bytes is None or expected_bytes == candidate_bytes
    artifact_path = output_dir / ARTIFACT_NAME
    artifact_path.write_bytes(candidate_bytes)
    summary = {
        "actionCount": 7,
        "artifact": {
            "path": ARTIFACT_NAME,
            "sha256": _sha256(candidate_bytes),
        },
        "baselineRef": args.baseline_ref,
        "expected": (
            None
            if expected_bytes is None
            else {"equal": expected_equal, "sha256": _sha256(expected_bytes)}
        ),
        "recordCount": 9,
        "results": {
            "baseline": {
                "bytes": len(baseline_bytes),
                "sha256": _sha256(baseline_bytes),
            },
            "candidate": {
                "bytes": len(candidate_bytes),
                "sha256": _sha256(candidate_bytes),
            },
            "equal": equal,
        },
        "runtimeTrees": {
            "baseline": {"sha256": baseline_tree},
            "candidate": {"sha256": candidate_tree},
        },
        "scenarioVersion": SCENARIO_VERSION,
        "schemaVersion": 1,
    }
    (output_dir / SUMMARY_NAME).write_bytes(_json_bytes(summary))
    if not equal:
        raise SystemExit("baseline and candidate lifecycle evidence differ")
    if not expected_equal:
        raise SystemExit("candidate lifecycle evidence differs from --expected")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduce the GM-03d baseline/current lifecycle differential."
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
