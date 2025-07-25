"""
Factory image creation and flashing utilities.
"""

import subprocess
from pathlib import Path


def create_factory_image(name: str, project_dir: Path) -> Path | None:
    """Create a factory image using PlatformIO."""
    print("🔧 Building factory image...")

    # First build the project to ensure all binaries exist
    try:
        subprocess.run(
            ["pio", "run"],
            cwd=str(project_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return None

    # Find the build directory and binaries
    build_dir = project_dir / ".pio" / "build"
    if not build_dir.exists():
        print("❌ Build directory not found")
        return None

    # Look for environment directories (usually esp32dev, esp32, etc.)
    env_dirs = [d for d in build_dir.iterdir() if d.is_dir()]
    if not env_dirs:
        print("❌ No build environment found")
        return None

    env_dir = env_dirs[0]  # Take the first environment
    print(f"📂 Using build environment: {env_dir.name}")

    # Check for required files
    bootloader_bin = env_dir / "bootloader.bin"
    partitions_bin = env_dir / "partitions.bin"
    firmware_bin = env_dir / "firmware.bin"

    if not all(f.exists() for f in [bootloader_bin, partitions_bin, firmware_bin]):
        print("❌ Required binary files not found")
        return None

    # Create factory image using esptool merge-bin
    factory_image = project_dir / f"{name}-factory.bin"

    try:
        boot_app0_path = env_dir / "boot_app0.bin"

        # Use relative paths within project directory for cleaner commands
        rel_bootloader = Path(".pio/build") / env_dir.name / "bootloader.bin"
        rel_partitions = Path(".pio/build") / env_dir.name / "partitions.bin"
        rel_firmware = Path(".pio/build") / env_dir.name / "firmware.bin"
        rel_factory = Path(f"{name}-factory.bin")

        cmd = [
            "python",
            "-m",
            "esptool",
            "--chip",
            "esp32",
            "merge-bin",
            "-o",
            str(rel_factory),
            "--flash-mode",
            "dio",
            "--flash-freq",
            "40m",
            "--flash-size",
            "4MB",
            "0x1000",
            str(rel_bootloader),
            "0x8000",
            str(rel_partitions),
        ]

        # Add boot_app0.bin only if it exists
        if boot_app0_path.exists():
            rel_boot_app0 = Path(".pio/build") / env_dir.name / "boot_app0.bin"
            cmd.extend(["0xe000", str(rel_boot_app0)])

        # Add firmware at the end
        cmd.extend(["0x10000", str(rel_firmware)])

        print(f"🔧 Command: {' '.join(cmd)}")
        print(f"📂 Working directory: {project_dir}")

        # Run esptool from the project directory to fix path issues
        subprocess.run(
            cmd, cwd=str(project_dir), check=True, capture_output=True, text=True
        )

        if factory_image.exists():
            size_kb = factory_image.stat().st_size / 1024
            print(f"✅ Factory image created: {size_kb:.1f} KB")
            return factory_image
        else:
            print("❌ Factory image creation failed - file not created")
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ Factory image creation failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def flash_factory_image(factory_image: Path, port: str | None, baudrate: int) -> bool:
    """Flash the factory image using esptool."""
    print("⬇️  Flashing factory image...")

    # Build esptool command
    cmd = ["python", "-m", "esptool", "--baud", str(baudrate)]

    # Add port if specified
    if port:
        cmd.extend(["--port", port])

    # Add flash command and parameters
    cmd.extend(
        [
            "write-flash",
            "0x0",  # Flash address for factory firmware
            str(factory_image),
        ]
    )

    print(f"🔧 Command: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Factory image flashed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Flashing failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error during flashing: {e}")
        return False
