#!/bin/bash

# Start the backend server
cd backend
python3 main.py &
BACKEND_PID=$!

# Start the frontend server
cd ../frontend
npm start &
FRONTEND_PID=$!

# Function to kill both servers
cleanup() {
    echo "Shutting down servers..."
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup INT

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID 