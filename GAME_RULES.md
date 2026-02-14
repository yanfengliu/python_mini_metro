## Metro Line Unlock Rules

- The game starts with exactly `1` available metro line.
- New line slots unlock based on cumulative travels handled (delivered passengers):
  - `2nd` line unlocks at `100` total travels.
  - `3rd` line unlocks at `250` total travels.
  - `4th` line unlocks at `500` total travels.
- Line colors are randomized at runtime, so each run can have a different line color set.
- The cumulative travel count is persistent for the current run and only increases as passengers reach their destinations.
