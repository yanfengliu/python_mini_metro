# GM-01a implementation review scope

This iteration reviews the canonical delivery/line-credit implementation and every compatibility surface changed with it.

The diff:

- separates lifetime deliveries from spendable line credits while retaining writable aliases;
- makes structured rewards default to deliveries and preserves explicit legacy credit-delta reconstruction;
- migrates internal pixel reads without changing terminal-metrics-v1 serialized keys;
- versions agent-play, recursive scenario/input, and canonical checkpoint records with genuine v1 replay paths;
- migrates the checked-in recursive fixture to v2 delivery reward and binds reward contract into verifier input comparison;
- extracts recursive document contracts and checkpoint tests so all newly enlarged recursive files remain below 500 lines; and
- updates public API, architecture, rules, persistent state, progress, evidence, and review documentation.

The review baseline is `0411e68f1a4fa83e6777480059ce5dce80a82774`. `.agents/` is pre-existing untracked user state and is outside this diff.
