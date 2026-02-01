# 🐳 Kubernetes + MongoDB Deployment Guide

## 📋 Overview

Configuración completa para deployar PVBESSCAR en Kubernetes con MongoDB
integrado.

---

## ✅ Requisitos

<!-- markdownlint-disable MD013 -->
```bash
# Kubernetes
kubectl version --client       # v1.34.1+

# Docker
docker version                 # 20.10+

# Helm (opcional)
helm version                   # 3.0+
```bash
<!-- markdownlint-enable MD013 -->

---

## 🚀 Quick Start

### 1. **Verificar Kubernetes**

<!-- markdownlint-disable MD013 -->
```bash
kubectl cluster-info
kubectl get nodes
```bash
<!-- markdownlint-enable MD013 -->

### 2. **De...
```

[Ver código completo en GitHub]bash
kubectl get pods -n pvbesscar
kubectl get svc -n pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

---

## 📦 Componentes Kubernetes

### 1. **Namespace**

<!-- markdownlint-disable MD013 -->
```yaml
Nombre: pvbesscar
Labels: app=pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

### 2. **MongoDB StatefulSet**

<!-- markdownlint-disable MD013 -->
```yaml
Nombre:        mongodb
Replicas:      1
Imagen:        mongo:7.0
Puerto:        27017
Almacenamiento: 10...
```

[Ver código completo en GitHub]yaml
Nombre:        pvbesscar-pipeline
Replicas:      1 (escalable)
Imagen:        pvbesscar:latest
Puertos:       5000 (Web), 8888 (Jupyter)
CPU:           2-4 cores
Memoria:       4-8 GB
```bash
<!-- markdownlint-enable MD013 -->

### 4. **Persistent Volumes**

<!-- markdownlint-disable MD013 -->
```yaml
mongodb-pvc:           10Gi
pvbesscar-data-pvc:    20Gi
pvbesscar-outputs-pvc: 50Gi
```bash
<!-- markdownlint-enable MD013 -->

### 5. **Services**

<!-- markdownlint-disable MD013 -->
```yaml
mongodb:             ClusterIP (27017)
pvbesscar-pipeline:  LoadBalancer (5000, 8888)
```bash
<!...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🐍 Uso con Python

### Deploy

<!-- markdownlint-disable MD013 -->
```bash
python k8s_manager.py deploy
```bash
<!-- markdownlint-enable MD013 -->

### Status

<!-- markdownlint-disable MD013 -->
```bash
python k8s_manager.py status
```bash
<!-- markdownlint-enable MD013 -->

### Logs

<!-- markdownlint-disable MD013 -->
```bash
python k8s_manager.py logs
python k8s_manager.py logs --pod pvbesscar-pipeline-0
```bash
<!-- markdownlint-enable MD013 -->

### Port Forward

<...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Scale

<!-- markdownlint-disable MD013 -->
```bash
python k8s_manager.py scale 3
```bash
<!-- markdownlint-enable MD013 -->

### MongoDB (CLI)

<!-- markdownlint-disable MD013 -->
```bash
python k8s_manager.py mongo status
python k8s_manager.py mongo shell
```bash
<!-- markdownlint-enable MD013 -->

### Delete

<!-- markdownlint-disable MD013 -->
```bash
python k8s_manager.py delete
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔑 MongoDB Cre...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Connection desde Pod

<!-- markdownlint-disable MD013 -->
```python
from pymongo import MongoClient
import os

uri = os.getenv('MONGODB_URI')
client = MongoClient(uri)
db = client['pvbesscar']
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 MongoDB Collections

### Inicializadas Automáticamente

<!-- markdownlint-disable MD013 -->
```javascript
// Collections
db.training_metrics      // Métricas de entrenamiento
db.checkpoints          // Checkpoints de mode...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🌐 Acceso Web

<!-- markdownlint-disable MD013 -->
### Rutas Disponibles | Ruta | Servicio | Puerto | | ------ | ---------- | -------- | | <http://localhost:5000> | Web Interface | 5000 | | <http://localhost:8888> | Jupyter Lab | 8888 | | <http://localhost:27017> | MongoDB | 27017 | ### Desde Ingress

