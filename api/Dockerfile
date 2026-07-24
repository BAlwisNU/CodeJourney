# Pinned to match Pyodide's CPython. See docs/architecture.md, "The divergence rule".
FROM python:3.12-slim

WORKDIR /app
COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" \
    pydantic pydantic-settings "passlib[bcrypt]" "bcrypt<4.1" pyjwt email-validator

COPY apps/api/app ./app
# The shared harness. Same file the browser bundles -- neither side owns a copy.
COPY packages/harness /packages/harness

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
