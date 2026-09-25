FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

CMD ["uv", "run", "sh", "docker-entrypoint.sh"]
