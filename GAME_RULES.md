## Game Rules

This document summarizes the game rules currently implemented in code.

## Objective

- Build and manage metro lines to deliver passengers to stations that match their destination shape.
- Maximize lifetime passenger deliveries before game over.

## Timing and Presentation

- Interactive play advances the simulation on a deterministic 60 Hz cadence of 17, 17, then 16 milliseconds; delayed frames are bounded so a stall cannot create an unlimited catch-up spiral.
- Player input is applied before the simulation updates for that frame.
- Metro positions are visually interpolated between completed simulation updates. Interpolation changes only presentation, not travel timing, stops, scoring, or passenger state.
- Multiple lines through the same station pair occupy symmetric visual lanes around their shared logical centerline. The logical path and padding segment sequence used for metro movement is unchanged.
- Drawing is observational: rendering does not advance time, rebuild logical routes, expire effects, or change hitboxes.

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
- Duplicate station picks are ignored while creating a line.
- Optional loop creation is supported by connecting the line back to its first station.
- When a line endpoint snaps onto a station during creation, that station emits a brief outward ring blip in the line color.
- A line can only be created if there is an unlocked line slot available.
- Removing a line also removes the metros assigned to it.
- Metro capacity is 6 passengers.
- Metro movement is automatic along the line:
  - Non-loop lines reverse direction at endpoints.
  - Loop lines continue around the loop.
- Maximum metros in the game is 4 total.
- When a new line is completed, one metro is added to it if the global metro limit is not reached.

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

## Timing and Spawning

- Game updates at 60 FPS.
- Each active station is initialized ready to spawn and attempts its first passenger on the first unpaused fixed update.
- Each station samples its own recurring spawn interval once, uniformly and inclusively from 70% to 130% of the 900-step base: 630-1,170 simulated steps, or 10.5-19.5 simulated seconds at 60 Hz.
- On each station spawn tick, that station attempts to spawn 1 passenger if it has room and then resets its counter even when full.
- The 2x and 4x controls advance counters by 2 and 4 per fixed update, reducing wall-clock time between attempts while preserving approximately the same simulated-time interval (subject to whole-tick quantization).

## Game Over

- A passenger is considered over-waiting at 40 seconds or more of station wait time.
- Game over occurs when 1 or more passengers are over-waiting.
- On game over:
  - Simulation time and gameplay updates stop.
  - `MiniMetroEnv.step(...)` calls become stable no-ops until reset; `PlayerPixelEnv.step(...)` rejects further actions until its required reset.
  - The game-over overlay presents lifetime passengers delivered as the primary result and remaining line credits as a secondary value.

## Controls

- Mouse:
  - Click and drag from station to station to create a line.
  - Hover a locked line button to see a two-line buy hint (`Buy` + price).
  - Click a locked line button (empty ring) to purchase that slot if enough line credits remain.
  - Click a line color button at the bottom to remove that line.
  - On game-over screen, click Restart or Exit buttons.
- Keyboard:
  - SPACE: pause / resume.
  - 1 / 2 / 3: set game speed to 1x / 2x / 4x.
  - R: restart (game-over screen).
  - ESC: exit (game-over screen).

## Programmatic Actions (Environment / API)

- `create_path`: create a line from station indices (with optional loop flag).
- `remove_path`: remove a line by index or id.
- `buy_line`: purchase the next locked line, optionally targeting its sequential button index.
- `pause`: pause simulation.
- `resume`: resume simulation.
- `noop` (or `None`): do nothing this step.
- Malformed actions are rejected without mutating game state.

## Player-Equivalent RL Controls

- The pixel RL environment uses the same 1920x1080 virtual player view, hitboxes, pygame event conversion, and fixed simulation updates as manual play.
- The policy observes only RGB pixels with a rendered software cursor. The default `fast` profile is 192x108 and the registered `fidelity` profile is 320x180; both are downsampled from the canonical player render.
- One action contains a kind plus a pointer coordinate. Supported kinds are no-op, mouse motion, left-button down, left-button up, Space, and the `1`/`2`/`3` speed keys. Mouse coordinates span the selected observation grid and map exactly to the edges of the canonical view.
- The default decision advances six fixed ticks, or 100 simulated milliseconds at 1x speed. Pause consumes decisions without accumulating simulation backlog; speed keys apply the same 1x/2x/4x gameplay multipliers as manual play.
- An episode terminates at game over and truncates at its configured decision horizon. The default learning reward is newly delivered passengers; the legacy pixel `display_score_delta` mode and structured `line_credits_delta` mode include line credits spent purchasing line slots.
- Adding mouse-driven stations, buttons, routes, passengers, or other visible content does not require a new action schema. Adding another keyboard control, changing action meanings, changing registered pixel profiles, or changing cursor pixels requires an explicit protocol update so saved models cannot silently receive a different task.
