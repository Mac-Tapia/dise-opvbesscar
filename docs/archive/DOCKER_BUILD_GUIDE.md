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

<!-- markdownlint-disable MD013 -->
```bash
docker-compose -f docker-compose.yml up -d
```bash
<!-- markdownlint-enable MD013 -->

#### Servicios iniciados:

- `pvbesscar-pipeline`: Pipeline principal
- `pvbesscar-monitor`: Monitoreo de checkpoints
- `pvbesscar-jupyter`: Jupyter Lab en puerto 8888

### 2. **GPU Support**

<!-- markdownlint-disable MD013 -->
```bash
# Requisitos: nvidia-docker2, CUDA 11.8+
docker-compose -f docker-compose.gp...
```

[Ver código completo en GitHub]bash
docker-compose -f docker-compose.dev.yml up -d
```bash
<!-- markdownlint-enable MD013 -->

#### Servicios iniciados: (3)

- `dev-notebook`: Jupyter Lab
- `dev-tests`: Pytest automation
- `dev-lint`: Pylint/Black/isort
- `dev-type-check`: MyPy type checking

---

## 📦 Build Commands

### Build CPU Image

<!-- markdownlint-disable MD013 -->
```bash
# Sin cache (fresh build)
docker build -t pvbesscar:latest .

# Con BuildKit y cache (recommended)
DOCKER_...
```

[Ver código completo en GitHub]bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t pvbesscar:latest-gpu .
```bash
<!-- markdownlint-enable MD013 -->

### Build Dev Image

<!-- markdownlint-disable MD013 -->
```bash
DOCKER_BUILDKIT=1 docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t pvbesscar:dev .
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔧 Resource Configuration

<!-- markdownlint-disable MD013 -->
### Default Limits | Service | CPU Limit | CPU Reservation | Memory Limit | Memory Reservat...
```

[Ver código completo en GitHub]bash
# Check pipeline health
docker exec pvbesscar-pipeline python -c "import stable_baselines3; print('OK')"

# Monitor service health
docker logs pvbesscar-pipeline --tail=20
```bash
<!-- markdownlint-enable MD013 -->

### GPU Services

<!-- markdownlint-disable MD013 -->
```bash
# Check GPU availability
docker exec pvbesscar-pipeline-gpu python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"

# Monitor GPU usage
docker exec pvbesscar-pipeline-gpu nvidia-smi
```bash
<!-- markdownlint-enable MD013 -->

---

<!-- markdownlint-disable MD013 -->
## 📝 Volume Mounts | ...
```

[Ver código completo en GitHub]bash
# Pipeline logs (last 100 lines)
docker logs -f pvbesscar-pipeline --tail=100

# Monitor service logs
docker logs -f pvbesscar-monitor --tail=50

# All services
docker-compose logs -f
```bash
<!-- markdownlint-enable MD013 -->

### Execute Commands

<!-- markdownlint-disable MD013 -->
```bash
# Run Python script in container
docker exec pvbesscar-pipeline python script.py

# Interactive shell
docker exec -it pvbesscar-pipeline bash

# Check dependencies
docker exec pvbesscar-pipeline pip list
```bash
<!-- markdownlint-enable MD013 -->

### Stop & Clean

<!-- markdownlint-disable MD013 ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🐛 Troubleshooting

### Build Fails

<!-- markdownlint-disable MD013 -->
```bash
# Clear Docker cache
docker builder prune --all

# Rebuild without cache
docker build --no-cache -t pvbesscar:latest .

# Check build logs
docker build --progress=plain -t pvbesscar:latest . 2>&1 | tail -50
```bash
<!-- markdownlint-enable MD013 -->

### GPU Not Available

<!-- markdownlint-disable MD013 -->
```bash
# Verify nvidia-docker
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-runtime...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Memory Issues

<!-- markdownlint-disable MD013 -->
```bash
# Check resource usage
docker stats

# Reduce memory allocation in docker-compose.yml
# Edit deploy.resources.limits.memory

# Restart with new limits
docker-compose restart
```bash
<!-- markdownlint-enable MD013 -->

### Permission Denied

<!-- markdownlint-disable MD013 -->
```bash
# Fix volume permissions
docker-compose exec pipeline chmod -R 777 /app/outputs

# Or use host user ID
docker-compo...
```

[Ver código completo en GitHub]dockerfile
RUN --mount=type=cache,target=/root/.cache/pip pip install ...
```bash
<!-- markdownlint-enable MD013 -->

Reduces build time by ~60% on rebuilds.

### Tini Init

<!-- markdownlint-disable MD013 -->
```dockerfile
ENTRYPOINT ["/usr/bin/tini", "--"]
```bash
<!-- markdownlint-enable MD013 -->

Ensures proper signal handling (SIGTERM, SIGINT) in containers.

### Health Checks

<!-- markdownlint-disable MD013 -->
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --re...
```

[Ver código completo en GitHub]bash
docker ps
docker ps -a
```bash
<!-- markdownlint-enable MD013 -->

### View Health Status

<!-- markdownlint-disable MD013 -->
```bash
docker inspect --format='{{json .State.Health}}' pvbesscar-pipeline|python -m json.tool
```bash
<!-- markdownlint-enable MD013 -->

### Monitor Resources

<!-- markdownlint-disable MD013 -->
```bash
# Real-time stats
docker stats

# Historical stats
docker stats --no-stream
```bash
<!-- markdown...
```

[Ver código completo en GitHub]bash
docker-compose -f docker-compose.yml -p pvbesscar up -d
```bash
<!-- markdownlint-enable MD013 -->

### Production (GPU)

<!-- markdownlint-disable MD013 -->
```bash
docker-compose -f docker-compose.gpu.yml -p pvbesscar-gpu up -d
```bash
<!-- markdownlint-enable MD013 -->

### Development

<!-- markdownlint-disable MD013 -->
```bash
docker-compose -f docker-compose.dev.yml -p pvbesscar-dev up -d
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔄 Update Proc...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

2. **Rebuild image**

<!-- markdownlint-disable MD013 -->
   ```bash
   DOCKER_BUILDKIT=1 docker build -t pvbesscar:latest .
```bash
<!-- markdownlint-enable MD013 -->

3. **Restart services**

<!-- markdownlint-disable MD013 -->
   ```bash
   docker-compose down
   docker-compose up -d
```bash
<!-- markdownlint-enable MD013 -->

---

## 📚 Additional Resources

- [Docker Best
  - Practices]([url0])
- [BuildKit](https://docs.docker.com/build/buildkit/)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)
- [Jupyter Lab Docker](https://jupyter-docker-stacks.readthedocs.io/)

---

**Last Updated**: 2026-01-20  
**Version**: 1.0.0  
**Status**: ✅ Production Ready