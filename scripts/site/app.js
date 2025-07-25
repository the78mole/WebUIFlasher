// ESP32 Firmware Flash Tool - JavaScript
async function loadFirmware() {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const table = document.getElementById('firmware-table');
    const tbody = document.getElementById('firmware-list');

    // Show loading, hide others
    loading.style.display = 'block';
    error.style.display = 'none';
    table.style.display = 'none';

    try {
        const response = await fetch('/api/firmware');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const firmware = await response.json();

        // Clear existing rows
        tbody.innerHTML = '';

        // Add firmware rows
        firmware.forEach(fw => {
            const row = document.createElement('tr');
            row.className = fw.available ? 'available' : 'unavailable';

            const statusIcon = fw.available ? '✅' : '❌';
            const flashButton = fw.available ?
                `<button class="flash-btn" onclick="flashFirmware('${fw.name}')" id="flash-${fw.name}">🚀 Flash</button>` :
                `<button class="flash-btn disabled" disabled>❌ Not Available</button>`;

            row.innerHTML = `
                <td data-label="Name">${statusIcon} <strong>${fw.name}</strong></td>
                <td data-label="Type">${fw.type}</td>
                <td data-label="Platform">${fw.platform}</td>
                <td data-label="Version">${fw.version}</td>
                <td data-label="Size">${fw.size_kb} KB</td>
                <td data-label="Description">${fw.description}</td>
                <td data-label="Action">${flashButton}</td>
            `;

            tbody.appendChild(row);
        });

        // Show table, hide loading
        loading.style.display = 'none';
        table.style.display = 'table';

    } catch (err) {
        // Show error
        loading.style.display = 'none';
        error.style.display = 'block';
        document.getElementById('error-message').textContent =
            `Failed to load firmware list: ${err.message}`;
    }
}

async function loadSerialPorts() {
    try {
        const response = await fetch('/api/serial-ports');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const ports = await response.json();
        const dropdown = document.getElementById('serial-port-select');

        // Clear existing options
        dropdown.innerHTML = '';

        // Add ports to dropdown
        ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port.device;
            option.textContent = `${port.device} - ${port.description}`;
            if (port.hwid && port.hwid !== 'n/a') {
                option.textContent += ` (${port.hwid})`;
            }
            dropdown.appendChild(option);
        });

        // Select auto by default
        dropdown.value = 'auto';

    } catch (err) {
        console.error('Failed to load serial ports:', err);
        // Add a fallback option
        const dropdown = document.getElementById('serial-port-select');
        dropdown.innerHTML = '<option value="auto">auto - Auto-detect</option>';
    }
}

async function updateFirmware() {
    const button = document.querySelector('.update-firmware-btn');
    const originalHTML = button.innerHTML;

    button.innerHTML = '⏳ Updating...';
    button.disabled = true;
    button.classList.add('updating');

    // Show terminal and run update command
    terminal.show();
    terminal.sendCommand('update_firmware', {});

    // Reset button after some time (the WebSocket will show actual progress)
    setTimeout(() => {
        button.innerHTML = originalHTML;
        button.disabled = false;
        button.classList.remove('updating');
    }, 5000);
}

