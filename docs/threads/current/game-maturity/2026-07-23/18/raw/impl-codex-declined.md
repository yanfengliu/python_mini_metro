# GM-09a implementation review — external Codex lane DECLINED

The escalated external Codex lane (`codex -m gpt-5.6-sol ... exec`) REFUSED this run with a safety egress decline: "This read-only CLI review would still transmit live repository code and review context to an external Codex service, and neither the user nor AGENTS.md specifically authorized exposing that payload to that destination." (It also declined a Claude MCP egress.) No output was produced.

This is a hard safety refusal, not a flake — the constitution and Codex's own message forbid working around it. Note: the external Codex lane ran successfully earlier THIS session (GM-07d/08a/08c impl reviews + the GM-09a plan review), so the decline is intermittent/policy-dependent.

Substitution for this behavior-PRESERVING refactor: the harness lane (below) independently reconstructed the pre-change HEAD code and recomputed the fingerprints (a non-circular determinism proof) and ran a 20,000-seed `choice(list)`-vs-`choice(tuple)` stress; plus a 60-seed empirical byte-identity check by the driver. Appropriate for a byte-identical change whose only behavioral delta is list↔tuple in `choice()`/iteration. Recorded honestly in EVIDENCE.
