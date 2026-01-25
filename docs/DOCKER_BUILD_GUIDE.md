# PVBESSCAR Docker Build Guide

## 📋 Overview

Configuración Docker actualizada para PVBESSCAR con:

- ✅ Multi-stage build optimizado
- ✅ BuildKit inline cache para faster rebuilds
- ✅ Tini init para proper signal handling
- ✅ Health checks mejorados
- ✅ Soporte GPU con nvidia-docker
- ✅ Jupyter Lab integrado
- ✅ Servicios de desarrollo (linting, testing, type checking)

---

## 🚀 Quick Start

### 1. **CPU Only (Development)**

```bash
docker-compose -f docker-compose.yml up -d
```bash

#### Servicios iniciados:

- `pvbesscar-pipeline`: Pipeline principal
- `pvbesscar-monitor`: Monitoreo de checkpoints
- `pvbesscar-jupyter`: Jupyter Lab en puerto 8888

### 2. **GPU Support**

```bash
# Requisitos: nvidia-docker2, CUDA 11.8+
docker-compose -f docker-compose.gpu.yml up -d
```bash

#### Servicios iniciados: (2)

- `pvbesscar-pipeline-gpu`: Pipeline con GPU
- `pvbesscar-monitor-gpu`: Monitoreo GPU
- `pvbesscar-jupyter-gpu`: Jupyter Lab en puerto 8889

### 3. **Development (All Services)**

```bash
docker-compose -f docker-compose.dev.yml up -d
```bash

#### Servicios iniciados: (3)

- `dev-notebook`: Jupyter Lab
- `dev-tests`: Pytest automation
- `dev-lint`: Pylint/Black/isort
- `dev-type-check`: MyPy type checking

---

## 📦 Build Commands

### Build CPU Image

```bash
# Sin cache (fresh build)
docker build -t pvbesscar:latest .

# Con BuildKit y cache (recommended)
DOCKER_BUILDKIT=1 docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t pvbesscar:latest .
```bash

### Build GPU Image

```bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t pvbesscar:latest-gpu .
```bash

### Build Dev Image

```bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t pvbesscar:dev .
```bash

---

## 🔧 Resource Configuration

### Default Limits

| Service | CPU Limit | CPU Reservation | Memory Limit | Memory Reservation |
| --------- | ----------- | ----------------- | -------------- | ------------------- |
| pipeline | 8 | 4 | 32 GB | 16 GB |
| monitor | 2 | 1 | 8 GB | 2 GB |
| jupyter | 4 | 2 | 16 GB | 8 GB |

### GPU Allocation

| Service | GPU Count | GPU Type | CPU | Memory |
| --------- | ----------- | ---------- | ----- | -------- |
| pipeline-gpu | 1 | nvidia | 16 | 64 GB |
| monitor-gpu | 1 | nvidia | 4 | 16 GB |
| jupyter-gpu | 1 | nvidia | 8 | 32 GB |

---

## 📊 Health Checks

### CPU Services

```bash
# Check pipeline health
docker exec pvbesscar-pipeline python -c "import stable_baselines3; print('OK')"

# Monitor service health
docker logs pvbesscar-pipeline --tail=20
```bash

### GPU Services

```bash
# Check GPU availability
docker exec pvbesscar-pipeline-gpu python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"

# Monitor GPU usage
docker exec pvbesscar-pipeline-gpu nvidia-smi
```bash

---

## 📝 Volume Mounts

| Volume | Host Path | Container Path | Permissions | Purpose |
| -------- | ----------- | ----------------- | ------------- | --------- |
| data | ./data | /app/data | RW | Input datasets |
| outputs | ./outputs | /app/outputs | RW | Results & checkpoints |
| configs | ./configs | /app/configs | RO | Configuration files |
| pipeline_cache | (managed) | /app/.cache | RW | Pip cache |
| jupyter_data | (managed) | /root/.jupyter | RW | Jupyter config |

---

## 🌐 Port Mappings

