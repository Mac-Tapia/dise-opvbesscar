# Docker Setup Guide

## Current Status

✅ **Docker infrastructure configured** - Ready for deployment
✅ **docker-compose files updated** - Removed deprecated `version` attribute
❌ **Docker daemon not running** - Requires separate installation

## Prerequisites

### Option 1: Docker Desktop (Windows - Recommended)

1. **Download Docker Desktop**
   - Visit: <https://www.docker.com/products/docker-desktop>
   - Download for Windows

2. **Install Docker Desktop**

<!-- markdownlint-disable MD013 -->
   ```powershell
   # Run installer and follow wizard
   # Enable WSL 2 backend when prompted
```bash
<!-- markdownlint-enable MD013 -->

3. **Start Docker Desktop**
   - Launch from Start Menu
   - Wait for "Docker Desktop is running" indicator

4. **Verify Installation**

<!-- markdownlint-disable MD013 -->
   ```powershell
   docker --version
   docker ps
```bash
<!-- markdownlint-enable MD013 -->

### Option 2...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

## Using docker-compose

Once Docker is installed and running:

### Build Images

<!-- markdownlint-disable MD013 -->
```powershell
# CPU version
docker-compose -f docker-compose.yml build

# GPU version
docker-compose -f docker-compose.gpu.yml build

# Development version
docker-compose -f docker-compose.dev.yml build
```bash
<!-- markdownlint-enable MD013 -->

### Start Services

<!-- markdownlint-disable MD013 -->
```powershell
# CPU version (2)
docker-compose -f docker-compose.yml up -d

# GPU version (requires NVIDIA Dock...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### View Logs

<!-- markdownlint-disable MD013 -->
```powershell
docker-compose logs -f pvbesscar-pipeline
```bash
<!-- markdownlint-enable MD013 -->

### Stop Services

<!-- markdownlint-disable MD013 -->
```powershell
docker-compose down
```bash
<!-- markdownlint-enable MD013 -->

## Web Interface (Docker Management)

The Flask web interface runs **without Docker daemon**:

<!-- markdownlint-disable MD013 -->
```powershell
py -3.11 docker_web_interface.py
# A...
```

[Ver código completo en GitHub]powershell
# Or restart if already installed
docker daemon
```bash
<!-- markdownlint-enable MD013 -->

### Error: "Cannot connect to Docker daemon"

**Solution**: Docker not installed or not running

- Install Docker Desktop (Option 1 above)
- Or check if Docker process is running: `Get-Process dockerd`

### Error: "version attribute is obsolete" (FIXED ✓)

Already resolved - `version` field removed from all compose files.

## Kubernetes Deployment

When Docker d...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

## MongoDB Integration

MongoDB configured in Kubernetes:

- **StatefulSet**: `pvbesscar-mongodb`
- **Port**: 27017
- **PVC Storage**: 10Gi
- **Replica Set**: Enabled for HA

Access via:

<!-- markdownlint-disable MD013 -->
```powershell
python k8s_manager.py mongo shell
```bash
<!-- markdownlint-enable MD013 -->

## Next Steps

1. ✅ Install Docker Desktop
2. ✅ Verify Docker daemon running: `docker ps`
3. ✅ Build images: `docker-compose build`
4. ✅ Start services: `docker-compose up -d`
5. ✅ Deploy to Kubernetes (when cluster ready)

---

**Last Updated**: 2026-01-20  
**Files Updated**: docker-compose.yml, docker-compose.gpu.yml,
docker-compose.dev.yml
**Status**: Ready for Docker deployment