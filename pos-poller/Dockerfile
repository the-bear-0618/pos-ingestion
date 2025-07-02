# Use an official Python runtime as a parent image
# Using a specific, recent version is a good practice.
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Prevent python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user for security
RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot

# Copy the requirements file. The path is now correct for the build context.
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code. The path is now correct.
COPY . .

# Switch to the non-root user
USER nonroot

# Cloud Run provides the PORT env var. Gunicorn will use it.
ENV PORT 8080

# Use Gunicorn to start the Flask app defined as 'app' in 'main.py'
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app