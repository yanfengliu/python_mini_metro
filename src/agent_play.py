from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from inspect import Parameter, signature
from typing import Any, Dict, Iterable, List, Protocol

from env import MiniMetroEnv, legacy_auto_assignment_step
from recursive_contract import (
    _LIVE_ONLY_ACTION_TYPES,
    CARRIAGE_ACTION_CONTRACT,
    FLEET_ACTION_CONTRACT,
    validate_replay_action,
)

Action = Dict[str, Any]

PLAYTHROUGH_RECORD_SCHEMA_V1 = "mini-metro-agent-play-v1"
PLAYTHROUGH_RECORD_SCHEMA_V2 = "mini-metro-agent-play-v2"
PLAYTHROUGH_RECORD_SCHEMA_V3 = "mini-metro-agent-play-v3"
PLAYTHROUGH_RECORD_SCHEMA_V4 = "mini-metro-agent-play-v4"
PLAYTHROUGH_RECORD_SCHEMA_V5 = "mini-metro-agent-play-v5"
LEGACY_PLAYTHROUGH_RECORD_SCHEMA = PLAYTHROUGH_RECORD_SCHEMA_V1
PLAYTHROUGH_RECORD_SCHEMA = PLAYTHROUGH_RECORD_SCHEMA_V5
DELIVERIES_REWARD_CONTRACT = "deliveries"
LINE_CREDITS_REWARD_CONTRACT = "line_credits_delta"
_SUPPORTED_RECORD_SCHEMAS = {
    PLAYTHROUGH_RECORD_SCHEMA_V1,
    PLAYTHROUGH_RECORD_SCHEMA_V2,
    PLAYTHROUGH_RECORD_SCHEMA_V3,
    PLAYTHROUGH_RECORD_SCHEMA_V4,
    PLAYTHROUGH_RECORD_SCHEMA_V5,
}
_SUPPORTED_REWARD_CONTRACTS = {
    DELIVERIES_REWARD_CONTRACT,
    LINE_CREDITS_REWARD_CONTRACT,
}
_CARRIAGE_ACTION_TYPES = {"attach_carriage", "detach_carriage"}


class Agent(Protocol):
    def reset(self, observation: Dict[str, Any]) -> None:
        pass

    def act(self, observation: Dict[str, Any]) -> Action:
        pass


class SimpleAgent:
    def __init__(self) -> None:
        self.has_created_path = False
        self.has_assigned_locomotive = False

    def reset(self, observation: Dict[str, Any]) -> None:
        self.has_created_path = False
        self.has_assigned_locomotive = False

    def act(self, observation: Dict[str, Any]) -> Action:
        if not self.has_created_path:
            stations = observation["structured"]["stations"]
            if len(stations) >= 2:
                self.has_created_path = True
                return {"type": "create_path", "stations": [0, 1], "loop": False}
        if not self.has_assigned_locomotive and observation["structured"]["paths"]:
            self.has_assigned_locomotive = True
            return {"type": "assign_locomotive", "path_index": 0}
        return {"type": "noop"}


@dataclass(frozen=True)
class PlaythroughStep:
    action: Action
    reward: int
    score: int
    time_ms: int
    is_done: bool
    deliveries: int = 0
    line_credits: int = 0


@dataclass
class PlaythroughRecord:
    seed: int | None
    dt_ms: int | None
    actions: List[Action] = field(default_factory=list)
    steps: List[PlaythroughStep] = field(default_factory=list)
    final_score: int = 0
    max_steps: int = 0
    schema: str = LEGACY_PLAYTHROUGH_RECORD_SCHEMA
    reward_contract: str = LINE_CREDITS_REWARD_CONTRACT
    final_deliveries: int = 0
    final_line_credits: int = 0
    overdue_passenger_threshold: int | None = None
    fleet_action_contract: str | None = None
    carriage_action_contract: str | None = None


def _coerce_contract(value: object) -> str | None:
    if hasattr(value, "value"):
        value = getattr(value, "value")
    if isinstance(value, str) and value in _SUPPORTED_REWARD_CONTRACTS:
        return value
    return None


