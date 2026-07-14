# RL model selection for the player-pixel task

## Decision

Keep a **ten-frame multiscale `MiniMetroCNN` feeding a 256-unit LSTM with RecurrentPPO** as the default pixel-only training lane and official player-equivalent baseline. The exact oldest-to-newest offsets are `[128, 64, 7, 6, 5, 4, 3, 2, 1, 0]`, so the policy retains dense local motion plus route-state anchors 6.4 and 12.8 seconds back at the default decision cadence. This is a bounded short-term visual context plus learned recurrent state, not a claim that raw pixels are the most efficient representation of route topology or long-term demand. Keep the existing delivery-delta reward: because a game begins at zero deliveries, the undiscounted sum of those deltas is exactly the total number of passengers delivered before the episode ends. The primary evaluation metric is therefore delivered passengers, not display score or shaped reward.

The next observation/memory research step is a **semantic structured-only and direct semantic-hybrid RecurrentPPO ladder**, followed—only if semantic assistance helps—by a **player-equivalent pixel actor trained with privileged semantic supervision that is absent at deployment**. Current route topology should be represented once as compact entities/edges rather than repeatedly inferred from old screenshots. Direct semantic tensors remain an assisted/privileged-representation task even when restricted to rendered facts; they cannot silently replace or inherit the official pixel task identity.

Run **DreamerV3 `size12m`** as a separate research lane only after the cheaper semantic, hybrid, and player-equivalent transfer baselines are trustworthy. Its recurrent state-space model and replay-based imagined training are well matched to long horizons, pixels, and sparse rewards, but adapting this repository's structured pointer action, artifact contract, and Windows training path is a materially larger project.

The next high-value model improvement after recurrent PPO is a **conditional pointer head**: select the action kind first, and predict a location only when that kind uses one. This targets a mismatch in the current action distribution more directly than replacing the proven CNN encoder with a larger visual transformer.

For the current official player-equivalent task, CNN-LSTM RecurrentPPO remains the best implementation-ready model. For diagnosing whether perception rather than strategy is the bottleneck, a compact semantic LSTM is the most informative next baseline. These are hypotheses to test, not claims that one architecture is universally best. No published benchmark covers this exact game, rendering protocol, or action schema.

## Task characteristics that drive the choice

The live player contract has the following properties:

- An observation is player-visible RGB only, channel-first `uint8`, at either 192 x 108 (`fast`) or 320 x 180 (`fidelity`). The current training path uses `fast` by default.
- The default transition advances six 60 Hz simulation ticks per decision, so the policy acts at 10 Hz. Eight observations span seven inter-frame intervals, about 0.7 seconds of visible change.
- The action is `MultiDiscrete([8, 192, 108])`: an action kind plus x and y. Coordinates matter only for motion, pointer-down, and pointer-up; they are ignored for no-op, Space, and the three speed keys.
- Reward in `deliveries` mode is the number of newly delivered passengers at that transition. The sum is a partial delivery total at a time-limit truncation and the final delivery total at game over.
- Game over is a true terminal state. The configured 36,000-decision horizon is an external truncation after one simulated hour at the default transition rate.
- A frame does not reveal all causally relevant history. Route editing is a multi-action gesture, arrivals and boarding depend on motion over time, and useful strategy depends on trends that are much longer than a short image stack.
- `MiniMetroEnv` already exposes privileged variable-length structured state for debugging and recursive verification, but the official `PlayerPixelEnv` learning policy receives pixels only. Exact semantic tensors bypass visual perception even when their facts are rendered, so semantic and pixel tasks require distinct truthful identities and separate claims.

This is consequently a partially observed, long-horizon, sparse-reward visual-control problem with a structured action space. A short frame stack is useful local context; it is not persistent memory.

## Candidate comparison

