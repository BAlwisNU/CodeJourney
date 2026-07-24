# The sandbox image. The ONE component that genuinely must be a separate process.
#
# Pinned to 3.12 to match Pyodide 0.27.x's CPython. Bumping this without bumping
# the Pyodide version in apps/web/src/lib/pyodide.worker.ts reintroduces exactly
# the run/submit divergence the shared harness exists to prevent.
FROM python:3.12-slim

# The harness, and nothing else. No pip install: the sandbox has no network at
# runtime (--network=none), and every package present is attack surface for code
# we have decided to assume is hostile.
COPY harness.py /harness/harness.py

# Runtime hardening is applied by the caller, not baked in here -- see
# DockerRunner in apps/api/app/services/grading.py:
#   --network=none --memory=128m --cpus=0.5 --pids-limit=64
#   --read-only --tmpfs /tmp:size=8m -u nobody   timeout 5
USER nobody
