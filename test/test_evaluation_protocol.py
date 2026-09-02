"""An evaluation's sample size is a horizon, and a handful of trials stops short.

A configuration here was published as **6.17 mean deliveries, max 19** on six
evaluation episodes. Twelve held-out episodes gave **1.50, max 9**. The number
had already been committed and written into a summary before anyone re-ran it.

Nothing was wrong with the arithmetic. Outcomes on this game are near-bimodal --
either the opening drag lands and the run continues, or it does not and the run
dies at exactly the decision deadline -- so a mean over a handful of episodes is
mostly a count of lucky seeds and its variance is enormous. The qualitative
finding survived the correction; the effect size did not.

The same shape cost more later: in-training evaluation ran on five episodes
against a score distribution spanning 110 to 800, an MDE near +/-190, so every
"new best, saved" was a five-sample lottery and the checkpoints picked that way
are what later comparisons were run against.

`docs/rl-model-selection.md` pre-registers the sample size, and this gate reads
the number out of that document rather than restating it, so the two cannot
drift apart.

WHAT BOUNDS THIS GATE: it binds the DEFAULT of each entry point, not every run.
`--episodes 1` remains available and CI's smoke jobs use it deliberately -- a
smoke test is not a comparison. What the gate removes is the case the defect
actually came from: a run launched without thinking about n, whose number is
then quoted as though it meant something.
"""

import ast
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs" / "rl-model-selection.md"

# The flags that decide how many episodes a reported number is averaged over.
EPISODE_FLAGS = ("--episodes", "--eval-episodes")

# The entry points are DISCOVERED, not listed. A hand-written list is an
# exemption list wearing a different hat: the next evaluation script somebody
# adds sits outside the gate until someone remembers to add it, which is the
# same silence the lesson is about. `test_a_new_script_is_inside_the_gate_the_day_it_is_written`
# below proves the discovery actually reaches a script this file has never seen.


# The floor lives HERE, not only in the document. An earlier version of this
# gate read its bound entirely out of `docs/rl-model-selection.md` and checked
# only that the number was at least 2 -- so editing one word of prose to "at
# least 2" would have made the whole gate green with both 10-episode defaults
# restored, and 2 is precisely "a handful of trials". The document may raise the
# bar; it may not lower it below what was measured. 6 episodes read 6.17 mean
# where 12 held-out episodes read 1.50.
MEASURED_FLOOR = 20


def _pre_registered_minimum() -> int:
    text = PROTOCOL.read_text(encoding="utf-8")
    found = re.search(r"at least (\d+) deterministic evaluation episodes", text)
    if found is None:
        raise AssertionError(
            f"{PROTOCOL.name} no longer states a minimum evaluation episode "
            "count in the form 'at least N deterministic evaluation episodes'; "
            "the pre-registered number is what this gate enforces, so without "
            "it there is nothing to enforce"
        )
    return int(found.group(1))


UNRESOLVED = object()


def _declared_episode_defaults(folder: Path) -> dict[str, object]:
    """Every `--episodes`/`--eval-episodes` default declared under `folder`.

    Resolves a module-level named constant, because a literal and a name bound
    to a literal are the same default and reporting the second as unreadable
    would fail a script that is doing the right thing.
    """
    found: dict[str, object] = {}
    for script in sorted(folder.glob("*.py")):
        try:
            tree = ast.parse(script.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        constants = {
            target.id: statement.value.value
            for statement in tree.body
            if isinstance(statement, ast.Assign)
            and isinstance(statement.value, ast.Constant)
            for target in statement.targets
            if isinstance(target, ast.Name)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "add_argument"):
                continue
            if not node.args:
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and first.value in EPISODE_FLAGS):
                continue
            key = f"{script.name} {first.value}"
            found[key] = None
            for keyword in node.keywords:
                if keyword.arg != "default":
                    continue
                value = keyword.value
                if isinstance(value, ast.Constant):
                    found[key] = _as_count(value.value)
                elif isinstance(value, ast.Name) and value.id in constants:
                    found[key] = _as_count(constants[value.id])
                else:
                    found[key] = UNRESOLVED
    return found