| Candidate | Fit to this task | Main advantage | Main limitation | Disposition |
| --- | --- | --- | --- | --- |
| CNN PPO with frame stacking | Strong baseline | Small, established, debuggable, and already integrated | A fixed stack cannot remember events outside its window | Retain 4-frame PPO as a control; use 8-frame PPO as the memory-free ablation |
| CNN-LSTM RecurrentPPO | Strongest implementation-ready fit | Adds per-episode learned state while preserving the current PPO, CNN, vector-env, and `MultiDiscrete` path | On-policy sample cost remains high; truncated backpropagation does not guarantee hour-long credit assignment | **Default lane: 10 multiscale frames, 256-unit LSTM** |
| Semantic structured-only or direct semantic-hybrid RecurrentPPO | Strong diagnostic and assisted-policy fit | Encodes current route/entity state in kilobytes instead of repeatedly storing hundreds of MiB of historical pixels; stays compatible with recurrent Dict policies | Exact tensors bypass perception and are not player-equivalent; require new protocol/task/manifest/history identities and leakage tests | **Next observation research lane after the final game-state schema stabilizes** |
| Pixel actor with privileged training-only semantics | Strong player-equivalent research fit | A structured teacher, semantic auxiliary target, or asymmetric critic can improve representation/strategy learning while the deployed actor remains pixel-only | Requires custom training and a hard proof that evaluation/actor inference cannot access privileged inputs | **Preferred transfer lane if direct semantic assistance demonstrates value** |
| IMPALA-style recurrent CNN | Good only when collection scale is the bottleneck | Decoupled actors and learner provide high throughput; V-trace corrects actor/learner policy lag | IMPALA is a distributed algorithm and systems architecture, not merely a better encoder; it adds queues, stale-policy handling, and operational complexity | Defer until profiling proves local environment throughput is limiting and many actors are available |
| Vision Transformer or spatial transformer | Plausible later encoder ablation | Patch attention can directly model long-distance station and route relationships | A ViT is spatial, not persistent temporal memory; a direct pixel-control comparison found RAD-trained CNNs generally superior to the tested ViT methods, although auxiliary reconstruction improved ViT | Defer; first try attention over CNN feature tokens, not a from-scratch pure ViT |
| GTrXL or temporal Transformer | Plausible long-memory research | GTrXL matched or exceeded an LSTM baseline in its original partially observed RL study | Results are task-sensitive: Memory Gym later found GRU significantly ahead of Transformer-XL on all of its endless variants; sequence batching, masks, cache semantics, and attention cost also add implementation risk | Compare against LSTM only after a memory benchmark shows the LSTM ceiling |
| DreamerV3 / RSSM | Strong research fit | Learns a recurrent world model from replay and trains behavior in imagined latent trajectories; published across visual, discrete, sparse, and long-horizon domains | Requires a custom environment/action adapter, replay storage, JAX integration, and new provenance/evaluation support | **Research lane: official `size12m` preset** |
| Decision Transformer | Poor current fit | Return-conditioned sequence modeling can exploit a large offline trajectory corpus | It is fundamentally an offline method and this repository does not yet have a broad, high-quality dataset spanning strong delivery returns | Revisit only after collecting and versioning a diverse trajectory dataset |

