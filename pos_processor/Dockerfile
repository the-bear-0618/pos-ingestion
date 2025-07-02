# ---- Base Stage ----
# Use a common base to define shared settings and create the non-root user.
FROM python:3.11-slim as base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot

# ---- Builder Stage ----
# Use a builder stage to install dependencies.
FROM base as builder
# Create a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pos_processor/requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime Stage ----
# This is the final, optimized image.
FROM base as runtime
# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
# Copy the application code and shared schemas
COPY pos_processor/. .
COPY schemas ./schemas
# Switch to the non-root user
ENV PATH="/opt/venv/bin:$PATH"
USER nonroot
# Cloud Run provides the PORT env var. Gunicorn will use it.
ENV PORT 8080
# Use Gunicorn to start the Flask app defined as 'app' in 'main.py'
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app