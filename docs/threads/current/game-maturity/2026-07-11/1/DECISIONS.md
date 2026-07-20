# Game maturity decision log

## D-001 - Repository-backed persistence

Decision: `PLAN.md` is the durable scope and acceptance contract; `STATE.md` is the sole resume cursor; `DECISIONS.md` prevents design drift; `EVIDENCE.md` records verification. All four are committed and updated incrementally.

Reason: chat context and active-process state are not sufficient evidence for a multi-session effort. The repository must say what is complete, what remains, and exactly where to resume.

## D-002 - Deliveries and currency are separate concepts

Decision: `Mediator.deliveries` is the canonical cumulative objective and `Mediator.line_credits` is the spendable balance. A delivery increments both; a purchase subtracts only line credits. `total_travels_handled` remains a compatibility property alias to deliveries and `score` remains a deprecated compatibility property alias to line credits, so callers that fund purchases by assigning `score` do not silently change meaning.

Reason: the current HUD and game-over overlay call remaining spendable currency `score`, while the user and RL objective define success as total passengers delivered. One value cannot truthfully represent both after a purchase.

Status: accepted implementation contract after adversarial plan review.

## D-003 - Longer history must be temporally meaningful

Decision: the fresh policy will receive more than eight frames, but the implementation will not blindly multiply contiguous RGB frames. It will preserve immediate interaction context and add older snapshots through a manifest-bound history layout selected after resource profiling.

Reason: eight consecutive 10 Hz frames cover only 0.8 seconds. Doubling contiguous frames covers 1.6 seconds while roughly doubling rollout observation memory, which is still too short for route and reroute planning. Recurrent state remains necessary for episode-long memory.

Result: the operationally valid fallback campaign promoted `decision-history-10-fallback-v1` with ten oldest-to-newest offsets `[128, 64, 7, 6, 5, 4, 3, 2, 1, 0]`, zero-filled missing history, and explicit channel ordering. This retains the last eight 10 Hz samples plus anchors 6.4 and 12.8 seconds back while the LSTM carries episode-long memory. Its measured median peak process-tree working set was 4,043,184,128 bytes versus 3,636,346,880 for the matched eight-contiguous control (1.1119x and below both RAM gates), while throughput retained 0.8482x of the control. The original twelve-frame primary campaign was operationally invalid and its target also exceeded the strict historical RAM cap, so it remains an explicit unpromoted ablation.

Status: accepted fresh recurrent default after GM-02d profiling; passenger-delivery efficacy remains pending GM-12.

## D-004 - Product features share one simulation

Decision: menus may wrap sessions, but route editing, resources, maps, upgrades, saves, manual controls, structured actions, recursive play, and pixel RL must all drive one canonical gameplay model.

Reason: parallel feature implementations would invalidate determinism, tests, and the claim that the pixel policy faces the same game as a player.

## D-005 - Compatibility before decomposition

Decision: complete the score/reward and history-contract migrations before splitting `Mediator`, then keep `Mediator` as a facade over composed collaborators.

Reason: doing the same contract migration across temporary and final module boundaries would increase risk and make artifact fingerprint changes harder to reason about.

## D-006 - Initial overload-pressure correction

Decision: rename the mechanic around an explicit overdue-passenger threshold, use two as the initial default, and retain `max_waiting_passengers` as a compatibility alias. One overdue passenger warns but does not end a default game; the second ends it. An explicitly configured threshold of one preserves the old behavior.

Reason: two is the smallest change that removes the current one-passenger failure cliff while retaining visible time pressure. The scripted paired-seed evidence was independently reproduced and remains directional only; GM-11 still owns final balance tuning from broader human and policy evidence.

## D-007 - Two-commit remote finalization

Decision: each independently green work unit uses implementation Commit A followed, after green CI, by metadata Commit B that records A's SHA/CI and advances the resume cursor. Commit messages carry exact `[<work-unit>:A]` and `[<work-unit>:B]` markers; B is located as the newest commit that changed the goal's `STATE.md` with the expected marker. Commit B is pushed and its CI must be green before new implementation starts; a later session queries B's CI and reopens the unit if it failed. Failing TDD tests are working-tree phases inside a work unit, not remotely finalized commits.

Reason: a local cursor advanced only after CI is not durable on `origin/main`, while endlessly committing the latest metadata CI result has no terminal transaction.

## D-008 - Explicit persisted-schema compatibility

Decision: GM-01 adds checkpoint schema v2 plus v1 normalization, recursive input schema v2 with explicit reward contract and legacy v1 score-delta replay, versioned agent-play records, writable compatibility aliases, and reconstructable pixel terminal-metrics versions. GM-02 adds manifest v2 with a separate validated history fingerprint while retaining the single-frame task fingerprint and arbitrary v1 contiguous stacks.

Reason: source/content drift flags cannot repair a protocol or persisted-document schema that the loader no longer understands.

## D-009 - Runtime selections belong to task identity

Decision: map ID and map-definition version will be included in RL task identity, manifests, train/resume/evaluate CLI reconstruction, saves, and high-score keys. Task descriptors and fingerprints become explicitly versioned; genuine legacy artifacts reconstruct and hash the exact pre-map descriptor rather than inserting fields and expecting the old hash to match.

