#!/usr/bin/env python3
"""
Web-based Firmware Flasher for ESP32

A FastAPI-based web interface for flashing ESP32 firmware.
Provides a user-friendly web interface for the flash utilities.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import serial
import serial.tools.list_ports
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from flash_utils import flash_firmware, load_sources_config
from pydantic import BaseModel

# Global monitor tasks tracking
monitor_tasks = {}


async def cleanup_finished_tasks():
    """Clean up finished monitor tasks from the global dict."""
    to_remove = []
    for port, task in monitor_tasks.items():
        if task.done():
            to_remove.append(port)

    for port in to_remove:
        del monitor_tasks[port]


app = FastAPI(
    title="ESP32 Firmware Flash Tool",
    description="Web interface for flashing ESP32 firmware",
    version="1.0.0",
)


def clean_ansi_sequences(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    # Pattern to match ANSI escape sequences
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[mKABC]")
    return ansi_pattern.sub("", text)


def determine_message_type(line: str) -> str:
    """Determine the appropriate message type based on line content."""
    line_lower = line.lower()

    if "writing at" in line_lower or "%" in line:
        return "progress"
    elif "error" in line_lower or "failed" in line_lower:
        return "error"
    elif "connecting" in line_lower or "chip is" in line_lower:
        return "info"
    elif "compressed" in line_lower or "wrote" in line_lower:
        return "success"
    else:
        return "output"


class FlashRequest(BaseModel):
    """Request model for firmware flashing."""

    firmware: str
    port: str = "auto"


class FlashResponse(BaseModel):
    """Response model for firmware flashing."""

    success: bool
    message: str
    firmware: str
    port: str | None = None


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


def get_serial_ports() -> list[dict]:
    """Get list of available serial ports."""
    ports = []

    # Add auto option
    ports.append(
        {"device": "auto", "description": "Auto-detect", "hwid": "Automatic detection"}
    )

    # Get system serial ports
    try:
        for port in serial.tools.list_ports.comports():
            # Filter out ports without proper hardware ID (virtual/internal ports)
            if port.hwid and port.hwid != "n/a" and port.hwid.strip():
                ports.append(
                    {
                        "device": port.device,
                        "description": port.description or "Unknown device",
                        "hwid": port.hwid,
                    }
                )
    except Exception as e:
        print(f"Error listing serial ports: {e}")

    return ports


def get_firmware_list() -> list[dict]:
    """Get list of available firmware."""
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
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker containers."""
    return {"status": "healthy", "service": "WebUIFlasher"}


@app.get("/api/firmware", response_model=list[dict])
async def api_get_firmware():
    """Get list of available firmware as JSON."""
    firmware_list = get_firmware_list()
    return [fw.to_dict() for fw in firmware_list]


@app.get("/api/serial-ports", response_model=list[dict])
async def api_get_serial_ports():
    """Get list of available serial ports as JSON."""
    return get_serial_ports()


@app.post("/api/update-firmware")
async def api_update_firmware():
    """Update firmware by running update_firmwares.py script."""
    try:
        # Run the update script using uv from main directory
        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            "scripts/update_firmwares.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=".",  # Current working directory
        )

        stdout, _ = await process.communicate()

        if process.returncode == 0:
            return {
                "success": True,
                "message": "Firmware update completed successfully",
                "output": stdout.decode("utf-8") if stdout else "",
            }
        else:
            return {
                "success": False,
                "message": f"Firmware update failed with code {process.returncode}",
                "output": stdout.decode("utf-8") if stdout else "",
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to run update script: {str(e)}",
            "output": "",
        }


@app.get("/api/firmware/{name}")
async def api_get_firmware_info(name: str):
    """Get detailed information about specific firmware."""
    config = load_sources_config("sources.yaml")

    for source in config.get("sources", []):
        if source.get("name") == name:
            firmware_info = FirmwareInfo(name, source)
            return firmware_info.to_dict()

    raise HTTPException(status_code=404, detail=f"Firmware '{name}' not found")


