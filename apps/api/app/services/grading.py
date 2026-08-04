"""Executing student code and grading it.

Two runners behind one interface:

  LocalRunner   -- dev only. Runs the harness in a subprocess on the API host.
                   This is NOT a sandbox. It exists so the team can work on the
                   submit path before the sandbox image is built in Week 3, and
                   it refuses to start outside development.
  DockerRunner  -- the real one. One container per submission, no network, read-
                   only root, capped memory/pids/cpu, hard timeout.

The sandbox is the one component that genuinely must be a separate process. See
docs/architecture.md, "Logical separation, monolithic deployment" -- everything
else in this codebase is a module in one FastAPI app on purpose.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from ..config import get_settings

settings = get_settings()

def _find_harness() -> Path:
    """Locate packages/harness/harness.py -- the file Pyodide also loads.

    It sits in two different places depending on how the app is running, and
    this used to assume only the first:

      source checkout   <repo>/apps/api/app/services/  -> four levels up
      container         /app/app/services/             -> two levels up is /,
                        and the Dockerfile puts the harness at /packages

    Walking four parents from inside the container runs off the top of the
    filesystem and raises IndexError *at import time*, which takes the whole API
    down before it serves a single request -- and does so only in production,
    because development never reaches this path.

    Candidates are tried in order and the first that exists wins. Nothing raises
    here: if none are found the value is still a usable Path, and the failure
    surfaces at grading time with a message about the harness rather than as an
    import error three frames deep in uvicorn.
    """
    override = os.environ.get("HARNESS_PATH")
    if override:
        return Path(override)

    here = Path(__file__).resolve()
    candidates: list[Path] = []
    # A source checkout, where the repo root is four levels up.
    if len(here.parents) > 4:
        candidates.append(here.parents[4] / "packages" / "harness" / "harness.py")
    # The container, where apps/api/Dockerfile copies it to /packages/harness.
    candidates.append(Path("/packages/harness/harness.py"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


HARNESS_PATH = _find_harness()

# Wrapper that feeds the harness from stdin and prints its verdict as JSON.
# Kept as a string rather than a file because the Docker runner pipes it in.
_RUNNER = """
import json, sys
sys.path.insert(0, {harness_dir!r})
import harness

payload = json.loads(sys.stdin.read())
result = harness.run_tests(
    payload["source"], payload["entrypoint"], payload["tests"]
)
sys.stdout.write("\\n__CODEJOURNEY_RESULT__" + json.dumps(result))
"""


def _parse(stdout: str) -> dict:
    """Pull the verdict out of the runner's stdout.

    The sentinel exists because student code prints. Anything before the marker
    is theirs; everything after is ours. Splitting on a marker rather than
    parsing the whole stream is what keeps a student's `print("{}")` from being
    mistaken for a result.
    """
    marker = "__CODEJOURNEY_RESULT__"
    index = stdout.rfind(marker)
    if index == -1:
        return {
            "phase": "harness_error",
            "error": {
                "type": "HarnessError",
                "message": "The grader did not return a result.",
                "line": None,
                "traceback": stdout[-2000:],
            },
            "stdout": stdout,
            "tests": [],
            "passed": False,
            "summary": {"passed": 0, "total": 0},
        }
    return json.loads(stdout[index + len(marker) :])


def _timeout_result(seconds: int) -> dict:
    return {
        "phase": "timeout",
        "error": {
            "type": "Timeout",
            "message": (
                f"Your program was still running after {seconds} seconds, so it "
                "was stopped. This usually means a loop that never ends."
            ),
            "line": None,
            "traceback": "",
        },
        "stdout": "",
        "tests": [],
        "passed": False,
        "summary": {"passed": 0, "total": 0},
    }


class LocalRunner:
    """Dev-only. Not a sandbox. Do not deploy."""

    def __init__(self) -> None:
        if settings.environment != "development":
            raise RuntimeError(
                "LocalRunner runs untrusted code unsandboxed and must never be "
                "used outside development. Build the sandbox image and use "
                "DockerRunner."
            )

    def run(self, source: str, entrypoint: str, tests: list) -> dict:
        payload = json.dumps(
            {"source": source, "entrypoint": entrypoint, "tests": tests}
        )
        script = _RUNNER.format(harness_dir=str(HARNESS_PATH.parent))
        try:
            proc = subprocess.run(
                [sys.executable, "-c", script],
                input=payload,
                capture_output=True,
                text=True,
                timeout=settings.sandbox_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return _timeout_result(settings.sandbox_timeout_seconds)
        return _parse(proc.stdout)


class DockerRunner:
    """One container per submission. Week 3.

    Flags, and why each is there:
      --network=none     no exfiltration, no calling home for answers
      --memory=128m      caps allocation bombs
      --pids-limit=64    caps fork bombs, which --memory alone does not stop
      --read-only        student code cannot persist anything
      --tmpfs /tmp:8m    ...except a small scratch space, capped
      -u nobody          no root inside the container
      timeout 5          hard wall-clock kill, belt-and-braces with the SDK timeout
    """

    def run(self, source: str, entrypoint: str, tests: list) -> dict:
        payload = json.dumps(
            {"source": source, "entrypoint": entrypoint, "tests": tests}
        )
        script = _RUNNER.format(harness_dir="/harness")
        cmd = [
            "docker", "run", "--rm", "-i",
            "--network=none",
            "--memory=128m",
            "--cpus=0.5",
            "--pids-limit=64",
            "--read-only",
            "--tmpfs", "/tmp:size=8m",
            "-u", "nobody",
            settings.sandbox_image,
            "timeout", str(settings.sandbox_timeout_seconds),
            "python", "-c", script,
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=payload,
                capture_output=True,
                text=True,
                # Outer timeout is deliberately longer than the inner one: the
                # inner `timeout` should do the killing, and if it doesn't, this
                # catches a wedged container rather than racing it.
                timeout=settings.sandbox_timeout_seconds + 10,
            )
        except subprocess.TimeoutExpired:
            return _timeout_result(settings.sandbox_timeout_seconds)
        return _parse(proc.stdout)


def get_runner():
    if settings.environment == "development":
        return LocalRunner()
    return DockerRunner()
