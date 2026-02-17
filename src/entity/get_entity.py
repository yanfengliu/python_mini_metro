import random
from typing import List

from config import (
    screen_height,
    screen_width,
    station_color,
    station_shape_type_list,
    station_size,
    station_unique_shape_type_list,
    station_unique_spawn_chance,
    station_unique_spawn_start_index,
)
from entity.metro import Metro
from entity.station import Station
from geometry.point import Point
from geometry.type import ShapeType
from utils import get_random_position, get_random_station_shape, get_shape_from_type


def get_station_spawn_position(existing_positions: List[Point]) -> Point:
    if not existing_positions:
        return get_random_position(screen_width, screen_height)

    center_left = sum(position.left for position in existing_positions) / len(
        existing_positions
    )
    center_top = sum(position.top for position in existing_positions) / len(
        existing_positions
    )
    candidate_positions = [
        get_random_position(screen_width, screen_height) for _ in range(8)
    ]
    candidate_weights = [
        1
        / (
            1
            + (
                (candidate.left - center_left) ** 2
                + (candidate.top - center_top) ** 2
            )
            ** 0.5
        )
        for candidate in candidate_positions
    ]
    return random.choices(candidate_positions, weights=candidate_weights, k=1)[0]


def get_random_station(
    shape_type: ShapeType | None = None,
    existing_positions: List[Point] | None = None,
) -> Station:
    shape = (
        get_shape_from_type(shape_type, station_color, station_size)
        if shape_type is not None
        else get_random_station_shape()
    )
    position = get_station_spawn_position(existing_positions or [])
    return Station(shape, position)


def get_random_stations(num: int) -> List[Station]:
    stations: List[Station] = []
    station_positions: List[Point] = []
    used_unique_shape_types: set[ShapeType] = set()
    for station_idx in range(num):
        shape_type = random.choice(station_shape_type_list)
        if (
            station_idx >= station_unique_spawn_start_index
            and random.random() < station_unique_spawn_chance
        ):
            available_unique_shape_types = [
                unique_shape_type
                for unique_shape_type in station_unique_shape_type_list
                if unique_shape_type not in used_unique_shape_types
            ]
            if available_unique_shape_types:
                shape_type = random.choice(available_unique_shape_types)
                used_unique_shape_types.add(shape_type)
        station = get_random_station(shape_type, existing_positions=station_positions)
        stations.append(station)
        station_positions.append(station.position)
    return stations


def get_metros(num: int) -> List[Metro]:
    metros: List[Metro] = []
    for _ in range(num):
        metros.append(Metro())
    return metros