def _environment_reward_contract(env: MiniMetroEnv) -> str:
    for attribute in ("reward_contract", "reward_mode"):
        if not hasattr(env, attribute):
            continue
        value = getattr(env, attribute)
        contract = _coerce_contract(value)
        if contract is not None:
            return contract
        raise ValueError(f"unsupported environment reward contract: {value!r}")
    return LINE_CREDITS_REWARD_CONTRACT


def _record_reward_contract(record: PlaythroughRecord) -> str:
    schema = getattr(record, "schema", LEGACY_PLAYTHROUGH_RECORD_SCHEMA)
    if schema not in _SUPPORTED_RECORD_SCHEMAS:
        raise ValueError(f"unsupported playthrough record schema: {schema!r}")
    if schema == PLAYTHROUGH_RECORD_SCHEMA_V1:
        contract = getattr(record, "reward_contract", LINE_CREDITS_REWARD_CONTRACT)
        if contract != LINE_CREDITS_REWARD_CONTRACT:
            raise ValueError("legacy playthrough records require line_credits_delta")
        return LINE_CREDITS_REWARD_CONTRACT
    if not hasattr(record, "reward_contract"):
        raise ValueError(f"{schema} records require reward_contract")
    contract = record.reward_contract
    if contract not in _SUPPORTED_REWARD_CONTRACTS:
        raise ValueError(f"unsupported playthrough reward contract: {contract!r}")
    return contract


def _record_overdue_passenger_threshold(record: PlaythroughRecord) -> int:
    schema = getattr(record, "schema", PLAYTHROUGH_RECORD_SCHEMA_V1)
    if schema not in _SUPPORTED_RECORD_SCHEMAS:
        raise ValueError(f"unsupported playthrough record schema: {schema!r}")
    if schema in {PLAYTHROUGH_RECORD_SCHEMA_V1, PLAYTHROUGH_RECORD_SCHEMA_V2}:
        return 1
    if not hasattr(record, "overdue_passenger_threshold"):
        raise ValueError("v3-v5 records require overdue_passenger_threshold")
    threshold = record.overdue_passenger_threshold
    if type(threshold) is not int or threshold <= 0:
        raise ValueError("v3-v5 overdue_passenger_threshold must be a positive integer")
    return threshold


def _record_fleet_action_contract(record: PlaythroughRecord) -> str | None:
    schema = getattr(record, "schema", PLAYTHROUGH_RECORD_SCHEMA_V1)
    contract = getattr(record, "fleet_action_contract", None)
    if schema in {PLAYTHROUGH_RECORD_SCHEMA_V4, PLAYTHROUGH_RECORD_SCHEMA_V5}:
        if contract != FLEET_ACTION_CONTRACT:
            raise ValueError(
                f"v4/v5 records require fleet_action_contract {FLEET_ACTION_CONTRACT!r}"
            )
        return contract
    if contract is not None:
        raise ValueError("v1-v3 records must not declare fleet_action_contract")
    return None


def _record_carriage_action_contract(record: PlaythroughRecord) -> str | None:
    schema = getattr(record, "schema", PLAYTHROUGH_RECORD_SCHEMA_V1)
    contract = getattr(record, "carriage_action_contract", None)
    if schema == PLAYTHROUGH_RECORD_SCHEMA_V5:
        if contract != CARRIAGE_ACTION_CONTRACT:
            raise ValueError(
                f"v5 records require carriage_action_contract "
                f"{CARRIAGE_ACTION_CONTRACT!r}"
            )
        return contract
    if contract is not None:
        raise ValueError("v1-v4 records must not declare carriage_action_contract")
    return None


def _validate_record_actions(
    record: PlaythroughRecord,
    *,
    allow_fleet: bool,
    allow_carriages: bool,
) -> None:
    for index, action in enumerate(record.actions):
        validate_replay_action(
            action,
            fleet_actions_allowed=allow_fleet,
            carriage_actions_allowed=allow_carriages,
            label=f"record.actions[{index}]",
        )


def _reject_record_carriage_actions(record: PlaythroughRecord) -> None:
    for index, action in enumerate(record.actions):
        if type(action) is dict and action.get("type") in _CARRIAGE_ACTION_TYPES:
            raise ValueError(
                f"record.actions[{index}] uses a carriage action before schema v5"
            )


