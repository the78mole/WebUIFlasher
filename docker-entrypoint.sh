#!/bin/bash
set -e

echo "🐳 WebUIFlasher Docker Container Starting..."

# Check if we're running in a container
if [ -f /.dockerenv ]; then
    echo "✅ Running in Docker container"
else
    echo "⚠️  Not running in Docker container"
fi

# Check for USB devices
echo "🔍 Checking for USB devices..."
if ls /dev/ttyUSB* /dev/ttyACM* 1> /dev/null 2>&1; then
    echo "📱 Found USB devices:"
    ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true
else
    echo "⚠️  No USB devices found. Make sure devices are mapped in docker-compose.yml"
fi

# Check if sources.yaml exists (must be mounted from outside)
if [ ! -f "/app/sources.yaml" ]; then
    echo "❌ ERROR: sources.yaml not found!"
    echo "💡 You must mount a sources.yaml file from outside the container:"
    echo "   -v ./your-sources.yaml:/app/sources.yaml:ro"
    echo "📝 See sources_example.yaml for reference"
    exit 1
else
    echo "✅ Found sources.yaml configuration"
fi

# Download firmware if tmpfw is empty
if [ ! "$(ls -A /app/tmpfw 2>/dev/null)" ]; then
    echo "📥 Downloading firmware..."
    uv run scripts/update_firmwares.py --sources=sources.yaml || echo "⚠️  Firmware download failed, continuing anyway..."
else
    echo "✅ Firmware already present in tmpfw/"
fi

# Start the web server
echo "🚀 Starting WebUIFlasher server on http://0.0.0.0:8000"
exec uv run scripts/webflasher.py
