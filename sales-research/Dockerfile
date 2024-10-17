# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install any necessary dependencies from pyproject.toml or requirements.txt
RUN pip install --no-cache-dir poetry \
    && poetry install --no-dev

# Run the application with Uvicorn
# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run the application (assuming FastAPI or similar using Uvicorn)
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]