# GM-03e reviewed diff

## Production boundary

- Add dependency-light, stateless `PassengerFlow` with a call-scoped structural host and late resolver thunks for facade-owned factories, globals, graph/search/plan functions, router iterators, and the per-rider delivery hook.
- Replace the 16 frozen `Mediator` algorithm bodies with exact-signature real wrappers while keeping canonical entities, lists, maps, RNG, clocks, pause/speed/game-over flags, progression, routing, and public effects on the facade.
- Reduce `src/mediator.py` from 984 to 735 physical lines; keep `src/passenger_flow.py` at 448 lines.

## Verification boundary

- Add 12 baseline-green facade/effect characterizations and 12 direct component contracts; preserve the expected-red missing-module run before production existed.
- Add a non-mutating archived-baseline differential runner and support module, both below 500 lines, plus one canonical artifact and digest summary. Exact baseline, candidate, and `--expected` replay are equal at 110,080 bytes with SHA-256 `d096c039cc613e70b38f6a137f83aaaa1b1404626040801d012fe29e9856da32` across two cases, five canonical records, and 80 mutation-sensitive events; exact-path `.gitattributes` rules preserve those LF bytes through Windows `core.autocrlf=true` clean checkouts.
- Core validation passes 560 tests with 12 expected optional-RL skips; the exact RL environment passes 563/563 without skips. Protocol, task, and training fingerprints remain unchanged; the content fingerprint changes intentionally with the new runtime source boundary.

## Documentation and scope

- Reconcile the durable game-maturity cursor with GM-03d Commit B, record decision D-014, and update architecture, progress, plan, evidence, and review surfaces for the completed local extraction.
- Change no dependency declaration, workflow, protocol/task/training contract, gameplay rule, reward, rendering behavior, or GM-03f input/layout ownership. Preserve and exclude the pre-existing untracked `.agents/` tree and ignored `output/` evidence.
