# Game maturity roadmap re-review - Codex

You are re-reviewing a persistent high-risk implementation roadmap after your original report in `docs/threads/current/game-maturity/2026-07-11/1/raw/codex.md` found three High and seven Medium defects. Do not modify files or propose patches. Return only remaining real High/Medium findings with live file/line evidence, or say APPROVED.

Begin with `===BEGIN-REVIEW===` on its own line and end with `===END-REVIEW===` on its own line.

Mandatory grounding directive: Verify every claimed resolution against the current live codebase and current `PLAN.md`, `STATE.md`, `DECISIONS.md`, `EVIDENCE.md`, and `THRESHOLD_BASELINE.md`; grep for the referenced symbols, schema keys, fingerprints, public IDs, reward paths, CLI behavior, and file paths. Do not approve from this prompt or the prior report alone.

Specifically try to refute these claimed resolutions:

1. Transactional work units now use identifiable `[unit:A]`/`[unit:B]` commits, remote CI, live Commit-B lookup, failed-CI reopening, and archival recovery without an infinite metadata-commit regress.
2. `STATE.md` has exact work-unit granularity, finer map/upgrade units, and requires per-configuration/seed training and per-checkpoint/held-out-seed evaluation rows, each remotely finalized with locators and hashes.
3. Map selection uses a versioned task descriptor/fingerprint and genuine legacy descriptor reconstruction rather than inserting fields into an old hash.
4. GM-06 no longer requires nonexistent saves; GM-07 saves preserve public IDs and introduce pause reasons before menus/tutorial/progression.
5. Deliveries/credits migration requires writable aliases, checkpoint v1 normalization, recursive-input v1 legacy reward reconstruction, versioned agent-play and terminal metrics, and genuine old regressions.
6. Threshold evidence is durably reproducible with exact command/seeds/route/horizon/output and remains explicitly directional.
7. History has a separate fingerprint, training-source coverage, arbitrary v1 contiguous stacks, genuine legacy bytes, staggered multi-slot reset tests, and measured promotion criteria.

Also flag any new process regression or contradiction introduced while fixing the prior findings.
