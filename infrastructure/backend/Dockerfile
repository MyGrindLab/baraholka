FROM python:3.13-slim

ENV PYTHONPATH=/app

COPY backend /app/
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.12 /uv /uvx /bin/
RUN uv sync --frozen --no-cache

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--loop", "uvloop"]
