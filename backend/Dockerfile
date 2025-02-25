FROM python:3.9

WORKDIR /app

# Install cron
RUN apt-get update && apt-get -y install cron

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Set up cron job
COPY backend/crontab /etc/cron.d/cleanup-cron
RUN chmod 0644 /etc/cron.d/cleanup-cron
RUN crontab /etc/cron.d/cleanup-cron
RUN touch /var/log/cron.log

# Start script that runs both the FastAPI app and cron
COPY backend/start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"] 