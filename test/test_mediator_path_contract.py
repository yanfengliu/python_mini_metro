import inspect
from unittest.mock import MagicMock

from test import mediator_test_support as support
from test.path_lifecycle_test_support import (
    ExplodingNodes,
    IntSubclass,
    LoggingList,
    LoggingPlans,
    assert_late_path_factory,
    path_through,
)

# isort: split

from config import station_color, station_size
from entity.metro import Metro
from entity.passenger import Passenger
from entity.station import Station
from env import MiniMetroEnv
from geometry.circle import Circle
from geometry.point import Point
from graph.graph_algo import build_station_nodes_dict
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from travel_plan import TravelPlan


class TestMediatorPathContract(support.MediatorTestCase):
    def test_public_lifecycle_signatures_are_frozen(self):
        expected = {
            "assign_paths_to_buttons": "(self) -> 'None'",
            "remove_path": "(self, path: 'Path') -> 'None'",
            "invalidate_travel_plans_for_path": "(self, path: 'Path') -> 'None'",
            "remove_path_by_id": "(self, path_id: 'str') -> 'bool'",
            "remove_path_by_index": "(self, path_index: 'int') -> 'bool'",
            "start_path_on_station": "(self, station: 'Station') -> 'None'",
            "create_path_from_station_indices": "(self, station_indices: 'List[int]', loop: 'bool' = False) -> 'Path | None'",
            "add_station_to_path": "(self, station: 'Station') -> 'None'",
            "abort_path_creation": "(self) -> 'None'",
            "release_color_for_path": "(self, path: 'Path') -> 'None'",
            "finish_path_creation": "(self) -> 'None'",
            "end_path_on_station": "(self, station: 'Station') -> 'None'",
        }

        self.assertEqual(
            {
                name: str(inspect.signature(getattr(Mediator, name)))
                for name in expected
            },
            expected,
        )

    def test_button_assignment_replaces_mapping_after_all_clears(self):
        mediator = Mediator(seed=0)
        first = path_through(*mediator.stations[:2])
        second = path_through(*mediator.stations[1:3])
        mediator.paths = [first, second]
        mediator.path_buttons = mediator.path_buttons[:2]
        old_mapping = {first: mediator.path_buttons[0]}
        mediator.path_to_button = old_mapping
        events = []

        for index, button in enumerate(mediator.path_buttons):
            button.remove_path = MagicMock(
                side_effect=lambda index=index: events.append(
                    ("clear", index, mediator.path_to_button is old_mapping)
                )
            )
            button.assign_path = MagicMock(
                side_effect=lambda path, index=index: events.append(
                    ("assign", index, tuple(mediator.path_to_button))
                )
            )
        mediator.update_path_button_lock_states = MagicMock(
            side_effect=lambda: events.append(("locks", tuple(mediator.path_to_button)))
        )

        mediator.assign_paths_to_buttons()

        self.assertEqual(
            events,
            [
                ("clear", 0, True),
                ("clear", 1, True),
                ("assign", 0, ()),
                ("assign", 1, (first,)),
                ("locks", (first, second)),
            ],
        )
        self.assertIsNot(mediator.path_to_button, old_mapping)
        self.assertEqual(old_mapping, {first: mediator.path_buttons[0]})

    def test_removal_order_snapshots_and_detached_graph_are_preserved(self):
        mediator = Mediator(seed=0)
        path = path_through(*mediator.stations[:2])
        metros = [Metro(), Metro()]
        passengers = [Passenger(mediator.stations[1].shape) for _ in metros]
        for metro, passenger in zip(metros, passengers):
            path.add_metro(metro)
            metro.add_passenger(passenger)
        late_metro = Metro()
        late_passenger = Passenger(mediator.stations[1].shape)
        events = []
        names = {
            id(path): "path",
            id(metros[0]): "metro-0",
            id(metros[1]): "metro-1",
            id(late_metro): "late-metro",
            id(passengers[0]): "passenger-0",
            id(passengers[1]): "passenger-1",
            id(late_passenger): "late-passenger",
        }

        def mutate_snapshotted_sources(value):
            if value is passengers[0]:
                path.metros.append(late_metro)
                metros[0].passengers.append(late_passenger)

        mediator.paths = LoggingList([path], "path", names, events)
        mediator.metros = LoggingList(metros, "metro", names, events)
        mediator.passengers = LoggingList(
            passengers, "passenger", names, events, mutate_snapshotted_sources
        )
        mediator.travel_plans = LoggingPlans(
            {passenger: TravelPlan([]) for passenger in passengers}, names, events
        )
        button = mediator.path_buttons[0]
        button.remove_path = MagicMock(side_effect=lambda: events.append("button"))
        mediator.path_to_button = {path: button}
        mediator.invalidate_travel_plans_for_path = MagicMock(
            side_effect=lambda _path: events.append("invalidate")
        )
        mediator.release_color_for_path = MagicMock(
            side_effect=lambda _path: events.append("release")
        )
        mediator.assign_paths_to_buttons = MagicMock(
            side_effect=lambda: events.append("assign")
        )
        mediator.find_travel_plan_for_passengers = MagicMock(
            side_effect=lambda: events.append("replan")
        )

        mediator.remove_path(path)

        self.assertEqual(
            events,
            [
                "button",
                "passenger:passenger-0",
                "plan:passenger-0",
                "metro:metro-0",
                "passenger:passenger-1",
                "plan:passenger-1",
                "metro:metro-1",
                "invalidate",
                "release",
                "path:path",
                "assign",
                "replan",
            ],
        )
        self.assertEqual(path.metros, [*metros, late_metro])
        self.assertEqual(metros[0].passengers, [passengers[0], late_passenger])
        self.assertEqual(metros[1].passengers, [passengers[1]])
        self.assertEqual(mediator.metros, [])
        self.assertEqual(mediator.passengers, [])

    def test_removal_re_resolves_public_hooks_and_rebound_collections(self):
        mediator = Mediator(seed=0)
        path = path_through(*mediator.stations[:2])
        old_paths = [path]
        rebound_paths = [path]
        mediator.paths = old_paths
        mediator.path_to_color = {path: path.color}
        mediator.path_colors = {path.color: True}
        button = mediator.path_buttons[0]
        button.remove_path = MagicMock()
        mediator.path_to_button = {path: button}
        events = []

        def late_assign():
            events.append("assign")
            mediator.find_travel_plan_for_passengers = lambda: events.append("replan")

        def late_release(removed):
            events.append("release")
            Mediator.release_color_for_path(mediator, removed)
            mediator.paths = rebound_paths
            mediator.assign_paths_to_buttons = late_assign

        def invalidate(_removed):
            events.append("invalidate")
            mediator.release_color_for_path = late_release

        mediator.invalidate_travel_plans_for_path = invalidate
        mediator.release_color_for_path = MagicMock(
            side_effect=AssertionError("early release hook")
        )
        mediator.assign_paths_to_buttons = MagicMock(
            side_effect=AssertionError("early assign hook")
        )
        mediator.find_travel_plan_for_passengers = MagicMock(
            side_effect=AssertionError("early replan hook")
        )

        mediator.remove_path(path)

        self.assertEqual(events, ["invalidate", "release", "assign", "replan"])
        self.assertEqual(old_paths, [path])
        self.assertEqual(rebound_paths, [])

    def test_invalidation_short_circuits_and_deletes_from_rebound_plan_map(self):
        mediator = Mediator(seed=0)
        start, end = mediator.stations[:2]
        surviving_path = path_through(start, end)
        removed_path = path_through(start, end, color=(40, 50, 60))
        metro = Metro()
        surviving_path.add_metro(metro)
        passenger = Passenger(end.shape)
        metro.add_passenger(passenger)
        plan = TravelPlan([])
        plan.next_path = surviving_path
        plan.node_path = ExplodingNodes()
        mediator.metros = [metro]
        mediator.travel_plans = {passenger: plan}

        mediator.invalidate_travel_plans_for_path(removed_path)

        self.assertIs(mediator.travel_plans[passenger], plan)

        removable = Passenger(end.shape)
        removable_plan = TravelPlan([])
        removable_plan.next_path = removed_path
        rebound = {removable: removable_plan}

        class RebindingPlans(dict):
            def items(self):
                result = super().items()
                mediator.travel_plans = rebound
                return result

        original = RebindingPlans({removable: removable_plan})
        mediator.metros = []
        mediator.travel_plans = original
        mediator.invalidate_travel_plans_for_path(removed_path)

        self.assertIn(removable, original)
        self.assertNotIn(removable, rebound)

    def test_path_factory_is_resolved_after_color_claim_and_keeps_identity(self):
        assert_late_path_factory(self, Mediator(seed=0))

    def test_completed_path_stays_unserved_until_explicit_assignment(self):
        mediator = Mediator(seed=0)
        mediator.start_path_on_station(mediator.stations[0])
        mediator.add_station_to_path(mediator.stations[1])
        path = mediator.path_being_created
        assert path is not None

        mediator.finish_path_creation()

        self.assertIsNone(mediator.path_being_created)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assertTrue(mediator.assign_locomotive(path))
        self.assertIs(path.metros[0], mediator.metros[0])

    def test_creation_hooks_and_station_transitions_remain_live_and_ordered(self):
        mediator = Mediator(seed=0)
        events = []
        original_start = mediator.start_path_on_station
        original_add = mediator.add_station_to_path
        original_end = mediator.end_path_on_station

        def end(station):
            events.append("end")
            original_end(station)

        def add(station):
            events.append("add")
            original_add(station)
            mediator.end_path_on_station = end

        def start(station):
            events.append("start")
            original_start(station)
            mediator.add_station_to_path = add

        mediator.start_path_on_station = start
        created = mediator.create_path_from_station_indices([0, 1, 2])

        self.assertEqual(events, ["start", "add", "end"])
        self.assertIs(created, mediator.paths[0])

        closed_mediator = Mediator(seed=2)
        closed_first, closed_middle, closed_last = closed_mediator.stations[:3]
        closed_adds = []
        original_closed_add = closed_mediator.add_station_to_path

        def closed_add(station):
            closed_adds.append(station)
            original_closed_add(station)

        closed_mediator.add_station_to_path = closed_add
        closed_path = closed_mediator.create_path_from_station_indices(
            [0, 1, 2, 0], loop=True
        )

        self.assertIsNotNone(closed_path)
        self.assertEqual(closed_adds, [closed_middle, closed_last])
        self.assertEqual(
            closed_path.stations, [closed_first, closed_middle, closed_last]
        )
        self.assertTrue(closed_path.is_looped)
        self.assertEqual(closed_first.snap_blips, [])
        self.assertEqual(
            [len(closed_middle.snap_blips), len(closed_last.snap_blips)], [1, 1]
        )

        loop_mediator = Mediator(seed=1)
        first, middle, later = loop_mediator.stations[:3]
        loop_mediator.start_path_on_station(first)
        loop_mediator.add_station_to_path(middle)
        path = loop_mediator.path_being_created
        assert path is not None
        equal_first = Station(
            Circle(station_color, station_size), Point(first.position.left + 1, 0)
        )
        equal_first.id = first.id
        snapshots = []
        equal_first.start_snap_blip = lambda *_args: snapshots.append(
            (path.is_looped, tuple(path.stations), loop_mediator.path_being_created)
        )
        loop_mediator.add_station_to_path(equal_first)
        later.start_snap_blip = lambda *_args: snapshots.append(
            (path.is_looped, tuple(path.stations), loop_mediator.path_being_created)
        )
        loop_mediator.add_station_to_path(later)

        self.assertEqual(
            snapshots,
            [
                (True, (first, middle), path),
                (False, (first, middle, later), path),
            ],
        )

    def test_end_snap_precedes_dynamic_finish_and_abort_retains_draft_state(self):
        mediator = Mediator(seed=0)
        first, second = mediator.stations[:2]
        mediator.start_path_on_station(first)
        path = mediator.path_being_created
        assert path is not None
        events = []
        original_finish = mediator.finish_path_creation

        def late_finish():
            events.append("finish")
            original_finish()

        def snap(*_args):
            events.append(
                (
                    "snap",
                    mediator.is_creating_path,
                    path.is_being_created,
                    mediator.path_being_created is path,
                    tuple(path.stations),
                    tuple(mediator.metros),
                )
            )
            mediator.finish_path_creation = late_finish

        second.start_snap_blip = snap
        mediator.end_path_on_station(second)

        self.assertEqual(
            events,
            [("snap", True, True, True, (first, second), ()), "finish"],
        )
        self.assertFalse(path.is_being_created)
        self.assertIsNone(mediator.path_being_created)

        aborted = Mediator(seed=1)
        station = aborted.stations[0]
        aborted.start_path_on_station(station)
        draft = aborted.path_being_created
        assert draft is not None
        temporary_point = Point(12, 34)
        draft.set_temporary_point(temporary_point)
        release_state = []
        original_release = aborted.release_color_for_path

        def release(removed):
            release_state.append(
                (
                    aborted.is_creating_path,
                    aborted.path_being_created,
                    removed in aborted.paths,
                    removed.is_being_created,
                    removed.temp_point,
                )
            )
            original_release(removed)

        aborted.release_color_for_path = release
        aborted.end_path_on_station(station)

        self.assertEqual(release_state, [(False, draft, True, True, temporary_point)])
        self.assertNotIn(draft, aborted.paths)
        self.assertIsNone(aborted.path_being_created)
        self.assertTrue(draft.is_being_created)
        self.assertIs(draft.temp_point, temporary_point)

    def test_id_index_and_draft_graph_checkpoint_contracts(self):
        mediator = Mediator(seed=0)
        first = path_through(*mediator.stations[:2])
        second = path_through(*mediator.stations[1:3])
        first.id = second.id = "duplicate"
        mediator.paths = [first, second]
        mediator.remove_path = MagicMock()

        self.assertTrue(mediator.remove_path_by_id("duplicate"))
        mediator.remove_path.assert_called_once_with(first)
        mediator.remove_path.reset_mock()
        for invalid in (False, IntSubclass(0), -1, 2):
            with self.subTest(invalid=invalid):
                self.assertFalse(mediator.remove_path_by_index(invalid))
        mediator.remove_path.assert_not_called()
        self.assertTrue(mediator.remove_path_by_index(1))
        mediator.remove_path.assert_called_once_with(second)

        env = MiniMetroEnv()
        env.reset(seed=11)
        topology = env.mediator
        start, end = topology.stations[:2]
        topology.start_path_on_station(start)
        topology.add_station_to_path(end)
        draft = topology.path_being_created
        assert draft is not None
        draft_graph = build_station_nodes_dict(topology.stations, topology.paths)
        draft_checkpoint = canonical_checkpoint(env)["topology"]

        self.assertIn(draft, topology.paths)
        self.assertNotIn(draft, draft_graph[start].paths)
        self.assertNotIn(draft_graph[end], draft_graph[start].neighbors)
        self.assertEqual(draft_checkpoint["path_being_created_index"], 0)
        self.assertTrue(draft_checkpoint["is_creating_path"])
        self.assertTrue(draft_checkpoint["paths"][0]["is_being_created"])

        topology.finish_path_creation()
        finished_graph = build_station_nodes_dict(topology.stations, topology.paths)
        finished_checkpoint = canonical_checkpoint(env)["topology"]

        self.assertIs(topology.paths[0], draft)
        self.assertIn(draft, finished_graph[start].paths)
        self.assertIn(finished_graph[end], finished_graph[start].neighbors)
        self.assertIsNone(finished_checkpoint["path_being_created_index"])
        self.assertFalse(finished_checkpoint["is_creating_path"])
        self.assertFalse(finished_checkpoint["paths"][0]["is_being_created"])
