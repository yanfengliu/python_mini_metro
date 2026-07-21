from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from inspect import Parameter, signature
from pathlib import Path
from typing import Any, Callable, Sequence

import recursive_contract as _recursive_contract
from env import MiniMetroEnv, legacy_auto_assignment_step
from recursive_checkpoint import canonical_checkpoint, normalize_checkpoint
from recursive_contract import (
    DELIVERIES_REWARD_CONTRACT,
    LINE_CREDITS_REWARD_CONTRACT,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
    SCHEMA_VERSION_V4,
    _json_copy,
    _nonempty_string,
    _overdue_threshold_for_document,
    _reward_contract_for_document,
    validate_inputs,
    validate_scenario,
)
from recursive_oracles import nonfinite_paths, reference_errors

# Compatibility re-exports retained after extracting the document contract.
LEGACY_SCHEMA_VERSION = _recursive_contract.LEGACY_SCHEMA_VERSION
SCHEMA_VERSION = _recursive_contract.SCHEMA_VERSION
load_inputs = _recursive_contract.load_inputs

_ARTIFACT_NAMES = (
    "inputs.json",
    "transcript.jsonl",
    "findings.authored.json",
    "run-result.json",
)


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
    *,
    environment_reward_contract: str | None = None,
) -> list[dict[str, Any]]:
    normalized_initial = normalize_checkpoint(initial_checkpoint)
    checkpoint_reward_contract = normalized_initial["environment"]["reward_mode"]
    if environment_reward_contract is None:
        environment_reward_contract = checkpoint_reward_contract
    if environment_reward_contract not in {
        DELIVERIES_REWARD_CONTRACT,
        LINE_CREDITS_REWARD_CONTRACT,
    }:
        raise ValueError("unsupported environment reward contract")
    if environment_reward_contract != checkpoint_reward_contract:
        raise ValueError(
            "environment reward contract disagrees with initial checkpoint"
        )
    normalized_checkpoints = [
        normalize_checkpoint(row["checkpoint"]) for row in transcript
    ]
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
        checkpoint = normalized_checkpoints[index]
        previous = (
            normalized_initial if index == 0 else normalized_checkpoints[index - 1]
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
        if checkpoint["environment"]["reward_mode"] != environment_reward_contract:
            add(
                "environment-reward-contract-changed",
                "checkpoint reward mode changed within the transcript",
            )
        if environment_reward_contract == DELIVERIES_REWARD_CONTRACT:
            reward_field = "deliveries"
            expected_reward = (
                checkpoint["progression"][reward_field]
                - previous["progression"][reward_field]
            )
        else:
            reward_field = "score"
            expected_reward = (
                checkpoint["structured"][reward_field]
                - previous["structured"][reward_field]
            )
        if row["reward"] != expected_reward:
            finding_class = (
                "reward-deliveries-mismatch"
                if environment_reward_contract == DELIVERIES_REWARD_CONTRACT
                else "reward-score-mismatch"
            )
            reward_label = f"{reward_field} delta"
            add(
                finding_class,
                f"reward {row['reward']} differs from {reward_label} {expected_reward}",
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
    document = {
        "schemaVersion": scenario["schemaVersion"],
        "runId": _nonempty_string(run_id, "run id"),
        "sourcePath": _nonempty_string(source_path, "source path"),
        "seed": scenario["seed"],
        "defaultDtMs": scenario["defaultDtMs"],
        "pythonExecutable": sys.executable,
        "pythonHashSeed": os.environ.get("PYTHONHASHSEED"),
        "operations": scenario["operations"],
    }
    if scenario["schemaVersion"] in {
        SCHEMA_VERSION_V2,
        SCHEMA_VERSION_V3,
        SCHEMA_VERSION_V4,
    }:
        document["environmentRewardContract"] = scenario["environmentRewardContract"]
    if scenario["schemaVersion"] in {SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}:
        document["overduePassengerThreshold"] = scenario["overduePassengerThreshold"]
    if scenario["schemaVersion"] == SCHEMA_VERSION_V4:
        document["fleetActionContract"] = scenario["fleetActionContract"]
    return validate_inputs(document)


def _make_environment(
    env_factory: Callable[..., MiniMetroEnv], reward_contract: str
) -> MiniMetroEnv:
    parameters = signature(env_factory).parameters
    accepts_reward_mode = "reward_mode" in parameters or any(
        parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    if accepts_reward_mode:
        env = env_factory(reward_mode=reward_contract)
    else:
        env = env_factory()
        if hasattr(env, "reward_mode"):
            env.reward_mode = reward_contract
        elif reward_contract == DELIVERIES_REWARD_CONTRACT:
            raise ValueError(
                "v2/v3 environment factories must support the deliveries reward contract"
            )
    if hasattr(env, "reward_mode") and env.reward_mode != reward_contract:
        raise ValueError("environment factory returned the wrong reward contract")
    return env


def _apply_overdue_threshold(env: MiniMetroEnv, threshold: int) -> None:
    mediator = env.mediator
    if hasattr(mediator, "overdue_passenger_threshold"):
        mediator.overdue_passenger_threshold = threshold
        return
    if hasattr(mediator, "max_waiting_passengers"):
        mediator.max_waiting_passengers = threshold
        return
    raise ValueError("environment mediator does not expose an overdue threshold")


def _checkpoint_version_for_schema(schema_version: int) -> int:
    if schema_version == SCHEMA_VERSION_V1:
        return 1
    if schema_version in {SCHEMA_VERSION_V2, SCHEMA_VERSION_V3}:
        return 2
    if schema_version == SCHEMA_VERSION_V4:
        return 3
    raise ValueError("unsupported recursive schema version")


def run_scenario(
    scenario: dict[str, Any],
    *,
    run_id: str,
    source_path: str,
    env_factory: Callable[..., MiniMetroEnv] = MiniMetroEnv,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    scenario = validate_scenario(scenario)
    inputs = _build_inputs(scenario, run_id, source_path)
    reward_contract = _reward_contract_for_document(inputs)
    overdue_threshold = _overdue_threshold_for_document(inputs)
    checkpoint_version = _checkpoint_version_for_schema(inputs["schemaVersion"])
    env = _make_environment(env_factory, reward_contract)
    initial_observation = env.reset(seed=inputs["seed"])
    _apply_overdue_threshold(env, overdue_threshold)
    initial_checkpoint = canonical_checkpoint(
        env,
        initial_observation,
        schema_version=checkpoint_version,
    )
    transcript: list[dict[str, Any]] = []
    for index, operation in enumerate(inputs["operations"]):
        requested_dt = operation.get("dtMs")
        effective_dt = inputs["defaultDtMs"] if requested_dt is None else requested_dt
        action_for_environment = _json_copy(operation["action"], "action")
        recorded_action = _json_copy(operation["action"], "action")
        if inputs["schemaVersion"] == SCHEMA_VERSION_V4:
            observation, reward, done, info = env.step(
                action_for_environment, dt_ms=effective_dt
            )
        else:
            observation, reward, done, info = legacy_auto_assignment_step(
                env, action_for_environment, dt_ms=effective_dt
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
                "checkpoint": canonical_checkpoint(
                    env,
                    observation,
                    schema_version=checkpoint_version,
                ),
            }
        )
    findings = evaluate_oracles(
        transcript,
        inputs["operations"],
        initial_checkpoint,
        environment_reward_contract=reward_contract,
    )
    result = {
        "schemaVersion": inputs["schemaVersion"],
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
            "schemaVersion": previous["schemaVersion"],
            "seed": previous["seed"],
            "defaultDtMs": previous["defaultDtMs"],
            "operations": previous["operations"],
        }
        if previous["schemaVersion"] in {
            SCHEMA_VERSION_V2,
            SCHEMA_VERSION_V3,
            SCHEMA_VERSION_V4,
        }:
            scenario["environmentRewardContract"] = previous[
                "environmentRewardContract"
            ]
        if previous["schemaVersion"] in {SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}:
            scenario["overduePassengerThreshold"] = previous[
                "overduePassengerThreshold"
            ]
        if previous["schemaVersion"] == SCHEMA_VERSION_V4:
            scenario["fleetActionContract"] = previous["fleetActionContract"]
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
