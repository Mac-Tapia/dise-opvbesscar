# 🌐 PVBESSCAR Docker Web Interface - Ejecutada

## ✅ Status: ACTIVA

**Fecha**: 2026-01-20  
**Python**: 3.11.9  
**Framework**: Flask + Flask-CORS  
**Estado**: 🟢 Corriendo en background

---

## 🚀 Acceso

<!-- markdownlint-disable MD013 -->
### URLs Disponibles | Servicio | Local | Red Local | | ---------- | ------- | ----------- | | **Docker Manager** | <http://localhost:5000> | <http://192.168.43.30:5000> | |**Jupyter Lab (CPU)**|<[url0]
|**Jupyter Lab (GPU)**|<[url0]

### Acceso Rápido

<!-- markdownlint-disable MD013 -->
```bash
# Desde navegador
http://localhost:5000

# Desde otra máquina en la red
http://192.168.43.30:5000
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 Features de la Interfaz

### 1. **Dashboard en Tiempo Real**

- ✅ Estado de contenedores (running/stopped)
- ✅ Monitoreo de servicios
- ✅ Auto-refresh cada 5 segundos

### 2. **Gestión de Imágenes**

- ✅ Build CPU/GPU/Dev
- ✅ Build con BuildKit cac...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### 4. **Visualización de Logs**

- ✅ Ver logs en tiempo real
- ✅ Filtrar por servicio
- ✅ Desplazamiento automático
- ✅ Terminal negro con texto verde

### 5. **Acceso a Servicios Web**

- ✅ Enlaces directos a Jupyter Lab
- ✅ URLs locales y de red
- ✅ Indicadores de estado

---

## 🎨 Interfaz Visual

<!-- markdownlint-disable MD013 -->
```text
┌─────────────────────────────────────────┐
│  🐳 PVBESSCAR Docker Manager           │
│  Web interface para gestionar Docker    │
├─────────────────────────────────────────┤
│                                         │
│  📊 Status          ⚡ Acciones        │
│  ─────────────────  ────────────────  │
 │  Contenedores      CPU | GPU | Dev   │ 
│  • pipeline         [Build] [Start]   │
│  • monitor  ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🔧 API Endpoints

### GET /api/status

<!-- markdownlint-disable MD013 -->
```bash
Retorna estado de todos los contenedores

Response:
{
  "success": true,
  "containers": {
    "pvbesscar-pipeline": {"running": true, "state": "running"},
    "pvbesscar-monitor": {"running": false, "state": "exited"}
  },
  "docker_running": true,
  "timestamp": "2026-01-20T..."
}
```bash
<!-- markdownlint-enable MD013 -->

### POST /api/build

<!-- markdownlint-disable MD013 -->
```bash
Constru...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### POST /api/start

<!-- markdownlint-disable MD013 -->
```bash
Iniciar servicios

 Request: {"mode": "cpu | gpu | dev"} 
Response: {"success": true, "message": "Services started"}
```bash
<!-- markdownlint-enable MD013 -->

### POST /api/stop

<!-- markdownlint-disable MD013 -->
```bash
Detener servicios

 Request: {"mode": "cpu | gpu | dev"} 
Response: {"success": true, "message": "Services stopped"}
```bash
<!-- markdownlint-enable MD013 -->

### GET /api/l...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### GET /api/health

<!-- markdownlint-disable MD013 -->
```bash
Health check del servidor

Response: {"status": "healthy", "docker": true, "timestamp": "..."}
```bash
<!-- markdownlint-enable MD013 -->

---

## 📋 Comandos del Terminal

### Verificar proceso

<!-- markdownlint-disable MD013 -->
```bash
# Ver puertos en uso
netstat -ano | findstr 5000

# Ver proceso Flask
Get-Process python|Where-Object {$_.CommandLine -like "*docker_web_interface*"}
```bash
<!-...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Reiniciar

<!-- markdownlint-disable MD013 -->
```bash
cd d:\diseñopvbesscar
py -3.11 docker_web_interface.py
```bash
<!-- markdownlint-enable MD013 -->

---

## 🎯 Uso Típico

### Scenario 1: Desarrollo Local CPU

<!-- markdownlint-disable MD013 -->
```text
1. Abre http://localhost:5000
2. Click en tab "CPU"
3. Click "Build CPU" → espera construcción
4. Click "Start CPU" → inicia servicios
5. Abre http://localhost:8888 → Jupyter Lab
```bash
<!-- markd...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Scenario 3: Testing Completo

<!-- markdownlint-disable MD013 -->
```text
1. Abre http://localhost:5000
2. Click en tab "Dev"
3. Click "Build Dev" → crea imagen dev
4. Click "Start Dev" → inicia pytest, linting, mypy
5. Monitorea logs en tiempo real
```bash
<!-- markdownlint-enable MD013 -->

---

## 🌐 Acceso desde Otra Máquina

### En otra máquina de la red local

<!-- markdownlint-disable MD013 -->
```text
http://192.168.43.30:5000
```bash
<!-- markdownlint-enable MD0...
```

