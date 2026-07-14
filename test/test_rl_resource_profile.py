from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.history import (
    DECISION_HISTORY_LAYOUT,
    EIGHT_MULTISCALE_HISTORY_LAYOUT,
    TEN_MULTISCALE_HISTORY_LAYOUT,
    contiguous_history,
)
from rl.resource_profile import (
    BASELINE_CANDIDATE,
    EIGHT_MULTISCALE_CANDIDATE,
    FALLBACK_CAMPAIGN,
    FALLBACK_CANDIDATES,
    HISTORICAL_WORKING_SET_CAP_BYTES,
    MAC_FORMULAS,
    PRIMARY_CAMPAIGN,
    PRIMARY_CANDIDATES,
    RECURRENT_BATCH_SIZE,
    RECURRENT_EPOCHS,
    TEN_MULTISCALE_CANDIDATE,
    TWELVE_MULTISCALE_CANDIDATE,
    ProfileRepeat,
    conv2d_macs,
    conv2d_output_size,
    counterbalanced_schedule,
    estimate_inference_macs,
    estimate_storage,
    evaluate_promotion,
    linear_macs,
    lstm_macs,
)


class TestProfileCandidates(unittest.TestCase):
    def test_candidate_sets_pin_exact_live_history_descriptors(self) -> None:
        self.assertEqual(
            tuple(PRIMARY_CANDIDATES),
            (
                BASELINE_CANDIDATE,
                EIGHT_MULTISCALE_CANDIDATE,
                TWELVE_MULTISCALE_CANDIDATE,
            ),
        )
        self.assertEqual(PRIMARY_CANDIDATES[BASELINE_CANDIDATE], contiguous_history(8))
        self.assertEqual(
            PRIMARY_CANDIDATES[EIGHT_MULTISCALE_CANDIDATE].layout,
            EIGHT_MULTISCALE_HISTORY_LAYOUT,
        )
        self.assertEqual(
            PRIMARY_CANDIDATES[TWELVE_MULTISCALE_CANDIDATE].layout,
            DECISION_HISTORY_LAYOUT,
        )
        self.assertEqual(
            tuple(FALLBACK_CANDIDATES),
            (BASELINE_CANDIDATE, TEN_MULTISCALE_CANDIDATE),
        )
        self.assertEqual(
            FALLBACK_CANDIDATES[TEN_MULTISCALE_CANDIDATE].layout,
            TEN_MULTISCALE_HISTORY_LAYOUT,
        )
        with self.assertRaises(TypeError):
            PRIMARY_CANDIDATES["extra"] = contiguous_history(1)  # type: ignore[index]

    def test_cyclic_schedule_is_position_balanced_for_primary_campaign(self) -> None:
        candidates = tuple(PRIMARY_CANDIDATES)
        schedule = counterbalanced_schedule(candidates, repeats=3)

        self.assertEqual(
            schedule,
            (
                candidates,
                (candidates[1], candidates[2], candidates[0]),
                (candidates[2], candidates[0], candidates[1]),
            ),
        )
        for position in range(3):
            self.assertEqual(
                {row[position] for row in schedule},
                set(candidates),
            )

    def test_schedule_rejects_too_few_repeats_duplicates_and_empty_names(self) -> None:
        invalid = (
            (("a", "b"), 2),
            (("a", "a"), 3),
            (("a", ""), 3),
            ((), 3),
        )
        for candidates, repeats in invalid:
            with self.subTest(candidates=candidates, repeats=repeats):
                with self.assertRaises((TypeError, ValueError)):
                    counterbalanced_schedule(candidates, repeats=repeats)

    def test_schedule_requires_complete_cycles_and_balances_fallback(self) -> None:
        with self.assertRaises(ValueError):
            counterbalanced_schedule(tuple(PRIMARY_CANDIDATES), repeats=4)
        with self.assertRaises(ValueError):
            counterbalanced_schedule(tuple(FALLBACK_CANDIDATES), repeats=3)

        candidates = tuple(FALLBACK_CANDIDATES)
        schedule = counterbalanced_schedule(candidates, repeats=4)
        self.assertEqual(
            schedule,
            (candidates, candidates[::-1], candidates, candidates[::-1]),
        )
        for position in range(len(candidates)):
            counts = {
                candidate: sum(row[position] == candidate for row in schedule)
                for candidate in candidates
            }
            self.assertEqual(counts, {candidate: 2 for candidate in candidates})


