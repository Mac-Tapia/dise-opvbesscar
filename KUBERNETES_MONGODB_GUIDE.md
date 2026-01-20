# 🐳 Kubernetes + MongoDB Deployment Guide

## 📋 Overview

Configuración completa para deployar PVBESSCAR en Kubernetes con MongoDB integrado.

---

## ✅ Requisitos

```bash
# Kubernetes
kubectl version --client       # v1.34.1+

# Docker
docker version                 # 20.10+

# Helm (opcional)
helm version                   # 3.0+
```

---

## 🚀 Quick Start

### 1. **Verificar Kubernetes**

```bash
kubectl cluster-info
kubectl get nodes
```

### 2. **Deploy Completo**

```bash
kubectl apply -f k8s-deployment.yaml
```

### 3. **Verificar Deployment**

```bash
kubectl get pods -n pvbesscar
kubectl get svc -n pvbesscar
```

---

## 📦 Componentes Kubernetes

### 1. **Namespace**

```yaml
Nombre: pvbesscar
Labels: app=pvbesscar
```

### 2. **MongoDB StatefulSet**

```yaml
Nombre:        mongodb
Replicas:      1
Imagen:        mongo:7.0
Puerto:        27017
Almacenamiento: 10Gi (PVC)

Credenciales:
  Username: admin
  Password: pvbesscar2026
```

### 3. **PVBESSCAR Pipeline Deployment**

```yaml
Nombre:        pvbesscar-pipeline
Replicas:      1 (escalable)
Imagen:        pvbesscar:latest
Puertos:       5000 (Web), 8888 (Jupyter)
CPU:           2-4 cores
Memoria:       4-8 GB
```

### 4. **Persistent Volumes**

```yaml
mongodb-pvc:           10Gi
pvbesscar-data-pvc:    20Gi
pvbesscar-outputs-pvc: 50Gi
```

### 5. **Services**

```yaml
mongodb:             ClusterIP (27017)
pvbesscar-pipeline:  LoadBalancer (5000, 8888)
```

### 6. **Ingress**

```yaml
Host: pvbesscar.local
Paths:
  /          → Web (5000)
  /jupyter   → Jupyter Lab (8888)
TLS: Habilitado
```

---

## 🐍 Uso con Python

### Deploy

```bash
python k8s_manager.py deploy
```

### Status

```bash
python k8s_manager.py status
```

### Logs

```bash
python k8s_manager.py logs
python k8s_manager.py logs --pod pvbesscar-pipeline-0
```

### Port Forward

```bash
python k8s_manager.py forward web      # 5000
python k8s_manager.py forward jupyter  # 8888
python k8s_manager.py forward mongodb  # 27017
```

### Scale

```bash
python k8s_manager.py scale 3
```

### MongoDB

```bash
python k8s_manager.py mongo status
python k8s_manager.py mongo shell
```

### Delete

```bash
python k8s_manager.py delete
```

---

## 🔑 MongoDB Credentials

```yaml
Secret: mongodb-credentials
Keys:
  username: admin
  password: pvbesscar2026
  connection_string: mongodb://admin:pvbesscar2026@mongodb:27017/pvbesscar
```

### Connection desde Pod

```python
from pymongo import MongoClient
import os

uri = os.getenv('MONGODB_URI')
client = MongoClient(uri)
db = client['pvbesscar']
```

---

## 📊 MongoDB Collections

### Inicializadas Automáticamente

```javascript
// Collections
db.training_metrics      // Métricas de entrenamiento
db.checkpoints          // Checkpoints de modelos
db.scenarios            // Escenarios de validación

// Indexes
training_metrics: {"model": 1, "timestamp": -1}
checkpoints:      {"model": 1, "episode": 1}
scenarios:        {"scenario_id": 1}
```

---

## 🌐 Acceso Web

### Rutas Disponibles

| Ruta | Servicio | Puerto |
| ------ | ---------- | -------- |
| <http://localhost:5000> | Web Interface | 5000 |
| <http://localhost:8888> | Jupyter Lab | 8888 |
| <http://localhost:27017> | MongoDB | 27017 |

### Desde Ingress

```text
http://pvbesscar.local
https://pvbesscar.local (con TLS)
```

### Port Forward

```bash
# Terminal 1: Web
kubectl port-forward svc/pvbesscar-pipeline 5000:5000 -n pvbesscar

# Terminal 2: Jupyter
kubectl port-forward svc/pvbesscar-pipeline 8888:8888 -n pvbesscar

# Terminal 3: MongoDB
kubectl port-forward svc/mongodb 27017:27017 -n pvbesscar
```

---

## 🔄 Scalabilidad

### HorizontalPodAutoscaler

```yaml
Min Replicas: 1
Max Replicas: 3
Metricas:
  CPU:    70% utilization → scale up
  Memory: 80% utilization → scale up
```

### Manual Scale

```bash
kubectl scale deployment pvbesscar-pipeline --replicas 3 -n pvbesscar
```

---

## 📈 Monitoreo

### ServiceMonitor (Prometheus)

