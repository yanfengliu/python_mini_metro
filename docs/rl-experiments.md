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

## E25 — Cloning the heuristic: two missing quantities, and an honest ceiling

The from-scratch search was abandoned after the collapse diagnosis was refuted
(E24) and no branch reproduced the collapse at 800k. Instead: clone the scripted
heuristic, then fine-tune. Two defects were found, both of the same shape -- a
quantity the machinery depended on was simply absent, so the visible symptom
pointed nowhere near the cause.

**Defect 1: the decision was not representable from the observation.** The clone
scored 198.8 against a 276.9 teacher despite 97.8% label agreement. That figure
was WAIT drowning everything: agreement on the teacher's **real** decisions was
**44.2%**, and it inverted a specific pair -- teacher EXTEND 14 / PREPEND 9,
clone 8 / 12. The teacher grafts each station onto the nearer line **end**, but
the observation reported only distance to the *nearest* endpoint, collapsing the
two ends into one number. Adding both (574 floats, was 494) took real-decision
agreement **44.2% -> 81.5%** and deliveries **198.8 -> 227.0**.

**Defect 2: the critic was never cloned.** Warm-starting PPO destroyed the policy
within 50k steps, twice, at `ent_coef` 0.001 and again at 0.0 -- so entropy was
not the cause. The clone trained only the policy head, leaving the value function
at initialisation: **0.28 against true discounted returns of ~32**. PPO's first
advantages were therefore (return minus garbage). Fitting the critic to the
teacher's own return-to-go moved it to **21.12**, and the first fine-tune eval
went **0.2 -> 146.5**.

**Where it actually lands, on 12 held-out episodes:**

| policy | mean | 95% CI |
| --- | --- | --- |
| scripted heuristic (teacher) | ~262 | -- |
| **cloned policy, deterministic** | **197.67** | +/-42.91 |
| control: one line then wait forever | 189.75 | +/-46.95 |
| control: random legal play | 0.00 | -- |

**Verdict: PARTIAL, and the honest reading is negative.** The clone's +7.9 margin
over a trivial control is far inside the interval -- it does **not** clearly beat
"build one line and wait", and it remains well below its own teacher. A recorded
episode reaches 378 deliveries and dies at a genuine game over, having built one
9-station line and spent **8,848 of 8,904 decisions waiting**.

**What that says about the task.** Every strong policy here converges on the same
shape: one line through every station, fully crewed, then wait. E23 showed the
difficulty ramp is keyed to deliveries, and the fleet is hard-capped at 4
locomotives and 2 carriages on the RL path, so total in-transit capacity is 36
riders regardless of skill. The ceiling may simply be close, and the remaining
headroom is route *ordering* -- which is exactly the decision the observation was
blind to until this experiment.

**Still unproven:** that any learned policy can exceed the scripted heuristic.
Fine-tuning from the corrected clone rose to 146.5 at 50k then fell to 46.4 at
100k, so PPO still erodes a cloned policy even with a fitted critic and zero
entropy bonus. The best-evidenced untried remedy is AlphaStar's continual KL
penalty toward the frozen reference, worth +380 Elo in their ablation against
+84 for initialisation alone.

---

## E26 — A KL anchor stops the drift that ended every previous fine-tune

**Hypothesis:** every warm start so far decayed. AlphaStar's ablation says
*initialising* from a reference is worth +84 Elo while a **continual** KL penalty
toward that same frozen reference is worth **+380** on top -- the reference is an
anchor, not a launch pad.

**Measured**, identical starting policy (`bc3`), identical hyperparameters, the
only difference being `--anchor-coef 10.0`:

| steps | anchored | unanchored |
| --- | --- | --- |
| 50k | 155.2 | 146.5 |
| 100k | **167.0** | **46.4** |
| 150k | **185.5** | -- |
| 200k | 175.4 | -- |

**Verdict: CONFIRMED.** This is the first configuration on this project where a
policy *improves* with training rather than degrading. The unanchored run lost
two-thirds of its score between 50k and 100k; the anchored run gained.

**Why it works where `target_kl` would not.** `target_kl` bounds one update
against the *previous* policy, so a slow drift made of many individually-tiny
steps passes it untouched -- and that is exactly the drift observed here, and
exactly why the earlier `targetkl` branch showed nothing. The anchor bounds
distance from a *fixed good policy*, so drift accumulates a cost instead of being
free. It remains a floor rather than a ceiling: a better action is still
available, it just has to outweigh the divergence it costs.

The mechanism was verified before being trusted -- over 2048 steps, KL to the
reference grows 0.0110 unanchored against 0.0078 at coefficient 1.0.

**Completed run (700k steps).** The early monotonic climb did not continue. Full
eval history: 155, 167, 186, 175, 144, 178, 194, 152, 192, 105, 151, 170, 194,
165 -- it plateaus and oscillates rather than improving, best 194.4.

Final, 20 held-out episodes: **deterministic 170.90, stochastic 166.70**, against
the scripted heuristic's 277.2 and random-legal-play-without-REMOVE's 178.2.

**So the anchor fixed stability, not performance.** No collapse across 700k steps
where the unanchored run died by 100k -- that part is real and reproducible. But
the policy settles *below* a random baseline that merely refrains from destroying
its own lines, and far below its own teacher. At coefficient 10 that is partly by
construction: a strong anchor holds the policy near its reference, which prevents
collapse and improvement alike. The next question is whether a weaker or annealed
coefficient buys improvement without giving back the stability.

**Caveats.** Checkpoint evals use 8 episodes, whose 95% interval on this task is
roughly +/-46, so 185.5 -> 175.4 is noise and only the anchored-vs-unanchored gap
is resolvable. One seed. And the run has not yet passed its own 261.8 teacher or
convincingly cleared the 189.8 one-line control -- it is improving, which is new,
but has not yet won.

---

## E27 — The pointer head does not help the semantic lane, and a dead-path bug

**Hypothesis:** every learned policy plateaus at ~170-195 while the scripted
heuristic reaches 277. The heuristic's rule is a comparison over station-line
*pairs* -- nearest unserved station to nearest line end -- which a flat MLP over a
574-vector must rediscover per slot, and which the pointer head expresses
structurally. So clone the heuristic with the pointer architecture.

**A bug found on the way, worth more than the result.** The cloning loop called
`policy.action_net(latent_pi)` directly. The pointer policy computes its logits in
`_action_logits()` and **never uses `action_net` at inference**, so training
optimised a head the policy does not consult: 98.0% surface agreement on a dead
path, **0.2% agreement on the teacher's real decisions, and 0.0 deliveries**. The
clone now routes through the policy's own logit path.

**Measured**, after the fix, 6 held-out episodes:

| clone | real-decision agreement | deliveries |
| --- | --- | --- |
| MLP | 71.8% | **194.7** (max 271) |
| pointer | 73.0% | 158.0 (max 206) |

**Verdict: REFUTED.** The pointer head matches the MLP on fidelity to the teacher
and plays *worse*. Whatever separates 195 from 277 is not the flat head's
inability to compare pairs -- both architectures reproduce ~72% of the teacher's
decisions and both fall well short of it.

That sharpens the open question. The clone disagrees with its teacher on ~28% of
roughly fourteen decisions per episode, i.e. about four wrong choices, and those
four cost ~70 deliveries. The gap is not capacity or architecture; it is that a
handful of specific decisions carry almost all the value, and imitation at 72%
fidelity is not close enough. That argues for DAgger-style correction on the
states the clone actually visits, rather than more offline demonstrations of
states the teacher visits.

**Note on the surface metric.** 98% label agreement was reported three times in
this lane and meant nothing each time: the dataset is ~91% WAIT after
subsampling, so a policy that always waits scores 91%, and the dead-path clone
scored 98% while delivering zero. Only real-decision agreement is informative
here.

---

## E28 — DAgger raises fidelity and does not raise score

**Hypothesis:** the clone reproduces ~72% of the teacher's ~14 real decisions per
episode. More offline demonstrations cannot fix that, because they demonstrate
states the *teacher* reaches while the clone's mistakes take it elsewhere. DAgger
labels the states the *policy* visits, so the training distribution converges on
the policy's own.

**Measured**, 8 rounds x 10 episodes, aggregating to 10,314 labelled samples:

| round | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| agreement | 74.8% | 77.2% | 74.2% | 76.4% | 78.2% | 73.6% | **85.0%** | 73.6% |
| deliveries | 178 | 154 | **263** | 173 | 221 | 203 | 234 | 166 |

