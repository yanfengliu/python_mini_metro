---
name: multi-cli-review
description: Use when running the multi-CLI (Codex + Claude) adversarial code review on high-risk changes or full-codebase audits — routes to the fleet-canonical runbook (pins, commands, output extraction, failure modes) plus python_mini_metro-specific notes.
---

# Multi-CLI review — python_mini_metro stub

**Read the fleet-canonical runbook now:** `../loop-ops/docs/skills/multi-cli-review.md` — current review model pins (the fleet's single bump site), exact CLI commands, `-o` output extraction, Windows gotchas, and failure modes. Do not act from memory of an older per-repo copy of this skill.

python_mini_metro-specific notes:

- Reviewer pin sites in scripts: NONE (verified 2026-07-10 — reviewer model strings appear only in AGENTS.md, this stub, and historical `docs/threads/` artifacts). The Codex PowerShell form below quotes the pinned model string, so re-sync it whenever the fleet bumps pins.
- Capture/artifact override: reviewer outputs are COMMITTED verbatim as thread artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/raw/` (`raw/codex.md`, `raw/opus.md`, extra instances as `raw/codex-2.md`, optional `raw/*.stdout.log` / `raw/*.stderr.log`) — this overrides the canonical never-staged `tmp/review-runs/` default; see AGENTS.md → Code review → Thread artifacts. Point the background poller at those paths (`until [ -s raw/codex.md ] && [ -s raw/opus.md ]; do sleep 8; done`).
- Failure-mode routing: record an unreachable CLI in the thread's `REVIEW.md` (this repo's replacement for the canonical's "devlog or progress log"), then retry it on the next iteration.
- Domain prompt enrichment: every review prompt in this repo also asks reviewers to flag process regressions, stale documentation, and missing validation (per AGENTS.md → Code review).
- PowerShell invocation forms: this repo's full-codebase reviews are historically driven from PowerShell, where multi-line prompts split into unexpected positional arguments — use the forms below instead of the canonical bash forms when driving from PowerShell.

Codex full-codebase reviewer (PowerShell) — keep the prompt in a file and pipe it via stdin (the trailing `-` reads the prompt from stdin); `-o` writes Codex's final message straight to the committed raw artifact, sidestepping the stdout prompt-echo problem; keep the marker discipline anyway as a safety net:

```powershell
Get-Content -Raw docs/threads/current/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.6-sol -c model_reasoning_effort='ultra' -a never -s read-only exec --cd . --ephemeral -o docs/threads/current/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
```

Claude full-codebase reviewer (PowerShell) — keep the prompt in a variable so PowerShell passes it as one argument:

```powershell
$prompt = Get-Content -Raw docs/threads/current/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
claude -p $prompt --model "opus[1m]" --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
```
