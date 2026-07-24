"""Shared test harness for CodeJourney.

This file is the single source of truth for how student code is executed and
graded. It runs in TWO places, unmodified:

  1. In the browser, under Pyodide, when a student hits "Run".
  2. On the server, inside the sandbox container, when a student hits "Submit".

Keeping one file for both is deliberate. If the run path and the submit path
could disagree, a student would see green on Run and red on Submit, and the
platform's core promise -- that failure is explainable -- would break at exactly
the moment it is being tested. Any divergence is a platform incident, not a
student error. See docs/architecture.md, "The divergence rule".

Constraints, because this runs under Pyodide:
  - stdlib only, and only modules Pyodide ships
  - no threading, no subprocess, no signal-based timeouts
  - no I/O other than what the caller injects

Timeouts are NOT enforced here. The browser enforces them by running Pyodide in
a Web Worker and terminating it; the server enforces them with `timeout` in the
container. Enforcing them differently is fine -- the *grading* is what must match.
"""

import copy
import io
import sys
import traceback

# The filename student code is compiled under. Appears in tracebacks, so it must
# be identical in both environments or error messages will differ.
STUDENT_FILENAME = "main.py"

MAX_REPR = 300


def _safe_repr(value):
    """repr() that can't itself blow up the harness or flood the UI."""
    try:
        text = repr(value)
    except BaseException:
        return f"<unreprable {type(value).__name__}>"
    if len(text) > MAX_REPR:
        return text[: MAX_REPR - 3] + "..."
    return text


def _student_line(exc):
    """Find the line number in the student's own file, ignoring harness frames.

    Novices need the line *they* wrote, not the innermost frame, which may be
    deep inside a stdlib call they've never heard of.
    """
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == STUDENT_FILENAME:
            line = frame.lineno
    return line


def _format_exception(exc):
    """Structured error info. The error-translation table (Week 4) consumes this.

    We return the raw pieces rather than a rendered string so the translator can
    pattern-match on `type` and `message` without re-parsing a traceback.
    """
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "line": _student_line(exc),
        # Full traceback is kept for the instructor view and the report, but the
        # student UI should render the translation, not this.
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
    }


def _load(source):
    """Exec student source into a fresh namespace.

    Returns (namespace, error). Syntax errors surface here, before any test runs.
    """
    namespace = {"__name__": "__main__", "__file__": STUDENT_FILENAME}
    stdout = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = stdout
        code = compile(source, STUDENT_FILENAME, "exec")
        exec(code, namespace)
    except BaseException as exc:
        return None, _format_exception(exc), stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    return namespace, None, stdout.getvalue()


def run_tests(source, entrypoint, tests):
    """Execute `source` and run `tests` against its `entrypoint` function.

    Args:
        source: the student's code, as a string.
        entrypoint: name of the function the tests call, e.g. "overdue_goals".
        tests: list of dicts, each with:
            name:     human-readable label, shown to the student
            args:     list of positional args to pass
            expected: the value the function should return
            hidden:   if True, the student sees pass/fail but not the args.
                      Hidden tests exist so exercises can't be gamed by
                      hardcoding, not to be mysterious -- keep at least one
                      visible test per exercise or feedback becomes unactionable.

    Returns a dict the frontend and the Submission row both consume directly:
        {
          "phase":  "loaded" | "syntax_error" | "missing_entrypoint",
          "error":  {type, message, line, traceback} | None,
          "stdout": str,            # printed at import time
          "tests":  [ {...}, ... ],
          "passed": bool,           # all tests passed
          "summary": {passed, total}
        }
    """
    namespace, error, import_stdout = _load(source)

    if error is not None:
        return {
            "phase": "syntax_error",
            "error": error,
            "stdout": import_stdout,
            "tests": [],
            "passed": False,
            "summary": {"passed": 0, "total": len(tests)},
        }

    function = namespace.get(entrypoint)
    if not callable(function):
        return {
            "phase": "missing_entrypoint",
            "error": {
                "type": "MissingFunction",
                "message": (
                    f"This exercise expects a function called {entrypoint!r}, "
                    "but it isn't defined yet."
                ),
                "line": None,
                "traceback": "",
            },
            "stdout": import_stdout,
            "tests": [],
            "passed": False,
            "summary": {"passed": 0, "total": len(tests)},
        }

    results = []
    for test in tests:
        results.append(_run_one(function, test))

    passed_count = sum(1 for r in results if r["status"] == "pass")
    return {
        "phase": "loaded",
        "error": None,
        "stdout": import_stdout,
        "tests": results,
        "passed": passed_count == len(results) and len(results) > 0,
        "summary": {"passed": passed_count, "total": len(results)},
    }


def _run_one(function, test):
    hidden = test.get("hidden", False)
    # deepcopy so a student mutating an argument can't corrupt later tests --
    # otherwise test 3 fails because of test 2 and the feedback is a lie.
    args = copy.deepcopy(test.get("args", []))
    expected = test.get("expected")

    stdout = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = stdout
        actual = function(*args)
    except BaseException as exc:
        sys.stdout = real_stdout
        return {
            "name": test.get("name", "test"),
            "status": "error",
            "hidden": hidden,
            "args": None if hidden else _safe_repr(args),
            "expected": None if hidden else _safe_repr(expected),
            "actual": None,
            "stdout": stdout.getvalue(),
            "error": _format_exception(exc),
        }
    finally:
        sys.stdout = real_stdout

    ok = _compare(actual, expected)
    return {
        "name": test.get("name", "test"),
        "status": "pass" if ok else "fail",
        "hidden": hidden,
        "args": None if hidden else _safe_repr(args),
        "expected": None if hidden else _safe_repr(expected),
        "actual": None if (hidden and not ok) else _safe_repr(actual),
        "stdout": stdout.getvalue(),
        "error": None,
    }


def _compare(actual, expected):
    """Equality with a float tolerance.

    Floats are compared with a tolerance because CPython and Pyodide can differ
    in the last bits on some operations, and because a novice computing a mean
    should not fail on 3.3333333333333335 != 3.3333333333333330. Exercises
    needing exact float equality should assert on a rounded value instead.
    """
    if isinstance(expected, float) and isinstance(actual, (int, float)):
        if isinstance(actual, bool):
            return False
        return abs(actual - expected) < 1e-9
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return False
        return all(_compare(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(_compare(actual[k], expected[k]) for k in expected)
    # bool/int: Python says True == 1. For a novice returning True where 1 is
    # expected, that's a real mistake worth surfacing, so compare types too.
    if isinstance(expected, bool) != isinstance(actual, bool):
        return False
    return actual == expected