Primary evidence for this comparison includes the [PPO paper](https://arxiv.org/abs/1707.06347), [SB3-Contrib RecurrentPPO documentation](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_recurrent.html), [IMPALA](https://arxiv.org/abs/1802.01561), the RL-specific [evaluation of ViT methods against RAD-trained CNNs](https://arxiv.org/abs/2204.04905), [GTrXL](https://arxiv.org/abs/1910.06764), [Memory Gym](https://arxiv.org/abs/2309.17207), [DreamerV3](https://www.nature.com/articles/s41586-025-08744-2), and [Decision Transformer](https://arxiv.org/abs/2106.01345).

## Recommended recurrent PPO design

Use these as the initial controlled configuration, not as permanently fixed hyperparameters:

- Shared `MiniMetroCNN` feature extractor with `features_dim=256`.
- Exact history `decision-history-10-fallback-v1` at the `fast` profile, with offsets `[128, 64, 7, 6, 5, 4, 3, 2, 1, 0]`. Keep contiguous eight as the memory-free recurrent/PPO control.
- One 256-unit LSTM layer. Start with SB3-Contrib's separate actor and critic LSTMs (`shared_lstm=False`, `enable_critic_lstm=True`) because that is its documented `CnnLstmPolicy` default; treat a shared LSTM as an ablation.
- RecurrentPPO with the implemented recurrent defaults: `gamma=1.0`, `gae_lambda=0.99`, `n_steps=128`, `batch_size=64`, four optimization epochs, and a linear learning-rate schedule starting at `2.5e-4`. The legacy feedforward PPO lane retains its established `gamma=0.999`, `gae_lambda=0.95`, and batch size 256 settings as a stable control; it is not the recurrent default. Recurrent batch size 256 was a profiled former candidate rejected before integration, not a supported training ablation.
- The delivery-delta reward with no game-over penalty and no display-score term in the primary experiment.

SB3-Contrib explicitly supports recurrent policies, multiprocessing, image observations, and `MultiDiscrete` actions. That makes it the smallest reliable implementation step from the current code. It does not prove that LSTM is the final performance ceiling.

### Temporal-history migration status

Training-manifest v2 gives temporal layout a separate immutable descriptor and `historyFingerprint` while preserving the single-frame task fingerprint. Genuine v1 manifests normalize any positive `frameStack` to their historical contiguous offsets and keep exact v1 bytes. Train, resume, and evaluation reconstruct the same descriptor-driven vector ring, with `--frame-stack` reserved for contiguous ablations and `--history-layout` for reviewed multiscale layouts; equal-channel semantic mismatch fails before artifact access. Fresh recurrent omission now resolves through one exact ten-frame default factory. Fresh explicit PPO omission deliberately remains contiguous eight, and resume/evaluation always inherit the authenticated saved descriptor.

The matched profiler used a two-stage durability contract: GM-02d1 remotely verified the campaign/gate layer, real two-update RecurrentPPO worker, and full Windows launcher/descendant sampling before any results were observed; GM-02d2 then ran from exact clean Commit B `3c684724`. The primary three-way campaign was operationally invalid because one control repeat exceeded the 100 ms sampling bound, and the valid twelve-frame target repeats independently exceeded the strict historical RAM cap. A fresh four-cycle interleaved fallback compared eight-contiguous against ten-multiscale with all eight repeats valid. Ten frames used 1.1119x the median peak working set and retained 0.8482x median throughput, passing the 1.25x relative-memory, strict 4,197,256,790-byte historical-memory, and 0.75x throughput gates. This proves an engineering-safe observation contract, not higher passenger deliveries; efficacy remains a held-out multi-seed experiment.

### Episode-memory semantics

"Persistent memory" means learned recurrent state that persists **within one episode**, not hidden state that leaks between games:

1. Maintain an independent `(hidden, cell)` state for every vector-environment slot.
2. Feed the state returned by one policy call into the next call for that same slot.
3. Reset state when that slot starts a new episode, whether the preceding episode ended by game over or by horizon truncation. Never transfer state across seeds, evaluation episodes, or vector slots.
4. Pass the episode-start mask on every inference/evaluation call. SB3-Contrib warns that both `lstm_states` and `episode_start` are required for correct recurrent prediction.
5. Preserve recurrent state across PPO rollout boundaries during collection. Store episode-start masks and the initial state for each training sequence so shuffled minibatches cannot join unrelated histories.
6. Model checkpoints persist learned weights, not the transient memory of a particular game. A resumed or newly evaluated game starts with zero recurrent state.

Inference reset and value bootstrapping are different concerns. A new episode always receives reset recurrent state. For learning targets, game over is a termination and must not bootstrap; the external horizon is a truncation and should bootstrap from the final observation's value. This distinction follows [Gymnasium's time-limit guidance](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/). Because vector wrappers can collapse both outcomes into `done`, tests must verify that the final observation and truncation marker reach RecurrentPPO correctly.

An LSTM state can be carried for 36,000 decisions, but that does not mean gradients span 36,000 decisions. With the current `n_steps=128`, one rollout covers 12.8 simulated seconds per environment; recurrent backpropagation is truncated by the sequence construction. If a diagnostic memory task requires longer credit assignment, sweep rollout/sequence length after measuring RAM and throughput rather than assuming persistent inference state alone solves it.

## Non-visual strategic state and privileged training

More image history is the wrong representation for facts that already have a compact current-state form. A route graph, queue composition, metro assignment, resources, and modal/progression state should be available as one current snapshot; recurrent memory should focus on trends, prior actions, and events that are not recoverable from that snapshot. This separates three honest task tiers:

1. `player_pixel` remains the official player-equivalent task. The deployed actor currently receives rendered pixels plus its learned recurrent state; explicit prior-action or reward inputs would be a separately declared future observation ablation.
2. `semantic_hybrid` receives pixels plus exact fixed-shape tensors derived from rendered game semantics. This is a perception-assist task, not player-equivalent, even if it excludes RNG, future spawns, hidden travel plans, and internal timers.
3. `structured_oracle` may use broader simulator state only as a diagnostic ceiling, teacher, semantic auxiliary target, or asymmetric critic. It is never a deployed player policy input.

