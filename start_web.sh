#!/bin/bash
# Start ReelForge Web UI

echo "🚀 Starting ReelForge Web UI..."
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

# Start Streamlit
uv run streamlit run web/app.py

