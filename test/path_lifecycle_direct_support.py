class FakeStation:
    def __init__(self, name, events):
        self.name = name
        self.events = events

    def __eq__(self, other):
        return isinstance(other, FakeStation) and self.name == other.name

    def start_snap_blip(self, time_ms, color):
        self.events.append(("blip", self.name, time_ms, color))


class FakeMetro:
    def __init__(self, name="metro"):
        self.name = name
        self.passengers = []


class FakePath:
    def __init__(self, path_id, color, events):
        self.id = path_id
        self.color = color
        self.events = events
        self.stations = []
        self.metros = []
        self.is_being_created = False
        self.is_looped = False
        self.temp_point = object()

    def add_station(self, station):
        self.events.append(("path:add-station", station.name))
        self.stations.append(station)

    def set_loop(self):
        self.events.append(("path:set-loop",))
        self.is_looped = True

    def remove_loop(self):
        self.events.append(("path:remove-loop",))
        self.is_looped = False

    def remove_temporary_point(self):
        self.events.append(("path:remove-temp",))
        self.temp_point = None

    def add_metro(self, metro):
        self.events.append(("path:add-metro", metro.name))
        self.metros.append(metro)


class FakeButton:
    def __init__(self, name, events):
        self.name = name
        self.events = events
        self.path = None

    def remove_path(self):
        self.events.append(("button:clear", self.name))
        self.path = None

    def assign_path(self, path):
        self.events.append(("button:assign", self.name, path.id))
        self.path = path


class FakeNode:
    def __init__(self, *paths):
        self.paths = set(paths)


class FakeTravelPlan:
    def __init__(self, next_path=None, node_path=()):
        self.next_path = next_path
        self.node_path = list(node_path)


class CallbackList(list):
    def __init__(self, values, on_remove):
        super().__init__(values)
        self.on_remove = on_remove

    def remove(self, value):
        super().remove(value)
        self.on_remove(value)


class LoggingDict(dict):
    def __init__(self, values, events, label):
        super().__init__(values)
        self.events = events
        self.label = label

    def __setitem__(self, key, value):
        self.events.append((f"{self.label}:set", key, value))
        super().__setitem__(key, value)

    def __delitem__(self, key):
        self.events.append((f"{self.label}:del", key))
        super().__delitem__(key)


class IntSubclass(int):
    pass


class EphemeralFactory:
    def __init__(self, name, events, builder):
        self.name = name
        self.events = events
        self.builder = builder

    def __call__(self, *args):
        self.events.append((f"factory:{self.name}:call", *args))
        return self.builder(*args)

    def __del__(self):
        self.events.append((f"factory:{self.name}:del",))


class FakeHost:
    def __init__(self, lifecycle):
        self.lifecycle = lifecycle
        self.events = []
        self.path_buttons = []
        self.path_to_button = {}
        self.paths = []
        self.metros = []
        self.passengers = []
        self.travel_plans = {}
        self.path_colors = {}
        self.path_to_color = {}
        self.stations = []
        self.unlocked_num_paths = 3
        self.num_metros = 3
        self.time_ms = 17
        self.is_creating_path = False
        self.path_being_created = None
        self.path_factory = lambda color: FakePath("created", color, self.events)
        self.metro_factory = lambda: FakeMetro()

    def update_path_button_lock_states(self):
        self.events.append(("locks",))

    def find_travel_plan_for_passengers(self):
        self.events.append(("replan",))

    def assign_paths_to_buttons(self):
        self.events.append(("public:assign",))
        self.lifecycle.assign_paths_to_buttons(self)

    def remove_path(self, path):
        self.events.append(("public:remove", path.id))
        self.lifecycle.remove_path(self, path)

    def invalidate_travel_plans_for_path(self, path):
        self.events.append(("public:invalidate", path.id))
        self.lifecycle.invalidate_travel_plans_for_path(self, path)

    def release_color_for_path(self, path):
        self.events.append(("public:release", path.id))
        self.lifecycle.release_color_for_path(self, path)

    def start_path_on_station(self, station):
        self.events.append(("public:start", station.name))
        self.lifecycle.start_path_on_station(
            self, station, get_path_factory=lambda: self.path_factory
        )

    def add_station_to_path(self, station):
        self.events.append(("public:add", station.name))
        self.lifecycle.add_station_to_path(self, station)

    def abort_path_creation(self):
        self.events.append(("public:abort",))
        self.lifecycle.abort_path_creation(self)

    def finish_path_creation(self):
        self.events.append(("public:finish",))
        self.lifecycle.finish_path_creation(self)

    def end_path_on_station(self, station):
        self.events.append(("public:end", station.name))
        self.lifecycle.end_path_on_station(self, station)