@app.post("/api/flash", response_model=FlashResponse)
async def api_flash_firmware(request: FlashRequest):
    """Flash firmware to ESP32 device."""
    try:
        # Load sources config
        config = load_sources_config("sources.yaml")

        # Check if firmware exists in config
        firmware_found = False
        for source in config.get("sources", []):
            if source.get("name") == request.firmware:
                firmware_found = True
                break

        if not firmware_found:
            raise HTTPException(
                status_code=404,
                detail=f"Firmware '{request.firmware}' not found in configuration",
            )

        # Check if firmware binary exists
        firmware_path = Path("tmpfw") / f"{request.firmware}.bin"
        if not firmware_path.exists():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Firmware '{request.firmware}' binary not found. "
                    "Run update_firmwares.py first."
                ),
            )

        # Perform the flash operation
        success = flash_firmware(
            name=request.firmware,
            port=request.port if request.port != "auto" else None,
            baudrate=921600,  # Standard ESP32 baudrate
            config=config,
        )

        if success:
            return FlashResponse(
                success=True,
                message=f"Successfully flashed {request.firmware}",
                firmware=request.firmware,
                port=request.port,
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Flash operation failed. Check ESP32 connection and try again.",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Flash operation failed: {str(e)}"
        ) from e


@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """WebSocket endpoint for terminal communication."""
    await websocket.accept()

    try:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "info",
                    "message": "🚀 WebSocket Terminal connected",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        while True:
            # Clean up finished tasks
            await cleanup_finished_tasks()

            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            command_type = message.get("type")

            if command_type == "flash":
                await handle_flash_command(websocket, message)
            elif command_type == "esptool":
                await handle_esptool_command(websocket, message)
            elif command_type == "update_firmware":
                await handle_update_firmware_command(websocket, message)
            elif command_type == "monitor":
                await handle_monitor_command(websocket, message)
            elif command_type == "stop_monitor":
                await handle_stop_monitor_command(websocket, message)
            elif command_type == "ping":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "pong",
                            "message": "Terminal connection alive",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Unknown command type: {command_type}",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )

    except WebSocketDisconnect:
        print("WebSocket disconnected - cleaning up monitor tasks")
        # Cancel all monitor tasks when WebSocket disconnects
        for _port, task in list(monitor_tasks.items()):
            task.cancel()
        monitor_tasks.clear()
    except Exception as e:
        print(f"Terminal error: {str(e)}")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Terminal error: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )


