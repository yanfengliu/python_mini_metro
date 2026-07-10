---
name: multi-cli-review
description: Use when running the multi-CLI (Codex + Claude) adversarial code review on high-risk changes or full-codebase audits — current review model pins, exact CLI commands, sandbox flags, output extraction, and CLI failure modes.
---

# Multi-CLI review runbook

This is the mechanics companion to AGENTS.md → Code review. Policy (when multi-CLI review is required, the review aspects, the reviewers-must-read directive, convergence criteria, and the review artifact conventions) lives in AGENTS.md; this file is how to actually run the CLIs. Read this file before every multi-CLI session.

## Current review model pins (single bump site)

| CLI | Model | Effort | Notes |
|---|---|---|---|
| Codex | `gpt-5.6-sol` | `-c model_reasoning_effort=ultra` | `ultra` verified 2026-07-09; earlier models capped at `xhigh` |
| Claude | `opus[1m]` | `--effort max` | tracks the latest Opus alias; `[1m]` selects the 1 M-token-context variant — quote the model string so the shell doesn't glob-expand the brackets |

Bump review pins here first, per the AGENTS.md model-currency rule, with a one-line smoke test before committing; then sync any repo-local scripts that hard-code reviewer pins (known sites in this repo: NONE — replace this note if a grep of scripts finds hard-coded reviewer models). If this repo pins app-facing LLM models for its own features, that policy lives in the repo's own docs, not here.

## Pre-flight

Always upgrade the Codex CLI before each review session (defensive against silent model-name rejection and sandbox-policy regressions in older builds): `npm install -g @openai/codex@latest`, then verify with `codex --version`.

## Prompt assembly

Start from the baseline below and **enrich it with task-specific context** — the change's intent, prior-iteration findings to verify, files to focus on, and an anti-regression checklist. The bare baseline returns generic feedback; useful reviews need the specifics.

> "You are a senior code reviewer. Flag bugs, security issues, and performance concerns. Do NOT modify files or propose patches. Only return findings, explanations, and suggestions in plain text. Only point out an issue if it is real and important. If there is no issue, say so instead of nit-picking."

Every prompt must additionally include the reviewers-must-read directive (quoted in AGENTS.md → Code review) and this repo's standing enrichment: ask reviewers to also flag process regressions, stale documentation, and missing validation (per AGENTS.md → Code review).

Codex prompts must also include the marker sentence (see Reading Codex output below): `Begin your review with the literal token "===BEGIN-REVIEW===" on its own line and end with "===END-REVIEW===" on its own line. Do not emit those markers anywhere else in your output.`

## Commands

Codex diff review:

```bash
git diff [branch] | codex exec --model gpt-5.6-sol -c model_reasoning_effort=ultra -c approval_policy=never --sandbox read-only --ephemeral <prompt>
```

**Do NOT pass `--ignore-user-config`.** That flag bypasses `~/.codex/rules/default.rules`, which is what permits codex on this Windows machine to use Windows-native commands (`findstr`, `type`, `dir`, `ls`) when its bash wrapper hits the PowerShell deny rule. Without those rules, codex's `read-only` sandbox blocks every shell tool and the reviewer silently falls back to "review without reading the code." Verified 2026-05-02.

Claude diff review (diff piped via stdin):

```bash
git diff [branch] | claude -p --model "opus[1m]" --effort max --append-system-prompt <prompt> --allowedTools "Read,Bash(git diff *),Bash(git log *),Bash(git show *)"
```

Claude full-codebase review (no diff): pass the prompt as the positional argument — `claude -p "<full prompt>" --model "opus[1m]" --effort max --allowedTools "Read,Glob,Grep,Bash(git diff *),Bash(git log *),Bash(git show *),Bash(wc *),Bash(ls *),Bash(find *)"`. `--append-system-prompt` is unnecessary there and the long-prompt-as-stdin form is not needed.

For full-codebase reviews generally, drop the `git diff` pipe and let each CLI agentically explore the workspace from its CWD; keep the same model/effort flags.

