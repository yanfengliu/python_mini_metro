from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Protocol

from env import MiniMetroEnv

Action = Dict[str, Any]


class Agent(Protocol):
    def reset(self, observation: Dict[str, Any]) -> None:
        pass

    def act(self, observation: Dict[str, Any]) -> Action:
        pass


class SimpleAgent:
    def __init__(self) -> None:
        self.has_created_path = False

    def reset(self, observation: Dict[str, Any]) -> None:
        self.has_created_path = False

    def act(self, observation: Dict[str, Any]) -> Action:
        if not self.has_created_path:
            stations = observation["structured"]["stations"]
            if len(stations) >= 2:
                self.has_created_path = True
                return {"type": "create_path", "stations": [0, 1], "loop": False}
        return {"type": "noop"}


@dataclass(frozen=True)
class PlaythroughStep:
    action: Action
    reward: int
    score: int
    time_ms: int


@dataclass
class PlaythroughRecord:
    seed: int | None
    dt_ms: int | None
    actions: List[Action] = field(default_factory=list)
    steps: List[PlaythroughStep] = field(default_factory=list)
    final_score: int = 0
    max_steps: int = 0


def run_agent_playthrough(
    agent: Agent | None = None,
    *,
    seed: int | None = None,
    max_steps: int = 100,
    dt_ms: int | None = None,
    env: MiniMetroEnv | None = None,
) -> tuple[int, PlaythroughRecord]:
    if env is None:
        env = MiniMetroEnv(dt_ms=dt_ms)
    if agent is None:
        agent = SimpleAgent()

    observation = env.reset(seed=seed)
    agent.reset(observation)

    record = PlaythroughRecord(seed=seed, dt_ms=dt_ms, max_steps=max_steps)

    for _ in range(max_steps):
        action = agent.act(observation)
        observation, reward, _, _ = env.step(action, dt_ms=dt_ms)
        record.actions.append(action)
        record.steps.append(
            PlaythroughStep(
                action=action,
                reward=reward,
                score=observation["structured"]["score"],
                time_ms=observation["structured"]["time_ms"],
            )
        )

    record.final_score = env.mediator.score
    return record.final_score, record


def iter_playthrough_observations(
    record: PlaythroughRecord,
    *,
    env: MiniMetroEnv | None = None,
    max_steps: int | None = None,
) -> Iterable[Dict[str, Any]]:
    if env is None:
        env = MiniMetroEnv(dt_ms=record.dt_ms)
    observation = env.reset(seed=record.seed)
    yield observation

    actions = record.actions
    if max_steps is not None:
        actions = actions[:max_steps]

    for action in actions:
        observation, _, _, _ = env.step(action, dt_ms=record.dt_ms)
        yield observation


def replay_playthrough(
    record: PlaythroughRecord,
    *,
    env: MiniMetroEnv | None = None,
    max_steps: int | None = None,
) -> int:
    if env is None:
        env = MiniMetroEnv(dt_ms=record.dt_ms)
    for _ in iter_playthrough_observations(
        record, env=env, max_steps=max_steps
    ):
        pass
    return env.mediator.score