def _as_count(value):
    """An episode count is an int, and anything else is unreadable, not small.

    `default="20"` would raise a TypeError on the comparison rather than fail
    the assertion -- red for the wrong reason, which is indistinguishable from
    a broken gate at the moment someone is trying to read one.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return UNRESOLVED
    return value


class EveryReportedScoreMeetsThePreRegisteredSampleSize(unittest.TestCase):
    def setUp(self):
        self.minimum = _pre_registered_minimum()

    def test_the_protocol_does_not_pre_register_a_handful(self):
        """The control, and it has to be a floor rather than a sanity check.

        This gate reads its bound out of a prose document. If the only check on
        that number is "greater than one", the gate is defeated by editing the
        prose -- which is not a hypothetical, since lowering the bar is exactly
        what someone under time pressure would reach for.
        """
        self.assertGreaterEqual(
            self.minimum,
            MEASURED_FLOOR,
            f"{PROTOCOL.name} pre-registers {self.minimum} evaluation episodes "
            f"against a measured floor of {MEASURED_FLOOR}; the document may "
            "raise this bar and may not lower it, because the number below it "
            "is what produced a published 6.17 that twelve held-out episodes "
            "put at 1.50",
        )

    def _short_and_unreadable(self, declared, bar):
        short = {
            key: value
            for key, value in declared.items()
            if value is not UNRESOLVED and (value is None or value < bar)
        }
        unreadable = sorted(
            key for key, value in declared.items() if value is UNRESOLVED
        )
        return short, unreadable

    def test_the_discovery_found_the_scripts_it_is_supposed_to_check(self):
        """The control: an empty sweep passes every assertion below."""
        declared = _declared_episode_defaults(ROOT / "scripts")

        self.assertGreaterEqual(
            len(declared),
            4,
            f"the sweep of scripts/ found {sorted(declared)}; if discovery has "
            "stopped finding the evaluation entry points, this gate is green "
            "because it is checking nothing",
        )

    def test_a_new_script_is_inside_the_gate_the_day_it_is_written(self):
        """Proving the REACH, not just one instance of it.

        The claim this file makes is about a CLASS -- every command that reports
        a comparable score -- and a hand-maintained list cannot make that claim,
        because the next script added sits outside it until somebody remembers.
        So the entry points are discovered, and this test adds a member of the
        class the discovery has never seen and requires it to be caught.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            fresh = Path(folder) / "evaluate_something_new.py"
            fresh.write_text(
                "import argparse\n"
                "def main():\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument('--episodes', type=int, default=5)\n",
                encoding="utf-8",
            )
            declared = _declared_episode_defaults(Path(folder))

        self.assertIn(
            "evaluate_something_new.py --episodes",
            declared,
            f"a newly added script declaring --episodes was not discovered "
            f"({sorted(declared)}); the gate would not cover it and the class "
            "claim in this file's header would be false",
        )
        short, _ = self._short_and_unreadable(declared, MEASURED_FLOOR)
        self.assertIn(
            "evaluate_something_new.py --episodes",
            short,
            f"a five-episode default in a newly added script was not reported "
            f"as short ({short}); discovery reaching it is not the same as the "
            "gate biting on it",
        )

    def test_no_entry_point_defaults_below_it(self):
        bar = max(self.minimum, MEASURED_FLOOR)
        declared = _declared_episode_defaults(ROOT / "scripts")
        short, unreadable = self._short_and_unreadable(declared, bar)

        self.assertEqual(
            unreadable,
            [],
            f"the declared default for {unreadable} is an expression this gate "
            "cannot read, so it cannot say whether the entry point meets the "
            "bar; use an integer literal or a module-level constant",
        )
        self.assertEqual(
            short,
            {},
            f"these entry points default below the pre-registered minimum of "
            f"{bar} episodes: {short}. A mean over a handful of episodes on a "
            "near-bimodal outcome is mostly a count of lucky seeds -- 6.17 over "
            "six episodes became 1.50 over twelve, and five episodes against a "
            "110-800 distribution made every saved 'best' a lottery",
        )


if __name__ == "__main__":
    unittest.main()
