# 📖 Guía de Funcionamiento - PVBESSCAR API

## 🎯 ¿Qué es PVBESSCAR?

**PVBESSCAR** es un sistema de **gestión inteligente de energía en edificios**
usando **Inteligencia Artificial**:

- 📊 **Monitorea** consumo de energía
- ☀️ **Optimiza** generación solar
- 🔋 **Gestiona** baterías de almacenamiento
- 💰 **Minimiza** costos energéticos
- 🤖 **Aprende** patrones de consumo con RL (Reinforcement Learning)

---

## 🏗️ Arquitectura del Sistema

<!-- markdownlint-disable MD013 -->
```text
┌─────────────────────────────────────────────────────────┐
│                    PVBESSCAR SYSTEM                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐  ┌────────────┐  │
│  │   FastAPI    │───→│   MongoDB    │  │ ML Models  │  │
│  │  (API REST)  │    │  (Database)  │ ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🚀 Cómo Funciona en 5 Pasos

### 1️⃣ **Sistema Recibe Datos Actuales**

<!-- markdownlint-disable MD013 -->
```text
Entrada (cada 5 minutos):
├─ Consumo del edificio (kW)
├─ Generación solar (kW)
├─ Batería disponible (kWh)
└─ Precio de electricidad (€/kWh)
```bash
<!-- markdownlint-enable MD013 -->

### 2️⃣ **Modelo ML Predice Futuro**

<!-- markdownlint-disable MD013 -->
```text
Análisis:
├─ ¿Qué consumo habrá en 1 hora?
├─ ¿Cuánto sol habrá?
├─ ¿Cuál es el precio más bajo hoy?
└─ ¿Cuánta batería debería guar...
```

[Ver código completo en GitHub]text
Decisión (optimizada por IA):
├─ ¿Cargar batería? (Sí/No/Parcial)
├─ ¿Usar solar? (100%)
├─ ¿Comprar electricidad a red? (Sí/No)
└─ Acción: CHARGE / DISCHARGE / IDLE
```bash
<!-- markdownlint-enable MD013 -->

### 4️⃣ **Sistema Ejecuta Acciones**

<!-- markdownlint-disable MD013 -->
```text
Ejecución:
├─ Activa inversores
├─ Controla cargadores
└─ Registra cambios en tiempo real
```bash
<!-- markdownlint-enable MD013 -->

### 5️⃣ **Resultado: Ahorro Financiero**

<!-- markdownlint-disable MD013 -->
```text
Salida:
├─ ✅ Costo total reducido
├─ ✅ Emisiones CO2 minimizad...
```

[Ver código completo en GitHub]bash
GET /health

# Respuesta:
{
  "status": "healthy",
  "timestamp": "2026-01-20T11:08:09.687815",
  "service": "PVBESSCAR API"
}
```bash
<!-- markdownlint-enable MD013 -->

### 2. **Estado del Sistema** 📊

Obtiene el estado actual de todos los componentes

<!-- markdownlint-disable MD013 -->
```bash
GET /api/status

