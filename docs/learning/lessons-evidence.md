# Lessons evidence

The war story and the anchor behind every rule in [lessons.md](lessons.md). Not session-start reading — open an entry when its rule is in doubt, or when the work is in that area.

An entry with no anchor is folklore. Entries are corrected in place as understanding improves, with the correction dated; deletion is reserved for a lesson that became a gate.

---

## Read the outcome curve before optimising the machinery that produces it

**Anchor:** 2026-08-14, commit `80efd95`; `docs/rl-experiments.md` E1, E2, E4.

Two real defects were found and fixed in the RL stack before anyone looked at a reward curve. The installed torch was a CPU build on a machine with an RTX 4090, worth **146x** on a forward+backward pass (398.88 ms to 2.73 ms). The pixel encoder pooled every render profile down to an identical 960 values, so raising resolution provably changed nothing — a 16 px shift of the whole frame moved the features less than a 2 px shift did.

Both were genuine. Neither could have moved the score. Two 3M-step training runs then held `rollout/ep_rew_mean` at **exactly 0.00 at every logged step**, because across 12 random episodes and 4,170 decisions the policy never once built a usable line: with no reward anywhere in a batch the advantage is identically zero and the policy gradient is the zero vector.

Reading one curve first would have reordered the whole day. The generalisation is not "profile before optimising" — it is that a fix on a path carrying no signal cannot be validated by the thing you care about, so it should be sequenced after something that can be.

What was tried and abandoned: throughput work. The environment pipeline delivers ~1300 env-FPS against training's 133-235, and `SubprocVecEnv` is 3.8x *faster* than in-process, so the IPC hypothesis was wrong too. All of it was moot at zero reward. Do not restart that work until a policy earns reward.

---

## When two metrics disagree in direction, the measurement is wrong

**Anchor:** 2026-08-14, commit `9b2fb66`; `docs/rl-experiments.md` E7 and E8.

An ablation compared a flat coordinate head against a spatial heatmap and reported the flat head at **8371x uniform** probability — an apparently crushing win for the status quo, and the opposite of the truth.

The tell was internal: the same run gave the flat head 40% probability *and* a **worse** argmax error than the arm it beat. Those cannot both be true of a better model. The cause was that the expert's pointer actions mix two populations — drags targeting stations, whose coordinates move with the layout, and clicks on fleet controls, which sit at **fixed UI pixels in every game**. A flat head memorises a constant trivially, so the experiment measured recall of a constant rather than visual grounding.

Restricted to station targets, the result reversed: flat **1.9x** uniform against spatial **9.5x**.

The habit worth keeping is to look for the internal contradiction before believing a surprising result, and to ask what population the data actually contains.

---

## Do not report an effect size from a handful of bimodal trials

**Anchor:** 2026-08-14, commit `d6e0148` correcting `9bc1321`.

A configuration was published as **6.17 mean deliveries, max 19** on six evaluation episodes. Twelve held-out episodes gave **1.50, max 9**. The number had already been committed and written into a published summary.

Outcomes here are near-bimodal: either the opening drag lands and the run continues, or it does not and the run dies at exactly the 400-decision deadline. A mean over a handful of episodes is therefore mostly a count of lucky seeds, and its variance is enormous. The qualitative finding survived the correction; the effect size did not.

`docs/rl-model-selection.md` pre-registers five seeds per configuration and at least 20 evaluation episodes with run-level statistics. That standard exists precisely for this, and was not met by the run that produced the wrong number.

---

## Match the finest addressable unit to the smallest target

**Anchor:** 2026-08-14, commits `9bc1321` and `526fea1`; `docs/rl-experiments.md` E9 and E12.

The policy must point at a station roughly ten pixels wide. Reading its heatmap from a 7x12 feature grid, resampled ~15x up to the action grid, delivered **0** passengers however well trained — the representation's finest addressable unit was coarser than the thing it had to hit. Reading from a 27x48 grid (4x resample) produced the first non-zero deliveries. Preserving resolution to the full action grid through a U-Net raised probability on the expert's exact pixel by **11.8x** (pointer loss 3.127 to 0.656) with **3.4x fewer parameters**, and deliveries from 3.08 to 3.75.

Two generalisations. First, resolution was being destroyed in two independent places — at render, where a passenger is **0.5 px** and therefore gone before the network sees it, and in the encoder, which strides it away — and fixing either alone leaves the ceiling in place. Raising the render profile *after* the encoder was fixed took deliveries from 3.75 to **17.33**.

Second, the reason partial fixes read as exactly zero: a drag needs about four correct pointer actions in sequence, so per-action accuracy compounds and there is no partial credit until a threshold is crossed.

