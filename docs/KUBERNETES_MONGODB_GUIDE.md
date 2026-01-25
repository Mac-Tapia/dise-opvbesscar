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
```bash

---

## 🚀 Quick Start

### 1. **Verificar Kubernetes**

```bash
kubectl cluster-info
kubectl get nodes
```bash

### 2. **Deploy Completo**

```bash
kubectl apply -f k8s-deployment.yaml
```bash

### 3. **Verificar Deployment**

```bash
kubectl get pods -n pvbesscar
kubectl get svc -n pvbesscar
```bash

---

## 📦 Componentes Kubernetes

### 1. **Namespace**

```yaml
Nombre: pvbesscar
Labels: app=pvbesscar
```bash

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
```bash

### 3. **PVBESSCAR Pipeline Deployment**

```yaml
Nombre:        pvbesscar-pipeline
Replicas:      1 (escalable)
Imagen:        pvbesscar:latest
Puertos:       5000 (Web), 8888 (Jupyter)
CPU:           2-4 cores
Memoria:       4-8 GB
```bash

### 4. **Persistent Volumes**

```yaml
mongodb-pvc:           10Gi
pvbesscar-data-pvc:    20Gi
pvbesscar-outputs-pvc: 50Gi
```bash

### 5. **Services**

```yaml
mongodb:             ClusterIP (27017)
pvbesscar-pipeline:  LoadBalancer (5000, 8888)
```bash

### 6. **Ingress**

```yaml
Host: pvbesscar.local
Paths:
  /          → Web (5000)
  /jupyter   → Jupyter Lab (8888)
TLS: Habilitado
```bash

---

## 🐍 Uso con Python

### Deploy

```bash
python k8s_manager.py deploy
```bash

### Status

```bash
python k8s_manager.py status
```bash

### Logs

```bash
python k8s_manager.py logs
python k8s_manager.py logs --pod pvbesscar-pipeline-0
```bash

### Port Forward

```bash
python k8s_manager.py forward web      # 5000
python k8s_manager.py forward jupyter  # 8888
python k8s_manager.py forward mongodb  # 27017
```bash

### Scale

```bash
python k8s_manager.py scale 3
```bash

### MongoDB (CLI)

```bash
python k8s_manager.py mongo status
python k8s_manager.py mongo shell
```bash

### Delete

```bash
python k8s_manager.py delete
```bash

---

## 🔑 MongoDB Credentials

```yaml
Secret: mongodb-credentials
Keys:
  username: admin
  password: pvbesscar2026
  connection_string: mongodb://admin:pvbesscar2026@mongodb:27017/pvbesscar
```bash

### Connection desde Pod

```python
from pymongo import MongoClient
import os

uri = os.getenv('MONGODB_URI')
client = MongoClient(uri)
db = client['pvbesscar']
```bash

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
```bash

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
```bash

### Port Forward (Ingress/Servicios)

```bash
# Terminal 1: Web
kubectl port-forward svc/pvbesscar-pipeline 5000:5000 -n pvbesscar

# Terminal 2: Jupyter
kubectl port-forward svc/pvbesscar-pipeline 8888:8888 -n pvbesscar

# Terminal 3: MongoDB
kubectl port-forward svc/mongodb 27017:27017 -n pvbesscar
```bash

---

## 🔄 Scalabilidad

### HorizontalPodAutoscaler

```yaml
Min Replicas: 1
Max Replicas: 3
Metricas:
  CPU:    70% utilization → scale up
  Memory: 80% utilization → scale up
```bash

### Manual Scale

```bash
kubectl scale deployment pvbesscar-pipeline --replicas 3 -n pvbesscar
```bash

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
```bash

### Ver Logs

```bash
# Todos los pods
kubectl logs -n pvbesscar -f

# Pod específico
kubectl logs pvbesscar-pipeline-0 -n pvbesscar -f

