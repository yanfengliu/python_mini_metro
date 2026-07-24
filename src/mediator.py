from __future__ import annotations

from typing import Dict, List

import pygame

from carriage_management import CarriageManagement
from config import (
    game_over_button_height,
    game_over_button_spacing,
    game_over_button_width,
    game_over_font_size,
    initial_num_stations,
    num_carriages,
    num_metros,
    num_paths,
    num_stations,
    overdue_passenger_threshold,
    passenger_color,
    passenger_max_wait_time_ms,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    path_order_shift,
    path_unlock_milestones,
    path_width,
    screen_height,
    screen_width,
    station_unlock_milestones,
)
from entity.carriage import Carriage
from entity.get_entity import get_random_stations
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from event.event import Event
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from fleet_management import FleetManagement
from geometry.point import Point
from geometry.type import ShapeType
from graph.graph_algo import bfs, build_station_nodes_dict
from graph.node import Node
from input_coordinator import InputCoordinator
from maps import CLASSIC, MapDefinition
from passenger_flow import PassengerFlow
from path_handles import PathEditSelection
from path_lifecycle import PathLifecycle
from path_redraw import PathRedrawGesture
from progression import NetworkProgression
from route_planner import RoutePlanner
from simulation_context import SimulationContext
from travel_plan import TravelPlan
from type import Color
from ui.button import Button
from ui.carriage_button import (
    get_carriage_buttons,
    update_carriage_button_positions,
    validate_resource_control_layout,
)
from ui.fleet_button import get_fleet_buttons, update_fleet_button_positions
from ui.path_button import PathButton, get_path_buttons, update_path_button_positions
from ui.speed_button import (
    SpeedAction,
    SpeedButton,
    get_speed_buttons,
    update_speed_button_positions,
)
from utils import get_shape_from_type, hue_to_rgb, pick_distinct_hue

TravelPlans = Dict[Passenger, TravelPlan]

_PAUSE_REASONS = frozenset({"user", "menu"})


def _get_game_renderer_factory():
    from rendering.game_renderer import GameRenderer

    return GameRenderer


