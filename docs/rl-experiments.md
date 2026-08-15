# RL experiment ledger

Every experiment run against the pixel task, in order, including the ones that
failed and the ones whose first answer was wrong. A negative result that is
written down is cheaper than the same negative result discovered twice.

Each entry records the hypothesis, what was actually measured, and the verdict.
Verdicts are deliberately blunt: **CONFIRMED**, **REFUTED**, **INVALID** (the
experiment could not answer the question it was asked), or **SUPERSEDED**.

Reference points on Classic, used throughout:

| policy | deliveries |
| --- | --- |
| random | 0 (game over in 364 decisions) |
| scripted expert | ~19-20 |
| scripted heuristic (no learning) | **277.2 mean** |
| random legal play, REMOVE excluded | 178.2 mean |
| trained agent (semantic lane) | 190.8 mean -- **below the script** |

There is no win condition. `GAME_RULES.md` defines only game over, so the
objective is lifetime passengers delivered before the system is overwhelmed.

---

## E1 — Is the GPU being used at all?

**Hypothesis:** training is slow because the environment is slow.

**Measured:** `torch.cuda.is_available()` was `False`. The installed build was
`torch 2.13.0+cpu` on a machine with an RTX 4090. A forward+backward pass took
**398.88 ms on CPU against 2.73 ms on CUDA — 146x**.

**Cause:** `requirements-rl-locked.txt` pins a bare `torch==2.13.0`, and PyPI's
Windows wheel is the CPU build; CUDA builds for Windows exist only on
download.pytorch.org. The `sys_platform == 'linux'` markers on the `nvidia-*`
packages are *not* the cause and are not a misdetection — they are correct
guards that Windows rightly skips, and no `nvidia-*` package is installed even
now with CUDA working, because on Windows the CUDA runtime ships inside the
torch wheel.

**Verdict:** CONFIRMED as a real defect. It did **not** move the score, because
the binding constraint was elsewhere (see E4). Fixed by an opt-in CUDA overlay
plus a startup guard that fails when `--device auto` finds no accelerator.

---

## E2 — Does the encoder preserve the resolution it is given?

**Hypothesis:** raising the render profile gives the policy more to see.

**Measured:** it does not. `AdaptiveAvgPool2d((3,5))` collapsed **both** profiles
to an identical 960 values — 192x108 and 320x180 produced byte-identical output
shape. Each pooled cell covered **64x60 px** of a 320x180 frame. Shifting the
whole frame 16 px (1.5 station widths) moved the features **1.79%**, *less* than
a 2 px shift did (1.95%).

**Verdict:** CONFIRMED. The pool was deleted and the flatten sized from the
observation space (960 -> 14,080 at fidelity). Again this did **not** move the
score on its own.

---

## E3 — Fleet allocation as the scripted expert's limiter

**Hypothesis:** the expert scores ~19 because it under-uses locomotives and
carriages.

**Measured:** sweeping locomotives 1 -> 5 and carriages 0 -> 5 moved mean
deliveries **18.0 -> 18.5**.

**Verdict:** REFUTED. Capacity is not what bounds expert play. Games end after
~1000 decisions with only 4 stations ever spawned, so the limiter is upstream of
fleet size.

---

## E4 — Can RecurrentPPO learn this task from scratch?

**Hypothesis:** with the GPU and encoder fixed, PPO will start to learn.

**Measured:** two 3M-step runs (fast and fidelity profiles, seed 42) held
`rollout/ep_rew_mean` at **exactly 0.00 at every logged step**, with
`ep_len_mean` ~330 against random play's 364. Direct probe: across **12 random
episodes and 4,170 decisions, zero built a usable line**. Action-kind frequencies
stayed uniform at ~12.5% each.

**Reasoning:** the reward is not *sparse*, it is **unreachable**. Drawing a line
requires pointer-down on a ~10 px station, motion, then pointer-up on a
*different* station; that ordered sequence essentially never occurs by chance in
a 192x108 coordinate space. With no reward anywhere in a batch the advantage is
identically zero and the policy gradient is the zero vector, so no quantity of
steps, resolution, throughput or capacity changes anything.

**Verdict:** CONFIRMED, and it retroactively explains E1 and E2 producing no
score movement. Both runs were killed rather than left to spin. **Lesson: read a
reward curve before optimising the machinery that produces it.**

---

## E5 — Behaviour cloning from the scripted expert

**Hypothesis:** cloning the expert bootstraps past the exploration barrier.

