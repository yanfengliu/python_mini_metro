from collections import deque
from typing import Dict, List

from entity.path import Path
from entity.station import Station
from graph.node import Node


def build_station_nodes_dict(stations: List[Station], paths: List[Path]):
    station_nodes: List[Node] = []
    connections: List[List[Node]] = []
    station_nodes_dict: Dict[Station, Node] = {}

    for station in stations:
        node = Node(station)
        station_nodes.append(node)
        station_nodes_dict[station] = node
    for path in paths:
        if path.is_being_created:
            continue
        connection = []
        for station in path.stations:
            station_nodes_dict[station].paths.add(path)
            connection.append(station_nodes_dict[station])
        if path.is_looped and len(connection) > 1:
            connection.append(connection[0])
        connections.append(connection)

    while len(station_nodes) > 0:
        root = station_nodes[0]
        for connection in connections:
            for idx in range(len(connection)):
                node = connection[idx]
                if node == root:
                    if idx - 1 >= 0:
                        root.neighbors.add(connection[idx - 1])
                    if idx + 1 <= len(connection) - 1:
                        root.neighbors.add(connection[idx + 1])
        station_nodes.remove(root)
        station_nodes_dict[root.station] = root

    return station_nodes_dict


def bfs(start: Node, end: Node) -> List[Node]:
    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        node, path = queue.popleft()

        if node == end:
            return path

        for neighbor in node.neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return []
