# Input and compatibility plan review

## Residual finding

Residual actionable finding after fresh reread: PLAN.md:18’s zero-station release matrix preserves cross-target assigned-button deletion (down A/up B) but says every other zero-station release cancels. In live `InputCoordinator.react_mouse_event` (`src/input_coordinator.py:267-274`), down on assigned A is currently a no-op beyond `is_mouse_down`, so up on a locked path button purchases it and up on a speed button applies its action. The new matrix would silently break both cross-target release outcomes while PLAN:21/acceptance:56 claim locked purchase/speed compatibility, and TDD:44 only names generic cases. Make zero-station armed release delegate the complete historical release-target matrix (assigned delete, locked purchase, speed action, other no-op), or explicitly narrow compatibility and test the intentional change; add down-assigned/up-locked and down-assigned/up-speed real-event regressions.

## Final reread

Fresh reread of the patched live PLAN/REVIEW is CLEAN. The complete zero-station release-target matrix now matches `InputCoordinator` precedence (including cross-target locked purchase/speed), and the named regressions pin it. I found no remaining actionable input-semantics, compatibility, TDD, hidden-state, cleanup, interpolation/cache, or GM-05c scope defect.
