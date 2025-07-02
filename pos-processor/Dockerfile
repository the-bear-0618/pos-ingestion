# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file from the build context (./pos-processor) into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code from the build context into the container
COPY . .

# Tell Cloud Run what port the application listens on
ENV PORT 8080

# Run main.py when the container launches.
# Assumes your entry point script is named main.py.
CMD ["python", "main.py"]