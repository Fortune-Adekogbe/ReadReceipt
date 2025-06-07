# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
# This assumes your bot script is named bot.py and is in the same directory as the Dockerfile
# Adjust if your main script has a different name or is in a subdirectory.
COPY . .

# Expose a volume for downloads (good for persisting data)
# The bot script currently uses "temp_files/" relative to its execution path.
# So /app/temp_files/ will be the path inside the container.
VOLUME /app/temp_files

# Expose a volume for cookies (for easier management)
VOLUME /app/cookies

# Define environment variables for configuration (these will be set at runtime)
# You can set defaults here, but it's better to pass them during `docker run`

# Command to run the application
# Replace bot.py with the actual name of your main Python script
CMD ["python", "bot.py"]