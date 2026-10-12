# Backend image — one Dockerfile, several targets so dev/test/prod can't drift.
#
#   base     python + uv + lockfile (shared by everything below)
#   test     base + `dev` extras (pytest, ruff, mypy, ...). Used by `make test-backend`
#            / `make lint-backend`; never pushed.
#   runtime  production image. MUST stay the LAST stage: CI builds this file with
#            no --target, and `docker build` without --target yields the last stage.
#
# Build context is the repo root (see Makefile / .github/workflows/backend-docker.yml).

FROM python:3.13-slim AS base

ENV PYTHONPATH=/app
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.12 /uv /uvx /bin/

# Dependency manifests first so source edits don't invalidate the deps layer.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version /app/


# --- test: dev extras on top of the runtime deps ----------------------------
FROM base AS test

# Bytecode would land in the bind-mounted source tree as root-owned files.
ENV PYTHONDONTWRITEBYTECODE=1 \
    # The venv is fixed at build time; `uv run` must never re-sync or hit the network.
    UV_NO_SYNC=1

RUN uv sync --frozen --no-cache --extra dev --no-install-project
COPY backend /app/

CMD ["uv", "run", "pytest"]


# --- runtime: production image (keep LAST) ----------------------------------
FROM base AS runtime

RUN uv sync --frozen --no-cache --no-install-project
COPY backend /app/
RUN uv sync --frozen --no-cache

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--loop", "uvloop"]