async def handle_flash_command(websocket: WebSocket, message: dict):
    """Handle firmware flashing via WebSocket with live output."""
    firmware_name = message.get("firmware")
    port = message.get("port", "auto")

    await websocket.send_text(
        json.dumps(
            {
                "type": "command",
                "message": f"flash firmware: {firmware_name}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )

    try:
        # Load config and validate firmware
        config = load_sources_config("sources.yaml")

        firmware_found = False
        for source in config.get("sources", []):
            if source.get("name") == firmware_name:
                firmware_found = True
                break

        if not firmware_found:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": (
                            f"Firmware '{firmware_name}' not found in " "configuration"
                        ),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
            return

        # Check if binary exists
        firmware_path = Path("tmpfw") / f"{firmware_name}.bin"
        if not firmware_path.exists():
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Firmware binary not found: {firmware_path}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
            return

        # Start flashing with live output
        await flash_with_live_output(websocket, firmware_name, port, config)

    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Flash command failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )


async def handle_esptool_command(websocket: WebSocket, message: dict):
    """Handle esptool commands with live output."""
    command = message.get("command", "")

    try:
        # Build esptool command
        cmd = ["python", "-m", "esptool"] + command.split()

        # Log the command that will be executed
        cmd_str = " ".join(cmd)
        await websocket.send_text(
            json.dumps(
                {
                    "type": "command",
                    "message": f"Executing: {cmd_str}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        # Execute with live output and improved parsing
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )

        # Stream output and improved parsing
        last_progress_line = None
        buffer = ""

        while True:
            chunk = await process.stdout.read(128)  # Smaller chunks
            if not chunk:
                break

            try:
                decoded_chunk = chunk.decode("utf-8")
                buffer += decoded_chunk
            except UnicodeDecodeError:
                continue

            # Send partial updates immediately if buffer gets substantial
            if len(buffer) > 10 and "\n" not in buffer and "\r" not in buffer:
                buffer_clean = clean_ansi_sequences(buffer)
                if buffer_clean.strip() and buffer_clean != last_progress_line:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "partial",
                                "message": buffer_clean,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )

            # Process complete lines and carriage returns
            while "\n" in buffer or "\r" in buffer:
                if "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line_complete = True
                elif "\r" in buffer:
                    line, buffer = buffer.split("\r", 1)
                    line_complete = False

                line_clean = clean_ansi_sequences(line)

                if line_complete:
                    if line_clean:
                        msg_type = determine_message_type(line_clean)

                        # Progress messages should always overwrite, even if complete
                        if msg_type == "progress":
                            # Force progress type to ensure overwriting
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "progress",
                                        "message": line_clean,
                                        "timestamp": datetime.now().isoformat(),
                                    }
                                )
                            )
                        else:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": msg_type,
                                        "message": line_clean,
                                        "timestamp": datetime.now().isoformat(),
                                    }
                                )
                            )
                else:
                    # Carriage return - likely progress update
                    if line_clean and line_clean != last_progress_line:
                        last_progress_line = line_clean
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "progress",
                                    "message": line_clean,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

        # Wait for process to complete
        await process.wait()

        if process.returncode == 0:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "success",
                        "message": "✅ Command completed successfully",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"❌ Command failed with code {process.returncode}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"esptool command failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )


async def handle_update_firmware_command(websocket: WebSocket, message: dict):
    """Handle firmware update command with live output."""

    # Get the working directory for debugging
    current_dir = Path(".").absolute()

    await websocket.send_text(
        json.dumps(
            {
                "type": "info",
                "message": f"Current directory: {current_dir}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )

    await websocket.send_text(
        json.dumps(
            {
                "type": "command",
                "message": "Executing: uv run scripts/update_firmwares.py",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )

    try:
        # Execute update_firmwares.py from main directory
        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            "scripts/update_firmwares.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=".",  # Current working directory
        )

        # Stream output
        buffer = ""
        while True:
            chunk = await process.stdout.read(128)
            if not chunk:
                break

            try:
                decoded_chunk = chunk.decode("utf-8")
                buffer += decoded_chunk
            except UnicodeDecodeError:
                continue

            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line_clean = clean_ansi_sequences(line.strip())

                if line_clean:
                    msg_type = determine_message_type(line_clean)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": msg_type,
                                "message": line_clean,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )

        # Send remaining buffer content
        if buffer.strip():
            buffer_clean = clean_ansi_sequences(buffer.strip())
            if buffer_clean:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "output",
                            "message": buffer_clean,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )

        # Wait for process to complete
        await process.wait()

        if process.returncode == 0:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "success",
                        "message": "✅ Firmware update completed successfully",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": (
                            f"❌ Firmware update failed with code "
                            f"{process.returncode}"
                        ),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Update command failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )


