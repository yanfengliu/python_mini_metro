# GM-01c implementation review

## Conclusion

APPROVED after fixes. Three independent in-process live-code lanes found one HIGH and two MEDIUM defects; every claim was independently reproduced, fixed, and re-reviewed to approval. The Opus fallback also approved the final live fixes. No HIGH or MEDIUM finding remains.

## Reviewer availability and dissent

- Fleet-pinned Fable was unavailable because its usage limit was reached, so the runbook-mandated `opus[1m]` fallback was used.
- The first Opus static review approved the pre-fix diff and explicitly treated the dataclass threshold default as deliberate. That conclusion was wrong: three in-process reviewers and a driver reproduction proved a v3 omission silently replayed threshold 1. The raw dissent is preserved unchanged in `raw/opus.md`; substantive evidence outweighed vote count.
- The targeted Opus re-review confirmed all fixes but could not execute shell gates because its `.claude/session-env` creation failed with EPERM. The driver ran every reported gate directly.
- Fleet-pinned Codex CLI 0.144.1 failed both initial and post-fix attempts with HTTP 401 missing authentication. Representative error output and session IDs are preserved; no authentication bypass was attempted.

## Findings and disposition

| Severity | Finding | Verified disposition |
| --- | --- | --- |
| High | V3 `PlaythroughRecord` omission inherited dataclass threshold `1` and replayed as valid | Field compatibility default is now `None`; v3 rejects it before reset; real-dataclass regression added |
| Medium | Threshold-blind environments could capture default `1` or accept a dynamically fabricated inert attribute | Capture/replay require canonical or legacy threshold control; threshold-blind regressions fail closed |
| Medium | Persistent cursor instructed resumers to restart completed plan/TDD work | `STATE.md` now resumes at fix verification, full gates, and Commit A |

## Verified contracts

- A fresh game ends on the second inclusive overdue station passenger, not the first; riders do not count and explicit threshold 1 remains terminal on the first.
- Config/runtime aliases address one canonical field without adding validation or changing legacy zero/negative assignment semantics.
- Genuine recursive v1/v2 and agent schema-less/v1/v2 evidence replays at threshold 1. V2 retains deliveries reward; strict v3 records/replays its positive non-boolean threshold after reset.
- Recursive scenario and checkpoint versions are decoupled: v1 to checkpoint v1, v2/v3 to checkpoint v2. V2 checkpoint aliases must agree.
- Protocol/task hashes remain unchanged and only the environment-content hash changes, keeping old RL artifacts fail-closed by default.

## Verification at convergence

- Focused post-fix surface: 55/55 passed.
- Full core: 377 tests passed with 8 expected optional-RL skips. Exact RL environment: 377/377 passed with no skips.
- Full Ruff check passed; Ruff format reported all 103 Python files formatted; `git diff --check` passed.
- Changed-file pre-commit passed all applicable hooks across the complete GM-01c file set without modifying source.
- A two-frame dummy-video `src/main.py` smoke passed.
- Fresh-process v3 verification matched inputs, findings, and all eight checkpoint digests; Node verifier unit surface passed 6/6; literal-v2 public replay passed 1/1.
- Full local Node baseline passed 25/44 and failed exactly the same 19 civ-engine 2.4.1-versus-pinned-2.2.0 cases. Pinned CI must pass the complete 44-test suite.
- The exact 12-seed thresholds 1/2/3 aggregates reproduced; repository default matched explicit threshold 2 on 12/12 seeds.

## Residual limits

- The fixed-route baseline remains directional evidence, not human or trained-policy balance proof; GM-11 owns broader balance promotion.
- `src/mediator.py` remains over the hard ceiling after minimal alias plumbing; GM-03 owns its staged decomposition and no tests were added to the oversized mediator test.
- Codex CLI authentication and the local civ-engine pin mismatch remain external limitations recorded above; neither was bypassed.