def _reject_record_live_only_actions(record: PlaythroughRecord) -> None:
    for index, action in enumerate(record.actions):
        if type(action) is dict and action.get("type") in _LIVE_ONLY_ACTION_TYPES:
            raise ValueError(
                f"record.actions[{index}] uses a live-only action in a persisted record"
            )


def _environment_overdue_passenger_threshold(env: MiniMetroEnv) -> int:
    mediator = env.mediator
    if hasattr(mediator, "overdue_passenger_threshold"):
        threshold = mediator.overdue_passenger_threshold
    elif hasattr(mediator, "max_waiting_passengers"):
        threshold = mediator.max_waiting_passengers
    else:
        raise ValueError("environment does not expose an overdue passenger threshold")
    if type(threshold) is not int or threshold <= 0:
        raise ValueError("environment overdue passenger threshold must be positive")
    return threshold


def _apply_overdue_passenger_threshold(env: MiniMetroEnv, threshold: int) -> None:
    mediator = env.mediator
    if hasattr(mediator, "overdue_passenger_threshold"):
        mediator.overdue_passenger_threshold = threshold
    elif hasattr(mediator, "max_waiting_passengers"):
        mediator.max_waiting_passengers = threshold
    else:
        raise ValueError("environment does not expose an overdue passenger threshold")


def _new_environment(
    dt_ms: int | None, reward_contract: str
) -> tuple[MiniMetroEnv, str]:
    parameters = signature(MiniMetroEnv).parameters
    accepts_keywords = any(
        parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values()
    )

    def accepts_keyword(name: str) -> bool:
        parameter = parameters.get(name)
        return accepts_keywords or (
            parameter is not None
            and parameter.kind
            in {Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}
        )

    accepts_reward_mode = accepts_keyword("reward_mode")
    kwargs: dict[str, Any] = {}
    if accepts_keyword("dt_ms"):
        kwargs["dt_ms"] = dt_ms
    if accepts_reward_mode:
        kwargs["reward_mode"] = reward_contract
    env = MiniMetroEnv(**kwargs)
    if accepts_reward_mode:
        return env, reward_contract
    if hasattr(env, "reward_mode"):
        env.reward_mode = reward_contract
        return env, reward_contract
    # Compatibility with MiniMetroEnv versions from before explicit reward modes.
    return env, LINE_CREDITS_REWARD_CONTRACT


def _observation_metrics(
    observation: Dict[str, Any], env: MiniMetroEnv
) -> tuple[int, int]:
    structured = observation.get("structured", {})
    mediator = env.mediator
    deliveries = structured.get(
        "deliveries",
        getattr(mediator, "deliveries", getattr(mediator, "total_travels_handled", 0)),
    )
    line_credits = structured.get(
        "line_credits",
        structured.get(
            "score", getattr(mediator, "line_credits", getattr(mediator, "score", 0))
        ),
    )
    return int(deliveries), int(line_credits)


def _mediator_deliveries(env: MiniMetroEnv) -> int:
    return int(
        getattr(
            env.mediator,
            "deliveries",
            getattr(env.mediator, "total_travels_handled", 0),
        )
    )


def _mediator_line_credits(env: MiniMetroEnv) -> int:
    return int(getattr(env.mediator, "line_credits", getattr(env.mediator, "score", 0)))


def run_agent_playthrough(
    agent: Agent | None = None,
    *,
    seed: int | None = None,
    max_steps: int = 100,
    dt_ms: int | None = None,
    env: MiniMetroEnv | None = None,
) -> tuple[int, PlaythroughRecord]:
    if env is None:
        env, reward_contract = _new_environment(dt_ms, DELIVERIES_REWARD_CONTRACT)
    else:
        reward_contract = _environment_reward_contract(env)
    if agent is None:
        agent = SimpleAgent()

    observation = env.reset(seed=seed)
    overdue_threshold = _environment_overdue_passenger_threshold(env)
    agent.reset(observation)
    effective_dt_ms = (
        dt_ms
        if dt_ms is not None
        else getattr(env, "dt_ms_default", getattr(env, "dt_ms", None))
    )

    record = PlaythroughRecord(
        seed=seed,
        dt_ms=effective_dt_ms,
        max_steps=max_steps,
        schema=PLAYTHROUGH_RECORD_SCHEMA,
        reward_contract=reward_contract,
        overdue_passenger_threshold=overdue_threshold,
        fleet_action_contract=FLEET_ACTION_CONTRACT,
        carriage_action_contract=CARRIAGE_ACTION_CONTRACT,
    )

    for _ in range(max_steps):
        action = agent.act(observation)
        action_snapshot = deepcopy(action)
        validate_replay_action(
            action_snapshot,
            fleet_actions_allowed=True,
            carriage_actions_allowed=True,
            label="agent action",
        )
        observation, reward, done, _ = env.step(action, dt_ms=dt_ms)
        deliveries, line_credits = _observation_metrics(observation, env)
        record.actions.append(action_snapshot)
        record.steps.append(
            PlaythroughStep(
                action=deepcopy(action_snapshot),
                reward=reward,
                score=line_credits,
                time_ms=observation["structured"]["time_ms"],
                is_done=done,
                deliveries=deliveries,
                line_credits=line_credits,
            )
        )
        if done:
            break

    record.final_deliveries, record.final_line_credits = _observation_metrics(
        observation, env
    )
    record.final_score = record.final_line_credits
    return record.final_score, record


