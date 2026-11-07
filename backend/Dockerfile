FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/backend

COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py \
    && pip install --no-cache-dir -e ".[dev]" \
    && rm -rf app

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
