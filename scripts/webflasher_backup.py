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
from fastapi.templating import Jinja2Templates

from flash_utils import load_sources_config

app = FastAPI(
    title="ESP32 Firmware Flash Tool",
    description="Web interface for flashing ESP32 firmware",
    version="1.0.0"
)

# Mount static files from site directory
site_dir = Path("scripts/site")
if site_dir.exists():
    app.mount("/", StaticFiles(directory=str(site_dir), html=True), name="static")

# Try to setup templates (for future use)
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)

try:
    templates = Jinja2Templates(directory="templates")
except Exception:
    # Fallback if templates don't exist
    templates = None


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
            "size_kb": round(self.size_kb, 1)
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


# API Routes
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


# Web Routes
@app.get("/", response_class=HTMLResponse)
async def home():
    """Main web interface - serve static HTML file."""
    html_file = Path("scripts/site/index.html")
    
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    else:
        # Fallback to generated HTML if static file doesn't exist
        firmware_list = get_firmware_list()
        html_content = generate_simple_html(firmware_list)
        return HTMLResponse(content=html_content)


def generate_simple_html(firmware_list: list[FirmwareInfo]) -> str:
    """Generate simple HTML without template engine."""
    
    firmware_rows = ""
    for fw in firmware_list:
        status_icon = "✅" if fw.available else "❌"
        status_class = "available" if fw.available else "unavailable"
        flash_button = ""
        
        if fw.available:
            flash_button = f'''
                <button class="flash-btn" onclick="flashFirmware('{fw.name}')" 
                        id="flash-{fw.name}">
                    🚀 Flash
                </button>
            '''
        else:
            flash_button = '''
                <button class="flash-btn disabled" disabled>
                    ❌ Not Available
                </button>
            '''
        
        firmware_rows += f'''
            <tr class="{status_class}">
                <td>{status_icon} <strong>{fw.name}</strong></td>
                <td>{fw.type}</td>
                <td>{fw.platform}</td>
                <td>{fw.version}</td>
                <td>{fw.size_kb} KB</td>
                <td>{fw.description}</td>
                <td>{flash_button}</td>
            </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ESP32 Firmware Flash Tool</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 30px;
            }}
            
            h1 {{
                color: #333;
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 3px solid #007acc;
                padding-bottom: 15px;
            }}
            
            .header-info {{
                background: #e8f4fd;
                padding: 15px;
                border-radius: 6px;
                margin-bottom: 25px;
                border-left: 4px solid #007acc;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            
            th {{
                background-color: #007acc;
                color: white;
                font-weight: 600;
            }}
            
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            
            tr:hover {{
                background-color: #f0f8ff;
            }}
            
            .available {{
                color: #2d7d2d;
            }}
            
            .unavailable {{
                color: #cc4125;
            }}
            
            .flash-btn {{
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 500;
                transition: background-color 0.2s;
            }}
            
            .flash-btn:hover:not(.disabled) {{
                background: #218838;
            }}
            
            .flash-btn.disabled {{
                background: #6c757d;
                cursor: not-allowed;
            }}
            
            .flash-btn:active {{
                transform: translateY(1px);
            }}
            
            .status-info {{
                margin-top: 20px;
                padding: 15px;
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
            }}
            
            .refresh-btn {{
                background: #007acc;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            
            .refresh-btn:hover {{
                background: #0056b3;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 ESP32 Firmware Flash Tool</h1>
            
            <div class="header-info">
                <p><strong>📋 Available Firmware:</strong> This tool allows you to flash ESP32 firmware directly from your browser.</p>
                <p><strong>💡 Note:</strong> Make sure your ESP32 device is connected via USB before flashing.</p>
            </div>
            
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh List</button>
            
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Platform</th>
                        <th>Version</th>
                        <th>Size</th>
                        <th>Description</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {firmware_rows}
                </tbody>
            </table>
            
            <div class="status-info">
                <p><strong>Status Legend:</strong></p>
                <p>✅ <strong>Available:</strong> Firmware binary is ready for flashing</p>
                <p>❌ <strong>Not Available:</strong> Run <code>uv run scripts/update_firmwares.py</code> to download</p>
            </div>
        </div>
        
        <script>
            function flashFirmware(name) {{
                const button = document.getElementById('flash-' + name);
                button.innerHTML = '⏳ Flashing...';
                button.disabled = true;
                
                // TODO: Implement actual flashing via API
                alert('Flash functionality will be implemented next!\\nFirmware: ' + name);
                
                // Reset button after 2 seconds (temporary)
                setTimeout(() => {{
                    button.innerHTML = '🚀 Flash';
                    button.disabled = false;
                }}, 2000);
            }}
            
            // Auto-refresh every 30 seconds
            setInterval(() => {{
                console.log('Auto-refreshing firmware list...');
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    '''


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting ESP32 Firmware Flash Web Tool...")
    print("📍 Open your browser to: http://localhost:8000")
    print("🔧 API documentation: http://localhost:8000/docs")
    print("💡 Press Ctrl+C to stop")
    
    uvicorn.run(
        "webflasher:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
