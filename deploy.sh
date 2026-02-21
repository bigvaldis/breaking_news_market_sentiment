#!/bin/bash
# Build frontend and run production server
set -e
cd "$(dirname "$0")"

echo "Installing Python dependencies..."
pip install -r requirements.txt -q

echo "Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..

echo "Starting server on port ${PORT:-5001}..."
exec gunicorn -w 2 -b 0.0.0.0:${PORT:-5001} api.app:app