<!-- markdownlint-disable MD013 -->
```text
http://pvbesscar.local
https://pvbesscar.local (con TLS)
```bash
<!-- markdownlint-enable MD013 -->

### Port Forward (Ingress/Servicios)

<!-- markdownlint-disable MD013 -->
```bash
# Terminal 1: Web
kubectl port-forward svc/pvbesscar-pipeline 5000:5000 -n pvbesscar

# Terminal 2: Jupyter
kubectl port-forward svc/pvbesscar-pipeline 8888:8888 -n pvbesscar

# Terminal 3: MongoDB
kubectl port-forwar...
```

[Ver código completo en GitHub]yaml
Min Replicas: 1
Max Replicas: 3
Metricas:
  CPU:    70% utilization → scale up
  Memory: 80% utilization → scale up
```bash
<!-- markdownlint-enable MD013 -->

### Manual Scale

<!-- markdownlint-disable MD013 -->
```bash
kubectl scale deployment pvbesscar-pipeline --replicas 3 -n pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

---

## 📈 Monitoreo

### ServiceMonitor (Prometheus)

<!-- markdownlint-disable MD013 -->
```bash
# Scrape metrics cada 30s
/metrics endpoint

# Métricas incluidas:
- HTTP requests
- Laten...
```

[Ver código completo en GitHub]bash
# Todos los pods
kubectl logs -n pvbesscar -f

# Pod específico
kubectl logs pvbesscar-pipeline-0 -n pvbesscar -f

# Últimas 100 líneas
kubectl logs pvbesscar-pipeline-0 -n pvbesscar --tail=100
```bash
<!-- markdownlint-enable MD013 -->

### Exec en Pod

<!-- markdownlint-disable MD013 -->
```bash
kubectl exec -it pvbesscar-pipeline-0 -n pvbesscar -- bash
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔐 Network Policy

<!-- markdownlint-disable MD013 -->
```yaml
Ingress:
  - podSelector: mongodb
    port: 27017 (TCP)

Egress:
  - To: mongodb
    port: 27017 (TCP)
  - To: External DNS
    po...
```

[Ver código completo en GitHub]yaml
PVC: mongodb-pvc
Size: 10Gi
AccessMode: ReadWriteOnce
Mounts: /data/db
```bash
<!-- markdownlint-enable MD013 -->

### Pipeline Data

<!-- markdownlint-disable MD013 -->
```yaml
PVC: pvbesscar-data-pvc
Size: 20Gi
AccessMode: ReadWriteOnce
Mounts: /app/data
```bash
<!-- markdownlint-enable MD013 -->

### Pipeline Outputs

<!-- markdownlint-disable MD013 -->
```yaml
PVC: pvbesscar-outputs-pvc
Size: 50Gi
AccessMode: ReadWriteOnce
Mounts: /app/outputs
```bash
<!-- markdownlint-e...
```

[Ver código completo en GitHub]yaml
Liveness:
  Command: mongosh --eval "db.adminCommand('ping')"
  Initial Delay: 30s
  Period: 10s
```bash
<!-- markdownlint-enable MD013 -->

### Pipeline

<!-- markdownlint-disable MD013 -->
```yaml
Liveness:
  HTTP GET: /api/health (port 5000)
  Initial Delay: 30s
  Period: 10s

Readiness:
  HTTP GET: /api/health (port 5000)
  Initial Delay: 10s
  Period: 5s
```bash
<!-- markdownlint-enable MD013 -->

---

## 🚀 Deployment Pipeline

### Paso 1: Build Image

<!-- markdownlint-disable MD013 -->
```bash...
```

[Ver código completo en GitHub]bash
docker tag pvbesscar:latest myregistry/pvbesscar:latest
docker push myregistry/pvbesscar:latest
```bash
<!-- markdownlint-enable MD013 -->

### Paso 3: Deploy a K8s

<!-- markdownlint-disable MD013 -->
```bash
kubectl apply -f k8s-deployment.yaml
```bash
<!-- markdownlint-enable MD013 -->

