# GM-03e review synthesis

## Baseline

The live 110-test passenger/simulation/route/path/overload/environment/checkpoint/oracle/render slice passes at repository baseline `2c4cd4fe484222549fd177455dd413859983ad50`. GM-03d Commit B `b1e419e21080fd5bd43e1ac6a4eef7e264f732ec` passed exact run `29386306430`; current HEAD passed exact run `29411000340`.

## Plan review

Three independent live-code lanes covered the passenger-flow boundary, the reserved GM-03f input/layout boundary and line budget, and an adversarial compatibility/evidence refutation. The first boundary pass corrected the planned extraction from 15 to 16 methods by adding passenger-owned application of bulk route proposals while retaining route queries and proposal generation in `RoutePlanner`.

The boundary and refutation lanes then found three substantive issue classes: wrapper-entry capture of late color/size and router/progression collaborators; failure to freeze the three separate per-tick graph builds; and a differential promise without the durable archive/isolated-child/drift-guard/artifact/event-trace/`--expected` contract required by GM-03d precedent. The corrected plan now resolves color/size/factories per due station, router iterator methods at their original one-time construction points, and the progression delivery hook per passenger; it preserves exception-sensitive counter reset, explicitly forbids graph reuse across the pre-move/planning/exchange phases, and requires a named non-mutating verifier with generator-effect traces.

All three live-code lanes approved the corrected boundary, invariants, `984 - 346 + 97 = 735` line model, TDD sequence, GM-03f exclusion, and A/B transaction. No substantive plan finding remains.

The fleet-required external lanes were attempted after upgrading Codex CLI to 0.144.6. The fleet-pinned Codex invocation exhausted WebSocket and HTTPS retries with HTTP 401 missing authentication; both attempt logs are preserved. The fleet-pinned Claude invocation failed because its OAuth session expired and could not be refreshed. Neither external lane produced a review or approval. The runbook fallback is the three independent in-process live-code lanes above, with the unavailable services recorded truthfully and scheduled for retry during implementation review.

## Implementation review

The frozen TDD sequence is complete. Twelve facade/effect characterizations passed against untouched production; the direct component module then produced exactly one intended loader error, `ModuleNotFoundError: No module named 'passenger_flow'`. After implementation, the 24 new direct/facade/effect tests passed, followed by the 134-test focused consumer slice.

`src/passenger_flow.py` now owns the 16 frozen algorithms through a call-scoped structural host and resolver thunks, while every real public `Mediator` signature and canonical collection/collaborator remains facade-owned. The final physical sizes are 448 lines for the component and 735 for `src/mediator.py`; all new handwritten test and verifier files remain below 500 lines. Protocol, task, and training fingerprints are unchanged, while the content fingerprint changes intentionally because the runtime source boundary changed.

The archived-baseline verifier materialized exact commit `2c4cd4fe484222549fd177455dd413859983ad50` through `git archive` and ran baseline and candidate in separate bytecode-disabled child processes with import-origin and before/after source-drift guards. Its two cases, five canonical records, and 80 mutation-sensitive events cover pause/speed/spawn/waiting, all three graph phases, two deliveries, transfer, boarding, arrival/route/fallback proposal effects, adjacent live-list skipping, iterator finalization, and destination/reducer/plan/delivery callable lifetimes. Baseline, candidate, canonical artifact, and `--expected` replay are byte-identical at 110,080 bytes with SHA-256 `d096c039cc613e70b38f6a137f83aaaa1b1404626040801d012fe29e9856da32`. After a reviewer exposed Windows checkout conversion, exact-path `.gitattributes` rules forced LF and a temporary-index `core.autocrlf=true` rematerialization retained the same bytes/digest and passed replay.

Two independent in-process semantic lanes returned `CLEAN` after method-by-method comparison with `2c4cd4f`, focused lifetime/evaluation-order analysis, import/retention checks, and live regression probes. The process/evidence lane found stale implementation/cursor text, copied model pins, one inaccurate warning description, and the Windows EOL portability defect; all findings were accepted and closed. Its final re-review returned `CLEAN` after refreshing the 37-path pre-staging scope, fingerprints, hashes, line budgets, clean-checkout replay, documentation, and `.agents/` exclusion.

The fleet-pinned external implementation lanes were retried against the live tree. Codex CLI 0.144.6 again exhausted WebSocket and HTTPS retries with HTTP 401 missing authentication, and Claude again failed because its OAuth session expired. Exact outputs are preserved in `raw/codex-implementation.stdout.log` and `raw/claude-implementation.md`; neither unavailable lane is approval.

Local regression evidence is green: py313 core passed 560 tests with 12 expected optional-RL skips, and the exact RL environment passed 563/563 with no skips. Ruff and format checks are green for the final Python scope. Changed-path pre-commit passes all 36 hook-safe paths; two byte-verbatim external failure captures are intentionally excluded from mutating EOF/trailing-whitespace hooks after exact recapture. The intended/live and staged sets agree at 38 paths; hook-safe cached check, credential/dependency scans, staged LF/size proof, and `.agents/`/ignored-output exclusion pass with no unstaged tracked file. Commit A, push, and exact remote CI remain pending.

## Commit A remote gate

Commit A `7ac89cf100e13a256ec3cbe7550d3e6926a31d23` is pushed to public `origin/main`, and exact workflow run `29719845761` completed successfully. `build` passed in 39 seconds and `rl-smoke` passed in 3 minutes 39 seconds. The evidence-only Commit B records this result before GM-03f begins.
