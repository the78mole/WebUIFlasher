# Docker Deployment Instructions

## Quick Start

1. **Create your sources configuration:**
   ```bash
   cp sources_example.yaml sources.yaml
   # Edit sources.yaml with your firmware repositories
   ```

2. **Start the container:**
   ```bash
   docker-compose up -d
   ```

3. **Access the web interface:**
   Open http://localhost:8000 in your browser

## Configuration Files

### sources.yaml (Required)
The `sources.yaml` file defines which firmware repositories to fetch from. It **must** be mounted from outside the container for security and flexibility.

**Example:**
```yaml
fetchdir: ./tmpfw

sources:
  - type: github
    platform: pio
    name: my-firmware
    repo: user/my-esp32-firmware
    asset_pattern: "^firmware-esp32-${revision}.bin$"
```

### Volume Mounts

| Host Path | Container Path | Description |
|-----------|---------------|-------------|
| `./sources.yaml` | `/app/sources.yaml:ro` | **Required** - Firmware source configuration |
| `./tmpfw` | `/app/tmpfw` | Firmware download directory |
| `./img` | `/app/img:ro` | Optional custom firmware images |
| `/dev` | `/dev` | USB device access |

## Docker Compose Files

- `docker-compose.yml` - Development setup with live reload
- `docker-compose.production.yml` - Production setup with published image
- `docker-compose.production-pinned.yml` - Production with pinned version
- `docker-compose.production-secure.yml` - Production with limited device access
- `examples/docker-compose.extended.yml` - Extended setup with custom features

## Security Notes

- The `sources.yaml` file is **never** included in the Docker image
- Always mount it as read-only (`:ro`)
- Use `docker-compose.production-secure.yml` for production environments
- Consider running without `privileged: true` by mapping specific TTY devices

## Troubleshooting

### Container fails to start with "sources.yaml not found"
```bash
# Make sure you have a sources.yaml file in your current directory
ls -la sources.yaml

# If not, create one from the example
cp sources_example.yaml sources.yaml
```

### No firmware appears in web interface
```bash
# Check if tmpfw directory has content
ls -la tmpfw/

# Check container logs
docker-compose logs webuiflasher
```

### USB devices not detected
```bash
# Check if devices are mapped correctly
docker-compose exec webuiflasher ls -la /dev/ttyUSB* /dev/ttyACM*

# For secure setup, adjust device mappings in docker-compose.production-secure.yml
```
