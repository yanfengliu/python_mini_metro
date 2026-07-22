# REVIEW — SHA-pin hardening (ci-actions-node20 / 2026-07-21 / iteration 2)

## Change under review

`.github/workflows/test.yml` only. Replaces the floating `@v7` major tags (landed and CI-verified in iteration 1, commit 7beb43f) with immutable full commit SHAs plus `# vX.Y.Z` version comments, across both jobs:

| Action | Ref before | Ref after | Comment |
|---|---|---|---|
| actions/checkout | `@v7` | `@3d3c42e5aac5ba805825da76410c181273ba90b1` | `# v7.0.1` |
| actions/setup-python | `@v7` | `@5fda3b95a4ea91299a34e894583c3862153e4b97` | `# v7.0.0` |
| actions/setup-node | `@v7` | `@820762786026740c76f36085b0efc47a31fe5020` | `# v7.0.0` |

Each pinned SHA is the commit its already-reviewed v7 tag resolves to, and each pinned version is also that action's current latest release — so this is a pure reference-immutability change with **no version drift and no behavior change**. The actions run the identical code iteration 1 already reviewed and proved green.

## Proportionality of review

Iteration 1 already ran the full high-risk discipline (Codex + an independent harness reviewer) on the v7 *versions* and confirmed CI green on both hosted platforms. SHA-pinning does not change which code executes; the only new risk it introduces is **"is each pinned SHA the exact commit the official tag resolves to, from the correct `actions/*` repo?"** — a mechanical, machine-verifiable property.

Accordingly the review here is one **independent adversarial re-resolution** plus the empirical CI gate, rather than a second full multi-CLI pass (which would be disproportionate for a SHA swap; the `claude -p` CLI also remains unreachable this session — expired OAuth). This scaling matches the fleet rule "these rules are strong defaults… scale the approach to the task."

## Reviewer

| Reviewer | Kind | Verdict |
|---|---|---|
| Independent harness subagent | general-purpose, read-only, adversarial | **OVERALL: PASS** (`raw/sha-pin-verify.md`) |

The reviewer distrusted the pinned values and independently resolved each tag from its official repo two ways (`commits/<tag>` and `git/ref/tags/<tag>`), confirming both agree and equal the pinned SHA.

## Findings & disposition

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | none | All three pinned SHAs independently re-resolve to the exact commit of their commented v7 tag, from the exact `actions/<name>` repo; all are 40-char lowercase hex. | CONFIRMED per action. No action. |
| 2 | none | All three tags are lightweight refs (object type `commit`), so each SHA resolves directly to a commit — no annotated-tag-object dereference trap. | Verified. No action. |
| 3 | none | Both occurrences of each action (build + rl-smoke) are byte-identical; no floating `@vN` tag remains; `test.yml` is the only workflow file, nothing left unpinned. | Verified. No action. |
| 4 | none | Each comment version is a real published, non-draft, non-prerelease release on the v7 line, and also the current latest release — no stale/yanked pin. | Verified. No action. |

## Local validation

- `pre-commit run --files .github/workflows/test.yml`: check-yaml / EOF / trailing-whitespace all Passed; no hook edits.
- Diff is exactly the six `uses:` lines; no other content changed.

## Gate

Delivery gated on **branch CI green** on the SHA-pinned commit (proves the pinned SHAs actually resolve and the actions run), then a fast-forward merge to `main` and a **green CI run on `main`**. Disposition: **approved**; proceed to commit → push → verify branch CI → fast-forward `main` → verify main CI.
