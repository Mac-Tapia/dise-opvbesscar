# Validación de Datos de Vehículos - SAC v5.2
**Fecha:** 2026-02-13  
**Autor:** GitHub Copilot  
**Estado:** ✅ CORRECCIONES IMPLEMENTADAS

---

## 📊 Hallazgos Principales

### **Terminología Corregida**
**Observación del usuario:** "no hay taxis son mototaxis"  
**Traducción:** "there are no taxis, they are mototaxis"

**Implicación:** Todos los vehículos en Iquitos son mototaxis (motorcycle-based), solo se diferencian por uso:
- **MOTO**: Motocicletas personales (motos)
- **MOTOTAXI**: Motocicletas de servicio de taxi (mototaxis)

Ambos son "mototaxis" en esencia, pero con roles distintos.

---

## 🔍 Verificación de Datos (CSV)

### **Archivo:** `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`

**Estructura Real (no simulada):**
```
Sockets 0-29:   MOTO       (30 sockets) ← 15 chargers × 2 sockets
Sockets 30-37:  MOTOTAXI   (8 sockets)  ← 4 chargers × 2 sockets
─────────────────────────────────────────────────────────────
TOTAL:          38 sockets = 19 chargers × 2 sockets
```

**Columnas de Energía (por tipo):**
- `ev_energia_motos_kwh`: Energía EV para vehículos MOTO
- `ev_energia_mototaxis_kwh`: Energía EV para vehículos MOTOTAXI

**Columnas de CO₂ (por tipo):**
- `co2_reduccion_motos_kg`: Reducción CO₂ para motos
- `co2_reduccion_mototaxis_kg`: Reducción CO₂ para mototaxis

---

## 🔧 Correcciones Implementadas

### **1. Distribución de Sockets**
**Antes (INCORRECTO - simulado):**
```python
for vehicle_type in ['moto', 'taxi']:
    n_vehicles = 270 if vehicle_type == 'moto' else 39  # ❌ Hardcoded, no validado
```

**Después (CORRECTO - datos reales):**
```python
class RealOE2Environment(Env):
    MOTO_SOCKETS      = 30    # Sockets 0-29 (15 chargers)
    MOTOTAXI_SOCKETS  = 8     # Sockets 30-37 (4 chargers)

# En step():
n_moto_at_level = int(self.MOTO_SOCKETS * ...)       # Basado en 30 sockets
n_mototaxi_at_level = int(self.MOTOTAXI_SOCKETS * ...) # Basado en 8 sockets
```

### **2. Nomenclatura Corregida**

**Variable anterior:**
```python
self.episode_taxis_10_max    # ❌ "taxa" incorrecto
self.episode_taxis_20_max
# ... etc
```

**Variable actualizada:**
```python
self.episode_mototaxis_10_max    # ✅ "mototaxi" correcto
self.episode_mototaxis_20_max
# ... etc
```

### **3. Mensajes de Resumen del Episodio**

**Antes:**
```
Taxis @ SOC: 10%=X 20%=Y ...  # ❌ Llamados "Taxis"
```

**Después:**
```
Mototaxis @ SOC: 10%=X 20%=Y ...  # ✅ Llamados "Mototaxis"
```

---

## ✅ Validaciones Realizadas

### **Datos del CSV Confirmados:**
- ✓ 8,760 horas de datos (1 año completo)
- ✓ 38 sockets (socket_000 hasta socket_037)
- ✓ Dos tipos de vehículos: MOTO (0-29) y MOTOTAXI (30-37)
- ✓ Columnas de energía y CO₂ segregadas por tipo
- ✓ Métricas horarias consistentes

### **Cambios en SAC (train_sac_multiobjetivo.py):**
- ✓ Clase `RealOE2Environment`: Constantes MOTO_SOCKETS=30, MOTOTAXI_SOCKETS=8
- ✓ Inicialización (`__init__`): Variables renombradas a `episode_mototaxis_*`
- ✓ Reset (`reset()`): Reinicios corregidos a mototaxis
- ✓ Step (`step()`): Lógica de tracking basada en sockets reales
- ✓ Resumen de episodio: Imprime "Mototaxis @ SOC" en lugar de "Taxis @ SOC"

### **Sintaxis Python:**
✅ Sin errores de compilación

---

## 📈 Impacto en Resultados

El SAC ahora:
1. **Rastrea vehículos con distribución real** (30 motos + 8 mototaxis)
2. **Usa terminología correcta** (mototaxis, no taxis)
3. **Mantiene consistencia con PPO/A2C** (misma estructura de datos)
4. **Se basa en datos CSV verificados**, no simulación hardcoded

---

## 🔗 Archivos Referenciados

- **Datos:** [chargers_ev_ano_2024_v3.csv](data/oe2/chargers/chargers_ev_ano_2024_v3.csv) (8,760 filas × 475 columnas)
- **Código SAC:** [train_sac_multiobjetivo.py](scripts/train/train_sac_multiobjetivo.py) (líneas 450, 514-520, 530-546, 614-658, 678)
- **Especificación v5.2:** 19 chargers × 2 sockets = 38 sockets totales

---

## 🚀 Próximos Pasos

Reanudar entrenamiento SAC con:
- ✅ Datos de vehículos corregidos (30 MOTO + 8 MOTOTAXI)
- ✅ Nomenclatura consistente con "mototaxi"
- ✅ Métricas de seguimiento validadas contra CSV
- Comparativa final: SAC vs PPO vs A2C con datos correctos