async function flashFirmware(name) {
    const button = document.getElementById('flash-' + name);
    const originalHTML = button.innerHTML;

    button.innerHTML = '⏳ Flashing...';
    button.disabled = true;
    button.classList.add('flashing');

    // Get selected port
    const portDropdown = document.getElementById('serial-port-select');
    const selectedPort = portDropdown ? portDropdown.value : 'auto';

    // Use WebSocket terminal for live output
    terminal.flashFirmware(name, selectedPort);

    // Set up button state handling
    // We'll listen for WebSocket messages to determine success/failure
    const handleFlashResult = (event) => {
        const data = JSON.parse(event.data);

        if (data.message && data.message.includes(name)) {
            if (data.type === 'success') {
                // Flash succeeded
                button.innerHTML = '✅ Success!';
                button.classList.remove('flashing');
                button.classList.add('success');

                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.disabled = false;
                    button.classList.remove('success');
                }, 3000);

                terminal.websocket.removeEventListener('message', handleFlashResult);
            } else if (data.type === 'error' && data.message.includes('Flash')) {
                // Flash failed
                button.innerHTML = '❌ Failed';
                button.classList.remove('flashing');
                button.classList.add('error');

                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.disabled = false;
                    button.classList.remove('error');
                }, 3000);

                terminal.websocket.removeEventListener('message', handleFlashResult);
            }
        }
    };

    if (terminal.websocket && terminal.websocket.readyState === WebSocket.OPEN) {
        terminal.websocket.addEventListener('message', handleFlashResult);

        // Fallback timeout in case we don't get a result
        setTimeout(() => {
            terminal.websocket.removeEventListener('message', handleFlashResult);
            if (button.classList.contains('flashing')) {
                button.innerHTML = '⏰ Timeout';
                button.classList.remove('flashing');
                button.classList.add('error');

                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.disabled = false;
                    button.classList.remove('error');
                }, 3000);
            }
        }, 60000); // 1 minute timeout
    } else {
        // Fallback to old HTTP method if WebSocket not available
        button.innerHTML = '🔌 No WebSocket';
        button.classList.remove('flashing');
        button.classList.add('error');

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.disabled = false;
            button.classList.remove('error');
        }, 3000);
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    // Load firmware on page load
    loadFirmware();

    // Load serial ports on page load
    loadSerialPorts();

    // Auto-refresh every 30 seconds
    setInterval(loadFirmware, 30000);

    // Handle refresh button
    const refreshBtn = document.querySelector('.refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadFirmware);
    }

    // Handle serial ports refresh button
    const refreshPortsBtn = document.querySelector('.refresh-ports-btn');
    if (refreshPortsBtn) {
        refreshPortsBtn.addEventListener('click', loadSerialPorts);
    }

    // Handle update firmware button
    const updateFirmwareBtn = document.querySelector('.update-firmware-btn');
    if (updateFirmwareBtn) {
        updateFirmwareBtn.addEventListener('click', updateFirmware);
    }

    // Initialize terminal
    terminal = new Terminal();

    console.log('ESP32 Firmware Flash Tool initialized');
});

// Terminal functionality
class Terminal {
    constructor() {
        this.output = document.getElementById('terminal-output');
        this.content = document.getElementById('terminal-content');
        this.isCollapsed = false;
        this.autoScroll = true;
        this.websocket = null;
        this.initializeControls();
        this.connectWebSocket();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            this.addLine('🚀 WebSocket Terminal connected', 'success', false);
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onclose = () => {
            this.addLine('⚠️ WebSocket connection closed', 'warning', false);
            // Try to reconnect after 3 seconds
            setTimeout(() => {
                this.addLine('🔄 Attempting to reconnect...', 'info', false);
                this.connectWebSocket();
            }, 3000);
        };

        this.websocket.onerror = (error) => {
            this.addLine('❌ WebSocket error: ' + error, 'error', false);
        };
    }

    handleWebSocketMessage(data) {
        const { type, message, timestamp } = data;

        switch (type) {
            case 'info':
                this.addLine(message, 'info', false);
                break;
            case 'command':
                this.addLine(message, 'command', true);
                break;
            case 'output':
                this.addLine(message, 'info', false);
                break;
            case 'progress':
                // Progress messages should overwrite previous progress only
                this.updateOrAddLine(message, 'progress', false);
                break;
            case 'partial':
                // Partial messages should also overwrite previous progress/partial
                this.updateOrAddLine(message, 'partial', false);
                break;
            case 'success':
                // Success messages are always new lines
                this.addLine(message, 'success', false);
                break;
            case 'error':
                this.addLine(message, 'error', false);
                break;
            case 'warning':
                this.addLine(message, 'warning', false);
                break;
            case 'pong':
                // Handle ping/pong silently
                break;
            default:
                this.addLine(`Unknown message type: ${type}`, 'warning', false);
        }
    }

