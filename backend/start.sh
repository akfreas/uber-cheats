#!/bin/bash

# Start cron
service cron start

# Start the FastAPI app
cd /app/backend && uvicorn main:app --host 0.0.0.0 --port 8000 