```bash
# Scrape metrics cada 30s
/metrics endpoint

# Métricas incluidas:
- HTTP requests
- Latency
- Error rates
- Custom training metrics
```

### Ver Logs

```bash
# Todos los pods
kubectl logs -n pvbesscar -f

# Pod específico
kubectl logs pvbesscar-pipeline-0 -n pvbesscar -f

# Últimas 100 líneas
kubectl logs pvbesscar-pipeline-0 -n pvbesscar --tail=100
```

### Exec en Pod

```bash
kubectl exec -it pvbesscar-pipeline-0 -n pvbesscar -- bash
```

---

## 🔐 Network Policy

```yaml
Ingress:
  - podSelector: mongodb
    port: 27017 (TCP)

Egress:
  - To: mongodb
    port: 27017 (TCP)
  - To: External DNS
    port: 53 (TCP/UDP)
```

---

## 💾 Persistent Storage

### MongoDB Storage

```yaml
PVC: mongodb-pvc
Size: 10Gi
AccessMode: ReadWriteOnce
Mounts: /data/db
```

### Pipeline Data

```yaml
PVC: pvbesscar-data-pvc
Size: 20Gi
AccessMode: ReadWriteOnce
Mounts: /app/data
```

### Pipeline Outputs

```yaml
PVC: pvbesscar-outputs-pvc
Size: 50Gi
AccessMode: ReadWriteOnce
Mounts: /app/outputs
```

---

## 🧪 Health Checks

### MongoDB

```yaml
Liveness:
  Command: mongosh --eval "db.adminCommand('ping')"
  Initial Delay: 30s
  Period: 10s
```

### Pipeline

```yaml
Liveness:
  HTTP GET: /api/health (port 5000)
  Initial Delay: 30s
  Period: 10s

Readiness:
  HTTP GET: /api/health (port 5000)
  Initial Delay: 10s
  Period: 5s
```

---

## 🚀 Deployment Pipeline

### Paso 1: Build Image

```bash
docker build -t pvbesscar:latest .
```

### Paso 2: Push a Registry

```bash
docker tag pvbesscar:latest myregistry/pvbesscar:latest
docker push myregistry/pvbesscar:latest
```

### Paso 3: Deploy a K8s

```bash
kubectl apply -f k8s-deployment.yaml
```

### Paso 4: Verificar

```bash
kubectl get pods -n pvbesscar
kubectl logs -n pvbesscar -f
```

---

## 🔧 Troubleshooting

### Pods no inician

```bash
kubectl describe pod pvbesscar-pipeline-0 -n pvbesscar
kubectl logs pvbesscar-pipeline-0 -n pvbesscar
```

### MongoDB no conecta

```bash
# Verificar service
kubectl get svc mongodb -n pvbesscar

# Verificar pod
kubectl logs mongodb-0 -n pvbesscar

# Testear conexión
kubectl exec -it pvbesscar-pipeline-0 -n pvbesscar -- \
  mongosh --uri "mongodb://admin:pvbesscar2026@mongodb:27017/pvbesscar"
```

### PVC no provisiona

```bash
kubectl get pvc -n pvbesscar
kubectl describe pvc mongodb-pvc -n pvbesscar

# Crear default StorageClass si no existe
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
EOF
```

### Ingress no funciona

```bash
# Verificar ingress controller
kubectl get ingress -n pvbesscar
kubectl describe ingress pvbesscar-ingress -n pvbesscar

# Agregar hosts entry
echo "127.0.0.1 pvbesscar.local" >> /etc/hosts
```

---

## 📊 Comandos Útiles

### Cluster Info

```bash
kubectl cluster-info
kubectl get nodes
kubectl top nodes
```

### Namespace

```bash
kubectl get ns
kubectl describe ns pvbesscar
```

### Resources

```bash
kubectl get all -n pvbesscar
kubectl get pods,svc,pvc,deploy -n pvbesscar
```

### Events

```bash
kubectl get events -n pvbesscar
kubectl get events -n pvbesscar --sort-by='.lastTimestamp'
```

### Resource Usage

```bash
kubectl top pods -n pvbesscar
kubectl top nodes
kubectl describe node
```

---

## 🔄 Updates & Rolling Deployment

### Update Image

```bash
kubectl set image deployment/pvbesscar-pipeline \
  pipeline=pvbesscar:v2 -n pvbesscar

# Verificar rollout
kubectl rollout status deployment/pvbesscar-pipeline -n pvbesscar
```

### Rollback

```bash
kubectl rollout undo deployment/pvbesscar-pipeline -n pvbesscar
```

### History

```bash
kubectl rollout history deployment/pvbesscar-pipeline -n pvbesscar
```

---

## 🌍 Multi-Region Deployment

### Replicar en múltiples clusters

```bash
for cluster in cluster1 cluster2 cluster3; do
  kubectl --context=$cluster apply -f k8s-deployment.yaml
done
```

---

## 📚 Recursos

### Archivos

- `k8s-deployment.yaml` - Configuración completa
- `k8s_manager.py` - Python CLI
- `docker-compose.yml` - Local dev
- `Dockerfile` - Imagen base

### Comandos Rápidos

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
```

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