Reason: hashing source code does not distinguish two maps selectable from the same revision.

## D-010 - Pause reasons precede modal product systems

Decision: GM-07a replaces internal boolean-only pause ownership with explicit pause reasons while retaining the `is_paused` compatibility facade. Menus/save, tutorial, and weekly choices build on that established contract.

Reason: introducing pause reasons only with weekly progression would force save and tutorial schema migrations and could let the Space key dismiss a non-manual modal pause.

## D-011 - Network progression has one internal owner behind the facade

Decision: GM-03b introduces a dependency-free `NetworkProgression` aggregate as the sole owner of current line/station/economy progression scalars, rules, and cached counts. `Mediator` retains explicit writable properties, real public method wrappers, all station/button collections and effects, and the exact per-delivery public-hook order. The aggregate holds no mediator backreference, entities, UI objects, RNG, or clocks.

Reason: a stateless controller over a broad mutable mediator protocol would relocate functions without extracting ownership, while duplicated controller state would break direct writes, checkpoints, and cached unlock semantics. A single internal store plus an explicit facade preserves the current API and gives GM-07 saves and GM-10 upgrades a narrow evolvable boundary without speculative serialization.

## D-012 - Route planning is stateless; mutation stays explicit

Decision: GM-03c extracts deterministic route filtering, search, compression, constrained selection, and lazy boarding/bulk proposals into a stateless dependency-light `RoutePlanner`. It receives fresh graphs, ordered candidates, factories, and resolver thunks; it owns no RNG, entity collection, map, graph, route, clock, or cache. `Mediator` keeps every public route method, RNG shuffle, graph build, `travel_plans` mutation, arrival/removal, topology, and passenger/metro effect. Newly created constrained plans may be wired while unowned, while bulk plans are installed before the public next-hop hook exactly as at baseline. Bulk proposals explicitly distinguish raw arrival, route, and fallback; arrival effects run while the destination iterator is suspended, iterator finalization then precedes the same-passenger fallback guard, and the in-frame selection loop retains baseline locals through those facade effects. Callable getters are resolved before argument evaluation and invoked without retaining the temporary callable after the call.

Reason: search-only extraction cannot restore the required mediator size trajectory, but moving passenger or topology ownership early would blur GM-03d/e and risk identity/timing drift. Lazy proposals move enough deterministic planning while letting the facade apply each result before iteration resumes, preserving callback rebinding, RNG, live-list mutation quirks, sentinel identity, checkpoint-visible object identity, iterator finalization, and Python local/callable lifetime side effects. Resolver thunks also preserve baseline reads of mutable path IDs at each short-circuited comparison and re-read a rebound `travel_plans` mapping between membership and indexed access.

## D-013 - Path lifecycle is stateless over canonical facade state

Decision: GM-03d extracts exactly 12 path creation, completion, invalidation, removal, and button-assignment transition algorithms into a stateless, non-retaining `PathLifecycle`. Each call receives an explicit topology-limited host; `Mediator` keeps every real public method and remains the sole canonical owner of directly writable lists, maps, flags, RNG, entities, and effects. The lifecycle re-reads host state at baseline expression points, dynamically invokes nested public hooks, and resolves `Path`/`Metro` factories through getter thunks only at their original construction points.

Reason: mirrored aggregate state or proxy properties would consume the below-1,000 line budget and enlarge the identity/rebinding surface used directly by tests, environments, checkpoints, routing, passenger flow, and rendering. A call-scoped transition coordinator moves the coherent behavior boundary without hidden delegation, retained backreferences, duplicated collections, or cross-call cache. The 168-line source envelope and 57-line hard replacement/wiring budget guarantee the required reduction without stealing GM-03e passenger-flow or GM-03f input/layout scope.

## D-014 - Passenger flow is stateless over canonical facade state

Decision: GM-03e extracts 16 passenger spawning, simulation tick, metro exchange, waiting/game-over, and bulk route-proposal application algorithms into a stateless, non-retaining `PassengerFlow`. Each call receives an explicit call-scoped host plus getter thunks that preserve late module-global, graph/search/plan, router-iterator, and progression-hook lookup. `Mediator` keeps every exact public signature and remains the canonical direct owner of entities, collections, maps, RNG, clocks, progression, routing, pause/speed/game-over state, overload configuration, and public effects.

Reason: passenger spawning and exchange form one temporal mutation boundary whose observable behavior depends on three fresh graph phases, live collection iteration, generator suspension/finalization, per-rider collaborator rebinding, partial failures, and exact delivery/transfer/boarding order. A retained controller or eager wrapper capture would change those seams, while moving route queries or input/layout behavior would steal GM-03c or GM-03f ownership. The reviewed 346-line removal and 97-line explicit facade/wiring model projects `Mediator` to 735 lines without proxy state or magic delegation.

## D-015 - Input coordination is stateless over canonical facade state

