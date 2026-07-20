BLOCKED — one acceptance gap.

- The frozen GM-04c contract requires independently captured actual and expected **path/version/commit/digest** ([GM-04 plan line 21]). The new payload records version, commit, and digest, but omits the actual and expected path values: [PLAN.md line 29], [REVIEW.md lines 19–21], and [EVIDENCE.md line 642]. Add the configured/physical expected fixture pin path and actual sibling-resolution path, while preserving the truthful boundary that the categorical guard message itself contains none of this metadata.

Everything else checked clean: `HEAD == origin/main == 41ecfc6`; run `29758092140` is live-successful at that SHA with jobs `88405558876` and `88405560427`; retained recursive evidence verifies 8/8 with `no-fix-candidate` correctly scoped; pin/root/sibling identities match; all four ACL-limited caches exist; the temporary fixture and drill file are absent; `.agents/` remains excluded; and the cursor truthfully awaits `[GM-04c:A]`.
