#!/bin/bash

# Define the lock file path
LOCK_FILE="/tmp/minecraft_server.lock"

# Check if the server is already running or if a stale lock file exists
if [ -f "$LOCK_FILE" ]; then
    EXISTING_PID=$(cat "$LOCK_FILE")
    # Check if the process with the recorded PID is running
    if ps -p "$EXISTING_PID" > /dev/null 2>&1; then
        echo "Server is already running with PID $EXISTING_PID!"
        exit 1
    else
        echo "Stale lock file detected. Cleaning up."
        rm -f "$LOCK_FILE"
    fi
fi

# Create the lock file
echo $$ > "$LOCK_FILE"

# Navigate to the server folder
cd /path/to/server/folder || { echo "Failed to navigate to server folder"; exit 1; }

# Start the Minecraft server
echo "Starting Minecraft server..."
java -Xmx1024M -Xms1024M -jar server.jar nogui >> server.log 2>&1 &

# Get the process ID of the server and store it in the lock file
SERVER_PID=$!
echo $SERVER_PID > "$LOCK_FILE"

echo "Minecraft server started with PID $SERVER_PID."
