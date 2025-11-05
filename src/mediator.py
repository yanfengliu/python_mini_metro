from __future__ import annotations

import math
import pprint
import random
from typing import Dict, List

import pygame

from config import (
    num_metros,
    num_paths,
    num_stations,
    passenger_color,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    score_display_coords,
    score_font_size,
    station_max_passengers,
    overcrowd_time_limit_ms,
    station_spawn_interval
)
from entity.get_entity import get_initial_stations, get_new_random_station
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
pp = pprint.PrettyPrinter(indent=4)


class Mediator:
    def __init__(self) -> None:
        pygame.font.init()

        # configs
        self.passenger_spawning_step = passenger_spawning_start_step
        self.passenger_spawning_interval_step = passenger_spawning_interval_step
        self.num_paths = num_paths
        self.num_metros = num_metros
        self.num_stations = num_stations

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [*self.path_buttons]
        self.font = pygame.font.SysFont("arial", score_font_size)
        self.game_over_font = pygame.font.SysFont("arial", 72)

        # entities
        self.stations = get_initial_stations()
        self.metros: List[Metro] = []
        self.paths: List[Path] = []
        self.passengers: List[Passenger] = []
        self.path_colors: Dict[Color, bool] = {}
        for i in range(num_paths):
            color = hue_to_rgb(i / (num_paths + 1))
            self.path_colors[color] = False  # not taken
        self.path_to_color: Dict[Path, Color] = {}

        # status
        self.time_ms = 0
        self.steps = 0
        self.steps_since_last_spawn = self.passenger_spawning_interval_step + 1
        self.is_mouse_down = False
        self.is_creating_path = False
        self.path_being_created: Path | None = None
        self.travel_plans: TravelPlans = {}
        self.is_paused = False
        self.score = 0
        self.is_game_over = False
        self.steps_since_last_station_spawn = 0
        self.overcrowd_start_times: Dict[Station, int] = {}
        self.is_extending_path = False
        self.original_stations_before_extend: List[Station] = []
        self.is_old_path_looped = False

    def assign_paths_to_buttons(self):
        for path_button in self.path_buttons:
            path_button.remove_path()

        self.path_to_button = {}
        for i in range(min(len(self.paths), len(self.path_buttons))):
            path = self.paths[i]
            button = self.path_buttons[i]
            button.assign_path(path)
            self.path_to_button[path] = button

    def spawn_new_station(self):
        new_station = get_new_random_station()
        self.stations.append(new_station)

    def render(self, screen: pygame.surface.Surface) -> None:
        for idx, path in enumerate(self.paths):
            path_order = idx - round(self.num_paths / 2)
            path.draw(screen, path_order)
        for station in self.stations:
            station.draw(screen)
        for metro in self.metros:
            metro.draw(screen)
        for button in self.buttons:
            button.draw(screen)
        text_surface = self.font.render(f"Score: {self.score}", True, (0, 0, 0))
        screen.blit(text_surface, score_display_coords)

        for station, start_time in self.overcrowd_start_times.items():
            duration = self.time_ms - start_time
            progress_pct = min(duration / overcrowd_time_limit_ms, 1.0)

            try:
                radius = station.size + 5
                center_point = station.position

                rect = pygame.Rect(
                    center_point.left - radius,
                    center_point.top - radius,
                    radius * 2,
                    radius * 2,
                )
                
                start_angle = math.pi / 2
                end_angle = (math.pi / 2) + (2 * math.pi * progress_pct)
                pygame.draw.arc(screen, (255, 0, 0), rect, start_angle, end_angle, 3)
            except AttributeError:
                pass

        if self.is_game_over:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            
            text_surface = self.game_over_font.render(
                "GAME OVER", True, (255, 0, 0)
            )
            text_rect = text_surface.get_rect(
                center=(screen.get_width() / 2, screen.get_height() / 2)
            )
            screen.blit(text_surface, text_rect)

    def react_mouse_event(self, event: MouseEvent):
        entity = self.get_containing_entity(event.position)

        if event.event_type == MouseEventType.MOUSE_DOWN:
            self.is_mouse_down = True
            if entity:
                if isinstance(entity, Station):
                    if self.is_creating_path:
                        return

                    path_to_extend = None
                    is_extending_from_start = False

                    for path in self.paths:
                        if not path.stations:
                            continue

                        if path.stations[0] == entity:
                            path_to_extend = path
                            is_extending_from_start = True
                            break
                        elif path.stations[-1] == entity:
                            if path.is_looped:
                                continue
                            path_to_extend = path
                            is_extending_from_start = False
                            break
                    
                    if path_to_extend:
                        self.is_creating_path = True
                        self.is_extending_path = True
                        self.path_being_created = path_to_extend
                        
                        self.original_stations_before_extend = list(path_to_extend.stations)
                        self.is_old_path_looped = path_to_extend.is_looped
                        
                        if is_extending_from_start:
                            path_to_extend.stations.reverse()
                        
                        if path_to_extend.is_looped:
                            path_to_extend.remove_loop()
                            
                        path_to_extend.is_being_created = True
                        path_to_extend.remove_temporary_point()
                    else:
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

    def react_keyboard_event(self, event: KeyboardEvent):
        if event.event_type == KeyboardEventType.KEY_UP:
            if event.key == pygame.K_SPACE:
                self.is_paused = not self.is_paused

    def react(self, event: Event | None):
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

    def remove_path(self, path: Path):
        self.path_to_button[path].remove_path()
        for metro in path.metros:
            for passenger in metro.passengers:
                self.passengers.remove(passenger)
            self.metros.remove(metro)
        self.release_color_for_path(path)
        self.paths.remove(path)
        self.assign_paths_to_buttons()
        self.find_travel_plan_for_passengers()

    def start_path_on_station(self, station: Station) -> None:
        if len(self.paths) < self.num_paths:
            self.is_creating_path = True
            assigned_color = (0, 0, 0)
            for path_color, taken in self.path_colors.items():
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

    def add_station_to_path(self, station: Station) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.stations[-1] == station:
            return

        if (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] == station
        ):
            self.path_being_created.set_loop()
            return

        if station in self.path_being_created.stations:
            return

        # Any loop should be removed
        if self.path_being_created.is_looped:
            self.path_being_created.remove_loop()
        self.path_being_created.add_station(station)

    def abort_path_creation(self) -> None:
        assert self.path_being_created is not None
        self.is_creating_path = False
        if self.is_extending_path:
            self.path_being_created.stations = self.original_stations_before_extend
            if self.is_old_path_looped:
                self.path_being_created.set_loop()
            else:
                self.path_being_created.remove_loop()
            
            self.path_being_created.is_being_created = False
            self.path_being_created.remove_temporary_point()
        else:
            self.release_color_for_path(self.path_being_created)
            self.paths.remove(self.path_being_created)
        self.is_extending_path = False
        self.original_stations_before_extend = []
        self.is_old_path_looped = False
        self.path_being_created = None

    def release_color_for_path(self, path: Path) -> None:
        self.path_colors[path.color] = False
        del self.path_to_color[path]

    def finish_path_creation(self) -> None:
        assert self.path_being_created is not None
        was_new_path = not self.is_extending_path
        self.is_creating_path = False
        self.is_extending_path = False
        self.original_stations_before_extend = []
        self.is_old_path_looped = False
        self.path_being_created.is_being_created = False
        self.path_being_created.remove_temporary_point()
        if was_new_path and len(self.metros) < self.num_metros:
            metro = Metro()
            self.path_being_created.add_metro(metro)
            self.metros.append(metro)
        self.path_being_created = None
        self.assign_paths_to_buttons()

    def end_path_on_station(self, station: Station) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.stations[-1] == station:
            if len(self.path_being_created.stations) > 1:
                self.finish_path_creation()
            else:
                self.abort_path_creation()
            return
        if (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] == station
        ):
            self.path_being_created.set_loop()
            self.finish_path_creation()
            return
        if station in self.path_being_created.stations:
            self.abort_path_creation()
            return
        self.path_being_created.add_station(station)
        self.finish_path_creation()

    def get_station_shape_types(self):
        station_shape_types: List[ShapeType] = []
        for station in self.stations:
            if station.shape.type not in station_shape_types:
                station_shape_types.append(station.shape.type)
        return station_shape_types

    def is_passenger_spawn_time(self) -> bool:
        return (
            self.steps == self.passenger_spawning_step
            or self.steps_since_last_spawn == self.passenger_spawning_interval_step
        )

    def spawn_passengers(self):
        for station in self.stations:
            station_types = self.get_station_shape_types()
            other_station_shape_types = [
                x for x in station_types if x != station.shape.type
            ]
            destination_shape_type = random.choice(other_station_shape_types)
            destination_shape = get_shape_from_type(
                destination_shape_type, passenger_color, passenger_size
            )
            passenger = Passenger(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)
                self.passengers.append(passenger)

    def increment_time(self, dt_ms: int) -> None:
        if self.is_paused or self.is_game_over:
            return

        # record time
        self.time_ms += dt_ms
        self.steps += 1
        self.steps_since_last_spawn += 1
        self.steps_since_last_station_spawn += 1

        stations_to_reset_timer = []
        for station in self.stations:
            if len(station.passengers) > station_max_passengers:
                if station not in self.overcrowd_start_times:
                    self.overcrowd_start_times[station] = self.time_ms
                else:
                    duration = self.time_ms - self.overcrowd_start_times[station]
                    if duration >= overcrowd_time_limit_ms:
                        self.is_game_over = True
                        break
            else:
                if station in self.overcrowd_start_times:
                    stations_to_reset_timer.append(station)

        for station in stations_to_reset_timer:
            del self.overcrowd_start_times[station]

        # move metros
        for path in self.paths:
            for metro in path.metros:
                path.move_metro(metro, dt_ms)

        # spawn passengers
        if self.is_passenger_spawn_time():
            self.spawn_passengers()
            self.steps_since_last_spawn = 0

        # spawn stations
        if self.steps_since_last_station_spawn >= station_spawn_interval:
            self.spawn_new_station()
            self.steps_since_last_station_spawn = 0

        self.find_travel_plan_for_passengers()
        self.move_passengers()

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

                for passenger in passengers_from_metro_to_station:
                    if metro.current_station.has_room():
                        metro.move_passenger(passenger, metro.current_station)
                        self.travel_plans[passenger].increment_next_station()
                        self.find_next_path_for_passenger_at_station(
                            passenger, metro.current_station
                        )

                for passenger in passengers_from_station_to_metro:
                    if metro.has_room():
                        metro.current_station.move_passenger(passenger, metro)

    def get_stations_for_shape_type(self, shape_type: ShapeType):
        stations: List[Station] = []
        for station in self.stations:
            if station.shape.type == shape_type:
                stations.append(station)
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
