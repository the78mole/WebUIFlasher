# WebUIFlasher Production Deployment

This directory contains production-ready Docker Compose configurations that use
the pre-built WebUIFlasher images from GitHub Container Registry.

## 🚀 Quick Start

### Standard Production Setup

```bash
# Download the compose file
curl -O https://raw.githubusercontent.com/the78mole/WebUIFlasher/main/docker-compose.production.yml

# Start WebUIFlasher
docker compose -f docker-compose.production.yml up -d

# Access at http://localhost:8000
```

## 📋 Available Configurations

### 1. **docker-compose.production.yml** - Standard Setup

- Uses `ghcr.io/the78mole/webuiflasher:latest`
- Full USB device access (`/dev` mounted)
- Privileged mode for maximum compatibility
- Health checks included
- **Recommended for:** Development and home use

### 2. **docker-compose.production-secure.yml** - Secure Setup

- Specific TTY device mapping only
- No privileged mode
- Minimal permissions
- **Recommended for:** Production servers

### 3. **docker-compose.production-pinned.yml** - Version Pinned

- Uses specific version tag (e.g., `v1.0.0`)
- Guarantees reproducible deployments
- **Recommended for:** Production environments requiring stability

## 🔧 Customization

### Environment Variables

```yaml
environment:
  - TZ=Europe/Berlin          # Timezone
  - WEBUI_TITLE=My Flasher    # Custom title
  - WEBUI_THEME=dark          # UI theme
```

### Volume Mapping

```yaml
volumes:
  - ./my-firmware:/app/firmware     # Custom firmware directory
  - ./my-sources:/app/sources       # Custom source configurations
```

### Port Mapping

```yaml
ports:
  - "9000:8000"  # Run on port 9000 instead of 8000
```

## 🛡️ Security Considerations

### Secure Setup (Recommended for Production)

```bash
# Use the secure compose file
docker compose -f docker-compose.production-secure.yml up -d

# Adjust TTY devices as needed
# Edit the file to match your hardware setup
```

### Device Permissions

```bash
# Add your user to dialout group (host system)
sudo usermod -a -G dialout $USER

# Or run container as root (already configured)
```

## 📦 Available Image Tags

| Tag | Description | Use Case |
|-----|-------------|----------|
| `latest` | Latest stable release | Development, testing |
| `v1.2.3` | Specific version | Production (recommended) |
| `1.2` | Major.minor version | Compatible updates |
| `1` | Major version | Long-term compatibility |

## 🔍 Health Checks

All configurations include health checks:

```bash
# Check container health
docker compose ps

# View health check logs
docker compose logs webuiflasher
```

## 🚨 Troubleshooting

### USB Device Not Found

```bash
# List available devices
ls -la /dev/tty*

# Update compose file with correct device paths
# Restart container
docker compose restart
```

### Permission Issues

```bash
# Run with root privileges (already configured)
# Or adjust host system permissions
sudo chmod 666 /dev/ttyUSB0
```

### Container Updates

```bash
# Pull latest image
docker compose pull

# Restart with new image
docker compose up -d
```

## 📚 Examples

See the `examples/` directory for:

- **Dockerfile.extended** - How to extend the base image
- **docker-compose.extended.yml** - Custom build example
- **custom-sources.yaml** - Custom firmware source configuration

## 🔗 Links

- **Docker Images:** <https://github.com/the78mole/WebUIFlasher/pkgs/container/webuiflasher>
- **Source Code:** <https://github.com/the78mole/WebUIFlasher>
- **Documentation:** <https://github.com/the78mole/WebUIFlasher/blob/main/README.md>