class Mediator:
    def __init__(
        self,
        *,
        seed: int | None = None,
        context: SimulationContext | None = None,
        map_definition: MapDefinition | None = None,
    ) -> None:
        if seed is not None and context is not None:
            raise ValueError("seed and context are mutually exclusive")
        self.context = context if context is not None else SimulationContext(seed)
        # The map definition supplies the station-shape palette one-way; the
        # default Classic map reproduces current behavior byte-for-byte.
        self.map_definition = map_definition if map_definition is not None else CLASSIC
        self._input = InputCoordinator()
        self._fleet = FleetManagement()
        self._carriage_fleet = CarriageManagement()
        self._passenger_flow = PassengerFlow()
        self._path_lifecycle = PathLifecycle()
        self._router = RoutePlanner()

        # configs
        self.passenger_spawning_step = passenger_spawning_start_step
        self.passenger_spawning_interval_step = passenger_spawning_interval_step
        self._progression = NetworkProgression(
            num_paths=num_paths,
            path_unlock_milestones=path_unlock_milestones,
            num_stations=num_stations,
            initial_num_stations=initial_num_stations,
            station_unlock_milestones=station_unlock_milestones,
        )
        self.path_purchase_prices = self.get_path_purchase_prices()
        self.num_metros = num_metros
        self.num_carriages = num_carriages

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.fleet_buttons = get_fleet_buttons(self.path_buttons)
        self.carriage_buttons = get_carriage_buttons(self.path_buttons)
        self.speed_buttons = get_speed_buttons()
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [
            *self.path_buttons,
            *self.fleet_buttons,
            *self.carriage_buttons,
            *self.speed_buttons,
        ]
        self.game_over_restart_rect: pygame.Rect | None = None
        self.game_over_exit_rect: pygame.Rect | None = None
        self._layout_size: tuple[int, int] | None = None
        self._compat_renderer: object | None = None

        # entities
        self.all_stations = self.get_initial_station_pool()
        self.stations = self.all_stations[: self.initial_num_stations]
        self.metros: List[Metro] = []
        self.paths: List[Path] = []
        self.passengers: List[Passenger] = []
        self.path_colors = self.generate_distinct_path_colors(num_paths)
        self.path_to_color: Dict[Path, Color] = {}

        # status
        self.time_ms = 0
        self.steps = 0
        self.station_steps_since_last_spawn: Dict[Station, int] = {}
        self.station_spawn_interval_steps: Dict[Station, int] = {}
        self.initialize_station_spawning_state(self.all_stations)
        self.is_mouse_down = False
        self.is_creating_path = False
        self.path_being_created: Path | None = None
        self.path_redraw: PathRedrawGesture | None = None
        self.path_edit_selection: PathEditSelection | None = None
        self.travel_plans: TravelPlans = {}
        self.is_paused = False
        self.game_speed_multiplier = 1
        self.unlocked_num_paths = self.get_unlocked_num_paths()
        self.unlocked_num_stations = self.get_unlocked_num_stations()
        self.update_path_button_lock_states()
        self.is_game_over = False
        self.passenger_max_wait_time_ms = passenger_max_wait_time_ms
        self.overdue_passenger_threshold = overdue_passenger_threshold
        self.prepare_layout(screen_width, screen_height)

    @property
    def num_paths(self) -> int:
        return self._progression.num_paths

    @num_paths.setter
    def num_paths(self, value: int) -> None:
        self._progression.num_paths = value

    @property
    def path_unlock_milestones(self) -> List[int]:
        return self._progression.path_unlock_milestones

    @path_unlock_milestones.setter
    def path_unlock_milestones(self, value: List[int]) -> None:
        self._progression.path_unlock_milestones = value

    @property
    def path_purchase_prices(self) -> List[int]:
        return self._progression.path_purchase_prices

    @path_purchase_prices.setter
    def path_purchase_prices(self, value: List[int]) -> None:
        self._progression.path_purchase_prices = value

    @property
    def num_stations(self) -> int:
        return self._progression.num_stations

    @num_stations.setter
    def num_stations(self, value: int) -> None:
        self._progression.num_stations = value

    @property
    def initial_num_stations(self) -> int:
        return self._progression.initial_num_stations

    @initial_num_stations.setter
    def initial_num_stations(self, value: int) -> None:
        self._progression.initial_num_stations = value

    @property
    def station_unlock_milestones(self) -> List[int]:
        return self._progression.station_unlock_milestones

    @station_unlock_milestones.setter
    def station_unlock_milestones(self, value: List[int]) -> None:
        self._progression.station_unlock_milestones = value

    @property
    def deliveries(self) -> int:
        return self._progression.deliveries

    @deliveries.setter
    def deliveries(self, value: int) -> None:
        self._progression.deliveries = value

    @property
    def line_credits(self) -> int:
        return self._progression.line_credits

    @line_credits.setter
    def line_credits(self, value: int) -> None:
        self._progression.line_credits = value

    @property
    def available_locomotives(self) -> int:
        """Return unassigned fleet capacity without owning duplicate state."""

        return max(0, self.num_metros - len(self.metros))

    @property
    def assigned_carriages(self) -> int:
        """Return the number of carriages attached to canonical global Metros."""

        return sum(len(metro.carriages) for metro in self.metros)

    @property
    def available_carriages(self) -> int:
        """Return fungible carriage capacity without owning an object pool."""

        return max(0, self.num_carriages - self.assigned_carriages)

    @property
    def purchased_num_paths(self) -> int:
        return self._progression.purchased_num_paths

    @purchased_num_paths.setter
    def purchased_num_paths(self, value: int) -> None:
        self._progression.purchased_num_paths = value

    @property
    def unlocked_num_paths(self) -> int:
        return self._progression.unlocked_num_paths

    @unlocked_num_paths.setter
    def unlocked_num_paths(self, value: int) -> None:
        self._progression.unlocked_num_paths = value

    @property
    def unlocked_num_stations(self) -> int:
        return self._progression.unlocked_num_stations

    @unlocked_num_stations.setter
    def unlocked_num_stations(self, value: int) -> None:
        self._progression.unlocked_num_stations = value

    @property
    def total_travels_handled(self) -> int:
        """Deprecated writable alias for cumulative passenger deliveries."""

        return self.deliveries

    @total_travels_handled.setter
    def total_travels_handled(self, value: int) -> None:
        self.deliveries = value

    @property
    def score(self) -> int:
        """Deprecated writable alias for spendable line credits."""

        return self.line_credits

    @score.setter
    def score(self, value: int) -> None:
        self.line_credits = value

    @property
    def max_waiting_passengers(self) -> int:
        """Deprecated writable alias for the overdue-passenger threshold."""

        return self.overdue_passenger_threshold

    @max_waiting_passengers.setter
    def max_waiting_passengers(self, value: int) -> None:
        self.overdue_passenger_threshold = value

    def prepare_layout(self, width: int, height: int) -> None:
        """Prepare every interactive hitbox before input is dispatched."""

        self._input.prepare_layout(
            self,
            width,
            height,
            get_update_path_button_positions=lambda: update_path_button_positions,
            get_update_fleet_button_positions=lambda: update_fleet_button_positions,
            get_update_carriage_button_positions=lambda: (
                update_carriage_button_positions
            ),
            get_validate_resource_control_layout=lambda: (
                validate_resource_control_layout
            ),
            get_update_speed_button_positions=lambda: update_speed_button_positions,
            get_game_over_font_size=lambda: game_over_font_size,
            get_rect_factory=lambda: pygame.Rect,
            get_game_over_button_width=lambda: game_over_button_width,
            get_game_over_button_height=lambda: game_over_button_height,
            get_game_over_button_spacing=lambda: game_over_button_spacing,
        )

    def generate_distinct_path_colors(self, path_count: int) -> Dict[Color, bool]:
        if path_count <= 0:
            return {}
        selected_hues: List[float] = [self.context.python_random.random()]
        candidate_count = 24
        while len(selected_hues) < path_count:
            candidate_hues = [
                self.context.python_random.random() for _ in range(candidate_count)
            ]
            candidate_hues.append(self.context.python_random.random())
            selected_hues.append(pick_distinct_hue(selected_hues, candidate_hues))
        path_colors: Dict[Color, bool] = {}
        for hue in selected_hues:
            path_colors[hue_to_rgb(hue, saturation=0.6, value=0.9)] = False
        while len(path_colors) < path_count:
            hue = self.context.python_random.random()
            path_colors[hue_to_rgb(hue, saturation=0.6, value=0.9)] = False
        return path_colors

    def get_path_purchase_prices(self) -> List[int]:
        return self._progression.get_path_purchase_prices()

    def get_initial_station_pool(self) -> List[Station]:
        # Keep initial gameplay valid by guaranteeing at least two shape types.
        while True:
            stations = get_random_stations(
                self.num_stations,
                context=self.context,
                shape_types=self.map_definition.shape_types,
                unique_shape_types=self.map_definition.unique_shape_types,
                unique_spawn_start_index=self.map_definition.unique_spawn_start_index,
                unique_spawn_chance=self.map_definition.unique_spawn_chance,
                spawn_regions=self.map_definition.spawn_regions,
            )
            initial_shapes = {
                station.shape.type for station in stations[: self.initial_num_stations]
            }
            if len(initial_shapes) >= 2:
                return stations

    def get_unlocked_num_stations(self) -> int:
        return self._progression.get_unlocked_num_stations()

    def update_unlocked_num_stations(self) -> None:
        (
            previous_unlocked_num_stations,
            self.unlocked_num_stations,
        ) = self._progression.set_unlocked_num_stations(
            self.get_unlocked_num_stations()
        )
        if self.unlocked_num_stations > len(self.stations):
            newly_unlocked_stations = self.all_stations[
                len(self.stations) : self.unlocked_num_stations
            ]
            self.stations = self.all_stations[: self.unlocked_num_stations]
            if self.unlocked_num_stations > previous_unlocked_num_stations:
                for station in newly_unlocked_stations:
                    station.start_unlock_blink(self.time_ms)

    def get_unlocked_num_paths(self) -> int:
        return self._progression.get_unlocked_num_paths()

    def update_unlocked_num_paths(self) -> None:
        self._input.update_unlocked_num_paths(self)

    def update_path_button_lock_states(self) -> None:
        self._input.update_path_button_lock_states(self)

    def get_next_path_button_idx_to_purchase(self) -> int | None:
        return self._progression.get_next_path_button_idx_to_purchase()

    def get_purchase_price_for_path_button_idx(self, button_idx: int) -> int | None:
        return self._progression.get_purchase_price_for_path_button_idx(button_idx)

    def can_purchase_path_button_idx(self, button_idx: int) -> bool:
        return self._input.can_purchase_path_button_idx(self, button_idx)

    def try_purchase_path_button(self, button: PathButton) -> bool:
        return self._input.try_purchase_path_button(self, button)

    def try_purchase_path_button_by_index(self, button_idx: int | None = None) -> bool:
        return self._input.try_purchase_path_button_by_index(self, button_idx)

    def step_time(self, dt_ms: int) -> None:
        self._input.step_time(self, dt_ms)

    def assign_paths_to_buttons(self) -> None:
        self._path_lifecycle.assign_paths_to_buttons(self)

    def get_surface_size(self, screen: pygame.surface.Surface) -> tuple[int, int]:
        return self._input.get_surface_size(
            self,
            screen,
            get_screen_width=lambda: screen_width,
            get_screen_height=lambda: screen_height,
        )

    def render(
        self,
        screen: pygame.surface.Surface,
        renderer: object | None = None,
        alpha: float = 1.0,
    ) -> None:
        """Compatibility rendering entrypoint; callers should own the renderer."""

        self._input.render(
            self,
            screen,
            renderer,
            alpha,
            get_renderer_factory=lambda: _get_game_renderer_factory(),
        )

    def handle_game_over_click(self, position: Point) -> str | None:
        return self._input.handle_game_over_click(self, position)

    def react_mouse_event(self, event: MouseEvent) -> None:
        self._input.react_mouse_event(
            self,
            event,
            get_mouse_event_type=lambda: MouseEventType,
            get_station_type=lambda: Station,
            get_path_button_type=lambda: PathButton,
            get_speed_button_type=lambda: SpeedButton,
            get_button_type=lambda: Button,
            get_path_redraw_factory=lambda: PathRedrawGesture,
        )

    def react_keyboard_event(self, event: KeyboardEvent) -> None:
        self._input.react_keyboard_event(
            self,
            event,
            get_keyboard_event_type=lambda: KeyboardEventType,
            get_pause_key=lambda: pygame.K_SPACE,
            get_speed_1_key=lambda: pygame.K_1,
            get_speed_2_key=lambda: pygame.K_2,
            get_speed_4_key=lambda: pygame.K_3,
        )

    def react(self, event: Event | None) -> None:
        self._input.react(
            self,
            event,
            get_mouse_event_class=lambda: MouseEvent,
            get_keyboard_event_class=lambda: KeyboardEvent,
        )

    def get_containing_entity(self, position: Point):
        return self._input.get_containing_entity(self, position)

    def remove_path(self, path: Path) -> None:
        self._path_lifecycle.remove_path(
            self,
            path,
            get_reconcile_station_service=lambda: self._reconcile_station_service,
        )

    def invalidate_travel_plans_for_path(self, path: Path) -> None:
        self._path_lifecycle.invalidate_travel_plans_for_path(self, path)

    def remove_path_by_id(self, path_id: str) -> bool:
        return self._path_lifecycle.remove_path_by_id(self, path_id)

    def remove_path_by_index(self, path_index: int) -> bool:
        return self._path_lifecycle.remove_path_by_index(self, path_index)

    def start_path_on_station(self, station: Station) -> None:
        self._path_lifecycle.start_path_on_station(
            self, station, get_path_factory=lambda: Path
        )

    def create_path_from_station_indices(
        self, station_indices: List[int], loop: bool = False
    ) -> Path | None:
        return self._path_lifecycle.create_path_from_station_indices(
            self, station_indices, loop
        )

    def replace_path(
        self, path: Path, station_indices: List[int], loop: bool = False
    ) -> bool:
        return self._path_lifecycle.replace_path(
            self,
            path,
            station_indices,
            loop,
            get_path_factory=lambda: Path,
            get_geometry_style=lambda: (path_order_shift, path_width),
            get_graph_builder=lambda: build_station_nodes_dict,
            get_scoped_replanner=lambda: self._replan_passenger_at_station,
        )

    def replace_path_by_id(
        self, path_id: str, station_indices: List[int], loop: bool = False
    ) -> bool:
        return self._path_lifecycle.replace_path_by_id(
            self, path_id, station_indices, loop
        )

    def replace_path_by_index(
        self, path_index: int, station_indices: List[int], loop: bool = False
    ) -> bool:
        return self._path_lifecycle.replace_path_by_index(
            self, path_index, station_indices, loop
        )

    def add_station_to_path(self, station: Station) -> None:
        self._path_lifecycle.add_station_to_path(self, station)

    def abort_path_creation(self) -> None:
        self._path_lifecycle.abort_path_creation(self)

    def release_color_for_path(self, path: Path) -> None:
        self._path_lifecycle.release_color_for_path(self, path)

    def finish_path_creation(self) -> None:
        self._path_lifecycle.finish_path_creation(self)

    def can_assign_locomotive(self, path: Path) -> bool:
        return self._fleet.can_assign(self, path)

    def assign_locomotive(self, path: Path) -> bool:
        return self._fleet.assign(self, path, get_metro_factory=lambda: Metro)

    def can_queue_locomotive_unassignment(self, path: Path) -> bool:
        return self._fleet.can_queue(self, path)

    def queue_locomotive_unassignment(self, path: Path) -> bool:
        return self._fleet.queue(
            self, path, reconcile_station_service=self._reconcile_station_service
        )

    def queued_locomotives_for_path(self, path: Path) -> int:
        return self._fleet.queued_count(self, path)

    def can_cancel_unassignment(self, path: Path) -> bool:
        return self._fleet.can_cancel(self, path)

    def cancel_unassignment(self, path: Path) -> bool:
        return self._fleet.cancel(
            self, path, reconcile_station_service=self._reconcile_station_service
        )

    def can_attach_carriage(self, path: Path) -> bool:
        return self._carriage_fleet.can_attach(self, path)

    def attach_carriage(self, path: Path) -> bool:
        return self._carriage_fleet.attach(
            self,
            path,
            get_carriage_factory=lambda: Carriage,
            reconcile_station_service=self._reconcile_station_service,
        )

    def can_detach_carriage(self, path: Path) -> bool:
        return self._carriage_fleet.can_detach(self, path)

    def detach_carriage(self, path: Path) -> bool:
        return self._carriage_fleet.detach(
            self,
            path,
            reconcile_station_service=self._reconcile_station_service,
        )

    def _reconcile_station_service(self, metro: Metro) -> None:
        self._passenger_flow.reconcile_station_service(
            self,
            metro,
            get_graph_builder=lambda: build_station_nodes_dict,
        )

    @property
    def is_paused(self) -> bool:
        """Project the active pause reasons to one effective exact bool."""

        return bool(getattr(self, "_pause_reasons", None))

    @is_paused.setter
    def is_paused(self, paused: bool) -> None:
        if paused:
            self.hold_pause_reason("user")
        else:
            self.release_pause_reason("user")

    @property
    def _user_pause_held(self) -> bool:
        return "user" in getattr(self, "_pause_reasons", ())

    def hold_pause_reason(self, reason: str) -> None:
        """Hold one validated pause reason; repeated holds are idempotent."""

        self._pause_reason_store(reason).add(reason)

    def release_pause_reason(self, reason: str) -> None:
        """Release one validated pause reason; a non-held reason is a no-op."""

        self._pause_reason_store(reason).discard(reason)

    def _pause_reason_store(self, reason: str) -> set[str]:
        # The store is created lazily per instance so bare hosts stay safe and
        # no class-level mutable default can leak holds across reconstructions.
        if reason not in _PAUSE_REASONS:
            raise ValueError(f"unknown pause reason: {reason!r}")
        store = getattr(self, "_pause_reasons", None)
        if store is None:
            store = set()
            self._pause_reasons = store
        return store

    def set_paused(self, paused: bool) -> None:
        self._input.set_paused(self, paused)

    def set_game_speed(self, speed_multiplier: int) -> None:
        self._input.set_game_speed(self, speed_multiplier)

    def apply_speed_action(self, action: SpeedAction) -> None:
        self._input.apply_speed_action(self, action)

    def is_speed_button_active(self, action: SpeedAction) -> bool:
        return self._input.is_speed_button_active(self, action)

    def apply_action(self, action: object) -> bool:
        return self._input.apply_action(self, action)

    def end_path_on_station(self, station: Station) -> None:
        self._path_lifecycle.end_path_on_station(self, station)

    def get_station_shape_types(self) -> List[ShapeType]:
        return self._passenger_flow.get_station_shape_types(self)

    def is_passenger_spawn_time(self) -> bool:
        return self._passenger_flow.is_passenger_spawn_time(self)

    def initialize_station_spawning_state(self, stations: List[Station]) -> None:
        self._passenger_flow.initialize_station_spawning_state(self, stations)

    def get_station_spawn_interval_step(self) -> int:
        return self._passenger_flow.get_station_spawn_interval_step(self)

    def should_spawn_passenger_at_station(self, station: Station) -> bool:
        return self._passenger_flow.should_spawn_passenger_at_station(self, station)

    def spawn_passengers(self) -> None:
        self._passenger_flow.spawn_passengers(
            self,
            get_passenger_factory=lambda: Passenger,
            get_shape_factory=lambda: get_shape_from_type,
            get_passenger_color=lambda: passenger_color,
            get_passenger_size=lambda: passenger_size,
        )

    def increment_time(self, dt_ms: int) -> None:
        transition_active = not self.is_paused and not self.is_game_over
        # The narrow reconcile runs unconditionally — including paused and
        # terminal states — so a repairable shape never survives a tick.
        self._fleet.reconcile(self)
        if transition_active:
            self._drain_and_settle_queued_returns()
        self._passenger_flow.increment_time(
            self,
            dt_ms,
            get_graph_builder=lambda: build_station_nodes_dict,
        )
        if transition_active:
            self._drain_and_settle_queued_returns()

    def _drain_and_settle_queued_returns(self) -> None:
        """Force-alight stranded riders, then settle emptied queued returns.

        The drain is gated on the live game-over flag so a tick that flips
        the game terminal never moves a rider afterwards; settle keeps its
        pre-existing terminal-tick behavior.
        """

        if not self.is_game_over:
            self._passenger_flow.drain_queued_returns(
                self,
                get_graph_builder=lambda: build_station_nodes_dict,
            )
        self._fleet.settle(self)

    def get_next_station_for_metro(self, metro: Metro) -> Station | None:
        return self._passenger_flow.get_next_station_for_metro(self, metro)

    def get_boarding_candidates_for_metro(
        self,
        metro: Metro,
        station: Station,
        station_nodes_dict: Dict[Station, Node],
        mutate_travel_plans: bool,
    ) -> List[Passenger]:
        if metro.is_unassignment_queued:
            return []
        return self._passenger_flow.get_boarding_candidates_for_metro(
            self,
            metro,
            station,
            station_nodes_dict,
            mutate_travel_plans,
            get_boarding_iterator=lambda: self._router.iter_boarding_candidates,
        )

    def get_unloading_candidates_for_metro(
        self, metro: Metro, station: Station
    ) -> tuple[List[Passenger], List[Passenger]]:
        return self._passenger_flow.get_unloading_candidates_for_metro(
            self, metro, station
        )

    def should_stop_at_next_station(
        self, metro: Metro, station_nodes_dict: Dict[Station, Node]
    ) -> bool:
        if metro.is_unassignment_queued:
            return self.get_next_station_for_metro(metro) is not None
        return self._passenger_flow.should_stop_at_next_station(
            self, metro, station_nodes_dict
        )

    def start_station_stop_if_needed(
        self,
        metro: Metro,
        station: Station,
        station_nodes_dict: Dict[Station, Node],
    ) -> None:
        self._passenger_flow.start_station_stop_if_needed(
            self, metro, station, station_nodes_dict
        )

    def can_board_at_station(self, metro: Metro, station: Station) -> bool:
        if getattr(metro, "is_unassignment_queued", False):
            return False
        return self._passenger_flow.can_board_at_station(self, metro, station)

    def move_passengers(self, dt_ms: int) -> None:
        self._passenger_flow.move_passengers(
            self,
            dt_ms,
            get_graph_builder=lambda: build_station_nodes_dict,
            get_record_delivery=lambda: self._progression.record_delivery,
            get_scoped_replanner=lambda: self._replan_passenger_at_station,
        )

    def update_waiting_and_game_over(self, dt_ms: int) -> None:
        was_game_over = self.is_game_over
        self._passenger_flow.update_waiting_and_game_over(self, dt_ms)
        if not was_game_over and self.is_game_over:
            self._input.clear_transient_input(self)

    def get_stations_for_shape_type(self, shape_type: ShapeType) -> List[Station]:
        stations = self._router.get_stations_for_shape_type(self.stations, shape_type)
        self.context.python_random.shuffle(stations)
        return stations

    def find_shared_path(self, station_a: Station, station_b: Station) -> Path | None:
        return self._router.find_shared_path(self.paths, station_a, station_b)

    def passenger_has_travel_plan(self, passenger: Passenger) -> bool:
        return self._router.passenger_has_travel_plan(
            contains_travel_plan=lambda: passenger in self.travel_plans,
            get_travel_plan=lambda: self.travel_plans[passenger],
        )

    def find_next_path_for_passenger_at_station(
        self, passenger: Passenger, station: Station
    ):
        self._router.update_next_path_for_plan(
            station,
            get_plan=lambda: self.travel_plans[passenger],
            find_shared_path=lambda start, end: self.find_shared_path(start, end),
        )

    def get_path_by_id(self, path_id: str) -> Path | None:
        return self._router.get_path_by_id(self.paths, path_id)

    def get_travel_plan_starting_with_path(
        self,
        passenger: Passenger,
        station: Station,
        required_first_path: Path,
        station_nodes_dict: Dict[Station, Node],
    ) -> TravelPlan | None:
        return self._router.get_travel_plan_starting_with_path(
            station,
            self.get_stations_for_shape_type(passenger.destination_shape.type),
            station_nodes_dict,
            get_required_first_path_id=lambda: required_first_path.id,
            find_node_path=lambda start, end: bfs(start, end),
            get_reduce_node_path=lambda: self.skip_stations_on_same_path,
            get_find_shared_path=lambda: self.find_shared_path,
            get_plan_factory=lambda: TravelPlan,
        )

    def skip_stations_on_same_path(self, node_path: List[Node]):
        return self._router.skip_stations_on_same_path(node_path)

    def _replan_passenger_at_station(
        self,
        passenger: Passenger,
        station: Station,
        station_nodes_dict: Dict[Station, Node],
    ) -> None:
        self._passenger_flow.replan_passenger_at_station(
            self,
            passenger,
            station,
            station_nodes_dict,
            get_best_path_finder=lambda: self._router.find_best_node_path,
            get_search=lambda: bfs,
            get_plan_factory=lambda: TravelPlan,
        )

    def find_travel_plan_for_passengers(self) -> None:
        self._passenger_flow.find_travel_plan_for_passengers(
            self,
            get_graph_builder=lambda: build_station_nodes_dict,
            get_bulk_iterator=lambda: self._router.iter_bulk_route_proposals,
            get_search=lambda: bfs,
            get_plan_factory=lambda: TravelPlan,
        )
