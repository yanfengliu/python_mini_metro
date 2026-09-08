# GM-01a implementation review

## Conclusion

APPROVED after fixes. Three independent in-process live-code lanes reviewed semantics/API compatibility, persisted replay/checkpoint compatibility, and maintainability/test/process quality. All High and Medium findings were reproduced or checked against the live tree, fixed, and re-reviewed to approval.

This approval covers GM-01a only. HUD/game-over wording and verified spawn cadence remain GM-01b; the initial overdue-passenger threshold remains GM-01c; longer visual history remains GM-02; mediator/test decomposition remains GM-03.

## Reviewer availability

- The high-risk change normally also requires Codex and Claude multi-CLI review. In GM-00 the environment allowed the initial external Codex pass, then rejected further private workspace transfer to both Claude and targeted Codex review. That policy limitation still applies; no bypass or repeated upload was attempted.
- The compensating review used three independent in-process lanes, each directed to verify claims against live symbols, call signatures, schemas, tests, and serialized fields. Semantics, persistence, and quality lanes all returned APPROVED after the fixes below.

## Findings and disposition

| Severity | Finding | Verified disposition |
| --- | --- | --- |
| High | Canonical-only privileged snapshot reads broke legacy-shaped demonstrator mediators | Restored fallback reads to `total_travels_handled` and `score`; demonstrator and player-environment tests pass |
| High | `run_scenario(env_factory=...)` stopped accepting the established zero-argument factory shape | Added signature-aware construction, mode adaptation, fail-closed v2 support checks, and v1/v2 zero-argument regressions |
| Medium | Agent-play records omitted a supplied environment's default timestep, so replay could stop advancing time | Persisted the effective timestep and pinned original/replay times in a regression |
| Medium | Invalid mutable reward modes and invalid foreign environment modes silently selected the legacy objective | Added a validating property, explicit reward branches, fail-closed foreign-mode handling, and mutation tests |
| Medium | Agent-play schema and reward contract were independently selectable; v2 could omit its explicit contract | Bound v1/schema-less records to `line_credits_delta`, required v2 contracts, and covered explicit v1, schema-less, v2, and malformed replay |
| Medium | Checkpoint v2 omitted reward mode even though it changes the next reward for identical state | Added reward mode to v2, synthesized legacy mode in v1 normalization, rejected mismatched v1 emission, and proved mode is the only checkpoint difference |
| Medium | Legacy reward oracle drifted from historical `structured.score` to another checkpoint view | Restored exact v1 semantics and exact finding wording; the masking test mutation was removed |
| Medium | Oracle contract inference guessed from schema instead of the checkpoint's recorded mode | Made normalized checkpoint mode authoritative, rejected explicit disagreement, and authored a finding for mid-transcript drift |
| Medium | Migrating the sole default fixture to v2 removed durable Node verification of genuine v1 omission | Added a public fresh-process v1 verifier case and independently replayed a pre-change artifact exactly |
| Medium | Recursive source/test files crossed the 500-line target | Extracted `recursive_contract.py` and `test_recursive_checkpoint.py`; all five affected files are below 500 lines and public imports remain re-exported |
| Medium | Checkpoint reward-mode test used different seeds, so it could pass for unrelated state differences | Matched seeds and asserted equality after removing only the reward-mode field |
| Low | A new test omitted `deepcopy`, and Windows temp cleanup could hit transient `EBUSY` | Added the import and bounded cleanup retries; focused verifier paths pass |
| Low | README described copied structured `score` as writable, and a test duplicated an assertion | Corrected the wording and removed the duplicate |

## Verification

- Focused merged semantic surface: 150/150 Python tests passed before the organization-only split.
- Final recursive surface: 27/27 Python tests passed.
- Full core environment: 341 tests passed with 8 expected optional-RL skips.
- Exact RL environment: 341 tests passed with no skips.
- Node verifier unit: 5/5 passed; public v1/v2 verifier paths: 2/2 passed.
- Full Node baseline: 23/42 passed; the same 19 pinned-engine tests fail because the live sibling is civ-engine 2.4.1 versus the declared 2.2.0 pin. Pinned CI is required before remote finalization.
- Full Ruff check and format passed across 99 Python files; all 26 changed-file pre-commit hook inputs passed; `git diff --check` passed; two-frame dummy-video app smoke passed.

## Residual limits

- `PrivilegedSnapshot.display_score` remains a read property over the new `line_credits` field; no in-repo caller keyword-constructs that internal validation dataclass. Treating its constructor as public would require a separately designed compatibility initializer.
- The pre-existing `src/mediator.py` and `test/test_mediator.py` size debt remains scheduled for GM-03 rather than being mixed into this contract migration.
- Full local Node parity remains blocked until GM-04 installs the pinned civ-engine in isolation. Targeted changed paths are green, and `[GM-01a:A]` cannot be remotely finalized unless pinned CI succeeds.
