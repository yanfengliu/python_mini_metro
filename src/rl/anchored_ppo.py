"""MaskablePPO with a continual KL penalty toward a frozen reference policy.

Warm-starting PPO from a cloned policy erodes it: 146.5 deliveries at 50k steps
falling to 46.4 by 100k, and that is *after* fixing the two defects that
previously destroyed it outright (a value head left at its initialisation, and an
observation that could not express the teacher's decision). The policy drifts
away from a good starting point and does not come back.

AlphaStar's ablation is the strongest published evidence on exactly this. Merely
*initialising* from the supervised policy is worth +84 Elo; adding a **continual**
KL penalty toward that same frozen policy is worth **+380** on top. The reference
is not a starting point to be left behind -- it is an anchor held throughout.

This is deliberately not `target_kl`. That bounds how far one update moves from
the *previous* policy, so a slow drift of many small steps passes it untouched --
which is the drift observed here. This bounds distance from a *fixed good policy*
instead, so drift accumulates a cost.

The anchor is a floor, not a ceiling: a genuinely better action can still be
taken, it just has to be worth more than the divergence it costs.
"""

from __future__ import annotations

import numpy as np
import torch as th
from torch.nn import functional as F


def build_anchored_ppo_class():
    """Build lazily, so importing this module does not require the RL stack."""
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.buffers import MaskableRolloutBufferSamples
    from stable_baselines3.common.utils import explained_variance

    class AnchoredMaskablePPO(MaskablePPO):
        """PPO that pays a price for leaving the reference policy behind."""

        def set_anchor(self, reference, coefficient: float) -> None:
            """Freeze `reference` as the policy to stay near."""
            self.anchor_policy = reference.policy
            self.anchor_policy.set_training_mode(False)
            for parameter in self.anchor_policy.parameters():
                parameter.requires_grad_(False)
            self.anchor_coefficient = float(coefficient)

        def train(self) -> None:
            self.policy.set_training_mode(True)
            self._update_learning_rate(self.policy.optimizer)
            clip_range = self.clip_range(self._current_progress_remaining)
            clip_range_vf = (
                self.clip_range_vf(self._current_progress_remaining)
                if self.clip_range_vf is not None
                else None
            )

            entropy_losses, anchor_losses = [], []
            pg_losses, value_losses = [], []
            clip_fractions = []
            continue_training = True

            for epoch in range(self.n_epochs):
                approx_kl_divs = []
                for rollout_data in self.rollout_buffer.get(self.batch_size):
                    actions = rollout_data.actions
                    if isinstance(self.action_space, type(self.action_space)) and (
                        actions.dtype in (th.int32, th.int64)
                    ):
                        actions = actions.long().flatten()

                    masks = (
                        rollout_data.action_masks
                        if isinstance(rollout_data, MaskableRolloutBufferSamples)
                        else None
                    )
                    values, log_prob, entropy = self.policy.evaluate_actions(
                        rollout_data.observations, actions, action_masks=masks
                    )
                    values = values.flatten()

                    advantages = rollout_data.advantages
                    if self.normalize_advantage and len(advantages) > 1:
                        advantages = (advantages - advantages.mean()) / (
                            advantages.std() + 1e-8
                        )

                    ratio = th.exp(log_prob - rollout_data.old_log_prob)
                    policy_loss_1 = advantages * ratio
                    policy_loss_2 = advantages * th.clamp(
                        ratio, 1 - clip_range, 1 + clip_range
                    )
                    policy_loss = -th.min(policy_loss_1, policy_loss_2).mean()
                    pg_losses.append(policy_loss.item())
                    clip_fractions.append(
                        th.mean((th.abs(ratio - 1) > clip_range).float()).item()
                    )

                    if clip_range_vf is None:
                        values_pred = values
                    else:
                        values_pred = rollout_data.old_values + th.clamp(
                            values - rollout_data.old_values,
                            -clip_range_vf,
                            clip_range_vf,
                        )
                    value_loss = F.mse_loss(rollout_data.returns, values_pred)
                    value_losses.append(value_loss.item())

                    entropy_loss = (
                        -th.mean(-log_prob) if entropy is None else -th.mean(entropy)
                    )
                    entropy_losses.append(entropy_loss.item())

                    loss = (
                        policy_loss
                        + self.ent_coef * entropy_loss
                        + self.vf_coef * value_loss
                    )

                    # The anchor. KL(reference || current) over the masked
                    # distribution, so it is measured on what the policy can
                    # actually choose rather than over all 364 table entries.
                    anchor = getattr(self, "anchor_policy", None)
                    if anchor is not None and self.anchor_coefficient > 0:
                        with th.no_grad():
                            reference = anchor.get_distribution(
                                rollout_data.observations, action_masks=masks
                            ).distribution
                        current = self.policy.get_distribution(
                            rollout_data.observations, action_masks=masks
                        ).distribution
                        anchor_loss = th.distributions.kl_divergence(
                            reference, current
                        ).mean()
                        anchor_losses.append(anchor_loss.item())
                        loss = loss + self.anchor_coefficient * anchor_loss

                    with th.no_grad():
                        log_ratio = log_prob - rollout_data.old_log_prob
                        approx_kl_div = (
                            th.mean((th.exp(log_ratio) - 1) - log_ratio).cpu().numpy()
                        )
                        approx_kl_divs.append(approx_kl_div)

                    if (
                        self.target_kl is not None
                        and approx_kl_div > 1.5 * self.target_kl
                    ):
                        continue_training = False
                        break

                    self.policy.optimizer.zero_grad()
                    loss.backward()
                    th.nn.utils.clip_grad_norm_(
                        self.policy.parameters(), self.max_grad_norm
                    )
                    self.policy.optimizer.step()

                self._n_updates += 1
                if not continue_training:
                    break

            explained_var = explained_variance(
                self.rollout_buffer.values.flatten(),
                self.rollout_buffer.returns.flatten(),
            )
            self.logger.record("train/entropy_loss", np.mean(entropy_losses))
            self.logger.record("train/policy_gradient_loss", np.mean(pg_losses))
            self.logger.record("train/value_loss", np.mean(value_losses))
            self.logger.record("train/approx_kl", np.mean(approx_kl_divs))
            self.logger.record("train/clip_fraction", np.mean(clip_fractions))
            self.logger.record("train/explained_variance", explained_var)
            if anchor_losses:
                self.logger.record("train/anchor_kl", np.mean(anchor_losses))
            self.logger.record(
                "train/n_updates", self._n_updates, exclude="tensorboard"
            )
            self.logger.record("train/clip_range", clip_range)

    return AnchoredMaskablePPO
