# --- Stage 1: Build Stage ---
    FROM python:3.9-slim-bullseye AS builder
    WORKDIR /app
    RUN python -m venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    RUN pip install --upgrade pip
    COPY services/pos-poller/requirements.txt .
    RUN pip install -r requirements.txt
    COPY services/pos-poller/ .
    
    # --- Stage 2: Final Production Image ---
    FROM python:3.9-slim-bullseye
    WORKDIR /app
    RUN useradd --system --no-create-home appuser
    COPY --from=builder /opt/venv /opt/venv
    COPY --from=builder /app .
    ENV PATH="/opt/venv/bin:$PATH"
    USER appuser
    EXPOSE 8080
    ENV PORT 8080
    ENV WORKERS 2
    ENV THREADS 4
    # Use shell form to allow environment variable substitution for PORT, WORKERS, etc.
    CMD gunicorn --bind 0.0.0.0:${PORT} --workers ${WORKERS} --threads ${THREADS} main:app