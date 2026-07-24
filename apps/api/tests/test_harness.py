"""Tests for the shared harness.

These matter more than they look. This harness runs in two environments and the
project's central promise -- that failure is explainable -- rests on the two
agreeing. A bug here doesn't produce a wrong grade, it produces a student who
cannot trust the feedback.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages" / "harness"))

import harness  # noqa: E402

ENTRY = "expired_quests"

TESTS = [
    {
        "name": "one overdue",
        "args": [
            [
                {"name": "Slay the dragon", "due_day": 10, "done": False},
                {"name": "Find the sword", "due_day": 30, "done": False},
            ],
            15,
        ],
        "expected": ["Slay the dragon"],
        "hidden": False,
    },
    {
        "name": "boundary",
        "args": [[{"name": "Slay the dragon", "due_day": 10, "done": False}], 10],
        "expected": [],
        "hidden": True,
    },
]

CORRECT = '''
def expired_quests(quests, today):
    out = []
    for q in quests:
        if q["due_day"] < today and not q["done"]:
            out.append(q["name"])
    return out
'''


def test_correct_solution_passes():
    result = harness.run_tests(CORRECT, ENTRY, TESTS)
    assert result["passed"] is True
    assert result["summary"] == {"passed": 2, "total": 2}
    assert result["phase"] == "loaded"


def test_off_by_one_fails_the_boundary_test():
    source = CORRECT.replace('q["due_day"] < today', 'q["due_day"] <= today')
    result = harness.run_tests(source, ENTRY, TESTS)
    assert result["passed"] is False
    assert result["summary"]["passed"] == 1
    assert result["tests"][1]["status"] == "fail"


def test_syntax_error_reports_line_and_runs_no_tests():
    result = harness.run_tests("def f(:\n    pass", ENTRY, TESTS)
    assert result["phase"] == "syntax_error"
    assert result["error"]["type"] == "SyntaxError"
    assert result["tests"] == []
    assert result["passed"] is False


def test_missing_entrypoint_is_its_own_phase():
    result = harness.run_tests("x = 1", ENTRY, TESTS)
    assert result["phase"] == "missing_entrypoint"
    assert ENTRY in result["error"]["message"]


def test_runtime_error_points_at_the_students_line_not_a_harness_frame():
    source = '''
def expired_quests(quests, today):
    return quests[99]["name"]
'''
    result = harness.run_tests(source, ENTRY, TESTS)
    first = result["tests"][0]
    assert first["status"] == "error"
    assert first["error"]["type"] == "IndexError"
    # The line must be inside the student's file. If this points into the
    # harness, novices get told to fix code they never wrote.
    assert first["error"]["line"] == 3


def test_hidden_test_never_leaks_args_or_expected():
    result = harness.run_tests(CORRECT, ENTRY, TESTS)
    hidden = result["tests"][1]
    assert hidden["hidden"] is True
    assert hidden["args"] is None
    assert hidden["expected"] is None


def test_hidden_failing_test_does_not_leak_actual_either():
    source = CORRECT.replace('q["due_day"] < today', 'q["due_day"] <= today')
    result = harness.run_tests(source, ENTRY, TESTS)
    hidden = result["tests"][1]
    assert hidden["status"] == "fail"
    # A failing hidden test showing `actual` would hand over the answer shape.
    assert hidden["actual"] is None


def test_mutating_an_argument_cannot_corrupt_a_later_test():
    """Without deepcopy, test 2 fails because of what test 1 did.

    That produces feedback that is actively a lie, which is worse than no
    feedback for a novice who cannot yet tell the difference.
    """
    shared = [{"name": "A", "due_day": 1, "done": False}]
    tests = [
        {"name": "first", "args": [shared, 5], "expected": ["A"], "hidden": False},
        {"name": "second", "args": [shared, 5], "expected": ["A"], "hidden": False},
    ]
    source = '''
def expired_quests(quests, today):
    for q in quests:
        q["done"] = True          # destructive on purpose
    return [q["name"] for q in quests]
'''
    result = harness.run_tests(source, ENTRY, tests)
    assert result["passed"] is True
    assert shared[0]["done"] is False  # caller's data untouched


def test_student_print_is_captured_not_lost():
    source = '''
def expired_quests(quests, today):
    print("checking", today)
    return []
'''
    result = harness.run_tests(source, ENTRY, [
        {"name": "t", "args": [[], 5], "expected": [], "hidden": False}
    ])
    assert "checking 5" in result["tests"][0]["stdout"]


def test_import_time_print_is_captured():
    result = harness.run_tests("print('hello')\n" + CORRECT, ENTRY, TESTS)
    assert "hello" in result["stdout"]


@pytest.mark.parametrize(
    "expected,actual,should_match",
    [
        (3.3333333333333335, 3.333333333333333, True),   # float tolerance
        (1.0, 1.0000001, False),                          # beyond tolerance
        (1, True, False),                                 # bool is not int here
        (True, 1, False),
        ([1, 2], [1, 2], True),
        ({"a": 1}, {"a": 1}, True),
        ({"a": 1}, {"a": 1, "b": 2}, False),
    ],
)
def test_comparison_rules(expected, actual, should_match):
    assert harness._compare(actual, expected) is should_match
