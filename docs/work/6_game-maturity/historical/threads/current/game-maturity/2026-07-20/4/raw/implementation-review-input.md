# GM-05c implementation review - input and lifecycle

Scope: live `InputCoordinator`, facade state, desktop adapter, handle derivation, checkpoint/array invisibility, PlayerPixel reachability, and the focused/adjacent tests after all implementation fixes.

## Initial findings and dispositions

- Opaque legacy event positions were treated as outside when no layout metadata existed. The compatibility branch now treats them as in-view, with the explicit desktop outside sentinel retaining cancellation; a real adapter-to-`InputCoordinator` regression pins the distinction.
- Cleanup assumed every historical/direct test facade exposed path buttons. The cleanup boundary now tolerates buttonless facades while preserving full cleanup for production hosts.
- The structural `InputCoordinator` dependency whitelist did not include the intended focused handle modules. The architectural contract was updated to admit only those exact dependencies.
- Final-target selection, ambiguous-hit consumption, false-to-true game-over cleanup, and both endpoint directions were reread against live code and their real-event/state regressions.

## Preserved final reviewer output

`CLEAN. Verified two-phase activation, cleanup, the live letterbox path, structured and array equality, both endpoint directions, fast/fidelity precedence blockers, the frozen differential, and changed-file Ruff.`

The external multi-CLI path remained unavailable at the established repository-export authorization boundary. This is compensating in-process evidence and does not claim external approval.
