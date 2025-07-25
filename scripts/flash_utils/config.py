"""
Configuration management for firmware flashing.
"""

import sys
from pathlib import Path

import yaml


def load_sources_config(sources_file: str) -> dict:
    """Load and parse the sources configuration file."""
    try:
        with open(sources_file, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Sources file not found: {sources_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing sources file: {e}")
        sys.exit(1)


def find_firmware_config(config: dict, name: str) -> dict | None:
    """Find firmware configuration by name."""
    for source in config.get("sources", []):
        if source.get("name") == name:
            return source
    return None


def get_firmware_path(config: dict, name: str) -> Path:
    """Get the path to the firmware binary file."""
    fetchdir = config.get("fetchdir", "./tmpfw")
    return Path(fetchdir) / f"{name}.bin"


def list_available_firmware(config: dict) -> None:
    """List all available firmware names from the configuration."""
    print("📋 Available firmware:")
    print("━" * 50)

    fetchdir = config.get("fetchdir", "./tmpfw")

    for source in config.get("sources", []):
        name = source.get("name", "unknown")
        source_type = source.get("type", "unknown")
        platform = source.get("platform", "unknown")

        # Check if firmware file exists
        firmware_path = Path(fetchdir) / f"{name}.bin"
        status = "✅" if firmware_path.exists() else "❌"

        print(f"{status} {name} ({source_type}, {platform})")
        if source_type == "github":
            repo = source.get("repo", "unknown")
            version = source.get("current_version", "latest")
            print(f"    📦 {repo} - {version}")
        elif source_type == "local":
            path = source.get("path", "unknown")
            print(f"    📁 {path}")

    print("\n💡 Use 'uv run scripts/update_firmwares.py' to download missing firmware")