Decision: GM-03f extracts exactly 19 path-button UI, timing/layout/render, mouse/keyboard, pause/speed, and structured-action algorithms into a stateless, non-retaining `InputCoordinator`. Each call receives an explicit call-scoped host plus getter thunks that resolve numeric configuration, pygame factories and keys, update helpers, runtime types, event enums, and the lazy renderer factory at their original expression points. `Mediator` keeps every exact public signature and remains the canonical direct owner of UI collections, hit rectangles, compatibility renderer, progression, topology, clocks, input flags, pause/speed/game-over state, and public effects.

Reason: human mouse/keyboard input, programmatic actions, layout hitboxes, compatibility rendering, and path-button effects form one player-interface coordination boundary whose observable behavior depends on live-list order, `isinstance` subclass precedence, short-circuiting, public-hook rebinding, partial failures, and Python bound-method evaluation order. Retained controller state, eager dependency capture, adjacent ownership theft, or generated delegation would break those seams. The cohesive boundary reduces `Mediator` from 735 to 605 lines; the reviewed mathematical facade floor makes the parent under-500 target impractical without hiding behavior, while the explicit implementation remains below the 625 hard ceiling and the new component remains below 500 lines.

## D-016 - Recursive execution uses one isolated physical engine pin

Decision: the canonical civ-engine descriptor is checked in under `scripts/`, while its retained Git checkout lives at the explicitly ignored repository root `/.civ-engine-pin/`. Package metadata, regenerated lock metadata, npm link semantics, CI checkout/build, provenance, and runtime resolution must agree on that physical root. Provenance resolves ESM without executing it and rejects a wrong physical location even under `--allow-dirty`; GM-04b owns the credential-free idempotent setup/verifier command and public pre-hooks. The unrelated `../civ-engine` sibling is never setup input or mutation scope.

Reason: a version string or descriptor alone cannot attest the code Node executes. Local-file installation is configuration-sensitive, bare ESM resolution can be shadowed below `scripts/`, and a mutable sibling is independent user state. One dedicated ignored checkout plus realpath/runtime-entry identity, Git commit, clean status, and complete runtime digest makes the local and CI boundary reproducible without changing historical persisted summary schemas.

## D-017 - Public Node bodies guard after a trusted bootstrap and child execution stays shell-free

Decision: GM-04b treats the tracked package scripts and `.npmrc`, selected top-level npm and Node executables, and their pre-start environment/configuration as an explicit trusted bootstrap boundary. The actual setup and guard mains share a dependency-light assertion that requires `NODE_OPTIONS` to be unset or empty and `process.execArgv` to be empty before their own effects. After that clean startup, each canonical Node test/playtest body passes through the identity guard, `npm test` has the complete zero-argument `node --test` child body, and npm lifecycle pre-hooks remain defense in depth. The exact root `.npmrc` fixes link semantics and silences the standard expanded-script prelude. On Windows and POSIX, setup validates the active Node distribution's npm launcher/CLI and launches its physical `npm-cli.js` through exact `process.execPath`; the engine build likewise launches only the physical pin-local TypeScript CLI through that Node executable, never `npm.cmd`, `cmd.exe`, an npm build lifecycle, or caller `PATH`.

Reason: npm's `ignore-scripts` setting can suppress pre-hooks while still executing a requested script body, unrestricted post-start test arguments can become child Node CLI surfaces, and npm can echo forwarded arguments before the guard runs. However, npm `--node-options`, ambient `NODE_OPTIONS`, or direct Node startup options can execute caller-selected code before any repository module starts; no Node assertion can prevent or undo those effects, so a pre-Node trusted launcher would be required to distrust that boundary. The shared assertion detects observable taint and stops later entry-point effects without claiming pre-main attestation. Separately, live Windows evidence proves direct `npm.cmd` with `shell: false` returns `EINVAL`, while wrapping it in `cmd.exe` reintroduces metacharacter parsing, and an npm build lifecycle would restore executable search. Within the trusted bootstrap, fixed guarded bodies, silent tracked npm policy, validated JavaScript CLIs, and exact Node execution preserve the intended child-process boundary.

## D-018 - Route replacement is an atomic identity-preserving transaction

Decision: GM-05a preserves the exact live path, public ID, color/button ownership, fleet, riders, and physical metro poses while replacing unique normalized station order and loop state only after an off-live candidate and semantic metro bindings validate. Moving logical edges map by oriented station trip, padding maps by its complete retained station transition, and stopped metros map from a reconstructed arrival edge. Unsafe or ambiguous edits reject without effects. Every waiting rider in a stable captured holder order receives one scoped refresh against the committed graph, while every onboard plan becomes a checkpoint-visible one-alight marker on its current line using a Node from that fresh graph and receives one scoped fresh route only after that safe alight; removal of an edited-line rider's target alight rejects. No new pending field or canonical checkpoint/replay schema is introduced.

Reason: live `Path.update_segments()` preserves a numeric segment index rather than a semantic edge and can teleport a metro after insertion or reorder. Clearing an onboard plan can strand the rider because unloading depends on its target station, while retaining the old route tail can make post-edit routing stale. A two-phase transaction plus an existing-field one-alight marker makes continuity, route freshness, rollback, RNG timing, and replay state explicit without changing public identities or the canonical checkpoint/replay schema.
