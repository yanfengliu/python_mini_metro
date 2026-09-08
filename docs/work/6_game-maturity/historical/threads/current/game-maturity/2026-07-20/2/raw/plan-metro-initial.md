Not clean. I found two acceptance-threatening ambiguities and two coverage gaps.

1. [P1] Two-station ambiguity must apply to every metro state, not only stopped metros.

The plan discusses unresolved ambiguity only in the stopped paragraph at `PLAN.md:35`. Moving path and padding mappings at lines 31–33 do not explicitly require collecting every candidate and rejecting non-unique results.

A two-station loop is:

```text
P(A→B), padding@B, P(B→A), padding@A
```

because loop construction adds the reverse closure at `src/entity/path.py:68`. Canonical lane direction makes both path segments occupy the same physical line, and both padding segments are zero-length at their respective stations.

Consequently:

- `P(A→B), forward` and `P(B→A), backward` both represent physical A→B.
- On a reordered two-station candidate, both directions of the zero-length padding can represent the same A-B-A anchor but lead to different logical continuation states.

A first-match implementation could preserve position and target yet silently choose a different future traversal.

Correction: every binding category must collect all candidate `(segment_index, is_forward)` states. Prefer the old direction only when it leaves exactly one candidate; otherwise reject. Never choose by segment-list order.

Required tests:

- `[A,B]` loop → `[B,A]` with a metro on each path segment in both directions.
- The same replacement with a metro on each padding segment in both directions.
- Assert either the documented unique binding or exact zero-effect rejection.
- `[A,B]` → `[A,B,C]` must still accept genuinely unique states.

2. [P1] The no-op ordering is ambiguous against the mandatory metro invariants.

`PLAN.md:21` says an exact no-op returns `True` before effects, while line 29 says every target metro must satisfy exact ownership and segment/index consistency. The plan does not explicitly order the read-only consistency audit before the no-op return.

This matters because a successful action advances time at `src/env.py:73`. A same-topology action against a metro with a stale segment reference or invalid index could return `True`, then immediately enter `Path.move_metro()`, which asserts a segment and depends on the live index state at `src/entity/path.py:168`.

Correction: order the transaction as:

```text
selector/completed-path validation
→ topology normalization
→ metro/holder ownership and live-reference validation
→ exact no-op return
→ candidate factory and binding
```

The no-op must precede factories and RNG, but not invariant validation.

Required test: corrupt one metro’s index/reference, issue an exact-topology replacement, and assert `False`, no time advancement, and exact checkpoint/reference equality.

3. [P2] Endpoint equality does not prove that a moving metro is physically on its segment.

`PLAN.md:31` and `:33` require matching old/candidate endpoints, but do not explicitly validate `metro.position`. `Path.move_metro()` uses the current position as an unconstrained starting point and travels directly toward the endpoint at `src/entity/path.py:183`. An off-line or beyond-endpoint metro would therefore be accepted and continue diagonally, violating physical-continuity acceptance.

Correction:

- For a non-zero segment, require the position’s projection to fall within `[0,1]` and its perpendicular residual to be within a documented floating tolerance.
- For a zero-length segment, require exact equality with the endpoint.
- Perform this against the old segment; equal candidate geometry then proves preservation.

Required test: in a two-metro line, place one metro slightly off its logical segment. The entire edit must reject without changing the valid metro.

4. [P2] The TDD matrix does not explicitly cover the asymmetric production transition branches.

The transition has distinct branches for:

- one-segment lines,
- first and last linear segments,
- first/last loop wrap,
- forward and backward interior traversal,

at `src/entity/path.py:224`. Generic “stopped,” “loop closure,” and “ambiguity” coverage at `PLAN.md:62` can miss a direction-specific off-by-one.

Add production-derived oracle tests for:

- Two-station linear: stopped at both termini after both travel directions.
- Three-station linear: stopped at the interior station from each direction.
- Three-station loop: forward closure arrival at the first station and backward arrival through segment zero.
- Final loop padding in both directions.
- Every path and padding state of a two-station loop.
- Multi-metro case with several safe bindings plus one unsafe wrap/padding binding, proving no binding is applied.

Generate the old stopped states through real `Path.move_metro()` endpoint transitions instead of manually fabricating indexes.

Residual risks:

- Rebuilt segment and endpoint objects will have new identities. Logical position remains continuous, but render interpolation keyed by segment index can still show a one-frame visual discontinuity; that belongs to GM-05b but should be retained as an explicit follow-up.
- Rejecting unresolved two-station edits is safe but may make equivalent station-order reversals return `False`; document that as intentional.
- Position-consistency tolerance needs one fixed value and boundary tests.
- No-op transaction tests should use `dt_ms=None`; a successful environment action otherwise advances time by design.
