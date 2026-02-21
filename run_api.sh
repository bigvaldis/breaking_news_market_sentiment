#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting Flask API at http://localhost:5001"
python api/app.py
