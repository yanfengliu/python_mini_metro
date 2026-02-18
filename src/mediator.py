from __future__ import annotations

import random
from typing import Dict, List

import pygame
from config import (
    font_name,
    max_waiting_passengers,
    initial_num_stations,
    num_metros,
    num_paths,
    path_unlock_milestones,
    station_unlock_milestones,
    num_stations,
    passenger_color,
    passenger_max_wait_time_ms,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    game_over_font_size,
    game_over_hint_font_size,
    game_over_button_border_color,
    game_over_button_border_width,
    game_over_button_color,
    game_over_button_padding_x,
    game_over_button_padding_y,
    game_over_button_spacing,
    game_over_overlay_color,
    game_over_text_color,
    score_display_coords,
    score_font_size,
    screen_height,
    screen_width,
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
    def __init__(self) -> None:
        pygame.font.init()

        # configs
        self.passenger_spawning_step = passenger_spawning_start_step
        self.passenger_spawning_interval_step = passenger_spawning_interval_step
        self.num_paths = num_paths
        self.path_unlock_milestones = sorted(path_unlock_milestones)
        self.path_purchase_prices = self.get_path_purchase_prices()
        self.num_metros = num_metros
        self.num_stations = num_stations
        self.initial_num_stations = initial_num_stations
        self.station_unlock_milestones = sorted(station_unlock_milestones)

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.speed_buttons = get_speed_buttons()
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [*self.path_buttons, *self.speed_buttons]
        self.font = pygame.font.SysFont(font_name, score_font_size)
        self.game_over_font = pygame.font.SysFont(font_name, game_over_font_size)
        self.game_over_hint_font = pygame.font.SysFont(
            font_name, game_over_hint_font_size
        )
        self.game_over_restart_rect: pygame.Rect | None = None
        self.game_over_exit_rect: pygame.Rect | None = None

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
        self.score = 0
        self.total_travels_handled = 0
        self.purchased_num_paths = 1
        self.unlocked_num_paths = self.get_unlocked_num_paths()
        self.unlocked_num_stations = self.get_unlocked_num_stations()
        self.update_path_button_lock_states()
        self.is_game_over = False
        self.passenger_max_wait_time_ms = passenger_max_wait_time_ms
        self.max_waiting_passengers = max_waiting_passengers

    def generate_distinct_path_colors(self, path_count: int) -> Dict[Color, bool]:
        if path_count <= 0:
            return {}
        selected_hues: List[float] = [random.random()]
        candidate_count = 24
        while len(selected_hues) < path_count:
            candidate_hues = [random.random() for _ in range(candidate_count)]
            candidate_hues.append(random.random())
            selected_hues.append(pick_distinct_hue(selected_hues, candidate_hues))
        path_colors: Dict[Color, bool] = {}
        for hue in selected_hues:
            path_colors[hue_to_rgb(hue, saturation=0.6, value=0.9)] = False
        while len(path_colors) < path_count:
            path_colors[hue_to_rgb(random.random(), saturation=0.6, value=0.9)] = False
        return path_colors

    def get_path_purchase_prices(self) -> List[int]:
        if self.num_paths <= 1:
            return []
        return [
            self.path_unlock_milestones[idx] - self.path_unlock_milestones[idx - 1]
            for idx in range(1, self.num_paths)
        ]

    def get_initial_station_pool(self) -> List[Station]:
        # Keep initial gameplay valid by guaranteeing at least two shape types.
        while True:
            stations = get_random_stations(self.num_stations)
            initial_shapes = {
                station.shape.type
                for station in stations[: self.initial_num_stations]
            }
            if len(initial_shapes) >= 2:
                return stations

    def get_unlocked_num_stations(self) -> int:
        unlocked = self.initial_num_stations + sum(
            1
            for milestone in self.station_unlock_milestones
            if self.total_travels_handled >= milestone
        )
        return min(unlocked, self.num_stations)

    def update_unlocked_num_stations(self) -> None:
        previous_unlocked_num_stations = self.unlocked_num_stations
        self.unlocked_num_stations = self.get_unlocked_num_stations()
        if self.unlocked_num_stations > len(self.stations):
            newly_unlocked_stations = self.all_stations[
                len(self.stations) : self.unlocked_num_stations
            ]
            self.stations = self.all_stations[: self.unlocked_num_stations]
            if self.unlocked_num_stations > previous_unlocked_num_stations:
                for station in newly_unlocked_stations:
                    station.start_unlock_blink(self.time_ms)

    def get_unlocked_num_paths(self) -> int:
        return min(max(1, self.purchased_num_paths), self.num_paths)

    def update_unlocked_num_paths(self) -> None:
        previous_unlocked_num_paths = self.unlocked_num_paths
        self.unlocked_num_paths = self.get_unlocked_num_paths()
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
        if self.unlocked_num_paths >= self.num_paths:
            return None
        return self.unlocked_num_paths

    def get_purchase_price_for_path_button_idx(self, button_idx: int) -> int | None:
        if button_idx <= 0 or button_idx >= self.num_paths:
            return None
        return self.path_purchase_prices[button_idx - 1]

    def can_purchase_path_button_idx(self, button_idx: int) -> bool:
        next_button_idx = self.get_next_path_button_idx_to_purchase()
        if next_button_idx is None or next_button_idx != button_idx:
            return False
        price = self.get_purchase_price_for_path_button_idx(button_idx)
        return price is not None and self.score >= price

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
        self.score -= price
        self.purchased_num_paths += 1
        self.update_unlocked_num_paths()
        return True

    def try_purchase_path_button_by_index(
        self, button_idx: int | None = None
    ) -> bool:
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
        for path_button in self.path_buttons:
            path_button.remove_path()

        self.path_to_button = {}
        for path, button in zip(self.paths, self.path_buttons):
            button.assign_path(path)
            self.path_to_button[path] = button
        self.update_path_button_lock_states()

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

    def render(self, screen: pygame.surface.Surface) -> None:
        width, height = self.get_surface_size(screen)
        update_path_button_positions(self.path_buttons, width, height)
        update_speed_button_positions(self.speed_buttons, width, height)
        active_path_count = len(self.paths)
        for idx, path in enumerate(self.paths):
            # Keep active paths centered so a single path has zero offset.
            path_order = idx - (active_path_count // 2)
            path.draw(screen, path_order)
        for station in self.stations:
            station.draw(
                screen,
                self.time_ms,
                passenger_max_wait_time_ms=self.passenger_max_wait_time_ms,
            )
        for metro in self.metros:
            metro.draw(screen)
        for button in self.buttons:
            if isinstance(button, PathButton):
                button_idx = self.path_buttons.index(button)
                button.draw(
                    screen,
                    self.time_ms,
                    locked_purchase_price=self.get_purchase_price_for_path_button_idx(
                        button_idx
                    ),
                    locked_purchase_affordable=self.can_purchase_path_button_idx(
                        button_idx
                    ),
                )
            elif isinstance(button, SpeedButton):
                button.draw(
                    screen,
                    self.time_ms,
                    is_active=self.is_speed_button_active(button.action),
                )
            else:
                button.draw(screen, self.time_ms)
        text_surface = self.font.render(f"Score: {self.score}", True, (0, 0, 0))
        screen.blit(text_surface, score_display_coords)
        if self.is_game_over:
            self.render_game_over(screen)

    def render_game_over(self, screen: pygame.surface.Surface) -> None:
        self.game_over_restart_rect = None
        self.game_over_exit_rect = None
        width, height = self.get_surface_size(screen)
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(game_over_overlay_color)
        screen.blit(overlay, (0, 0))

        title_surface = self.game_over_font.render(
            "Game Over", True, game_over_text_color
        )
        title_rect = title_surface.get_rect(
            center=(width // 2, height // 2 - game_over_font_size // 3)
        )
        screen.blit(title_surface, title_rect)

        score_surface = self.font.render(
            f"Final Score: {self.score}", True, game_over_text_color
        )
        score_rect = score_surface.get_rect(
            center=(width // 2, height // 2 + game_over_font_size // 3)
        )
        screen.blit(score_surface, score_rect)

        button_texts = [
            ("Restart (R)", "restart"),
            ("Exit (Esc)", "exit"),
        ]
        button_surfaces = [
            self.game_over_hint_font.render(text, True, game_over_text_color)
            for text, _ in button_texts
        ]
        button_width = max(surface.get_width() for surface in button_surfaces)
        button_height = max(surface.get_height() for surface in button_surfaces)
        start_top = height // 2 + game_over_font_size // 3 + 40
        current_top = start_top

        for surface, (_, action) in zip(button_surfaces, button_texts):
            rect = pygame.Rect(
                0,
                0,
                button_width + 2 * game_over_button_padding_x,
                button_height + 2 * game_over_button_padding_y,
            )
            rect.centerx = width // 2
            rect.top = current_top
            current_top = rect.bottom + game_over_button_spacing

            pygame.draw.rect(screen, game_over_button_color, rect, border_radius=8)
            pygame.draw.rect(
                screen,
                game_over_button_border_color,
                rect,
                game_over_button_border_width,
                border_radius=8,
            )
            text_rect = surface.get_rect(center=rect.center)
            screen.blit(surface, text_rect)

            if action == "restart":
                self.game_over_restart_rect = rect
            elif action == "exit":
                self.game_over_exit_rect = rect

    def handle_game_over_click(self, position: Point) -> str | None:
        if not self.is_game_over:
            return None
        if (
            self.game_over_restart_rect
            and self.game_over_restart_rect.collidepoint(position.to_tuple())
        ):
            return "restart"
        if (
            self.game_over_exit_rect
            and self.game_over_exit_rect.collidepoint(position.to_tuple())
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
        self.path_to_button[path].remove_path()
        for metro in path.metros:
            for passenger in metro.passengers:
                self.passengers.remove(passenger)
            self.metros.remove(metro)
        self.release_color_for_path(path)
        self.paths.remove(path)
        self.assign_paths_to_buttons()
        self.find_travel_plan_for_passengers()

    def remove_path_by_id(self, path_id: str) -> bool:
        for path in self.paths:
            if path.id == path_id:
                self.remove_path(path)
                return True
        return False

    def remove_path_by_index(self, path_index: int) -> bool:
        if 0 <= path_index < len(self.paths):
            self.remove_path(self.paths[path_index])
            return True
        return False

    def start_path_on_station(self, station: Station) -> None:
        if len(self.paths) < self.unlocked_num_paths:
            self.is_creating_path = True
            assigned_color = (0, 0, 0)
            available_colors = list(self.path_colors.keys())[: self.unlocked_num_paths]
            for path_color in available_colors:
                taken = self.path_colors[path_color]
                if not taken:
                    assigned_color = path_color
                    self.path_colors[path_color] = True
                    break
            path = Path(assigned_color)
            self.path_to_color[path] = assigned_color
            path.add_station(station)
            path.is_being_created = True
            self.path_being_created = path
            self.paths.append(path)

    def create_path_from_station_indices(
        self, station_indices: List[int], loop: bool = False
    ) -> Path | None:
        if len(station_indices) < 2 or len(self.paths) >= self.unlocked_num_paths:
            return None
        if any(
            idx < 0 or idx >= len(self.stations) for idx in station_indices
        ):
            return None

        self.start_path_on_station(self.stations[station_indices[0]])
        if not self.path_being_created:
            return None

        for idx in station_indices[1:-1]:
            self.add_station_to_path(self.stations[idx])

        if loop:
            self.end_path_on_station(self.stations[station_indices[0]])
        else:
            self.end_path_on_station(self.stations[station_indices[-1]])

        return self.paths[-1] if self.paths else None

    def add_station_to_path(self, station: Station) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.stations[-1] == station:
            return
        # loop
        if (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] == station
        ):
            self.path_being_created.set_loop()
            station.start_snap_blip(self.time_ms, self.path_being_created.color)
        # non-loop
        elif self.path_being_created.stations[0] != station:
            if self.path_being_created.is_looped:
                self.path_being_created.remove_loop()
            self.path_being_created.add_station(station)
            station.start_snap_blip(self.time_ms, self.path_being_created.color)

    def abort_path_creation(self) -> None:
        assert self.path_being_created is not None
        self.is_creating_path = False
        self.release_color_for_path(self.path_being_created)
        self.paths.remove(self.path_being_created)
        self.path_being_created = None

    def release_color_for_path(self, path: Path) -> None:
        self.path_colors[path.color] = False
        del self.path_to_color[path]

    def finish_path_creation(self) -> None:
        assert self.path_being_created is not None
        self.is_creating_path = False
        self.path_being_created.is_being_created = False
        self.path_being_created.remove_temporary_point()
        if len(self.metros) < self.num_metros:
            metro = Metro()
            self.path_being_created.add_metro(metro)
            self.metros.append(metro)
        self.path_being_created = None
        self.assign_paths_to_buttons()

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

    def apply_action(self, action: Dict) -> bool:
        action_type = action.get("type")
        if action_type == "create_path":
            stations = action.get("stations", [])
            loop = bool(action.get("loop", False))
            return self.create_path_from_station_indices(stations, loop) is not None
        if action_type == "buy_line":
            button_idx = action.get("path_index")
            if button_idx is not None and not isinstance(button_idx, int):
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
        if action_type == "noop" or action_type is None:
            return True
        return False

    def end_path_on_station(self, station: Station) -> None:
        assert self.path_being_created is not None
        # current station de-dupe
        if (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[-1] == station
        ):
            self.finish_path_creation()
        # loop
        elif (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] == station
        ):
            self.path_being_created.set_loop()
            self.finish_path_creation()
        # non-loop
        elif self.path_being_created.stations[0] != station:
            self.path_being_created.add_station(station)
            station.start_snap_blip(self.time_ms, self.path_being_created.color)
            self.finish_path_creation()
        else:
            self.abort_path_creation()

    def get_station_shape_types(self) -> List[ShapeType]:
        return list(dict.fromkeys(station.shape.type for station in self.stations))

    def is_passenger_spawn_time(self) -> bool:
        return any(self.should_spawn_passenger_at_station(station) for station in self.stations)

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
        max_interval = max(min_interval, int(self.passenger_spawning_interval_step * 1.3))
        return random.randint(min_interval, max_interval)

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
            destination_shape_type = random.choice(other_station_shape_types)
            destination_shape = get_shape_from_type(
                destination_shape_type, passenger_color, passenger_size
            )
            passenger = Passenger(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)
                self.passengers.append(passenger)
            self.station_steps_since_last_spawn[station] = 0

    def increment_time(self, dt_ms: int) -> None:
        if self.is_paused:
            return

        speed_multiplier = self.game_speed_multiplier
        scaled_dt_ms = dt_ms * speed_multiplier

        # record time
        self.time_ms += scaled_dt_ms
        self.steps += speed_multiplier
        self.initialize_station_spawning_state(self.stations)
        for station in self.stations:
            self.station_steps_since_last_spawn[station] += speed_multiplier

        # move metros
        station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
        for path in self.paths:
            for metro in path.metros:
                if metro.current_station is not None and metro.stop_time_remaining_ms <= 0:
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
        for passenger in station.passengers:
            current_travel_plan = self.travel_plans.get(passenger)
            if (
                current_travel_plan
                and current_travel_plan.next_path
                and current_travel_plan.next_path.id == metro.path_id
            ):
                candidates.append(passenger)
                continue

            travel_plan_for_arriving_metro = self.get_travel_plan_starting_with_path(
                passenger,
                station,
                metro_path,
                station_nodes_dict,
            )
            if travel_plan_for_arriving_metro is not None:
                if mutate_travel_plans:
                    self.travel_plans[passenger] = travel_plan_for_arriving_metro
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
        unload_to_destination, unload_to_transfer = self.get_unloading_candidates_for_metro(
            metro, station
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
            if (
                travel_plan is not None
                and travel_plan.get_next_station() == station
            ):
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
                        (
                            len(unload_to_destination)
                            + len(unload_to_transfer)
                            + len(boarding_candidates)
                        )
                        * metro.boarding_time_per_passenger_ms
                    )
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
                        self.score += 1
                        self.total_travels_handled += 1
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

        if waiting_over_limit >= self.max_waiting_passengers:
            self.is_game_over = True

    def get_stations_for_shape_type(self, shape_type: ShapeType) -> List[Station]:
        stations = [
            station for station in self.stations if station.shape.type == shape_type
        ]
        random.shuffle(stations)

        return stations

    def find_shared_path(self, station_a: Station, station_b: Station) -> Path | None:
        for path in self.paths:
            stations = path.stations
            if (station_a in stations) and (station_b in stations):
                return path
        return None

    def passenger_has_travel_plan(self, passenger: Passenger) -> bool:
        return (
            passenger in self.travel_plans
            and self.travel_plans[passenger].next_path is not None
        )

    def find_next_path_for_passenger_at_station(
        self, passenger: Passenger, station: Station
    ):
        next_station = self.travel_plans[passenger].get_next_station()
        assert next_station is not None
        next_path = self.find_shared_path(station, next_station)
        self.travel_plans[passenger].next_path = next_path

    def get_path_by_id(self, path_id: str) -> Path | None:
        for path in self.paths:
            if path.id == path_id:
                return path
        return None

    def get_travel_plan_starting_with_path(
        self,
        passenger: Passenger,
        station: Station,
        required_first_path: Path,
        station_nodes_dict: Dict[Station, Node],
    ) -> TravelPlan | None:
        possible_dst_stations = self.get_stations_for_shape_type(
            passenger.destination_shape.type
        )
        best_node_path: List[Node] | None = None
        best_path_cost: tuple[int, int] | None = None
        start = station_nodes_dict[station]
        for possible_dst_station in possible_dst_stations:
            end = station_nodes_dict[possible_dst_station]
            node_path = bfs(start, end)
            if len(node_path) <= 1:
                continue
            reduced_node_path = self.skip_stations_on_same_path(list(node_path))
            if len(reduced_node_path) <= 1:
                continue
            first_hop_path = self.find_shared_path(
                station, reduced_node_path[1].station
            )
            if (
                first_hop_path is None
                or first_hop_path.id != required_first_path.id
            ):
                continue
            candidate_cost = (len(node_path), len(reduced_node_path))
            if best_path_cost is None or candidate_cost < best_path_cost:
                best_path_cost = candidate_cost
                best_node_path = reduced_node_path

        if best_node_path is None:
            return None
        travel_plan = TravelPlan(best_node_path[1:])
        next_station = travel_plan.get_next_station()
        if next_station is None:
            return None
        travel_plan.next_path = self.find_shared_path(station, next_station)
        return travel_plan

    def skip_stations_on_same_path(self, node_path: List[Node]):
        assert len(node_path) >= 2
        if len(node_path) == 2:
            return node_path
        else:
            nodes_to_remove = []
            i = 0
            j = 1
            path_set_list = [x.paths for x in node_path]
            path_set_list.append(set())
            while j <= len(path_set_list) - 1:
                set_a = path_set_list[i]
                set_b = path_set_list[j]
                if set_a & set_b:
                    j += 1
                else:
                    for k in range(i + 1, j - 1):
                        nodes_to_remove.append(node_path[k])
                    i = j - 1
                    j += 1
            for node in nodes_to_remove:
                node_path.remove(node)
        return node_path

    def find_travel_plan_for_passengers(self) -> None:
        station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
        for station in self.stations:
            for passenger in station.passengers:
                if not self.passenger_has_travel_plan(passenger):
                    possible_dst_stations = self.get_stations_for_shape_type(
                        passenger.destination_shape.type
                    )
                    best_node_path: List[Node] | None = None
                    best_path_cost: tuple[int, int] | None = None
                    for possible_dst_station in possible_dst_stations:
                        start = station_nodes_dict[station]
                        end = station_nodes_dict[possible_dst_station]
                        node_path = bfs(start, end)
                        if len(node_path) == 1:
                            # passenger arrived at destination
                            station.remove_passenger(passenger)
                            self.passengers.remove(passenger)
                            passenger.is_at_destination = True
                            del self.travel_plans[passenger]
                            best_node_path = None
                            break
                        elif len(node_path) > 1:
                            # Prefer the shortest reachable destination route so
                            # passengers board metros that can deliver them sooner.
                            reduced_node_path = self.skip_stations_on_same_path(
                                list(node_path)
                            )
                            candidate_cost = (len(node_path), len(reduced_node_path))
                            if (
                                best_path_cost is None
                                or candidate_cost < best_path_cost
                            ):
                                best_path_cost = candidate_cost
                                best_node_path = reduced_node_path

                    if best_node_path is not None:
                        self.travel_plans[passenger] = TravelPlan(best_node_path[1:])
                        self.find_next_path_for_passenger_at_station(passenger, station)
                    elif (
                        not passenger.is_at_destination and passenger not in self.travel_plans
                    ):
                        self.travel_plans[passenger] = TravelPlan([])
