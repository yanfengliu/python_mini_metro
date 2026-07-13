"""Supervise clean, fresh-process RL temporal-history resource campaigns."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rl.profile_supervisor import (  # noqa: E402
    analyze_status_records as analyze_status_records,
)
from rl.profile_supervisor import (  # noqa: E402
    collect_source_state,
    runtime_metadata,
    sha256_file,
    supervise_worker,
    write_json,
)
from rl.profile_validation import (  # noqa: E402
    validate_worker_result as validate_worker_result,
)
from rl.resource_profile import (  # noqa: E402
    FALLBACK_CAMPAIGN,
    FALLBACK_CANDIDATES,
    MAC_ASSUMPTIONS,
    MAC_FORMULAS,
    PRIMARY_CAMPAIGN,
    PRIMARY_CANDIDATES,
    ProfileRepeat,
    counterbalanced_schedule,
    estimate_inference_macs,
    estimate_storage,
    evaluate_promotion,
)

CAMPAIGN_SCHEMA = "mini-metro-history-profile-campaign-v1"


def _campaign_contract(campaign: str) -> Any:
    if campaign == PRIMARY_CAMPAIGN:
        return PRIMARY_CANDIDATES, 3
    if campaign == FALLBACK_CAMPAIGN:
        return FALLBACK_CANDIDATES, 4
    raise ValueError(f"unsupported campaign: {campaign!r}")


def _worker_command(
    *, candidate: str, result_path: Path, seed: int, threads: int, interop: int
) -> tuple[str, ...]:
    return (
        sys.executable,
        str(REPO_ROOT / "scripts" / "profile_rl_history_worker.py"),
        "--candidate",
        candidate,
        "--result",
        str(result_path),
        "--seed",
        str(seed),
        "--torch-threads",
        str(threads),
        "--torch-interop-threads",
        str(interop),
    )


def run_campaign(args: argparse.Namespace) -> Path:
    candidates, default_repeats = _campaign_contract(args.campaign)
    repeats = default_repeats if args.repeats is None else args.repeats
    schedule = counterbalanced_schedule(tuple(candidates), repeats=repeats)
    source = collect_source_state()
    runtime = runtime_metadata()
    worker_script = REPO_ROOT / "scripts" / "profile_rl_history_worker.py"
    profile_script_sha256 = sha256_file(Path(__file__))
    worker_script_sha256 = sha256_file(worker_script)
    output_dir = args.output_dir or (
        REPO_ROOT
        / "output"
        / "rl-profile"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    run_summaries = []
    samples = []
    campaign_failures = []
    abort_campaign = False
    for repeat, row in enumerate(schedule):
        for position, candidate in enumerate(row):
            if abort_campaign:
                break
            run_source = collect_source_state(require_clean=False)
            if not run_source["clean"] or run_source["commit"] != source["commit"]:
                campaign_failures.append(
                    {
                        "candidate": candidate,
                        "kind": "source-state-invalid-before-worker",
                        "repeat": repeat,
                        "source": run_source,
                    }
                )
                abort_campaign = True
                break
            run_dir = (
                output_dir / f"repeat-{repeat:02d}-position-{position}-{candidate}"
            )
            result_path = run_dir / "worker-result.json"
            command = _worker_command(
                candidate=candidate,
                result_path=result_path,
                seed=args.seed,
                threads=args.torch_threads,
                interop=args.torch_interop_threads,
            )
            try:
                outcome = supervise_worker(
                    command,
                    run_dir=run_dir,
                    result_path=result_path,
                )
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                outcome = {
                    "failures": [{"error": str(error), "kind": "supervisor-exception"}],
                    "fullLifecyclePeakWorkingSetBytes": 0,
                    "schema": "mini-metro-history-profile-supervisor-v1",
                    "valid": False,
                    "workerResult": None,
                }
            outcome.setdefault("command", list(command))
            worker_contract_valid = False
            if outcome["workerResult"] is not None:
                contract_errors = validate_worker_result(
                    candidate,
                    outcome["workerResult"],
                    repo_root=REPO_ROOT,
                    seed=args.seed,
                    torch_threads=args.torch_threads,
                    torch_interop_threads=args.torch_interop_threads,
                )
                outcome["failures"].extend(
                    {"kind": "worker-contract-mismatch", "field": field}
                    for field in contract_errors
                )
                worker_contract_valid = not contract_errors
                outcome["valid"] = not outcome["failures"]
            post_source = collect_source_state(require_clean=False)
            post_profile_sha256 = sha256_file(Path(__file__))
            post_worker_sha256 = sha256_file(worker_script)
            source_stable = (
                post_source["clean"]
                and post_source["commit"] == run_source["commit"]
                and post_profile_sha256 == profile_script_sha256
                and post_worker_sha256 == worker_script_sha256
            )
            if not source_stable:
                drift = {
                    "kind": "source-state-changed-during-worker",
                    "sourceAfter": post_source,
                }
                outcome["failures"].append(drift)
                outcome["valid"] = False
                campaign_failures.append(
                    {"candidate": candidate, "repeat": repeat, **drift}
                )
                abort_campaign = True
            outcome.update(
                {
                    "candidate": candidate,
                    "analyticalInferenceMacs": {
                        **asdict(estimate_inference_macs(candidates[candidate])),
                        "assumptions": list(MAC_ASSUMPTIONS),
                        "formulas": dict(MAC_FORMULAS),
                        "total": estimate_inference_macs(candidates[candidate]).total,
                    },
                    "analyticalStorage": asdict(
                        estimate_storage(candidates[candidate])
                    ),
                    "position": position,
                    "profileScriptSha256": profile_script_sha256,
                    "repeat": repeat,
                    "runtime": runtime,
                    "profileScriptSha256After": post_profile_sha256,
                    "sourceAfter": post_source,
                    "sourceBefore": run_source,
                    "workerScriptSha256After": post_worker_sha256,
                    "workerScriptSha256": worker_script_sha256,
                }
            )
            write_json(run_dir / "run-summary.json", outcome)
            run_summaries.append(outcome)
            worker = outcome["workerResult"]
            if (
                worker_contract_valid
                and isinstance(worker, dict)
                and outcome["fullLifecyclePeakWorkingSetBytes"] > 0
            ):
                samples.append(
                    ProfileRepeat(
                        candidate,
                        repeat,
                        outcome["fullLifecyclePeakWorkingSetBytes"],
                        worker["rates"]["endToEndFps"],
                        outcome["valid"],
                        worker["workload"]["batchSize"],
                        worker["workload"]["nEpochs"],
                    )
                )
    decision = evaluate_promotion(
        samples,
        campaign=args.campaign,
        expected_repeats=repeats,
    )
    aggregate = {
        "campaign": args.campaign,
        "campaignFailures": campaign_failures,
        "decision": asdict(decision),
        "operationallyValid": (
            decision.complete
            and decision.all_valid
            and decision.settings_match
            and not campaign_failures
        ),
        "profileScriptSha256": profile_script_sha256,
        "repeats": repeats,
        "runSummaries": run_summaries,
        "runtime": runtime,
        "schedule": [list(row) for row in schedule],
        "schema": CAMPAIGN_SCHEMA,
        "seed": args.seed,
        "source": source,
        "torchInteropThreads": args.torch_interop_threads,
        "torchThreads": args.torch_threads,
        "workerScriptSha256": worker_script_sha256,
    }
    summary_path = output_dir / "campaign-summary.json"
    write_json(summary_path, aggregate)
    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        choices=(PRIMARY_CAMPAIGN, FALLBACK_CAMPAIGN),
        default=PRIMARY_CAMPAIGN,
    )
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--torch-threads", type=int, required=True)
    parser.add_argument("--torch-interop-threads", type=int, required=True)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_campaign(args)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        build_parser().error(str(error))
    print(f"campaign summary: {summary}")
    document = json.loads(summary.read_text(encoding="utf-8"))
    if not document["operationallyValid"]:
        print("campaign completed with invalid or incomplete repeats", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
