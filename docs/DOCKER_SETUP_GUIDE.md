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

   ```powershell
   # Run installer and follow wizard
   # Enable WSL 2 backend when prompted
   ```

3. **Start Docker Desktop**
   - Launch from Start Menu
   - Wait for "Docker Desktop is running" indicator

4. **Verify Installation**

   ```powershell
   docker --version
   docker ps
   ```

### Option 2: Docker CE via Chocolatey

```powershell
choco install docker-cli docker-buildx -y
# Still requires Docker Engine running separately
```bash

## Using docker-compose

Once Docker is installed and running:

### Build Images

```powershell
# CPU version
docker-compose -f docker-compose.yml build

# GPU version
docker-compose -f docker-compose.gpu.yml build

# Development version
docker-compose -f docker-compose.dev.yml build
```bash

### Start Services

```powershell
# CPU version (2)
docker-compose -f docker-compose.yml up -d

# GPU version (requires NVIDIA Docker)
docker-compose -f docker-compose.gpu.yml up -d

# Development version (2)
docker-compose -f docker-compose.dev.yml up -d
```bash

### View Logs

```powershell
docker-compose logs -f pvbesscar-pipeline
```bash

### Stop Services

```powershell
docker-compose down
```bash

## Web Interface (Docker Management)

The Flask web interface runs **without Docker daemon**:

```powershell
py -3.11 docker_web_interface.py
# Available at: http://localhost:5000
```bash

This provides:

- 📊 Container status monitoring
- 🔨 Build management
- 📋 Log viewer
- ⚙️ Service control

## Troubleshooting

### Error: "docker daemon is not running"

**Solution**: Start Docker Desktop

```powershell
# Or restart if already installed
docker daemon
```bash

### Error: "Cannot connect to Docker daemon"

**Solution**: Docker not installed or not running

- Install Docker Desktop (Option 1 above)
- Or check if Docker process is running: `Get-Process dockerd`

### Error: "version attribute is obsolete" (FIXED ✓)

Already resolved - `version` field removed from all compose files.

## Kubernetes Deployment

When Docker daemon is ready, deploy to Kubernetes:

```powershell
# Using Python CLI manager
python k8s_manager.py deploy

# Or directly
kubectl apply -f k8s-deployment.yaml

# Monitor status
python k8s_manager.py status
```bash

## MongoDB Integration

MongoDB configured in Kubernetes:

- **StatefulSet**: `pvbesscar-mongodb`
- **Port**: 27017
- **PVC Storage**: 10Gi
- **Replica Set**: Enabled for HA

Access via:

```powershell
python k8s_manager.py mongo shell
```bash

## Next Steps

1. ✅ Install Docker Desktop
2. ✅ Verify Docker daemon running: `docker ps`
3. ✅ Build images: `docker-compose build`
4. ✅ Start services: `docker-compose up -d`
5. ✅ Deploy to Kubernetes (when cluster ready)

---

**Last Updated**: 2026-01-20  
**Files Updated**: docker-compose.yml, docker-compose.gpu.yml, docker-compose.dev.yml  
**Status**: Ready for Docker deployment