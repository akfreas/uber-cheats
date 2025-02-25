# Use Node.js as base image for frontend build
FROM node:18-slim as frontend-build

# Set working directory
WORKDIR /app/frontend

# Add build argument for API URL
ARG REACT_APP_API_URL=https://ubercheats.freas.me
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies using npm
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Use Ubuntu as base image for final image
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    unzip \
    gpg \
    jq \
    chromium-browser \
    chromium-chromedriver \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set up Python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the built frontend from the build stage
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Copy the rest of the application
COPY . /app
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Setup cron job
COPY backend/crontab /etc/cron.d/cleanup-cron
RUN chmod 0644 /etc/cron.d/cleanup-cron
RUN crontab /etc/cron.d/cleanup-cron
RUN touch /var/log/cron.log

# Make start script executable
RUN chmod +x /app/start.sh

ENTRYPOINT ["/app/start.sh"]