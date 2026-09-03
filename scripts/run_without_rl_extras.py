"""Run a command with the optional RL packages hidden, as the base environment sees them.

WHY THIS EXISTS. CI has two Python jobs. `build` installs `requirements-locked.txt`
and runs the whole suite; `rl-smoke` installs `requirements-rl-locked.txt` and runs a
named list of RL modules. A development machine has the RL extras installed, so
`python -m unittest` there exercises a dependency set that `build` never has, and a
test that reaches for torch without skipping passes locally and fails only in CI.
That is how main's build job stayed red for 112 consecutive runs, the last green
being d6b5e39 on 2026-08-14; run 33777420299 is the newest, reporting
`Ran 1721 tests, FAILED (errors=11, skipped=37)`.

WHAT IT PROVES, AND ITS BOUND. It hides every import root provided only by a
distribution that requirements-rl-locked.txt pins and requirements-locked.txt does
not -- derived from the two lockfiles on every run, so a `uv pip compile` cannot
widen the hole silently. It hides them in THIS interpreter only: a child started with sys.executable sees the real
packages, so a test that shells out is outside this harness. Finders appended to
sys.meta_path after startup are not wrapped. And it proves nothing about any other
difference between a laptop and a runner -- not the OS, not the Python patch
version, not package versions. And it can only hide what is installed here: the
mapping from distribution to import root comes from the local environment, so a
root is missed if its package is absent on this machine.

USAGE
    python scripts/run_without_rl_extras.py -m unittest
    python scripts/run_without_rl_extras.py -m unittest -v test.test_instrument_knobs
    python scripts/run_without_rl_extras.py scripts/some_script.py --flag

The exit status is the wrapped command's own.
"""

from __future__ import annotations

import os
import re
import runpy
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE_LOCKFILE = REPO / "requirements-locked.txt"
RL_LOCKFILE = REPO / "requirements-rl-locked.txt"

# Roots that must come out of the derivation below. A hand-written list goes stale
# silently the next time `uv pip compile` runs, which is why the real set is
# derived -- but a derivation that quietly produces nothing is worse than a stale
# list, so these five are asserted rather than assumed.
REQUIRED_ROOTS = frozenset(
    {"PIL", "sb3_contrib", "stable_baselines3", "tensorboard", "torch"}
)


def _normalize(distribution: str) -> str:
    return distribution.lower().replace("_", "-")


def _pinned(lockfile: Path) -> set[str]:
    return {
        _normalize(match.group(1))
        for line in lockfile.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^([A-Za-z0-9_.-]+)==", line))
    }


def _rl_only_distributions() -> frozenset[str]:
    """Everything requirements-rl-locked.txt pins that requirements-locked.txt does not.

    Measured 2026-09-03: base pins 8 distributions, RL pins 47, so 39 are RL-only --
    torch and Pillow, but also setuptools, packaging, networkx, sympy and jinja2,
    which a test reaches for without thinking and which `build` does not have.
    """
    base, rl = _pinned(BASE_LOCKFILE), _pinned(RL_LOCKFILE)
    if not base or not rl:
        raise RuntimeError(
            f"parsed {len(base)} pins from {BASE_LOCKFILE.name} and {len(rl)} from "
            f"{RL_LOCKFILE.name}; this harness hides what the second has and the first "
            f"does not, so it cannot run until both parse"
        )
    return frozenset(rl - base)


def _blocked_roots() -> frozenset[str]:
    """Import roots provided ONLY by RL-only distributions.

    Mapped through importlib.metadata rather than guessed, because a distribution
    name is not an import root: pillow ships PIL, protobuf ships google, grpcio
    ships grpc, setuptools ships pkg_resources and _distutils_hack. A root that any
    base distribution also provides is left alone.
    """
    rl_only = _rl_only_distributions()
    roots = set()
    for root, providers in metadata.packages_distributions().items():
        normalized = {_normalize(name) for name in providers}
        if normalized and normalized <= rl_only:
            roots.add(root)
    return frozenset(roots)


BLOCKED_DISTRIBUTIONS = _rl_only_distributions()
BLOCKED = _blocked_roots()

if BLOCKED and not REQUIRED_ROOTS <= BLOCKED:
    raise RuntimeError(
        f"the RL extras are installed but these roots were not derived as RL-only: "
        f"{sorted(REQUIRED_ROOTS - BLOCKED)}. Hiding nothing would make every run "
        f"here a false green, so the harness refuses instead."
    )

USAGE = "usage: run_without_rl_extras.py (-m MODULE | SCRIPT) [args...]"


class HidesBlockedRoots:
    """Wraps one finder so a blocked root is reported absent rather than found.

    Answering "not found" -- rather than raising -- is what a genuinely missing
    package does: `import torch` raises ModuleNotFoundError from the import
    machinery, and `importlib.util.find_spec("torch")` returns None. Tests guard
    on both, so both have to behave.
    """

    def __init__(self, inner):
        self.inner = inner

    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] in BLOCKED:
            return None
        find = getattr(self.inner, "find_spec", None)
        return None if find is None else find(fullname, path, target)

    def find_distributions(self, context=None):
        """Delegate metadata lookups, minus the blocked distributions.

        Without this, importlib.metadata sees a meta_path of objects that cannot
        answer, and reports EVERY package as uninstalled -- numpy and pygame-ce
        included. That is a false red: `build` has those installed.
        """
        find = getattr(self.inner, "find_distributions", None)
        if find is None:
            return ()
        return (
            distribution
            for distribution in find(context)
            if _normalize(distribution.name or "") not in BLOCKED_DISTRIBUTIONS
        )

    def invalidate_caches(self):
        invalidate = getattr(self.inner, "invalidate_caches", None)
        if invalidate is not None:
            invalidate()


def hide_blocked_roots() -> None:
    sys.meta_path = [HidesBlockedRoots(finder) for finder in sys.meta_path]
    for name in [n for n in sys.modules if n.partition(".")[0] in BLOCKED]:
        del sys.modules[name]


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE, file=sys.stdout if argv else sys.stderr)
        return 0 if argv else 2

    hide_blocked_roots()

    if argv[0] == "-m":
        # `python -m X` puts the working directory first on sys.path; running this
        # file puts its own directory there instead, so restore it before discovery.
        sys.path[0] = os.getcwd()
        if len(argv) < 2:
            print(f"{USAGE}\n-m needs a module name", file=sys.stderr)
            return 2
        module, rest = argv[1], argv[2:]
        sys.argv = [module, *rest]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    else:
        script, rest = argv[0], argv[1:]
        # `python script.py` puts the SCRIPT's directory first; ten scripts here
        # import a sibling by bare name and need it.
        sys.path[0] = os.path.dirname(os.path.abspath(script)) or os.getcwd()
        sys.argv = [script, *rest]
        runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    # unittest raises SystemExit from inside run_module with its own status, so
    # main() only returns for a wrapped command that does not exit by itself.
    raise SystemExit(main(sys.argv[1:]))
