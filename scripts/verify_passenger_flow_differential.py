from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import passenger_flow_differential_support as support

BASELINE_REF = "2c4cd4fe484222549fd177455dd413859983ad50"
SCENARIO_VERSION = "gm03e-passenger-flow-v1"
ARTIFACT_NAME = "passenger-flow-differential.json"
SUMMARY_NAME = "passenger-flow-differential-summary.json"


def _proposal_case() -> dict[str, Any]:
    import mediator as mediator_module
    from entity.passenger import Passenger
    from entity.path import Path
    from env import MiniMetroEnv
    from geometry.type import ShapeType
    from travel_plan import TravelPlan

    env = MiniMetroEnv()
    env.reset(seed=919)
    host = env.mediator
    events: list[dict[str, Any]] = []
    labels: dict[int, str] = {}
    source = support.station(ShapeType.RECT, 0)
    reachable = support.station(ShapeType.CIRCLE, 1000)
    isolated = support.station(ShapeType.TRIANGLE, 2000)
    host.all_stations = host.stations = [source, reachable, isolated]
    for name, value in (
        ("station-source", source),
        ("station-reachable", reachable),
        ("station-isolated", isolated),
    ):
        labels[id(value)] = name
    path = Path((30, 40, 50))
    path.add_station(source)
    path.add_station(reachable)
    host.paths = [path]
    host.metros = []
    labels[id(path)] = "path-main"
    riders = {
        "arrived": Passenger(source.shape),
        "adjacent": Passenger(support.station(ShapeType.CROSS, 3000).shape),
        "route-1": Passenger(reachable.shape),
        "route-2": Passenger(reachable.shape),
        "fallback": Passenger(isolated.shape),
    }
    for name, rider in riders.items():
        labels[id(rider)] = name
        source.add_passenger(rider)
        host.passengers.append(rider)
    host.travel_plans[riders["arrived"]] = TravelPlan([])
    host.station_spawn_interval_steps.clear()
    host.station_steps_since_last_spawn.clear()
    original_has_plan = host.passenger_has_travel_plan

    def has_plan(rider: Any) -> bool:
        events.append(
            {"event": "proposal.visit", "rider": support.label(labels, rider)}
        )
        return original_has_plan(rider)

    host.passenger_has_travel_plan = has_plan
    destination_names = iter(("arrived", "route-1", "route-2", "fallback"))

    def destinations(shape_type: Any) -> support.Destinations:
        if shape_type == ShapeType.CROSS:
            raise AssertionError("live-list iteration must skip the adjacent rider")
        name = next(destination_names)
        target = {
            ShapeType.RECT: source,
            ShapeType.CIRCLE: reachable,
            ShapeType.TRIANGLE: isolated,
        }[shape_type]
        events.append({"event": "destinations.create", "rider": name})
        return support.Destinations(name, [target], events)

    host.get_stations_for_shape_type = destinations
    original_reduce = host.skip_stations_on_same_path
    host.skip_stations_on_same_path = support.RebindingCallable(
        "reducer-1",
        events,
        host,
        "skip_stations_on_same_path",
        support.RebindingCallable(
            "reducer-2",
            events,
            host,
            "skip_stations_on_same_path",
            original_reduce,
            original_reduce,
        ),
        original_reduce,
    )
    original_plan_factory = mediator_module.TravelPlan
    mediator_module.TravelPlan = support.RebindingCallable(
        "plan-route-1",
        events,
        mediator_module,
        "TravelPlan",
        support.RebindingCallable(
            "plan-route-2",
            events,
            mediator_module,
            "TravelPlan",
            support.RebindingCallable(
                "plan-fallback",
                events,
                mediator_module,
                "TravelPlan",
                original_plan_factory,
                original_plan_factory,
            ),
            original_plan_factory,
        ),
        original_plan_factory,
    )
    original_next_path = host.find_next_path_for_passenger_at_station

    def next_path(rider: Any, station: Any) -> None:
        events.append(
            {"event": "proposal.next-path", "rider": support.label(labels, rider)}
        )
        original_next_path(rider, station)

    host.find_next_path_for_passenger_at_station = next_path
    host._router = support.RouterTrace(host._router, host, events, labels)
    original_builder = mediator_module.build_station_nodes_dict

    def build(stations: Any, paths: Any) -> support.TaggedGraph:
        events.append({"event": "graph.build", "phase": "planning"})
        return support.TaggedGraph(original_builder(stations, paths), "planning")

    mediator_module.build_station_nodes_dict = build
    records = [support.record(env, "proposals-prepared", {}, events)]
    try:
        host.find_travel_plan_for_passengers()
        records.append(
            support.record(
                env,
                "proposals-applied",
                {
                    name: support.rider_state(host, rider, labels)
                    for name, rider in riders.items()
                },
                events,
            )
        )
    finally:
        mediator_module.TravelPlan = original_plan_factory
        mediator_module.build_station_nodes_dict = original_builder

    visits = [event["rider"] for event in events if event["event"] == "proposal.visit"]
    kinds = [event["kind"] for event in events if event["event"] == "proposal.yield"]
    releases = [
        event["name"] for event in events if event["event"] == "callable.release"
    ]
    if visits != ["arrived", "route-1", "route-2", "fallback"]:
        raise AssertionError(
            "arrival removal no longer preserves adjacent live-list skip"
        )
    if kinds != ["arrival", "fallback", "route", "route", "fallback"]:
        raise AssertionError("arrival, route, or fallback proposal timing changed")
    if releases != [
        "reducer-1",
        "plan-route-1",
        "reducer-2",
        "plan-route-2",
        "plan-fallback",
    ]:
        raise AssertionError("reducer or plan-factory callable lifetime changed")
    if (
        riders["adjacent"] in host.travel_plans
        or not riders["arrived"].is_at_destination
    ):
        raise AssertionError("proposal side effects changed")
    return {"events": events, "name": "proposal-lifetimes", "records": records}


