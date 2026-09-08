I've now verified everything against live symbols. Key confirmation: `Mediator.__init__` (mediator.py:57-62) takes only `seed`/`context`; the `overdue_passenger_threshold` on the RHS of line 117 is the **module-level config import** (line 16, value `2`), so every fresh `Mediator(seed=seed)` (env.py:47) bakes in threshold 2 — "threshold-two" is real, and replay overrides it via attribute assignment after reset. There is no JSON serialization of `PlaythroughRecord` anywhere (grep shows `json.dumps` only in `recursive_*`/`rl/*`), so the `None` default only ever flows through the in-memory validation paths I traced.

My review is complete. Here is the verdict.

---

## Re-review: GM-01c — APPROVED

**Scope/method caveat.** Bash is blocked session-wide (`EPERM: mkdir ...\.claude\session-env\...`) on every call, including from a spawned subagent — so I could not execute the Validation Gates (`python -m unittest`, `ruff`, Node baseline) or `git diff`. This is a **static trace of the live working-tree source + tests** (Read/Grep), tracing each test assertion against the code rather than re-running it. Test *pass* status is inferred, not re-executed. (The prior iteration-4 `raw/opus.md` review hit the identical block and recorded the same caveat.) Note that `raw/opus.md` is a **pre-fix** review — it describes `overdue_passenger_threshold` defaulting to `1` (opus.md:25), whereas live `agent_play.py:77` is now `None`; that raw report predates the fixes under review here.

### Fix 1 - v3 record missing its required threshold no longer inherits a silent default - CONFIRMED

- `agent_play.py:77`: field default is now `int | None = None` (was `1`).
- `_record_overdue_passenger_threshold` (`agent_play.py:117-128`): for v3 it rejects a missing attr (`:123-124`) and rejects any non-positive / non-`int` value including `None` via `type(threshold) is not int or threshold <= 0` (`:126-127`).
- Ordering: it is called at `iter_playthrough_observations:305`, **before** `env.reset()` at `:308` - so an invalid v3 record raises before any reset.
- Tests: the **actual-dataclass** case (`test_agent_play_threshold.py:241-251`) constructs a real `PlaythroughRecord(schema=V3, ...)` with no threshold -> `None` -> `ValueError`, and the `_MISSING`/`None`/`True`/`False`/`0`/`-1`/`1.5`/`"2"` sweep (`:224-239`) each assert `env.reset_count == 0`. `type(True) is int` is `False`, so bools are correctly rejected.

### Fix 2 - capture/replay require a real threshold capability (canonical or legacy) - CONFIRMED

- Capture: `_environment_overdue_passenger_threshold` (`agent_play.py:131-141`) reads `overdue_passenger_threshold`, else `max_waiting_passengers`, else raises `"environment does not expose..."`; called post-reset at `run_agent_playthrough:234`.
- Replay: `_apply_overdue_passenger_threshold` (`agent_play.py:144-151`) writes the same two aliases, else raises; called post-reset at `iter_playthrough_observations:309`.
- Both fail closed on a threshold-blind mediator - verified by `test_capture_and_replay_fail_closed_without_a_threshold_control` (`:253-285`), which asserts capture and replay each raise `"does not expose"` with `reset_count == 1` (fabrication is impossible; the env is exercised, not bypassed).
- Real-env grounding: the live `Mediator` exposes `overdue_passenger_threshold` as a settable attr (`mediator.py:117`) and `max_waiting_passengers` as a read/write property over it (`:140-148`), so real captures/replays hit the canonical branch - no universal fail-closed regression. Legacy-only capture is exercised by `MetricEnv` (`test_agent_play.py:43`, exposes only `max_waiting_passengers`).

### Fix 3 - persistent cursor (STATE.md) no longer tells resumers to restart completed work - CONFIRMED

- `STATE.md:11` status = "implementation review fixes in progress; rerun focused/full gates and re-review before Commit A"; `:22-25` "Resume here" step 1 = "Verify the confirmed agent-play strict-v3 and fail-closed capability fixes, then re-review iteration 4/ to convergence"; ledger `:56` marks GM-01c "adversarial review". The cursor points at verify-and-re-review, not redo.

### v1/v2/v3 compatibility - CONFIRMED

- **Schema-less & v1:** both `_record_reward_contract` (`:101`) and `_record_overdue_passenger_threshold` (`:118`) default a missing `schema` to v1 -> threshold `1`, `line_credits_delta` enforced (`:104-108`). A v1 record carrying a delivery contract raises `"legacy..."` (`test_agent_play.py:182`).
- **v2:** threshold `1` (`:121-122`); `reward_contract` required (`:109-110`), verified by `"require reward_contract"` (`test_agent_play.py:184`). A default-`None` threshold on a v1/v2 dataclass is never read, so it is harmless (`test_old_style_record_constructor_defaults_to_legacy_contract`).
- **v3:** requires reward_contract plus strictly-positive non-bool int threshold; strict identifiers and the v3 alias advance is pinned by `test_public_schema_aliases_keep_v1_immutable_and_advance_current_to_v3` and `test_literal_v1_v2_and_v3_identifiers_remain_supported`. Capture to replay round-trips the recorded threshold (`test_new_capture_records...`, `test_v3_replay_applies_threshold_after_supplied_environment_reset`, zero-arg factory case).

### Non-blocking observation (not a defect, no action required)

`agent_play._apply_overdue_passenger_threshold` and `recursive_playtest._apply_overdue_threshold` (`recursive_playtest.py:266-274`) are near-duplicate 3-line appliers with different error strings; both fail closed and are functionally equivalent. Intentional per the plan's minimal-plumbing scope - a Low nit, not a High/Medium defect.

**No remaining High or Medium defects.** The three prior grounded findings are each fixed and regression-guarded, and v1/v2/v3 compatibility holds. **APPROVED** - subject to the driver confirming `python -m unittest -v` and the Node baseline are green (modulo the known civ-engine 2.4.1-vs-2.2.0 pin failures), which I could not execute this session.
