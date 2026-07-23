# GM-09a PLAN — Adversarial Review (harness lane, verbatim)

Verified against live code. Empirically reproduced the two load-bearing invariants (legacy fingerprint reconstruction + the byte-compat descriptor switch). Core design sound; 2 MAJOR + MINOR/NIT.

## LEGACY BYTE-COMPAT — VERIFIED, cannot refute
Prototyped the switch: map-absent output is byte-identical to today's task_descriptor (canonical_json sorts each branch's keys independently; the two paths never interact) — `canonical_json(proposed(spec, map_id=None)) == canonical_json(task_descriptor(spec))` True. Map-bound differs and carries all three keys. `TaskSpec(FAST,6,"deliveries",4).fingerprint()` == fixture `c2ef342f…`; `protocol_fingerprint` unchanged (69c604ac…). A v1/v2 manifest builds a map-less spec and preserves the hash — PROVIDED the impl never adds a key to the map-absent branch (byte-lock test mandatory).

## MAJOR-1 — `--map classic` default breaks legacy resume
scripts/train_rl.py:230-235,257-269: on resume `spec` is built from CLI args and used as expected_task_fingerprint (line 260) + `task_spec_from_manifest(resume_manifest) != spec` (line 269). `--map` default classic → resuming a v1/v2 manifest yields map-bound spec vs stored map-absent c2ef… → `task fingerprint mismatch` (manifest.py:194-199). No `--map` value expresses "legacy". Contradicts the plan's "legacy validates on resume". Evaluate is fine (evaluate_rl.py:220 reconstructs from the manifest, no CLI map). Fix: on resume inherit map from the resume manifest (precedent: _resolve_algorithm_and_history train_rl.py:169-207).

## MAJOR-2 — to_dict/from_dict v2-exact-equality drops history on v3
manifest_schema.py:246,256: history emitted only `if self.schema == TRAINING_MANIFEST_SCHEMA` (v2). _V3_KEYS ⊇ v2 includes history, so a v3 to_dict omits history → _require_exact_keys raises missing history. from_dict has no v3 branch. Fix: widen history conditionals to {v2,v3}; add elif v3 → expected_keys=_V3_KEYS; add a v3-only map-keys block; add v3 to SUPPORTED.

## DETERMINISM — reproducible today; test must cover more
get_random_stations reads config globals; get_station_spawn_position reads screen dims + 8-candidate loop. A map-parameterized generator must substitute at exactly those read points, same order: the `idx>=start and random()<chance` short-circuit (idx 0-9 draw no random()), the unique-shape-list order, the 8-candidate weighted choices, the retry `>=2` threshold + initial slice. CRITICAL: station gen precedes generate_distinct_path_colors on the SAME python_random stream — an off-by-one that leaves stations coincidentally identical still shifts colors + trajectory. The determinism test must lock stations AND path_colors AND a stepped trajectory vs a clean pre-change worktree. Use additive keyword-only params defaulting to config globals so the 6 existing callers stay byte-identical.

## MINOR — env default must stay legacy
test_player_env.py:280-284 asserts PlayerPixelEnv().task_spec == TaskSpec(). Passes only if the env defaults map_id=None (map binding comes from CLI/thunk). The plan's "env threads the map" must NOT default the env to Classic.

## MINOR — env.py inaccurate; NIT — append fields last
MiniMetroEnv (env.py) builds no TaskSpec; the "player_env.py/env.py" pairing is a phantom surface — at most a Mediator(map_definition=) param. TaskSpec map fields MUST append after max_episode_steps (~15 positional call sites).

## Save deferral / high-score / isolation — sound (with locks)
D-026 blesses save-map absence with one implicit map; deserialize overwrites stations/rng so a loaded Mediator's map is cosmetic; save-v1.json stays byte-frozen. High-score: source map from map_id keeps "classic" iff CLASSIC.map_id=="classic"; pin the literal in a test. maps not in the isolation forbidden set; no cycle if maps.py doesn't import mediator.

## Verdict: NOT CLEAN — fix MAJOR-1 (resume inherit) + MAJOR-2 (v3 history/branches); pin the byte-lock + determinism(+colors+trajectory) tests; env defaults map None; append fields last. Large but coherent; no split required (harness view).
