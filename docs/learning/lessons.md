# Lessons

The one-line form of every lesson this repo has paid for. Read this file at session start; it is short by construction.

Each rule links into [lessons-evidence.md](lessons-evidence.md), which holds the war story and the anchor. Open that only when a rule is in doubt, or the work is in that area — it is not session-start reading.

A new lesson is an entry there plus one line here. There is no `lessons:check` script in this repo yet, so the two files are kept in step by hand: a rule always has an entry, and an entry always has a rule.

When a lesson becomes a gate — a test, a lint rule, a fixed command — delete both halves. The machine enforces it, so nobody needs to read it.

## Rules

### Measurement

- Resample a simulator's randomness when planning inside it; a reproducible simulator is not a deterministic game, and one rollout per candidate selects the luckiest future rather than the best action. ([evidence](lessons-evidence.md#resample-the-simulators-randomness-when-planning-inside-it))
- A deterministic simulation is not a faithful one: prove a snapshot reproduces the live run's continuation, since a rewound seed is perfectly repeatable and perfectly wrong. ([evidence](lessons-evidence.md#deterministic-is-not-faithful))
- Drive a gate with a policy that can actually play; one driven by random play only tests what bad play happens to touch. ([evidence](lessons-evidence.md#drive-a-gate-with-play-that-can-play))
- Read the outcome curve before optimising the machinery that produces it; a real defect on a path that carries no signal buys nothing. ([evidence](lessons-evidence.md#read-the-outcome-curve-before-optimising-the-machinery-that-produces-it))
- When two metrics from one experiment disagree in direction, the measurement is wrong — not the surprising one. ([evidence](lessons-evidence.md#when-two-metrics-disagree-in-direction-the-measurement-is-wrong))
- Do not report an effect size from a handful of trials when the outcome is bimodal; the mean is mostly a count of lucky seeds. ([evidence](lessons-evidence.md#do-not-report-an-effect-size-from-a-handful-of-bimodal-trials))

- Save the best result while it exists; a training run is not monotonic and the final weights are not the peak. ([evidence](lessons-evidence.md#save-the-best-result-while-it-exists))
- A stated intention is not a completed action -- end a turn on what was done, not on what will be done next. ([evidence](lessons-evidence.md#a-stated-intention-is-not-a-completed-action))

### Model and task design

- Before scaling a student, measure the teacher's own headroom; imitation cannot exceed its labels, and a plateau across unrelated architectures indicts the target rather than the learner. ([evidence](lessons-evidence.md#measure-the-teachers-headroom-before-scaling-the-student))
- Set a lookahead from the measured interval between consequences; one shorter than that gap sees cost without benefit and reliably recommends inaction. ([evidence](lessons-evidence.md#set-a-lookahead-from-the-interval-between-consequences))
- Validate the capability the agent gained, not the mechanism you built: measure what it can now reach, express, decide and exploit. ([evidence](lessons-evidence.md#validate-the-capability-not-the-mechanism))

- Match a representation's finest addressable unit to the smallest target it must resolve, before tuning anything else about it. ([evidence](lessons-evidence.md#match-the-finest-addressable-unit-to-the-smallest-target))
- A training-time signal must be reachable by the policy that needs it, and then bounded against being farmed. ([evidence](lessons-evidence.md#a-training-signal-must-be-reachable-then-bounded))
- Keep training-time concerns out of fingerprinted contracts; a wrapper costs nothing, an enum member invalidates every saved artifact. ([evidence](lessons-evidence.md#keep-training-time-concerns-out-of-fingerprinted-contracts))

### Editing this repo

- Anchor programmatic text edits to the file's real bytes: these files are CRLF, and a formatter may already have rewritten the line you are matching. ([evidence](lessons-evidence.md#anchor-text-edits-to-the-files-real-bytes))
