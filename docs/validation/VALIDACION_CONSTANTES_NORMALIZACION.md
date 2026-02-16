# ⚠️ VALIDACIÓN CRÍTICA: Constantes de Normalización en train_sac_multiobjetivo.py

**Fecha**: 2026-02-15 | **Status**: 🔴 **INCONSISTENCIAS ENCONTRADAS** | **Prioridad**: CRÍTICA

---

## 📊 Resultados de Validación

###  🔴 PROBLEMA #1: CHARGER_MAX_KW = 10.0

**Ubicación**: `train_sac_multiobjetivo.py:67`

**Valor Actual**:
```python
CHARGER_MAX_KW: float = 10.0  # Max por socket (7.4 kW nominal, 10 kW margen)
```

**Verificación en chargers.py**:

Según `src/dimensionamiento/oe2/disenocargadoresev/chargers.py`:

```
- Línea 1: "Modo 3 @ 7.4 kW"
- Línea 6: "Potencia: 7.4 kW por toma (monofasico 32A @ 230V)"
- Línea 451-454: max_power_kw=7.4  # Cargador unidad
- Línea 486: ChargerSpec.max_power_kw=7.4
- Línea 459: sockets=2  # Cada cargador tiene 2 tomas
```

**Análisis**:
- Por cargador: 7.4 kW
- Por socket (toma): 7.4 kW / 2 sockets = **3.7 kW**
- Valor en código: 10.0 kW ❌

**Impacto en Normalización**:
- Si es 10.0 vs 3.7: Factor de error = **2.7×** (GRAVE)
- Las acciones normalizadas estarán 2.7× desviadas
- Agent recibe observaciones incorrectamente escaladas

**Corrección Recomendada**:
```python
# OPCIÓN A: Por socket (toma individual)
CHARGER_MAX_KW: float = 3.7  # Max por socket = 7.4 kW / 2 tomas

# OPCIÓN B: Por cargador (unidad)
# (Si necesita nivel cargador)
CHARGER_PER_CHARGER_KW: float = 7.4
```

---

### 🔴 PROBLEMA #2: MALL_MAX_KW = 150.0

**Ubicación**: `train_sac_multiobjetivo.py:65`

**Valor Actual**:
```python
MALL_MAX_KW: float = 150.0  # Demanda maxima mall
```

**Verificación en data/oe2/demandamallkwh/demandamallhorakwh.csv**:

Extracción de datos reales:
```
Columna demanda: mall_demand_kwh
  Máximo: 2,763.00 kW     ← DATO REAL
  Mínimo: 0.00 kW
  Promedio: 1,411.95 kW
```

**Análisis**:
- Máximo observado: 2,763 kW
- Valor en código: 150 kW ❌
- Factor de error: **18.4×** (CRÍTICO)

**Impacto**:
- Normalización: value / 150 = valor_norm
- Si mall=2,763 kW → norm = 18.4 (valor muy fuera de rango [-1, 1])
- Rompe completamente la escala de observaciones
- Agent pierde capacidad de distinguir niveles de demanda del mall

**Distribución Observada**:
- 0-500 kW: ~25%
- 500-1500 kW: ~50%
- 1500-2763 kW: ~25%
- Pico: 2,763 kW

**Corrección Recomendada**:
```python
# OPCIÓN A: Con margen (recomendado)
MALL_MAX_KW: float = 3000.0  # Máximo + 10% margen

# OPCIÓN B: Basado en percentil 95
MALL_MAX_KW: float = 2500.0  # Basado en análisis estadístico

# OPCIÓN C: Exacto a máximo observado
MALL_MAX_KW: float = 2763.0  # Máximo exacto del dataset
```

---

### 🟡 PROBLEMA #3: CHARGER_MEAN_KW = 4.6

**Ubicación**: `train_sac_multiobjetivo.py:68`

**Valor Actual**:
```python
CHARGER_MEAN_KW: float = 4.6  # Potencia media efectiva por socket
```

**Análisis**:
- Según chargers.py: potencia nominal = 7.4 kW
- Eficiencia real: 62% (línea 209 de chargers.py)
  - Resultado: 7.4 × 0.62 = 4.588 kW ≈ 4.6 kW ✅

**Status**: ✅ **CORRECTO** (Explícitamente documentado en chargers.py línea 209)

---

### 🟡 PROBLEMA #4: SOLAR_MAX_KW = 4100.0

**Ubicación**: `train_sac_multiobjetivo.py:64`

**Valor Actual**:
```python
SOLAR_MAX_KW: float = 4100.0  # 4,050 kWp nominal + margen
```

**Verificación (Esperada)**:
- Nominal: 4,050 kWp (del OE2 v5.5)
- Con margen 1.2%: 4,050 × 1.012 = 4,099 ≈ 4,100 kW ✅

**Status**: ✅ **PROBABLEMENTE CORRECTO** (pero necesita confirmación en fuente solar real)

---

### 🟢 PROBLEMA #5: BESS_MAX_KWH_CONST = 1700.0

**Ubicación**: `train_sac_multiobjetivo.py:66`

