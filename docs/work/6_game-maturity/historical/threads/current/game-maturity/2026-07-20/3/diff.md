# GM-05b selected-line mouse-redraw diff

Status: remotely finalized through exact-green implementation Commit A and evidence-only Commit B

- Reconciled GM-05a Commit B's exact remote success and opened `[GM-05b:A]` from `47b93491662ebe56a38aba8653d868ae66249d6c`.
- Added assigned-line button hold-drag-release redraw through real mouse events while retaining click deletion, cross-target deletion, purchase, speed, creation, and the existing structured replacement transaction.
- Added an immutable facade-owned draft, a pure render-only preview with separate bounded caching, selected/invalid button feedback, and exact-segment transition validation that prevents the confirmed immediate no-tick metro jump.
- Added 52 focused methods proving manual/structured equality, fast/fidelity pixel-policy reachability, malformed/canceled/unsafe cleanup, hover and blink feedback, cache/reference bounds, deterministic surfaces, and replay/checkpoint continuity.
- Split only the structural `InputCoordinatorHost` typing contract into a dependency-light module so `InputCoordinator` remains 442 lines; every changed handwritten file remains below 500 lines except the explicit 655-line Mediator facade.
- Updated public and durable documentation while preserving unrelated `.agents/`, ignored output/pin state, and the external review boundary. Implementation Commit A `37865d4` passed run `29786749550`; evidence-only Commit B `0d6f5b9` passed run `29787168196` and was reconciled by GM-05c.
