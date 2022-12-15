from typing import List

from metro import Metro
from station import Station
from utils import get_uuid


class Path:
    def __init__(self):
        self.id = f"P-{get_uuid()}"

    def __repr__(self) -> str:
        return self.id
