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

# Install necessary packages (including jq for JSON parsing)
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
    dbus-x11 \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-cyrillic \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and ChromeDriver
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | \
      gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    \
    # Extract Chrome version and major version
    GOOGLE_CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    GOOGLE_CHROME_MAJOR_VERSION=$(echo $GOOGLE_CHROME_VERSION | cut -d '.' -f 1) && \
    echo "Installed Chrome version: $GOOGLE_CHROME_VERSION" && \
    echo "Chrome major version: $GOOGLE_CHROME_MAJOR_VERSION" && \
    \
    # Depending on the major version, fetch the correct ChromeDriver:
    if [ "$GOOGLE_CHROME_MAJOR_VERSION" -ge 115 ]; then \
       echo "Using new endpoint for ChromeDriver (Chrome $GOOGLE_CHROME_MAJOR_VERSION)"; \
       echo "Fetching JSON from new endpoint:"; \
       curl -sS "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone.json" | tee /tmp/latest-versions.json; \
       echo "JSON content:"; cat /tmp/latest-versions.json; \
       echo "Querying for major version $GOOGLE_CHROME_MAJOR_VERSION"; \
       CHROMEDRIVER_VERSION=$(cat /tmp/latest-versions.json | jq -r --arg M "$GOOGLE_CHROME_MAJOR_VERSION" '.milestones[$M].version'); \
       echo "Extracted ChromeDriver version from new endpoint: ${CHROMEDRIVER_VERSION}"; \
       if [ -z "$CHROMEDRIVER_VERSION" ] || [ "$CHROMEDRIVER_VERSION" = "null" ]; then \
           echo "New endpoint did not return a valid version; falling back to legacy endpoint"; \
           CHROMEDRIVER_VERSION=$(curl -sS "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${GOOGLE_CHROME_MAJOR_VERSION}"); \
           echo "Legacy ChromeDriver version: ${CHROMEDRIVER_VERSION}"; \
       fi; \
       echo "Final ChromeDriver version to install: ${CHROMEDRIVER_VERSION}"; \
       FINAL_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
       echo "Downloading ChromeDriver from: ${FINAL_URL}" && \
       wget -q -O chromedriver_linux64.zip "${FINAL_URL}"; \
    else \
       echo "Using legacy endpoint for ChromeDriver (Chrome $GOOGLE_CHROME_MAJOR_VERSION)"; \
       CHROMEDRIVER_VERSION=$(curl -sS "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${GOOGLE_CHROME_MAJOR_VERSION}"); \
       echo "Installing ChromeDriver version: ${CHROMEDRIVER_VERSION}"; \
       wget -q -O chromedriver_linux64.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"; \
    fi && \
    \
    unzip -j chromedriver_linux64.zip -d /usr/local/bin && \
    rm chromedriver_linux64.zip && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /var/lib/apt/lists/* && \
    google-chrome --version
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

# Set up Chrome directories and permissions
RUN mkdir -p /app/.chrome-data && \
    mkdir -p /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix && \
    chown root:root /tmp/.X11-unix && \
    # Ensure Chrome directories are properly set up
    mkdir -p /var/lib/chrome && \
    mkdir -p /var/lib/chrome/chrome && \
    chmod -R 777 /var/lib/chrome

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV CHROME_DATA_DIR=/app/.chrome-data
ENV DISPLAY=:99
ENV CHROME_PATH=/usr/bin/google-chrome
ENV CHROME_DRIVER_PATH=/usr/local/bin/chromedriver

# Create a non-root user and set up permissions
RUN useradd -m -d /home/chrome chrome && \
    # Give chrome user access to necessary directories
    chown -R chrome:chrome /app /app/venv /app/.chrome-data /var/lib/chrome && \
    # Set up chromedriver permissions
    chown root:chrome /usr/local/bin/chromedriver && \
    chmod 755 /usr/local/bin/chromedriver && \
    # Set up chrome permissions
    chown root:chrome /usr/bin/google-chrome && \
    chmod 755 /usr/bin/google-chrome

# Create simple entrypoint script with Xvfb
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\nsleep 1\nexec "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER chrome

# Expose ports
EXPOSE 3000 8000

# Start the application with Xvfb
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["./start.sh"]