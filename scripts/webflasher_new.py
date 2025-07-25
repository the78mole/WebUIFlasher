#!/usr/bin/env python3
"""
Web-based Firmware Flasher for ESP32

A FastAPI-based web interface for flashing ESP32 firmware.
Provides a user-friendly web interface for the flash utilities.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from flash_utils import load_sources_config

app = FastAPI(
    title="ESP32 Firmware Flash Tool",
    description="Web interface for flashing ESP32 firmware",
    version="1.0.0",
)


class FirmwareInfo:
    """Information about firmware for web display."""

    def __init__(self, name: str, source_config: dict):
        self.name = name
        self.type = source_config.get("type", "unknown")
        self.platform = source_config.get("platform", "unknown")
        self.description = self._get_description(source_config)
        self.available = self._check_availability(name)
        self.version = self._get_version(source_config)
        self.size_kb = self._get_size(name) if self.available else 0

    def _get_description(self, config: dict) -> str:
        """Generate a description for the firmware."""
        if self.type == "github":
            return f"GitHub: {config.get('repo', 'unknown')}"
        elif self.type == "local":
            return f"Local: {config.get('path', 'unknown')}"
        else:
            return f"Type: {self.type}"

    def _check_availability(self, name: str) -> bool:
        """Check if firmware binary is available."""
        firmware_path = Path("tmpfw") / f"{name}.bin"
        return firmware_path.exists()

    def _get_version(self, config: dict) -> str:
        """Get firmware version."""
        if self.type == "github":
            return config.get("current_version", "latest")
        else:
            return "local"

    def _get_size(self, name: str) -> float:
        """Get firmware size in KB."""
        firmware_path = Path("tmpfw") / f"{name}.bin"
        if firmware_path.exists():
            return firmware_path.stat().st_size / 1024
        return 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "platform": self.platform,
            "description": self.description,
            "available": self.available,
            "version": self.version,
            "size_kb": round(self.size_kb, 1),
        }


def get_firmware_list() -> list[FirmwareInfo]:
    """Get list of available firmware from sources.yaml."""
    try:
        config = load_sources_config("sources.yaml")
        firmware_list = []

        for source in config.get("sources", []):
            name = source.get("name")
            if name:
                firmware_info = FirmwareInfo(name, source)
                firmware_list.append(firmware_info)

        return firmware_list
    except Exception as e:
        print(f"Error loading firmware list: {e}")
        return []


# API Routes - diese müssen vor dem Static Mount stehen
@app.get("/api/firmware", response_model=list[dict])
async def api_get_firmware():
    """Get list of available firmware as JSON."""
    firmware_list = get_firmware_list()
    return [fw.to_dict() for fw in firmware_list]


@app.get("/api/firmware/{name}")
async def api_get_firmware_info(name: str):
    """Get detailed information about specific firmware."""
    config = load_sources_config("sources.yaml")

    for source in config.get("sources", []):
        if source.get("name") == name:
            firmware_info = FirmwareInfo(name, source)
            return firmware_info.to_dict()

    raise HTTPException(status_code=404, detail=f"Firmware '{name}' not found")


# Mount static files - das muss nach den API-Routen stehen
site_dir = Path("scripts/site")
if site_dir.exists():
    app.mount("/", StaticFiles(directory=str(site_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting ESP32 Firmware Flash Web Tool...")
    print("📍 Open your browser to: http://localhost:8000")
    print("🔧 API documentation: http://localhost:8000/docs")
    print("💡 Press Ctrl+C to stop")

    uvicorn.run(
        "webflasher:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
