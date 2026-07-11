# RL framework review

## Outcome

Approved after finder/fix/verifier iteration. Three independent in-process reviewers inspected the player contract, Gymnasium/SB3 behavior, exact-byte artifact and provenance boundary, seed semantics, CLI safety, CI, locks, documentation, and pinned Node integration; all three reported no remaining important finding after the verified fixes. The required external Codex and Claude plan/diff commands were attempted, but Codex lacked API authentication and both Claude model attempts were account-limited; those commands returned no review content and are not counted as approvals. Their raw outputs are preserved under `raw/`.

## Findings and dispositions

| Severity | Finding | Disposition |
|---|---|---|
| High | Artifact verification hashed one read but model loading and manifest parsing could consume later filesystem bytes. | Fixed. Manifest, index, and model are each captured once, authenticated from those bytes, parsed or loaded from the same immutable snapshot, and covered by mutation-after-verification tests. |
| High | Evaluation could overwrite authenticated run artifacts and did not prove content/trainer/runtime compatibility remained unchanged after model execution. | Fixed. Manifest, index, model, and every indexed path are protected; final provenance is recaptured before result output; independent content, trainer, and runtime drift injections fail closed and write nothing. |
| High | Requested resume/evaluation seeds could be displaced by SB3 load state, while repeated callback evaluations advanced rather than replayed the declared seed suite. | Fixed. Load applies the requested seed explicitly, standalone evaluation derives its default from the manifest, and every callback evaluation resets to the same recorded suite. Real callback and fresh/resume lifecycle checks prove terminal seeds 10042 and 10077. |
| Medium | Gymnasium behavior could silently skip when the dependency was absent, bool-valued action elements passed integer validation, and true game-over precedence over the horizon was not explicit. | Fixed. Contract tests import Gymnasium directly, mixed bool actions are rejected, and game-over termination wins over simultaneous horizon truncation. |
| Medium | Player-equivalence evidence did not pin exact event dispatch, cursor/press pixels, fidelity rendering, or future visible station content. | Fixed. Surface-level tests now assert exact routed events and coordinates, cursor/pressed marker pixels, fidelity profile output, future station pixels, fixed tick cadence, and a positive-delivery trajectory. |
| Medium | Runtime compatibility and trainer fingerprints omitted direct dependencies and the new RL lock. | Fixed. Shapely and shortuuid are captured with the other runtime packages, and both universal hash locks contribute to the trainer fingerprint. |
| Medium | CI did not exercise all focused RL CLI tests or a real authenticated resume path. | Fixed. The Windows RL smoke installs the locked stack, runs the complete focused suite, trains/evaluates a fresh spawned run, resumes with a distinct seed, and asserts tags, parent digests, and terminal seeds. |
| Medium | Documentation had stale input-location text and did not fully explain locked setup, exact-byte provenance, or deterministic scope. | Fixed. README, architecture, and game rules now match the implemented controls, locks, seed behavior, artifact boundary, runtime packages, and the fact that opaque structured IDs remain session-unique. |
| Low | Full-repository Ruff checks exposed pre-existing import ordering and formatting drift in touched surfaces. | Fixed mechanically without changing behavior; all 94 Python files now pass lint and format checks. |

## Independent verification

- Player/RL finder: approved after 62/62 focused tests, fresh-process pixel-hash comparison, exact protocol checks, and repeated evaluation-seed verification.
- Artifact/CI finder: approved after 32 focused tests, Ruff, formatting, and diff checks; it recorded the managed-environment limitation rather than treating the local environment as updated.
- Independent verifier: reproduced identical repeated callback seed/observation suites, one-read manifest/index/model behavior, rejection of 5/5 protected output paths, and three independent post-evaluation drift failures with no result writes; 10/10 focused regressions passed.

## External review availability

- Plan review: Codex CLI 0.144.1 reached pinned `gpt-5.6-sol` but received HTTP 401 due missing API authentication; Claude Fable was quota-limited; the required `opus[1m]` fallback timed out after ten minutes without output.
- Final diff review: Codex again received HTTP 401; Claude Fable reported its Fable limit; the required `opus[1m]` fallback reported the Claude session limit. No external response contained a code finding or approval.
- Disposition: proceed under the repository's documented unavailable-CLI fallback with the three grounded in-process approvals, retain all raw failure evidence, and retry the unavailable CLIs on the next high-risk iteration.

## Validation

- Python: the direct managed `py313` interpreter ran against the exact locked workspace site-packages and passed 305/305 tests with no skips; focused RL 62/62 passed.
- Static checks: Ruff lint and format passed for all 94 Python files; `git diff --check` passed; direct checked-out pre-commit hook implementations passed for changed non-raw files, and the commit hook normalized missing EOF terminators on two Claude limit messages without changing their textual payload.
- Supply chain: both Python hash locks audited with zero known vulnerabilities; repository npm audit reported zero vulnerabilities.
- Real lifecycle: fresh spawned train/evaluate and authenticated resume/evaluate completed with exact parent/model/manifest/index binding, requested seed authority, protected output rejection, tamper rejection, and final drift recapture.
- Cross-runtime: pinned civ-engine build and 41/41 Node tests passed; proposal-only recursive replay was exact for 8/8 bounded cases with zero findings.
