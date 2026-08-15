"""A pointer head for the semantic lane: score each action from its own entities.

The working policy uses Stable-Baselines3's stock MLP, which flattens the whole
observation and predicts all 364 action logits from a single 64-unit vector. That
repeats, in a different costume, the mistake already measured on the pixel lane:
a flat categorical over locations predicted from a global bottleneck reached only
1.9x uniform, while reading the choice from the place it refers to beat it by
11.8x.

Here the same shape recurs twice over. Stations occupy fixed slots, so slot 3 and
slot 17 pass through entirely separate weights and the network must learn what a
station is twenty times without transfer. And nothing links observation slot *i*
to action index *i* -- that correspondence is pure memorisation.

This encodes every station with one shared MLP and scores an action from the
entities it names: CONNECT(a, b) from station a and station b, EXTEND(l, s) from
line l and station s, ASSIGN(p) from line p. The scoring function is shared, so
what is learned about one station applies to all twenty, and the link between an
action and its subject is structural rather than remembered.

The action table is fixed at import, so the gather indices are computed once.
"""

from __future__ import annotations

import torch
from torch import nn

from rl.semantic_env import (
    ACTION_TABLE,
    MAX_PATHS,
    MAX_STATIONS,
    PATH_FEATURES,
    REACH_FEATURES,
    RESOURCE_FEATURES,
    STATION_FEATURES,
    ActionKind,
)

STATION_BLOCK = MAX_STATIONS * STATION_FEATURES
PATH_BLOCK = MAX_PATHS * PATH_FEATURES


def _gather_indices():
    """For each action, which station and which line it refers to (-1 for none)."""
    stations, paths, kinds = [], [], []
    for kind, first, second in ACTION_TABLE:
        kinds.append(int(kind))
        if kind == ActionKind.CONNECT:
            stations.append((first, second))
            paths.append(-1)
        elif kind in (ActionKind.EXTEND_LINE, ActionKind.PREPEND_LINE):
            stations.append((second, second))
            paths.append(first)
        elif kind in (
            ActionKind.ASSIGN_LOCOMOTIVE,
            ActionKind.ATTACH_CARRIAGE,
            ActionKind.REMOVE_LINE,
        ):
            stations.append((-1, -1))
            paths.append(first)
        else:
            stations.append((-1, -1))
            paths.append(-1)
    return (
        torch.tensor(stations, dtype=torch.long),
        torch.tensor(paths, dtype=torch.long),
        torch.tensor(kinds, dtype=torch.long),
    )


class PointerExtractor(nn.Module):
    """Shared per-entity encoders plus a context vector, ready for pointer scoring."""

    def __init__(self, observation_space, features_dim: int = 128, width: int = 64):
        super().__init__()
        self.features_dim = features_dim
        self.width = width
        self.station = nn.Sequential(
            nn.Linear(STATION_FEATURES + MAX_PATHS, width),
            nn.ReLU(inplace=True),
            nn.Linear(width, width),
            nn.ReLU(inplace=True),
        )
        self.path = nn.Sequential(
            nn.Linear(PATH_FEATURES, width),
            nn.ReLU(inplace=True),
            nn.Linear(width, width),
            nn.ReLU(inplace=True),
        )
        self.context = nn.Sequential(
            nn.Linear(width * 2 + RESOURCE_FEATURES, features_dim),
            nn.ReLU(inplace=True),
        )
        self.station_embeddings: torch.Tensor | None = None
        self.path_embeddings: torch.Tensor | None = None

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        batch = observations.shape[0]
        cursor = 0
        stations = observations[:, cursor : cursor + STATION_BLOCK].view(
            batch, MAX_STATIONS, STATION_FEATURES
        )
        cursor += STATION_BLOCK
        paths = observations[:, cursor : cursor + PATH_BLOCK].view(
            batch, MAX_PATHS, PATH_FEATURES
        )
        cursor += PATH_BLOCK
        reach = observations[:, cursor : cursor + REACH_FEATURES].view(
            batch, MAX_STATIONS, MAX_PATHS
        )
        cursor += REACH_FEATURES
        resources = observations[:, cursor : cursor + RESOURCE_FEATURES]

        # Each station is encoded with its own distances to every line, so the
        # embedding already answers "how far is this station from that route".
        self.station_embeddings = self.station(torch.cat([stations, reach], dim=-1))
        self.path_embeddings = self.path(paths)
        pooled = torch.cat(
            [
                self.station_embeddings.mean(dim=1),
                self.path_embeddings.mean(dim=1),
                resources,
            ],
            dim=-1,
        )
        return self.context(pooled)


def build_pointer_policy_class():
    """Build lazily so importing this module does not require the RL stack."""
    from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy

    station_index, path_index, kind_index = _gather_indices()

    class PointerPolicy(MaskableActorCriticPolicy):
        """Action logits scored from the entities each action names."""

        def _build(self, lr_schedule) -> None:
            super()._build(lr_schedule)
            width = self.features_extractor.width
            latent = self.mlp_extractor.latent_dim_pi
            # One shared scorer over [context, station a, station b, line], with
            # absent entities zeroed. Shared weights are the point: what is
            # learned about one station transfers to all twenty.
            self.pointer = nn.Sequential(
                nn.Linear(latent + width * 3 + len(ActionKind), 128),
                nn.ReLU(inplace=True),
                nn.Linear(128, 1),
            )
            self.register_buffer("_station_index", station_index)
            self.register_buffer("_path_index", path_index)
            self.register_buffer(
                "_kind_onehot",
                torch.nn.functional.one_hot(kind_index, len(ActionKind)).float(),
            )
            self.optimizer = self.optimizer_class(
                self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
            )

        def _action_logits(self, latent_pi: torch.Tensor) -> torch.Tensor:
            extractor = self.features_extractor
            stations = extractor.station_embeddings
            paths = extractor.path_embeddings
            batch, actions = latent_pi.shape[0], len(ACTION_TABLE)
            width = stations.shape[-1]

            padded_stations = torch.cat(
                [stations, torch.zeros(batch, 1, width, device=stations.device)], dim=1
            )
            padded_paths = torch.cat(
                [paths, torch.zeros(batch, 1, width, device=paths.device)], dim=1
            )
            first = padded_stations[:, self._station_index[:, 0]]
            second = padded_stations[:, self._station_index[:, 1]]
            line = padded_paths[:, self._path_index]

            context = latent_pi.unsqueeze(1).expand(batch, actions, latent_pi.shape[-1])
            kinds = self._kind_onehot.unsqueeze(0).expand(batch, actions, -1)
            joined = torch.cat([context, first, second, line, kinds], dim=-1)
            return self.pointer(joined).squeeze(-1)

        def _get_action_dist_from_latent(self, latent_pi: torch.Tensor):
            return self.action_dist.proba_distribution(
                action_logits=self._action_logits(latent_pi)
            )

    return PointerPolicy