Agreement rose from the clone's 71.8% to a 77.3% final. **Score did not follow.**
Definitive evaluation, 16 held-out episodes:

| policy | mean | 95% CI |
| --- | --- | --- |
| scripted heuristic | ~262 | -- |
| **DAgger policy** | **175.31** | +/-37.23 |
| control: one line then wait | 174.81 | +/-38.22 |

**Verdict: REFUTED as a route to the teacher's score.** DAgger did exactly what it
promises -- it improved fidelity on the policy's own distribution -- and the
score is statistically identical to a control that builds one line and never acts
again. The assumed link from imitation fidelity to performance does not hold
here.

**What that implies.** Three architecturally different approaches now converge on
the same 170-195 band: cloning, cloning plus anchored PPO, and DAgger. The
scripted heuristic reaches 262 from the same action space and observation. So the
gap is not stability (the anchor fixed that), not architecture (the pointer head
was refuted in E27), and not distribution mismatch (DAgger addressed that
directly). What remains is that ~14 decisions per episode each carry enormous
value, their quality depends on a global comparison over all station-line pairs,
and a network that gets 3-4 of them wrong loses ~70 deliveries no matter how
closely it matches the teacher elsewhere. Imitation metrics average over
decisions; this game multiplies them.

---

## E29 -- the teacher was the ceiling, and it is ~40% below the action space

After DAgger (E28) showed fidelity rising without score rising, the remaining
suspect was the teacher itself. Testing it is cheap, because the game serialises
exactly: take a decision point, try each candidate, and roll it to the end of the
episode under the heuristic. Deterministic replay was verified first -- three
rollouts from one snapshot return the same value, and a snapshot rolled forward
800 decisions reproduces the live game's 19.0 deliveries exactly -- so these are
the real futures, not estimates.

Seed 9000, first four decision points:

| decision | the heuristic's choice | its value | best candidate found | value |
| --- | --- | --- | --- | --- |
| 0 | `CONNECT(0,2)` | 275 | `CONNECT(0,1)` | **380** |
| 1 | `PREPEND_LINE(0,1)` | 275 | `ASSIGN_LOCOMOTIVE(0,0)` | **398** |
| 2 | `ASSIGN_LOCOMOTIVE(0,0)` | 275 | `WAIT` | 287 |
| 3 | `ASSIGN_LOCOMOTIVE(0,0)` | 275 | tied | 275 |

**This explains the entire plateau.** At the very first decision of the game the
heuristic gives up ~105 deliveries, and at the second ~123. Every learned policy
in this repository was trained to imitate that. Cloning, anchored PPO, the
pointer head and DAgger were all competing to reproduce a player that is roughly
40% below what its own action space allows -- so the 170-195 band was never a
learning failure, it was faithful reproduction of a mediocre target.

It also retires the standing explanation from E28. The claim there was that ~14
decisions each carry enormous value and imitation averages where the game
multiplies. The multiplication is real, but the binding constraint is simpler and
was measured rather than inferred: **the labels were wrong**.

**Consequence.** Better labels are available without any new architecture, from
the simulator that already exists. The next step is to distil search's choices
rather than the heuristic's.

---

## E30 -- search beats the heuristic on every seed, and by a lot

Following E29's finding that the teacher was the ceiling, the question is
whether choosing by rollout actually converts into score across whole episodes
rather than at a single probed decision. Paired design: the same seed is played
twice, once by search and once by the heuristic, so layout luck cancels.

| seed | search | heuristic | gap | overrode | longest line |
| --- | --- | --- | --- | --- | --- |
| 9000 | **803** | 275 | **+528** | 9/32 | 11 |
| 9001 | 318 | 253 | +65 | 15/27 | 8 |
| 9002 | 265 | 174 | +91 | 8/19 | 8 |
| 9003 | 276 | 217 | +59 | 7/18 | 8 |
| 9004 | 393 | 391 | +2 | 6/22 | 8 |
| 9005 | 468 | 279 | +189 | 8/21 | 9 |
| 9006 | 474 | 425 | +49 | 10/24 | 9 |
| 9007 | 266 | 221 | +45 | 6/17 | 7 |

**search 407.88, heuristic 279.38, paired gap +128.50 +/-117.96, won 8/8.**

**CONFIRMED.** This is the first method in this repository to beat the scripted
heuristic, and it does so on every seed. The previous best of any kind was the
heuristic's ~262-279; the best *learned* policy was 194.7 and the best evaluated
policy 175.3, statistically tied with a control that builds one line and waits.

Three things worth noting in the detail.

**It overrides rarely.** Between 6 and 15 of roughly 17-32 search points, so most
of the heuristic's choices are already right and a minority of decisions carry
the entire 128-delivery gap. That is consistent with E28's observation that this
game multiplies decisions rather than averaging them -- and it is why imitation
metrics could look healthy at 77% agreement while the score did not move.

**It builds bigger networks.** Longest line rises from the heuristic's typical
7-8 stations to 8-11. Search finds that committing further to one line pays,
which is exactly the kind of long-horizon consequence a 150-step lookahead was
blind to and a myopic scripted rule cannot represent.

**The variance is enormous.** The +/-117.96 interval is wide because seed 9000
gained +528 while seed 9004 gained +2. The lower bound is still positive, but the
honest statement is that search wins consistently and by a wildly seed-dependent
amount, not that it reliably triples the score.

### E30 correction -- the +128.50 was an eight-seed artefact

A second, independent paired set of 15 seeds (20000-20026, search's own dataset
run against the heuristic on the identical boards) gives a very different effect
size:

```
paired gap +30.20 +/-16.48 over 15 seeds; search won 14, tied 1, lost 0
```

Per-seed gaps: +3, +73, +18, +32, +7, +76, +93, +3, +17, +79, +21, +0, +6, +8, +17.

**The direction survives and the magnitude does not.** Across all 23 paired seeds
measured so far, search beat the heuristic on 22, tied 1, and lost 0 -- it has
never once been worse, which is what rollout policy improvement predicts and is
the claim actually worth making. But the headline +128.50 was inflated by seed
9000's +528, one outlier in a sample of eight. Excluding it, the first set's mean
gap is +71.4; the second set's is +30.20. The typical gain is a few tens of
deliveries, with occasional large wins on boards where committing to one long
line pays off dramatically.

This is a repeat of a mistake already recorded in `docs/learning/lessons.md`:
*do not report an effect size from a handful of trials when the outcome is
bimodal; the mean is mostly a count of lucky seeds.* The rule was written, read
at session start, and violated anyway. What makes it easy to miss is that the
paired 95% interval on eight seeds (+/-117.96) did exclude zero, so the result
looked statistically clean -- pairing correctly established *that* search wins
while saying nothing reliable about *by how much*.

**Revised standing claim:** search beats the heuristic reliably and by roughly
30-70 deliveries on a typical board, not by the ~130 first reported.

---

## E31 -- distillation memorises; held-out agreement is flat at ~52%

Search's labels are better than the heuristic's (E29, E30), so the next step was
distilling them into a network that plays at that standard without searching.
28 search episodes produced 4,815 labels, of which 495 are real decisions.

Training agreement climbed convincingly:

| epochs | 50 | 100 | 150 | 200 | 250 |
| --- | --- | --- | --- | --- | --- |
| **train** real-decision | 55.2% | 69.0% | 83.7% | 90.8% | **92.9%** |
| **held-out** real-decision | 52.0% | 49.6% | 49.6% | 53.5% | **52.8%** |

**REFUTED, and the training number is worthless.** Held-out agreement is flat
across the entire run -- it is no better at epoch 250 than at epoch 50 -- while
training agreement nearly doubles. Every one of those 190 extra epochs bought
memorisation of specific boards and nothing that transfers.

Without the split this would have been reported as a success: 92.7% agreement
with a teacher that scores 306.75 reads like a solved problem.

**The split has to be by episode.** Samples from one episode share a board, a
layout and a difficulty ramp, so a random split over the 4,815 samples puts
near-duplicate states on both sides and would have shown a healthy validation
curve while measuring nothing. The dataset had no episode ids at all, which is
why this was not checkable when the first model was trained; they are now
recorded, and the existing dataset was backfilled from the run log (4,815 labels
across 28 episodes, an exact match, so the mapping is reconstructed rather than
guessed).

