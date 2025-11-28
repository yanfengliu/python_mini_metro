from __future__ import annotations

import math
import pprint
import random
from typing import Dict, List

import pygame

#diff from main.py -- can define the game as 1 class, so can train mutliple games at once
# game is done as a timestep --> so can run more games at once and train faster
from config import (
    num_planes,
    num_paths,
    num_airports,
    passenger_color,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    score_display_coords,
    score_font_size,
    airport_max_passengers,
    overcrowd_time_limit_ms,
    airport_spawn_interval
)
from entity.get_entity import get_initial_airports, get_new_random_airport
from entity.plane import Plane
from entity.passenger import Passenger
from entity.path import Path
from entity.airport import Airport
from event.event import Event
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from geometry.type import ShapeType
from graph.graph_algo import bfs, build_airport_nodes_dict
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
        self.num_planes = num_planes
        self.num_airports = num_airports

        # UI
        self.path_buttons = get_path_buttons(self.num_paths)
        self.path_to_button: Dict[Path, PathButton] = {}
        self.buttons = [*self.path_buttons]
        self.font = pygame.font.SysFont("arial", score_font_size)
        self.game_over_font = pygame.font.SysFont("arial", 72)

        # entities
        self.airports = get_initial_airports()
        self.planes: List[Plane] = []
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
        self.steps_since_last_airport_spawn = 0
        self.is_extending_path = False
        self.original_airports_before_extend: List[Airport] = []
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

    def spawn_new_airport(self):
        new_airport = get_new_random_airport()
        self.airports.append(new_airport)

    def render(self, screen: pygame.surface.Surface) -> None:
        for idx, path in enumerate(self.paths):
            path_order = idx - round(self.num_paths / 2)
            path.draw(screen, path_order)
        for airport in self.airports:
            airport.draw(screen)
            if airport.is_overcrowded:
                duration = self.time_ms - airport.overcrowd_start_time_ms
                progress_pct = min(duration / overcrowd_time_limit_ms, 1.0)
                radius = airport.size + 5
                center_point = airport.position
                rect = pygame.Rect(
                    center_point.left - radius,
                    center_point.top - radius,
                    radius * 2,
                    radius * 2,
                )
                start_angle = -math.pi / 2
                end_angle = start_angle + (2 * math.pi * progress_pct)
                pygame.draw.arc(screen, (255, 0, 0), rect, start_angle, end_angle, 3)
        for plane in self.planes:
            plane.draw(screen)
        for button in self.buttons:
            button.draw(screen)
        text_surface = self.font.render(f"Score: {self.score}", True, (0, 0, 0))
        screen.blit(text_surface, score_display_coords)

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

    def create_or_extend_path(self, airport_a: Airport, airport_b: Airport) -> bool:
        """Atomically creates a new path or extends an existing one."""
        for path in self.paths:
            if not path.airports or path.is_looped:
                continue
            
            extend_from_end = path.airports[-1] == airport_a
            extend_from_start = path.airports[0] == airport_a
            
            if extend_from_end or extend_from_start:
                if airport_b in path.airports:
                    if (extend_from_end and path.airports[0] == airport_b) or \
                       (extend_from_start and path.airports[-1] == airport_b):
                        if len(path.airports) > 2:
                            path.set_loop()
                            return True
                        else:
                            return False
                    return False
                
                if extend_from_start:
                    path.airports.reverse()
                
                path.add_airport(airport_b)
                return True

        if len(self.paths) < self.num_paths:
            assigned_color = (0, 0, 0)
            for path_color, taken in self.path_colors.items():
                if not taken:
                    assigned_color = path_color
                    self.path_colors[path_color] = True
                    break
            new_path = Path(assigned_color)
            self._assign_color_to_path(new_path, assigned_color)
            new_path.add_airport(airport_a)
            new_path.add_airport(airport_b)
            self._add_plane_to_path(new_path)
            self.paths.append(new_path)
            return True
        
        return False
    
    def _assign_color_to_path(self, path: Path, color: Color):
        """Assigns a color to a path and marks it as taken."""
        path.color = color
        self.path_colors[color] = True
        self.path_to_color[path] = color

    def _add_plane_to_path(self, path: Path):
        """Adds a new plane to a path if the limit has not been reached."""
        if len(self.planes) < self.num_planes:
            plane = Plane()
            path.add_plane(plane)
            self.planes.append(plane)

    def insert_airport_on_path(self, s_insert: Airport, s1: Airport, s2: Airport) -> bool:
        if s_insert == s1 or s_insert == s2 or s1 == s2:
            return False
        
        for path in self.paths:
            if path.insert_airport_on_segment(s_insert, s1, s2):
                return True
        return False

    def react_mouse_event(self, event: MouseEvent):
        entity = self.get_containing_entity(event.position)

        if event.event_type == MouseEventType.MOUSE_DOWN:
            self.is_mouse_down = True
            if entity:
                if isinstance(entity, Airport):
                    if self.is_creating_path:
                        return

                    path_to_extend = None
                    is_extending_from_start = False

                    for path in self.paths:
                        if not path.airports:
                            continue

                        if path.airports[0] == entity:
                            path_to_extend = path
                            is_extending_from_start = True
                            break
                        elif path.airports[-1] == entity:
                            if path.is_looped:
                                continue
                            path_to_extend = path
                            is_extending_from_start = False
                            break
                    
                    if path_to_extend:
                        self.is_creating_path = True
                        self.is_extending_path = True
                        self.path_being_created = path_to_extend
                        
                        self.original_airports_before_extend = list(path_to_extend.airports)
                        self.is_old_path_looped = path_to_extend.is_looped
                        
                        if is_extending_from_start:
                            path_to_extend.airports.reverse()
                        
                        if path_to_extend.is_looped:
                            path_to_extend.remove_loop()
                            
                        path_to_extend.is_being_created = True
                        path_to_extend.remove_temporary_point()
                    else:
                        self.start_path_on_airport(entity)

        elif event.event_type == MouseEventType.MOUSE_UP:
            self.is_mouse_down = False
            if self.is_creating_path:
                assert self.path_being_created is not None
                if entity and isinstance(entity, Airport):
                    self.end_path_on_airport(entity)
                else:
                    self.abort_path_creation()
            else:
                if entity and isinstance(entity, PathButton):
                    if entity.path:
                        self.remove_path(entity.path)

        elif event.event_type == MouseEventType.MOUSE_MOTION:
            if self.is_mouse_down:
                if self.is_creating_path and self.path_being_created:
                    if entity and isinstance(entity, Airport):
                        self.add_airport_to_path(entity)
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
        for airport in self.airports:
            if airport.contains(position):
                return airport
        for button in self.buttons:
            if button.contains(position):
                return button

    def remove_path(self, path: Path):
        self.path_to_button[path].remove_path()
        for plane in path.planes:
            for passenger in plane.passengers:
                self.passengers.remove(passenger)
            self.planes.remove(plane)
        self.release_color_for_path(path)
        self.paths.remove(path)
        self.assign_paths_to_buttons()
        self.find_travel_plan_for_passengers()

    def start_path_on_airport(self, airport: Airport) -> None:
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
            path.add_airport(airport)
            path.is_being_created = True
            self.path_being_created = path
            self.paths.append(path)

    def add_airport_to_path(self, airport: Airport) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.airports[-1] == airport:
            return

        if (
            len(self.path_being_created.airports) > 1
            and self.path_being_created.airports[0] == airport
        ):
            self.path_being_created.set_loop()
            return

        if airport in self.path_being_created.airports:
            return

        # Any loop should be removed
        if self.path_being_created.is_looped:
            self.path_being_created.remove_loop()
        self.path_being_created.add_airport(airport)

    def abort_path_creation(self) -> None:
        assert self.path_being_created is not None
        self.is_creating_path = False
        if self.is_extending_path:
            self.path_being_created.airports = self.original_airports_before_extend
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
        self.original_airports_before_extend = []
        self.is_old_path_looped = False
        self.path_being_created = None

    def release_color_for_path(self, path: Path) -> None:
        if path in self.path_to_color:
            color = self.path_to_color[path]
            self.path_colors[color] = False
            del self.path_to_color[path]

    def finish_path_creation(self) -> None:
        assert self.path_being_created is not None
        was_new_path = not self.is_extending_path
        self.is_creating_path = False
        self.is_extending_path = False
        self.original_airports_before_extend = []
        self.is_old_path_looped = False
        self.path_being_created.is_being_created = False
        self.path_being_created.remove_temporary_point()
        if was_new_path and len(self.planes) < self.num_planes:
            plane = Plane()
            self.path_being_created.add_plane(plane)
            self.planes.append(plane)
        self.path_being_created = None
        self.assign_paths_to_buttons()

    def end_path_on_airport(self, airport: Airport) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.airports[-1] == airport:
            if len(self.path_being_created.airports) > 1:
                self.finish_path_creation()
            else:
                self.abort_path_creation()
            return
        if (
            len(self.path_being_created.airports) > 1
            and self.path_being_created.airports[0] == airport
        ):
            self.path_being_created.set_loop()
            self.finish_path_creation()
            return
        if airport in self.path_being_created.airports:
            self.abort_path_creation()
            return
        self.path_being_created.add_airport(airport)
        self.finish_path_creation()

    def get_airport_shape_types(self):
        airport_shape_types: List[ShapeType] = []
        for airport in self.airports:
            if airport.shape.type not in airport_shape_types:
                airport_shape_types.append(airport.shape.type)
        return airport_shape_types

    def is_passenger_spawn_time(self) -> bool:
        return (
            self.steps == self.passenger_spawning_step
            or self.steps_since_last_spawn == self.passenger_spawning_interval_step
        )

    def spawn_passengers(self):
        for airport in self.airports:
            airport_types = self.get_airport_shape_types()
            other_airport_shape_types = [
                x for x in airport_types if x != airport.shape.type
            ]
            destination_shape_type = random.choice(other_airport_shape_types)
            destination_shape = get_shape_from_type(
                destination_shape_type, passenger_color, passenger_size
            )
            passenger = Passenger(destination_shape)
            if airport.has_room():
                airport.add_passenger(passenger)
                self.passengers.append(passenger)

    def increment_time(self, dt_ms: int) -> None:
        if self.is_paused or self.is_game_over:
            return

        # record time
        self.time_ms += dt_ms
        self.steps += 1
        self.steps_since_last_spawn += 1
        self.steps_since_last_airport_spawn += 1

        for airport in self.airports:
            if len(airport.passengers) > airport_max_passengers:
                if not airport.is_overcrowded:
                    airport.is_overcrowded = True
                    airport.overcrowd_start_time_ms = self.time_ms
                else:
                    duration = self.time_ms - airport.overcrowd_start_time_ms
                    if duration >= overcrowd_time_limit_ms:
                        self.is_game_over = True
                        break
            else:
                if airport.is_overcrowded:
                    airport.is_overcrowded = False
                    airport.overcrowd_start_time_ms = 0

        # move planes
        for path in self.paths:
            for plane in path.planes:
                path.move_plane(plane, dt_ms)

        # spawn passengers
        if self.is_passenger_spawn_time():
            self.spawn_passengers()
            self.steps_since_last_spawn = 0

        # spawn airports
        if self.steps_since_last_airport_spawn >= airport_spawn_interval:
            self.spawn_new_airport()
            self.steps_since_last_airport_spawn = 0

        self.find_travel_plan_for_passengers()
        self.move_passengers()

    def move_passengers(self) -> None:
        for plane in self.planes:
            if plane.current_airport:
                passengers_to_remove = []
                passengers_from_plane_to_airport = []
                passengers_from_airport_to_plane = []

                # queue
                for passenger in plane.passengers:
                    if (
                        plane.current_airport.shape.type
                        == passenger.destination_shape.type
                    ):
                        passengers_to_remove.append(passenger)
                    elif (
                        self.travel_plans[passenger].get_next_airport()
                        == plane.current_airport
                    ):
                        passengers_from_plane_to_airport.append(passenger)
                for passenger in plane.current_airport.passengers:
                    if (
                        self.travel_plans[passenger].next_path
                        and self.travel_plans[passenger].next_path.id == plane.path_id  # type: ignore
                    ):
                        passengers_from_airport_to_plane.append(passenger)

                # process
                for passenger in passengers_to_remove:
                    passenger.is_at_destination = True
                    plane.remove_passenger(passenger)
                    self.passengers.remove(passenger)
                    del self.travel_plans[passenger]
                    self.score += 1

                for passenger in passengers_from_plane_to_airport:
                    if plane.current_airport.has_room():
                        plane.move_passenger(passenger, plane.current_airport)
                        self.travel_plans[passenger].increment_next_airport()
                        self.find_next_path_for_passenger_at_airport(
                            passenger, plane.current_airport
                        )

                for passenger in passengers_from_airport_to_plane:
                    if plane.has_room():
                        plane.current_airport.move_passenger(passenger, plane)

    def get_airports_for_shape_type(self, shape_type: ShapeType):
        airports: List[Airport] = []
        for airport in self.airports:
            if airport.shape.type == shape_type:
                airports.append(airport)
        random.shuffle(airports)

        return airports

    def find_shared_path(self, airport_a: Airport, airport_b: Airport) -> Path | None:
        for path in self.paths:
            airports = path.airports
            if (airport_a in airports) and (airport_b in airports):
                return path
        return None

    def passenger_has_travel_plan(self, passenger: Passenger) -> bool:
        return (
            passenger in self.travel_plans
            and self.travel_plans[passenger].next_path is not None
        )

    def find_next_path_for_passenger_at_airport(
        self, passenger: Passenger, airport: Airport
    ):
        next_airport = self.travel_plans[passenger].get_next_airport()
        assert next_airport is not None
        next_path = self.find_shared_path(airport, next_airport)
        self.travel_plans[passenger].next_path = next_path

    def skip_airports_on_same_path(self, node_path: List[Node]):
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
        airport_nodes_dict = build_airport_nodes_dict(self.airports, self.paths)
        for airport in self.airports:
            for passenger in airport.passengers:
                if not self.passenger_has_travel_plan(passenger):
                    possible_dst_airports = self.get_airports_for_shape_type(
                        passenger.destination_shape.type
                    )
                    should_set_null_path = True
                    for possible_dst_airport in possible_dst_airports:
                        start = airport_nodes_dict[airport]
                        end = airport_nodes_dict[possible_dst_airport]
                        node_path = bfs(start, end)
                        if len(node_path) == 1:
                            # passenger arrived at destination
                            airport.remove_passenger(passenger)
                            self.passengers.remove(passenger)
                            passenger.is_at_destination = True
                            del self.travel_plans[passenger]
                            should_set_null_path = False
                            break
                        elif len(node_path) > 1:
                            node_path = self.skip_airports_on_same_path(node_path)
                            self.travel_plans[passenger] = TravelPlan(node_path[1:])
                            self.find_next_path_for_passenger_at_airport(
                                passenger, airport
                            )
                            should_set_null_path = False
                            break
                    if should_set_null_path:
                        self.travel_plans[passenger] = TravelPlan([])
