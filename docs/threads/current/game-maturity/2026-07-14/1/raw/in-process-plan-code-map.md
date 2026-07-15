# GM-03d live-code map

Recommended boundary: add a focused, stateless `PathLifecycle` transition coordinator in `src/path_lifecycle.py`, while keeping all canonical public collections/maps/flags on `Mediator`. This gives real transition ownership without proxy properties, duplicated state, or identity/rebinding drift.

At mapping start, `HEAD == origin/main == 5e6186d8b331207d2a6ec583b7a82f80533f5203`; only `.agents/` was untracked. No files were edited.

## Exact extraction set

Move these 12 method bodies behind unchanged public `Mediator` wrappers:

| Method | Current lines | Physical lines |
| --- | ---: | ---: |
| `assign_paths_to_buttons` | `src/mediator.py:371` | 10 |
| `remove_path` | `src/mediator.py:491` | 15 |
| `invalidate_travel_plans_for_path` | `src/mediator.py:506` | 12 |
| `remove_path_by_id` | `src/mediator.py:518` | 7 |
| `remove_path_by_index` | `src/mediator.py:525` | 8 |
| `start_path_on_station` | `src/mediator.py:533` | 18 |
| `create_path_from_station_indices` | `src/mediator.py:551` | 36 |
| `add_station_to_path` | `src/mediator.py:587` | 18 |
| `abort_path_creation` | `src/mediator.py:605` | 7 |
| `release_color_for_path` | `src/mediator.py:612` | 4 |
| `finish_path_creation` | `src/mediator.py:616` | 12 |
| `end_path_on_station` | `src/mediator.py:694` | 23 |

Total moved: exactly 170 physical lines.

Keep these adjacent responsibilities in place for now:

- Palette generation at `src/mediator.py:257`: it consumes the isolated Python RNG and has an existing `patch("mediator.hue_to_rgb")` contract at `test/test_mediator_interaction.py:36`.
- Station-pool and progression effects at `src/mediator.py:279` and `src/mediator.py:292`.
- Mouse/action dispatch at `src/mediator.py:426` and `src/mediator.py:659`, including temporary-point updates at line 458; GM-03f owns input coordination.
- Metro movement, passenger effects, graph construction, and routing from `src/mediator.py:773` onward; GM-03e/GM-03c own those boundaries.

## Line budget

`Mediator` is 1,110 lines.

- Remove 170 lifecycle lines.
- Replace them with approximately 43-47 wrapper lines.
- Add one import and one coordinator-construction line.

Projected result: 985-989 physical lines. Set an implementation target of at most 990 to retain margin under the hard 1,000-line gate. No state-proxy properties are needed.

The new module should remain roughly 180-230 lines and below 500.

## State and ownership contract

Keep these as the canonical, directly writable `Mediator` objects:

- `paths`, `metros`
- `path_to_button`
- `path_colors`, `path_to_color`
- `is_creating_path`, `path_being_created`

Direct writes are widespread, including `test/mediator_test_support.py:63`, route characterization tests, passenger-flow tests, and `test/test_mediator_paths.py:102`. Checkpoints also read every draft/color/button mapping directly at `src/recursive_checkpoint.py:450`.

`PathLifecycle` should:

- Store no `Mediator` backreference and cache no collection, map, factory, RNG, graph, or route.
- Receive a call-scoped, topology-limited host protocol.
- Own the exact transition algorithms and mutation ordering.
- Use resolver thunks for `Path`/`Metro` factories if patch/rebinding timing is characterized.
- Invoke nested public methods through the host at the original points, never bypassing wrappers with private controller-to-controller calls.

## Behavior hazards to freeze

1. Public hook dispatch is observable.

   - Programmatic creation calls public `start_path_on_station`, repeated public `add_station_to_path`, then public `end_path_on_station` at `src/mediator.py:564`.
   - Removal calls public invalidation, color release, button assignment, and replanning in that order at lines 500-504.
   - `end_path_on_station` calls public finish/abort methods.
   - An existing test replaces `start_path_on_station` on the instance at `test/test_gameplay.py:52`. Resolve hooks lazily so mid-operation rebinding remains visible.

