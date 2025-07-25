#!/bin/bash
# Custom entrypoint script for extended WebUIFlasher

echo "🚀 Starting Custom WebUIFlasher"
echo "================================"

# Check if custom firmware directory exists
if [ -d "$CUSTOM_FIRMWARE_PATH" ]; then
    echo "✅ Custom firmware found at $CUSTOM_FIRMWARE_PATH"
    ls -la "$CUSTOM_FIRMWARE_PATH"
else
    echo "ℹ️  No custom firmware directory found"
fi

# Apply custom configurations
if [ -f "/app/sources.yaml" ]; then
    echo "✅ Using custom sources configuration"
fi

# Set custom web UI title if provided
if [ -n "$WEBUI_TITLE" ]; then
    echo "🎨 Setting custom title: $WEBUI_TITLE"
fi

echo "🌐 WebUIFlasher will be available at: http://localhost:8000"
echo ""

# Execute the original command
exec "$@"
