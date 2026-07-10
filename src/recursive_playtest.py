from __future__ import annotations

import argparse
import json
import math
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Sequence

from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint
from recursive_oracles import nonfinite_paths, reference_errors

SCHEMA_VERSION = 1
_SCENARIO_KEYS = {"schemaVersion", "seed", "defaultDtMs", "operations"}
_INPUT_KEYS = {
    "schemaVersion",
    "runId",
    "sourcePath",
    "seed",
    "defaultDtMs",
    "pythonExecutable",
    "pythonHashSeed",
    "operations",
}
_OPERATION_KEYS = {"name", "action", "expectedActionOk"}
_ARTIFACT_NAMES = (
    "inputs.json",
    "transcript.jsonl",
    "findings.authored.json",
    "run-result.json",
)


def _exact_keys(
    value: object, required: set[str], optional: set[str], label: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be an object")
    keys = set(value)
    if keys - required - optional or required - keys:
        raise ValueError(
            f"{label} keys must be exactly {sorted(required)}"
            + (f" plus optional {sorted(optional)}" if optional else "")
        )
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _uint32(value: object, label: str) -> int:
    integer = _nonnegative_int(value, label)
    if integer > 4_294_967_295:
        raise ValueError(f"{label} must be a uint32 integer")
    return integer


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a nonempty trimmed string")
    return value


def _hash_seed(value: object) -> str:
    seed = _nonempty_string(value, "inputs.pythonHashSeed")
    if not seed.isdecimal() or not 0 <= int(seed) <= 4_294_967_295:
        raise ValueError("inputs.pythonHashSeed must be a uint32 string")
    return seed


def _validate_json(value: object, label: str, seen: set[int] | None = None) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{label} must not contain non-finite numbers")
        return
    if seen is None:
        seen = set()
    if type(value) in (list, dict):
        if id(value) in seen:
            raise ValueError(f"{label} must not contain cycles")
        seen.add(id(value))
        children = enumerate(value) if isinstance(value, list) else value.items()
        for key, item in children:
            if isinstance(value, dict) and not isinstance(key, str):
                raise ValueError(f"{label} keys must be strings")
            _validate_json(item, f"{label}.{key}", seen)
        seen.remove(id(value))
        return
    raise ValueError(f"{label} must contain only JSON values")


def _json_copy(value: Any, label: str = "value") -> Any:
    _validate_json(value, label)
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


def _validate_operations(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise ValueError("operations must be a nonempty array")
    result: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(value):
        operation = _exact_keys(raw, _OPERATION_KEYS, {"dtMs"}, f"operations[{index}]")
        name = _nonempty_string(operation["name"], f"operations[{index}].name")
        if name in names:
            raise ValueError("operation names must be unique")
        names.add(name)
        if type(operation["expectedActionOk"]) is not bool:
            raise ValueError(f"operations[{index}].expectedActionOk must be boolean")
        if "dtMs" in operation:
            _nonnegative_int(operation["dtMs"], f"operations[{index}].dtMs")
        _validate_json(operation["action"], f"operations[{index}].action")
        result.append(_json_copy(operation, f"operations[{index}]"))
    return result


def validate_scenario(value: object) -> dict[str, Any]:
    document = _exact_keys(value, _SCENARIO_KEYS, set(), "scenario")
    if (
        type(document["schemaVersion"]) is not int
        or document["schemaVersion"] != SCHEMA_VERSION
    ):
        raise ValueError("scenario schemaVersion must be 1")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "seed": _uint32(document["seed"], "scenario.seed"),
        "defaultDtMs": _nonnegative_int(
            document["defaultDtMs"], "scenario.defaultDtMs"
        ),
        "operations": _validate_operations(document["operations"]),
    }


def validate_inputs(value: object) -> dict[str, Any]:
    document = _exact_keys(value, _INPUT_KEYS, set(), "inputs")
    if (
        type(document["schemaVersion"]) is not int
        or document["schemaVersion"] != SCHEMA_VERSION
    ):
        raise ValueError("inputs schemaVersion must be 1")
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "runId": _nonempty_string(document["runId"], "inputs.runId"),
        "sourcePath": _nonempty_string(document["sourcePath"], "inputs.sourcePath"),
        "seed": _uint32(document["seed"], "inputs.seed"),
        "defaultDtMs": _nonnegative_int(document["defaultDtMs"], "inputs.defaultDtMs"),
        "pythonExecutable": _nonempty_string(
            document["pythonExecutable"], "inputs.pythonExecutable"
        ),
        "pythonHashSeed": _hash_seed(document["pythonHashSeed"]),
        "operations": _validate_operations(document["operations"]),
    }
    return _json_copy(result, "inputs")


