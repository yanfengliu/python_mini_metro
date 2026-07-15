GM-03d contract map is complete at baseline `5e6186d8`. No files were edited. The focused baseline passed 61/61 tests:

`test_mediator_paths`, `test_gameplay`, `test_graph`, `test_path`, and `test_recursive_checkpoint`.

Prioritized observable contracts:

1. Creation identity/order (`mediator.py:533-626`)
   - Public signatures must remain exact for `start_path_on_station`, `create_path_from_station_indices`, `add_station_to_path`, `abort_path_creation`, `release_color_for_path`, and `finish_path_creation`.
   - Start marks `is_creating_path` before selecting color or constructing `Path`.
   - During `Path.add_station`, the color is taken and `path_to_color[path]` exists, but the path is not yet in `paths`; append occurs last.
   - The same `Path` instance remains through construction, completion, observations, buttons, graph nodes, and return value.
   - Finish clears creation flags/temp geometry before constructing a metro; the identical `Metro` is added to `path.metros` and `mediator.metros`, then `path_being_created` becomes `None` before button assignment.
   - Metro-cap exhaustion still completes the path without creating a metro.

2. Branch and station semantics (`mediator.py:587-603,694-715`)
   - Station comparisons use equality, not identity; `Station.__eq__` is ID-based.
   - Duplicate-current station: no mutation or snap.
   - Returning to the first station through motion sets a loop and snaps the passed station.
   - Ending on the first station sets a loop and finishes without a snap.
   - A new endpoint is added and snapped before finishing.
   - Ending the one-station path at its start aborts.
   - `loop=False` can still produce a loop when the final index returns to the first station; loop closure is not duplicated in `path.stations`.

3. Abort semantics (`mediator.py:605-614`)
   - `is_creating_path=False` precedes color release.
   - Color release precedes path removal; `path_being_created=None` is last.
   - The detached external `Path` remains `is_being_created=True` and retains temp/entity state.
   - All-taken colors currently fall back to black; abort then inserts black into `path_colors` as free.

4. Button assignment (`mediator.py:371-379`)
   - Every button is cleared first.
   - `path_to_button` is replaced with a new dict, not cleared in place.
   - Each button is assigned before its mapping entry is inserted.
   - Lock-state refresh runs after all assignments.
   - Ordering is `zip(paths, path_buttons)` insertion order.

5. Removal and invalidation (`mediator.py:491-531`)
   - Button detachment occurs before entity cleanup.
   - `path.metros` and each `metro.passengers` are snapshotted for iteration.
   - Removed-path passengers are removed from mediator globals/plans, then metros from mediator globals.
   - Invalidation runs before color release; path removal, button reassignment, and global replanning follow in that order.
   - Detached objects intentionally retain their graph: `path.metros` still contains the metro and `metro.passengers` still contains its passengers.
   - An onboard passenger on a surviving line keeps a plan when `next_path != removed_path`, even if its later node path mentions the removed line.
   - `remove_path_by_id` removes the first live ID match; `remove_path_by_index` accepts exact `int` only, rejecting `bool` and subclasses.

6. Dynamic observability
   - Calls to public lifecycle hooks are dynamically re-resolved at their original point. Collections such as `paths`, `metros`, and `travel_plans` are re-read after callbacks and may be rebound.
   - Do not constructor-capture facade collections or eagerly bind factories/callbacks.
   - Temporary callable release must precede the following lifecycle hook, matching the route-planner observability standard.

7. Graph/checkpoint boundary
   - An in-progress path already exists in `paths` but `build_station_nodes_dict` excludes it.
   - Flipping `is_being_created=False` makes the same path immediately graph-visible, including exact station/path identities and loop closure.
   - Recursive checkpoints expose path order, stations, metros, creation pointer/flag, colors, button mapping, geometry, and identity relations.

Baseline-green tests to add first, in priority order:

- Frozen signatures for all 12 lifecycle facade methods.
- One event-log test covering start → add → snap → finish, including exact state snapshots and Path/Metro identity.
- One removal event-log test covering button, passenger, metro, invalidation, color, path, assignment, and replan order, plus retained detached object graphs.
- Button-map replacement identity and per-button callback order.
- Abort ordering, retained detached state, and all-colors-taken fallback.
- Rebound-collection/callback test proving later steps use the replacement objects.
- Station equal-ID clone matrix: duplicate-last, loop-first, and new endpoint.
- Invalidation short-circuit/snapshot tests, including an exploding `node_path` for the surviving-onboard branch.
- ID/index validation and first-match behavior.
- Canonical lifecycle checkpoint trace at start, intermediate add/loop, finish, and remove.

Expected-red direct tests after freezing the new module API:

- Import/instantiate the new lifecycle component with fake paths, metros, stations, mappings, and callbacks.
- Direct normal and loop creation event vectors matching the facade characterization.
- Direct finish identity/cap behavior.
- Direct abort/color behavior.
- Direct remove/invalidate ordering and detached-graph retention.
- Direct button-map replacement behavior.
- Direct resolver/rebinding test proving the component does not retain stale facade collections or eagerly bound callbacks.

The main implementation risk is a clean-looking stateful extraction that caches lists/maps or callbacks: it would pass ordinary gameplay tests while changing writable-facade, mutation-order, and callback-lifetime behavior.

<oai-mem-citation>
<citation_entries>
MEMORY.md:1-3|note=[repo scope and live-state verification requirement]
MEMORY.md:43-49|note=[player RL and provenance contracts]
MEMORY.md:53-54|note=[safe directory and dirty-tree handling]
</citation_entries>
<rollout_ids>
019f4ca7-809d-7cb3-ab38-1cc1db98bb16
</rollout_ids>
</oai-mem-citation>