async def handle_monitor_command(websocket: WebSocket, message: dict):
    """Handle serial monitor start command."""
    port = message.get("port", "auto")
    baudrate = int(message.get("baudrate", 115200))

    if port == "auto":
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": "❌ Please select a specific serial port for monitoring",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
        return

    # Check if already monitoring this port
    if port in monitor_tasks:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"❌ Already monitoring port {port}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
        return

    await websocket.send_text(
        json.dumps(
            {
                "type": "command",
                "message": f"🔍 Starting serial monitor on {port} at {baudrate} baud",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )

    # Start monitoring task
    task = asyncio.create_task(serial_monitor_task(websocket, port, baudrate))
    monitor_tasks[port] = task

    # Don't await the task here - let it run in background
    # The task will be cancelled by handle_stop_monitor_command

    # Send immediate confirmation that monitoring started
    await websocket.send_text(
        json.dumps(
            {
                "type": "info",
                "message": f"🔍 Serial monitor started for {port}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )


async def handle_stop_monitor_command(websocket: WebSocket, message: dict):
    """Handle serial monitor stop command."""
    port = message.get("port", "auto")

    if port == "auto" or port not in monitor_tasks:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"❌ No monitor running for port {port}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
        return

    # Cancel the monitoring task
    task = monitor_tasks[port]
    task.cancel()

    # Wait a bit for the task to actually cancel
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except TimeoutError:
        pass  # Task didn't cancel within timeout
    except asyncio.CancelledError:
        pass  # Task cancelled successfully
    except Exception as e:
        print(f"Exception while cancelling monitor task: {e}")

    # Remove from tasks dict
    if port in monitor_tasks:
        del monitor_tasks[port]

    await websocket.send_text(
        json.dumps(
            {
                "type": "info",
                "message": f"⏹️ Serial monitor stopped for {port}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )


async def serial_monitor_task(websocket: WebSocket, port: str, baudrate: int):
    """Async task for serial monitoring."""

    try:
        # Open serial connection
        ser = serial.Serial(port, baudrate, timeout=0.1)

        await websocket.send_text(
            json.dumps(
                {
                    "type": "success",
                    "message": f"✅ Connected to {port} at {baudrate} baud",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

        buffer = ""

        while True:
            # Check if task should be cancelled (this will raise CancelledError)
            if asyncio.current_task().cancelled():
                break

            # Read from serial port
            try:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    if data:
                        try:
                            decoded = data.decode("utf-8", errors="replace")
                            buffer += decoded

                            # Process complete lines
                            while "\n" in buffer or "\r" in buffer:
                                if "\n" in buffer:
                                    line, buffer = buffer.split("\n", 1)
                                elif "\r" in buffer:
                                    line, buffer = buffer.split("\r", 1)

                                if line.strip():
                                    try:
                                        await websocket.send_text(
                                            json.dumps(
                                                {
                                                    "type": "monitor",
                                                    "message": line.strip(),
                                                    "timestamp": (
                                                        datetime.now().isoformat()
                                                    ),
                                                }
                                            )
                                        )
                                    except Exception:
                                        raise  # Re-raise to break the loop
                        except UnicodeDecodeError:
                            # Handle binary data that can't be decoded
                            hex_data = " ".join(f"{b:02x}" for b in data)

                            try:
                                await websocket.send_text(
                                    json.dumps(
                                        {
                                            "type": "monitor",
                                            "message": f"[HEX] {hex_data}",
                                            "timestamp": datetime.now().isoformat(),
                                        }
                                    )
                                )
                            except Exception:
                                raise  # Re-raise to break the loop

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.01)

            except serial.SerialException as e:
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"❌ Serial error: {str(e)}",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )
                except Exception:
                    print("Could not send error message via WebSocket")
                break
            except Exception as e:
                print(f"Exception in monitor loop: {e}")
                break

    except serial.SerialException as e:
        print(f"Failed to open serial port {port}: {e}")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"❌ Could not open serial port {port}: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
    except Exception as e:
        print(f"Unexpected error in serial_monitor_task: {e}")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"❌ Monitor error: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )
    finally:
        # Clean up serial connection

        try:
            if "ser" in locals():
                ser.close()

        except Exception:
            pass

        # Remove from monitor_tasks if still there
        if port in monitor_tasks:
            del monitor_tasks[port]


async def flash_with_live_output(
    websocket: WebSocket, firmware_name: str, port: str, config: dict
):
    """Flash firmware with live output streaming."""

    await websocket.send_text(
        json.dumps(
            {
                "type": "info",
                "message": f"🚀 Starting flash for {firmware_name}...",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )

    # For now, simulate the flash process by calling the existing function
    # but we'll capture its output
    firmware_path = Path("tmpfw") / f"{firmware_name}.bin"

    # Build flash command manually to get live output
    cmd = ["python", "-m", "esptool"]

    # Add port parameter first if not auto
    if port != "auto":
        cmd.extend(["--port", port])

    # Add remaining parameters
    cmd.extend(
        [
            "--baud",
            "921600",
            "write-flash",
            "0x0",
            str(firmware_path),
        ]
    )

    # Log the command that will be executed
    cmd_str = " ".join(cmd)
    await websocket.send_text(
        json.dumps(
            {
                "type": "command",
                "message": f"Executing: {cmd_str}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    )

    try:
        # Execute flash command with live output
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )

        # Stream output with chunked reading for real-time updates
        last_progress_line = None
        buffer = ""

        while True:
            # Read in smaller chunks for more responsive updates
            chunk = await process.stdout.read(128)  # Smaller chunks
            if not chunk:
                break

            # Decode chunk and add to buffer
            try:
                decoded_chunk = chunk.decode("utf-8")
                buffer += decoded_chunk
            except UnicodeDecodeError:
                # Handle partial UTF-8 sequences
                continue

            # Send partial updates immediately if buffer gets substantial
            if len(buffer) > 10 and "\n" not in buffer and "\r" not in buffer:
                buffer_clean = clean_ansi_sequences(buffer)
                if buffer_clean.strip() and buffer_clean != last_progress_line:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "partial",
                                "message": buffer_clean,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )

            # Process complete lines and carriage returns
            while "\n" in buffer or "\r" in buffer:
                if "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line_complete = True
                elif "\r" in buffer:
                    line, buffer = buffer.split("\r", 1)
                    line_complete = False

                # Clean ANSI escape sequences
                line_clean = clean_ansi_sequences(line)

                if line_complete:
                    # Complete line - check if it's progress to override previous
                    if line_clean:
                        msg_type = determine_message_type(line_clean)

                        # Progress messages should always overwrite, even if complete
                        if msg_type == "progress":
                            # Force progress type to ensure overwriting
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "progress",
                                        "message": line_clean,
                                        "timestamp": datetime.now().isoformat(),
                                    }
                                )
                            )
                        else:
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": msg_type,
                                        "message": line_clean,
                                        "timestamp": datetime.now().isoformat(),
                                    }
                                )
                            )
                else:
                    # Carriage return - likely progress update
                    if line_clean and line_clean != last_progress_line:
                        last_progress_line = line_clean
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "progress",
                                    "message": line_clean,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

        # Send remaining buffer content at the end if any
        if buffer.strip():
            buffer_clean = clean_ansi_sequences(buffer)
            if buffer_clean.strip():
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "output",
                            "message": buffer_clean,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                )

        # Wait for process to complete
        await process.wait()

        if process.returncode == 0:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "success",
                        "message": f"✅ {firmware_name} flashed successfully!",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"❌ Flash failed with code {process.returncode}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Flash process failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )


# Mount static files - das muss nach den API-Routen stehen
site_dir = Path("scripts/site")
if site_dir.exists():
    app.mount("/", StaticFiles(directory=str(site_dir), html=True), name="static")
else:
    # Fallback: check if we're running from scripts directory
    site_dir_fallback = Path("site")
    if site_dir_fallback.exists():
        app.mount(
            "/", StaticFiles(directory=str(site_dir_fallback), html=True), name="static"
        )
    else:
        print(
            f"⚠️ Warning: Static files directory not found. "
            f"Checked: {site_dir} and {site_dir_fallback}"
        )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting ESP32 Firmware Flash Web Tool...")
    print("📍 Open your browser to: http://localhost:8000")
    print("🔧 API documentation: http://localhost:8000/docs")
    print("💡 Press Ctrl+C to stop")

    uvicorn.run(
        "webflasher:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
