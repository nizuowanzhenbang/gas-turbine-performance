FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip \
 && pip install fastapi==0.115.0 "uvicorn[standard]==0.30.6" sqlalchemy==2.0.35 \
        "psycopg[binary]==3.2.3" alembic==1.13.3 pydantic==2.9.2 pydantic-settings==2.5.2 \
        "python-jose[cryptography]==3.3.0" bcrypt==4.2.0 python-multipart==0.0.12 \
        apscheduler==3.10.4 httpx==0.27.2 openpyxl==3.1.5 pandas==2.2.3 numpy==2.1.2

COPY app ./app

EXPOSE 8011

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8011/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