A current feasibility packing—not a frozen future schema—can represent the present 20-station, 4-line, 4-metro, 7-destination-shape game in about 2,178 `float32` values. That is 8.51 KiB per observation or 8.51 MiB for 8 environments x 128 rollout steps, compared with 607.5 MiB for the current raw ten-frame pixel payload. The final schema must wait until GM-05 through GM-10 finish route editing, fleet/carriages, application state, maps/tunnels, calendar/progression, upgrades, and pause/modal mechanics.

The first semantic encoder should be intentionally simple: padded masked station/line/metro/global tensors, shared per-entity MLPs or a flat diagnostic MLP, simple pooling, fusion to 256 features, and the existing separate 256-unit actor/critic LSTMs through `MultiInputLstmPolicy`. A small relation-aware encoder is justified only if route/topology diagnostics expose a pooling failure. GTrXL or another temporal Transformer is justified only if a dedicated held-out memory task exposes an LSTM/GRU ceiling: the original [GTrXL study](https://arxiv.org/abs/1910.06764) was strong, while the 2025 [Memory Gym](https://www.jmlr.org/papers/v26/24-0043.html) results found GRU significantly ahead of Transformer-XL on all endless variants and found Transformer-XL's finite-task advantage only with auxiliary reconstruction.

The direct semantic and hybrid lanes answer whether compact strategy state helps delivery performance. If they do, preserve player equivalence through a separate pixel actor trained with privileged information that is unavailable during evaluation. [Asymmetric Actor Critic](https://arxiv.org/abs/1710.06542) conditions only the critic on simulator state, [Learning by Cheating](https://arxiv.org/abs/1912.12294) transfers a privileged teacher into a visual student, and [UNREAL](https://arxiv.org/abs/1611.05397) demonstrates auxiliary representation-learning signals. None of these results proves the method will help Mini Metro; they define controlled candidates.

Implementation is more than selecting a policy alias. The current task/protocol descriptors promise a pixels-only `Box`; `MiniMetroCNN` and `VecTemporalHistory` are Box-specific; manifest v2 requires positive RGB history. A future semantic/hybrid lane therefore needs a distinct protocol/task descriptor, manifest v3, a Dict-aware wrapper that histories only pixels while aligning latest semantic state through terminal/autoreset boundaries, a custom multi-input extractor, per-slot derived-memory isolation, and genuine pixel v1/v2 compatibility. The versioned manifest is the semantic authority: it authenticates the artifact-index snapshot, the index authenticates models, and durable experiment evidence separately authenticates the exact manifest bytes.

## Why the conditional pointer head comes next

The current generic `MultiDiscrete` policy emits independent categorical distributions whose total logit count is `8 + 192 + 108 = 308`. It must emit x and y for every action even though five of the eight action kinds ignore them. It also cannot make the pointer distribution conditional on whether it chose motion, down, or up.

A task-aligned head should:

1. Predict the eight-way action kind.
2. For motion/down/up, predict a spatial heatmap or kind-conditioned x/y distributions.
3. For the other kinds, omit pointer loss and use a canonical ignored coordinate at execution.
4. Compute the joint log probability and entropy only over semantically active branches so PPO ratios remain correct.

This is a repository-specific inference from the action contract. Prior parameterized-action research likewise found value in conditioning parameter policies on the selected discrete action; see [Hierarchical Approaches for Reinforcement Learning in Parameterized Action Space](https://arxiv.org/abs/1810.09656). The proposed discrete pointer head still needs an implementation and ablation here.

## Resource math

The tensor sizes below are deterministic shape calculations:

| Item at 192 x 108 | Size |
| --- | ---: |
| One RGB `uint8` frame | 62,208 bytes = 60.75 KiB |
| Four-frame `uint8` observation | 243 KiB |
| Eight-frame `uint8` observation | 486 KiB |
| Ten-frame `uint8` observation | 607.5 KiB |
| 8 envs x 128 steps of eight-frame observations as raw `uint8` | 486 MiB |
| 8 envs x 128 steps of ten-frame observations as raw `uint8` | 607.5 MiB |
| Current diagnostic semantic vector, one `float32` observation | 8.51 KiB |
| 8 envs x 128 steps of current diagnostic semantic vectors | 8.51 MiB |
| One eight-frame observation materialized as `float32` | 1.898 MiB |
| One ten-frame observation materialized as `float32` | 2.373 MiB |
| 64 eight-frame observations materialized as `float32` | 121.5 MiB |
| 64 ten-frame observations materialized as `float32` | 151.875 MiB |
| 256 eight-frame observations materialized as `float32` | 486 MiB |
| 8 envs x 128 steps of eight-frame observations as dense `float32` | 1.898 GiB |

The default ten-frame rollout's raw observation payload is already 607.5 MiB before metadata; the matched eight-frame control is 486 MiB. The `float32` rows show the additional risk when recurrent sequence padding and image normalization materialize minibatches; activations, gradients, optimizer state, recurrent state, process workers, and framework copies are additional.

The older one-run CPU profile rejected recurrent batch 256 in favor of batch 64. The newer matched fallback campaign measured eight-contiguous and ten-multiscale under identical 8-environment x 128-step, batch-64/four-epoch training. Median process-tree working set was 3,636,346,880 versus 4,043,184,128 bytes; median end-to-end throughput was 86.3032 versus 73.2052 FPS. These gigabyte values sum instantaneous working set across the trainer and eight environment processes and may double-count shared pages; they are not disk use. The complete raw JSONL/log/summary evidence for both primary and fallback campaigns occupies about 16.7 MiB. These Windows measurements are engineering guardrails, not portable performance guarantees, so longer training must still record wall time and peak RAM/VRAM.

At ten frames, the current CNN has 377,248 trainable parameters. One 256-input/256-hidden PyTorch LSTM has 526,336 parameters; separate actor and critic LSTMs have 1,052,672. Adding the current 308-logit action head and scalar value head makes the CNN/recurrent/head core 1,450,005 parameters. The two live 256-to-64-to-64 policy MLPs bring the exact profiled policy total to 1,491,221. The model is therefore modest; observation and rollout tensors, not weights, are the first memory concern.

DreamerV3's official configuration defines [`size12m`](https://github.com/danijar/dreamerv3/blob/main/dreamerv3/configs.yaml) as the second-smallest named preset. Twelve million FP32 parameters are about 45.8 MiB; parameters, gradients, and two Adam moments are roughly 183 MiB before activations and JAX runtime allocation. Replay is the larger storage issue here: uncompressed single RGB frames consume about 5.79 GiB per 100,000 frames, 57.94 GiB per million, and 289.68 GiB at DreamerV3's default five-million-item replay capacity. A Dreamer lane must cap or compress replay and store individual frames rather than repeated frame stacks.

## Discounting and GAE

The user's objective is the undiscounted delivery total at game over. Fresh recurrent runs therefore use `gamma=1.0`: the sum of delivery deltas is exactly the number of passengers delivered, while `gamma < 1` optimizes a time-discounted proxy.

`gamma=1.0` also removes a task-specific speed-control distortion. Discount is applied once per policy decision, but the `1`/`2`/`3` controls change how much simulated time advances during a decision. With `gamma < 1`, reaching the same delivery after fewer decisions at a faster game speed receives a larger discounted weight even when the final delivery total is unchanged. The undiscounted default removes that artificial preference; real effects of speed on control quality, passenger waiting, and deliveries remain part of the task.

The 36,000-decision horizon is an external truncation, not game over. Learning targets must bootstrap from the final observation's value at that cutoff, including with `gamma=1.0`; only true game over receives no bootstrap. Otherwise the arbitrary training horizon would be assigned a false zero continuation value and would reintroduce pressure to deliver earlier for the wrong reason.

Undiscounted returns can increase value-target variance. Pre-register `gamma=0.9999` as the first recurrent stability ablation while keeping `gae_lambda=0.99`; at the default 1x cadence of 10 decisions per simulated second it has an 11.6-minute reward-weight half-life and weights a delivery ten minutes later about 0.549. Select between it and `1.0` on the held-out delivery-total protocol, not one lucky seed. The legacy feedforward PPO setting of `gamma=0.999` remains a control, not a canonical recurrent candidate: at 1x its half-life is only about 69 seconds, and it weights a delivery ten minutes later about 0.0025.

GAE trades bias against variance; it does not define the policy's memory capacity. The recurrent default `gamma=1.0`, `gae_lambda=0.99` has an advantage-trace half-life of about 69 decisions, or 6.9 simulated seconds at the default 1x cadence. The legacy feedforward `0.999/0.95` pair has a trace half-life of about 13.3 decisions, or 1.33 simulated seconds at 1x. If recurrent value loss or between-seed variance is unstable, ablate lower GAE lambda values such as `0.97` and `0.95` without confusing that estimator change with persistent-memory capacity. The underlying estimator is described in the [GAE paper](https://arxiv.org/abs/1506.02438).

## Experiment protocol

Architecture choice is complete only after controlled evaluation:

1. Compare at least these observation/action lanes: 4-frame CNN PPO, 8-frame CNN PPO, ten-frame multiscale CNN-LSTM RecurrentPPO, semantic structured-only RecurrentPPO, direct semantic-hybrid RecurrentPPO, a pixel-only actor with privileged training assistance, and the recurrent pixel lane with the conditional pointer head. Change one observation or action-head dimension at a time before interpreting a combined candidate. Add DreamerV3 `size12m` only when its task adapter passes the same environment tests.
2. Run at least **five independent training seeds per configuration**. Five is a minimum engineering threshold, not enough evidence to report tiny differences as settled.
3. Use separate training, tuning/validation, and final evaluation seed sets. Evaluate every checkpoint on the same held-out seed suite; do not select a checkpoint on its training episodes.
4. Use at least 20 deterministic evaluation episodes per seed for final comparisons. Preserve recurrent state within each episode and reset it at every episode boundary.
5. Treat each independently trained run/seed as the top-level independent experimental unit. Summarize the fixed held-out episode suite within each run and retain every episode row. Compute mean, median, and interquartile mean over run-level summaries, never pooled episodes. Resample training runs for confidence intervals; if episode-level uncertainty is retained, use a hierarchical cluster bootstrap that resamples runs first and episodes within selected runs. Keep the held-out environment-seed suite paired across architectures and report the full run-level distribution. With five runs, intervals remain exploratory. Report the best-seed score only as a diagnostic, never as the headline.
6. Report game-over count/rate, truncation count/rate, episode decisions, simulation time, environment steps, wall-clock training time, environment frames per second, hardware, peak RAM/VRAM, and parameter count.
7. Separate game-over episodes from horizon-truncated episodes. A strong policy that reaches the horizon has a right-censored delivery total; if truncation is common, lengthen the evaluation horizon rather than declaring the partial total final. `meanDeliveriesAmongGameOverEpisodes` is conditional and potentially selection-biased when other episodes truncate, so it supplements rather than replaces the full episode-boundary distribution.
8. Compare equal environment-step budgets and also show wall-clock curves. Dreamer can reuse samples more heavily than PPO, so either axis alone is incomplete.
9. Keep task fingerprints, reward mode, render profile, fixed ticks, action semantics, and evaluation seeds identical across architecture comparisons. Any curriculum or reward shaping is a separate experiment.
10. Include random/no-op and deterministic demonstrator sanity baselines, inspect action-kind frequencies, and verify that a trained agent can complete a route gesture rather than exploiting ignored coordinates or pause/speed controls.

These practices follow the variance and evaluation warnings in [Stable-Baselines3's RL guidance](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html), [Deep Reinforcement Learning that Matters](https://arxiv.org/abs/1709.06560), [Empirical Design in Reinforcement Learning](https://arxiv.org/abs/2304.01315), and [Deep RL at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264).

## Promotion criteria

Retain the ten-frame RecurrentPPO lane as the trained pixel-policy default only if, across the pre-registered seed suite, it improves held-out deliveries over both frame-stack PPO controls without an unacceptable wall-clock or memory regression and without increasing invalid or semantically wasted action behavior.

Promote a direct semantic or hybrid model only within its explicitly assisted task and only if leakage/lifecycle tests pass. Promote a player-equivalent transferred model only if evaluation physically omits the privileged channel, the actor cannot access teacher/critic-only tensors, and held-out delivery evidence beats the pixel baseline at acceptable cost.

Promote the conditional pointer head only if it improves deliveries or sample efficiency while PPO log-probability/entropy tests prove that inactive coordinate branches are masked correctly.

Promote DreamerV3 only if its adapter preserves the exact player-visible observation and action contract, its replay and checkpoint artifacts are reproducible, and it beats the recurrent PPO lane on held-out deliveries under transparently reported environment-step and wall-clock budgets.
