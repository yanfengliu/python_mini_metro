## Game Rules

This document summarizes the game rules currently implemented in code.

## Objective

- Build and manage metro lines to deliver passengers to stations that match their destination shape.
- Maximize lifetime passenger deliveries before game over.

## Timing and Presentation

- Interactive play advances the simulation on a deterministic 60 Hz cadence of 17, 17, then 16 milliseconds; delayed frames are bounded so a stall cannot create an unlimited catch-up spiral.
- Player input is applied before the simulation updates for that frame.
- Metro positions are visually interpolated between completed simulation updates. Interpolation changes only presentation, not travel timing, stops, scoring, or passenger state.
- Attached carriage bodies follow the rendered route through bends, loops, and terminal turns. Passenger order is sliced across the locomotive first and then each attached carriage in order; a queued-return outline covers the whole consist.
- Multiple lines through the same station pair occupy symmetric visual lanes around their shared logical centerline. The logical path and padding segment sequence used for metro movement is unchanged.
- Drawing is observational: rendering does not advance time, rebuild logical routes, expire effects, or change hitboxes.
- Interactive play adds short, deterministic, procedurally-synthesized sound effects: a distinct tone plays when a delivery completes, a line is purchased, a station unlocks, the game ends, and a line endpoint snaps, each scaled by the master and SFX volumes. Tones are generated in-process (no external audio files) and are purely presentational — they never affect timing, scoring, or state, and audio-device failure degrades silently to no sound. The snap cue, and a purchase made in the same frame as loading a saved game, are best-effort and may occasionally be skipped. Audio plays only at the interactive entry point; headless, agent, recursive, and RL play are silent and open no audio device.

## Stations and Passengers

- The map starts with 3 stations and unlocks up to 20 as lifetime passenger deliveries increase.
- Station shapes are from: rectangle, circle, triangle, and cross.
- New station positions are sampled randomly but weighted to be more likely near the
  current center of existing stations, so very far placements are less common.
- After the 10th station slot in the unlock pool, rare one-of-a-kind stations can appear:
  diamond, pentagon, and star (each at most once per run).
- Each station can hold up to 12 waiting passengers.
- Passengers spawn with a destination shape that is different from their origin station shape.
- A passenger is delivered when they reach any station whose shape matches their destination shape.
- Passengers waiting at stations accumulate wait time; passengers riding metros do not.

## Metro Lines and Trains

