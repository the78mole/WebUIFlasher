"""
PlatformIO utilities for firmware flashing.
"""

import subprocess
from pathlib import Path


def flash_via_platformio(name: str, port: str | None, project_dir: Path) -> bool:
    """Fallback: Flash using direct PlatformIO upload."""
    print("🔄 Using direct PlatformIO upload...")

    # Build PlatformIO command
    cmd = ["pio", "run", "--target", "upload"]

    # Add port if specified
    if port:
        cmd.extend(["--upload-port", port])

    print(f"🔧 Command: {' '.join(cmd)}")
    print(f"📂 Working directory: {project_dir}")
    print()

    try:
        subprocess.run(
            cmd,
            cwd=str(project_dir),
            check=True,
            capture_output=False,  # Show live output
        )
        print("\n✅ Upload successful!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Upload failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ PlatformIO not found. Install it with:")
        print("   pip install platformio")
        return False
    except Exception as e:
        print(f"❌ Error during upload: {e}")
        return False