**Measured:** BC drove `-log_prob` from the uniform **12.019 to 2.350** over
2,042 samples from 30 expert games (mean 19.0 deliveries) — roughly 9.5%
probability on the expert's exact action out of 165,888. The cloned policy
delivered **0**.

Inspecting the policy at the exact step the expert draws separated the halves:
it had learned **when** to act (noop 2.3%, motion/down/up 95%) but not **where**
(argmax x=81 against the expert's 123; `P(expert x)` 0.63% against a 0.52%
uniform).

**Verdict:** PARTIAL. Fitting demonstrations and reproducing them are different
problems. The failure localised to the pointer.

---

## E6 — Is the pointer failure a data limit?

**Hypothesis:** more demonstrations will fix the coordinates.

**Measured:** 80 expert episodes / 3,562 samples reached `-log_prob` 3.255 and
still delivered **0**, as did the tighter-fitting smaller run.

**Verdict:** REFUTED. Not data-limited.

---

## E7 — Flat coordinate head against a spatial heatmap (first attempt)

**Measured:** flat head at **8371x uniform** probability, spatial heatmap at
51.6x — apparently a crushing win for the status quo.

**Verdict:** INVALID. The expert's pointer actions mix two populations: drags
targeting stations, whose coordinates move with the layout, and clicks on fleet
controls, which sit at **fixed UI pixels in every game**. A flat head memorises a
constant trivially, so this measured recall of a constant rather than visual
grounding. The tell was an internal contradiction — 40% probability alongside a
*worse* argmax error than the arm it beat. **Lesson: when two metrics disagree
in direction, the measurement is wrong, not the surprising one.**

---

## E8 — Flat against spatial, station targets only

**Measured**, with UI-control samples excluded:

| head | P(expert x,y) | vs uniform | argmax error |
| --- | --- | --- | --- |
| flat categorical | 0.00924% | 1.9x | 58.5 px |
| spatial heatmap | 0.04603% | 9.5x | 38.1 px |

**Verdict:** CONFIRMED, reversing E7. The flat head is barely above chance at
pointing to a station. Architectural, not data-starved.

---

## E9 — Pointer resolution sweep

**Hypothesis:** a heatmap resampled ~15x from a 7x12 grid cannot resolve a ~10 px
station however well trained, because its finest addressable unit is coarser
than the target.

**Measured:** identical data, encoder, optimiser and 40 epochs, varying only
which encoder depth the heatmap is read from:

| pointer grid | upsample | pointer loss | deliveries |
| --- | --- | --- | --- |
| 7x12 (depth 6) | 15x | 6.50 | **0.00** |
| 27x48 (depth 2) | 4x | 3.07 | first non-zero |

**Verdict:** CONFIRMED — the single largest effect found before E12. A drag needs
~4 correct pointer actions in sequence, so per-action accuracy compounds, which
is why intermediate improvements showed up as exactly zero rather than partial
credit.

**Correction:** the depth-2 result was first reported as **6.17 mean / max 19**
from 6 evaluation episodes. Twelve held-out episodes gave **1.50 / max 9**.
Episode outcomes are near-bimodal — the drag lands and the run continues, or it
does not and the run dies at the deadline — so a six-episode mean mostly counts
lucky seeds. **Lesson: never report an effect size from a handful of episodes on
a bimodal outcome.**

---

## E10 — The forty-second deadline

**Observed** while debugging E9: every non-delivering policy dies at *exactly*
400 decisions. A decision advances 6 ticks at 60 Hz, so 400 x 0.1 s = **40.0 s**,
which is precisely the over-waiting threshold in `GAME_RULES.md`.

**Verdict:** CONFIRMED as a task characterisation, not a bug. The agent has a
hard 40-second budget to complete its first working drag or the run is over. Any
curriculum or reward shaping has to respect that window.

---

## E11 — Rendering the game at a smaller canvas