- You can create a line by connecting at least 2 stations.
- During interactive creation, repeating the current endpoint is ignored; reconnecting to the first station after at least two stations closes a loop. Other nonconsecutive repeated stations retain the existing creation behavior.
- Optional loop creation is supported by connecting the line back to its first station.
- Programmatic line replacement requires unique active station indices and objects after removing at most one trailing copy of the first station for a loop. A safe replacement preserves the line, fleet, riders, and metro poses; an ambiguous or continuity-breaking edit is rejected atomically.
- To redraw an established line manually, hold its assigned colored button, drag through the desired station order, and release on the final station. The completed old line remains live while an off-network preview follows the pointer; the selected button is outlined and a non-first repeated station marks the draft invalid in red.
- A manual redraw commits only a valid route with at least two stations. Returning to the first station closes a loop, continuing to a new station reopens it, and a short, invalid, or button-targeted release cancels without changing the line. A no-station release on a button retains the existing release-target behavior, including click deletion; a release over empty in-view space selects handles, and a release outside the viewport cancels.
- Releasing an assigned-button drag over empty in-view space selects that exact live line and shows collision-resolved edit handles. A separate fresh drag from a filled linear endpoint handle extends to a station not already on the line or removes exactly that endpoint when released on the adjacent interior station; a hollow edge handle inserts a new station between its neighbors. Loops expose hollow insertion handles for every physical edge, including closure, and no endpoint handles; a two-station loop exposes one canonical physical-edge handle.
- Handle previews and removal marks are transient interface feedback. Invalid, ambiguous, stale, off-station, button-targeted, outside-viewport, unsafe, and game-over-interrupted edits clear without partial mutation; a valid edit delegates once to the same atomic replacement used by programmatic play. The selected line remains operational throughout selection and preview.
- When a line endpoint snaps onto a station during creation, that station emits a brief outward ring blip in the line color.
- A line can only be created if there is an unlocked line slot available.
- The locomotive inventory starts at 4 total. `Mediator.metros` contains assigned locomotives only, and available inventory is the nonnegative difference between the total and assigned counts; unassigned locomotives are fungible capacity rather than preconstructed entities.
- Completing a line does not assign a locomotive. A completed line remains valid but unserved until the player uses its plus control or the `assign_locomotive` structured action. Multiple locomotives can serve one line while total inventory remains available.
- The minus control and `unassign_locomotive` action prefer the last empty, nonqueued locomotive on the line; when every nonqueued locomotive carries riders, the request selects the occupied one with the fewest riders, breaking ties by latest line order. An empty locomotive at a real station returns immediately; otherwise the locomotive remains assigned, boards no new passengers, and stops at every real station so riders can leave. Endpoint-coordinate equality alone does not count as a station arrival.
- A queued occupied locomotive first serves ordinary destination and transfer unloads at each stop; riders with no usable exit on the line — no plan, no alight on this line, or a transfer blocked only by a full station — then step off together at that stop, keep waiting there with a reset wait clock, and replan normally. Forced alights ignore the station's 12-passenger cap, and an over-capacity station accepts no new spawns or transfers until ordinary boarding drains it below capacity. The emptied locomotive returns to inventory the same moment its last rider leaves at a real station.
- A queued return is a visible subset of assigned inventory and does not increase availability early. Repeated requests can queue distinct eligible locomotives; an already queued locomotive is never selected again. The `cancel_unassignment` structured action restores the earliest queued locomotive on the line to normal service with its riders and carriages intact. Redistribution is the explicit two-step sequence of returning a source locomotive and then assigning the newly available capacity to a destination line.
- A paused game accepts a return or cancellation request, but a moving locomotive does not advance until play resumes. A terminal game rejects fleet actions.
- The carriage inventory starts at 2 total. Unassigned carriages are fungible capacity and exist as entities only after attachment; assigned and available counts derive from carriage lists owned by canonical global Metros.
- A line's carriage-plus control or `attach_carriage` action selects the eligible nonqueued locomotive with the fewest carriages, breaking ties by earliest line order, and appends one new six-seat carriage. A paused game permits the immediate composition change; a terminal game rejects it.
- A line's carriage-minus control or `detach_carriage` action selects the eligible nonqueued locomotive with the most carriages, breaking ties by latest line order, and removes that locomotive's last carriage only if all current riders still fit. Removed carriage identities are retired rather than pooled or reused.
- Removing a line never deletes a rider. Each onboard passenger leaves the train at its locomotive's current or nearest route station: a passenger already at a station matching its destination shape counts as a delivered trip, and every other passenger joins that station's queue — even past the 12-passenger cap — with a reset wait clock and a fresh route search. Passengers with no reachable destination simply keep waiting under the normal overdue rules.
- Removing a line then removes its assigned metros from the active global collection, making those locomotive and carriage units available again in ordinary gameplay. Detached historical path graphs do not count as live inventory. A removal that fails partway restores the exact prior state — line, riders, fleet, credits, and progression included — instead of leaving a half-removed network.
- A locomotive has 6 base passenger spaces, and each attached carriage adds 6 more. Passengers remain canonically owned by the locomotive and are rendered across the locomotive slice followed by ordered carriage slices.
- Metro movement is automatic along the line:
  - Non-loop lines reverse direction at endpoints.
  - Loop lines continue around the loop.
- The current total locomotive limit is 4. Availability is always `max(0, total - assigned)`, including compatibility states that contain more assigned locomotives than the current total.

## Deliveries, Line Credits, and Progression

- Each delivered passenger increases lifetime deliveries by 1 and awards 1 spendable line credit.
- Spending line credits never reduces lifetime deliveries.
- Line slot unlocks are purchased using line credits by clicking locked (empty ring) line buttons:
  - Start with 1 available line.
  - 2nd line costs 90 line credits.
  - 3rd line costs 210 line credits.
  - 4th line costs 350 line credits.
  - These costs are incremental amounts derived from milestones [0, 90, 300, 650].
- Unlocked stations are based on lifetime deliveries:
  - Start with 3 stations.
  - Unlock the 4th station at 10 deliveries.
  - Then each next station requires 20 more deliveries than the previous gap (5th at 40, 6th at 90, 7th at 160, ...), up to 20 stations.
