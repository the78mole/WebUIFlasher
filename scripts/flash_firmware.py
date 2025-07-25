#!/usr/bin/env python3
"""
Firmware Flash Tool

This script flashes firmware to ESP32 devices using esptool.
It reads firmware information from sources.yaml and automatically
flashes the corresponding .bin file.

Usage:
    flash_firmware.py [<name>] [--port=<port>] [--sources=<file>]
                      [--baudrate=<rate>] [--loop]
    flash_firmware.py --list [--sources=<file>]
    flash_firmware.py --help

Arguments:
    <name>              Name of the firmware to flash (from sources.yaml)

Options:
    -p --port=<port>       Serial port (optional, esptool will auto-detect)
    -s --sources=<file>    Path to sources.yaml file [default: sources.yaml]
    -b --baudrate=<rate>   Baud rate for flashing [default: 921600]
    -l --loop              Continue flashing after each device (for batch production)
    --list                 List available firmware names
    -h --help              Show this help message

Examples:
    uv run scripts/flash_firmware.py
    uv run scripts/flash_firmware.py dewenni-km271
    uv run scripts/flash_firmware.py km271-esphome -p /dev/ttyUSB0
    uv run scripts/flash_firmware.py blinkenlights --loop
    uv run scripts/flash_firmware.py --list
"""

import sys

from docopt import docopt
from flash_utils import flash_firmware, load_sources_config
from flash_utils.config import list_available_firmware


def wait_for_user_input() -> bool:
    """Wait for user input and return True to continue, False to stop."""
    print("\n" + "━" * 60)
    print("🔄 Batch Production Mode")
    print("━" * 60)
    print("📱 Connect next device and press any key to continue...")
    print("🛑 Press 'ESC' or 'n' to stop")
    print("━" * 60)

    try:
        # Try to use termios for better key detection (Unix/Linux)
        import termios
        import tty

        # Check if stdin is a real terminal (not a pipe or redirect)
        if not sys.stdin.isatty():
            raise ImportError("Not a TTY")

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # Try modern method first, then fall back to older method
            if hasattr(tty, "setcbreak"):
                tty.setcbreak(sys.stdin.fileno())
            else:
                tty.cbreak(sys.stdin.fileno())
            key = sys.stdin.read(1)

            # Check for ESC key (ASCII 27) or 'n'/'N' to stop
            if ord(key) == 27 or key.lower() == "n":
                print("🛑 Stopping batch production...")
                return False
            else:
                print(f"🚀 Continuing with next device... (pressed: {repr(key)})")
                return True

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    except (ImportError, OSError, termios.error):
        # Fallback for systems without termios or when not in a TTY
        try:
            user_input = (
                input("Press ENTER to continue or 'n' to stop: ").strip().lower()
            )
            if user_input == "n":
                print("🛑 Stopping batch production...")
                return False
            else:
                print("🚀 Continuing with next device...")
                return True
        except (EOFError, KeyboardInterrupt):
            print("\n🛑 Stopping batch production...")
            return False


def main():
    """Main entry point."""
    args = docopt(__doc__)

    sources_file = args["--sources"]

    # Load configuration
    config = load_sources_config(sources_file)

    # List available firmware (default if no name provided or explicit --list)
    if args["--list"] or not args["<name>"]:
        list_available_firmware(config)
        return

    # Flash firmware
    name = args["<name>"]
    port = args["--port"]
    baudrate = int(args["--baudrate"])
    loop_mode = args["--loop"]

    # Handle loop mode for batch production
    if loop_mode:
        print("🏭 Batch Production Mode Enabled")
        print("━" * 60)
        print(f"📦 Firmware: {name}")
        print(f"⚡ Baudrate: {baudrate}")
        if port:
            print(f"🔗 Port: {port}")
        else:
            print("🔗 Port: Auto-detect")
        print("━" * 60)

        device_count = 0

        while True:
            device_count += 1
            print(f"\n🔢 Device #{device_count}")

            # Flash the firmware
            success = flash_firmware(name, port, baudrate, config)

            if success:
                print(f"✅ Device #{device_count} flashed successfully!")
            else:
                print(f"❌ Device #{device_count} failed to flash!")
                print("💡 Check connection and try again")

            # Wait for user input to continue or stop
            if not wait_for_user_input():
                break

        print(f"\n📊 Batch production completed: {device_count} device(s) processed")

    else:
        # Single device mode
        success = flash_firmware(name, port, baudrate, config)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
