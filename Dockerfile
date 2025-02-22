# Use Node.js as base image for frontend build
FROM --platform=$BUILDPLATFORM node:18 as frontend-build

# Set working directory
WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Use Ubuntu as base image for final image
FROM --platform=$TARGETPLATFORM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    gnupg2 \
    curl \
    unzip \
    fonts-liberation \
    xvfb \
    software-properties-common \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome based on architecture
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
        && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
        && apt-get update \
        && apt-get install -y google-chrome-stable; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        apt-get update \
        && apt-get install -y chromium-browser; \
    fi \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create and activate virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install fastapi uvicorn websockets python-dotenv selenium webdriver-manager beautifulsoup4 pandas tabulate aiohttp openai

# Copy backend code
COPY backend/ backend/
COPY uber_deals.py .
COPY chat_deals.py .

# Copy built frontend from previous stage
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Copy start script
COPY start.sh .
RUN chmod +x start.sh

# Create directory for Chrome data and set permissions
RUN mkdir -p /app/.chrome-data && \
    chmod -R 777 /app/.chrome-data

# Set up X11 directories with correct permissions
RUN mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV CHROME_DATA_DIR=/app/.chrome-data
ENV DISPLAY=:99

# Set Chrome binary path based on architecture
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        echo "export CHROME_PATH=/usr/bin/google-chrome" >> /app/venv/bin/activate; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        echo "export CHROME_PATH=/usr/bin/chromium-browser" >> /app/venv/bin/activate; \
    fi

# Create a non-root user to run Chrome
RUN useradd -m -d /home/chrome chrome && \
    chown -R chrome:chrome /app /app/venv && \
    chown chrome:chrome /tmp/.X11-unix

# Create Xvfb startup script
RUN echo '#!/bin/bash\n\
mkdir -p /tmp/.X11-unix\n\
chmod 1777 /tmp/.X11-unix\n\
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\n\
sleep 1\n\
source /app/venv/bin/activate\n\
exec "$@"' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Switch to non-root user
USER chrome

# Expose ports
EXPOSE 3000 8000

# Start the application with Xvfb
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["./start.sh"] 