- Line colors are randomized at runtime each run, using a less saturated palette for softer visuals.

## Passenger Routing and Transfers

- Passengers compute travel plans based on currently available, completed lines.
- Routing is shortest-hop style (BFS over the station graph).
- When multiple equal-length BFS routes exist, neighbors are explored in graph-connection insertion order and duplicate connections keep their first position, so the first inserted route wins deterministically.
- Looped lines include the closing segment between their last and first stations in routing, matching metro movement.
- If multiple stations match a destination shape, the game uses one with a valid route.
- Passengers can transfer between lines at stations according to their travel plan.
- If no route exists, passengers wait until the network changes. Removing a line invalidates waiting-passenger plans that used it; passengers already riding a surviving line keep their immediate transfer plan until they leave that line, then replan against the updated network.
- Replacing a line immediately replans every waiting passenger against the committed network. An onboard passenger retains the next safe alight on its current line, then receives a fresh route from that station; removing that alight from the edited line rejects the replacement.

## Timing and Spawning

- Game updates at 60 FPS.
- Station service is timed one executable passenger at a time in 500 ms intervals: destination unload first, then a transfer when the station has room, then boarding when the locomotive has room and boarding is permitted. Eligibility is recomputed after every completed action, so blocked transfers or full trains create no phantom dwell interval and larger time steps retain residual progress across successive actions.
- Each active station is initialized ready to spawn and attempts its first passenger on the first unpaused fixed update.
- Each station samples its own recurring spawn interval once, uniformly and inclusively from 70% to 130% of the 900-step base: 630-1,170 simulated steps, or 10.5-19.5 simulated seconds at 60 Hz.
- On each station spawn tick, that station attempts to spawn 1 passenger if it has room and then resets its counter even when full.
- The 2x and 4x controls advance counters by 2 and 4 per fixed update, reducing wall-clock time between attempts while preserving approximately the same simulated-time interval (subject to whole-tick quantization).

## Game Over

- A passenger is considered over-waiting at 40 seconds or more of station wait time.
- Only passengers waiting at stations count toward overload; passengers already riding metros do not.
- A fresh game uses an overdue-passenger threshold of 2. The first over-waiting station passenger is a warning and the second ends the game. Programmatic callers may set `Mediator.overdue_passenger_threshold`; the deprecated writable `max_waiting_passengers` alias controls the same value, and explicit threshold `1` preserves the historical one-passenger rule.
- On game over:
  - Simulation time and gameplay updates stop.
  - `MiniMetroEnv.step(...)` calls become stable no-ops until reset; `PlayerPixelEnv.step(...)` rejects further actions until its required reset.
  - The game-over overlay presents lifetime passengers delivered as the primary result and remaining line credits as a secondary value.
  - The run's lifetime deliveries are recorded once to the high-score leaderboard at `saves/highscores.json` (ranked descending and capped at ten per map and rules version); if the run set a new best for its key, a compact indicator is shown on the game-over screen. A missing or corrupt leaderboard starts empty and never blocks play.

## Controls

- Mouse:
  - Click and drag from station to station to create a line.
  - Hold an assigned line button, drag through stations, and release on the final station to redraw that line; invalid or incomplete drafts cancel without changing it.
  - Hold an assigned line button and release over empty in-view space to show its handles, then begin a separate drag on a filled endpoint or hollow insertion handle to edit one route edge.
  - Hover a locked line button to see a two-line buy hint (`Buy` + price).
  - Click a locked line button (empty ring) to purchase that slot if enough line credits remain.
  - Click the plus above a completed line button to assign one available locomotive. Click its minus to request the return of the last eligible empty locomotive.
  - Use the carriage plus and minus in the same four-control line-slot group to attach one available carriage or safely detach the selected locomotive's last carriage.
  - Click and release a line color button without capturing a station to remove its release-target line.
  - On the title screen, click New Game to start a fresh game, Continue to resume the autosave (shown only when one exists), or Exit to quit.
  - On the pause menu, click Resume, Restart, or Exit to Title. A menu button fires only when pressed and released on that same button, so releasing a drag that was in progress when the menu opened does nothing.
  - On game-over screen, click Restart or Exit buttons.
