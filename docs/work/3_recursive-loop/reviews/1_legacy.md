# Recursive loop implementation review

## Reviewer availability

The external Codex and Claude commands required for a high-risk multi-CLI pass were attempted during plan review, but the security layer denied repository-context export before either reviewer received content. The limitation and converged three-reviewer in-process plan pass are preserved in iteration 1. Implementation review therefore used independent in-process finder and verifier passes grounded in the live tree.

## Findings and dispositions

- **High — lock ownership race: fixed.** `recursive-ledger-lock.mjs` uses unique owner tokens, live-process checks, heartbeats, token-checked stale recovery, and token-checked release. Boundary tests cover a live stale heartbeat, dead owner, and successor ownership.
- **High — torn run/pass authority: fixed.** Schema-v2 write-ahead intents contain both manifests and portable targets before either file or row is authoritative. Reconciliation creates and reads back both manifest files, batches missing rows into both ledgers, confirms exact equality, and only then deletes the intent.
- **High — source TOCTOU: fixed.** The orchestrator recaptures source immediately before finalization. Drift replaces any success/proposal with `run-failed`, records `source-changed`, and preserves final-state evidence.
- **High — linked runtime outside provenance: fixed.** The live resolved `civ-engine` package is pinned by name, version 2.2.0, commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, and line-ending-canonical 365-file runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`. Regressions prove Windows/Unix text line endings are equivalent and that a content mutation in gitignored `dist/` is rejected while Git remains clean.
- **High — engine execution before attribution: fixed.** The bootstrap captures and validates both source inventories before dynamically importing the pass and verifier modules that load `civ-engine`; the ending recapture closes the persistent-change window.
- **Medium — incomplete final drift evidence and stale exit result: fixed.** Source mismatch errors retain ending provenance, and the black-box drift regression proves the final state and patch both exist, the paired manifests record `source-changed`, and the public CLI exits nonzero from that attributed result.
- **Medium — unrecoverable torn JSONL tail: fixed.** Locked recovery truncates only an unterminated final fragment. Terminated or middle corruption fails closed.
- **Medium — repeated intent scans: fixed.** One reconciliation reads/indexes both ledgers once and drains all valid intents in deterministic order.
- **Medium — incomplete documentation map: fixed.** Architecture and user docs now describe engine provenance, final recapture, the split lock module, and manifest-plus-ledger recovery.
- **High — provenance-schema upgrade stranded retained rows: fixed after acceptance.** New manifests now write `source-state-v2`; strict legacy readers accept the bounded historical v1 shapes (without engine data, with the earlier engine summary, or with the current summary) while rejecting corrupt digests and unknown fields. A real retained ledger reconciled an interrupted v1 finalization, appended v2 rows, and ended with seven matched run/pass rows and zero pending intents.
- **Medium — source-version tags failed open: fixed.** Unknown-only, mixed known/unknown, and duplicate source-version tags are rejected; truly pre-version rows are accepted only when they carry no source-state payload.

## Verification

The final independent re-review found no substantive remaining issue after inspecting the live fixes and rerunning the focused provenance/end-to-end suites (17/17).

- Python: 193/193 `unittest` tests passed on Python 3.13.10.
- Node: 41/41 contract tests passed.
- Ruff changed-file check and format check passed.
- Pre-commit hooks passed for the complete intended change set.
- `pip-audit -r requirements-locked.txt --disable-pip`: no known vulnerabilities.
- `npm audit --audit-level=low`: 0 vulnerabilities.

## Post-commit acceptance

- Final clean pass `recursive-2026-07-10T18-34-36-249Z-e32f24d7` ran at commit `0890e29517b5dc26faf3591c8d12b9a604460735`, used `source-state-v2`, matched the pinned engine runtime, and returned `no-fix-candidate`.
- Canary pass `recursive-2026-07-10T18-35-06-823Z-798b5f2b` retained a one-line `src/env.py` patch, returned `proposal-only`, and selected stable class `observation-path-topology-mismatch`. Its promoted regression failed red with `[0, 1, 2] != [2, 1, 0]`.
- After byte-for-byte restoration, the promoted regression passed and clean pass `recursive-2026-07-10T18-35-41-715Z-3569c73d` returned `no-fix-candidate` at the same commit with clean source and the pinned engine runtime.
- Retained failure drills at the final commit recorded missing-Python spawn failure `recursive-2026-07-10T18-34-38-319Z-5fbc85ed`, node-as-Python drive failure `recursive-2026-07-10T18-34-37-484Z-892dc1fe`, and unparseable-scenario drive failure `recursive-2026-07-10T18-34-36-430Z-0832bac2`. The retained aggregate has ten matched run/pass rows and zero pending intents.