def run_agent_playthrough_deliveries(
    agent: Agent | None = None,
    *,
    seed: int | None = None,
    max_steps: int = 100,
    dt_ms: int | None = None,
    env: MiniMetroEnv | None = None,
) -> tuple[int, PlaythroughRecord]:
    """Run a playthrough and return its canonical delivered-passenger total."""

    _, record = run_agent_playthrough(
        agent,
        seed=seed,
        max_steps=max_steps,
        dt_ms=dt_ms,
        env=env,
    )
    return record.final_deliveries, record


def iter_playthrough_observations(
    record: PlaythroughRecord,
    *,
    env: MiniMetroEnv | None = None,
    max_steps: int | None = None,
) -> Iterable[Dict[str, Any]]:
    schema = getattr(record, "schema", PLAYTHROUGH_RECORD_SCHEMA_V1)
    reward_contract = _record_reward_contract(record)
    overdue_threshold = _record_overdue_passenger_threshold(record)
    _record_fleet_action_contract(record)
    _record_carriage_action_contract(record)
    _reject_record_live_only_actions(record)
    if schema == PLAYTHROUGH_RECORD_SCHEMA_V5:
        _validate_record_actions(record, allow_fleet=True, allow_carriages=True)
    elif schema == PLAYTHROUGH_RECORD_SCHEMA_V4:
        _reject_record_carriage_actions(record)
    else:
        _validate_record_actions(record, allow_fleet=False, allow_carriages=False)
    if env is None:
        env, _ = _new_environment(record.dt_ms, reward_contract)
    observation = env.reset(seed=record.seed)
    if schema == PLAYTHROUGH_RECORD_SCHEMA_V4:
        _validate_record_actions(record, allow_fleet=True, allow_carriages=False)
    _apply_overdue_passenger_threshold(env, overdue_threshold)
    yield observation

    actions = record.actions
    if max_steps is not None:
        actions = actions[:max_steps]

    for action in actions:
        if schema in {PLAYTHROUGH_RECORD_SCHEMA_V4, PLAYTHROUGH_RECORD_SCHEMA_V5}:
            observation, _, done, _ = env.step(action, dt_ms=record.dt_ms)
        else:
            observation, _, done, _ = legacy_auto_assignment_step(
                env, action, dt_ms=record.dt_ms
            )
        yield observation
        if done:
            break


def replay_playthrough(
    record: PlaythroughRecord,
    *,
    env: MiniMetroEnv | None = None,
    max_steps: int | None = None,
) -> int:
    if env is None:
        env, _ = _new_environment(record.dt_ms, _record_reward_contract(record))
    for _ in iter_playthrough_observations(record, env=env, max_steps=max_steps):
        pass
    return _mediator_line_credits(env)


def replay_playthrough_deliveries(
    record: PlaythroughRecord,
    *,
    env: MiniMetroEnv | None = None,
    max_steps: int | None = None,
) -> int:
    """Replay a record and return its canonical delivered-passenger total."""

    if env is None:
        env, _ = _new_environment(record.dt_ms, _record_reward_contract(record))
    for _ in iter_playthrough_observations(record, env=env, max_steps=max_steps):
        pass
    return _mediator_deliveries(env)
