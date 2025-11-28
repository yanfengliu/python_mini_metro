import gymnasium as gym
from gymnasium import spaces
import numpy as np
import itertools
from typing import Dict, Any

from mediator import Mediator
from config import num_paths, screen_width, screen_height, screen_color
from geometry.type import ShapeType
from geometry.utils import distance

import pygame

MAX_airportS = 20
MAX_PATHS = num_paths
MAX_airportS_PER_PATH = 12

class PlaneGameEnv(gym.Env):
    """A Gymnasium environment for the Python Mini plane game."""

    metadata = {"render_modes": ["human"], "render_fps": 30}

    def __init__(self, render_mode: str | None = None):
        super().__init__()
        self.mediator = Mediator()
        
        self.render_mode = render_mode
        self.screen = None
        self.clock = None
        if self.render_mode == "human":
            pygame.init()
            pygame.display.set_caption("plane RL Training")
            self.screen = pygame.display.set_mode((screen_width, screen_height))
            self.clock = pygame.time.Clock()

        self.shape_types = sorted([e.value for e in ShapeType])
        self.shape_to_idx = {shape: i for i, shape in enumerate(self.shape_types)}
        self.num_shape_types = len(self.shape_types)
        
        self._action_map = self._create_action_map()
        self.action_space = spaces.Discrete(len(self._action_map))

        self.observation_space = self._create_observation_space()

    def _get_action_mask(self) -> np.ndarray:
        """
        Generates a boolean mask for valid actions
        Basically just lets the model know immeaditly
        if it can take certain actions
        """
        mask = np.zeros(self.action_space.n, dtype=np.int8)
        num_airports = len(self.mediator.airports)

        for action_id, action_info in self._action_map.items():
            action_type = action_info["type"]
            is_valid = False
            if action_type == "NO_OP":
                is_valid = True
            elif action_type == "CREATE_OR_EXTEND_PATH":
                start_idx, end_idx = action_info["start_idx"], action_info["end_idx"]
                if start_idx < num_airports and end_idx < num_airports and start_idx != end_idx:
                    is_valid = True
            elif action_type == "INSERT_airport":
                insert_idx, exist1_idx, exist2_idx = action_info["insert_idx"], action_info["exist1_idx"], action_info["exist2_idx"]
                if all(i < num_airports for i in [insert_idx, exist1_idx, exist2_idx]) and len({insert_idx, exist1_idx, exist2_idx}) == 3:
                    s_insert = self.mediator.airports[insert_idx]
                    s1 = self.mediator.airports[exist1_idx]
                    s2 = self.mediator.airports[exist2_idx]
                    for p in self.mediator.paths:
                        if s_insert in p.airports: continue # Cannot insert a airport already on the path
                        for i in range(len(p.airports) - 1):
                            if (p.airports[i] == s1 and p.airports[i+1] == s2) or \
                               (p.airports[i] == s2 and p.airports[i+1] == s1):
                                is_valid = True; break
                        if is_valid: break
                        if p.is_looped and len(p.airports) > 1:
                            if (p.airports[-1] == s1 and p.airports[0] == s2) or \
                               (p.airports[-1] == s2 and p.airports[0] == s1):
                                is_valid = True; break
            if is_valid:
                mask[action_id] = 1
        return mask

    def render(self):
        if self.render_mode != "human" or self.screen is None: 
            return
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return

        self.screen.fill(screen_color)
        self.mediator.render(self.screen)
        pygame.display.flip()
        self.clock.tick(self.metadata["render_fps"])

    def close(self):
        if self.screen is not None:
            pygame.display.quit()
            pygame.quit()
            self.screen = None
            self.clock = None

    def _create_action_map(self) -> Dict[int, Dict[str, Any]]:
        """Creates the mapping from discrete action int to game action."""
        action_map = {0: {"type": "NO_OP"}}
        action_id = 1
        
        airport_pairs = list(itertools.permutations(range(MAX_airportS), 2))
        for start_idx, end_idx in airport_pairs:
            action_map[action_id] = {"type": "CREATE_OR_EXTEND_PATH", "start_idx": start_idx, "end_idx": end_idx}
            action_id += 1
            
        airport_trios = list(itertools.permutations(range(MAX_airportS), 3))
        for insert_idx, exist1_idx, exist2_idx in airport_trios:
            action_map[action_id] = {"type": "INSERT_airport", "insert_idx": insert_idx, "exist1_idx": exist1_idx, "exist2_idx": exist2_idx}
            action_id += 1
            
        return action_map

    def _create_observation_space(self) -> spaces.Box:
        """Correctly defines the size of the observation space."""
        # 1 (exists) + 1 (is_connected) + 2 (pos) + 1 (overcrowd) + 1 (timer) + num_shapes (type) + num_shapes (passengers)
        airport_obs_size = 1 + 1 + 2 + 1 + 1 + self.num_shape_types + self.num_shape_types
        total_airport_obs_size = MAX_airportS * airport_obs_size
        
        # 1 (exists/is_loop) + MAX_airportS_PER_PATH (airport indices)
        path_obs_size = 1 + MAX_airportS_PER_PATH
        total_path_obs_size = MAX_PATHS * path_obs_size
        
        total_size = total_airport_obs_size + total_path_obs_size
        # low=-1 for airport indices in paths, high=screen_width just to be safe (though 1.0 is max for most)
        return spaces.Box(low=-1.0, high=2.0, shape=(total_size,), dtype=np.float32)

    def _get_obs(self) -> np.ndarray:
        """
        The observation is a flattened `spaces.Box` vector composed of two
        main parts:
        
        1.  **airport Data** (for `MAX_airportS`):
            - `exists` (1): 1.0 if the airport exists, 0.0 otherwise.
            - `is_connected` (1): 1.0 if part of any path, 0.0 otherwise.
            - `position` (2): (x, y) normalized by screen dimensions.
            - `is_overcrowded` (1): 1.0 if overcrowded, 0.0 otherwise.
            - `overcrowd_timer` (1): Normalized time since overcrowding started
              (0.0 to 1.0).
            - `type` (num_shapes): One-hot encoding of the airport's shape.
            - `passengers` (num_shapes): Count of waiting passengers
              for each destination shape, normalized by airport capacity.
        
        2.  **Path Data** (for `MAX_PATHS`):
            - `exists/is_loop` (1): 0.0 for non-existent, 1.0 for existing,
              2.0 for looped path.
            - `airports` (MAX_airportS_PER_PATH): List of airport indices (-1
              for empty).

        Final vector will look like this:
        [
        --- airport 0 (14 floats) ---
        exists, is_connected, x_pos, y_pos, is_overcrowd, crowd_timer,
        (type_shape_0, type_shape_1, type_shape_2, type_shape_3),  <-- 1-hot type
        (pass_shape_0, pass_shape_1, pass_shape_2, pass_shape_3), <-- passenger counts

        --- airport 1 (14 floats) ---
        exists, is_connected, x_pos, y_pos, is_overcrowd, crowd_timer,
        (0, 0, 1, 0),  <-- 1-hot (e.g., is a triangle)
        (1.2, 0.5, 0.0, 3.1), <-- passenger counts (normalized)
        
        ... (repeated for all MAX_airportS) ...

        --- airport 19 (14 floats) ---
        (0, 0, 0, 0, 0, 0, (0,0,0,0), (0,0,0,0)), <-- all zeros if airport doesn't exist

        --- Path 0 (13 floats) ---
        exists_or_loop_status, (idx_0, idx_1, idx_2, ..., idx_11),

        --- Path 1 (13 floats) ---
        exists_or_loop_status, (idx_0, idx_1, idx_2, ..., idx_11),

        ... (repeated for all MAX_PATHS) ...
        ]
        """
        # figure out which airports are connected
        airports_in_paths = set()
        for path in self.mediator.paths:
            for airport in path.airports:
                airports_in_paths.add(airport.id)

        obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        
        # 1 (exists) + 1 (is_connected) + 2 (pos) + 1 (overcrowd) + 1 (timer) + num_shapes (type) + num_shapes (passengers)
        airport_chunk_size = 1 + 1 + 2 + 1 + 1 + self.num_shape_types + self.num_shape_types
        
        for i in range(MAX_airportS):
            offset = i * airport_chunk_size
            # Create a vector representation of every airport:
            if i < len(self.mediator.airports):
                airport = self.mediator.airports[i]
                
                # Base offset for this airport's features
                feat_offset = 0
                
                # 1. Existence flag
                obs[offset + feat_offset] = 1.0 
                feat_offset += 1
                
                # 2. is_connected
                obs[offset + feat_offset] = 1.0 if airport.id in airports_in_paths else 0.0
                feat_offset += 1

                # 3. Position (2 floats)
                obs[offset + feat_offset] = airport.position.left / screen_width
                feat_offset += 1
                obs[offset + feat_offset] = airport.position.top / screen_height
                feat_offset += 1
                
                # 4. is_overcrowded flag
                obs[offset + feat_offset] = 1.0 if airport.is_overcrowded else 0.0
                feat_offset += 1

                # 5. Overcrowd timer
                if airport.is_overcrowded:
                    elapsed = self.mediator.time_ms - airport.overcrowd_start_time_ms
                    obs[offset + feat_offset] = min(elapsed / 10000.0, 1.0)
                feat_offset += 1
                
                # 6. airport shape (one-hot)
                shape_idx = self.shape_to_idx[airport.shape.type.value]
                obs[offset + feat_offset + shape_idx] = 1.0
                feat_offset += self.num_shape_types
                
                # 7. Passenger counts (per destination shape)
                passenger_counts = np.zeros(self.num_shape_types, dtype=np.float32)
                for p in airport.passengers:
                    dest_idx = self.shape_to_idx[p.destination_shape.type.value]
                    passenger_counts[dest_idx] += 1
                
                obs[offset + feat_offset : offset + airport_chunk_size] = passenger_counts / airport.capacity
        
        path_chunk_size = 1 + MAX_airportS_PER_PATH
        airport_offset = MAX_airportS * airport_chunk_size
        airport_to_game_idx = {s.id: i for i, s in enumerate(self.mediator.airports)}
        
        for i in range(MAX_PATHS):
            offset = airport_offset + i * path_chunk_size
            if i < len(self.mediator.paths):
                path = self.mediator.paths[i]
                obs[offset] = 1.0 if not path.is_looped else 2.0 # Use 2.0 to signify a loop
                path_indices = [-1.0] * MAX_airportS_PER_PATH
                for j, airport in enumerate(path.airports):
                    if j < MAX_airportS_PER_PATH:
                        path_indices[j] = airport_to_game_idx.get(airport.id, -1.0)
                obs[offset + 1 : offset + path_chunk_size] = path_indices
        return obs

    def _get_info(self) -> Dict[str, Any]:
        """Returns info dict, including the crucial action mask."""
        return {
            "score": self.mediator.score,
            "steps": self.mediator.steps,
            "action_mask": self._get_action_mask()
        }

    def reset(self, seed=None, options=None) -> tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.mediator = Mediator()
        if self.render_mode == "human":
            self.render()
        return self._get_obs(), self._get_info()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        prev_score = self.mediator.score
        num_loops_before = sum(1 for p in self.mediator.paths if p.is_looped)
        
        action_info = self._action_map.get(action)
        action_was_valid = False
        
        if action_info:
            action_type = action_info["type"]
            if action_type == "NO_OP":
                action_was_valid = True

            elif action_type == "CREATE_OR_EXTEND_PATH":
                start_idx, end_idx = action_info["start_idx"], action_info["end_idx"]
                if start_idx < len(self.mediator.airports) and end_idx < len(self.mediator.airports) and start_idx != end_idx:
                    start_airport = self.mediator.airports[start_idx]
                    end_airport = self.mediator.airports[end_idx]
                    action_was_valid = self.mediator.create_or_extend_path(start_airport, end_airport)

            elif action_type == "INSERT_airport":
                insert_idx, exist1_idx, exist2_idx = action_info["insert_idx"], action_info["exist1_idx"], action_info["exist2_idx"]
                if all(i < len(self.mediator.airports) for i in [insert_idx, exist1_idx, exist2_idx]):
                    s_insert = self.mediator.airports[insert_idx]
                    s1 = self.mediator.airports[exist1_idx]
                    s2 = self.mediator.airports[exist2_idx]
                    action_was_valid = self.mediator.insert_airport_on_path(s_insert, s1, s2)

        # Simulate 15 game-ticks
        for _ in range(15): 
            if self.mediator.is_game_over: break
            self.mediator.increment_time(16)

        reward = (self.mediator.score - prev_score) * 25.0
        
        reward += 0.01
        
        if not action_was_valid:
            reward -= 1.0

        terminated = self.mediator.is_game_over
        
        if self.render_mode == "human":
            self.render()

        return self._get_obs(), reward, terminated, False, self._get_info()
    