class TestStorageContract(unittest.TestCase):
    def test_storage_math_is_exact_for_contiguous_and_multiscale_histories(
        self,
    ) -> None:
        contiguous = estimate_storage(contiguous_history(8))
        multiscale = estimate_storage(PRIMARY_CANDIDATES[EIGHT_MULTISCALE_CANDIDATE])
        twelve = estimate_storage(PRIMARY_CANDIDATES[TWELVE_MULTISCALE_CANDIDATE])

        self.assertEqual(contiguous.single_frame_bytes, 62_208)
        self.assertEqual(contiguous.rollout_observations_bytes, 509_607_936)
        self.assertEqual(contiguous.history_ring_bytes, 3_981_312)
        self.assertEqual(contiguous.one_step_output_bytes, 3_981_312)
        self.assertEqual(contiguous.nominal_minibatch_uint8_bytes, 31_850_496)
        self.assertEqual(contiguous.nominal_minibatch_float32_bytes, 127_401_984)

        self.assertEqual(multiscale.rollout_observations_bytes, 509_607_936)
        self.assertEqual(multiscale.history_ring_bytes, 64_198_656)
        self.assertEqual(twelve.rollout_observations_bytes, 764_411_904)
        self.assertEqual(twelve.history_ring_bytes, 64_198_656)
        self.assertEqual(twelve.one_step_output_bytes, 5_971_968)
        self.assertEqual(twelve.nominal_minibatch_uint8_bytes, 47_775_744)
        self.assertEqual(twelve.nominal_minibatch_float32_bytes, 191_102_976)

    def test_storage_rejects_invalid_dimensions(self) -> None:
        for kwargs in (
            {"n_envs": 0},
            {"n_steps": True},
            {"channels_per_frame": -1},
            {"height": 0},
            {"width": 1.5},
            {"batch_size": 0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises((TypeError, ValueError)):
                    estimate_storage(contiguous_history(8), **kwargs)


def campaign_samples(
    campaign: str,
    *,
    baseline_peak: int = 2_000_000_000,
    target_peak: int = 2_400_000_000,
    baseline_fps: float = 100.0,
    target_fps: float = 80.0,
    repeats: int = 3,
) -> list[ProfileRepeat]:
    candidates = (
        PRIMARY_CANDIDATES if campaign == PRIMARY_CAMPAIGN else FALLBACK_CANDIDATES
    )
    target = (
        TWELVE_MULTISCALE_CANDIDATE
        if campaign == PRIMARY_CAMPAIGN
        else TEN_MULTISCALE_CANDIDATE
    )
    samples = []
    for repeat in range(repeats):
        for candidate in candidates:
            samples.append(
                ProfileRepeat(
                    candidate=candidate,
                    repeat=repeat,
                    peak_working_set_bytes=(
                        target_peak if candidate == target else baseline_peak
                    ),
                    end_to_end_fps=(
                        target_fps if candidate == target else baseline_fps
                    ),
                    valid=True,
                    batch_size=RECURRENT_BATCH_SIZE,
                    n_epochs=RECURRENT_EPOCHS,
                )
            )
    return samples


class TestPromotionContract(unittest.TestCase):
    def test_primary_and_fallback_targets_pass_the_same_gates(self) -> None:
        primary = evaluate_promotion(
            campaign_samples(PRIMARY_CAMPAIGN), campaign=PRIMARY_CAMPAIGN
        )
        fallback = evaluate_promotion(
            campaign_samples(FALLBACK_CAMPAIGN, repeats=4),
            campaign=FALLBACK_CAMPAIGN,
            expected_repeats=4,
        )

        for decision, target in (
            (primary, TWELVE_MULTISCALE_CANDIDATE),
            (fallback, TEN_MULTISCALE_CANDIDATE),
        ):
            self.assertEqual(decision.target, target)
            self.assertTrue(decision.eligible)
            self.assertTrue(decision.complete)
            self.assertTrue(decision.all_valid)
            self.assertTrue(decision.settings_match)
            self.assertTrue(decision.relative_memory_passed)
            self.assertTrue(decision.historical_memory_passed)
            self.assertTrue(decision.throughput_passed)
            self.assertTrue(decision.promoted)
            self.assertEqual(decision.reasons, ())

        with self.assertRaises(ValueError):
            evaluate_promotion(
                campaign_samples(FALLBACK_CAMPAIGN),
                campaign=FALLBACK_CAMPAIGN,
                expected_repeats=3,
            )

    def test_relative_memory_and_throughput_equality_pass_but_cap_is_strict(
        self,
    ) -> None:
        equality = campaign_samples(
            PRIMARY_CAMPAIGN,
            baseline_peak=2_000_000_000,
            target_peak=2_500_000_000,
            baseline_fps=100.0,
            target_fps=75.0,
        )
        decision = evaluate_promotion(equality, campaign=PRIMARY_CAMPAIGN)
        self.assertTrue(decision.relative_memory_passed)
        self.assertTrue(decision.throughput_passed)
        self.assertTrue(decision.promoted)

        cap_equality = campaign_samples(
            PRIMARY_CAMPAIGN,
            baseline_peak=HISTORICAL_WORKING_SET_CAP_BYTES // 2,
            target_peak=HISTORICAL_WORKING_SET_CAP_BYTES,
        )
        decision = evaluate_promotion(cap_equality, campaign=PRIMARY_CAMPAIGN)
        self.assertFalse(decision.historical_memory_passed)
        self.assertFalse(decision.promoted)

    def test_missing_duplicate_invalid_and_setting_drift_fail_closed(self) -> None:
        complete = campaign_samples(PRIMARY_CAMPAIGN)
        cases = (
            ("missing", complete[:-1], "campaign-incomplete"),
            ("duplicate", [*complete, complete[0]], "campaign-incomplete"),
            (
                "invalid",
                [
                    sample
                    if index
                    else ProfileRepeat(
                        sample.candidate,
                        sample.repeat,
                        sample.peak_working_set_bytes,
                        sample.end_to_end_fps,
                        False,
                        sample.batch_size,
                        sample.n_epochs,
                    )
                    for index, sample in enumerate(complete)
                ],
                "repeat-invalid",
            ),
            (
                "batch-drift",
                [
                    sample
                    if index
                    else ProfileRepeat(
                        sample.candidate,
                        sample.repeat,
                        sample.peak_working_set_bytes,
                        sample.end_to_end_fps,
                        sample.valid,
                        32,
                        sample.n_epochs,
                    )
                    for index, sample in enumerate(complete)
                ],
                "settings-mismatch",
            ),
            (
                "epoch-drift",
                [
                    sample
                    if index
                    else ProfileRepeat(
                        sample.candidate,
                        sample.repeat,
                        sample.peak_working_set_bytes,
                        sample.end_to_end_fps,
                        sample.valid,
                        sample.batch_size,
                        3,
                    )
                    for index, sample in enumerate(complete)
                ],
                "settings-mismatch",
            ),
        )

        for name, samples, reason in cases:
            with self.subTest(name=name):
                decision = evaluate_promotion(samples, campaign=PRIMARY_CAMPAIGN)
                self.assertFalse(decision.promoted)
                self.assertEqual(decision.reasons, (reason,))
                self.assertEqual(
                    (
                        decision.baseline_median_peak_bytes,
                        decision.target_median_peak_bytes,
                        decision.baseline_median_fps,
                        decision.target_median_fps,
                    ),
                    (None, None, None, None),
                )
                self.assertFalse(decision.relative_memory_passed)
                self.assertFalse(decision.historical_memory_passed)
                self.assertFalse(decision.throughput_passed)

    def test_controls_and_cross_campaign_targets_are_ineligible(self) -> None:
        primary = campaign_samples(PRIMARY_CAMPAIGN)
        for target in (
            BASELINE_CANDIDATE,
            EIGHT_MULTISCALE_CANDIDATE,
            TEN_MULTISCALE_CANDIDATE,
        ):
            with self.subTest(target=target):
                decision = evaluate_promotion(
                    primary,
                    campaign=PRIMARY_CAMPAIGN,
                    target=target,
                )
                self.assertFalse(decision.eligible)
                self.assertFalse(decision.promoted)
                self.assertEqual(decision.reasons, ("target-ineligible",))
                self.assertIsNone(decision.target_median_peak_bytes)
                self.assertIsNone(decision.target_median_fps)

    def test_repeat_contract_rejects_unknown_indices_and_bad_measurements(self) -> None:
        with self.assertRaises((TypeError, ValueError)):
            ProfileRepeat("candidate", -1, 1, 1.0, True, 64, 4)
        with self.assertRaises((TypeError, ValueError)):
            ProfileRepeat("candidate", 0, 0, 1.0, True, 64, 4)
        with self.assertRaises((TypeError, ValueError)):
            ProfileRepeat("candidate", 0, 1, float("nan"), True, 64, 4)


class TestMacContract(unittest.TestCase):
    def test_published_formulas_are_exact_and_immutable(self) -> None:
        self.assertEqual(
            MAC_FORMULAS,
            {
                "conv2d": "output_height * output_width * out_channels * (in_channels / groups) * kernel_height * kernel_width",
                "linear": "in_features * out_features",
                "lstm": "directions * 4 * hidden_size * (layer_input_size + hidden_size) per layer",
            },
        )
        with self.assertRaises(TypeError):
            MAC_FORMULAS["linear"] = "changed"  # type: ignore[index]

    def test_layer_formula_helpers_are_exact_and_validate_inputs(self) -> None:
        self.assertEqual(conv2d_output_size(108, kernel=8, stride=4, padding=2), 27)
        self.assertEqual(conv2d_output_size(192, kernel=8, stride=4, padding=2), 48)
        self.assertEqual(
            conv2d_macs(
                in_channels=24,
                out_channels=32,
                output_height=27,
                output_width=48,
                kernel_height=8,
                kernel_width=8,
            ),
            63_700_992,
        )
        self.assertEqual(linear_macs(960, 256), 245_760)
        self.assertEqual(lstm_macs(256, 256), 524_288)
        for call in (
            lambda: conv2d_output_size(0, kernel=3),
            lambda: linear_macs(True, 64),
            lambda: lstm_macs(256, -1),
        ):
            with self.assertRaises((TypeError, ValueError)):
                call()

    def test_full_estimate_models_live_shared_cnn_and_recurrent_heads(self) -> None:
        eight = estimate_inference_macs(contiguous_history(8))
        twelve = estimate_inference_macs(
            PRIMARY_CANDIDATES[TWELVE_MULTISCALE_CANDIDATE]
        )

        self.assertEqual(eight.cnn_convolutions, 77_021_184)
        self.assertEqual(eight.cnn_projection, 245_760)
        self.assertEqual(eight.actor_lstm, 524_288)
        self.assertEqual(eight.critic_lstm, 524_288)
        self.assertEqual(eight.actor_mlp, 20_480)
        self.assertEqual(eight.critic_mlp, 20_480)
        self.assertEqual(eight.action_head, 19_712)
        self.assertEqual(eight.value_head, 64)
        self.assertEqual(eight.total, 78_376_256)
        self.assertEqual(twelve.total, 110_226_752)
        self.assertEqual(twelve.total - eight.total, 31_850_496)


if __name__ == "__main__":
    unittest.main()