2. Collection and mapping identity matters.

   - `assign_paths_to_buttons` clears every button, then replaces `path_to_button` with a new dict, then assigns zipped path/button pairs, then refreshes locks.
   - Do not change the replacement to `.clear()`.
   - `paths`, `metros`, passenger lists, and travel-plan maps are otherwise mutated in place.
   - Recursive checkpoints index entities by Python identity at `src/recursive_checkpoint.py:218`.

3. Removal order is non-transactional and exact.

   - Clear the assigned button first.
   - Snapshot `path.metros`, then each metro's passengers.
   - Remove global passengers/plans and surviving global-metro membership.
   - Invalidate remaining plans.
   - Release color.
   - Remove path.
   - Rebuild button mapping.
   - Replan last; this is where destination shuffling can consume the isolated RNG.
   - The removed `Path` object intentionally retains its own `metros` list.
   - Onboard riders on surviving lines retain a plan whose immediate `next_path` survives, even if a later node references the removed path; existing coverage is `test/test_mediator_paths.py:55`.

4. Draft topology is live but excluded from routing.

   - `start_path_on_station` appends the new `Path` immediately and sets `is_being_created`.
   - Graph construction explicitly skips draft paths at `src/graph/graph_algo.py:18`.
   - Abort does not clear the detached path object's `is_being_created` flag or temporary point; it only clears facade state after release/removal.
   - Finish clears the draft flag/temp point before creating a metro, adds that same metro to both `path.metros` and global `metros`, clears the facade pointer, then assigns buttons.

5. Loop/duplicate semantics must remain exact.

   - Station comparison uses `==`; `Station.__eq__` is ID-based at `src/entity/station.py:36`.
   - Only an immediate duplicate is ignored.
   - Returning to the first station sets a loop; adding another station after that removes the loop and appends.
   - Non-first, non-adjacent duplicate stations are currently appendable.
   - Interactive hover-to-first emits one snap blip; releasing on that already-current station finishes without a second blip.

6. Entity and geometry identity must not drift.

   - `Path` owns station/metro/draft/segment state at `src/entity/path.py:18`.
   - `add_station`, `set_loop`, and `remove_loop` rebuild logical segments; `add_metro` binds the metro to the exact first segment and copies the current path ID at `src/entity/path.py:153`.
   - Preserve `Path` then `Metro` construction count/order. Their opaque shortuuid IDs are public in observations even though canonical checkpoints intentionally normalize them.

7. UI assignment remains identity-bearing.

   - `PathButton.remove_path`, `assign_path`, and `set_locked` mutate path references, crosses, and colors at `src/ui/path_button.py:38`.
   - Removing a path bubbles surviving assignments left; covered at `test/test_gameplay.py:207`.

## TDD coverage recommended before production

Baseline-green facade characterization:

- AST equality for all 12 public signatures.
- Lazy nested-hook rebinding for create/remove/end/finish/abort.
- Exact button-clear -> dict-rebind -> assignment -> lock-refresh order and old-dict identity.
- Exact remove-path mutation/hook/RNG order, including retained detached `path.metros`.
- Factory timing and same-object identity across pointer/list/maps/path-metro/global-metro.
- Draft append/exclusion, abort residue, loop transitions, snap-blip count, bool-index rejection, and first matching path-ID dispatch.

Expected-red direct tests for `PathLifecycle`:

- Creation validation and loop station sequences.
- Start/add/end/abort/finish transitions with fake identity-bearing objects.
- Removal cleanup/invalidation and exact callback order.
- Button rebinding/bubbling.
- A fresh import should not load pygame, graph, route planner, progression, or simulation context.

Wider equivalence:

- Existing lifecycle behavior: `test/test_mediator_paths.py:23`.
- Player interaction and button bubbling: `test/test_gameplay.py:67`.
- Structured API validation/topology: `test/test_env.py:35`, `test/test_env.py:220`, and `test/test_env.py:299`.
- Latent topology and metro identity: `test/test_recursive_checkpoint.py:190`.
- Render-side identity purity: `test/test_render_purity.py:77`.
- Finish with a seeded baseline/current action-and-canonical-checkpoint differential covering non-loop creation, loop creation, abort, removal with waiting/onboard passengers, and path-button rebinding.

This boundary is leaner and safer than moving storage into a hidden aggregate: explicit facade properties for six or seven mutable fields would consume most of the line savings and create a larger identity/rebinding surface precisely where the current tests and checkpoint format are most coupled.