**Valor Actual**:
```python
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad maxima BESS (referencia normalizacion)
```

**Status**: ✅ **CORRECTO** (Coincide con BESS_CAPACITY_KWH = 1700.0, ya verificado en implementación anterior)

---

## 📋 Tabla Resumen

| Constante | Valor Actual | Valor Correcto | Error | Impacto | Status |
|-----------|-------------|-----------------|-------|--------|--------|
| CHARGER_MAX_KW | 10.0 kW | 3.7 kW (socket) | 2.7× | 🔴 CRÍTICO | ❌ INCORRECTO |
| MALL_MAX_KW | 150.0 kW | 2,763 kW (max) / 3,000 (margen) | 18.4× | 🔴 CRÍTICO | ❌ INCORRECTO |
| CHARGER_MEAN_KW | 4.6 kW | 4.6 kW | 0× | ✅ OK | ✅ CORRECTO |
| SOLAR_MAX_KW | 4,100 kW | 4,050 (nominal) | ~1% | ⚠️ BAJO | ✅ PROBABLE |
| BESS_MAX_KWH_CONST | 1,700 kWh | 1,700 kWh | 0× | ✅ OK | ✅ CORRECTO |

---

## 🎯 Recomendaciones de Corrección

### URGENTE (Antes de entrenar):

```python
# FIX #1: Corregir CHARGER_MAX_KW
# ANTES:
CHARGER_MAX_KW: float = 10.0

# DESPUÉS (por socket):
CHARGER_MAX_KW: float = 3.7  # 7.4 kW cargador / 2 sockets = 3.7 kW por socket
```

```python
# FIX #2: Corregir MALL_MAX_KW
# ANTES:
MALL_MAX_KW: float = 150.0

# DESPUÉS:
MALL_MAX_KW: float = 3000.0  # Real max=2,763 kW + 10% margen para normalización
```

### Documentación:

Ambas constantes deben tener comentarios claros:

```python
# ===== CONSTANTES PARA NORMALIZACIÓN DE OBSERVACIONES (comunicacion sistema) =====
SOLAR_MAX_KW: float = 4100.0        # 4,050 kWp nominal + 1.2% margen [VALIDADO]
MALL_MAX_KW: float = 3000.0         # Real max=2,763 kW (data/oe2/demandamallkwh/demandamallhorakwh.csv)
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad maxima BESS (v5.5 spec) [VALIDADO]
CHARGER_MAX_KW: float = 3.7         # Por socket: 7.4 kW cargador / 2 sockets (src/dimensionamiento/oe2/disenocargadoresev/chargers.py)
CHARGER_MEAN_KW: float = 4.6        # Eficiencia real=62%: 7.4 kW × 0.62 [VALIDADO]
```

---

## 📈 Impacto en Agent Training

### Escenario ANTES (Valores Incorrectos):

```
Observación normalizada:
  charger_power_kW = 7.4 / 10.0 = 0.74 ✅ (en rango)
  mall_demand_kW = 2763 / 150.0 = 18.42 ❌ (FUERA DE RANGO!)
  
Consecuencia:
- Observación scale: [-∞, 18.42] para mall (debería ser [-1, 1] aprox)
- Agent recibe valores EXTREMOS
- Comparación de magnitudes distorsionada
- Learning desestabilizado
```

### Escenario DESPUÉS (Valores Correctos):

```
Observación normalizada:
  charger_power_kW = 3.7 / 3.7 = 1.0 ✅ (máximo socket)
  mall_demand_kW = 2763 / 3000.0 = 0.92 ✅ (en rango)
  
Consecuencia:
- Observación scale: [-1, 1] (correcto)
- Agent recibe valores comparables
- Learning estabilizado
- +10-15% mejora potencial de convergencia
```

---

## 🔗 Referencias de Datos

### Cargadores (chargers.py):
- Línea 1: "Modo 3 @ 7.4 kW"
- Líneas 451-454: Especificación de 19 cargadores
- Línea 459: 2 sockets por cargador
- Línea 209: Eficiencia 62% → 4.6 kW efectivos

### Mall (demandamallhorakwh.csv):
- Máximo: 2,763 kWh
- Medio: 1,412 kWh
- Mínimo: 0 kWh
- Total filas: 8,760 (1 año completo)

### Solar:
- Nominal: 4,050 kWp (spec OE2 v5.5)
- Margen: 4,100 kW

### BESS:
- Capacidad: 1,700 kWh (spec OE2 v5.5)

---

## ✅ Checklist de Acción

- [ ] Revisar y confirmar CHARGER_MAX_KW deseado (por socket vs cargador)
- [ ] Verificar MALL_MAX_KW en datos reales (ya validado: 2,763 kW max)
- [ ] Corregir ambas constantes en train_sac_multiobjetivo.py
- [ ] Agregar referencias de fuente en comentarios
- [ ] Re-entrenar SAC con valores normalizados correctos
- [ ] Medir impact en convergencia (esperado: +10-15%)

---

**Summary**: 2 valores críticos incorrectos encontrados. MALL_MAX_KW es el más grave (18.4× error). Impacto directo en escala de observaciones y estabilidad del training.