- Keyboard:
  - SPACE: pause / resume (the user pause; it never dismisses the pause menu).
  - 1 / 2 / 3: set game speed to 1x / 2x / 4x.
  - ESC: open the pause menu while playing (cancelling any in-progress drag first); close it while it is open.
  - ENTER: start a new game (title screen).
  - R: restart (game-over screen).
  - ESC: exit (game-over screen).
- The pause menu holds its own pause reason: opening it while SPACE-paused keeps both, and resuming from the menu releases only the menu hold, so the game stays paused until SPACE (or a speed button) clears the user pause. Speed-button selections still clear only the user pause and never the menu hold; the keyboard speed keys only set the speed and never unpause.
- Autosave: opening the pause menu and Exit to Title each write a single autosave to `saves/autosave.json`, and closing the window mid-run keeps it, so the title screen's Continue reloads the game exactly where you left off (releasing the menu pause, honoring a held SPACE pause). Reaching game over deletes the autosave, so a finished run cannot be Continued; every autosave is best-effort and never blocks play or exit.
- Settings: a Settings screen, reached from the title or pause menu (Back returns to whichever opened it, and opening it from the pause menu keeps the game paused), toggles fullscreen, steps the master/music/SFX volumes in 25% increments, and toggles reduced motion. Settings persist to `saves/settings.json` and survive restart; fullscreen applies to the live window and reduced motion holds the passenger-warning, station-unlock, and path-button blinks steady while suppressing the snap-blip rings (the master and SFX volumes scale the procedural audio cues). Settings are presentation-only and change no game balance; a missing or corrupt settings file falls back to the defaults and never blocks play.

## Programmatic Actions (Environment / API)

- `create_path`: create a line from station indices (with optional loop flag).
- `replace_path`: atomically replace one existing line selected by exactly one index or id, using a unique station-index sequence and optional loop flag.
- `assign_locomotive`: assign one available locomotive to a completed line selected by exactly one index or id.
- `unassign_locomotive`: immediately return or queue the return of a locomotive from a completed line selected by exactly one index or id; empty locomotives are preferred, and an occupied locomotive drains its riders at stations before returning.
- `cancel_unassignment`: restore the earliest queued locomotive on a completed line selected by exactly one index or id to normal service. This action is live-only: persisted recursive and agent recordings reject it at every schema version.
- `attach_carriage`: attach one available carriage to a completed line selected by exactly one index or id; the eligible nonqueued locomotive with the fewest carriages wins, with earliest line order breaking ties.
- `detach_carriage`: safely detach the last carriage from a completed line selected by exactly one index or id; the eligible nonqueued locomotive with the most carriages wins, with latest line order breaking ties, and every rider must fit afterward.
- `remove_path`: remove a line by index or id.
- `buy_line`: purchase the next locked line, optionally targeting its sequential button index.
- `pause`: pause simulation.
- `resume`: resume simulation.
- `noop` (or `None`): do nothing this step.
- Malformed or unsafe actions are rejected without mutating game state or advancing programmatic time.
- Locomotive and carriage resource actions are accepted while paused and rejected after game over; queued locomotives cannot receive carriage mutations.

## Player-Equivalent RL Controls

- The pixel RL environment uses the same 1920x1080 virtual player view, hitboxes, pygame event conversion, and fixed simulation updates as manual play.
- The policy observes only RGB pixels with a rendered software cursor. The default `fast` profile is 192x108 and the registered `fidelity` profile is 320x180; both are downsampled from the canonical player render.
- One action contains a kind plus a pointer coordinate. Supported kinds are no-op, mouse motion, left-button down, left-button up, Space, and the `1`/`2`/`3` speed keys. Mouse coordinates span the selected observation grid and map exactly to the edges of the canonical view.
- The default decision advances six fixed ticks, or 100 simulated milliseconds at 1x speed. Pause consumes decisions without accumulating simulation backlog; speed keys apply the same 1x/2x/4x gameplay multipliers as manual play.
- An episode terminates at game over and truncates at its configured decision horizon. The default learning reward is newly delivered passengers; the legacy pixel `display_score_delta` mode and structured `line_credits_delta` mode include line credits spent purchasing line slots.
- Adding mouse-driven stations, buttons, routes, passengers, or other visible content does not require a new action schema. Adding another keyboard control, changing action meanings, changing registered pixel profiles, or changing cursor pixels requires an explicit protocol update so saved models cannot silently receive a different task.
