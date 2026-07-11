# Purity and performance review

- **High — `Mediator.render()` defeated bounded cache and resource lifetime.** Without a supplied renderer, every call constructed a new `GameRenderer`, including full-resolution route surfaces and fonts.
- **Medium — per-entity signature reflection consumed a material part of every frame and scaled with future content.** `_call_flexibly()` invoked `inspect.signature()` for every station, metro, and button. A 100-frame profile recorded 1,200 inspections taking about 1.24 ms/frame and 26% of renderer CPU time.

## Re-review

No important findings remain. `Mediator.render()` retains one lazy compatibility renderer and adapts layout only when the surface size changes; twenty warm 1920x1080 compatibility renders took 0.0146 seconds total. Flexible draw contracts now use a bounded per-method signature cache; a 100-frame profile recorded four inspections with 1,196 cache hits. Focused mediator, renderer, and render-purity suites passed 67/67.
