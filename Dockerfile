FROM python:3.13-alpine

# Set environment variables to prevent Python from writing .pyc files to disk and buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies needed for building Python packages
RUN apk add --no-cache build-base libffi-dev

# Create and set the working directory
WORKDIR /app

# Copy the requirements.txt file to the working directory
COPY requirements.txt .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py bot.py

# Create a non-root user and switch to it
RUN adduser -D myuser
USER myuser

# Command to run the application
ENTRYPOINT ["python", "bot.py"]