    sendCommand(type, data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: type,
                ...data
            }));
        } else {
            this.addLine('❌ WebSocket not connected', 'error', false);
        }
    }

    flashFirmware(firmwareName, port = 'auto') {
        this.show();
        this.sendCommand('flash', {
            firmware: firmwareName,
            port: port
        });
    }

    runEsptoolCommand(command) {
        this.show();

        // Get selected port from dropdown
        const portDropdown = document.getElementById('serial-port-select');
        const selectedPort = portDropdown ? portDropdown.value : 'auto';

        // Add port parameter to command if not auto
        let fullCommand = command;
        if (selectedPort !== 'auto') {
            fullCommand = `--port ${selectedPort} ${command}`;
        }

        this.sendCommand('esptool', {
            command: fullCommand
        });
    }

    initializeControls() {
        // Clear button
        document.getElementById('clear-terminal').addEventListener('click', () => {
            this.clear();
        });

        // Scroll lock button
        const scrollLockBtn = document.getElementById('scroll-lock');
        scrollLockBtn.addEventListener('click', () => {
            this.autoScroll = !this.autoScroll;
            scrollLockBtn.textContent = this.autoScroll ? '📌 Lock' : '🔓 Unlock';
            scrollLockBtn.title = this.autoScroll ? 'Disable Auto-Scroll' : 'Enable Auto-Scroll';
        });

        // Collapse/expand button
        const collapseBtn = document.getElementById('toggle-terminal');
        collapseBtn.addEventListener('click', () => {
            this.toggle();
        });
    }

    addLine(text, type = 'info', showPrompt = true) {
        const line = document.createElement('div');
        line.className = `terminal-line terminal-${type}`;

        if (showPrompt) {
            const prompt = document.createElement('span');
            prompt.className = 'terminal-prompt';
            prompt.textContent = 'esp32@webflash:~$';
            line.appendChild(prompt);
        }

        const textSpan = document.createElement('span');
        textSpan.className = 'terminal-text';
        textSpan.textContent = text;
        line.appendChild(textSpan);

        this.output.appendChild(line);

        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    updateOrAddLine(text, type = 'progress', showPrompt = false) {
        // Simple logic: only overwrite if last line was progress/partial AND this is also progress/partial
        const lines = this.output.getElementsByClassName('terminal-line');
        if (lines.length > 0) {
            const lastLine = lines[lines.length - 1];

            const lastWasProgressOrPartial =
                lastLine.classList.contains('terminal-progress') ||
                lastLine.classList.contains('terminal-partial');

            const thisIsProgressOrPartial =
                type === 'progress' ||
                type === 'partial';

            // Only overwrite if both conditions are met
            if (lastWasProgressOrPartial && thisIsProgressOrPartial) {
                const textSpan = lastLine.querySelector('.terminal-text');
                if (textSpan) {
                    textSpan.textContent = text;
                    lastLine.className = `terminal-line terminal-${type}`;
                    if (this.autoScroll) this.scrollToBottom();
                    return;
                }
            }
        }

        // Otherwise, add new line
        this.addLine(text, type, showPrompt);
    }

    addCommand(command) {
        this.addLine(command, 'command', true);
    }

    addOutput(text, type = 'info') {
        // Split multi-line output
        const lines = text.split('\n');
        lines.forEach((line, index) => {
            if (line.trim()) {
                this.addLine(line, type, false);
            }
        });
    }

    addProgress(text) {
        this.addLine(text, 'progress', false);
    }

    addSuccess(text) {
        this.addLine(`✅ ${text}`, 'success', false);
    }

    addError(text) {
        this.addLine(`❌ ${text}`, 'error', false);
    }

    addWarning(text) {
        this.addLine(`⚠️ ${text}`, 'warning', false);
    }

    clear() {
        this.output.innerHTML = '';
        this.addLine('Terminal cleared', 'info');
    }

    toggle() {
        this.isCollapsed = !this.isCollapsed;
        const collapseBtn = document.getElementById('toggle-terminal');

        if (this.isCollapsed) {
            this.content.classList.add('collapsed');
            collapseBtn.textContent = '➕';
            collapseBtn.title = 'Expand Terminal';
        } else {
            this.content.classList.remove('collapsed');
            collapseBtn.textContent = '➖';
            collapseBtn.title = 'Collapse Terminal';
        }
    }

    scrollToBottom() {
        this.content.scrollTop = this.content.scrollHeight;
    }

    show() {
        if (this.isCollapsed) {
            this.toggle();
        }
    }
}

// Global terminal instance
let terminal;
