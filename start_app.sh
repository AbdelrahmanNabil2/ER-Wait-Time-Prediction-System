#!/bin/bash

echo "ER Wait Time Prediction - Starting Services"
echo "=============================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed"
    exit 1
fi

echo "Checking dependencies..."
python3 -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Streamlit not found. Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Dependencies OK"
echo ""

echo "Starting FastAPI server on port 8000..."
python3 main.py &
API_PID=$!

echo $API_PID > .api.pid

echo "Waiting for API to initialize..."
sleep 3

if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
    echo "FastAPI server is running (PID: $API_PID)"
else
    echo "FastAPI server may not be ready yet..."
fi

echo ""

echo "Starting Streamlit app on port 8501..."
echo "Opening browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop both services"
echo "=============================================="
echo ""

streamlit run streamlit_app.py

cleanup() {
    echo ""
    echo "Stopping services..."
    
    if [ -f .api.pid ]; then
        API_PID=$(cat .api.pid)
        kill $API_PID 2>/dev/null
        rm .api.pid
        echo "FastAPI server stopped"
    fi
    
    echo "Goodbye!"
    exit 0
}

trap cleanup INT TERM

wait
