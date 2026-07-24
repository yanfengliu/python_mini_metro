"""A cancelled path draft must leave NO trace (GM-09c follow-up, task_384488d0).

Two pre-existing non-inert side effects of ``abort_path_creation`` are locked here:

* the transient snap-blips a draft paints as it grows must be dropped on abort, so
  a headless/structured rollout never checkpoints a rejected creation's blips -- and
  the removal must target the draft's OWN blips (matched by last-recorded value), not
  by color (a draft can reclaim a removed line's freed color while that line's blips
  still linger, so a color match would wrongly erase the survivor's blip);
* a draft that a mid-draft ``remove_path`` bound to a path button must be unbound on
  abort, so no colored button points at a removed line.

CLASSIC's frozen fixtures never abort a drag, so these fixes cannot move them; the
byte-identity guard lives in the GM-09a/GM-07b determinism suites.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import button_color
from env import MiniMetroEnv
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint


def _cbytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


class TestAbortSnapBlipInertness(unittest.TestCase):
    def test_classic_drag_then_cancel_is_fully_checkpoint_inert(self):
        # The whole canonical checkpoint before the draft and after the abort must be
        # byte-identical: building-then-aborting draws no RNG (empirically verified),
        # so once the draft's snap-blips are dropped, abort is a complete no-op.
        env = MiniMetroEnv(dt_ms=17)
        env.reset(seed=0)
        mediator = env.mediator
        before = _cbytes(canonical_checkpoint(env))

        mediator.start_path_on_station(mediator.stations[0])
        mediator.add_station_to_path(mediator.stations[1])
        mediator.add_station_to_path(mediator.stations[2])
        # the drag paints transient blips on every station it snaps
        self.assertTrue(mediator.stations[1].snap_blips)
        self.assertTrue(mediator.stations[2].snap_blips)

        mediator.abort_path_creation()

        self.assertEqual(mediator.stations[1].snap_blips, [], "draft blip dropped")
        self.assertEqual(mediator.stations[2].snap_blips, [], "draft blip dropped")
        self.assertEqual(
            before,
            _cbytes(canonical_checkpoint(env)),
            "a cancelled draft is fully checkpoint-inert",
        )

    def test_abort_removes_only_the_drafts_own_blips_not_a_reclaimed_colors(self):
        # A removed line's snap-blip lingers on its stations; a later draft reclaims
        # the freed color. Abort must drop the DRAFT's own blip and leave the removed
        # line's identically-colored survivor untouched -- a color match would erase
        # both (the regression the GM-09c re-review flagged).
        mediator = Mediator(seed=0)
        mediator.unlocked_num_paths = 3

        mediator.time_ms = 100
        line = mediator.create_path_from_station_indices([0, 1, 2])
        self.assertIsNotNone(line)
        color = line.color
        self.assertEqual(mediator.stations[1].snap_blips, [(100, color)])
        self.assertEqual(mediator.stations[2].snap_blips, [(100, color)])

        mediator.remove_path(line)  # frees `color`; the two blips linger
        self.assertEqual(mediator.stations[1].snap_blips, [(100, color)])

        mediator.time_ms = 200
        mediator.start_path_on_station(mediator.stations[0])
        draft = mediator.path_being_created
        assert draft is not None
        self.assertEqual(draft.color, color, "the draft reclaimed the freed color")
        mediator.add_station_to_path(mediator.stations[1])
        self.assertEqual(mediator.stations[1].snap_blips, [(100, color), (200, color)])

        mediator.abort_path_creation()

        # only the draft's (200, color) blip is gone; the removed line's (100, color)
        # survivor stays -- and station 2, which the draft never snapped, is untouched.
        self.assertEqual(mediator.stations[1].snap_blips, [(100, color)])
        self.assertEqual(mediator.stations[2].snap_blips, [(100, color)])

    def test_multi_station_draft_abort_drops_every_blip_it_painted(self):
        # Duplicate-station drafts snap a station more than once; abort must drop each
        # painted blip, not just the first.
        mediator = Mediator(seed=0)
        mediator.unlocked_num_paths = 3
        mediator.time_ms = 10
        mediator.start_path_on_station(mediator.stations[0])
        mediator.add_station_to_path(mediator.stations[1])
        mediator.time_ms = 20
        mediator.add_station_to_path(mediator.stations[2])
        mediator.time_ms = 30
        mediator.add_station_to_path(mediator.stations[1])  # re-snap -> second blip
        self.assertEqual(len(mediator.stations[1].snap_blips), 2)

        mediator.abort_path_creation()

        for station in mediator.stations:
            self.assertEqual(station.snap_blips, [], "no painted blip survives abort")

    def test_abort_drops_the_drafts_blip_amid_identical_survivors_preserving_order(
        self,
    ):
        # Adversarial ordering: a removed line and the draft both snap ONE station at
        # the SAME time with the SAME reclaimed color, on either side of a differently
        # colored survivor. The draft's blip is appended LAST, so abort must drop the
        # tail match; dropping the FIRST value-match would erase the removed line's
        # blip and reorder the survivor list.
        mediator = Mediator(seed=0)
        mediator.unlocked_num_paths = 4
        mediator.time_ms = 0
        line_l = mediator.create_path_from_station_indices([0, 1])
        assert line_l is not None
        c0 = line_l.color
        line_m = mediator.create_path_from_station_indices([2, 1])
        assert line_m is not None
        c1 = line_m.color
        self.assertNotEqual(c0, c1)
        self.assertEqual(mediator.stations[1].snap_blips, [(0, c0), (0, c1)])

        mediator.remove_path(line_l)  # frees c0; its (0, c0) blip lingers at index 0
        mediator.start_path_on_station(mediator.stations[0])
        draft = mediator.path_being_created
        assert draft is not None
        self.assertEqual(draft.color, c0, "the draft reclaimed the removed line's c0")
        mediator.add_station_to_path(mediator.stations[1])  # appends (0, c0) at tail
        self.assertEqual(mediator.stations[1].snap_blips, [(0, c0), (0, c1), (0, c0)])

        mediator.abort_path_creation()

        # the draft's tail (0, c0) is gone; the removed line's leading (0, c0) and the
        # survivor (0, c1) keep their original order.
        self.assertEqual(mediator.stations[1].snap_blips, [(0, c0), (0, c1)])


class TestAbortButtonReconciliation(unittest.TestCase):
    def test_abort_after_mid_draft_removal_leaves_no_ghost_button(self):
        # A remove_path mid-draft runs assign_paths_to_buttons, which binds the still
        # drafting path to a button. Abort must unbind it, or a colored button points
        # at a line that no longer exists.
        mediator = Mediator(seed=0)
        mediator.unlocked_num_paths = 3
        committed = mediator.create_path_from_station_indices([0, 1])
        self.assertIsNotNone(committed)

        mediator.start_path_on_station(mediator.stations[2])
        draft = mediator.path_being_created
        assert draft is not None
        mediator.remove_path(committed)  # binds the draft to a button
        self.assertIn(draft, mediator.path_to_button, "setup: draft is bound")
        bound_button = mediator.path_to_button[draft]
        self.assertIs(bound_button.path, draft)

        mediator.abort_path_creation()

        self.assertNotIn(draft, mediator.path_to_button, "no ghost mapping")
        self.assertIsNone(bound_button.path, "button no longer points at the draft")
        self.assertIsNone(bound_button.cross, "button's removal cross is cleared")
        self.assertEqual(bound_button.shape.color, button_color, "button de-colored")
        self.assertFalse(
            [b for b in mediator.path_buttons if b.path is draft],
            "no button references the removed draft",
        )
        self.assertEqual(mediator.paths, [], "both the committed line and draft gone")

    def test_plain_abort_without_a_bound_button_touches_no_button(self):
        # The common path: an ordinary drag-then-cancel never bound the draft, so
        # abort must not disturb any button (guards the no-button-reassign contract).
        mediator = Mediator(seed=0)
        mediator.start_path_on_station(mediator.stations[0])
        draft = mediator.path_being_created
        assert draft is not None
        colors_before = [b.shape.color for b in mediator.path_buttons]
        paths_before = [b.path for b in mediator.path_buttons]

        mediator.abort_path_creation()

        self.assertNotIn(draft, mediator.path_to_button)
        self.assertEqual([b.shape.color for b in mediator.path_buttons], colors_before)
        self.assertEqual([b.path for b in mediator.path_buttons], paths_before)


if __name__ == "__main__":
    unittest.main()
