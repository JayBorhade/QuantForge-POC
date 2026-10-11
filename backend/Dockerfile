FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system quantforge \
    && useradd --system --gid quantforge --home-dir /app --shell /usr/sbin/nologin quantforge

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=quantforge:quantforge . .

USER quantforge

EXPOSE 8000

# Schema migrations are a separate deploy/compose step, never an implicit
# side effect of every API replica starting.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
