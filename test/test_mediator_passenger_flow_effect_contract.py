from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from test import mediator_test_support as support

# isort: split

import mediator as mediator_module
from mediator import Mediator


class _Passenger:
    def __init__(
        self,
        name: str,
        events: list[object],
        *,
        log_wait: bool = False,
    ) -> None:
        self.name = name
        self.events = events
        self.destination_shape = SimpleNamespace(type=f"destination-{name}")
        self._is_at_destination = False
        self._wait_ms = 25
        self.log_wait = log_wait

    @property
    def is_at_destination(self) -> bool:
        return self._is_at_destination

    @is_at_destination.setter
    def is_at_destination(self, value: bool) -> None:
        self.events.append(("arrived", self.name, value))
        self._is_at_destination = value

    @property
    def wait_ms(self) -> int:
        return self._wait_ms

    @wait_ms.setter
    def wait_ms(self, value: int) -> None:
        if self.log_wait:
            self.events.append(("wait", self.name, value))
        self._wait_ms = value


class _Station:
    def __init__(self, name: str, events: list[object], capacity: int = 12) -> None:
        self.name = name
        self.events = events
        self.capacity = capacity
        self.passengers: list[_Passenger] = []

    def has_room(self) -> bool:
        return len(self.passengers) < self.capacity

    def add_passenger(self, passenger: _Passenger) -> None:
        self.passengers.append(passenger)

    def remove_passenger(self, passenger: _Passenger) -> None:
        self.events.append(("station-remove", passenger.name))
        self.passengers.remove(passenger)

    def move_passenger(self, passenger: _Passenger, metro: _Metro) -> None:
        self.events.append(("board", passenger.name))
        self.passengers.remove(passenger)
        metro.passengers.append(passenger)


class _Metro:
    def __init__(
        self,
        station: _Station,
        events: list[object],
        passengers: list[_Passenger],
    ) -> None:
        self.current_station = station
        self.events = events
        self.passengers = passengers
        self.capacity = 6
        self.stop_time_remaining_ms = 1000
        self.boarding_progress_ms = 0
        self.boarding_time_per_passenger_ms = 500
        self.speed = 1

    def has_room(self) -> bool:
        return len(self.passengers) < self.capacity

    def remove_passenger(self, passenger: _Passenger) -> None:
        self.events.append(("metro-remove", passenger.name))
        self.passengers.remove(passenger)

    def move_passenger(self, passenger: _Passenger, station: _Station) -> None:
        self.events.append(("transfer", passenger.name))
        self.passengers.remove(passenger)
        station.passengers.append(passenger)


class _EventList(list[_Passenger]):
    def __init__(self, values: list[_Passenger], events: list[object]) -> None:
        super().__init__(values)
        self.events = events

    def remove(self, passenger: _Passenger) -> None:
        self.events.append(("global-remove", passenger.name))
        super().remove(passenger)


class _EventPlans(dict[_Passenger, object]):
    def __init__(
        self,
        values: dict[_Passenger, object],
        events: list[object],
    ) -> None:
        super().__init__(values)
        self.events = events

    def __delitem__(self, passenger: _Passenger) -> None:
        self.events.append(("plan-delete", passenger.name))
        super().__delitem__(passenger)

    def __setitem__(self, passenger: _Passenger, plan: object) -> None:
        kind = getattr(plan, "kind", "unknown")
        nodes = tuple(getattr(plan, "nodes", ()))
        self.events.append(("plan-set", passenger.name, kind, nodes))
        super().__setitem__(passenger, plan)


