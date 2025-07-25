#!/usr/bin/env python3
"""
Start script for ESP32 WebUIFlasher from main directory.
"""

import sys
from pathlib import Path

# Add scripts directory to Python path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

if __name__ == "__main__":
    import uvicorn

    from webflasher import app

    print("🚀 Starting ESP32 Firmware Flash Web Tool...")
    print("📍 Open your browser to: http://localhost:8000")
    print("🔧 API documentation: http://localhost:8000/docs")
    print("💡 Press Ctrl+C to stop")

    uvicorn.run(
        app, host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