### Paso 4: Verificar

<!-- markdownlint-disable MD013 -->
```bash
kubectl get pods -n pvbesscar
kubectl logs -n pvbesscar -f
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔧 Troubleshooting

### Pods no inic...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### MongoDB no conecta

<!-- markdownlint-disable MD013 -->
```bash
# Verificar service
kubectl get svc mongodb -n pvbesscar

# Verificar pod
kubectl logs mongodb-0 -n pvbesscar

# Testear conexión
kubectl exec -it pvbesscar-pipeline-0 -n pvbesscar -- \
  mongosh --uri "mongodb://admin:pvbesscar2026@mongodb:27017/pvbesscar"
```bash
<!-- markdownlint-enable MD013 -->

### PVC no provisiona

<!-- markdownlint-disable MD013 -->
```bash
kubectl get pvc -n pvbesscar
ku...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Ingress no funciona

<!-- markdownlint-disable MD013 -->
```bash
# Verificar ingress controller
kubectl get ingress -n pvbesscar
kubectl describe ingress pvbesscar-ingress -n pvbesscar

# Agregar hosts entry
echo "127.0.0.1 pvbesscar.local" >> /etc/hosts
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 Comandos Útiles

### Cluster Info

<!-- markdownlint-disable MD013 -->
```bash
kubectl cluster-info
kubectl get nodes
kubectl top nodes
```bash
<!-- markdow...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Resources

<!-- markdownlint-disable MD013 -->
```bash
kubectl get all -n pvbesscar
kubectl get pods,svc,pvc,deploy -n pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

### Events

<!-- markdownlint-disable MD013 -->
```bash
kubectl get events -n pvbesscar
kubectl get events -n pvbesscar --sort-by='.lastTimestamp'
```bash
<!-- markdownlint-enable MD013 -->

### Resource Usage

<!-- markdownlint-disable MD013 -->
```bash
kubectl top pods -n pvbessc...
```

[Ver código completo en GitHub]bash
kubectl set image deployment/pvbesscar-pipeline \
  pipeline=pvbesscar:v2 -n pvbesscar

# Verificar rollout
kubectl rollout status deployment/pvbesscar-pipeline -n pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

### Rollback

<!-- markdownlint-disable MD013 -->
```bash
kubectl rollout undo deployment/pvbesscar-pipeline -n pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

### History

<!-- markdownlint-disable MD013 -->
```bash
kubectl rollout history deployment/pvbesscar-pipeline -n pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

---

## 🌍 Multi-Region Deploym...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 📚 Recursos

### Archivos

- `k8s-deployment.yaml` - Configuración completa
- `k8s_manager.py` - Python CLI
- `docker-compose.yml` - Local dev
- `Dockerfile` - Imagen base

### Comandos Rápidos

<!-- markdownlint-disable MD013 -->
```bash
# Deploy completo
kubectl apply -f k8s-deployment.yaml

# Ver status
kubectl get all -n pvbesscar

# Port forward web
kubectl port-forward svc/pvbesscar-pipeline 5000:5000 -n pvbesscar

# MongoDB shell
kubectl exec -it mongodb-0 -n pvbesscar -- mongosh -u admin -p pvbesscar2026

# Logs en vivo
kubectl logs -f -n pvbesscar -l app=pvbesscar-pipeline

# Delete todo
kubectl delete namespace pvbesscar
```bash
<!-- markdownlint-enable MD013 -->

---

## 🎓 Next Steps

1. **Build Image**: `docker build -t pvbesscar:latest .`
2. **Deploy**: `kubectl apply -f k8s-deployment.yaml`
3. **Verify**: `kubectl get pods -n pvbesscar`
4. **Access**: `http://localhost:5000` (con port-forward)
5. **Monitor**: `kubectl logs -f -n pvbesscar -l app=pvbesscar-pipeline`

---

**Created**: 2026-01-20  
**K8s Version**: 1.34.1  
**MongoDB**: 7.0  
**Status**: ✅ Production Ready
