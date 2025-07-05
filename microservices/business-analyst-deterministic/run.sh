#!/bin/bash

# Run script for business-analyst-deterministic development

set -e

SERVICE_NAME="business-analyst-deterministic"
PORT="${PORT:-8081}"

echo "Starting ${SERVICE_NAME} development server..."

# Set PYTHONPATH
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Start the service
cd src
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT} --reload --log-level info

echo "Service started on http://localhost:${PORT}"