**What this says about the bottleneck.** ~52% held-out agreement on real
decisions means the policy reproduces about half of search's choices on an unseen
board. 21 training episodes carry roughly 370 real decisions -- for a 364-way
action space over a game whose right answer depends on a global comparison across
all station-line pairs, that is very little. The constraint has moved from label
*quality* (fixed by search) to label *quantity*.

**Consequence.** Two routes, and they are complementary. Generate far more search
episodes, which is expensive; and use the evaluations already being thrown away
-- each search point scores one full-episode rollout per candidate and only the
argmax was kept, so five sixths of the most expensive computation here was
discarded. Recording all of them turns every search point into a preference
ordering rather than a single label, at no extra simulation cost.

---

## E32 -- better labels do not move the learned score, and E29 was incomplete

The distilled policy from E31, evaluated on 20 held-out seeds against the full
control set:

| player | mean | 95% CI |
| --- | --- | --- |
| control: random | 0.00 | -- |
| control: wait | 0.00 | -- |
| control: one line then wait | 174.75 | +/-30.40 |
| **control: scripted heuristic** | **267.35** | +/-33.28 |
| distilled, deterministic | 179.85 | +/-23.12 |
| distilled, stochastic | 193.20 | +/-32.33 |

**Paired against the heuristic: -74.2 +/-24.1, won 1 of 20.**

**REFUTED, and it refutes part of E29 with it.** The distilled policy scores
193.20. Cloning the *heuristic* scored 194.7. Those are the same number. Search
labels come from a player scoring 306.75 where the heuristic scores 248.43, and
distilling the better teacher produced no improvement whatsoever.

E29 concluded "the labels were wrong" and called that the whole explanation for
the 170-195 plateau. The first half stands: the heuristic really is ~40% below
its own action space, and search really does beat it on 27 of 28 paired seeds.
The second half does not. Fixing the labels was necessary and is not sufficient,
because the learner cannot absorb the better labels from this much data --
held-out agreement sits at 52% (E31) and 52% agreement scores about 190 whoever
the teacher is.

**So there are two separate ceilings, and they were being conflated.**

* The *heuristic* ceiling, ~250-280, caused by a myopic rule. Search breaks it.
* The *imitation* ceiling, ~190, caused by a 364-way decision that depends on a
  global comparison across all station-line pairs being learned from a few
  hundred real decisions. Neither a better teacher nor a better architecture has
  moved it: cloning, anchored PPO, a pointer head, DAgger, and now search
  distillation all land in 158-195.

**What actually distinguishes the two.** Search does not *predict* which action
is good, it *measures* it, and it re-measures at every decision point. That is
not a representational advantage a network can be handed by better labels -- it
is a different amount of computation per decision. Expecting one forward pass to
reproduce hundreds of full-episode simulations was the unexamined assumption.

**Consequence.** Two routes remain, and the first is already in flight.
Quantity: 90 more search episodes, roughly quadrupling the real-decision count.
Density: each search point scores one full-episode rollout per candidate and only
the argmax was kept, so recording all of them turns every decision point into a
preference ordering over its shortlist at no extra simulation cost -- roughly six
times the supervision from the same compute.

If neither moves held-out agreement well above 52%, the honest conclusion is that
this task wants search at inference time rather than a policy that has memorised
one, and the deliverable is the search player.

---

## E33 -- the critic does not generalise either, so search cannot be shortcut yet

Search costs tens of minutes per episode because every candidate is rolled to the
end of the game. The standard fix is to stop early and add V(s), which is an
order-of-magnitude saving and converts directly into more episodes -- and more
episodes is exactly what E31 and E32 identified as the constraint. That requires
a critic that works on boards it never trained on.

Distilled critic, evaluated on the same 7 held-out episodes (1,164 states):

| | |
| --- | --- |
| actual return-to-go | mean 34.85, sd 9.90 |
| predicted | mean 34.26, sd 12.80 |
| mean absolute error | 8.81 |
| correlation | **+0.418** |
| R^2 against predicting the mean | **-0.594** |

**REFUTED for now.** A negative R^2 means the critic is worse than a constant:
predicting 34.85 for every state would beat it. It has learned the average and
then added noise around it, with predicted spread (12.80) wider than the real
spread (9.90) -- overconfident in exactly the way that makes a leaf evaluation
dangerous, since search would act on differences that are not there.

**One caveat against writing the route off.** Search does not need calibrated
values, only correct *ranking* among candidates, and the correlation is positive
at +0.418. So the failure is not total. But +0.418 is far too weak to trust for
choosing between actions whose true values differ by a few deliveries, which is
what most decision points look like.

**Where this leaves things.** Both halves of the distilled network fail to
generalise from 21 training episodes -- the policy at 52% held-out agreement
(E31), the critic below a constant baseline here. That is one consistent story
rather than two failures, and it points at the same cause: too few episodes. The
90-episode run in flight roughly quadruples the real-decision count, and this
measurement should be repeated against it before the AlphaZero-style loop
(policy proposes candidates, critic evaluates leaves, distil, repeat) is
attempted, because every stage of that loop depends on the critic being better
than a constant.

---

## E34 -- search was picking lucky futures, not good actions

Search rolls each candidate to the end of the episode and takes the best. Those
rollouts are deterministic given the serialised state, and the serialised state
*includes the RNG*. So each candidate is scored against exactly one future -- the
one that will actually happen -- and search knows which passengers and stations
are coming. The 574-float observation encodes none of that.

The test holds the board fixed and varies only the RNG, at decision 0 of seed
9000:

