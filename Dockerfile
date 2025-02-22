# Use Node.js as base image for frontend build
FROM node:18 as frontend-build

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

# Use Python as base image for final image
FROM python:3.9-slim

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    curl \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxshmfence1 \
    libxss1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/* \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/* \
    && google-chrome --version

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV CHROME_DATA_DIR=/app/.chrome-data
ENV DISPLAY=:99

# Create a non-root user to run Chrome
RUN useradd -m -d /home/chrome chrome && \
    chown -R chrome:chrome /app

# Switch to non-root user
USER chrome

# Expose ports
EXPOSE 3000 8000

# Start the application
CMD ["./start.sh"] 