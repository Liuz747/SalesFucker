#!/bin/bash

set -e

MODE=${MODE:-api}

TEMPORAL_HOST=${TEMPORAL_HOST:-temporal}
TEMPORAL_PORT=${TEMPORAL_PORT:-7233}

# Wait for Temporal
echo "⏳ Waiting for Temporal to start..."
until curl -sf "http://$TEMPORAL_HOST:$TEMPORAL_PORT" > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Temporal is ready!"

echo "Starting MAS in $MODE mode..."

if [ "$MODE" = "api" ]; then
    echo "Running migrations"
    uv run scripts/database.py
    echo "Launching FastAPI server..."
    exec uv run main.py
elif [ "$MODE" = "worker" ]; then
    echo "Launching Temporal worker..."
    exec uv run temporal-worker.py
else
    echo "ERROR: Unknown MODE '$MODE'. Valid values are 'api' or 'worker'"
    exit 1
fi