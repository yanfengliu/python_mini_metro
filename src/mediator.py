from __future__ import annotations

from typing import Dict, List

import pygame

from config import (
    game_over_button_height,
    game_over_button_spacing,
    game_over_button_width,
    game_over_font_size,
    initial_num_stations,
    num_metros,
    num_paths,
    num_stations,
    overdue_passenger_threshold,
    passenger_color,
    passenger_max_wait_time_ms,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    path_unlock_milestones,
    screen_height,
    screen_width,
    station_unlock_milestones,
)
from entity.get_entity import get_random_stations
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from event.event import Event
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from geometry.type import ShapeType
from graph.graph_algo import bfs, build_station_nodes_dict
from graph.node import Node
from path_lifecycle import PathLifecycle
from progression import NetworkProgression
from route_planner import RoutePlanner
from simulation_context import SimulationContext
from travel_plan import TravelPlan
from type import Color
from ui.button import Button
from ui.path_button import PathButton, get_path_buttons, update_path_button_positions
from ui.speed_button import (
    SpeedAction,
    SpeedButton,
    get_speed_buttons,
    update_speed_button_positions,
)
from utils import get_shape_from_type, hue_to_rgb, pick_distinct_hue

TravelPlans = Dict[Passenger, TravelPlan]


class Mediator:
    def __init__(
        self,
        *,
        seed: int | None = None,
        context: SimulationContext | None = None,
    ) -> None:
        if seed is not None and context is not None:
            raise ValueError("seed and context are mutually exclusive")
        self.context = context if context is not None else SimulationContext(seed)
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

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.speed_buttons = get_speed_buttons()
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [*self.path_buttons, *self.speed_buttons]
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

        update_path_button_positions(self.path_buttons, width, height)
        update_speed_button_positions(self.speed_buttons, width, height)
        start_top = height // 2 + game_over_font_size // 3 + 40
        restart_rect = pygame.Rect(
            0, 0, game_over_button_width, game_over_button_height
        )
        restart_rect.centerx = width // 2
        restart_rect.top = start_top
        exit_rect = restart_rect.copy()
        exit_rect.top = restart_rect.bottom + game_over_button_spacing
        self.game_over_restart_rect = restart_rect
        self.game_over_exit_rect = exit_rect
        self._layout_size = (width, height)

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
            stations = get_random_stations(self.num_stations, context=self.context)
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
        (
            previous_unlocked_num_paths,
            self.unlocked_num_paths,
        ) = self._progression.set_unlocked_num_paths(self.get_unlocked_num_paths())
        if self.unlocked_num_paths > previous_unlocked_num_paths:
            for path_button_idx in range(
                previous_unlocked_num_paths, self.unlocked_num_paths
            ):
                self.path_buttons[path_button_idx].start_unlock_blink(self.time_ms)
        self.update_path_button_lock_states()

    def update_path_button_lock_states(self) -> None:
        for idx, button in enumerate(self.path_buttons):
            button.set_locked(idx >= self.unlocked_num_paths)

    def get_next_path_button_idx_to_purchase(self) -> int | None:
        return self._progression.get_next_path_button_idx_to_purchase()

    def get_purchase_price_for_path_button_idx(self, button_idx: int) -> int | None:
        return self._progression.get_purchase_price_for_path_button_idx(button_idx)

    def can_purchase_path_button_idx(self, button_idx: int) -> bool:
        next_button_idx = self.get_next_path_button_idx_to_purchase()
        if next_button_idx is None or next_button_idx != button_idx:
            return False
        return self._progression.can_purchase_resolved_path_button_idx(
            button_idx,
            next_button_idx=next_button_idx,
            price=self.get_purchase_price_for_path_button_idx(button_idx),
        )

    def try_purchase_path_button(self, button: PathButton) -> bool:
        if not button.is_locked:
            return False
        try:
            button_idx = self.path_buttons.index(button)
        except ValueError:
            return False
        if not self.can_purchase_path_button_idx(button_idx):
            return False
        price = self.get_purchase_price_for_path_button_idx(button_idx)
        if price is None:
            return False
        self._progression.record_path_purchase(price)
        self.update_unlocked_num_paths()
        return True

    def try_purchase_path_button_by_index(self, button_idx: int | None = None) -> bool:
        if button_idx is None:
            button_idx = self.get_next_path_button_idx_to_purchase()
        if button_idx is None:
            return False
        if button_idx < 0 or button_idx >= len(self.path_buttons):
            return False
        return self.try_purchase_path_button(self.path_buttons[button_idx])

    def step_time(self, dt_ms: int) -> None:
        self.increment_time(dt_ms)

    def assign_paths_to_buttons(self) -> None:
        self._path_lifecycle.assign_paths_to_buttons(self)

    def get_surface_size(self, screen: pygame.surface.Surface) -> tuple[int, int]:
        width = screen_width
        height = screen_height
        maybe_width = screen.get_width()
        maybe_height = screen.get_height()
        if isinstance(maybe_width, (int, float)):
            width = int(maybe_width)
        if isinstance(maybe_height, (int, float)):
            height = int(maybe_height)
        return (width, height)

    def render(
        self,
        screen: pygame.surface.Surface,
        renderer: object | None = None,
        alpha: float = 1.0,
    ) -> None:
        """Compatibility rendering entrypoint; callers should own the renderer."""

        size = self.get_surface_size(screen)
        if self._layout_size != size:
            self.prepare_layout(*size)
        if renderer is None and self._compat_renderer is None:
            from rendering.game_renderer import GameRenderer

            self._compat_renderer = GameRenderer()
        if renderer is None:
            renderer = self._compat_renderer
        assert renderer is not None
        draw = getattr(renderer, "draw")
        draw(screen, self, alpha=alpha)

    def handle_game_over_click(self, position: Point) -> str | None:
        if not self.is_game_over:
            return None
        if self.game_over_restart_rect and self.game_over_restart_rect.collidepoint(
            position.to_tuple()
        ):
            return "restart"
        if self.game_over_exit_rect and self.game_over_exit_rect.collidepoint(
            position.to_tuple()
        ):
            return "exit"
        return None

    def react_mouse_event(self, event: MouseEvent) -> None:
        entity = self.get_containing_entity(event.position)

        if event.event_type == MouseEventType.MOUSE_DOWN:
            self.is_mouse_down = True
            if entity:
                if isinstance(entity, Station):
                    self.start_path_on_station(entity)

        elif event.event_type == MouseEventType.MOUSE_UP:
            self.is_mouse_down = False
            if self.is_creating_path:
                assert self.path_being_created is not None
                if entity and isinstance(entity, Station):
                    self.end_path_on_station(entity)
                else:
                    self.abort_path_creation()
            else:
                if entity and isinstance(entity, PathButton):
                    if entity.path:
                        self.remove_path(entity.path)
                    elif entity.is_locked:
                        self.try_purchase_path_button(entity)
                elif entity and isinstance(entity, SpeedButton):
                    self.apply_speed_action(entity.action)

        elif event.event_type == MouseEventType.MOUSE_MOTION:
            if self.is_mouse_down:
                if self.is_creating_path and self.path_being_created:
                    if entity and isinstance(entity, Station):
                        self.add_station_to_path(entity)
                    else:
                        self.path_being_created.set_temporary_point(event.position)
            else:
                if entity and isinstance(entity, Button):
                    entity.on_hover()
                else:
                    for button in self.buttons:
                        button.on_exit()

    def react_keyboard_event(self, event: KeyboardEvent) -> None:
        if event.event_type == KeyboardEventType.KEY_UP:
            if event.key == pygame.K_SPACE:
                self.is_paused = not self.is_paused
            elif event.key == pygame.K_1:
                self.set_game_speed(1)
            elif event.key == pygame.K_2:
                self.set_game_speed(2)
            elif event.key == pygame.K_3:
                self.set_game_speed(4)

    def react(self, event: Event | None) -> None:
        if isinstance(event, MouseEvent):
            self.react_mouse_event(event)
        elif isinstance(event, KeyboardEvent):
            self.react_keyboard_event(event)

    def get_containing_entity(self, position: Point):
        for station in self.stations:
            if station.contains(position):
                return station
        for button in self.buttons:
            if button.contains(position):
                return button

    def remove_path(self, path: Path) -> None:
        self._path_lifecycle.remove_path(self, path)

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

    def add_station_to_path(self, station: Station) -> None:
        self._path_lifecycle.add_station_to_path(self, station)

    def abort_path_creation(self) -> None:
        self._path_lifecycle.abort_path_creation(self)

    def release_color_for_path(self, path: Path) -> None:
        self._path_lifecycle.release_color_for_path(self, path)

    def finish_path_creation(self) -> None:
        self._path_lifecycle.finish_path_creation(self, get_metro_factory=lambda: Metro)

    def set_paused(self, paused: bool) -> None:
        self.is_paused = paused

    def set_game_speed(self, speed_multiplier: int) -> None:
        self.game_speed_multiplier = speed_multiplier

    def apply_speed_action(self, action: SpeedAction) -> None:
        if action == "pause":
            self.set_paused(True)
            return
        if action == "speed_1":
            self.set_game_speed(1)
        elif action == "speed_2":
            self.set_game_speed(2)
        elif action == "speed_4":
            self.set_game_speed(4)
        self.set_paused(False)

    def is_speed_button_active(self, action: SpeedAction) -> bool:
        if action == "pause":
            return self.is_paused
        if self.is_paused:
            return False
        if action == "speed_1":
            return self.game_speed_multiplier == 1
        if action == "speed_2":
            return self.game_speed_multiplier == 2
        if action == "speed_4":
            return self.game_speed_multiplier == 4
        return False

    def apply_action(self, action: object) -> bool:
        if self.is_game_over:
            return False
        if not isinstance(action, dict):
            return False
        action_type = action.get("type")
        if not isinstance(action_type, str):
            return False
        if action_type == "create_path":
            stations = action.get("stations", [])
            loop = action.get("loop", False)
            if type(loop) is not bool:
                return False
            return self.create_path_from_station_indices(stations, loop) is not None
        if action_type == "buy_line":
            button_idx = action.get("path_index")
            if button_idx is not None and type(button_idx) is not int:
                return False
            return self.try_purchase_path_button_by_index(button_idx)
        if action_type == "remove_path":
            if "path_id" in action:
                return self.remove_path_by_id(action["path_id"])
            if "path_index" in action:
                return self.remove_path_by_index(action["path_index"])
            return False
        if action_type == "pause":
            self.set_paused(True)
            return True
        if action_type == "resume":
            self.set_paused(False)
            return True
        if action_type == "noop":
            return True
        return False

    def end_path_on_station(self, station: Station) -> None:
        self._path_lifecycle.end_path_on_station(self, station)

    def get_station_shape_types(self) -> List[ShapeType]:
        return list(dict.fromkeys(station.shape.type for station in self.stations))

    def is_passenger_spawn_time(self) -> bool:
        return any(
            self.should_spawn_passenger_at_station(station) for station in self.stations
        )

    def initialize_station_spawning_state(self, stations: List[Station]) -> None:
        for station in stations:
            if station not in self.station_spawn_interval_steps:
                self.station_spawn_interval_steps[station] = (
                    self.get_station_spawn_interval_step()
                )
            if station not in self.station_steps_since_last_spawn:
                self.station_steps_since_last_spawn[station] = (
                    self.station_spawn_interval_steps[station]
                )

    def get_station_spawn_interval_step(self) -> int:
        min_interval = max(1, int(self.passenger_spawning_interval_step * 0.7))
        max_interval = max(
            min_interval, int(self.passenger_spawning_interval_step * 1.3)
        )
        return self.context.python_random.randint(min_interval, max_interval)

    def should_spawn_passenger_at_station(self, station: Station) -> bool:
        self.initialize_station_spawning_state([station])
        return (
            self.steps == self.passenger_spawning_step
            or self.station_steps_since_last_spawn[station]
            >= self.station_spawn_interval_steps[station]
        )

    def spawn_passengers(self) -> None:
        station_types = self.get_station_shape_types()
        for station in self.stations:
            if not self.should_spawn_passenger_at_station(station):
                continue
            other_station_shape_types = [
                shape_type
                for shape_type in station_types
                if shape_type != station.shape.type
            ]
            destination_shape_type = self.context.python_random.choice(
                other_station_shape_types
            )
            destination_shape = get_shape_from_type(
                destination_shape_type, passenger_color, passenger_size
            )
            passenger = Passenger(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)
                self.passengers.append(passenger)
            self.station_steps_since_last_spawn[station] = 0

    def increment_time(self, dt_ms: int) -> None:
        if self.is_paused or self.is_game_over:
            return

        speed_multiplier = self.game_speed_multiplier
        scaled_dt_ms = dt_ms * speed_multiplier

        # record time
        self.time_ms += scaled_dt_ms
        self.steps += speed_multiplier
        self.initialize_station_spawning_state(self.stations)
        for station in self.stations:
            self.station_steps_since_last_spawn[station] += speed_multiplier
            station.prune_visual_effects(self.time_ms)

        # move metros
        station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
        for path in self.paths:
            for metro in path.metros:
                if (
                    metro.current_station is not None
                    and metro.stop_time_remaining_ms <= 0
                ):
                    self.start_station_stop_if_needed(
                        metro,
                        metro.current_station,
                        station_nodes_dict,
                    )
                should_stop_at_next_station = self.should_stop_at_next_station(
                    metro, station_nodes_dict
                )
                path.move_metro(
                    metro,
                    scaled_dt_ms,
                    should_stop_at_next_station=should_stop_at_next_station,
                )
                if metro.just_arrived_and_stopped and metro.current_station is not None:
                    self.start_station_stop_if_needed(
                        metro,
                        metro.current_station,
                        station_nodes_dict,
                    )

        # spawn passengers
        if self.is_passenger_spawn_time():
            self.spawn_passengers()

        self.find_travel_plan_for_passengers()
        self.move_passengers(scaled_dt_ms)
        self.update_waiting_and_game_over(scaled_dt_ms)

    def get_next_station_for_metro(self, metro: Metro) -> Station | None:
        assert metro.current_segment is not None
        if metro.is_forward:
            return metro.current_segment.end_station
        return metro.current_segment.start_station

    def get_boarding_candidates_for_metro(
        self,
        metro: Metro,
        station: Station,
        station_nodes_dict: Dict[Station, Node],
        mutate_travel_plans: bool,
    ) -> List[Passenger]:
        metro_path = self.get_path_by_id(metro.path_id)
        if metro_path is None:
            return []

        candidates: List[Passenger] = []
        for passenger, travel_plan in self._router.iter_boarding_candidates(
            station.passengers,
            get_required_path_id=lambda: metro.path_id,
            get_current_plan=lambda item: self.travel_plans.get(item),
            get_constrained_plan=lambda item: self.get_travel_plan_starting_with_path(
                item, station, metro_path, station_nodes_dict
            ),
        ):
            if travel_plan is not None and mutate_travel_plans:
                self.travel_plans[passenger] = travel_plan
            candidates.append(passenger)
        return candidates

    def get_unloading_candidates_for_metro(
        self, metro: Metro, station: Station
    ) -> tuple[List[Passenger], List[Passenger]]:
        passengers_to_destination: List[Passenger] = []
        passengers_to_transfer: List[Passenger] = []
        for passenger in metro.passengers:
            if station.shape.type == passenger.destination_shape.type:
                passengers_to_destination.append(passenger)
                continue
            travel_plan = self.travel_plans.get(passenger)
            if travel_plan is not None and travel_plan.get_next_station() == station:
                passengers_to_transfer.append(passenger)
        return passengers_to_destination, passengers_to_transfer

    def should_stop_at_next_station(
        self, metro: Metro, station_nodes_dict: Dict[Station, Node]
    ) -> bool:
        if metro.current_segment is None:
            return False
        destination_station = self.get_next_station_for_metro(metro)
        if destination_station is None:
            return False
        unload_to_destination, unload_to_transfer = (
            self.get_unloading_candidates_for_metro(metro, destination_station)
        )
        if unload_to_destination or unload_to_transfer:
            return True
        if not self.can_board_at_station(metro, destination_station):
            return False
        boarding_candidates = self.get_boarding_candidates_for_metro(
            metro,
            destination_station,
            station_nodes_dict,
            mutate_travel_plans=False,
        )
        return len(boarding_candidates) > 0

    def start_station_stop_if_needed(
        self,
        metro: Metro,
        station: Station,
        station_nodes_dict: Dict[Station, Node],
    ) -> None:
        if metro.stop_time_remaining_ms > 0:
            return
        unload_to_destination, unload_to_transfer = (
            self.get_unloading_candidates_for_metro(metro, station)
        )
        num_unload_actions = len(unload_to_destination) + len(unload_to_transfer)
        boarding_candidates = self.get_boarding_candidates_for_metro(
            metro,
            station,
            station_nodes_dict,
            mutate_travel_plans=False,
        )
        num_boarding_actions = 0
        if self.can_board_at_station(metro, station):
            num_boarding_actions = len(boarding_candidates)
        num_actions = num_unload_actions + num_boarding_actions
        if num_actions > 0:
            metro.stop_time_remaining_ms = (
                num_actions * metro.boarding_time_per_passenger_ms
            )
            metro.boarding_progress_ms = 0
            metro.speed = 0

    def can_board_at_station(self, metro: Metro, station: Station) -> bool:
        if metro.has_room():
            return True
        for passenger in metro.passengers:
            if station.shape.type == passenger.destination_shape.type:
                return True
            travel_plan = self.travel_plans.get(passenger)
            if travel_plan is not None and travel_plan.get_next_station() == station:
                return True
        return False

    def move_passengers(self, dt_ms: int) -> None:
        station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
        for metro in self.metros:
            if metro.current_station:
                station = metro.current_station
                unload_to_destination, unload_to_transfer = (
                    self.get_unloading_candidates_for_metro(metro, station)
                )
                boarding_candidates = self.get_boarding_candidates_for_metro(
                    metro,
                    station,
                    station_nodes_dict,
                    mutate_travel_plans=True,
                )
                if metro.stop_time_remaining_ms > 0:
                    active_boarding_dt = min(dt_ms, metro.stop_time_remaining_ms)
                    metro.stop_time_remaining_ms = max(
                        0, metro.stop_time_remaining_ms - dt_ms
                    )
                    metro.boarding_progress_ms += active_boarding_dt
                elif unload_to_destination or unload_to_transfer or boarding_candidates:
                    metro.stop_time_remaining_ms = (
                        len(unload_to_destination)
                        + len(unload_to_transfer)
                        + len(boarding_candidates)
                    ) * metro.boarding_time_per_passenger_ms
                    metro.boarding_progress_ms = 0
                    metro.speed = 0
                    active_boarding_dt = min(dt_ms, metro.stop_time_remaining_ms)
                    metro.stop_time_remaining_ms = max(
                        0, metro.stop_time_remaining_ms - dt_ms
                    )
                    metro.boarding_progress_ms += active_boarding_dt
                boarding_slots = int(
                    metro.boarding_progress_ms // metro.boarding_time_per_passenger_ms
                )
                if boarding_slots > 0:
                    metro.boarding_progress_ms -= (
                        boarding_slots * metro.boarding_time_per_passenger_ms
                    )

                while boarding_slots > 0:
                    unload_to_destination, unload_to_transfer = (
                        self.get_unloading_candidates_for_metro(metro, station)
                    )
                    if unload_to_destination:
                        passenger = unload_to_destination[0]
                        passenger.is_at_destination = True
                        metro.remove_passenger(passenger)
                        self.passengers.remove(passenger)
                        if passenger in self.travel_plans:
                            del self.travel_plans[passenger]
                        self._progression.record_delivery()
                        self.update_unlocked_num_paths()
                        self.update_unlocked_num_stations()
                        boarding_slots -= 1
                        continue

                    if unload_to_transfer and station.has_room():
                        passenger = unload_to_transfer[0]
                        metro.move_passenger(passenger, station)
                        passenger.wait_ms = 0
                        travel_plan = self.travel_plans.get(passenger)
                        if travel_plan is not None:
                            travel_plan.increment_next_station()
                            self.find_next_path_for_passenger_at_station(
                                passenger, station
                            )
                        boarding_slots -= 1
                        continue

                    boarding_candidates = self.get_boarding_candidates_for_metro(
                        metro,
                        station,
                        station_nodes_dict,
                        mutate_travel_plans=True,
                    )
                    if not boarding_candidates:
                        break
                    if not metro.has_room():
                        break
                    passenger = boarding_candidates[0]
                    station.move_passenger(passenger, metro)
                    passenger.wait_ms = 0
                    boarding_slots -= 1

                if (
                    boarding_slots > 0
                    and not unload_to_destination
                    and (not unload_to_transfer or not station.has_room())
                    and (not metro.has_room() or not boarding_candidates)
                ):
                    # Avoid keeping the metro parked when no transfer action can proceed.
                    metro.stop_time_remaining_ms = 0
                    metro.boarding_progress_ms = 0

    def update_waiting_and_game_over(self, dt_ms: int) -> None:
        if self.is_game_over:
            return

        waiting_over_limit = 0
        for station in self.stations:
            for passenger in station.passengers:
                passenger.wait_ms += dt_ms
                if passenger.wait_ms >= self.passenger_max_wait_time_ms:
                    waiting_over_limit += 1

        if waiting_over_limit >= self.overdue_passenger_threshold:
            self.is_game_over = True

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

    def find_travel_plan_for_passengers(self) -> None:
        station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
        for station, rider, route, kind in self._router.iter_bulk_route_proposals(
            self.stations,
            has_travel_plan=lambda item: self.passenger_has_travel_plan(item),
            get_destination_stations=lambda item: self.get_stations_for_shape_type(
                item.destination_shape.type
            ),
            node_map=station_nodes_dict,
            find_node_path=lambda start, end: bfs(start, end),
            get_reduce_node_path=lambda: self.skip_stations_on_same_path,
        ):
            if kind == "arrival":
                station.remove_passenger(rider)
                self.passengers.remove(rider)
                rider.is_at_destination = True
                del self.travel_plans[rider]
            elif kind == "route":
                self.travel_plans[rider] = TravelPlan(route[1:])
                self.find_next_path_for_passenger_at_station(rider, station)
            elif not rider.is_at_destination and rider not in self.travel_plans:
                self.travel_plans[rider] = TravelPlan([])