class TestPassengerFlowEffectContract(support.MediatorTestCase):
    def test_delivery_order_re_resolves_progression_and_public_hooks_per_rider(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[object] = []
        station = _Station("station", events)
        first = _Passenger("first", events)
        second = _Passenger("second", events)
        metro = _Metro(station, events, [first, second])
        mediator.stations = [station]
        mediator.paths = []
        mediator.metros = [metro]
        mediator.passengers = _EventList([first, second], events)
        mediator.travel_plans = _EventPlans({first: object(), second: object()}, events)
        mediator.get_unloading_candidates_for_metro = lambda active_metro, _station: (
            list(active_metro.passengers),
            [],
        )
        mediator.get_boarding_candidates_for_metro = lambda *_args, **_kwargs: []
        progression = mediator._progression

        def second_record() -> None:
            events.append("record-second")
            progression.deliveries += 1
            progression.line_credits += 1

        def first_record() -> None:
            events.append("record-first")
            progression.deliveries += 1
            progression.line_credits += 1
            progression.record_delivery = second_record

        def second_paths() -> None:
            events.append("paths-second")

        def first_paths() -> None:
            events.append("paths-first")
            mediator.update_unlocked_num_paths = second_paths

        def second_stations() -> None:
            events.append("stations-second")

        def first_stations() -> None:
            events.append("stations-first")
            mediator.update_unlocked_num_stations = second_stations

        progression.record_delivery = first_record
        mediator.update_unlocked_num_paths = first_paths
        mediator.update_unlocked_num_stations = first_stations

        with patch.object(mediator_module, "build_station_nodes_dict", return_value={}):
            mediator.move_passengers(1000)

        self.assertEqual(
            events,
            [
                ("arrived", "first", True),
                ("metro-remove", "first"),
                ("global-remove", "first"),
                ("plan-delete", "first"),
                "record-first",
                "paths-first",
                "stations-first",
                ("arrived", "second", True),
                ("metro-remove", "second"),
                ("global-remove", "second"),
                ("plan-delete", "second"),
                "record-second",
                "paths-second",
                "stations-second",
            ],
        )
        self.assertEqual(mediator.deliveries, 2)
        self.assertEqual(mediator.line_credits, 2)

    def test_exchange_orders_transfer_plan_effects_before_boarding_effects(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[object] = []
        station = _Station("station", events)
        transfer = _Passenger("transfer", events, log_wait=True)
        boarder = _Passenger("boarder", events, log_wait=True)
        station.passengers = [boarder]
        metro = _Metro(station, events, [transfer])

        class Plan:
            def increment_next_station(self) -> None:
                events.append("increment-plan")

        plan = Plan()
        mediator.stations = [station]
        mediator.paths = []
        mediator.metros = [metro]
        mediator.passengers = [transfer, boarder]
        mediator.travel_plans = {transfer: plan}
        mediator.get_unloading_candidates_for_metro = lambda active_metro, _station: (
            [],
            [transfer] if transfer in active_metro.passengers else [],
        )
        mediator.get_boarding_candidates_for_metro = (
            lambda _metro, active_station, *_args, **_kwargs: (
                [boarder] if boarder in active_station.passengers else []
            )
        )
        mediator.find_next_path_for_passenger_at_station = (
            lambda passenger, active_station: events.append(
                ("next-path", passenger.name, active_station.name)
            )
        )

        with patch.object(mediator_module, "build_station_nodes_dict", return_value={}):
            mediator.move_passengers(1000)

        self.assertEqual(
            events,
            [
                ("transfer", "transfer"),
                ("wait", "transfer", 0),
                "increment-plan",
                ("next-path", "transfer", "station"),
                ("board", "boarder"),
                ("wait", "boarder", 0),
            ],
        )
        self.assertEqual(metro.passengers, [boarder])
        self.assertEqual(station.passengers, [transfer])

    def test_station_stop_dispatches_unload_board_can_board_in_baseline_order(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[str] = []
        station = object()
        metro = SimpleNamespace(
            stop_time_remaining_ms=0,
            boarding_progress_ms=99,
            boarding_time_per_passenger_ms=500,
            speed=3,
        )
        mediator.get_unloading_candidates_for_metro = lambda *_args: (
            events.append("unload") or ([object()], [])
        )
        mediator.get_boarding_candidates_for_metro = lambda *_args, **_kwargs: (
            events.append("board") or [object(), object()]
        )
        mediator.can_board_at_station = lambda *_args: (
            events.append("can-board") or False
        )

        mediator.start_station_stop_if_needed(metro, station, {})

        self.assertEqual(events, ["unload", "board", "can-board"])
        self.assertEqual(metro.stop_time_remaining_ms, 500)
        self.assertEqual(metro.boarding_progress_ms, 0)
        self.assertEqual(metro.speed, 0)

    def test_bulk_application_orders_all_effects_and_keeps_one_router_iterator(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[object] = []
        arrival = _Passenger("arrival", events)
        route = _Passenger("route", events)
        fallback = _Passenger("fallback", events)
        station = _Station("station", events)
        station.passengers = [arrival]
        mediator.stations = [station]
        mediator.paths = []
        mediator.passengers = _EventList([arrival, route, fallback], events)
        mediator.travel_plans = _EventPlans({arrival: object()}, events)
        head, next_node = object(), object()
        graph = object()
        test_case = self

        def fallback_factory(nodes: list[object]) -> object:
            events.append(("fallback-factory", tuple(nodes)))
            return SimpleNamespace(kind="fallback", nodes=list(nodes))

        def route_factory(nodes: list[object]) -> object:
            events.append(("route-factory", tuple(nodes)))
            mediator_module.TravelPlan = fallback_factory
            return SimpleNamespace(kind="route", nodes=list(nodes))

        def unresolved_factory(_nodes: list[object]) -> object:
            raise AssertionError("TravelPlan resolved before its proposal effect")

        class ExplodingRouter:
            @property
            def iter_bulk_route_proposals(self):
                raise AssertionError("bulk iterator was resolved more than once")

        class Router:
            @property
            def iter_bulk_route_proposals(self):
                events.append("router-resolve")

                def build(
                    stations: list[object],
                    **kwargs: object,
                ):
                    events.append(
                        (
                            "router-build",
                            stations is mediator.stations,
                            kwargs["node_map"] is graph,
                        )
                    )

                    def proposals():
                        try:
                            events.append("yield-arrival")
                            yield station, arrival, [head], "arrival"
                            test_case.assertNotIn(arrival, station.passengers)
                            test_case.assertNotIn(arrival, mediator.passengers)
                            test_case.assertNotIn(arrival, mediator.travel_plans)
                            events.append("arrival-observed")
                            mediator._router = ExplodingRouter()
                            mediator_module.TravelPlan = route_factory
                            events.append("destination-finalized")
                            yield station, arrival, None, "fallback"
                            test_case.assertNotIn(arrival, mediator.travel_plans)
                            events.append("arrival-fallback-observed")
                            events.append("yield-route")
                            yield station, route, [head, next_node], "route"
                            test_case.assertEqual(
                                mediator.travel_plans[route].kind,
                                "route",
                            )
                            events.append("route-observed")
                            events.append("yield-fallback")
                            yield station, fallback, None, "fallback"
                            test_case.assertEqual(
                                mediator.travel_plans[fallback].kind,
                                "fallback",
                            )
                            events.append("fallback-observed")
                        finally:
                            events.append("iterator-finalized")

                    return proposals()

                return build

        def wire(passenger: _Passenger, active_station: _Station) -> None:
            events.append(
                (
                    "wire",
                    passenger.name,
                    active_station.name,
                    mediator.travel_plans[passenger].kind,
                )
            )

        mediator._router = Router()
        mediator.find_next_path_for_passenger_at_station = wire

        def build_graph(stations: list[object], paths: list[object]) -> object:
            events.append(
                (
                    "graph",
                    stations is mediator.stations,
                    paths is mediator.paths,
                )
            )
            return graph

        with (
            patch.object(
                mediator_module,
                "build_station_nodes_dict",
                side_effect=build_graph,
            ),
            patch.object(mediator_module, "TravelPlan", unresolved_factory),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(
            events,
            [
                ("graph", True, True),
                "router-resolve",
                ("router-build", True, True),
                "yield-arrival",
                ("station-remove", "arrival"),
                ("global-remove", "arrival"),
                ("arrived", "arrival", True),
                ("plan-delete", "arrival"),
                "arrival-observed",
                "destination-finalized",
                "arrival-fallback-observed",
                "yield-route",
                ("route-factory", (next_node,)),
                ("plan-set", "route", "route", (next_node,)),
                ("wire", "route", "station", "route"),
                "route-observed",
                "yield-fallback",
                ("fallback-factory", ()),
                ("plan-set", "fallback", "fallback", ()),
                "fallback-observed",
                "iterator-finalized",
            ],
        )

    def test_waiting_scan_uses_live_station_and_passenger_lists_before_game_over(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[object] = []

        class WaitingPassenger:
            def __init__(self, name: str) -> None:
                self.name = name
                self._wait_ms = 4
                self.on_update = lambda: None

            @property
            def wait_ms(self) -> int:
                return self._wait_ms

            @wait_ms.setter
            def wait_ms(self, value: int) -> None:
                events.append((self.name, value, mediator.is_game_over))
                self._wait_ms = value
                self.on_update()

        first = WaitingPassenger("first")
        appended = WaitingPassenger("appended")
        later_station_passenger = WaitingPassenger("later-station")
        first_station = SimpleNamespace(passengers=[first])
        second_station = SimpleNamespace(passengers=[later_station_passenger])

        def grow_live_collections() -> None:
            first.on_update = lambda: None
            first_station.passengers.append(appended)
            mediator.stations.append(second_station)

        first.on_update = grow_live_collections
        mediator.stations = [first_station]
        mediator.passenger_max_wait_time_ms = 5
        mediator.overdue_passenger_threshold = 3
        mediator.is_game_over = False

        mediator.update_waiting_and_game_over(1)

        self.assertEqual(
            events,
            [
                ("first", 5, False),
                ("appended", 5, False),
                ("later-station", 5, False),
            ],
        )
        self.assertTrue(mediator.is_game_over)


if __name__ == "__main__":
    support.unittest.main()