**Hypothesis (user's):** the observation is mostly whitespace with sub-pixel
content; render smaller with bigger icons.

**Measured** at the fast profile, confirming the premise exactly:

| entity | canonical | in observation | |
| --- | --- | --- | --- |
| station | 30 px | 3 px | |
| line | 10 px | 1 px | |
| passenger | 5 px | **0.5 px** | sub-pixel |

Ink coverage **3.98%** — 96% of the frame is empty. **Passengers are sub-pixel:
the agent cannot see the objects it is scored on.**

**But 600x800 is impossible.** Every smaller canvas fails a UI layout validator,
including 960x540, 800x600, 600x800 and even 1600x900, and so does 2x entities at
the full canvas. Mechanism: `station_safe_bottom = height * 0.9 + station_size +
margin`, so a shorter surface shrinks the resource-control band while button
sizes stay fixed, and larger stations push down into it — both directions squeeze
the same gap.

Scaling entities instead, with the (now named) `playfield_bottom_ratio` lowered
to buy room:

| entity scale | station | line | passenger | ink |
| --- | --- | --- | --- | --- |
| x1 | 3 px | 1 px | 0.5 px | 3.9% |
| x4 | 12 px | 4 px | 2 px | 10.7% |

**Verdict:** PARTIAL / NOT YET LANDED. Two blockers. Station spawn weights
candidates by `1/(1+distance)` toward the centroid of existing stations with no
size-aware minimum separation, so larger stations spawn **overlapping** (observed
at 3x). And scaling the UI hits a second validator, "resource controls disjoint",
because the horizontal offsets do not scale with the radii.

---

## E12 — Resolution-preserving U-Net against the Nature-DQN stack

**Hypothesis:** choosing where to click is **keypoint localisation**, not
classification. Nature DQN was built for the opposite job — Atari needed
translation *invariance* to pick one of 18 joystick actions, so it strides
position away on purpose, and this repository's variant strides 2 on the third
convolution where the original used stride 1, discarding another 2x. Preserving
resolution end-to-end should beat it.

**Measured**, identical data, loss, optimiser and eval seeds; 12 held-out
episodes:

| arm | params | pointer loss | deterministic | stochastic |
| --- | --- | --- | --- | --- |
| strided | 1,541,705 | 3.127 | 3.08 (max 9) | 0.92 |
| **U-Net** | **450,281** | **0.656** | **3.75 (max 17)** | **3.83 (max 16)** |

**Verdict:** CONFIRMED. Pointer loss 3.127 -> 0.656 is **11.8x** the probability
on the expert's exact pixel, with **3.4x fewer parameters** — preserving
resolution removes the giant flatten-to-linear that dominated the old count.

The stochastic column is the strongest evidence and would be invisible in a mean:
sampling used to cost most of the score (0.92 against 3.08) because a diffuse
heatmap breaks a multi-step drag the moment one coordinate lands wrong; it now
costs nothing (3.83 against 3.75). That is what a genuinely peaked heatmap looks
like, and it matters because PPO samples its actions.

---

## E13 — Raising the information ceiling under a resolution-preserving encoder

**Hypothesis:** E2 showed extra input resolution was wasted because the encoder
averaged it away, and E12 replaced that encoder. A resolution-preserving network
should now convert extra pixels into score, where the strided one could not.

**Measured**, U-Net at the fidelity profile (320x180) against the same U-Net at
fast (192x108), 12 held-out episodes:

| lane | pointer loss | deterministic | stochastic |
| --- | --- | --- | --- |
| U-Net @ fast 192x108 | 0.656 | 3.75 (max 17) | 3.83 |
| **U-Net @ fidelity 320x180** | **0.467** | **17.33 (max 21)** | 16.08 (max 22) |

Per-episode deterministic: 21, 14, 18, 21, 21, 20, 18, 13, 20, 19, 3, 20. All
twelve ended in game over; **none hit the 4000-decision horizon**, so no total is
right-censored.

**Verdict:** CONFIRMED, and the largest single jump measured — 3.75 to 17.33,
against a scripted teacher averaging ~19-20. Ten of twelve episodes score 18 or
better. This is the other half of E11: render sets the information ceiling and
architecture decides how much survives, and only fixing both converts pixels into
deliveries.

**Caveats, stated because the protocol in `rl-model-selection.md` demands them.**
This is **one seed and 12 episodes**, against a pre-registered standard of five
seeds and 20 episodes with run-level statistics — so the number is a strong
signal, not a settled effect size. The fidelity arm also used batch size 64
against 96 for the fast arms, to fit memory, so it differs in **two** variables
rather than one; the resolution comparison is confounded to that extent. And the
policy is cloned, non-recurrent, and cannot in principle exceed its teacher.

---

## E14 — Reward shaping on the connection milestone (teacher-free attempt 1)

**Hypothesis:** paying partial credit for joining stations onto a route gives an
exploring policy the gradient the deliveries reward cannot.

**Measured:** across **24 random episodes and 8,721 decisions, 0 received any
shaping credit.**

**Verdict:** REFUTED, and obviously so in hindsight. The credit was attached to
"a usable line exists", which is *precisely* the event E4 measured as
unreachable. Shaping an unreachable milestone reproduces the zero gradient it
was built to remove. **Lesson: a shaping signal must be reachable by the policy
that needs it — check that it fires under random play before training on it.**

---

## E15 — Dense proximity shaping, and the farming exploit it creates

**Hypothesis:** a signal available on *every* pointer-down, rising smoothly as
the click nears a station, is reachable where a milestone is not.

**Measured:** **24 of 24** random episodes received credit, mean 0.233 per
episode. The gradient is no longer zero.

**But it is farmable.** Dense credit is payable on every action, so at 0.02 per
pointer-down over a 4000-decision episode a policy could bank ~80 against the
~19-20 real play earns. The optimal policy would be to stand beside a station
and click forever. Capped with a per-episode budget of 1.0; a spam-click policy
now scores **1.00 total**, verified by driving exactly that degenerate policy.

**Verdict:** CONFIRMED as reachable, with the exploit closed. Whether it is
*sufficient* to learn from scratch is E16 and is not yet answered. Shaping is a
`gym.Wrapper`, not a `RewardMode`, because adding an enum member rotates the
protocol fingerprint and breaks task reconstruction for every saved model — the
suite caught that with six identity failures and a legacy byte-compat error.

---

## E16 — Learning without a teacher, on shaped reward alone

**Hypothesis:** with a reachable, bounded shaping signal (E15) an agent can find
the game unaided — the barrier was a zero gradient, not difficulty.

**Measured**, RecurrentPPO from scratch, 300,000 steps, shaping on, flat pointer
head:

| metric | result |
| --- | --- |
| `rollout/ep_rew_mean` (shaped) | 0.31 → **0.97, then flat** |
| `eval/mean_reward` (true deliveries, unshaped) | **0.00** at 100k, 150k, 200k, 250k, 300k |

**Verdict:** REFUTED as posed, and instructive. The gradient was real — reward
moved off zero for the first time on this task, against 0.00 across 3M steps in
E4 — but the agent converged to collecting **exactly the 1.0 shaping budget** and
never earned a single passenger.

**Reasoning:** the budget that stops the bootstrap being farmed (E15) also caps
the incentive. Once banked there is no further gradient until a delivery, and a
delivery still requires the same unreachable conjunction. Proximity credit
teaches "click near stations"; it does not teach "complete the drag", because
pointer-down → motion → pointer-up on a *different* station remains a sequence
random exploration does not produce. The intermediate rung is missing, not the
starting one.

Also note the arm carried the flat pointer head, which E12 showed cannot resolve
a station in the first place, so this does not yet test whether a policy that
*can* point benefits from the same signal.

**Completed follow-up.** That combination was then run — spatial pointer *and*
the full-gesture ladder, 600,000 steps — and reached the same place:
`ep_rew_mean` plateaued at **1.03** with `eval/mean_reward` at **0.00 at every
checkpoint through 600k**. Three teacher-free PPO configurations have now
returned exactly zero deliveries: unshaped, proximity-shaped, and
ladder-shaped-with-a-working-pointer. Go-Explore (E19) reached lines under the
same no-teacher constraint, which is why the archive approach rather than the
reward approach is the one worth extending.

**Standing implication:** a bootstrap signal has to form a *ladder* to the
objective, not a single rung. Each rung must be reachable from the one below it.

---

## E17 — Was it exploring? Entropy and action frequencies of the shaped run

**Question:** did the agent explore the action space at all, or collapse early?

**Measured**, from the 300,000-step shaped run (`train/entropy_loss` is negative
entropy; maximum for `MultiDiscrete([8,192,108])` is 12.02 nats):

| | start | end |
| --- | --- | --- |
| entropy | 12.016 | **10.603** |

Still **88% of maximum entropy** after 300k steps. But the aggregate hides the
structure. Sampling 1,500 actions from the final checkpoint:

| kind | frequency | uniform |
| --- | --- | --- |
| **down** | **63.5%** | 12.5% |
| motion | 4.6% | 12.5% |
| up | 2.9% | 12.5% |
| others | 4.6-6.7% each | 12.5% |

x coordinate spread: std **48.7** against a uniform 55.4.

**Verdict:** exploration collapsed on precisely the dimension the reward
addressed and stayed random on the dimensions it did not. Proximity credit is
paid only on pointer-**down**, and pointer-down is enriched 5x. Coordinates are
still near-uniform — and they hold 9.94 of the 10.60 remaining nats, which is
why aggregate entropy looks high while the policy is in fact committed on kind.

**The damaging part:** motion (4.6%) and up (2.9%) were driven *below* uniform.
PPO correctly inferred they were worth less than pointer-down, so the shaping
actively taught the agent to stop performing the two actions a drag requires. A
reward that pays for one step of a sequence does not merely fail to teach the
sequence, it suppresses the rest of it.

**Implication for the ladder E16 called for:** rungs must cover the whole
gesture, not its first step — credit for a drag in progress, and a larger credit
for a pointer-up that lands on a *different* station and completes one.

---

## E18 — Go-Explore: archive, return, explore

**Research:** [Go-Explore](https://www.nature.com/articles/s41586-020-03157-9) (Ecoffet et al., Nature 2021) targets exactly this failure. Its
premise is that exploration algorithms *forget*: an agent that stumbles into a
promising state wanders off and cannot get back. So it archives states, **returns**
to one without exploring, then explores onward, and progress accumulates.
[Random Network Distillation](https://arxiv.org/abs/1810.12894) was considered and rejected on its documented
failure mode — it detects only large state changes, while here a drawn line moves
a few hundred of 20,736 pixels and the clock and moving metros change constantly
and mean nothing.

**Two prerequisites verified before building:** the game serialises and restores
*exactly* (simulation time, paths and the observation itself are byte-identical
after a round trip), so returning costs one deserialize rather than a replay. And
`serialize_game` **refuses to save mid-gesture** — "cannot save while a
path-creation gesture is active" — which is precisely the state worth returning
to, so a cell stores its last saveable ancestor plus the action suffix that
reaches it. That is Go-Explore's own deterministic phase.

**Measured**, 800 iterations x 40 random steps:

| | |
| --- | --- |
| cells archived | 12 |
| **cells holding the pointer on a station** | **4** |
| iterations ending mid-drag | 381/800 |
| usable lines created | **0** |
| deliveries | **0** |

**Verdict:** the machinery works; the budget does not. Mid-drag states — the
promising intermediate — *are* archived and returned to. The arithmetic explains
the zero: a drag ends at the **first** pointer-up, and a pointer-up lands on a
different station roughly 0.4% of the time, so ~268 visits to held cells buys
about **one** expected completion. Observing zero is within noise, not evidence
against the method.

**A correction this experiment forced.** E15 recorded random play completing a
drag in "roughly 4% of episodes". That was **one lucky episode out of 24**; a
second seed set gave zero, and 24,000 random actions here produced no line at
all. The real rate is nearer 1 in 1,000 episodes. This is the same error E9
already recorded and I repeated it — reporting a rate from a single event.

**A claim corrected in passing:** the gesture is **two** precise hits, not four.
`DOWN` on one station then `UP` on another creates a line with no motion between
them, verified directly. Motion is only needed to route through additional
stations. The conjunction is therefore two ~0.14%-of-grid hits, which is the
whole difficulty.

---

## E19 — Go-Explore with the budget it needed: the first teacher-free lines

**Measured**, 12,000 then 15,000 iterations x 10 random steps:

| | 800 iters | 12,000 | 15,000 (fleet in key) |
| --- | --- | --- | --- |
| cells | 12 | 30 | 35 |
| **usable lines created** | 0 | **7** | **10** |
| locomotives assigned | — | — | **0** |
| deliveries | 0 | 0 | 0 |

**Verdict:** CONFIRMED for the first rung, and this is the headline result of the
teacher-free work. **Go-Explore draws lines with no teacher** — in 40-60
decisions — which nothing else here has done: random play never does it (0 across
48 episodes), and PPO never does it (0 across 3M steps and two shaped runs).
Verified through an independent code path, `count_connected_stations` returning 2
after restoring an archived cell.

Deliveries stay at zero for a structural reason, and adding fleet size to the
cell key found the wall rather than climbing it: **no locomotive was ever
assigned**. A line with no locomotive carries nobody, and assigning one means
clicking a small "+" control that exists only in states that already have a
line. It is the same targeting problem one rung up.

**What the whole teacher-free arc establishes:** every rung of this game is a
precise click on a small target — a station covers ~0.14% of the coordinate
grid, a fleet control less. Random exploration clears each rung with probability
in the 0.1-0.4% range, Go-Explore compounds rungs but pays ~1,000 trials each,
and shaped PPO banks whichever rung it can reach and stops. The difficulty is not
strategy, credit assignment, or horizon. It is **targeting precision**, and it
recurs identically at every level of the interaction.

That is the strongest argument yet for the render change, and it reframes it:
enlarging stations and controls is not cosmetic and not only a perception fix —
it raises the hit probability of every rung simultaneously, which is the single
intervention that helps random exploration, shaped RL, and Go-Explore at once.

---

## E20 — The semantic lane: name stations instead of pointing at pixels

**Change (user's call):** clicking anywhere but a station is meaningless, so stop
making it expressible. `SemanticMetroEnv` hands the agent station positions and
shapes, who is waiting and for what, and line/fleet state, and takes actions that
*name* stations and lines. Action space falls from 8x192x108 = 165,888 to
5x20x20 = 2,000, and every action means something.

**Measured, with no learning at all:**

| | pixel task | semantic | semantic + masks |
| --- | --- | --- | --- |
| random builds a usable line | 0 / 48 | 2 / 12 | **12 / 12** |
| random delivers | never | 0 / 12 | **6 / 12** |
| deliveries | 0 | 0 | **mean 2.8, max 8** |

Masking is load-bearing, not a convenience: station slots run to twenty while a
young game has three, so unmasked sampling wastes nearly every CONNECT on a
station that does not exist.

**MaskablePPO, 400,000 steps, 20 held-out episodes on disjoint seeds:**

per-episode `[9, 8, 5, 8, 9, 4, 0, 7, 8, 6, 3, 1, 1, 1, 9, 8, 7, 9, 0, 9]` —
**mean 5.60, median 7.0, max 9**, against random-legal 2.8 and the scripted
expert's ~19-20.

**Verdict:** CONFIRMED as the unblock. This is the first reward curve on this
project that climbed on *real deliveries* rather than shaping credit; every
pixel-lane run either sat at exactly 0.00 or banked a shaping budget while
evaluation stayed at zero. It roughly doubles random play and remains well short
of the scripted expert, so the lane is open but not solved.

**A reporting bug worth keeping.** The first evaluation of this model reported
**0.00 across all 20 episodes** while training reward read 5.91. The policy was
fine; the evaluator used `deterministic=True`, and `WAIT` is the single most
likely action at almost every step — correctly, since most steps should wait — so
greedy argmax waits forever. Measured on the same checkpoint: deterministic
`WAIT x3335, CONNECT x1`, mean 0.00; stochastic `WAIT x2126, CONNECT x2057,
ASSIGN x43`, mean 6.25. **For any task with a dominant no-op, greedy evaluation
can report a working policy as a total failure.** The evaluator now reports both.

**Standing note:** this lane is strictly easier than the pixel task and its
scores are not interchangeable with pixel-task scores. The pixel environment is
untouched and remains the player-equivalent lane.

---

## E21 — The semantic lane, trained: 190.8 deliveries on held-out seeds

**Setup:** MaskablePPO, 600,000 steps, one seed, on the corrected environment --
exact per-action masking, routes editable in both directions, episodes running to
a real game over, canonical shape slots, and station-to-line distances in the
observation.

**Training curve** (`rollout/ep_rew_mean`):

| steps | 73k | 139k | 192k | 256k | 323k | 475k | 600k |
| --- | --- | --- | --- | --- | --- | --- | --- |
| deliveries | 1.1 | 26.7 | 50.1 | 67.5 | 108 | 162 | **222** |

It never plateaued; the budget ran out first. Episode length rose from 506 to
~3,400 decisions, so the agent is *surviving* longer, which is the actual
objective rather than a proxy for it.

**Held-out, 20 episodes, seeds disjoint from training, stochastic:**

`[186, 198, 109, 180, 184, 264, 242, 179, 146, 336, 117, 383, 111, 108, 136, 101, 189, 178, 176, 293]`

**mean 190.80, median 179.5, max 383**, against **0** for random legal play on the
same action space.

**Verdict:** CONFIRMED. This is the first policy on this project that plays the
game. A recorded episode reached 174 deliveries over 6,174 decisions ending in a
genuine game over, with 2 lines and a 7-station route, and its action mix shows
real strategy rather than coasting: 147 prepends, 73 connects, **71 removals** and
57 extends -- it redraws lines, the move that had been masked out as "never
useful to an exploring policy".

**Caveats, stated because the protocol demands them.** One seed against the
pre-registered five. The **deterministic** evaluation reads 0.00 on all 20
episodes -- the greedy-no-op trap from E20, since WAIT is 94% of correct play and
argmax therefore waits forever; the stochastic figure is the real one. And the
random baseline of 0 is not a claim that the game is hard for a random policy in
general, only on this action space, where removals and mis-ordered routes undo
progress.

**Open thread:** across 6,174 decisions the agent used ASSIGN_LOCOMOTIVE 4 times,
ATTACH_CARRIAGE twice and PURCHASE_LINE once. Either those options are rarely
offered or they are badly under-used, and a line without a locomotive carries
nobody. That is the next measurement.

---

## E22 — A run is not monotonic, and the peak was thrown away

**Measured**, v4 (MaskablePPO, MLP, diverse layouts, flat 3e-4):

| steps | 400k | 500k | 600k | 700k | 856k |
| --- | --- | --- | --- | --- | --- |
| deliveries | 76.9 | **97.5** | 89.4 | 46.0 | 35.5 |

Not noise. Across the same span `entropy_loss` went **-0.282 to -0.420**,
`approx_kl` **0.0037 to 0.0128**, and `clip_fraction` **0.034 to 0.082**: updates
grew larger as the policy got worse. A step size that suits a crude policy is too
hot once an episode runs thousands of decisions and one bad update costs a whole
network.

**Verdict:** CONFIRMED, and the damage was self-inflicted. The trainer called
`model.save()` only at the end, so the 97.5 policy was never written to disk. The
run's best result is now only a number in a log — unrecoverable. Losing the peak
was worse than the collapse, because the collapse was recoverable and the loss is
not.

**Fixed:** a `KeepBest` callback evaluates on held-out seeds every `--eval-every`
steps and saves whichever policy actually scored best, plus a `-latest` for
resuming; the final report reloads the best rather than assuming the last update
was the good one. The learning rate decays with progress. The evaluation history
prints inline, so a collapse is visible while it happens instead of reconstructed
from a log afterwards.

**A second error this exposed.** v3 was described as "never plateaued" and that
was read as headroom justifying a 1.2M-step follow-up. It was flat at 206 from
600k onward — it had plateaued, and a still-rising final number was mistaken for
a trend. Same shape as the six-episode mean in E9: extrapolating from the
direction of travel rather than from the data.

**Early v5 comparison** (checkpointed, decaying LR): 0.0 at 50k, **57.6** at
100k, **89.6** at 150k, 81.8 at 200k — reaching by 150k roughly what v4 needed
~500k to reach. One seed against one seed, so that is a hypothesis about the
learning rate, not a measurement.

---

## E23 — The game escalates on the agent's score, not on the clock

**Measured** under the v3 policy on two independent seeds, recording when each new
station arrives:

| new station | seed 9000 | seed 9005 |
| --- | --- | --- |
| 4th | decision 456, **10 deliveries** | decision 527, **10 deliveries** |
| 5th | decision 1687, **40** | decision 1792, **40** |
| 6th | decision 3558, **90** | decision 3603, **90** |
| 7th | decision 5615, **160** | decision 5566, **160** |

The decision counts differ; the **delivery counts are identical**. Stations arrive
on a delivery ladder at 10, 40, 90, 160 -- first differences 30, 50, 70, so a
quadratic schedule -- and not on a timer.

**Verdict:** CONFIRMED, and it defines the goal's endpoint. The difficulty ramp is
*driven by the agent's own success*: every delivery brings the next station
closer, and each station adds passengers the same capped fleet must serve. Both
runs ended at 7 stations with 2 lines, 217 and 186 deliveries.

**What this means for "spawn beyond the point of sustainability".** That point is
structural, not distant: line slots unlock on delivery milestones, and the fleet
is fixed at 4 locomotives and 2 carriages because the weekly-offer upgrades that
grow it are interactive-play only and never applied on the headless path. Total
in-transit capacity is therefore 36 riders no matter how well the agent plays. A
policy that keeps improving does not escape the ramp -- it *accelerates* it, and
the run ends when arrivals at 7+ stations exceed what 4 locomotives can move.

So the success criterion is reachable and close: reach the capacity wall
reliably, rather than die early to a mistake. The open question is whether the
wall sits at ~200 deliveries for every policy, or whether better routing pushes
it further -- which is exactly what a non-collapsing training run would answer.

---

## E24 — Adversarial review: the headline result was below a 30-line script

An adversarial reviewer was asked to refute E21's claims and did. All numbers on
E21's own held-out seed set (base 9000), 20 episodes.

| policy | mean | median | max |
| --- | --- | --- | --- |
| **scripted heuristic, ~15 actions/episode, no learning** | **277.15** | 277.5 | 410 |
| trained agent (E21, stochastic) | 190.80 | 179.5 | 383 |
| **random legal play, REMOVE_LINE excluded** | **178.2** | 189.5 | 257 |
| build one 2-station line then wait forever | 5.6 | 6.5 | 9 |
| random legal play (the published baseline) | 0.0 | 0 | 0 |

**Verdict: SUPERSEDED. E21's three claims do not survive.**

**"The first policy that plays the game" is false.** A script that buys a line
slot, connects nearest unserved stations, crews each line and otherwise waits
beats the agent on **17 of 20 seeds** and outlives it (10,614 decisions against
~6,000-7,000). The agent is not merely coasting -- freezing it into WAIT after N
decisions costs most of its score (N=200 -> 19.6, N=1000 -> 54.0, unfrozen ->
201.4), so its decisions carry ~73% of its result. The accurate charge is that
its active play is **worse than a fixed rule**.

**"Random legal play scores 0, so any positive score is learning" is false.**
Delete one action kind from random sampling -- REMOVE_LINE -- and the identical
uniform policy scores **178.2**, reproducing **93%** of the agent's headline.
Random play fires REMOVE 68-87 times per episode and terminates at exactly 417
decisions on all 20 seeds, byte-identical to doing nothing. Its 0 is a
no-op-equivalent outcome, not a difficulty measurement. The repo already
contained the contradiction: `semantic_env.py` records random play at 180.8
before REMOVE was un-masked. **Every "beats random" comparison after that commit
is inflated.**

**"Decision freedom was restored" is false.** In the trained policy's own state
distribution (4 seeds, 23,286 states): median **2** legal actions, median **0**
*constructive* ones, and **61%** of states offering nothing but WAIT and
REMOVE. The agency gate reads a healthy 4 only because it samples *random*
play's distribution, where constant self-destruction manufactures rebuild
options. Un-masking REMOVE raised the counter by adding destructive entries.

**The gate itself is weak.** `test_env_agency.py` stayed fully green under three
environment-breaking mutations: horizon forced to 450 (re-censoring the very bug
it cites), lines capped at 3 stations, and fleet assignment masked out entirely
so no delivery is possible. And
`test_a_degenerate_policy_cannot_outscore_real_play` **cannot fail** -- its
baseline is random play scoring 0, so the bar is a hardcoded 1.0 floor, and the
two policies it tests are guaranteed to score 0.

**Fixed in this commit:** the age gate keyed by `id(path)` leaked on **71%** of
fresh lines (CPython recycles addresses and `setdefault` kept the dead line's
birth time); now keyed by `path.id`, pruned each step, and failing closed --
measured 0%. And `train_semantic.py` printed the false random-baseline claim on
every run.

---

## Standing conclusions

1. **Read the reward curve first.** E1 and E2 were real defects that could not
   have moved the score, and were fixed before E4 revealed why.
2. **The reward is unreachable, not sparse.** Any approach must bootstrap
   (cloning, curriculum, or shaped reward) rather than explore.
3. **Pointer precision compounds.** A drag needs ~4 correct coordinates in
   sequence, so partial improvements read as exactly zero until a threshold.
4. **Resolution is destroyed in two independent places** — at render, where a
   passenger is 0.5 px, and in the encoder, which strides it away. Fixing one
   without the other leaves the ceiling in place.
5. **Cloning cannot exceed its teacher.** The scripted expert averages ~19, so
   that is the ceiling of every BC result here. Beating it requires a better
   teacher or genuine RL fine-tuning.
6. **If an action is meaningless, do not make it expressible.** Removing pixel
   coordinates from the action space achieved in one change what better
   encoders, spatial heatmaps, shaping ladders and an exploration archive could
   not: a *random* policy now delivers where no PPO run on pixels ever did.
7. **With a dominant no-op action, greedy evaluation is misleading.** The same
   checkpoint scored 0.00 deterministic and 6.25 stochastic, because WAIT is the
   most likely single action almost everywhere. Report both.
8. **The difficulty is targeting precision, at every rung.** Stations cover
   ~0.14% of the coordinate grid and fleet controls less; random exploration
   clears any given rung with probability 0.1-0.4%. Go-Explore compounds rungs
   and reached lines, then stalled on the locomotive control. Enlarging the
   render targets is therefore the one change that helps every method at once.
7. **A bootstrap signal must form a ladder, not a single rung.** Shaping
   proximity moved reward off zero for the first time, and the agent then banked
   exactly the budget and stopped: true deliveries stayed at 0.00 through
   300,000 steps. Every rung has to be reachable from the one below it.
7. **A shaping signal must be reachable, and then it must be bounded.** E14
   shaped an unreachable milestone and changed nothing; E15 made it dense and
   immediately created a farming exploit worth 4x the real objective. Both
   failure modes are cheap to test for before any training run: check the signal
   fires under random play, then drive a deliberately degenerate policy against
   it.
