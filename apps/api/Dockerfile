# Pinned to match Pyodide's CPython. See docs/architecture.md, "The divergence rule".
FROM python:3.12-slim

WORKDIR /app

# The Docker CLI, because grading shells out to `docker run` per submission
# (DockerRunner in app/services/grading.py). Without it the API starts fine and
# then fails on the first Submit with FileNotFoundError -- the worst kind of
# missing dependency, since nothing is wrong until a student presses the button.
#
# This is the client only. The daemon it talks to is the host's, reached through
# the mounted socket; see the warning on that mount in docker-compose.yml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" \
    pydantic pydantic-settings "passlib[bcrypt]" "bcrypt<4.1" pyjwt email-validator \
    httpx "pyjwt[crypto]" python-multipart anthropic

COPY apps/api/app ./app
# The shared harness. Same file the browser bundles -- neither side owns a copy.
COPY packages/harness /packages/harness

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
