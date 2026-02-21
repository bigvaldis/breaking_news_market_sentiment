#!/bin/bash
# Start Flask API and React frontend

cd "$(dirname "$0")"
ROOT="$(pwd)"

# Start Flask in background
echo "Starting Flask API on http://localhost:5001 ..."
source venv/bin/activate 2>/dev/null || . venv/bin/activate
python api/app.py &
FLASK_PID=$!

# Wait for Flask to be ready
sleep 3
if ! kill -0 $FLASK_PID 2>/dev/null; then
  echo "Flask failed to start. Run manually: python api/app.py"
  exit 1
fi

# Start React
echo "Starting React frontend on http://localhost:3000 ..."
cd frontend
npm run dev &
VITE_PID=$!

echo ""
echo "=========================================="
echo "  Both servers are running!"
echo "  Frontend: http://localhost:3000"
echo "  API:      http://localhost:5001"
echo "=========================================="
echo "Press Ctrl+C to stop both servers."
echo ""

# Wait for either to exit
wait $FLASK_PID $VITE_PID 2>/dev/null
kill $FLASK_PID $VITE_PID 2>/dev/null
exit 0
