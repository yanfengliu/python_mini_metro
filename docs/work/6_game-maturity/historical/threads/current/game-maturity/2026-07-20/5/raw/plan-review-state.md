# Independent GM-06a state and checkpoint plan review

Result: not clean on first pass.

1. P1 - the over-cap removal/refund semantics contradicted the clamp. The corrected contract must say every actual global removal decreases assigned count, while availability follows the clamped formula and may stay zero until an artificial deficit clears. Tests must cover successful and partial-failure over-cap removal.

2. P1 - the no-schema justification lacked the exact genuine-v1 and detached-graph proof it relied on. Both checkpoint v1 and v2 contain `progression.limits.num_metros` and normalized `structured.metros`; tests must pin `max(0, total - len(structured.metros))` for both versions, including over-cap. A detached path-only Metro must prove runtime/global assigned zero and checkpoint `structured.metros` zero even while `metroMotion` is one.

3. P2 - legacy HUD resolution was unspecified. Pin exact order: public property first; otherwise derive from complete `num_metros` plus `metros` compatibility surfaces; otherwise use the selected zero default.

Structured field names, additive raw-observation compatibility, frozen-differential reasoning, and all three recorded protocol/task fingerprints matched live code. No files were edited by the reviewer.
