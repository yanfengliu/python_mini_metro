# Smooth rendering implementation plan

1. Capture a deterministic baseline frame and add red tests for complete render-state purity, stable logical segment identities/state-machine trajectories, symmetric half-slot lanes, corner/loop/reverse/stopped metro projection, cache invalidation, and fixed-clock timing.
2. Make holder/metro passenger positioning, station-effect painting, and UI painting observational; initialize station/button hitboxes at reset and prepare game-over/resize layout before input. Compare first-frame raw input through windowless and GUI sessions.
3. Keep the exact logical path/padding sequence, transition timing, and indices centered and topology-built; add immutable visual layout and a one-entry value-keyed cache, and project logical metro progress onto visual lanes/connectors.
4. Add cached antialiased halo/stroke/round-cap routes and outlined line-colored metros while preserving z-order. Cache keys cover path order/identity/station identity and coordinates/loop/color/style/surface size; zero-size viewports do not allocate targets.
5. Add `FixedStepClock`, pure previous/current pose interpolation, and shared `GameSession`. Process `prepare_layout -> raw input -> fixed updates -> render`; remove requested vsync and use one `Clock.tick(60)` pacing authority, consume paused/game-over wall time without backlog, and reset cadence on restart.
6. Capture the after frame and validate repeatable pixels, semantic antialias/centering, bounded cache reuse, long rendered-vs-never-rendered checkpoint equivalence, and no model/entity/UUID allocation during repeated renders. In a fresh dummy-SDL process with no display mode, prove state-only construction creates no render resources and headless pixel rendering is repeatable.
7. Update architecture, rules/user docs, and progress; run the full Python suite, changed-file Ruff/format, pre-commit, and independent adversarial review before committing.

The external Codex/Claude review commands remain unavailable because the security layer denied repository-context export earlier in this task; independent in-process reviewers will be preserved under `raw/`.
