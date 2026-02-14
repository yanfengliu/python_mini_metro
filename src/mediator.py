from __future__ import annotations

import random
from typing import Dict, List

import pygame
from config import (
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
from ui.path_button import PathButton, get_path_buttons
from utils import get_shape_from_type, hue_to_rgb

TravelPlans = Dict[Passenger, TravelPlan]
class Mediator:
    def __init__(self) -> None:
        pygame.font.init()

        # configs
        self.passenger_spawning_step = passenger_spawning_start_step
        self.passenger_spawning_interval_step = passenger_spawning_interval_step
        self.num_paths = num_paths
        self.path_unlock_milestones = sorted(path_unlock_milestones)
        self.num_metros = num_metros
        self.num_stations = num_stations
        self.initial_num_stations = initial_num_stations
        self.station_unlock_milestones = sorted(station_unlock_milestones)

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [*self.path_buttons]
        self.font = pygame.font.SysFont("arial", score_font_size)
        self.game_over_font = pygame.font.SysFont("arial", game_over_font_size)
        self.game_over_hint_font = pygame.font.SysFont(
            "arial", game_over_hint_font_size
        )
        self.game_over_restart_rect: pygame.Rect | None = None
        self.game_over_exit_rect: pygame.Rect | None = None

        # entities
        self.all_stations = self.get_initial_station_pool()
        self.stations = self.all_stations[: self.initial_num_stations]
        self.metros: List[Metro] = []
        self.paths: List[Path] = []
        self.passengers: List[Passenger] = []
        self.path_colors: Dict[Color, bool] = {}
        for _ in range(num_paths):
            color = hue_to_rgb(random.random())
            while color in self.path_colors:
                color = hue_to_rgb(random.random())
            self.path_colors[color] = False  # not taken
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
        self.score = 0
        self.total_travels_handled = 0
        self.unlocked_num_paths = self.get_unlocked_num_paths()
        self.unlocked_num_stations = self.get_unlocked_num_stations()
        self.update_path_button_lock_states()
        self.is_game_over = False
        self.passenger_max_wait_time_ms = passenger_max_wait_time_ms
        self.max_waiting_passengers = max_waiting_passengers

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
        self.unlocked_num_stations = self.get_unlocked_num_stations()
        if self.unlocked_num_stations > len(self.stations):
            self.stations = self.all_stations[: self.unlocked_num_stations]

    def get_unlocked_num_paths(self) -> int:
        return max(
            1,
            sum(
                1
                for milestone in self.path_unlock_milestones
                if self.total_travels_handled >= milestone
            ),
        )

    def update_unlocked_num_paths(self) -> None:
        self.unlocked_num_paths = self.get_unlocked_num_paths()
        self.update_path_button_lock_states()

    def update_path_button_lock_states(self) -> None:
        for idx, button in enumerate(self.path_buttons):
            button.set_locked(idx >= self.unlocked_num_paths)

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

    def render(self, screen: pygame.surface.Surface) -> None:
        active_path_count = len(self.paths)
        for idx, path in enumerate(self.paths):
            # Keep active paths centered so a single path has zero offset.
            path_order = idx - (active_path_count // 2)
            path.draw(screen, path_order)
        for station in self.stations:
            station.draw(screen)
        for metro in self.metros:
            metro.draw(screen)
        for button in self.buttons:
            button.draw(screen)
        text_surface = self.font.render(f"Score: {self.score}", True, (0, 0, 0))
        screen.blit(text_surface, score_display_coords)
        if self.is_game_over:
            self.render_game_over(screen)

    def render_game_over(self, screen: pygame.surface.Surface) -> None:
        self.game_over_restart_rect = None
        self.game_over_exit_rect = None
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill(game_over_overlay_color)
        screen.blit(overlay, (0, 0))

        title_surface = self.game_over_font.render(
            "Game Over", True, game_over_text_color
        )
        title_rect = title_surface.get_rect(
            center=(screen_width // 2, screen_height // 2 - game_over_font_size // 3)
        )
        screen.blit(title_surface, title_rect)

        score_surface = self.font.render(
            f"Final Score: {self.score}", True, game_over_text_color
        )
        score_rect = score_surface.get_rect(
            center=(screen_width // 2, screen_height // 2 + game_over_font_size // 3)
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
        start_top = screen_height // 2 + game_over_font_size // 3 + 40
        current_top = start_top

        for surface, (_, action) in zip(button_surfaces, button_texts):
            rect = pygame.Rect(
                0,
                0,
                button_width + 2 * game_over_button_padding_x,
                button_height + 2 * game_over_button_padding_y,
            )
            rect.centerx = screen_width // 2
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
        # non-loop
        elif self.path_being_created.stations[0] != station:
            if self.path_being_created.is_looped:
                self.path_being_created.remove_loop()
            self.path_being_created.add_station(station)

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

    def apply_action(self, action: Dict) -> bool:
        action_type = action.get("type")
        if action_type == "create_path":
            stations = action.get("stations", [])
            loop = bool(action.get("loop", False))
            return self.create_path_from_station_indices(stations, loop) is not None
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

        # record time
        self.time_ms += dt_ms
        self.steps += 1
        self.initialize_station_spawning_state(self.stations)
        for station in self.stations:
            self.station_steps_since_last_spawn[station] += 1

        # move metros
        for path in self.paths:
            for metro in path.metros:
                path.move_metro(metro, dt_ms)

        # spawn passengers
        if self.is_passenger_spawn_time():
            self.spawn_passengers()

        self.find_travel_plan_for_passengers()
        self.move_passengers()
        self.update_waiting_and_game_over(dt_ms)

    def move_passengers(self) -> None:
        for metro in self.metros:
            if metro.current_station:
                passengers_to_remove = []
                passengers_from_metro_to_station = []
                passengers_from_station_to_metro = []

                # queue
                for passenger in metro.passengers:
                    if (
                        metro.current_station.shape.type
                        == passenger.destination_shape.type
                    ):
                        passengers_to_remove.append(passenger)
                    elif (
                        self.travel_plans[passenger].get_next_station()
                        == metro.current_station
                    ):
                        passengers_from_metro_to_station.append(passenger)
                for passenger in metro.current_station.passengers:
                    if (
                        self.travel_plans[passenger].next_path
                        and self.travel_plans[passenger].next_path.id == metro.path_id  # type: ignore
                    ):
                        passengers_from_station_to_metro.append(passenger)

                # process
                for passenger in passengers_to_remove:
                    passenger.is_at_destination = True
                    metro.remove_passenger(passenger)
                    self.passengers.remove(passenger)
                    del self.travel_plans[passenger]
                    self.score += 1
                    self.total_travels_handled += 1
                    self.update_unlocked_num_paths()
                    self.update_unlocked_num_stations()

                for passenger in passengers_from_metro_to_station:
                    if metro.current_station.has_room():
                        metro.move_passenger(passenger, metro.current_station)
                        passenger.wait_ms = 0
                        self.travel_plans[passenger].increment_next_station()
                        self.find_next_path_for_passenger_at_station(
                            passenger, metro.current_station
                        )

                for passenger in passengers_from_station_to_metro:
                    if metro.has_room():
                        metro.current_station.move_passenger(passenger, metro)
                        passenger.wait_ms = 0

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
                    should_set_null_path = True
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
                            should_set_null_path = False
                            break
                        elif len(node_path) > 1:
                            node_path = self.skip_stations_on_same_path(node_path)
                            self.travel_plans[passenger] = TravelPlan(node_path[1:])
                            self.find_next_path_for_passenger_at_station(
                                passenger, station
                            )
                            should_set_null_path = False
                            break
                    if should_set_null_path:
                        self.travel_plans[passenger] = TravelPlan([])
