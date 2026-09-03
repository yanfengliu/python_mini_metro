"""A test that skips without the RL extras must run in the job that has them.

CI's `build` job installs requirements-locked.txt, so every RL-dependent test skips
there. The `rl-smoke` job installs requirements-rl-locked.txt and runs a NAMED list
of modules. A module that skips in one and is absent from the other runs nowhere,
and its gate is a green tick over nothing.

That is not hypothetical. Guarding test_training_readout_contract.py on 2026-09-02
turned 7 errors into `OK (skipped=12)` in `build` and left those 12 tests with no
remote coverage at all, because the module was never added to the rl-smoke list.
This test is what would have caught that in the same commit; it was written red
against exactly that module.

BOUND. It finds guards by text, so it reasons about what a file SAYS, not what it
does: a module that skips for an RL reason without naming one of RL_PACKAGES is
invisible, and a module naming a marker without using one reads as guarded. This
file names every marker, which is why it excludes itself, and a second such file
would need excluding too. It reads workflow text, not the job graph -- it can see
`if:` and a missing lockfile because those are checked below, but not a workflow
disabled at the repository level, a runner that never provisions, or a depleted
Actions allowance, under which both jobs are dark and everything here is green by
absence. It asserts a module is NAMED, not that its tests passed there.

One consequence of being named, worth knowing before adding a module: a module that
raises SkipTest at import aborts unittest's loader for the WHOLE rl-smoke step,
before any test runs, so a broken RL install there reports zero tests rather than a
partial result. That is the right verdict for a job whose whole purpose is the RL
stack, but it is not a partial failure.
"""

import re
import unittest
from importlib.util import find_spec
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "test.yml"
TEST_DIR = REPO / "test"

# A module is RL-guarded when it skips AND the skip is about an RL package. Naming
# both halves keeps a platform guard (skipUnless on sys.platform) from reading as an
# RL guard, and catches spellings a fixed marker list would miss -- decorators, a
# bare SkipTest, an annotated constant.
SKIP_MARKERS = (
    "RL_DEPS_AVAILABLE",
    "RL dependencies unavailable",
    "SkipTest(",
    "skipTest(",
    "skipIf(",
    "skipUnless(",
)
RL_PACKAGES = (
    "torch",
    "stable_baselines3",
    "sb3_contrib",
    "PIL",
    "tensorboard",
)

# This file lists every marker above, so a text search cannot tell it apart from a
# file that uses one. It is excluded by name.
SELF = Path(__file__).stem

# The job key as it appears in the workflow, indented under the jobs mapping.
RL_SMOKE_KEY = "  rl-smoke:"


def rl_smoke_modules() -> set[str]:
    """The module names the rl-smoke job runs, read out of the workflow as text.

    Deliberately not parsed with PyYAML: PyYAML is not in requirements-locked.txt,
    so importing it here would fail in the very job this test has to pass in.
    """
    lines = [
        line
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if "python -m unittest -v test." in line and not line.lstrip().startswith("#")
    ]
    if len(lines) != 1:
        raise AssertionError(
            "expected exactly one uncommented `python -m unittest -v test.<module>` "
            f"line in {WORKFLOW.name}, found {len(lines)}; this test reads that line "
            "to learn which modules rl-smoke runs, so it cannot answer until the "
            "file has exactly one"
        )
    return {
        token.split(".", 1)[1]
        for token in re.split(r"\s+", lines[0])
        if token.startswith("test.")
    }


def guarded_modules() -> set[str]:
    found = set()
    for path in sorted(TEST_DIR.glob("test_*.py")):
        if path.stem == SELF:
            continue
        source = path.read_text(encoding="utf-8")
        skips = any(marker in source for marker in SKIP_MARKERS)
        about_rl = any(package in source for package in RL_PACKAGES)
        if skips and about_rl:
            found.add(path.stem)
    return found


def rl_smoke_job() -> str:
    """The rl-smoke job's text, from its key to the end of the file."""
    text = WORKFLOW.read_text(encoding="utf-8")
    if RL_SMOKE_KEY not in text:
        raise AssertionError(
            f"no `{RL_SMOKE_KEY.strip()}` job in {WORKFLOW.name}; every RL gate in "
            "this repo runs there, so its absence is the whole coverage story"
        )
    return text.split(RL_SMOKE_KEY, 1)[1]


class EveryGuardedModuleRunsSomewhere(unittest.TestCase):
    def test_each_module_that_skips_without_the_extras_is_named_in_rl_smoke(self):
        unreachable = sorted(guarded_modules() - rl_smoke_modules())
        self.assertEqual(
            unreachable,
            [],
            "these modules skip when the RL extras are absent and are not in the "
            f"rl-smoke module list, so they run nowhere: {', '.join(unreachable)}. "
            "Add each to the `Run RL contract and library smoke tests` step in "
            ".github/workflows/test.yml, or remove its skip guard.",
        )

    def test_the_job_does_not_name_a_module_that_does_not_exist(self):
        missing = sorted(
            name
            for name in rl_smoke_modules()
            if not (TEST_DIR / f"{name}.py").exists()
        )
        self.assertEqual(
            missing,
            [],
            f"rl-smoke names test modules that are not on disk: {', '.join(missing)}. "
            "unittest reports a renamed or deleted module as an error, so the job "
            "would go red for a reason unrelated to the code under test.",
        )

    def test_the_smoke_step_is_enabled_and_installs_the_extras(self):
        """Being named in a step that cannot run is not coverage.

        The check above reads a run: line. That line survives `if: false`,
        `continue-on-error: true`, and the step being moved into a job that installs
        the base lockfile -- each of which leaves every listed module running
        nowhere while the rest of this file stays green.
        """
        before_the_run = rl_smoke_job().split("python -m unittest -v test.", 1)[0]
        for disabler in ("if:", "continue-on-error:"):
            self.assertNotIn(
                disabler,
                before_the_run,
                f"the rl-smoke job carries `{disabler}` ahead of its module list; a "
                "module named in a step that may not run is not coverage, and the "
                "other checks here cannot see that",
            )
        self.assertIn(
            "requirements-rl-locked.txt",
            before_the_run,
            "the job that runs the RL module list does not install the RL lockfile "
            "before it, so every module named there would skip rather than run",
        )


class NoGuardIsPermanentlyFalse(unittest.TestCase):
    """A guard naming a package that does not exist skips in BOTH jobs, silently.

    `build` skips it because the extras are absent, which is correct. `rl-smoke`
    skips it too, because the name never resolves, and reports OK. The module runs
    nowhere and nothing is red -- and run_without_rl_extras.py cannot see it either,
    since there a correct guard and a permanently false one behave identically. Only
    the job that HAS the extras can tell them apart, which is where this runs.
    """

    def test_every_guard_package_resolves_where_the_extras_are_installed(self):
        if find_spec("torch") is None:
            self.skipTest("RL dependencies unavailable: this check belongs to rl-smoke")
        unresolvable = [name for name in RL_PACKAGES if find_spec(name) is None]
        self.assertEqual(
            unresolvable,
            [],
            "the RL extras are installed here, but these guard names do not "
            f"resolve: {unresolvable}. Every module guarded on one of them skips in "
            "both CI jobs and runs nowhere, while both jobs stay green.",
        )


if __name__ == "__main__":
    unittest.main()