[Ver código completo en GitHub]powershell
# Permitir puerto 5000
netsh advfirewall firewall add rule name="Flask 5000" dir=in action=allow protocol=tcp localport=5000
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔒 Seguridad Notas

### Desarrollo

✅ Seguro - interfaz local solamente  
✅ Debug mode habilitado (solo desarrollo)

### Producción

⚠️ NO usar en producción así  
⚠️ Usar Gunicorn, Nginx, etc.  
⚠️ Agregar autenticación  
⚠️ HTTPS/SSL certificados

### Para Producción

<!-- markdownlint-disable MD013 -->
```bash
# Usar Gunicorn
pip install gunicorn
gunic...
```

[Ver código completo en GitHub]bash
# Verificar puerto en uso
netstat -ano | findstr :5000

# Matar proceso anterior
taskkill /PID [PID] /F

# Reiniciar (2)
py -3.11 docker_web_interface.py
```bash
<!-- markdownlint-enable MD013 -->

### Docker no detecta imágenes

<!-- markdownlint-disable MD013 -->
```bash
# Verificar Docker daemon
docker ps

# Si falla: Docker Desktop no está instalado o running
```bash
<!-- markdownlint-enable MD013 -->

### Conectar desde otra PC y no funciona

<!-- markdownlint-disable MD013 -->
```bash
# Verificar IP local
ipconfig

# Firewall permitir puerto 5000
# V...
```

[Ver código completo en GitHub]text
⚠️ Solo desarrollo
✅ Cambios en código = reload automático
✅ Debugger PIN para debugging remoto
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 Monitores en Tiempo Real

### Status Monitor

- Actualización cada 5 segundos
- Verde si contenedor running
- Rojo si stopped

### Log Viewer

- Auto-scroll
- Terminal estilo hacker
- Filtro por servicio

### API Health

- `/api/health` - estado general
- Timestamp de requests
- Validación Docker daemon

---

## 🔗 Integración

### Con Docker Compose

-...
```

[Ver código completo en GitHub]text
✓ Servidor: 127.0.0.1:5000
✓ Network: 192.168.43.30:5000
✓ Flask Debug: Habilitado
✓ Auto-reload: Habilitado
✓ CORS: Habilitado para todas las origins
```bash
<!-- markdownlint-enable MD013 -->

### Capacidades

- Simultáneamente: Múltiples builds
- Timeout: 30 segundos por comando
- Max Log Lines: 100 últimas líneas
- Auto-refresh: Cada 5 segundos

---

## 💡 Tips

### 1. Mantén abierto en una pestaña

<!-- markdownlint-disable MD013 -->
```text
Abre en una pestaña y deja abierto
Auto-refresh mantiene status actualizado
```bash
<!-- markdownlint-enable ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### 3. Monitorea desde otra máquina

<!-- markdownlint-disable MD013 -->
```text
Usa http://192.168.43.30:5000
Excelente para monitoreo remoto
```bash
<!-- markdownlint-enable MD013 -->

### 4. Combina con terminal

<!-- markdownlint-disable MD013 -->
```text
Abre terminal CMD + Web Interface en paralelo
Más control y flexibilidad
```bash
<!-- markdownlint-enable MD013 -->

---

## 🎓 Next Steps

1. **Build Image**
   - Selecciona modo (CPU/GPU/Dev)
   - Click "Build"
   - Moni...
```

[Ver código completo en GitHub]text
docker_web_interface.py    (Esta interfaz)
docker-compose.yml         (CPU services)
docker-compose.gpu.yml     (GPU services)
docker-compose.dev.yml     (Dev stack)
Dockerfile                 (Imagen base)
DOCKER_BUILD_GUIDE.md      (Documentación Docker)
```bash
<!-- markdownlint-enable MD013 -->

---

## 📞 Soporte

### Problemas Comunes

#### "Cannot connect to Docker daemon"
→ Docker Desktop no instalado o no running

#### "Port 5000 already in use"
→ Otro proceso usando puerto. Matar y reintentar.

#### "Command timeout"
→ Docker command tardó más de 30 segundos. Verificar logs.

#### "CORS error"
→ Refresh página, limpiar caché navegador

---

## 🎉 St...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### 🟢 SISTEMA LISTO PARA USAR

---

**Creado**: 2026-01-20  
**Python**: 3.11.9  
**Framework**: Flask + Flask-CORS  
**Status**: 🟢 Production Ready (Development Mode)