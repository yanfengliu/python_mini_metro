The `.claude` tree is not writable in this session either (same EPERM class), so I'll skip the memory note and deliver the review directly.

---

## Code Review — GM-01c (fresh-game overdue threshold 1→2; recursive/agent-play evidence → v3)

**Verdict: APPROVED.** No real bugs, public-compatibility regressions, stale documentation, process regressions, or missing validation found across the live working-tree diff.

### Review method / scope caveat

I could not execute the Validation Gates. The Bash tool failed session-wide (`EPERM: mkdir ...\.claude\session-env\...`) on every call including `echo ok`, `dangerouslyDisableSandbox` didn't help, and a spawned subagent inherited the identical block — so `git diff`, `python -m unittest`, `ruff`, and `npm test` were unrunnable. This review is a **static read of the live source/test/doc files** (Read/Grep/Glob), not a re-run of the gates. Test *pass* status is author-asserted, not re-verified by me. The 6 civ-engine 2.4.1-vs-2.2.0 Node failures were treated as known env noise per instructions, not product defects.

### What I verified against the live code

- **Alias agreement is structural, not coincidental.** `mediator.overdue_passenger_threshold` is the single backing field (`mediator.py:117`); `max_waiting_passengers` is a pure get/set property over it (`mediator.py:140-148`). Every writer (`recursive_playtest._apply_overdue_threshold:266`, `agent_play._apply_overdue_passenger_threshold:143`) routes to the same value, and `canonical_checkpoint` derives both `limits.max_waiting_passengers` (`recursive_checkpoint.py:395`) and `limits.overdue_passenger_threshold` (`:442`) from it, so `normalize_checkpoint`'s disagreement check (`:110-122`) can never trip on genuine runtime state. Config default `2` plus alias `2` (`config.py:53-55`); game-over fires at `waiting_over_limit >= overdue_passenger_threshold` (`mediator.py:965`).
- **Reset ordering is correct.** `env.reset()` replaces the mediator (`env.py:47`); both drivers apply the threshold *after* reset and before stepping/initial checkpoint (`recursive_playtest.py:298-300`, `agent_play.py:312-313`). Threshold validation runs *before* reset in agent-play (`iter_playthrough_observations:308-312`), proven by the `reset_count == 0` assertion (`test_agent_play_threshold.py:238`). The `ReplacingResetEnv` tests prove override survives a reset that sets 99/17/19 (`test_recursive_threshold_schema.py:186-225`, `test_agent_play_threshold.py:185-221`).
- **Version routing dispatches by immutable constants, never the mutable `SCHEMA_VERSION` alias:** `_overdue_threshold_for_document` (`recursive_contract.py:108-114`), `_reward_contract_for_document` (`:100-105`), `_checkpoint_version_for_schema` (v1 to 1, v2/v3 to 2, `recursive_playtest.py:277-282`), and `replayableInputs` (literal `=== 2/=== 3`, `playtest-verify.mjs:279-284`). Advancing the alias to v3 does not erase v2 routing.
- **Strict validation holds:** exact-key sets reject a v2 doc carrying `overduePassengerThreshold` (`_exact_keys`; test `test_recursive_threshold_schema.py:106,142`), and `_positive_int` (`recursive_contract.py:59-62`) / agent-play `type(threshold) is not int` (`agent_play.py:126`) reject bool, 0, negatives, floats, strings, None - tested in both modules.
- **Checkpoint schema correctly stays at v2** even for v3 scenarios; `normalize_checkpoint`/`canonical_checkpoint` reject `schemaVersion 3` (`recursive_checkpoint.py:64-68,204-208`; test `:137-140`). v1→line_credits+threshold 1, v2→deliveries+threshold 1, v3→deliveries+recorded threshold — pinned by `test_recursive_threshold_schema.py:144-184` and the fresh-process Node tests (`playtest-recursive.test.mjs:62-70,281-287`).
- **Tests genuinely distinguish literal v2 from the v3 alias** (in-process and fresh-process), and **docs match runtime**: `GAME_RULES.md:84`, `README.md:82` and `:200`, `ARCHITECTURE.md:177`, `PROGRESS.md:102`, and both fixtures are all consistent with the implemented behavior.

### Non-blocking observations (optional, not defects)

- Two near-duplicate 3-line threshold appliers exist (`recursive_playtest._apply_overdue_threshold` vs `agent_play._apply_overdue_passenger_threshold`) with slightly different fallback semantics. Intentional per the plan's "minimal plumbing" scope; fine to leave.
- `PlaythroughRecord.overdue_passenger_threshold` defaults to `1` (`agent_play.py:77`) while the fresh-game default is `2`. This is deliberate historical-compat for backward construction and is always overwritten by `run_agent_playthrough` (`:238,252`); not a bug.

Recommendation: since I could not run the gates, please confirm `python -m unittest -v` and the Node suite are green (modulo the known civ-engine pin failures) before committing — the code is correct on inspection, but that's the one thing this session couldn't verify for you.
