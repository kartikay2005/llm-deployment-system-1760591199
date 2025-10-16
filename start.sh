#!/bin/bash

# Render deployment start script
echo "Starting LLM Code Deployment System on Render..."

# Create data directory for deployment state
mkdir -p /app/data

# Initialize deployment state file if it doesn't exist
if [ ! -f "/app/data/deployment_state.json" ]; then
    echo "{}" > /app/data/deployment_state.json
fi

# Update deployment state file path
export DEPLOYMENT_STATE_FILE="/app/data/deployment_state.json"

# Start the application with gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app