# Initial review

HIGH — unsafe intermediate compatibility window (PLAN 16-17 vs 29). GM-02a can parse a self-consistent multiscale v2 manifest, but evaluate_rl.py:250-255 and train_rl.py:253-264 still construct VecFrameStack from only manifest.frame_stack until GM-02c. Add a GM-02a fail-closed guard: while VecFrameStack is active, accepted history must equal contiguous_history(frameStack); reject any other v2 descriptor before model/env load. Remove guard only in GM-02c when descriptor-driven wrapper is used everywhere.

MEDIUM — pin fingerprint enforcement at both trust boundaries. v2 parsing must recompute descriptor fingerprint and reject stored historyFingerprint mismatch immediately; validate_training_manifest/load_training_manifest should gain expected_history_fingerprint and issue a separate ManifestCompatibilityError on saved/requested layout mismatch. v1 derives the digest from frameStack. Evaluation may derive expected history from the authenticated manifest; resume compares an explicit request to saved before env/model construction.

MEDIUM — avoid dual-source factory API. Make create_training_manifest take the immutable history descriptor and derive both frameStack and historyFingerprint. Do not accept independent frame_stack + history unless a temporary compatibility path enforces exact equality; otherwise callers can create contradictory v2 objects before serialization.

MEDIUM — semantic fields must be closed literals, not merely fingerprinted strings. DecisionHistory should accept only offsets; its schema fixes offset unit=agent decisions, oldest→newest sample-major RGB channel concatenation, zero-fill, reset, and terminal semantics. from_dict exact-key/literal checks must reject a self-consistent fingerprint over unsupported semantics the wrapper would ignore. Offsets: nonempty, int-not-bool, nonnegative, strictly decreasing, final 0.

LOW — fixture wording: preserve at least one literal canonical pre-GM-02 v1 payload unmodified and byte/hash round-trip it; use separate literal documents or generated parser cases for N=1,4,8,other. Do not mutate one fixture then call every variant genuine.

Recommended v2 shape: exact old top-level key set plus history + historyFingerprint; keep frameStack checked against len(offsets). Parsed v1 retains schema=v1 and v1 to_dict shape, with derived in-memory history/historyFingerprint, so current canonical byte/hash preservation remains true.

Tests first: nested/outer exact keys; lowercase SHA format + valid-but-wrong digest; frameStack disagreement; fixed semantic tampering; equal-count descriptor mismatch through validate/load; v1 unknown/v2-injected keys; canonical v1 byte/hash roundtrip and derived offsets at N=1,4,8,13; fresh factory derivation; GM-02a multiscale resume/eval rejection before build_vector_env/load_model; training fingerprint includes history.py while content fingerprint excludes it.

Focused current baseline run directly: py313 unittest test.test_rl_manifest + test.test_rl_cli = 23/23 passed. No files edited.

# Re-review

APPROVED — no remaining substantive manifest/v1-v2/API findings. Evidence: corrected PLAN.md lines 18/31 close the GM-02a/b unsafe window by rejecting non-contiguous descriptors before the current train/evaluate paths can reduce them to frame_stack (live train_rl.py:236-264; evaluate_rl.py:250-255). Lines 17/30 require parse-time recomputation plus separate expected-history compatibility validation, addressing live validate_training_manifest's current protocol/task-only checks (manifest.py:391-416). Lines 16/31 make descriptor the factory's sole source and derive frameStack/fingerprint, avoiding contradictory inputs to current create_training_manifest (manifest.py:283-338). Lines 14/29-30 close semantic literals and exact nested keys rather than trusting arbitrary strings. Lines 16/30 preserve the exact v1 key set/schema serialization and one immutable literal byte/hash fixture while testing arbitrary positive N separately, preserving the canonical round-trip contract in test_rl_manifest.py:193-207. Read-only; no edits.

# Implementation finder

CLEAN — no grounded substantive manifest trust/schema findings. Parse-time v2 digest recomputation and frameStack agreement are enforced; v1 exact output branching and derivation preserve canonical bytes; drift replaces re-run frozen-dataclass invariants; train/evaluate noncontiguous guards precede artifact opening; and both identity modules are in `TRAINING_SOURCE_PATHS`. Focused core tests passed with expected optional skips, exact RL passed 49/49, and Ruff check/format passed. No edits.
