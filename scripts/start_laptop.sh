#!/bin/bash

# Function to cleanup background processes
cleanup() {
    echo "🛑 Stopping NILA-V2..."
    if [ ! -z "$SERVER_PID" ]; then
        echo "🛑 Stopping TTS Server (PID: $SERVER_PID)..."
        kill $SERVER_PID
    fi
    exit
}

# Trap Ctrl+C
trap cleanup SIGINT

echo "🚀 Starting NILA-V2 (Laptop Mode)..."

# Check .env for TTS_PROVIDER
if grep -q "TTS_PROVIDER=ai4bharat" .env; then
    echo "🧠 AI4Bharat Provider detected!"
    echo "⏳ Starting local TTS server..."
    
    # Check if server requirements are installed (basic check)
    if ! python3 -c "import parler_tts" 2>/dev/null; then
        echo "⚠️  'parler_tts' not found. Installing server requirements..."
        pip install -r extra/tts_server/requirements.txt
    fi
    
    # Start Server in background
    cd extra/tts_server
    python3 server.py > ../../data/logs/tts_server.log 2>&1 &
    SERVER_PID=$!
    cd ../..
    
    echo "✅ TTS Server started (PID: $SERVER_PID). Logs: data/logs/tts_server.log"
    echo "⏳ Waiting for server to be ready..."
    sleep 5 # Give it a moment to load model
else
    echo "ℹ️  Using configured TTS provider (not ai4bharat)"
fi

# Start Main Robot
echo "🤖 Starting Robot..."
python3 main.py

# Cleanup on exit
cleanup
