# REVIEW — CI action Node 20 deprecation bump (ci-actions-node20 / 2026-07-21 / iteration 1)

## Change under review

`.github/workflows/test.yml` only. Bumps three GitHub Actions off the deprecated Node 20 action runtime onto Node 24, identically across the `build` (ubuntu-latest) and `rl-smoke` (windows-latest) jobs:

- `actions/checkout` v4 → v7 (current latest v7.0.1)
- `actions/setup-python` v5 → v7 (current latest v7.0.0)
- `actions/setup-node` v4 → v7 (current latest v7.0.0)

Motivation: GitHub deprecated the Node 20 action runtime and force-runs the old majors on Node 24; all three v7 actions declare `runs.using: node24`, so the bump clears the hosted-runner deprecation annotation. Pure CI hygiene; no application code.

This surface is "locally high-risk" per AGENTS.md (`.github/workflows/*`) and a supply-chain trust change (new major of third-party actions), so it escalated to the multi-CLI adversarial review.

## Reviewers

| Reviewer | Model / kind | Verdict |
|---|---|---|
| Codex | `gpt-5.6-sol`, `model_reasoning_effort=ultra`, read-only sandbox | No findings (`raw/codex.md`) |
| Independent harness subagent | general-purpose, read-only, adversarial lens | No blocking issues (`raw/subagent-reviewer.md`) |
| Claude CLI | `claude-fable-5[1m]` | UNREACHABLE — OAuth session expired, could not refresh in this non-interactive session (`raw/claude-cli.unreachable.txt`). Compensated per runbook by spawning the extra independent harness reviewer above. Retry on a future interactive session. |

Both reachable reviewers read the live files and each action's upstream v7 `action.yml` independently, and converged.

## Findings & disposition

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | none | All inputs the workflow uses survive the v7 majors: checkout `path`/`persist-credentials`/`fetch-depth`; setup-python `python-version`/`architecture`; setup-node `node-version`/`cache`/`cache-dependency-path`. | Confirmed by both reviewers against v7 `action.yml`. No action. |
| 2 | info | Precision: across v4→v7, setup-node ALSO removed the unused `always-auth` input (not only setup-python's `pip-install`). The workflow uses neither, so operationally harmless — but the original "only pip-install removed" claim was incomplete. | Corrected here for accuracy. No workflow change needed. |
| 3 | none | Behavior changes don't affect this workflow: `persist-credentials` v7 default flips to `true` but both jobs set it explicitly `false`; `cache: npm` + `cache-dependency-path` semantics unchanged and `package-lock.json` exists at repo root; Node 24 actions need Actions Runner ≥ 2.327.1, satisfied by GitHub-hosted ubuntu-latest/windows-latest. Project toolchain `node-version: "22"` is untouched. | No action. |
| 4 | low (optional) | `@v7` is a floating major tag (mutable ref). Full-SHA pinning is stronger immutability. | Out of scope for this hygiene bump and NOT a blocker: GitHub-owned actions, push-only workflow, top-level `permissions: contents: read`, no secrets supplied, and the pre-existing workflow already used floating majors (`@v4`/`@v5`) — this preserves, not regresses, the convention. Noted as future optional hardening. |
| 5 | none | The one remaining `@v4`/`@v5` mention at `docs/threads/current/game-maturity/2026-07-11/1/EVIDENCE.md:685` is a verbatim historical record of a past CI annotation; README/ARCHITECTURE/PROGRESS have zero references. | Correctly left unchanged — editing would falsify the historical record. |

## Local validation

- `pre-commit run --files .github/workflows/test.yml`: `check-yaml`, `end-of-file-fixer`, `trailing-whitespace` all Passed; no hook edits.
- Diff scoped to six `uses:` lines; no other file touched.

## Convergence & gate

Two independent reviewers, zero blocking findings, full agreement. Both explicitly require the empirical gate both reviewers named: **both hosted CI jobs (build on Ubuntu, rl-smoke on Windows) must pass green** on the pushed branch before this is considered delivered. That run is the definitive proof the node24 actions execute correctly on the hosted runners.

Disposition: **approved**; proceed to commit, push, and confirm green CI on both platforms.
