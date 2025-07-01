# --- Stage 1: Build Stage ---
    FROM python:3.9-slim-bullseye AS builder
    WORKDIR /app
    RUN python -m venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    RUN pip install --upgrade pip
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . /app/
    COPY ../schemas/ /app/schemas/
    
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
    # --- THIS IS THE FIX ---
    # Use shell form to allow environment variable substitution for PORT.
    CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 main:app