Inherited defaults are worth checking against the task. The encoder here was Nature DQN's, designed for Atari, where translation *invariance* is correct because the output is one of eighteen joystick actions. Choosing where to click is keypoint localisation and needs equivariance — the opposite property. This repo's variant also strided 2 on the third convolution where the original used stride 1, discarding another 2x.

---

## A training signal must be reachable, then bounded

**Anchor:** 2026-08-14; `docs/rl-experiments.md` E14 and E15, `src/rl/shaping.py`.

Reward shaping was added to let the game be learned without a teacher. The first version paid credit for joining stations onto a usable route. Across **24 random episodes and 8,721 decisions it paid out zero times**, because that is precisely the event an exploring policy never reaches — it reproduced the exact zero gradient it was built to remove.

Replacing it with a dense signal — credit on every pointer-down, rising as the click nears a station — fires in **24 of 24** episodes. That immediately created the opposite failure: at 0.02 per pointer-down over a 4000-decision episode a policy can bank ~80 against the ~19-20 real play earns, making "stand beside a station and click forever" optimal. A per-episode budget of 1.0 closes it, verified by driving exactly that degenerate policy and measuring 1.00 total.

Both checks are cheap and belong before any training run: confirm the signal fires under random play, then drive a deliberately degenerate policy against it.

---

## Keep training-time concerns out of fingerprinted contracts

**Anchor:** 2026-08-14; `test/test_gm09a2_task_identity.py`, protocol fingerprint `69c604ac` to `233b0d6b`.

Reward shaping was first implemented as a new `RewardMode.SHAPED` enum member. Adding it rotated the protocol fingerprint, which broke `task_spec_from_manifest` for every previously saved model: six task-identity tests failed and a legacy-manifest byte-compatibility test errored outright.

The suite was right, and the wrapper it forced is the better design regardless. The task is "deliver passengers"; shaping is scaffolding used while learning it, so it belongs in a `gym.Wrapper` applied to training environments only. Evaluation wraps nothing, and a test now pins that both fingerprints are unmoved by wrapping.

The general form: anything that changes a declared contract invalidates saved artifacts built against it, so ask whether the concern is really part of the task before extending the contract to hold it.

---

## Anchor text edits to the file's real bytes

**Anchor:** 2026-08-14; the GIF save block in `scripts/bc_spatial.py`, which collected frames for a full run and silently wrote nothing.

Programmatic edits failed repeatedly in one session for two reasons, both silent. These files are **CRLF**, so an anchor string built with `\n` never matches and the patch reports "anchor not found" at best — or, when several edits are batched before a single write, discards the edits that *did* apply. And `ruff format` may already have rewritten the exact line being matched, so an anchor copied from memory of the pre-format source no longer exists.

The GIF case is the one that cost real work: the save block's anchor had been reformatted, the edit silently never applied, and a full training run finished having captured frames it never wrote.

What works: read the file, detect its line ending from its own bytes, assert each anchor immediately before its own write rather than batching, and re-read after any formatter run.

---

## Validate the capability, not the mechanism

**Anchor:** 2026-08-14; `test/test_env_agency.py`, and experiments E14-E20 in `docs/rl-experiments.md`.

Six environment defects in one project shared a single shape. Each time the
mechanism was verified -- it imported, it ran, the loss descended -- and the
capability the agent actually gained was not. Each looked like a weak policy
rather than a broken environment, and every one was found by *playing* the
environment, never by reading the code.

    shaping paid for a milestone exploration never reaches   0 payouts / 24 episodes
    a denser signal was farmable                             ~80 vs ~20 for real play
    the mask advertised line slots the game had not unlocked 283 of 284 actions no-ops
    lines could only ever hold two stations                  no network expressible
    the shape encoding moved between episodes                shape-matching unlearnable
    the mask left one legal action per step                  the score measured the sim

The last is the sharpest. After fixing everything else the environment scored
171.5 with a random policy and looked solved; the median number of legal
actions per step was **one**. The agent was watching the simulation. Restoring
route editing took the median to 4 and random play to 0 -- a worse number and
a far better environment, because there were finally decisions to get wrong.

What was tried and abandoned: reasoning about these from the code. Every
defect above is invisible in a diff and obvious in a rollout. The five
questions that catch them are cheap and now run as tests -- can the agent
reach the signal, express the strategies the game rewards, decide between
real options, and not exploit any of it, and does an episode end because the
game ended?

Deleted from `lessons.md` when `test_env_agency.py` covers a case fully; the
rule stays only while judgement is still doing work the gate cannot.
