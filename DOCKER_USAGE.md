# AlienRecon Docker Usage Guide

> **For Learners:** Following our free ethical hacking course on [Alien37.com](https://www.alien37.com)? Using Docker is the **highly recommended** way to get started with AlienRecon. It provides a zero-friction setup with all tools pre-installed, so you can focus on learning and hacking, not on configuration issues.

This guide covers how to build, run, and use AlienRecon with Docker.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose v2.0+
- OpenAI API key
- Target systems accessible from your Docker host

## Quick Start

### 1. Build the Image

```bash
# Build the Docker image
docker-compose build

# Or build with specific tags
docker build -t alienrecon:latest .
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run AlienRecon

```bash
# Start a reconnaissance session
docker-compose run --rm alienrecon

# Or run specific commands
docker-compose run --rm alienrecon alienrecon recon --target 10.10.10.10
docker-compose run --rm alienrecon alienrecon doctor
```

## Usage Examples

### Reconnaissance Session

```bash
# Start an AI-guided reconnaissance session
docker-compose run --rm alienrecon alienrecon recon --target 10.10.10.10

```

### Direct Tool Execution

```bash
# Run specific tools directly
docker-compose run --rm alienrecon alienrecon manual nmap -sC -sV 10.10.10.10
docker-compose run --rm alienrecon alienrecon manual nikto -h http://10.10.10.10
```

### CTF Mission Management

```bash
# Initialize a CTF mission
docker-compose run --rm alienrecon alienrecon init --ctf htb_lame

# Sessions and missions are persisted in Docker volumes
```

### Cache Management

```bash
# View cache status
docker-compose run --rm alienrecon alienrecon cache status

# Clear cache
docker-compose run --rm alienrecon alienrecon cache clear
```

## Docker Compose Services

### Main Service: `alienrecon`

The primary AlienRecon container with all tools installed:

- **Network Mode**: Host networking for scanning capabilities
- **Security**: Runs as non-root user with minimal capabilities
- **Volumes**: Persistent storage for sessions, cache, and missions
- **Health Check**: Automatic health monitoring

### Optional Service: `redis`

Redis cache for improved performance (optional):

```bash
# Start with Redis caching
docker-compose up -d redis
docker-compose run --rm alienrecon
```

## Volume Management

AlienRecon uses several Docker volumes for persistence:

- `alienrecon_data`: General application data
- `alienrecon_cache`: Tool output cache
- `alienrecon_sessions`: Session state files
- `alienrecon_missions`: CTF mission folders

### Backup Volumes

```bash
# Backup all AlienRecon data
docker run --rm -v alienrecon_data:/data -v $(pwd):/backup alpine tar czf /backup/alienrecon-backup.tar.gz -C /data .

# Restore from backup
docker run --rm -v alienrecon_data:/data -v $(pwd):/backup alpine tar xzf /backup/alienrecon-backup.tar.gz -C /data
```

### Clean Up Volumes

```bash
# Remove all AlienRecon volumes (WARNING: deletes all data)
docker-compose down -v
```

## Development Mode

For development, uncomment the volume mounts in `docker-compose.yml`:

```yaml
volumes:
  - ./src:/app/src:ro
  - ./pyproject.toml:/app/pyproject.toml:ro
  - ./poetry.lock:/app/poetry.lock:ro
```

Then rebuild when dependencies change:

```bash
docker-compose build --no-cache
```

## Production Deployment

### 1. Build Production Image

```bash
# Build with production optimizations
docker build --target base -t alienrecon:prod .
```

### 2. Deploy with Docker Compose

```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f alienrecon

# Stop services
docker-compose down
```

### 3. Security Considerations

- Container runs as non-root user (UID 1000)
- Minimal capabilities (only NET_RAW and NET_ADMIN for scanning)
- No new privileges flag enabled
- Resource limits enforced

## Troubleshooting

### Permission Issues

If you encounter permission errors with scanning tools:

```bash
# Ensure proper capabilities
docker-compose run --rm --cap-add=NET_RAW --cap-add=NET_ADMIN alienrecon
```

### Network Connectivity

The container uses host networking by default. If you need bridge networking:

1. Comment out `network_mode: host` in docker-compose.yml
2. Map required ports explicitly
3. Note: Some scanning features may be limited

### Tool Availability

Check all tools are properly installed:

```bash
docker-compose run --rm alienrecon alienrecon doctor
```

### Volume Permissions

If volumes have incorrect permissions:

```bash
# Fix ownership
docker-compose run --rm --user root alienrecon chown -R alienrecon:alienrecon /data
```

## Advanced Configuration

### Custom Wordlists

Mount additional wordlists:

```yaml
volumes:
  - /path/to/custom/wordlists:/app/custom-wordlists:ro
```

### Proxy Support

Configure proxy for tools:

```yaml
environment:
  - HTTP_PROXY=http://proxy:8080
  - HTTPS_PROXY=http://proxy:8080
  - NO_PROXY=localhost,127.0.0.1
```

### Resource Limits

Adjust CPU and memory limits in docker-compose.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

## Container Shell Access

For debugging or manual operations:

```bash
# Get a shell in the running container
docker-compose exec alienrecon /bin/bash

# Or start a new container with shell
docker-compose run --rm alienrecon /bin/bash
```

## Updating

To update AlienRecon:

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build --no-cache

# Restart services
docker-compose down
docker-compose up -d
```

## Uninstallation

To completely remove AlienRecon:

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker rmi alienrecon:latest
docker rmi alienrecon:prod
```
