from __future__ import annotations

from ast import Tuple
from enum import Enum
import pprint
from random import Random
import random
import time
from typing import Dict, List, Set

import pygame

from config import (
    num_metros,
    num_paths,
    num_stations_max,
    passenger_color,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    score_display_coords,
    score_font_size,
    station_spawning_interval_step,
)
from entity.get_entity import get_station_at_grid
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
from geometry.utils import distance
from graph.graph_algo import bfs, build_station_nodes_dict
from graph.node import Node
from travel_plan import TravelPlan
from type import Color
from ui.button import Button
from ui.path_button import PathButton, get_path_buttons
from utils import get_shape_from_type, hue_to_rgb, get_random_grid_seqs

TravelPlans = Dict[Passenger, TravelPlan]
pp = pprint.PrettyPrinter(indent=4)

class MeditatorState(Enum):
    ENDED=0,
    PAUSED=1,
    RUNNING=2,
    NEW_STATION=3

class Mediator:
    def __init__(self, gamespeed: int = 1, gen_stations_first=False) -> None:
        pygame.font.init()

        self.gamespeed = gamespeed
        self.seed = time.time()
        self.gen_stations_first = gen_stations_first

        self.reset_progress()

    def reset_progress(self) -> None:
        # rng
        self.rng = Random(int(self.seed))

        # configs
        self.passenger_spawning_step = passenger_spawning_start_step
        self.passenger_spawning_interval_step = passenger_spawning_interval_step
        self.num_paths = num_paths
        self.num_metros = num_metros
        self.num_stations_max = num_stations_max

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [*self.path_buttons]
        self.font = pygame.font.SysFont("arial", score_font_size)

        # status
        self.time_ms = 0
        self.steps = 0

        self.next_station_spawn_timestep = 0

        self.is_mouse_down = False
        self.is_creating_path = False
        self.path_being_created: Path | None = None
        self.travel_plans: TravelPlans = {}
        self.is_paused = False
        self.score = 0

        # stations
        self.existing_station_shape_types: Set[ShapeType] = set()
        self.OTHER_STATION_SHAPE_TYPES = {}

        self.used_stations_list: List[int] = [] # stores used station num

        if self.gen_stations_first:
            if hasattr(self, 'stations'):
                for station in self.stations:
                    station.reset_progress(self.rng)
            else:
                self.stations: List[Station] = []
                self.try_spawn_stations(self.num_stations_max)
        else:
            self.stations: List[Station] = []
            
        # entities
        self.metros: List[Metro] = []
        self.paths: List[Path] = []
        self.cancelled_paths: List[Path] = []
        self.passengers: List[Passenger] = []
        self.path_colors: Dict[Color, bool] = {}
        for i in range(num_paths):
            color = hue_to_rgb(i / (num_paths + 1))
            self.path_colors[color] = False  # not taken
        self.path_to_color: Dict[Path, Color] = {}


        # TABLES
        # for managing reasonable passenger generation
        self.init_existing_station_shape_types()
        self.update_OTHER_STATION_SHAPE_TYPES()
    
    # for STATIC API ONLY!
    # for PROGRESSIVE API, use recreate()
    def initialize_paths(self, *paths_config: Tuple[List[int], bool]):
        self.paths: List[Path] = []
        self.metros: List[Metro] = []

        for config in paths_config:
            self.create_path(config)

    # for PROGRESSIVE API ONLY!
    # for STATIC API, use initialize_paths()
    def recreate_path(self, path_index: int, path_config: Tuple[List[int], bool]):
        self.cancel_path(self.paths[path_index])
        self.create_path(path_config)

    def create_path(self, path_config: Tuple[List[int], bool]):
        stations, is_loop = path_config
        
        self.start_path_on_station(self.stations[stations[0]])
        for station in stations[1:]:
            self.add_station_to_path(self.stations[station])
        
        self.path_being_created.is_looped = is_loop
        self.finish_path_creation()
        
        # newly created path resides at the end of the list
        self.paths[-1].update_segments()

    def init_existing_station_shape_types(self):
        for station in self.stations:
            self.existing_station_shape_types.add(station.shape.type)

    def update_OTHER_STATION_SHAPE_TYPES(self):
        existing_shape_types = list(self.existing_station_shape_types)

        for shape_type in existing_shape_types:
            self.OTHER_STATION_SHAPE_TYPES[shape_type] = [
                x for x in existing_shape_types if x != shape_type
            ]

    def assign_paths_to_buttons(self):
        for path_button in self.path_buttons:
            path_button.remove_path()

        self.path_to_button = {}
        for i in range(min(len(self.paths), len(self.path_buttons))):
            path = self.paths[i]
            button = self.path_buttons[i]
            button.assign_path(path)
            self.path_to_button[path] = button

    def render(self, screen: pygame.surface.Surface) -> None:
        for idx, path in enumerate(self.cancelled_paths):
            path_order = idx - round(self.num_paths / 2)
            path.draw(screen, path_order, cancelled=True)
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

    def react_mouse_event(self, event: MouseEvent):
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
                        self.cancel_path(entity.path)

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
        for metro in path.metros:
            for passenger in metro.passengers:
                self.passengers.remove(passenger)
            self.metros.remove(metro)
    
    def cancel_path(self, path: Path):
        self.path_to_button[path].remove_path()
        self.release_color_for_path(path)
        self.paths.remove(path)
        self.assign_paths_to_buttons()
        self.find_travel_plan_for_passengers()
        if any([len(metro.passengers) > 0 for metro in path.metros]):
            self.cancelled_paths.append(path)
            for metro in path.metros:
                metro.cancel()
            print(f'{path.id} cancelled.')
        else:
            self.remove_path(path)

    def get_unused_color(self) -> Color:
        assigned_color = (0, 0, 0)
        for path_color, taken in self.path_colors.items():
            if not taken:
                assigned_color = path_color
                self.path_colors[path_color] = True
                break
        return assigned_color

    def start_path_on_station(self, station: Station) -> None:
        if len(self.paths) >= self.num_paths:
            print("No more lanes available!")
            return

        self.is_creating_path = True

        assigned_color = self.get_unused_color()
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

    def get_station_shape_types(self):
        station_shape_types: List[ShapeType] = []
        for station in self.stations:
            if station.shape.type not in station_shape_types:
                station_shape_types.append(station.shape.type)
        return station_shape_types
    
    def try_spawn_passengers(self) -> None:
        for station in self.stations:
            station.steps += self.gamespeed
            if not station.need_spawn_passenger():
                continue
            
            # failed to spawn passenger if no other station shape type
            if len(self.existing_station_shape_types) == 1:
                continue
            
            destination_shape_type = self.rng.choice(self.OTHER_STATION_SHAPE_TYPES[station.shape.type])
            destination_shape = get_shape_from_type(
                destination_shape_type, passenger_color, passenger_size
            )
            passenger = Passenger(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)
                self.passengers.append(passenger)

    def try_spawn_stations(self, num: int = 1) -> bool:
        if len(self.stations) >= self.num_stations_max:
            return False
        
        if self.steps < self.next_station_spawn_timestep:
            return False
        
        new_stations_seq = get_random_grid_seqs(self.used_stations_list, self.rng, num)
        for seq in new_stations_seq:
            avail_shapes = [s for s in list(ShapeType) if s not in self.existing_station_shape_types]
            new_station = get_station_at_grid(seq, self.rng, need_new_shape=True, choose_from_types=avail_shapes)
            
            self.stations.append(new_station)
            self.existing_station_shape_types.add(new_station.shape.type)
        
        self.used_stations_list.extend(new_stations_seq)
        self.update_OTHER_STATION_SHAPE_TYPES()

        self.next_station_spawn_timestep += station_spawning_interval_step
        return True

    def increment_time(self, dt_ms: int) -> MeditatorState:
        state = MeditatorState.RUNNING
        if self.try_spawn_stations():
            state = MeditatorState.NEW_STATION

        if self.is_paused:
            return MeditatorState.PAUSED
        
        dt_ms *= self.gamespeed

        # record time
        self.time_ms += dt_ms
        self.steps += self.gamespeed

        # move metros
        for path in self.paths:
            for metro in path.metros:
                path.move_metro(metro, dt_ms)
        
        for path in self.cancelled_paths:
            can_remove = True
            for metro in path.metros:
                if len(metro.passengers) > 0:
                    can_remove = False
                    path.move_metro(metro, dt_ms)
            if can_remove:
                self.remove_path(path)
                self.cancelled_paths.remove(path)
        
        for station in self.stations:
            if station.check_timeout(dt_ms):
                return MeditatorState.ENDED

        # spawn passengers
        # now spawn passengers independently by every station obeying poisson process
        self.try_spawn_passengers()

        self.find_travel_plan_for_passengers()
        self.move_passengers()
        
        return state

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
                if not metro.cancelled:
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
        self.rng.shuffle(stations)

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
