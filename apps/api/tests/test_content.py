"""Every exercise in the library must be solvable and internally consistent.

The exercise library is the most important artefact in the project, and a
broken exercise is worse than a missing one -- a student who writes a correct
solution and is told it's wrong learns to distrust the platform. These tests run
a reference solution through the real harness for every exercise, so a content
bug is caught here rather than by a confused student.

They also guard the two structural rules the whole study rests on.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages" / "harness"))
import harness  # noqa: E402

from app.content import ALL_EXERCISES  # noqa: E402
from app.content.games import GAMES  # noqa: E402

# A reference solution per slug. Adding an exercise without adding its solution
# here fails test_every_exercise_has_a_reference_solution -- deliberately, so the
# library cannot grow un-vetted.
SOLUTIONS = {
    "expired-quests": (
        "def expired_quests(quests, today):\n"
        "    return [q['name'] for q in quests "
        "if q['due_day'] < today and not q['done']]\n"
    ),
    "can-i-craft-it": (
        "def can_craft(inventory, recipe):\n"
        "    return all(inventory.get(i, 0) >= n for i, n in recipe.items())\n"
    ),
    "boss-fight": (
        "def turns_to_win(hp, damage, heal):\n"
        "    if damage <= heal:\n"
        "        return -1\n"
        "    turns = 0\n"
        "    while hp > 0:\n"
        "        hp -= damage\n"
        "        turns += 1\n"
        "        if hp > 0:\n"
        "            hp += heal\n"
        "    return turns\n"
    ),
    "save-game-names": (
        "def parse_save(name):\n"
        "    a, b, c = name.split(':')\n"
        "    return {'level': int(a.replace('lvl', '')), 'role': b, "
        "'xp': int(c.replace('xp', ''))}\n"
    ),
    "character-sheet": (
        "def power(c):\n"
        "    return c['level'] * 10 + c['hp']\n"
        "def is_tough(c):\n"
        "    return power(c) >= 100\n"
        "def describe(c):\n"
        "    p = power(c)\n"
        "    if is_tough(c):\n"
        "        return f\"{c['name']} the tough (power {p})\"\n"
        "    return f\"{c['name']} (power {p})\"\n"
    ),
    "high-score-table": (
        "def top_scores(contents, n):\n"
        "    rows = []\n"
        "    for line in contents.split('\\n'):\n"
        "        if line.strip() == '':\n"
        "            continue\n"
        "        name, score = line.split(',')\n"
        "        rows.append((int(score), name))\n"
        "    rows.sort(reverse=True)\n"
        "    return [name for _, name in rows[:n]]\n"
    ),
}


def _solution_for(spec):
    """A vetted solution: co-located `_solution` (lessons) or the SOLUTIONS
    table (the themed games set)."""
    return spec.get("_solution") or SOLUTIONS.get(spec["slug"])


@pytest.mark.parametrize("spec", ALL_EXERCISES, ids=lambda s: s["slug"])
def test_reference_solution_passes_every_test(spec):
    solution = _solution_for(spec)
    assert solution, f"{spec['slug']} has no reference solution"
    result = harness.run_tests(solution, spec["entrypoint"], spec["tests"])
    assert result["passed"], (
        f"{spec['slug']}: reference solution failed "
        f"{result['summary']}. A test case is wrong."
    )


@pytest.mark.parametrize("spec", ALL_EXERCISES, ids=lambda s: s["slug"])
def test_every_exercise_has_a_reference_solution(spec):
    """No exercise ships without a vetted solution proving it's solvable."""
    assert _solution_for(spec), (
        f"{spec['slug']} has no reference solution"
    )


@pytest.mark.parametrize("spec", ALL_EXERCISES, ids=lambda s: s["slug"])
def test_every_exercise_keeps_at_least_one_visible_test(spec):
    """Hidden tests stop hardcoding; they must not make feedback unactionable."""
    assert any(not t.get("hidden") for t in spec["tests"]), (
        f"{spec['slug']} has no visible test -- feedback would be a black box"
    )


@pytest.mark.parametrize("spec", ALL_EXERCISES, ids=lambda s: s["slug"])
def test_the_entrypoint_is_actually_defined(spec):
    """A starter that doesn't define the entrypoint is a broken first impression."""
    result = harness.run_tests(spec["starter_code"], spec["entrypoint"], [])
    assert result["phase"] != "missing_entrypoint", (
        f"{spec['slug']}: starter code never defines {spec['entrypoint']!r}"
    )


def test_slugs_are_unique():
    slugs = [s["slug"] for s in ALL_EXERCISES]
    assert len(slugs) == len(set(slugs)), "duplicate slug in the exercise library"


@pytest.mark.parametrize("spec", ALL_EXERCISES, ids=lambda s: s["slug"])
def test_tests_survive_the_json_round_trip(spec):
    """`tests` is a JSON column, so it must mean the same after a round-trip.

    The classic trap: a dict with integer keys. In Python `{2: [...]}` is fine,
    but JSON has only string keys, so it comes back as `{"2": [...]}` and can
    never equal a solution that returns integer keys -- the exercise would fail
    for every student. Catch it here, not in production.
    """
    import json

    for case in spec["tests"]:
        for field in ("args", "expected"):
            value = case.get(field)
            assert json.loads(json.dumps(value)) == value, (
                f"{spec['slug']} test {case['name']!r}: {field} changes shape when "
                f"stored as JSON (often an int-keyed dict or a tuple)"
            )
