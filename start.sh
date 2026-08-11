#!/bin/bash

# Bringh Bot Start Script
# =======================

# Set PYTHONPATH so Python can find modules
export PYTHONPATH=/app:$PYTHONPATH

# Ensure data directory exists
mkdir -p /app/data

# Start admin web in background
python admin/app.py &
ADMIN_PID=$!

# Start bot in background
python bot/app.py &
BOT_PID=$!

# Wait for both processes
echo "Bringh Bot and Admin Web are starting..."
echo "Admin Web: http://localhost:8080"
echo "Bot: Running in background"

# Trap signals to kill both processes
cleanup() {
    echo "Stopping Bringh Bot..."
    kill -TERM $BOT_PID 2>/dev/null
    kill -TERM $ADMIN_PID 2>/dev/null
    wait $BOT_PID 2>/dev/null
    wait $ADMIN_PID 2>/dev/null
    echo "Bringh Bot stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Wait for both processes
wait $ADMIN_PID
wait $BOT_PID