| Service | Port | Access |
| --------- | ------ | -------- |
| pvbesscar-jupyter | 8888 | <http://localhost:8888> |
| pvbesscar-jupyter-gpu | 8889 | <http://localhost:8889> |
| dev-notebook | 8888 | <http://localhost:8888> |

---

## 🛑 Common Commands

### View Logs

```bash
# Pipeline logs (last 100 lines)
docker logs -f pvbesscar-pipeline --tail=100

# Monitor service logs
docker logs -f pvbesscar-monitor --tail=50

# All services
docker-compose logs -f
```bash

### Execute Commands

```bash
# Run Python script in container
docker exec pvbesscar-pipeline python script.py

# Interactive shell
docker exec -it pvbesscar-pipeline bash

# Check dependencies
docker exec pvbesscar-pipeline pip list
```bash

### Stop & Clean

```bash
# Stop specific service
docker-compose stop pvbesscar-pipeline

# Stop all services
docker-compose down

# Clean all (including volumes)
docker-compose down -v

# Remove unused images
docker image prune
```bash

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Clear Docker cache
docker builder prune --all

# Rebuild without cache
docker build --no-cache -t pvbesscar:latest .

# Check build logs
docker build --progress=plain -t pvbesscar:latest . 2>&1 | tail -50
```bash

### GPU Not Available

```bash
# Verify nvidia-docker
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi

# Check CUDA availability in container
docker exec pvbesscar-pipeline-gpu python -c "import torch; print(torch.cuda.get_device_name())"

# Troubleshoot
export NVIDIA_VISIBLE_DEVICES=0
docker-compose -f docker-compose.gpu.yml up -d
```bash

### Memory Issues

```bash
# Check resource usage
docker stats

# Reduce memory allocation in docker-compose.yml
# Edit deploy.resources.limits.memory

# Restart with new limits
docker-compose restart
```bash

### Permission Denied

```bash
# Fix volume permissions
docker-compose exec pipeline chmod -R 777 /app/outputs

# Or use host user ID
docker-compose exec -u $(id -u):$(id -g) pipeline ls -la /app/outputs
```bash

---

## 📋 Dockerfile Improvements

### Multi-Stage Build

- **Stage 1 (Builder)**: Builds dependencies, creates wheels
- **Stage 2 (Runtime)**: Uses wheels from builder, minimal final image

### BuildKit Cache

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip pip install ...
```bash

Reduces build time by ~60% on rebuilds.

### Tini Init

```dockerfile
ENTRYPOINT ["/usr/bin/tini", "--"]
```bash

Ensures proper signal handling (SIGTERM, SIGINT) in containers.

### Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 ...
```bash

Docker automatically restarts unhealthy containers.

---

## 🔍 Monitoring

### Check Container Status

```bash
docker ps
docker ps -a
```bash

### View Health Status

```bash
docker inspect --format='{{json .State.Health}}' pvbesscar-pipeline | python -m json.tool
```bash

### Monitor Resources

```bash
# Real-time stats
docker stats

# Historical stats
docker stats --no-stream
```bash

---

## 📦 Deployment

### Production (CPU)

```bash
docker-compose -f docker-compose.yml -p pvbesscar up -d
```bash

### Production (GPU)

```bash
docker-compose -f docker-compose.gpu.yml -p pvbesscar-gpu up -d
```bash

### Development

```bash
docker-compose -f docker-compose.dev.yml -p pvbesscar-dev up -d
```bash

---

## 🔄 Update Process

1. **Update source code**

   ```bash
   git pull origin main
```bash

2. **Rebuild image**

   ```bash
   DOCKER_BUILDKIT=1 docker build -t pvbesscar:latest .
```bash

3. **Restart services**

   ```bash
   docker-compose down
   docker-compose up -d
```bash

---

## 📚 Additional Resources

- [Docker Best
  - Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [BuildKit](https://docs.docker.com/build/buildkit/)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)
- [Jupyter Lab Docker](https://jupyter-docker-stacks.readthedocs.io/)

---

**Last Updated**: 2026-01-20  
**Version**: 1.0.0  
**Status**: ✅ Production Ready