def load_inputs(path: str | Path) -> dict[str, Any]:
    return validate_inputs(json.loads(Path(path).read_text(encoding="utf-8")))


def _finding(
    finding_class: str,
    details: list[str],
    *,
    step: int | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    severity = {
        "input-transcript-cardinality-mismatch": "critical",
        "terminal-state-mutation": "critical",
        "invalid-reference": "critical",
        "non-finite-coordinate": "critical",
        "expected-action-result-mismatch": "medium",
    }.get(finding_class, "high")
    finding_id = f"python-mini-metro-{finding_class}"
    evidence: list[dict[str, Any]] = []
    data: dict[str, Any] = {"class": finding_class, "details": sorted(details)}
    if step is not None:
        finding_id += f"-step-{step}"
        evidence_ref: dict[str, Any] = {
            "kind": "step",
            "step": step,
            "actionIndex": step,
        }
        if name is not None:
            evidence_ref["label"] = name
        evidence.append(evidence_ref)
        data.update({"stepIndex": step, "operationName": name})
    return {
        "schemaVersion": 1,
        "id": finding_id,
        "title": finding_class.replace("-", " "),
        "severity": severity,
        "category": "bug",
        "observed": "; ".join(sorted(details)),
        "expected": "The recorded environment contract remains internally consistent.",
        "suggestion": "Correct the environment or harness contract and promote this class to a regression test.",
        "area": "environment-contract",
        "evidence": evidence,
        "verificationStatus": "unverified",
        "nextAction": "autoFix",
        "promotionTarget": "test",
        "disposition": "candidate",
        "data": data,
    }


def evaluate_oracles(
    transcript: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    initial_checkpoint: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if len(transcript) != len(operations):
        findings.append(
            _finding(
                "input-transcript-cardinality-mismatch",
                [f"{len(operations)} operations produced {len(transcript)} rows"],
            )
        )
    for index, row in enumerate(transcript):
        operation = operations[index] if index < len(operations) else None
        name = row.get("name")
        checkpoint = row["checkpoint"]
        previous = (
            initial_checkpoint if index == 0 else transcript[index - 1]["checkpoint"]
        )

        def add(finding_class: str, *details: str) -> None:
            findings.append(
                _finding(finding_class, list(details), step=index, name=name)
            )

        if operation is None or row["actionOk"] != operation["expectedActionOk"]:
            expected = None if operation is None else operation["expectedActionOk"]
            add(
                "expected-action-result-mismatch",
                f"expected actionOk {expected}, observed {row['actionOk']}",
            )
        score_delta = (
            checkpoint["structured"]["score"] - previous["structured"]["score"]
        )
        if row["reward"] != score_delta:
            add(
                "reward-score-mismatch",
                f"reward {row['reward']} differs from score delta {score_delta}",
            )
        was_terminal = previous["structured"]["is_game_over"]
        if not row["actionOk"] and not was_terminal and checkpoint != previous:
            add("rejected-action-mutation", "a rejected action changed the checkpoint")
        action_type = (
            row["action"].get("type") if isinstance(row["action"], dict) else None
        )
        was_paused = previous["structured"]["is_paused"]
        paused_changed_clock = any(
            checkpoint["structured"][key] != previous["structured"][key]
            for key in ("time_ms", "steps")
        )
        if (
            action_type == "pause" or (was_paused and action_type != "resume")
        ) and paused_changed_clock:
            add("paused-time-progression", "time or steps advanced while paused")
        if action_type == "pause" and row["actionOk"] and not was_terminal:
            expected_pause = deepcopy(previous)
            expected_pause["structured"]["is_paused"] = True
            expected_pause["progression"]["is_paused"] = True
            if checkpoint != expected_pause:
                add(
                    "paused-state-mutation",
                    "pause changed state beyond the pause flag",
                )
        elif was_paused and action_type in (None, "noop") and checkpoint != previous:
            add("paused-state-mutation", "a paused noop changed simulation state")
        terminal_values = (
            row["done"],
            checkpoint["structured"]["is_game_over"],
            checkpoint["progression"]["is_game_over"],
        )
        if len(set(terminal_values)) != 1:
            add(
                "terminal-result-mismatch",
                f"done/structured/progression terminal flags differ: {terminal_values}",
            )
        if was_terminal and checkpoint != previous:
            add("terminal-state-mutation", "a terminal step changed the checkpoint")
        structured_paths = [
            item["station_indices"] for item in checkpoint["structured"]["paths"]
        ]
        array_paths = checkpoint["arrays"]["path_station_indices"]
        if structured_paths != array_paths:
            add(
                "observation-path-topology-mismatch",
                f"structured topology {structured_paths} differs from arrays topology {array_paths}",
            )
        references = reference_errors(checkpoint)
        if references:
            add("invalid-reference", *references)
        nonfinite = nonfinite_paths(checkpoint)
        if nonfinite:
            add("non-finite-coordinate", *nonfinite)
    return sorted(findings, key=lambda item: item["id"])


def _build_inputs(
    scenario: dict[str, Any], run_id: str, source_path: str
) -> dict[str, Any]:
    return validate_inputs(
        {
            "schemaVersion": SCHEMA_VERSION,
            "runId": _nonempty_string(run_id, "run id"),
            "sourcePath": _nonempty_string(source_path, "source path"),
            "seed": scenario["seed"],
            "defaultDtMs": scenario["defaultDtMs"],
            "pythonExecutable": sys.executable,
            "pythonHashSeed": os.environ.get("PYTHONHASHSEED"),
            "operations": scenario["operations"],
        }
    )


def run_scenario(
    scenario: dict[str, Any],
    *,
    run_id: str,
    source_path: str,
    env_factory: Callable[[], MiniMetroEnv] = MiniMetroEnv,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    scenario = validate_scenario(scenario)
    inputs = _build_inputs(scenario, run_id, source_path)
    env = env_factory()
    initial_observation = env.reset(seed=inputs["seed"])
    initial_checkpoint = canonical_checkpoint(env, initial_observation)
    transcript: list[dict[str, Any]] = []
    for index, operation in enumerate(inputs["operations"]):
        requested_dt = operation.get("dtMs")
        effective_dt = inputs["defaultDtMs"] if requested_dt is None else requested_dt
        action_for_environment = _json_copy(operation["action"], "action")
        recorded_action = _json_copy(operation["action"], "action")
        observation, reward, done, info = env.step(
            action_for_environment, dt_ms=effective_dt
        )
        transcript.append(
            {
                "index": index,
                "name": operation["name"],
                "action": recorded_action,
                "requestedDtMs": requested_dt,
                "effectiveDtMs": effective_dt,
                "actionOk": info["action_ok"],
                "reward": reward,
                "done": done,
                "checkpoint": canonical_checkpoint(env, observation),
            }
        )
    findings = evaluate_oracles(transcript, inputs["operations"], initial_checkpoint)
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "runId": inputs["runId"],
        "seed": inputs["seed"],
        "operationCount": len(inputs["operations"]),
        "transcriptRows": len(transcript),
        "findingCount": len(findings),
        "completed": True,
    }
    return inputs, transcript, findings, result


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, rows: Sequence[Any]) -> None:
    text = "".join(
        json.dumps(row, allow_nan=False, separators=(",", ":"), sort_keys=True) + "\n"
        for row in rows
    )
    Path(path).write_text(text, encoding="utf-8")


def _write_artifacts(
    out_dir: Path,
    inputs: dict[str, Any],
    transcript: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    result: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if any((out_dir / name).exists() for name in _ARTIFACT_NAMES):
        raise ValueError(
            "recursive playtest artifacts are append-only and already exist"
        )
    write_json(out_dir / "inputs.json", inputs)
    write_jsonl(out_dir / "transcript.jsonl", transcript)
    write_json(out_dir / "findings.authored.json", findings)
    write_json(out_dir / "run-result.json", result)


def drive_from_file(
    input_path: str | Path,
    out_dir: str | Path,
    run_id: str,
    *,
    recorded_inputs: bool = False,
) -> None:
    path = Path(input_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if recorded_inputs:
        previous = validate_inputs(document)
        scenario = {
            "schemaVersion": SCHEMA_VERSION,
            "seed": previous["seed"],
            "defaultDtMs": previous["defaultDtMs"],
            "operations": previous["operations"],
        }
        source_path = previous["sourcePath"]
    else:
        scenario = validate_scenario(document)
        source_path = str(path)
    artifacts = run_scenario(scenario, run_id=run_id, source_path=source_path)
    _write_artifacts(Path(out_dir), *artifacts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Drive a deterministic Mini Metro scenario"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--scenario")
    source.add_argument("--inputs")
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", required=True)
    try:
        args = parser.parse_args(argv)
        drive_from_file(
            args.inputs or args.scenario,
            args.out,
            args.run_id,
            recorded_inputs=args.inputs is not None,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"recursive playtest failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
