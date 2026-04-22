FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    fonts-dejavu \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv pip install --system -e .

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000

CMD ["uvicorn", "bot_estiv.main:app", "--host", "0.0.0.0", "--port", "8000"]
