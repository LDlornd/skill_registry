FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SKILLS_DIR=/skills \
    HOST=0.0.0.0 \
    PORT=5000

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir . \
    && useradd --system --uid 10001 --create-home registry

USER registry

EXPOSE 5000
CMD ["skill-registry"]
