from __future__ import annotations

import hashlib
import os
import sys
import unittest
from dataclasses import FrozenInstanceError

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.history import (
    CONTIGUOUS_HISTORY_LAYOUT,
    DECISION_HISTORY_LAYOUT,
    EIGHT_MULTISCALE_HISTORY_LAYOUT,
    NAMED_HISTORY_LAYOUTS,
    TEN_MULTISCALE_HISTORY_LAYOUT,
    HistoryDescriptor,
    canonical_history_bytes,
    contiguous_history,
    history_for_layout,
)


class TestHistoryDescriptor(unittest.TestCase):
    def test_contiguous_history_is_immutable_canonical_and_fingerprinted(self) -> None:
        history = contiguous_history(4)
        expected = (
            b'{"channelOrder":"sample-major-channel-first-rgb",'
            b'"layout":"contiguous-history-v1","offsetUnit":"agent-decisions",'
            b'"prehistoryFill":"zeros",'
            b'"resetBehavior":"clear-then-insert-initial",'
            b'"sampleOffsets":[3,2,1,0],"sampleOrder":"oldest-to-newest",'
            b'"schema":"mini-metro-observation-history-v1",'
            b'"terminalBehavior":"append-terminal-copy-before-autoreset"}\n'
        )

        self.assertEqual(history.layout, CONTIGUOUS_HISTORY_LAYOUT)
        self.assertEqual(history.offsets, (3, 2, 1, 0))
        self.assertEqual(history.frame_stack, 4)
        self.assertEqual(canonical_history_bytes(history), expected)
        self.assertEqual(history.fingerprint(), hashlib.sha256(expected).hexdigest())
        with self.assertRaises(FrozenInstanceError):
            history.layout = DECISION_HISTORY_LAYOUT

    def test_named_layouts_pin_the_reviewed_offsets(self) -> None:
        self.assertEqual(
            NAMED_HISTORY_LAYOUTS,
            (
                DECISION_HISTORY_LAYOUT,
                EIGHT_MULTISCALE_HISTORY_LAYOUT,
                TEN_MULTISCALE_HISTORY_LAYOUT,
            ),
        )
        self.assertEqual(
            history_for_layout(DECISION_HISTORY_LAYOUT).offsets,
            (128, 64, 32, 16, 7, 6, 5, 4, 3, 2, 1, 0),
        )
        self.assertEqual(
            history_for_layout(EIGHT_MULTISCALE_HISTORY_LAYOUT).offsets,
            (128, 64, 32, 16, 3, 2, 1, 0),
        )
        self.assertEqual(
            history_for_layout(TEN_MULTISCALE_HISTORY_LAYOUT).offsets,
            (128, 64, 7, 6, 5, 4, 3, 2, 1, 0),
        )

    def test_equal_frame_counts_do_not_imply_equal_history_identity(self) -> None:
        contiguous = contiguous_history(12)
        multiscale = history_for_layout(DECISION_HISTORY_LAYOUT)

        self.assertEqual(contiguous.frame_stack, multiscale.frame_stack)
        self.assertNotEqual(contiguous, multiscale)
        self.assertNotEqual(contiguous.fingerprint(), multiscale.fingerprint())

    def test_rejects_invalid_offsets_and_unsupported_layouts(self) -> None:
        invalid = (
            (CONTIGUOUS_HISTORY_LAYOUT, ()),
            (CONTIGUOUS_HISTORY_LAYOUT, (True, 0)),
            (CONTIGUOUS_HISTORY_LAYOUT, (2, 2, 0)),
            (CONTIGUOUS_HISTORY_LAYOUT, (0, 1)),
            (CONTIGUOUS_HISTORY_LAYOUT, (2, 1)),
            (CONTIGUOUS_HISTORY_LAYOUT, (2, -1, 0)),
            (CONTIGUOUS_HISTORY_LAYOUT, (2, 0)),
            (DECISION_HISTORY_LAYOUT, (11, 10, 0)),
            ("unreviewed-history-v1", (0,)),
        )
        for layout, offsets in invalid:
            with self.subTest(layout=layout, offsets=offsets):
                with self.assertRaises((TypeError, ValueError)):
                    HistoryDescriptor(layout, offsets)

        for value in (0, -1, True, 1.5):
            with self.subTest(frame_stack=value):
                with self.assertRaises((TypeError, ValueError)):
                    contiguous_history(value)

    def test_parser_requires_exact_keys_and_fixed_semantics(self) -> None:
        document = contiguous_history(4).to_dict()
        self.assertEqual(HistoryDescriptor.from_dict(document), contiguous_history(4))

        cases = []
        missing = dict(document)
        missing.pop("sampleOrder")
        cases.append(missing)
        unknown = dict(document)
        unknown["future"] = "ignored"
        cases.append(unknown)
        tampered = dict(document)
        tampered["sampleOrder"] = "newest-to-oldest"
        cases.append(tampered)
        wrong_offsets_type = dict(document)
        wrong_offsets_type["sampleOffsets"] = (3, 2, 1, 0)
        cases.append(wrong_offsets_type)

        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises((TypeError, ValueError)):
                    HistoryDescriptor.from_dict(case)


if __name__ == "__main__":
    unittest.main()
