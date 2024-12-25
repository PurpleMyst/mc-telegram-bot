#!/bin/bash

# Define the lock file path
LOCK_FILE="/tmp/minecraft_server.lock"

# Check if the lock file exists
if [ ! -f "$LOCK_FILE" ]; then
    echo "Server is not running!"
    exit 1
fi

# Read the server PID from the lock file
SERVER_PID=$(cat "$LOCK_FILE")

# Check if the process with the recorded PID is still running
if ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo "Stopping Minecraft server with PID $SERVER_PID..."
    kill "$SERVER_PID"
else
    echo "Server process not found. Cleaning up stale lock file."
fi

# Remove the lock file
rm -f "$LOCK_FILE"

echo "Minecraft server stopped."