## PowerShell invocation forms (this repo)

This repo's full-codebase reviews have historically been driven from PowerShell, where multi-line prompts split into unexpected positional arguments. Use these forms when driving reviews from PowerShell instead of Git Bash.

Codex full-codebase reviewer — keep the prompt in a file and pipe it through stdin; the trailing `-` reads the prompt from stdin and `-o` writes Codex's final message straight to the raw artifact (which sidesteps the stdout prompt-echo problem below; keep the marker discipline anyway as a safety net):

```powershell
Get-Content -Raw docs/threads/current/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.6-sol -c model_reasoning_effort='ultra' -a never -s read-only exec --cd . --ephemeral -o docs/threads/current/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
```

Claude full-codebase reviewer — keep the prompt in a variable so PowerShell passes it as one argument:

```powershell
$prompt = Get-Content -Raw docs/threads/current/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
claude -p $prompt --model "opus[1m]" --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
```

## Per-CLI codebase-reading capability

Grounded reviews require reviewers that can actually read the repo:

- **Claude** reads via the Read/Glob/Grep tools you grant it (`--allowedTools "Read,Glob,Grep,..."`). Treat as load-bearing for code-vs-spec correctness. Caution: a spawned `claude -p` reviewer with `--allowedTools` is not hard-sandboxed — audit `git status` after a Claude review and prefer the Codex read-only sandbox when rigor matters.
- **Codex** can read files when `--sandbox read-only` runs WITHOUT `--ignore-user-config` (see above). Smoke-test occasionally with `echo "Read X and report" | codex exec --sandbox read-only --ephemeral` — codex must return content, not bail on "PowerShell blocked."

## Running

Diff reviews take ~5 minutes per CLI on a multi-hundred-line diff. Run both CLIs in parallel with `run_in_background: true`, capturing each CLI's output under the active thread's `raw/` directory (`docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/raw/`) — in this repo raw reviewer outputs are committed verbatim as thread artifacts (see AGENTS.md → Code review → Thread artifacts). Wait via a single background `until` poller (`until [ -s raw/codex.md ] && [ -s raw/opus.md ]; do sleep 8; done`) so the harness's no-long-sleeps guard doesn't fire and you don't poll repeatedly.

## Reading Codex output

Codex's captured stdout echoes the entire piped stdin (including the prompt that quotes the BEGIN/END markers as instructions) plus exec-sandbox chatter, then prints the actual review TWICE near the end. A naive `awk` from the first marker captures the PROMPT (which contains the literal marker strings as instructions to Codex), not the review. This was the root cause of the "Codex unreachable" misdiagnosis observed in impls 16–24 of the aoe2 v0.1.6 thread.

Correct extraction (only the actual review, NOT the prompt-echo):

```bash
# Slice everything from the FIRST `^codex$` line onward — Codex prints
# this header right before its real response. Then grab the BEGIN/END
# block. This avoids matching the markers inside the prompt-echo.
sed -n '/^codex$/,$p' codex.txt | awk '/===BEGIN-REVIEW===/{p=1; next} /===END-REVIEW===/{exit} p'
```

Wrong extraction (the bug): `awk '/===BEGIN-REVIEW===/{p=1; next} /===END-REVIEW===/{exit} p' codex.txt` grabs the FIRST pair, which is the literal markers in the prompt-echo. Every review using this extraction silently lost Codex's actual findings.

Fallback when markers are missing: `wc -l codex.txt`, then `Read` with `offset = lines - 250`. Or `sed -n '/<\/stdin>/,$p' codex.txt | head -300`.

Claude output is clean — markers optional there.

## Failure modes

If a CLI is unreachable (quota exhaustion, model name rejected by harness), proceed with the remaining reviewer and note the unreachable CLI in the thread's `REVIEW.md`. Convergence is the signal to stop iterating; one reviewer is acceptable for a single iteration when the other is unreachable, but always retry the unreachable CLI on the next iteration.
