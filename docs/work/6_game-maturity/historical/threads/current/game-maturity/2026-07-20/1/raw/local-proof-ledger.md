# GM-04c local proof ledger

Evidence-source boundary: the recursive run directory below is retained ignored evidence. Repeated-setup stdout, canonical suite output, isolated-drill JSON, and the harness source were terminal-observed ephemeral evidence and are not retained artifacts. The removed harness was statically reviewed at SHA-256 `6C09AF80A153969D3E742F43268A7C2AB237E1FEEC1E0DB2FCE0B7E188421CFA`; raw line links are historical and no longer resolve.

Baseline: `main == origin/main == 41ecfc691ac4d4784acff549f06e3fe2f26e9c3b`; GM-04b Commit B exact workflow run `29758092140` passed `build` job `88405558876` and `rl-smoke` job `88405560427`.

Repeated setup: terminal-observed canonical setup completed repeatedly with stable retained pin and root-resolution identity; no production repair was required.

Canonical guarded suite: terminal-observed output reported 245 registered, 241 passed, four expected platform skips, zero failures, and all 44 frozen pre-GM04 names retained.

Recursive run: `output/recursive/recursive-2026-07-20T16-21-12-855Z-ea664784`; `run-result.json` records `completed: true`, `findingCount: 0`, `operationCount: 8`, `schemaVersion: 3`, `seed: 42`, and `transcriptRows: 8`.

Public verifier: fresh-process full-checkpoint-vector verification returned `ok: true`; original and replay final states, findings, and inputs matched across eight rows, with no verified finding IDs.

Strict identity: root resolution remained civ-engine 2.2.0 at commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` and runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`.

Audits: root dependency audit reported zero vulnerabilities; the pin development graph retained nine moderate dependency instances and zero high/critical; high-confidence scans of the ten tracked dependency surfaces and exact staged 18-path evidence payload found no recognized credential signature.

Integrity: production Git HEAD/status, the retained pin and sibling fingerprints, and root resolution were unchanged; the exact isolated mismatch fixture was removed.

Scope: `no-fix-candidate` closes only the declared GM-04c proof. Independent review, changed-path hooks, exact staging, cached diff/credential/dependency/exclusion gates, and full staged review pass; Commit A, delivery, and exact CI remain pending, and the broader roadmap remains open.
