# GM-04c final reproducibility and mismatch-proof plan

Status: GM-04b is remotely finalized at evidence-only Commit B `41ecfc691ac4d4784acff549f06e3fe2f26e9c3b`, whose exact workflow run `29758092140` passed; the declared GM-04c local proof is complete without production changes, two independent payload reviews converged `CLEAN`, and changed-path hooks plus exact 18-path staging, cached diff, credential, dependency-surface, and exclusion gates pass; Commit A, push, and exact remote CI remain pending

Transaction marker: `[GM-04c:A]`

## Baseline and boundary

GM-04c begins from `main == origin/main == 41ecfc691ac4d4784acff549f06e3fe2f26e9c3b`. That GM-04b Commit B passed exact workflow run `29758092140`, including `build` job `88405558876` and `rl-smoke` job `88405560427`.

This unit records the live final reproducibility, complete guarded Node suite, clean recursive public-verifier result, and isolated hostile-resolution mismatch proof required by GM-04. It changes no production, test, package, lock, workflow, or dependency surface.

The proof authenticates the retained repository-owned pin while preserving the unrelated sibling. A task-owned isolated fixture may redirect only its own dependency resolution to exercise the mismatch guard; it must not mutate the production repository, retained pin, or sibling.

The recursive run directory is retained ignored evidence. Repeated-setup stdout, canonical suite output, isolated-drill JSON, and the reviewed harness source were terminal-observed ephemeral evidence and are recorded as such; they are not represented as retained artifacts. The removed harness was statically reviewed at SHA-256 `6C09AF80A153969D3E742F43268A7C2AB237E1FEEC1E0DB2FCE0B7E188421CFA`; line links in verbatim raw reviews are historical and no longer resolve.

## Required clean proofs

- Repeated canonical setup must remain stable and report the same exact retained pin and default-resolution identity without unnecessary rebuild, install, clone, or repair work.
- The fixed zero-argument canonical `npm test` body must register 245 tests and report 241 passed, four expected platform skips, zero failures, and all 44 frozen pre-GM04 test names retained.
- A clean recursive run must finish with no finding and no fix candidate, and the public verifier must independently accept its full checkpoint vector, transcript, findings, and inputs.
- Strict verification and default-resolution identity must resolve exactly to retained civ-engine 2.2.0 at commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` with runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`.
- Root and pin dependency audits must retain their accepted results, and both the tracked dependency material and exact staged evidence payload must contain no credential signature or secret material.

## Isolated mismatch proof

The isolated drill must make its own root resolution target the clean unrelated sibling at captured path `../civ-engine`, civ-engine 2.4.1, commit `2632daca2ea1d1330cf1270962941005354f775b`, runtime digest `8da72fd76e9f513773bb5f63c899321ffd7a9ef6dbb0cf82d2aec3dbba481971`, while the descriptor still expects captured path `.civ-engine-pin`, civ-engine 2.2.0, commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`. The independent comparison must report `matches.path: false` as well as false version, commit, and runtime-digest matches.

The canonical public guard must exit 1 with the categorical diagnostic `[civ-engine-guard] root civ-engine dependency needs repair` before the engine body starts. Expected and actual version, commit, and runtime digest are captured independently rather than reflected through the categorical production diagnostic.

The drill must remove its exact temporary fixture after proving the result. Production Git HEAD/status, the root dependency target, and retained pin and sibling fingerprints must remain unchanged.

## Evidence and cleanup boundary

The accepted clean recursive run is `output/recursive/recursive-2026-07-20T16-21-12-855Z-ea664784`; it completed eight operations with zero findings, and its public fresh-process verifier accepted all eight rows. Its `no-fix-candidate` outcome closes only the declared GM-04c finalization proof and does not complete GM-05 through GM-13 or the broader game-maturity roadmap.

Four old ignored output pre-commit cache roots remain retained because ACL-blocked descendants prevent safely proving complete task-owned removal: `output/gm04a-precommit-cache`, `output/gm04b-a3-precommit-cache`, `output/gm04b-final-precommit-cache`, and `output/gm04b-precommit-cache-final2`. They are cleanup limitations outside this tracked transaction, not proof inputs or commit content.

The exact task cache `C:\tmp\python-mini-metro-gm04b-precommit-cache` remains intentionally retained only through the GM-04c changed-path hook run. It is not commit content and may be reconsidered for exact scoped cleanup only after those hooks complete.

## Delivery sequence

1. Independently review the live tracked documentation payload against the retained artifacts and repository state; adjudicate every substantive finding without claiming review coverage that did not occur.
2. Run changed-path whitespace/end-of-file hooks, cached diff checking after exact staging, high-confidence credential scans over the tracked dependency material and staged payload, and scoped-path/exclusion audits.
3. Commit the exact evidence-only payload as `[GM-04c:A]`, push it, and wait for that exact commit's `build` and `rl-smoke` jobs before treating Commit A as remotely green.
4. Only after Commit A's exact workflow succeeds, create the evidence-only `[GM-04c:B]` finalization that records that result; push it and wait for its own exact workflow before marking GM-04 complete or opening GM-05.

## Acceptance

- The repeated setup, 245/241/four-skip canonical suite, clean recursive public verification, strict identity, audits, dependency-material and staged-payload credential scans, and isolated pre-body mismatch refusal with independently captured path/version/commit/digest values are all recorded with exact attributable evidence.
- Production remains unchanged, the isolated fixture is removed, the sibling and retained pin are preserved, and cleanup limitations are explicit.
- The tracked Commit A payload passes independent local review and required delivery gates before commit; no GM-04c remote result or remote approval is claimed until it exists.
- `no-fix-candidate` closes only this proof unit; the remaining roadmap stays open.
