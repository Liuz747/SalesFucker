#!/bin/bash

set -e

MODE=${MODE:-api}

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