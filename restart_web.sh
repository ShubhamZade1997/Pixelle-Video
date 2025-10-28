#!/bin/bash
# Restart ReelForge Web UI on port 8502

echo "🔄 Restarting ReelForge Web UI on port 8502..."
echo ""

# Check if config.yaml exists
if [ ! -f config.yaml ]; then
    echo "⚠️  config.yaml not found, copying from config.example.yaml..."
    cp config.example.yaml config.yaml
    echo "✅ config.yaml created"
    echo ""
    echo "📝 Please edit config.yaml and fill in your API keys before using."
    echo ""
fi

# Check if port 8502 is in use
PORT=8502
PID=$(lsof -ti:$PORT)

if [ ! -z "$PID" ]; then
    echo "⚠️  Port $PORT is in use by process $PID"
    echo "🛑 Killing process $PID..."
    kill -9 $PID
    sleep 1
    echo "✅ Process killed"
    echo ""
fi

# Start Streamlit in background with nohup
echo "🚀 Starting ReelForge Web UI in background..."
nohup uv run streamlit run web.py --server.port $PORT > nohup.out 2>&1 &

# Wait a moment and check if the process started
sleep 2
NEW_PID=$(lsof -ti:$PORT)

if [ ! -z "$NEW_PID" ]; then
    echo "✅ ReelForge Web UI started successfully!"
    echo "📝 Process ID: $NEW_PID"
    echo "🌐 Access at: http://localhost:$PORT"
    echo "📄 Logs: nohup.out"
else
    echo "❌ Failed to start ReelForge Web UI"
    echo "📄 Check nohup.out for error details"
    exit 1
fi

echo ""

