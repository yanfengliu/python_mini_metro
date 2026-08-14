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
| trained agent, best so far | 3.75 mean / max 17 |

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
*can* point benefits from the same signal. That combination is E17.

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
6. **A bootstrap signal must form a ladder, not a single rung.** Shaping
   proximity moved reward off zero for the first time, and the agent then banked
   exactly the budget and stopped: true deliveries stayed at 0.00 through
   300,000 steps. Every rung has to be reachable from the one below it.
7. **A shaping signal must be reachable, and then it must be bounded.** E14
   shaped an unreachable milestone and changed nothing; E15 made it dense and
   immediately created a farming exploit worth 4x the real objective. Both
   failure modes are cheap to test for before any training run: check the signal
   fires under random play, then drive a deliberately degenerate policy against
   it.