| candidate | future 0 | future 1 | future 2 | future 3 | **mean** |
| --- | --- | --- | --- | --- | --- |
| `CONNECT(0,2)` *(the heuristic's pick)* | **291** | **292** | 274 | 285 | 285.5 |
| `CONNECT(0,1)` | 266 | 287 | **328** | **302** | **295.8** |
| `CONNECT(1,2)` | 275 | 275 | 289 | 275 | 278.5 |

**The best action changes with the future -- 2 of 4 each way.** And the headline
number from E29 does not survive. Measured against the one real future,
`CONNECT(0,2)` scored 275 and `CONNECT(0,1)` scored 380, a gap of 105 that was
the entire basis for "the teacher is ~40% below its own action space". **In
expectation the gap is about 10.** The other ~95 was luck.

**This is the winner's curse, and it was designed in.** A single rollout is a
one-sample estimate of a candidate's value. Taking the max over noisy one-sample
estimates selects for the candidate with the luckiest sample, not the best action,
and the selected estimate is biased upward. The numbers show the noise is the
same size as the signal: within any one future the candidates differ by 17-54
deliveries, while one *fixed* candidate varies by up to 62 across futures
(`CONNECT(0,1)`: 266 to 328).

**The error of principle.** Monte Carlo rollout in a stochastic environment
averages each candidate over sampled futures. What is implemented here is the
K=1 case, which is only correct when the environment is deterministic. This game
is not -- passenger and station spawns are random -- and the *simulator* being
reproducible was mistaken for the *game* being deterministic. E30's determinism
and fidelity checks were both correct and both irrelevant to this: they proved
the rollout faithfully reproduces one future, and said nothing about whether one
future is enough.

**What it explains.** Three results that looked unrelated are one result.

* Search's paired +58.32 over the heuristic is partly foreknowledge, not skill.
  It genuinely delivers those passengers in that game, but no reactive policy can
  reproduce it, because the information it used is not in the observation.
* Distillation stalls at 52% held-out agreement (E31) because a fraction of the
  labels are unlearnable by construction -- identical observations, different
  correct answers.
* The distilled policy scores 193.20, indistinguishable from cloning the
  heuristic at 194.7 (E32), because once the luck is averaged out the learnable
  part of search's policy is not far from the heuristic's.

**Consequence.** The fix is the standard one: average each candidate over K
independent futures, which estimates E[return | state, action]. That quantity is
a function of the observation, so it is learnable in principle, and it removes
the selection bias. It costs K times more rollouts, and it will almost certainly
shrink search's margin over the heuristic -- the honest margin is the one worth
having. The 90-episode generation run was stopped at 25 episodes; its labels
carry this defect.

---

## E35 -- the network does not beat random at the decisions it is given

Most steps in this game are not decisions, so the natural design is to script the
forced ones and learn only the rest. The gate used is the same one search uses
and is computable from the observation alone: a structural action is legal, and
either the heuristic wants to act or the set of available capabilities changed.
It hands the policy about 15.4 decisions per game.

The arm that matters is `ablated` -- the identical script making a RANDOM legal
choice at exactly the same handover points. If the hybrid does not clearly beat
it, the script is playing the game and the network is decoration.

16 seeds, every player on the same boards:

| player | mean | 95% CI |
| --- | --- | --- |
| scripted heuristic | **251.69** | +/-64.50 |
| policy alone | 185.06 | +/-59.19 |
| hybrid (script + policy at decision points) | 167.81 | +/-49.01 |
| ablated (script + RANDOM at the same points) | 116.44 | +/-42.32 |

| paired comparison | gap | won |
| --- | --- | --- |
| hybrid vs ablated | **+51.38 +/-58.76** | 10/16 |
| hybrid vs heuristic | -83.88 +/-24.39 | **0/16** |
| policy alone vs heuristic | -66.62 +/-24.36 | 1/16 |

**REFUTED.** The hybrid does not clearly beat random choice -- the interval
includes zero and it wins only 10 of 16. Whatever the distilled policy has
learned, it is not reliably better than picking a legal action at random on the
decisions that were judged worth learning.

**Two separate failures, and the second was not anticipated.**

*The network is weak.* Expected, given E31-E34: held-out agreement of 52%,
labels partly unlearnable, a critic below a constant baseline.

*Splicing costs more than either component.* The hybrid at 167.81 is worse than
**both** pure players -- the policy alone reaches 185.06 and the heuristic
251.69. That is not explained by a weak network, because a weak network mixed
with a strong script should land between them. It is distribution shift: the
policy was trained on states search visits, and the heuristic drives the game
into states it never saw, so it is asked for decisions on boards outside its
training distribution. The composition is worse than its parts.

**Consequence.** The hybrid decomposition is not merely unhelpful here, it is
actively harmful, and "learn only what matters, script the rest" cannot be
adopted without training the learned component *on the state distribution the
script produces* -- which is the DAgger loop already run in E28 with a null
result.

Incidentally, the `ablated` arm paid for itself immediately by crashing the game.
Random-but-legal play at decision points reached a state where a passenger held a
travel plan naming a station that had spawned after the routing graph was built,
raising `KeyError` in `route_planner` (seed 50007, step 8587). The scripted
heuristic never explores oddly enough to reach it. Fixed, with a test written
from the reproduction.

---

## E36 -- with foreknowledge removed, search does not beat the heuristic

E34 showed that scoring each candidate against a single rollout measures it
against the one future that actually happens, because the serialised state
carries the RNG. The fix is to average each candidate over independently
resampled futures, using common random numbers so the comparison isolates the
action. This is that measurement, at scale.

20 paired seeds, 3 candidates averaged over 3 sampled futures, rollouts to
episode end:

```
search:     mean 274.90   max 405
heuristic:  mean 267.35   max 425
paired gap: +7.55 +/-17.70   (search won 11/20, lost 9)
```

Seed by seed against the *same* seeds measured one-sample:

| seed | 9000 | 9001 | 9002 | 9003 | 9004 | 9005 | 9006 | 9007 | mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| one-sample | **+528** | +65 | +91 | +59 | +2 | +189 | +49 | +45 | **+128.5** |
| honest | +17 | -51 | +4 | +57 | -17 | +45 | -37 | +57 | **+9.4** |

**REFUTED, and it retires E29 and E30 with it.** Seed 9000 falls from +528 to
+17. The interval spans zero, and search now loses on 9 of 20 seeds rather than
0 of 28. The scripted heuristic is not "40% below its own action space" (E29);
that number was the winner's curse. Search is not worth +58.32 (E30); that was
the same artefact measured on more seeds, which is why more seeds did not
expose it -- the bias is in every sample, so averaging samples cannot remove it.

**One honest caveat in the other direction.** Three futures is still a small
sample, and taking a max over three noisy means retains some selection bias. So
+7.55 is an upper bound on the true margin rather than an estimate of it. The
defensible claim is that search is *not worse* than its default policy -- which
is what rollout policy improvement guarantees -- and that any advantage beyond
that is too small to measure at this budget.

**What this kills.** The entire search-as-better-teacher programme. Search was
adopted (E29-E31) because it appeared to reach decisions the heuristic missed,
which would make its choices better training labels. They are not better labels;
they are the heuristic's labels plus noise. That explains, without any further
theory, why distilling them produced 193.20 against cloning-the-heuristic's 194.7
(E32), and why held-out agreement stalled at 52% (E31) -- a fraction of those
labels were coin flips.

**What survives.** The measurement apparatus is sound and was worth building: the
exact serialise/restore round-trip, the fidelity gate against the live game, the
sampled-future averaging, and the paired protocol. They are what made this
falsifiable.

**Where this leaves the goal.** No learned policy beats the heuristic, and now no
*planner* does either. The heuristic at ~267 is a stronger baseline than it
looked, and beating it needs something structurally different from
one-step-lookahead-over-itself -- a better default policy inside the rollout, a
deeper search, or a genuinely different action representation.

---

## E37 -- the labels were clairvoyant, and nothing here beats a blind policy

A nine-lane review (four claims verified empirically, each attacked by an
independent lane, then synthesised) found two defects that neither the claims
nor I had looked for. Both are larger than anything the claims were about.

### The label generator scored against the future that happens

`scripts/search_dataset.py` passed the **unmodified** serialized document to
every rollout. The RNG travels inside that document, so each candidate was
measured against the one future that actually occurs. Verified directly rather
than accepted:

* `search_dataset.py` scored `_rollout(env, document, ...)` with no reseeding.
* `search_policy.play` had `futures: int = 0` as its **function** default while
  the CLI defaulted to 4, so any programmatic caller silently got the oracle.
* `output/semantic/search.log` -- the run behind "the first method here to beat
  the heuristic" -- has no futures line in its header. It ran clairvoyant.

The consequence is not "noisy labels". The label is a function of
(state, realized future); the observation carries state alone. **Every label in
`output/semantic/search-data*.npz` is unlearnable in principle.** No
architecture, no quantity of data, no soft target and no DAgger round could have
fitted them, because the information that produced them is not in the input and
never will be.

That retires more than the labels. **Every architecture comparison run through
that pipeline is void** -- the pointer head's 158.0 was never a test of the
pointer head.

### Nothing learned here beats a network that cannot see

The review's blind control: a network fed a constant vector of ones, sampling
under the legality mask.

| player | mean | 95% CI |
| --- | --- | --- |
| distilled policy, stochastic | 203.71 | +/-35.77 |
| **blind net + legality mask** | **203.96** | +/-44.70 |

Paired difference -0.25 over 24 seeds, 10/24 wins. And `mask_only` vs `full_obs`
agreement is +0.47pp at n=495 -- **the 574-float observation carries nothing
usable through this network.**

So the "158-195 imitation band" that five approaches converged on is not a
property of imitation, of architecture, or of teacher quality. **It is the score
of mask-restricted prior sampling.** The action mask alone, sampled from, plays
at ~204.

Two direct training runs confirm it from the other side. Online PPO from
scratch, 11,000,088 steps (~1,300 episodes, against the 146 previously called a
plateau) reached **175.4**, still below the blind control. A warm-started
KL-anchored run peaked at 207.0 at 6M steps and oscillated to 152.6 by 8M. Both
stopped: they had answered.

### The instrument was wrong throughout

`longest_line` alone explains **R^2 = 0.892** of delivery variance, and
`corr(steps, deliveries) = 0.973`. Deliveries is a 4-5 rung ordinal ladder with
roughly 90-delivery spacing wearing a continuous costume, and per-episode noise
is about one whole rung. **Any effect below ~45 deliveries is sub-rung and needs
n in the hundreds.** That is why every dispute in this project has been a power
dispute -- including the three effect sizes I quoted from small samples today.

Worse, the controls were wrong. `oneline` scores 189.75, *below* the blind
sampler at 204, and `random` scores 0 only because uniform-over-legal
self-destructs. **Every historical "beats the baseline" claim in this file was
measured against a broken null.**

### Standing implications

* Distilling `search-data*.npz`: permanently dead. Keep the datasets as a
  cautionary fixture.
* The imitation branch's ceiling arithmetic: honest search is heuristic + ~10
  (E36), so a perfect distillation of a perfect honest teacher tops out near 275
  against a free scripted heuristic at ~262. Best case for the whole branch is
  about +13 deliveries.
* The primary outcome should be `longest_line` or a survival model on it, with
  deliveries secondary; the null should be masked-prior sampling at ~204; and
  every reported null needs its minimum detectable effect stated beside it.

---

## E38 -- 98% agreement with an honest teacher still loses 45 deliveries

Every clone evaluated in this project was trained on the clairvoyant search
labels (E37), which are unlearnable by construction. That left the obvious
question never actually asked: can a network reproduce the SCRIPTED HEURISTIC --
free, deterministic, honest labels -- well enough to matter?

60 episodes of heuristic play, 60 epochs, the same MLP, evaluated paired against
the blind control on 40 shared seeds with per-seed torch seeding:

| player | deliveries | longest_line |
| --- | --- | --- |
| blind net (constant input) | 186.32 +/-26.60 | 6.85 |
| **clone of the heuristic** | **203.70 +/-26.73** | 7.08 |
| the heuristic itself | 248.78 +/-30.39 | 7.50 |

| paired | gap | won | MDE(80%) |
| --- | --- | --- | --- |
| clone vs blind | +17.38 +/-21.98 | 24/40 | 31.4 |
| heuristic vs clone | **+45.08 +/-19.40** | **32/40** | 27.7 |

**The clone fits its teacher and still cannot play like it.** Training agreement
reaches **98.1%**, on labels that are a deterministic function of the state, with
no hidden information anywhere -- and the result is 45 deliveries worse than the
thing it copied, landing in the same band as a network that cannot see the board.

**This is the cleanest statement of the real problem, and it is not the one this
project has been chasing.** It is not label quality: these labels are perfect. It
is not architecture: the same net reaches 98% agreement. It is not data volume:
the residual is 2% of decisions.

**Roughly 2% of decisions carry ~18% of the score.** The heuristic acts about 14
times in 8,000 steps, so a 2% error rate over the decisions that matter is a
handful of wrong choices per episode, and each one forecloses a line that would
have compounded for thousands of steps. Imitation metrics average over decisions;
this game multiplies them. E28 proposed exactly this and could never demonstrate
it, because every measurement since was made through clairvoyant labels.

**What it implies for anything trained by imitation here.** The ceiling is not
the teacher's score. It is the teacher's score discounted by however much the
last few percent of decisions are worth -- and here that discount is 18%. A
policy cloned from a 248-delivery teacher lands at 204. Getting to the teacher
requires being right on the decisions that compound, not on more of them.

**Settled at n=180 (MDE 16.1): the clone does NOT beat the blind control.**

```
blind      179.42 +/-11.18      longest_line 6.74
hclone     187.08 +/-13.31      longest_line 6.87
heuristic  267.47 +/-15.31      longest_line 7.71

clone vs blind        +7.66 +/-11.29,  won  95/180   (a coin flip)
clone vs blind        +0.13 +/-0.13,   won  58/180   on longest_line
heuristic vs clone   +80.39 +/-13.06,  won 155/180
```

### The number that explains it, and why 98.1% was the wrong one

98.1% was *training* agreement on a WAIT-dominated mixture. Measured on 12 unseen
seeds, following the teacher so both are always judged on the same board:

| decisions | agreement | count |
| --- | --- | --- |
| all | 99.9% | 89,621 of 89,667 |
| **real (non-WAIT)** | **72.8%** | **123 of 169** |

**The clone gets about four of its fourteen real decisions per episode wrong, and
that costs 80 deliveries.** Every headline agreement figure in this file --
including the ones used to justify DAgger and the pointer head -- was an
aggregate over a population that is 99.8% forced WAIT, and therefore said nothing
about the decisions that carry the score.

**The rule for anything measured here: quote agreement on decisions the teacher
did not spend on WAIT, or do not quote agreement.**

---

## E39 -- the 75% decision ceiling is representational, not data-limited

E38 established that a clone of the scripted heuristic gets 72.8% of real
decisions right on unseen boards, and that the resulting 80-delivery shortfall
puts it level with a network that cannot see the board. The obvious remedy is
more data -- and unlike the search labels, heuristic labels are free.

Held-out real-decision agreement, identical 12 evaluation seeds each time,
teacher followed so both are judged on the same board:

| training episodes | 40 | 120 | 360 |
| --- | --- | --- | --- |
| agreement | 76.3% | 76.9% | **74.6%** |

**Flat. Nine times the data changes nothing.** The ceiling is not the quantity of
labels, and this closes the whole family of remedies that assume it is: more
episodes, DAgger rounds, soft targets, aggregation. All of them were sold on the
premise that the learner was starved. It is not.

**Where the difficulty actually sits.** The heuristic's rule is an ARGMIN over
station-line pairs -- graft the unserved station onto the nearer end of a line,
or connect the closest unserved pair. The distances that rule needs are in the
observation; they were added specifically for it (`REACH_PER_PAIR`, the per-end
distances). So the information is present and the network still cannot use it.

What the network is being asked to do is not function approximation, it is
SELECTION: identify which of ~80 station-line pairs minimises a distance, then
emit the single action index that names that pair. A flat MLP over a 574-vector
has to learn that correspondence separately for every slot, and slot `i` holds a
different station on every board -- so nothing it learns about slot 3 transfers
to the board where the same station sits in slot 7.

**Consequence.** Only two things can move this number, and neither is more data:
an architecture that scores actions from the entities they name, or an
observation in which the comparison is already made. The pointer head
(`src/rl/semantic_nets.py`) is the first; its only previous trials were an RL run
and a distillation on clairvoyant labels, so it has never been tested against
honest labels on the metric that matters.

---

## E40 -- imitation fidelity is uncorrelated with score; the gap is selection

Four independent things a clone can copy were measured against what they buy.

**Decision agreement does not predict score.** Held-out real-decision agreement
against the heuristic, and the score each policy actually reaches:

| policy | held-out agreement | deliveries |
| --- | --- | --- |
| blind net (constant input) | ~0% | 183.2 |
| MLP clone | 72.8% | 187.1 |
| pointer clone | ~81% | 184.7 |
| the heuristic | 100% | 260.4 |

Going from 0% to 81% agreement is worth **under 2 deliveries**. The curve is flat
until it is not: only the teacher's own play reaches the teacher's score. Every
agreement figure this project has reported as progress -- DAgger's 71.8% -> 77.3%
among them -- was measuring a quantity with no demonstrated relationship to the
outcome.

**Action frequency and action mix do not predict score either.** Self-play over
12 seeds:

| policy | deliveries | actions/episode | dominant kinds |
| --- | --- | --- | --- |
| heuristic | 295.8 | 14.3 | ASSIGN 28%, EXTEND 23%, PREPEND 19% |
| MLP clone | 199.7 | 25.3 | EXTEND 35%, ASSIGN 16%, **REMOVE 10%** |
| blind | 193.2 | 29.8 | PREPEND 46%, ASSIGN 17% |
| pointer clone | **175.8** | **13.7** | ASSIGN 32%, PREPEND 21%, no REMOVE |

The pointer clone matches the teacher's action rate (13.7 against 14.3) and its
action mix, and scores **the worst of the four**. Copying how often and what kind
is worth nothing.

**Removing a demonstrably wrong behaviour buys nothing.** The MLP clone spends
10% of its actions on REMOVE_LINE; the heuristic uses it 0 times in 114 actions.
Banning it via `remove_min_age`, applied to every arm on 60 paired seeds:

```
heuristic   254.4 -> 254.4   +0.0 +/-0.0   won  0/60
hclone      167.8 -> 170.5   +2.7 +/-5.4   won 16/60
pointer     184.5 -> 185.0   +0.5 +/-4.3   won  1/60
blind       177.6 -> 182.2   +4.5 +/-5.5   won 13/60
```

That also settles a contested review claim that "65% of the hybrid effect is
banning line removal" -- measured directly, it is +2.7 +/-5.4.

**More data buys nothing** (E39: 40/120/360 episodes give 76.3/76.9/74.6%).
**A permutation-correct architecture buys nothing** (the pointer head raised
agreement ~8pp and moved the score by +1.45 +/-17.23). **Direct RL buys nothing**
(11M steps from scratch reached 175.4, below the blind control).

### What is left

By elimination, the entire 75-delivery gap lives in **which station pair is
chosen**, and nothing tried touches it. The heuristic's rule is an argmin over
station-line distances; those distances are in the observation; no learner has
converted them into the right selection.

Two things follow, and neither has been tried.

* **Make the comparison explicit in the observation.** Instead of supplying the
  distances and hoping a network discovers the argmin, supply the ranking -- e.g.
  a flag per action for "this names the nearest unserved station to this line's
  nearer end". If the score moves, selection was the bottleneck and the finding
  is precise. If it does not, the bottleneck is not selection either, and that
  would be genuinely surprising.
* **Optimise the score directly at the decision points, not the labels.** Every
  method tried optimises agreement with a teacher, and agreement has now been
  shown to be uncorrelated with score over the 0-81% range. That is an argument
  for a method whose objective is the outcome.

---

## E41 -- handing the network the argmin does not help either

E40 concluded by elimination that the whole gap is WHICH station pair gets
chosen, and proposed the direct remedy: stop supplying the distances and hoping a
network discovers the argmin, and supply the ranking itself.

Implemented as 80 new observation features (`RANK_FEATURES`), one per
station-line pair, holding 1.0 for the nearest UNSERVED station to that line's
nearer end and falling off with rank. Verified load-bearing before training:
across a full episode, **5 of 5** of the heuristic's graft targets were the
station the feature marks as nearest. The observation grew 574 -> 654 floats.

Held-out real-decision agreement rose, and by more than any architecture change
managed: **73.8% -> 83.3%** at its best readout, against the plain
observation's 72.8-76.9% ceiling and the pointer head's ~81%.

The score did not follow.

| player | deliveries | longest_line |
| --- | --- | --- |
| clone with ranks | 189.25 +/-18.83 | 6.88 |
| the heuristic | 263.01 +/-21.15 | 7.64 |

**heuristic beats it +73.76 +/-15.16, winning 82 of 100.** Against the earlier
clones at 185-187, supplying the argmin is worth about two deliveries.

**REFUTED.** This was the strongest remaining hypothesis and it fails the same
way everything else has: agreement moves, score does not. It is now the fourth
independent confirmation of E40's central finding -- across architectures
(MLP/pointer), data volume (9x), action-space edits (REMOVE ban) and now feature
engineering, **held-out agreement with the teacher has never once predicted the
score.**

**What that rules out.** The gap is not the argmin, because the argmin was handed
over and nothing happened. Whatever the heuristic is doing that a copy of it
cannot do, it is not "identify the nearest unserved station" -- a clone can now
do that at 83% and still plays 74 deliveries worse.

**What is left, stated precisely.** The heuristic's advantage survives only in
the full trajectory it produces. A policy that agrees with it on 83% of decisions
lands on a different board within a few decisions, and from there the teacher's
remaining choices are answers to questions it is no longer being asked. That is
compounding divergence, and no imitation objective addresses it -- which is
consistent with DAgger, whose entire purpose is that problem, also having failed
here (E28).

---

## E42 -- an episode is 21 decisions, and it has always been 7,600

**Hypothesis:** the semantic lane's difficulty is partly a presentation artefact.
`SemanticMetroEnv` asks for an action every `TICKS_PER_DECISION`, so an episode
runs about 7,600 decisions -- and the scripted heuristic acts on 15 of them. If
over 99.8% of every rollout is spent emitting WAIT, the policy gradient for the
handful of real choices is diluted about 500:1 and a delivery's credit has to
travel back across thousands of no-ops.

**Measured first, before designing anything** -- the heuristic over 5 seeds:

| quantity | mean |
| --- | --- |
| decisions per episode | 7,989 |
| actions taken | 14.8 |
| action-mask changes | 17.2 |
| observation floats CONSTANT for the whole episode | 572.8 of 654 |
| observation floats ALWAYS ZERO | 560.8 of 654 |

That last row also settles the "most suspicious open fact" the previous session
left. The 590 constant floats are not mysterious: **560 of them are permanently
zero**, because the observation is fixed-slot for 20 stations and 4 lines while
a real episode reaches 7-10 stations and 1-3 lines. It is padding, not signal
loss.

### The gate, and the two wrong versions before it

`src/rl/event_gate.py` fast-forwards the simulation -- still WAITing, still
accruing deliveries -- until the action mask changes, then re-queries.

**Version 1 gated on mask changes alone and scored 0 deliveries against 525.**
The heuristic's follow-up moves (graft the second station, then crew the line)
are *already legal* when the first is taken, so the mask does not move; the gate
sat idle for the whole backstop and the run died at the 40-second overcrowding
deadline. Acting changes what to do next without changing what is *possible*.
The gate must therefore be asymmetric: fast-forward only after WAIT, re-query
immediately after anything else.

**Version 2 read its baseline mask after the WAIT step had executed.** A WAIT
advances six ticks before the fast-forward begins, so a station spawning inside
those ticks became the baseline and the gate slept a full backstop through the
very change it exists to wake for. This survived an n=8 check and was caught
only by comparing **(decision, action) pairs per seed at n=200**:

```
seed 90048: plain acts at decision  411, gated at  611   (same action, 203)
seed 90072: plain acts at decision 5217, gated at 5417   (same action, 286)
seed 90110: plain acts at decision 9248, gated at 9448   (same action, 288)
seed 90145: plain acts at decision 3033, gated at 3233   (same action, 199)
seed 90182: plain acts at decision 6869, gated at 7069   (same action, 207)
```

Every divergence is the correct action delayed by *exactly* `wait_backstop`.
Five seeds in 200, and the means were **249.29 against 249.50** -- an aggregate
that would never have shown it.

### The result

With the baseline captured before the step, on 200 independent seeds:

| | queries/episode | decisions/episode | mean | per-seed mismatches |
| --- | --- | --- | --- | --- |
| plain | 6,859.6 | 6,859.6 | 249.29 | -- |
| gated | **50.9** | 6,862.6 | 249.50 | **0 of 200** |

Deliveries, decision counts and the entire action sequence are identical. The
horizon a learner sees falls **135x**, and with the backstop disabled entirely
it is 365x at 20.6 queries.

**CONFIRMED.** The gate is free for the heuristic. It restricts *when* a policy
may act, which is a restriction on the policy class -- like frame-skip -- so it
cannot inflate a score, and the bar it is measured against provably scores the
same either way.

### Why this changes what is affordable

Prior RL runs on this lane burned ~7,600 policy steps per episode. 4,000
episodes cost 30M steps and about 41 hours. Under the gate the same 4,000
episodes are 200,000 policy steps. The simulation cost is unchanged -- the game
still runs every tick -- so training becomes simulation-bound rather than
policy-bound, which also means the 1.55x sim speedup from the previous session
now converts into training throughput where before it did not.

---

## E43 -- the rest of the dead knobs

`--eval-episodes` was found by accident, so the whole knob surface was audited:
every argparse flag plus constructor keywords and module constants, each traced
from its parse site into its consumer *with the callee's signature opened*, and
each suspect handed to an independent lane instructed to refute it. **18
suspected, 13 confirmed, 5 refuted.**

The five refutations matter as much as the confirmations -- `--anchor-coef`,
`--max-decisions`, `distill_search --gamma`, `--fps`, and `--spatial-pointer`'s
manifest consumer are all live, and two of them were only shown live by running
the real script end to end.

**CRITICAL -- `--learning-rate` was dead on every `--resume`.** SB3's `load()`
builds `lr_schedule` from the checkpoint's saved rate, and
`_update_learning_rate` reads the schedule and never the attribute the script
assigned afterwards. So every warm start in this project's history trained at a
constant 3e-4 inherited from the clone, whatever the flag said. This is
checkable after the fact rather than by reproduction, because SB3 pickles the
live schedule into the save: **all eight resumed artifacts on disk carry
`Constant(0.0003)` beside an attribute of 5e-5 or 1e-4**, and all twelve
from-scratch checkpoints are clean.

That gives **E26 a live alternative explanation**. The KL anchor was introduced
because an unanchored warm start decayed from 146.5 to 46.4; `train_semantic.py`
itself blames a *constant* 3e-4 for exactly that failure mode and installs a
decaying schedule as the remedy -- into the from-scratch branch only. The
collapse the anchor was built to cure was measured under the rate the code's own
comment says causes collapses. E26's conclusion is not refuted; it is
**unfounded as measured**.

**MAJOR -- `PointerExtractor` never stepped over the rank block.** The
observation is `stations | paths | reach | RANK | resources`; the extractor
advanced its cursor past reach and read `resources` immediately, landing 80
floats early on the tail of the rank block, which is all zeros in ordinary play.
It was structurally blind to locomotives, carriages, credits and the distance to
the next unlock, and trained end to end without error. Measured on a real
observation: true resource offset 640, read at 560, and the slice it fed the
network was `[0.]*14` against a real block of
`[0.565 0 0 0.428 0 0.5 0.3 0.5 0.25 0.3 0 0 0 0.974]`.

Blast radius, checked rather than assumed: every checkpoint on disk carries
`policy_kwargs {}` and the stock policy, so E41 and the rank-rl runs were the
MLP arm and are unaffected. **E27's pointer comparison was run under it.**

**MAJOR, four more.** `--arch` and `--spatial-pointer` were silently ignored on
a warm start, so a run could record an architecture it was not using.
`--device cuda:N` slipped past a membership test against `("auto", "cuda")` and
got the silent CPU fallback -- the ~100x slowdown -- on the one spelling anyone
with two cards would use. `blind_control` fell through to the Laplace uniform
when its gitignored dataset was absent, quietly swapping the blind null for the
random control. `record_semantic --player search` still called `_rollout` on the
unmodified document after `search_policy` was fixed, so **every playthrough it
has produced was the clairvoyant oracle**, including `search-9000.gif` and the
docstring claims read off it.

**MINOR.** `SemanticMetroEnv(seed=42)` was accepted and dropped -- a fresh
random board on every reset, no `TypeError`, no warning.
`estimate_inference_macs` took a `render_profile` that moved the convolutions
and silently not the action head, written as the literals `8 + 192 + 108`. The
dead `--checkpoint-episodes` is removed rather than left accepted-and-ignored.

All thirteen are pinned by `test/test_instrument_knobs.py` at the level of
observable consequence -- what the optimiser reads, what the network is fed,
what the environment plays -- because every one of them type-checked, ran clean,
and produced entirely plausible logs.

---
## E44 -- the bar builds one line, and that is the right answer

E40 concluded by elimination that the whole 75-delivery gap lives in **which
station pair gets chosen**. Nobody had counted how many pairs there are.

**Measured**, every decision the heuristic makes over 10 episodes, with the size
of the choice set the rule was actually choosing from:

| rule | decisions | options | fraction with >1 |
| --- | --- | --- | --- |
| WAIT | 374 | 12.1 legal alternatives | 54.5% |
| ASSIGN_LOCOMOTIVE | 40 | **always exactly 1** | **0%** |
| ATTACH_CARRIAGE | 20 | **always exactly 1** | **0%** |
| GRAFT (extend/prepend) | 59 | **always exactly 2** | 100% |
| PURCHASE_LINE | 13 | 1 | -- |
| CONNECT | 10 | 3 | 100% |

The crewing rule -- `legal[kind][0][0]`, "whichever line sits lowest in the
action table" -- reads as arbitrary and is not. It is **forced**: there is never
more than one legal option. Three variants that change it produce byte-identical
play, which is how this was found rather than argued.

GRAFT having exactly two options every time is the finding. Head or tail of
**one** line. On 12 seeds the heuristic ends with `lines=1` and
`longest_line == stations`, every time. It buys line slots and never spends
them, because its CONNECT rule requires two UNSERVED stations while its graft
rule fires first on every new station, so a second unserved station never
accumulates. The mask makes CONNECT legal for **any** pair, served or not; the
restriction to unserved pairs is the heuristic's own.

So the bar that has defeated four architectures, nine experiments, a search
programme and an imitation programme is a single-line policy running trains
around one loop. "Which station pair is chosen" has two candidates and they are
both the same line.

### Opening a second line costs 95 deliveries

`scripts/heuristic_variants.py` changes one rule at a time and is scored by
`paired_eval.py` on identical seeds. n=60, MDE(80%) stated per arm:

```
arm                                     mean   vs heur    95CI   MDE80   W/L/T
heuristic                             247.38     +0.00    0.00    0.00   0/0/60
v0-rebuilt (control)                  247.38     +0.00    0.00    0.00   0/0/60
v4-graft-prefers-short                247.38     +0.00    0.00    0.00   0/0/60
v5-graft-prefers-long                 247.38     +0.00    0.00    0.00   0/0/60
v6-defer-purchase                     248.25     +0.87    8.30   11.86  14/15/31
v7-second-line-closest                152.32    -95.07   24.17   34.55   6/48/ 6
v8-second-line-farthest               152.37    -95.02   24.08   34.43   8/52/ 0
v9-hold-for-second-line               106.52   -140.87   23.42   33.48   1/58/ 1
v10-second-line-late-closest          152.32    -95.07   24.17   34.55   6/48/ 6
v11-second-line-late-farthest         157.03    -90.35   25.02   35.77   8/43/ 9
v12-second-line-mid-farthest          157.03    -90.35   25.02   35.77   8/43/ 9
```

`v4` and `v5` push the graft toward short and long lines respectively and are
**byte-identical to the control**, because a per-line penalty added to both
candidates of a single line cancels. That is an independent confirmation of
`lines=1` from a completely different direction.

### The binding constraint is the fleet

Every second-line arm also ends the episode *earlier* -- 4,770 decisions against
6,839, and 3,714 for the arm that holds a station back. Measured over 8 seeds:

| | lines | metros | spare locomotives | spare carriages | decisions with a line carrying NO train |
| --- | --- | --- | --- | --- | --- |
| heuristic | 1 | 4 | 0 | 0 | **4%** |
| v7 second line | 2 | 4 | 0 | 0 | **29%** (peak 50%) |

Both policies deploy the entire fleet and both end with nothing spare. The game
grants **four metros**. Splitting them across two lines leaves one line without
a train for a third of the episode, and a line with no train still attracts the
passengers routed onto it.

**CONFIRMED, and it reframes the goal.** The single-line strategy is not an
oversight in the heuristic, it is the correct response to a four-train fleet.
The headroom that looked obvious -- "it buys line slots it never uses" -- is
negative by 95 deliveries at n=60, well outside an MDE of +/-34.5. Line slots
are not the scarce resource; trains are, and the heuristic already commits all
of them to the only line that can use them.

This is consistent with everything the ledger already contains and explains it
in one stroke: honest search does not beat the heuristic (E36) because there is
almost nothing to search over; agreement does not predict score (E40) because
the decisions agreement is measured on are 0-option or 2-option; and handing the
network the argmin does nothing (E41) because the argmin ranges over two
candidates on one line.

---

## E45 -- the residual policy was not starting at the heuristic

The design was: offer DEFER, initialise the action head DEFER-dominant, and let
PPO be paid to deviate -- so the run starts at the bar rather than 80 deliveries
below it, and every deviation is bought with measured deliveries rather than
with agreement.

**The initialisation was never measured, and it was not the heuristic.**
`action_net.weight.mul_(0.01)` sits on top of SB3's own `ortho_init` gain of
0.01, leaving the weights at std 5.2e-6. The opening policy was therefore not
"the heuristic" but "DEFER with probability p, otherwise **uniform over the
legal actions**". A critic lane built the exact checkpoint the script produces
and scored it:

| arm | opening policy | heuristic | gap | W/L/T | deviation |
| --- | --- | --- | --- | --- | --- |
| scope=all, bias 6.0 | 211.85 | 248.78 | **-36.92 +/-19.75** | 4/17/19 | 2.44% |
| scope=kind, bias 4.0 | 247.78 | 248.78 | -1.00 +/-5.53 | 3/5/32 | 0.59% |

Both live runs were therefore doing something quite different from what they
appeared to be doing. Their readouts:

```
scope=all    gap -36.9 (init) -> -15.94 -> -3.46    deviation 2.44% -> 1.29% -> 0.39%
scope=kind   gap  -1.0 (init) ->  -3.74 -> -0.84    deviation 0.59% -> 2.26% -> 0.93%
```

PPO was **un-learning the noise its own initialisation had injected**, and the
end state of that trajectory is the heuristic. Read as "the gap is closing,
training is working", it is exactly backwards. Stopped at 30,008 of 150,000
steps.

The multiply also throttled learning: gradients into the policy trunk are
proportional to the action head's norm, and 5.2e-6 is below Adam's own `eps`, so
in practice only the DEFER bias could move.

**INVALID, not refuted.** This says nothing about whether a residual policy can
beat the heuristic; it says the experiment as built could not have answered the
question. What it does establish is a discipline: the run now saves an `-init`
checkpoint and reports **readout zero** before a single gradient step, and warns
when the opening gap is below -10.

Two further design facts the same review measured, both worth having before the
experiment is rerun:

* Under `deviation_scope="kind"`, a genuine choice among the arguments of the
  proposed kind exists at **1.9% of decision points** -- about one per episode.
  In 73.4% the heuristic proposes WAIT and the offered set is {WAIT, DEFER},
  which are the same behaviour; in a further 92.9% of acting decisions the only
  alternative to the proposal is WAIT. That arm is close to a no-op.
* A gated WAIT substituted for the heuristic's move consumes the **full
  backstop, 201 decisions, on 32 of 32 substitutions** -- 19.3 game-seconds
  against a 40-second overcrowding clock. "WAIT is always a legitimate
  alternative" understates what the gate makes it cost.

---
## E46 -- head or tail is the whole game, and it explains every prior score

E44 established that the scripted policy faces exactly one decision with more
than one option: which END of its single line a new station joins. Two
candidates, about 59 times an episode. That looked like a reason the task has no
headroom. It is the opposite.

**Measured**, n=100, changing only the end-selection rule and nothing else:

| arm | mean | vs heuristic | 95% CI | MDE(80%) | W/L/T |
| --- | --- | --- | --- | --- | --- |
| heuristic (nearest end) | 253.32 | +0.00 | -- | -- | 0/0/100 |
| v0-rebuilt (control) | 253.32 | +0.00 | 0.00 | 0.00 | 0/0/100 |
| **v14 arbitrary end** | **193.14** | **-60.18** | 14.20 | 20.30 | 17/79/4 |
| v13 always far end | 149.09 | -104.23 | 13.47 | 19.25 | 2/98/0 |

**The single binary choice spans 104 deliveries.** Nothing else in the action
space comes close: crewing is forced, a second line is negative, deferring a
purchase is +0.87 +/-8.30.

### What this explains

Coin-flipping that one decision scores **193.14**. The blind control scores
183.2, the MLP clone 187.1, the pointer clone 184.7, the rank clone 189.25, and
direct RL 175.4 -- **every learned policy this project has produced sits in the
band an arbitrary head-or-tail rule produces**, and none is distinguishable from
it.

So the seven-experiment mystery of "why does nothing learned beat the heuristic,
and why is everything stuck at 185-190" has a single mechanical answer. There is
one decision. Getting it right is worth 253, getting it at chance is worth 193,
getting it wrong is worth 149. Every learner has been at chance on it.

It also retires the framing of E40 and E41 rather than contradicting them. E40
concluded "the entire gap lives in which station pair is chosen" and E41 handed
the network the argmin and got nothing. Both were looking at station SELECTION.
The decision that carries the score is not which station, it is which end -- and
the observation has carried the two distances needed for it since the REACH
block was added, which is why adding rank features on top changed agreement and
not score.

### What it does NOT establish

That the heuristic is optimal. Nearest-end is the greedy rule for growing a
path, and greedy is not optimal for path growth: a sequence of locally minimal
insertions can produce a worse final route than a sequence that occasionally
takes the longer end. That is exactly the residual the honest search measured at
**+7.55 +/-17.70 (n=20, E36)** -- consistent with zero, consistent with a real
single-digit gain, and never re-measured at adequate n.

**CONFIRMED as a characterisation of the task.** The action space offers one
real decision; it is worth 104 deliveries; the heuristic takes the greedy side
of it; every learned policy is at chance on it. A learned policy that beats the
heuristic has to beat GREEDY NEAREST-END INSERTION on a path-growing problem --
which is a well-posed question with a small expected answer, and it is the only
question this action space still contains.

**The next measurement, stated precisely.** Re-run honest search at n>=200 with
the event gate (which makes it ~130x cheaper per episode), restricted to the
graft decision alone. If the gap is a real +7, that is the ceiling of this
action space and the goal as stated is unreachable without changing the game. If
it is larger, the search's own default policy is the thing to distil.

---

## E47 -- searching the one decision directly, and finding nothing at +/-3

E46 left exactly one question: greedy nearest-end insertion is the rule that
carries the score, and greedy is not optimal for growing a path, so is there a
better end-selection rule?

`scripts/learn_end_rule.py` asks it directly. Each candidate end is scored by
six weights over local features -- distance to this end, distance to the other,
head-or-tail, stations on the line, route length, bias -- and the weights are
searched by cross-entropy method against **deliveries**, not against agreement.

**Why CEM and not PPO, stated as a measurement rather than a preference.**
Per-episode deliveries have SD ~95 against an effect of order 10, and E45
measured what attributing that to individual actions through a value function
costs: 30,000 steps spent un-learning the noise of the run's own
initialisation. CEM attributes nothing to an action. It scores a whole policy
against the scripted one **on identical seeds**, so board luck cancels inside
every comparison, and it searches six numbers instead of forty thousand.

**The anchor is checked, not asserted** -- the lesson E45 paid for. Weights
`[-1, 0, 0, 0, 0, 0]` score each end by the negative distance to it, which IS
the scripted rule, and the run refuses to start unless the maximum per-seed
difference against `rl.heuristic` is exactly zero. Measured: **0.00**.

**The search, 5 generations x 12 candidates x 60 paired seeds:**

```
[gen  0] best-of-12 gap   +2.82 +/-3.53  won 6/60   elite mean gap   +0.45
[gen  1] best-of-12 gap   +0.02 +/-0.03  won 1/60   elite mean gap   -1.14
[gen  2] best-of-12 gap   +0.72 +/-1.04  won 4/60   elite mean gap   -0.64
[gen  3] best-of-12 gap   +2.82 +/-3.53  won 6/60   elite mean gap   +0.69
[gen  4] best-of-12 gap   +1.28 +/-2.20  won 4/60   elite mean gap   +0.65
```

Every best-of-12 figure is inside the winner's-curse inflation for twelve draws
at that standard error, and the elite means straddle zero. The search converges
back onto the greedy rule because perturbing away from it loses.

**Held out, on seeds the search never saw, n=200:**

| arm | mean | vs heuristic | 95% CI | MDE(80%) | W/L/T |
| --- | --- | --- | --- | --- | --- |
| heuristic | 249.29 | +0.00 | -- | -- | -- |
| **learned end-rule** | 249.12 | **-0.17** | 2.09 | **2.99** | 5/2/**193** |
| arbitrary end (control) | 180.86 | -68.43 | 10.16 | 14.52 | 25/165/10 |

**REFUTED, and this is the best-powered negative in the ledger.** The MDE is
**+/-2.99 deliveries** -- an order of magnitude tighter than anything this
project has measured -- because 193 of 200 seeds are exact ties, so the paired
variance nearly vanishes. A real improvement of even three deliveries would have
been visible and there is none.

The control in the same table is what makes the power credible rather than a
degenerate artefact of a policy that never deviates: the arbitrary-end arm, run
on the same seeds through the same harness, reproduces E46's effect at -68.43
+/-10.16.

**What is now established.** Within a six-parameter linear family over local
features, greedy nearest-end insertion is a local optimum to within +/-3
deliveries. Combined with E36's honest search (+7.55 +/-17.70) and E44's finding
that every other decision is forced or negative, the scripted policy is at or
extremely near the ceiling of this action space.

**What is not.** A richer end-rule -- one with lookahead, or with features the
six do not span, such as where unserved stations are likely to spawn -- is
untested. So is any policy that changes the game's own parameters. The honest
statement is that the *marginal* return to better play in this action space is
now bounded near zero, not that no better policy exists.

---

## Standing conclusions

0. **There is ONE decision, it is binary, and it is worth 104 deliveries.**
   Crewing is forced (one legal option, always). A second line is worth
   -95. The only choice is which END of the single line a new station
   joins: nearest scores 253, arbitrary 193, farthest 149. Every learned
   policy this project has produced -- blind 183, clones 185-189, direct
   RL 175 -- sits in the band an arbitrary rule produces, so all of them
   have been at chance on the one decision that carries the score. Beating
   the heuristic means beating greedy nearest-end insertion, and nothing
   else in this action space is worth measuring.
   Searched directly, that decision yields nothing: a six-weight rule
   optimised on deliveries lands at -0.17 +/-2.09 on 200 held-out seeds,
   193 of them exact ties, at an MDE of +/-2.99. The scripted policy is
   at or near the ceiling of this action space.
0b. **The task is smaller than it looks, and the bar is near its ceiling.**
   The fleet is four metros and the heuristic deploys all of them on one
   line. Its crewing decisions have exactly one legal option and its graft
   decisions exactly two, so nine experiments' worth of "the learner cannot
   make the right choice" were about a choice between two candidates on one
   line. Opening a second line costs 95 deliveries. Any future claim of
   headroom should name the decision it lives in and how many options that
   decision has.
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
