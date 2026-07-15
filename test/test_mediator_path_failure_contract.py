from unittest.mock import MagicMock, patch

import mediator as mediator_module
from test import mediator_test_support as support
from test.path_lifecycle_test_support import path_through

# isort: split

from geometry.point import Point
from mediator import Mediator


class TestMediatorPathFailureContract(support.MediatorTestCase):
    def test_start_uses_black_when_only_locked_color_is_free(self):
        mediator = Mediator(seed=0)
        colors = list(mediator.path_colors)
        mediator.unlocked_num_paths = 2
        mediator.path_colors = dict(zip(colors, [True, True, False, False]))

        mediator.start_path_on_station(mediator.stations[0])

        draft = mediator.path_being_created
        assert draft is not None
        self.assertEqual(draft.color, (0, 0, 0))
        self.assertEqual(mediator.path_to_color[draft], (0, 0, 0))
        self.assertFalse(mediator.path_colors[colors[2]])

    def test_remove_path_by_index_re_reads_paths_after_bounds_check(self):
        mediator = Mediator(seed=0)
        stale_paths = [
            path_through(*mediator.stations[:2]),
            path_through(*mediator.stations[1:3]),
        ]
        rebound_paths = [
            path_through(*mediator.stations[2:4]),
            path_through(*mediator.stations[3:5]),
        ]

        class LengthRebindingPaths(list):
            def __len__(self):
                mediator.paths = rebound_paths
                return super().__len__()

        mediator.paths = LengthRebindingPaths(stale_paths)
        mediator.remove_path = MagicMock()

        self.assertTrue(mediator.remove_path_by_index(1))

        removed = mediator.remove_path.call_args.args[0]
        self.assertIs(removed, rebound_paths[1])
        self.assertIs(mediator.paths, rebound_paths)

    def test_abort_re_reads_draft_and_paths_after_release_hook(self):
        mediator = Mediator(seed=0)
        mediator.start_path_on_station(mediator.stations[0])
        original = mediator.path_being_created
        assert original is not None
        original_paths = mediator.paths
        replacement = path_through(mediator.stations[1])
        rebound_paths = [replacement]
        released = []
        original_release = mediator.release_color_for_path

        def release(path):
            released.append((path, mediator.is_creating_path))
            original_release(path)
            mediator.path_being_created = replacement
            mediator.paths = rebound_paths

        mediator.release_color_for_path = release

        mediator.abort_path_creation()

        self.assertIs(released[0][0], original)
        self.assertFalse(released[0][1])
        self.assertEqual(original_paths, [original])
        self.assertEqual(rebound_paths, [])
        self.assertIsNone(mediator.path_being_created)

    def test_finish_resolves_rebound_assignment_after_metro_installation(self):
        mediator = Mediator(seed=0)
        mediator.start_path_on_station(mediator.stations[0])
        mediator.add_station_to_path(mediator.stations[1])
        path = mediator.path_being_created
        assert path is not None
        events = []

        def late_assign():
            events.append(
                (
                    mediator.path_being_created,
                    tuple(path.metros),
                    tuple(mediator.metros),
                )
            )

        class AssignmentRebindingMetros(list):
            def append(self, metro):
                super().append(metro)
                mediator.assign_paths_to_buttons = late_assign

        mediator.metros = AssignmentRebindingMetros()
        early_assign = MagicMock(
            side_effect=AssertionError(
                "assignment hook resolved before metro installation"
            )
        )
        mediator.assign_paths_to_buttons = early_assign

        mediator.finish_path_creation()

        early_assign.assert_not_called()
        metro = mediator.metros[0]
        self.assertIs(path.metros[0], metro)
        self.assertEqual(events, [(None, (metro,), (metro,))])

    def test_programmatic_creation_uses_captured_path_and_current_paths(self):
        mediator = Mediator(seed=0)
        captured = path_through(mediator.stations[0])
        captured.is_being_created = True
        replacement = path_through(mediator.stations[1])
        replacement.is_being_created = True
        paths_after_start = [replacement]
        paths_after_end = [captured]
        events = []

        def start(_station):
            events.append("start")
            mediator.path_being_created = captured
            mediator.paths = paths_after_start

        def add(_station):
            events.append("add")

        def end(_station):
            events.append("end")
            captured.is_being_created = False
            mediator.path_being_created = replacement
            mediator.paths = paths_after_end

        mediator.paths = []
        mediator.start_path_on_station = start
        mediator.add_station_to_path = add
        mediator.end_path_on_station = end

        created = mediator.create_path_from_station_indices([0, 1, 2])

        self.assertIs(created, captured)
        self.assertEqual(events, ["start", "add", "end"])
        self.assertIs(mediator.paths, paths_after_end)
        self.assertIs(mediator.path_being_created, replacement)

    def test_path_factory_exception_preserves_claimed_partial_state(self):
        mediator = Mediator(seed=0)
        claimed_color = next(
            color for color, taken in mediator.path_colors.items() if not taken
        )
        error = RuntimeError("path factory failure")
        snapshot = {}

        def failing_factory(color):
            snapshot["state"] = (
                color,
                mediator.is_creating_path,
                mediator.path_colors[color],
                dict(mediator.path_to_color),
                mediator.path_being_created,
                tuple(mediator.paths),
            )
            raise error

        with patch.object(mediator_module, "Path", failing_factory):
            with self.assertRaises(RuntimeError) as raised:
                mediator.start_path_on_station(mediator.stations[0])

        self.assertIs(raised.exception, error)
        self.assertEqual(snapshot["state"], (claimed_color, True, True, {}, None, ()))
        self.assertTrue(mediator.is_creating_path)
        self.assertTrue(mediator.path_colors[claimed_color])
        self.assertEqual(mediator.path_to_color, {})
        self.assertIsNone(mediator.path_being_created)
        self.assertEqual(mediator.paths, [])

    def test_metro_factory_exception_preserves_cleaned_partial_state(self):
        mediator = Mediator(seed=0)
        mediator.start_path_on_station(mediator.stations[0])
        mediator.add_station_to_path(mediator.stations[1])
        path = mediator.path_being_created
        assert path is not None
        path.set_temporary_point(Point(12, 34))
        error = LookupError("metro factory failure")
        snapshot = {}
        mediator.assign_paths_to_buttons = MagicMock()

        def failing_factory():
            snapshot["state"] = (
                mediator.is_creating_path,
                path.is_being_created,
                path.temp_point,
                mediator.path_being_created,
                tuple(path.metros),
                tuple(mediator.metros),
            )
            raise error

        with patch.object(mediator_module, "Metro", failing_factory):
            with self.assertRaises(LookupError) as raised:
                mediator.finish_path_creation()

        self.assertIs(raised.exception, error)
        state = snapshot["state"]
        self.assertEqual(state[:3], (False, False, None))
        self.assertIs(state[3], path)
        self.assertEqual(state[4:], ((), ()))
        self.assertFalse(mediator.is_creating_path)
        self.assertFalse(path.is_being_created)
        self.assertIsNone(path.temp_point)
        self.assertIs(mediator.path_being_created, path)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        mediator.assign_paths_to_buttons.assert_not_called()
