# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the subdirectory
COPY pos-processor/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code from the subdirectory
COPY pos-processor/ .

# Tell Cloud Run what port the application listens on
ENV PORT 8080

# Use Gunicorn to start the Flask app defined as 'app' in 'main.py'
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app