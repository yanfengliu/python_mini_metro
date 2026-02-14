## Game Rules

This document summarizes the game rules currently implemented in code.

## Objective

- Build and manage metro lines to deliver passengers to stations that match their destination shape.
- Maximize the score (total successful passenger deliveries) before game over.

## Stations and Passengers

- The map contains 10 stations.
- Station shapes are from: rectangle, circle, triangle, and cross.
- Each station can hold up to 12 waiting passengers.
- Passengers spawn with a destination shape that is different from their origin station shape.
- A passenger is delivered when they reach any station whose shape matches their destination shape.
- Passengers waiting at stations accumulate wait time; passengers riding metros do not.

## Metro Lines and Trains

- You can create a line by connecting at least 2 stations.
- Duplicate station picks are ignored while creating a line.
- Optional loop creation is supported by connecting the line back to its first station.
- A line can only be created if there is an unlocked line slot available.
- Removing a line also removes the metros assigned to it.
- Metro capacity is 6 passengers.
- Metro movement is automatic along the line:
  - Non-loop lines reverse direction at endpoints.
  - Loop lines continue around the loop.
- Maximum metros in the game is 4 total.
- When a new line is completed, one metro is added to it if the global metro limit is not reached.

## Scoring and Progression

- Score increases by 1 for each delivered passenger.
- The game tracks cumulative travels handled (delivered passengers).
- Unlocked line slots are based on cumulative travels:
  - Start with 1 available line.
  - Unlock 2nd line at 100 travels.
  - Unlock 3rd line at 250 travels.
  - Unlock 4th line at 500 travels.
- Line colors are randomized at runtime each run.

## Passenger Routing and Transfers

- Passengers compute travel plans based on currently available, completed lines.
- Routing is shortest-hop style (BFS over the station graph).
- If multiple stations match a destination shape, the game uses one with a valid route.
- Passengers can transfer between lines at stations according to their travel plan.
- If no route exists, passengers wait until the network changes.

## Timing and Spawning

- Game updates at 60 FPS.
- Passenger spawning starts at step 1, then repeats every 600 steps (about every 10 seconds at 60 FPS).
- On each spawn tick, each station attempts to spawn 1 passenger if it has room.

## Game Over

- A passenger is considered over-waiting at 60 seconds or more of station wait time.
- Game over occurs when 20 or more passengers are over-waiting.
- On game over:
  - Simulation time and gameplay updates stop.
  - A game-over overlay appears with final score.

## Controls

- Mouse:
  - Click and drag from station to station to create a line.
  - Click a line color button at the top to remove that line.
  - On game-over screen, click Restart or Exit buttons.
- Keyboard:
  - SPACE: pause / resume.
  - R: restart (game-over screen).
  - ESC: exit (game-over screen).

## Programmatic Actions (Environment / API)

- `create_path`: create a line from station indices (with optional loop flag).
- `remove_path`: remove a line by index or id.
- `pause`: pause simulation.
- `resume`: resume simulation.
- `noop` (or `None`): do nothing this step.
