"""Runtime and source snapshots used by RL manifests."""

from __future__ import annotations

import platform
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Any

DEFAULT_PACKAGE_NAMES = (
    "gymnasium",
    "numpy",
    "pygame-ce",
    "sb3-contrib",
    "shapely",
    "shortuuid",
    "stable-baselines3",
    "tensorboard",
    "torch",
)
COMPATIBILITY_PACKAGE_NAMES = (
    "gymnasium",
    "numpy",
    "pygame-ce",
    "sb3-contrib",
    "shapely",
    "shortuuid",
    "stable-baselines3",
    "torch",
)


def _require_nonempty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_exact_keys(
    document: Mapping[str, Any], expected: set[str], name: str
) -> None:
    actual = set(document)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"invalid {name} keys: missing={missing}, unknown={unknown}")


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    python_version: str
    platform_name: str
    package_versions: Mapping[str, str | None]

    def __post_init__(self) -> None:
        _require_nonempty(self.python_version, "python_version")
        _require_nonempty(self.platform_name, "platform_name")
        versions: dict[str, str | None] = {}
        for name in sorted(self.package_versions):
            _require_nonempty(name, "package name")
            version = self.package_versions[name]
            if version is not None:
                _require_nonempty(version, f"package version for {name}")
            versions[name] = version
        object.__setattr__(self, "package_versions", MappingProxyType(versions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "packageVersions": dict(self.package_versions),
            "platform": self.platform_name,
            "pythonVersion": self.python_version,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> RuntimeSnapshot:
        _require_exact_keys(
            document,
            {"packageVersions", "platform", "pythonVersion"},
            "runtime snapshot",
        )
        packages = document["packageVersions"]
        if not isinstance(packages, Mapping):
            raise TypeError("runtime packageVersions must be an object")
        return cls(
            python_version=document["pythonVersion"],
            platform_name=document["platform"],
            package_versions=packages,
        )


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    git_revision: str | None
    dirty_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.git_revision is not None:
            _require_nonempty(self.git_revision, "git_revision")
        normalized = {
            _require_nonempty(path, "dirty path") for path in self.dirty_paths
        }
        object.__setattr__(self, "dirty_paths", tuple(sorted(normalized)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dirtyPaths": list(self.dirty_paths),
            "gitRevision": self.git_revision,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> SourceSnapshot:
        _require_exact_keys(document, {"dirtyPaths", "gitRevision"}, "source snapshot")
        dirty_paths = document["dirtyPaths"]
        if not isinstance(dirty_paths, list):
            raise TypeError("source dirtyPaths must be an array")
        return cls(git_revision=document["gitRevision"], dirty_paths=tuple(dirty_paths))


def collect_runtime_snapshot(
    package_names: Sequence[str] = DEFAULT_PACKAGE_NAMES,
) -> RuntimeSnapshot:
    """Record runtime versions while representing absent optional packages as null."""

    versions: dict[str, str | None] = {}
    for name in sorted(set(package_names)):
        _require_nonempty(name, "package name")
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return RuntimeSnapshot(
        python_version=sys.version.replace("\n", " "),
        platform_name=platform.platform(),
        package_versions=versions,
    )


def _git_output(repo_root: Path, *arguments: str) -> str | None:
    safe_root = repo_root.resolve().as_posix()
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={safe_root}", *arguments],
            cwd=repo_root,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="surrogateescape",
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def _dirty_paths_from_porcelain(output: str) -> tuple[str, ...]:
    paths: set[str] = set()
    records = output.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise ValueError("invalid git porcelain status record")
        status = record[:2]
        paths.add(record[3:])
        if ("R" in status or "C" in status) and index < len(records):
            original_path = records[index]
            index += 1
            if original_path:
                paths.add(original_path)
    return tuple(sorted(paths))


def collect_source_snapshot(repo_root: str | Path = ".") -> SourceSnapshot:
    root = Path(repo_root)
    revision_output = _git_output(root, "rev-parse", "HEAD")
    status_output = _git_output(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    )
    revision = revision_output.strip() if revision_output else None
    dirty_paths = (
        _dirty_paths_from_porcelain(status_output) if status_output is not None else ()
    )
    return SourceSnapshot(git_revision=revision, dirty_paths=dirty_paths)


def _python_minor(version: str) -> str:
    numeric = version.split(maxsplit=1)[0]
    pieces = numeric.split(".")
    return ".".join(pieces[:2]) if len(pieces) >= 2 else numeric


def runtime_compatibility_differences(
    saved: RuntimeSnapshot,
    current: RuntimeSnapshot,
    package_names: Sequence[str] = COMPATIBILITY_PACKAGE_NAMES,
) -> tuple[str, ...]:
    """Return deterministic runtime differences that may affect pixels or policy."""

    differences: list[str] = []
    saved_python = _python_minor(saved.python_version)
    current_python = _python_minor(current.python_version)
    if saved_python != current_python:
        differences.append(f"python saved={saved_python!r} current={current_python!r}")
    if saved.platform_name != current.platform_name:
        differences.append(
            f"platform saved={saved.platform_name!r} current={current.platform_name!r}"
        )
    for name in sorted(set(package_names)):
        saved_version = saved.package_versions.get(name)
        current_version = current.package_versions.get(name)
        if saved_version != current_version:
            differences.append(
                f"{name} saved={saved_version!r} current={current_version!r}"
            )
    return tuple(differences)