def _emit_target(source_root: Path, output: Path) -> None:
    source_root = source_root.resolve()
    sys.path.insert(0, str(source_root))
    import env as env_module
    import mediator as mediator_module
    import recursive_checkpoint as checkpoint_module
    import route_planner as route_module

    for module in (env_module, mediator_module, checkpoint_module, route_module):
        if not Path(module.__file__).resolve().is_relative_to(source_root):
            raise RuntimeError(f"{module.__name__} did not load from the target source")
    cases = [support.tick_case(), _proposal_case()]
    passenger_flow_module = sys.modules.get("passenger_flow")
    if passenger_flow_module is not None and not Path(
        passenger_flow_module.__file__
    ).resolve().is_relative_to(source_root):
        raise RuntimeError("passenger_flow did not load from the target source")
    result = {
        "caseCount": len(cases),
        "cases": cases,
        "eventCount": sum(len(case["events"]) for case in cases),
        "recordCount": sum(len(case["records"]) for case in cases),
        "scenarioVersion": SCENARIO_VERSION,
        "schemaVersion": 1,
    }
    if result["caseCount"] != 2 or result["recordCount"] != 5:
        raise AssertionError("scenario case or record cardinality changed")
    output.write_bytes(support.json_bytes(result))


def _run_child(script: Path, root: Path, output: Path) -> str:
    source_root = root / "src"
    before = support.runtime_tree_sha256(source_root)
    verifier_files = (script, Path(support.__file__).resolve())
    verifier_before = {
        path: support.sha256(path.read_bytes()) for path in verifier_files
    }
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
    if before != support.runtime_tree_sha256(source_root):
        raise RuntimeError(f"runtime source drifted while capturing {root}")
    if verifier_before != {
        path: support.sha256(path.read_bytes()) for path in verifier_files
    }:
        raise RuntimeError("the differential verifier drifted while capturing a target")
    return before


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
    with tempfile.TemporaryDirectory(prefix="gm03e-passenger-flow-") as temporary:
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
        baseline_tree = _run_child(script, baseline_root, baseline_output)
        candidate_tree = _run_child(script, candidate_root, candidate_output)
        baseline_bytes = baseline_output.read_bytes()
        candidate_bytes = candidate_output.read_bytes()

    equal = baseline_bytes == candidate_bytes
    expected_equal = expected_bytes is None or expected_bytes == candidate_bytes
    artifact_path = output_dir / ARTIFACT_NAME
    artifact_path.write_bytes(candidate_bytes)
    summary = {
        "artifact": {
            "bytes": len(candidate_bytes),
            "path": ARTIFACT_NAME,
            "sha256": support.sha256(candidate_bytes),
        },
        "baselineCommit": baseline_commit,
        "baselineRef": args.baseline_ref,
        "expected": (
            None
            if expected_bytes is None
            else {"equal": expected_equal, "sha256": support.sha256(expected_bytes)}
        ),
        "results": {
            "baseline": {
                "bytes": len(baseline_bytes),
                "sha256": support.sha256(baseline_bytes),
            },
            "candidate": {
                "bytes": len(candidate_bytes),
                "sha256": support.sha256(candidate_bytes),
            },
            "equal": equal,
        },
        "runtimeTrees": {
            "baseline": {"sha256": baseline_tree},
            "candidate": {"sha256": candidate_tree},
        },
        "scenarioVersion": SCENARIO_VERSION,
        "schemaVersion": 1,
        "verifier": {
            "runnerSha256": support.sha256(script.read_bytes()),
            "supportSha256": support.sha256(
                Path(support.__file__).resolve().read_bytes()
            ),
        },
    }
    (output_dir / SUMMARY_NAME).write_bytes(support.json_bytes(summary))
    if not equal:
        raise SystemExit("baseline and candidate passenger-flow evidence differ")
    if not expected_equal:
        raise SystemExit("candidate passenger-flow evidence differs from --expected")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduce the GM-03e baseline/current passenger-flow differential."
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
