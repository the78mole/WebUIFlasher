"""
Main flash functionality.
"""

import subprocess
from pathlib import Path

from .config import find_firmware_config, get_firmware_path, load_sources_config
from .factory import create_factory_image, flash_factory_image
from .platformio import flash_via_platformio


def flash_local_project(
    name: str, port: str | None, baudrate: int, firmware_config: dict
) -> bool:
    """Flash firmware using PlatformIO.

    Prefer downloaded factory image over rebuild.
    """
    project_path = firmware_config.get("path", "")
    if not project_path:
        print("❌ No project path specified in configuration")
        return False

    project_dir = Path(project_path)
    if not project_dir.exists():
        print(f"❌ Project directory not found: {project_dir}")
        return False

    print("🚀 PlatformIO Local Project")
    print("━" * 50)
    print(f"📦 Project: {name}")
    print(f"📁 Path: {project_dir}")
    if port:
        print(f"🔗 Port: {port}")
    else:
        print("🔗 Port: Auto-detect")
    print(f"⚡ Baudrate: {baudrate}")
    print()

    # First check if we have a downloaded factory image from update_firmwares.py
    config = load_sources_config("sources.yaml")  # Get config to find fetchdir
    fetchdir = config.get("fetchdir", "./tmpfw")
    downloaded_firmware = Path(fetchdir) / f"{name}.bin"

    if downloaded_firmware.exists():
        print(f"📦 Using downloaded factory image: {downloaded_firmware}")
        size_kb = downloaded_firmware.stat().st_size / 1024
        print(f"📊 Size: {size_kb:.1f} KB")
        return flash_factory_image(downloaded_firmware, port, baudrate)

    # If no downloaded image, create one from source
    print("📥 No downloaded factory image found, creating from source...")
    factory_image_path = create_factory_image(name, project_dir)
    if factory_image_path and factory_image_path.exists():
        print(f"📦 Created factory image: {factory_image_path}")
        return flash_factory_image(factory_image_path, port, baudrate)
    else:
        print("⚠️  Factory image creation failed, using direct PlatformIO upload")
        return flash_via_platformio(name, port, project_dir)


def flash_binary_file(
    name: str, port: str | None, baudrate: int, config: dict, firmware_config: dict
) -> bool:
    """Flash firmware from binary file using esptool."""
    # Get firmware file path
    firmware_path = get_firmware_path(config, name)
    if not firmware_path.exists():
        print(f"❌ Firmware file not found: {firmware_path}")
        print("💡 Use 'uv run scripts/update_firmwares.py' to download firmware")
        return False

    print("🚀 ESP32 Firmware Flasher")
    print("━" * 50)
    print(f"📦 Firmware: {name}")
    print(f"📁 File: {firmware_path}")
    print("🔌 Chip: Auto-detect")
    if port:
        print(f"🔗 Port: {port}")
    else:
        print("🔗 Port: Auto-detect")
    print(f"⚡ Baudrate: {baudrate}")
    print()

    # Build esptool command
    cmd = ["python", "-m", "esptool", "--baud", str(baudrate)]

    # Add port if specified
    if port:
        cmd.extend(["--port", port])

    # Add flash command and parameters
    cmd.extend(
        [
            "write-flash",  # Updated to use hyphen instead of underscore
            "0x0",  # Flash address for factory firmware
            str(firmware_path),
        ]
    )

    print(f"🔧 Command: {' '.join(cmd)}")
    print()

    try:
        # Run esptool
        subprocess.run(cmd, check=True)
        print("\n✅ Firmware flashed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Flashing failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ esptool not found. Install it with:")
        print("   pip install esptool")
        return False
    except Exception as e:
        print(f"❌ Error during flashing: {e}")
        return False


def flash_firmware(name: str, port: str | None, baudrate: int, config: dict) -> bool:
    """Flash firmware to ESP32 device using esptool or PlatformIO."""

    # Find firmware configuration
    firmware_config = find_firmware_config(config, name)
    if not firmware_config:
        print(f"❌ Firmware '{name}' not found in configuration")
        print("💡 Use --list to see available firmware")
        return False

    source_type = firmware_config.get("type", "unknown")

    # Handle local PlatformIO projects differently
    if source_type == "local":
        return flash_local_project(name, port, baudrate, firmware_config)
    else:
        return flash_binary_file(name, port, baudrate, config, firmware_config)
