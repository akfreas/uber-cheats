#!/bin/bash
set -e

# Activate virtual environment if not already activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    source /app/venv/bin/activate
fi

# Start the backend server with reload enabled
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start a simple HTTP server for the frontend built files
cd ../frontend/build
python3 -m http.server 3000 &
FRONTEND_PID=$!

# Function to kill both servers
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}

# Set up trap to catch Ctrl+C and SIGTERM
trap cleanup INT TERM

echo "Backend server running on http://0.0.0.0:8000"
echo "Frontend server running on http://localhost:3000"

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID 