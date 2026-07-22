# Independent adversarial reviewer (harness subagent) — verbatim

Compensating reviewer spawned because the Claude CLI reviewer was unreachable (expired OAuth in a non-interactive session). General-purpose harness subagent, read-only, instructed to refute the change against the live files and upstream v7 `action.yml`.

---

I have completed my independent verification. All checks pass against the live files and the upstream v7 `action.yml` definitions.

## Review findings: `.github/workflows/test.yml` action major bumps

**No blocking issues. The change is sound.**

### Verified evidence

**1. Consistency across both jobs — PASS.** `test.yml` is the only workflow file (`.github/workflows/` contains just `test.yml`). Both jobs bump all three actions identically: `build` (ubuntu-latest) lines 14/21/27 and `rl-smoke` (windows-latest) lines 61/67/73 are all `@v7`. These six `uses:` statements are the only third-party action references in the file; every other step is a `run:` step. No action was left on an older major or the Node 20 runtime.

**2. Runtime — this is the actual fix, and it works.** All three v7 `action.yml` files declare `runs.using: node24` (confirmed by fetching `raw.githubusercontent.com/actions/<name>/v7/action.yml` for checkout, setup-python, setup-node). The prior majors (checkout v4, setup-node v4, setup-python v5) ran on the deprecated node20 runtime — the exact thing GitHub warned about in EVIDENCE.md:685. The bump moves all three to node24. Objective achieved.

**3. Input compatibility — PASS, every input still exists in v7.**
- checkout@v7: `path`, `persist-credentials`, `fetch-depth` — all present.
- setup-python@v7: `python-version`, `architecture` — both present; no deprecation notice on `architecture` (and `x64` is the default on the hosted x64 runners anyway, so it is a no-op even in the worst case).
- setup-node@v7: `node-version`, `cache`, `cache-dependency-path` — all present. (`cache: npm` still valid; v7 adds an unrelated optional `package-manager-cache` input that does not affect this usage.)

**4. Behavior-change checks — no impact on this workflow.**
- `persist-credentials`: v7 default is `true`, but both jobs set it explicitly to `false`, so any default change is irrelevant — the explicit value wins (and is the more secure choice, already in place).
- npm caching semantics: unchanged for `cache: npm` + `cache-dependency-path`. Confirmed `package-lock.json` exists at repo root (resolves `rl-smoke`'s path and, after checkout into `path: python_mini_metro`, the `build` job's `python_mini_metro/package-lock.json`). setup-node runs after checkout in both jobs, so the lockfile is present when caching resolves.
- Minimum runner version: node24 actions need Actions Runner >= 2.327.1; GitHub-hosted ubuntu-latest/windows-latest always satisfy this. No self-hosted runners are used.
- Note: the bump changes the actions' own *runtime* to node24 but does not change the Node the project installs (`node-version: "22"` is untouched), so the repo still runs its own commands on Node 22 per the >= 20.6 requirement.

**5. `@v7` is a valid current major — PASS.** All three `@v7` refs resolved to real `action.yml` content, confirming the tag exists for each. Floating major tags are a mutable-ref/supply-chain consideration, but the pre-existing workflow already used floating majors (`@v4`/`@v5`), so this change preserves — does not regress — the repo's convention. Combined with top-level `permissions: contents: read` and `persist-credentials: false`, exposure is minimized. SHA-pinning would be a reasonable optional hardening but is out of scope for this CI-hygiene bump and is **not a blocker**.

**6. Other references — author's claim confirmed.** The only pre-existing repo reference to the old versions is the intentional historical mention at `docs/threads/current/game-maturity/2026-07-11/1/EVIDENCE.md:685`. I read it: it is a verbatim record of a past CI annotation tied to a specific past run (run 29776047898) stating GitHub deprecated the node20 runtimes for `checkout@v4`, `setup-node@v4`, `setup-python@v5`. Leaving it unchanged is correct — it is an immutable historical evidence record, not live config; editing it would falsify the record. README.md, ARCHITECTURE.md, and PROGRESS.md have zero references. The remaining `@v4/@v5` hits (`codex.stdout.log`, `diff.md`) are this review thread's own working artifacts that necessarily quote the diff — not stale source references.

### Conclusion
Pure CI hygiene, correctly and consistently applied. Every input the workflow uses survives the v7 majors, the one behavior change (`persist-credentials` default) is explicitly overridden, hosted runners meet the node24 requirement, and the single remaining old-version mention is an intentional, correct historical record. No changes required.
