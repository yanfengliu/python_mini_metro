from typing import Dict, List

from entity.path import Path
from entity.airport import Airport
from graph.node import Node


def build_airport_nodes_dict(airports: List[Airport], paths: List[Path]):
    airport_nodes: List[Node] = []
    connections: List[List[Node]] = []
    airport_nodes_dict: Dict[Airport, Node] = {}

    for airport in airports:
        node = Node(airport)
        airport_nodes.append(node)
        airport_nodes_dict[airport] = node
    for path in paths:
        if path.is_being_created:
            continue
        connection = []
        for airport in path.airports:
            airport_nodes_dict[airport].paths.add(path)
            connection.append(airport_nodes_dict[airport])
        connections.append(connection)

    while len(airport_nodes) > 0:
        root = airport_nodes[0]
        for connection in connections:
            for idx in range(len(connection)):
                node = connection[idx]
                if node == root:
                    if idx - 1 >= 0:
                        root.neighbors.add(connection[idx - 1])
                    if idx + 1 <= len(connection) - 1:
                        root.neighbors.add(connection[idx + 1])
        airport_nodes.remove(root)
        airport_nodes_dict[root.airport] = root

    return airport_nodes_dict


def bfs(start: Node, end: Node) -> List[Node]:
    # Create a queue and enqueue the start node\
    queue = [(start, [start])]

    # While the queue is not empty
    while queue:
        # Dequeue the first node
        (node, path) = queue.pop(0)

        # If the node is the end node, return the path
        if node == end:
            return path

        # Enqueue the neighbors of the node
        for next in node.neighbors:
            if next not in path:
                queue.append((next, path + [next]))

    # If no path was found, return an empty list
    return []