# Últimas 100 líneas
kubectl logs pvbesscar-pipeline-0 -n pvbesscar --tail=100
```bash

### Exec en Pod

```bash
kubectl exec -it pvbesscar-pipeline-0 -n pvbesscar -- bash
```bash

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
```bash

---

## 💾 Persistent Storage

### MongoDB Storage

```yaml
PVC: mongodb-pvc
Size: 10Gi
AccessMode: ReadWriteOnce
Mounts: /data/db
```bash

### Pipeline Data

```yaml
PVC: pvbesscar-data-pvc
Size: 20Gi
AccessMode: ReadWriteOnce
Mounts: /app/data
```bash

### Pipeline Outputs

```yaml
PVC: pvbesscar-outputs-pvc
Size: 50Gi
AccessMode: ReadWriteOnce
Mounts: /app/outputs
```bash

---

## 🧪 Health Checks

### MongoDB Health Checks

```yaml
Liveness:
  Command: mongosh --eval "db.adminCommand('ping')"
  Initial Delay: 30s
  Period: 10s
```bash

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
```bash

---

## 🚀 Deployment Pipeline

### Paso 1: Build Image

```bash
docker build -t pvbesscar:latest .
```bash

### Paso 2: Push a Registry

```bash
docker tag pvbesscar:latest myregistry/pvbesscar:latest
docker push myregistry/pvbesscar:latest
```bash

### Paso 3: Deploy a K8s

```bash
kubectl apply -f k8s-deployment.yaml
```bash

### Paso 4: Verificar

```bash
kubectl get pods -n pvbesscar
kubectl logs -n pvbesscar -f
```bash

---

## 🔧 Troubleshooting

### Pods no inician

```bash
kubectl describe pod pvbesscar-pipeline-0 -n pvbesscar
kubectl logs pvbesscar-pipeline-0 -n pvbesscar
```bash

### MongoDB no conecta

```bash
# Verificar service
kubectl get svc mongodb -n pvbesscar

# Verificar pod
kubectl logs mongodb-0 -n pvbesscar

# Testear conexión
kubectl exec -it pvbesscar-pipeline-0 -n pvbesscar -- \
  mongosh --uri "mongodb://admin:pvbesscar2026@mongodb:27017/pvbesscar"
```bash

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
```bash

### Ingress no funciona

```bash
# Verificar ingress controller
kubectl get ingress -n pvbesscar
kubectl describe ingress pvbesscar-ingress -n pvbesscar

# Agregar hosts entry
echo "127.0.0.1 pvbesscar.local" >> /etc/hosts
```bash

---

## 📊 Comandos Útiles

### Cluster Info

```bash
kubectl cluster-info
kubectl get nodes
kubectl top nodes
```bash

### Namespace

```bash
kubectl get ns
kubectl describe ns pvbesscar
```bash

### Resources

```bash
kubectl get all -n pvbesscar
kubectl get pods,svc,pvc,deploy -n pvbesscar
```bash

### Events

```bash
kubectl get events -n pvbesscar
kubectl get events -n pvbesscar --sort-by='.lastTimestamp'
```bash

### Resource Usage

```bash
kubectl top pods -n pvbesscar
kubectl top nodes
kubectl describe node
```bash

---

## 🔄 Updates & Rolling Deployment

### Update Image

```bash
kubectl set image deployment/pvbesscar-pipeline \
  pipeline=pvbesscar:v2 -n pvbesscar

# Verificar rollout
kubectl rollout status deployment/pvbesscar-pipeline -n pvbesscar
```bash

### Rollback

```bash
kubectl rollout undo deployment/pvbesscar-pipeline -n pvbesscar
```bash

### History

```bash
kubectl rollout history deployment/pvbesscar-pipeline -n pvbesscar
```bash

---

## 🌍 Multi-Region Deployment

### Replicar en múltiples clusters

```bash
for cluster in cluster1 cluster2 cluster3; do
  kubectl --context=$cluster apply -f k8s-deployment.yaml
done
```bash

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
```bash

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