# Respuesta: (2)
{
  "system": "PVBESSCAR",
  "status": "operational",
  "timestamp": "2026-01-20T11:08:09",
  "components": {
    "database": "connected",
    "ml_models": "loaded",
    "energy_controller": "active"
  ...
```

[Ver código completo en GitHub]bash
GET /api/metrics

# Respuesta: (3)
{
  "timestamp": "2026-01-20T11:08:09",
  "building_load_kw": 45.2,          # Consumo edificio
  "pv_generation_kw": 12.5,          # Generación solar
  "battery_soc": 87.3,               # Batería (porcentaje 0-100)
  "grid_import_kw": 32.7,            # Importación de red
  "total_cost": 156.45               # Costo acumulado (€)
}
```bash
<!-- markdownlint-enable MD013 -->

### 4. **Ejecutar Acción** 🎮

Envía comando al controlador de energía

<!-- markdownlint-disable MD013 -->
```bash
POST /api/control

# Parámetros requeridos:
{
  "action": "charge",    # "charge", "discharge", "idle"
  "value": 5.0           # Potencia en kW (opcional)
}

# Respuesta: (4)
{
  "action": "charge",
  "value": 5.0,
  "timestamp": "2026-01-20T11:08:...
```

[Ver código completo en GitHub]bash
curl http://localhost:8000/health

# ✅ Respuesta:
# {"status": "healthy", ...}
```bash
<!-- markdownlint-enable MD013 -->

#### **PASO 2: Obtener estado actual**

<!-- markdownlint-disable MD013 -->
```bash
curl http://localhost:8000/api/status

# El sistema reporta:
# - Database: ✅ conectada
# - ML Models: ✅ cargados
# - Controller: ✅ activo
```bash
<!-- markdownlint-enable MD013 -->

#### **PASO 3: Leer métricas de sensores**

<!-- markdownlint-disable MD013 -->
```bash
curl http:...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### **PASO 4: Análisis IA**

El modelo ML analiza:

- ❓ "¿Vendrán más nubes?"
- ❓ "¿A qué hora baja la demanda?"
- ❓ "¿Cuál es el horario peak?"
- ❓ "¿Qué batería necesito guardar?"

#### **PASO 5: Decisión del Controlador**

<!-- markdownlint-disable MD013 -->
```text
🤖 IA decide: "CARGAR batería ahora"

Razón:
- ✅ Solar disponible: 12.5 kW
- ✅ Batería no llena: 87.3%
- ✅ En 2 horas habrá nubes
- ✅ A las 18h subirá demanda (peak)
- ✅ Cargar ahora = ahorrar €5 después
```bash
<!-- markdownlint-enable MD013 -->

#### **PASO 6: Ejecutar acción**

<!-- markdownlint-disable MD013 -->
```bash
curl -X POST http://localhost:8000/api/control \
  -H "Content-Type: applic...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### **PASO 7: Sistema ejecuta**

<!-- markdownlint-disable MD013 -->
```text
⚡ Acciones en tiempo real:
├─ Inversor se activa
├─ Cargador batería ON → 5.0 kW
├─ Consumo solar: 12.5 kW
│  ├─ 5.0 kW → Batería (carga)
│  ├─ 7.5 kW → Edificio (consumo)
│  └─ 0 kW (equilibrado, sin red)
└─ Resultado: ✅ No pagamos a la red en este período
```bash
<!-- markdownlint-enable MD013 -->

#### **PASO 8: 2 Horas Después...**

<!-- markdownlint-disable MD013 -->
```text
☁️ Llegaron las n...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### **PASO 9: Verificar Resultado**

<!-- markdownlint-disable MD013 -->
```bash
curl http://localhost:8000/api/metrics

# Métricas finales:
{
  "building_load_kw": 48.0,
  "pv_generation_kw": 2.3,
  "battery_soc": 92.1,           # Bajó de 95%
  "grid_import_kw": 35.7,        # Bajó de 32.7
  "total_cost": 159.95            # Subió +€3.50 (pero sin pico)
}
```bash
<!-- markdownlint-enable MD013 -->

---

## 📋 Valores que Debes Proporcionar

<!-- markdownlint-disable MD013 -->...
```

[Ver código completo en GitHub]python
# Simulación en 1 hora (12 mediciones)

 Hora | Consumo | Solar | Batería | Acción | Costo 
 ------ | --------- | ------- | --------- | -------------- | ------- 
 11:00 | 45 kW | 85 kW | 60% | CHARGE | €8 
 11:05 | 44 kW | 82 kW | 62% | CHARGE | €8 
 11:10 | 46 kW | 88 kW | 65% | CHARGE | €8 
 11:15 | 45 kW | 90 kW | 70% | CHARGE | €8 
 11:20 | 47 kW | 85 kW | 75% | CHARGE | €8 
 11:25 | 45 kW | 80 kW | 80% | CHARGE | €8 
 11:30 | 46 kW | 75 kW | 85% | IDLE | €8 
 11:35 | 45 kW | 70 kW | 90% | IDLE | €8 
 11:40 | 47 kW | 65 kW | 90% | IDLE | €9 
 11:45 | 48 kW | 60 kW | 90% | DISCHARGE | €8 
 11:50 | 46 kW | 58 kW | 88% | DISCHARGE | €8 
 11:55 | 45 kW | 55 kW | 86% | IDLE | €8 

📊 RESULTADO: Costo hora = €99 (sin IA sería €105)
💰 AHORRO: €6 por hora = €144 por día
```bash
<!-- markdownlint-enable MD013 -->

### **Ejemplo 2: Día Nublado (Invierno)**

<!-- markdownlint-disable MD013 -->
```python
 Hora | Consumo | Solar | Batería | Acción | Costo 
 ------ | --------- | ------- | --------- | -------------- | ------- 
 10:00 | 52 kW | 8 kW | 70% | IDLE | €11 
 10:05 | 51 kW | 6 kW | 70% | IDLE | €11 
 10:10 | 53 kW | 5 kW | 70% | DISCHARGE | €10 
 10:15 | 52 kW | 4 kW ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🔄 Ciclo de Operación Típico

<!-- markdownlint-disable MD013 -->
```text
BUCLE CONTINUO (cada 5 minutos):

1. LEER SENSORES
   ├─ Smart Meter: Consumo = ?
   ├─ Inversor Solar: Generación = ?
   ├─ BMS: Batería = ?%
   └─ Grid: Precio = ?€

2. PREDICCIÓN (5-24 horas)
   ├─ ¿Consumo futuro?
   ├─ ¿Solar futuro?
   └─ ¿Precio futuro?

3. OPTIMIZACIÓN (RL Agent)
   ├─ Evaluar 100 escenarios
   ├─ Calcular recompensa (ahorro €)
   └─ Elegir mejor acción

4. EJECUTAR
   ├─ ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🧪 Prueba la API Ahora

### **Opción 1: Con cURL (Terminal)**

<!-- markdownlint-disable MD013 -->
```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Ver estado
curl http://localhost:8000/api/status

# 3. Leer métricas
curl http://localhost:8000/api/metrics

# 4. Enviar comando
curl -X POST http://localhost:8000/api/control \
  -H "Content-Type: application/json" \
  -d '{"action":"charge","value":10}'
```bash
<!-- markdownlint-enable MD013 -->

### **Opción 2: Con Swagger (Navegador)**
...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### **Opción 3: Con Python (Script)**

<!-- markdownlint-disable MD013 -->
```python
import requests
import json

# URL base
BASE = "http://localhost:8000"

# 1. Health check (2)
resp = requests.get(f"{BASE}/health")
print("✅ Sistema:", resp.json()["status"])

# 2. Leer métricas
resp = requests.get(f"{BASE}/api/metrics")
data = resp.json()
print(f"📊 Consumo: {data['building_load_kw']} kW")
print(f"☀️ Solar: {data['pv_generation_kw']} kW")
print(f"🔋 Batería: {data['battery_soc']}%"...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 📊 Dashboard de Monitoreo

Para ver todo en tiempo real:

<!-- markdownlint-disable MD013 -->
```text
DOCKER MANAGER: http://localhost:5000
├─ Estado de contenedores
├─ Logs en vivo
└─ Botones de control

MONGO ADMIN: http://localhost:8081
├─ Base de datos
├─ Colecciones
└─ Documentos registrados

SWAGGER API: http://localhost:8000/docs
├─ Todos los endpoints
├─ Documentación interactiva
└─ Pruebas en vivo
```bash
<!-- markdownlint-enable MD013 -->

---

<!-- markdownlint-disable MD013 -->
## 🎓 Resumen | Concepto | Explicación | | ---------- | ------------- | | **PVBESSCAR** | Sistema IA para... | | **Entrada** | Sensores (consumo, solar,... | | **Proceso** | ML predice futuro + RL optimiza decisión | | **Salida** | Acción (cargar/descargar/esperar) | | **Resultado** | Menor costo +... | | **API** | FastAPI + MongoDB + ML Models | | **Ejecución** | Ciclo cada 5 minutos (288 veces/día) | | **Ahorro** | ~€100/día por edificio = €36,500/año | **¡Listo! Ahora entiendes cómo funciona el sistema completo.**
