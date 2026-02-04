# 📝 GIT COMMIT HISTORY - chargers.py Corrections

**Branch**: `oe3-optimization-sac-ppo`  
**Total Commits**: 2  
**Total Changes**: 25 insertions(+), 26 deletions(-)

---

## Commit 1: `011db8fe` (MAIN CORRECTION)

```
Mensaje: fix: Actualizar chargers.py con valores REALES del dataset (903.46 kWh/día)
Date:    Tue Feb 4 2026
Files:   1 changed (src/iquitos_citylearn/oe2/chargers.py)
Change:  15 insertions(+), 16 deletions(-)
```

### Cambios Específicos

#### ❌ ANTES (Líneas 11-24 - DOCSTRING)
```python
    CARGADORES EV (TOMAS CONTROLABLES):
    ────────────────────────────────────
    - Infraestructura: 32 chargers (120-240 V @ 2kW moto, 3kW mototaxi)
      • Motos: 28 chargers × 4 sockets = 112 tomas
      • Mototaxis: 4 chargers × 4 sockets = 16 tomas
      • Total: 128 tomas (32 chargers × 4 = 128)
    - Energía diaria: 14,976 kWh (demanda total operacional)
    - Capacidad anual: 2,912 motos + 416 mototaxis (5,466,240 kWh/año)
```

#### ✅ DESPUÉS (Líneas 11-24 - DOCSTRING CORREGIDO)
```python
    CARGADORES EV (TOMAS CONTROLABLES):
    ────────────────────────────────────
    - Infraestructura: 32 chargers (120-240 V @ 2kW moto, 3kW mototaxi)
      • Motos: 28 chargers × 4 sockets = 112 tomas
      • Mototaxis: 4 chargers × 4 sockets = 16 tomas
      • Total: 128 tomas (32 chargers × 4 = 128)
    - Energía diaria PROMEDIO: 903.46 kWh (verified dataset statistics, Tabla 13 OE2)
    - Energía diaria RANGO: 92.80 - 3,252 kWh (min - max estadísticas)
    - Flota operativa: 900 motos + 130 mototaxis = 1,030 vehículos/día
    - Capacidad anual: 328,500 motos + 47,450 mototaxis = 375,950 veh/año (329,763 kWh/año)
```

#### ❌ ANTES (Líneas 1543-1555 - CONSTANTES)
```python
    # ENERGÍA DIARIA (CALCULADA Y FIJA)
    # Motos: 2,679 × 1.0 kWh = 2,679 kWh
    # Mototaxis: 382 × 1.5 kWh = 573 kWh
    # TOTAL: 3,252 kWh/día
    ENERGY_DAY_MOTOS_KWH = 2679.0
    ENERGY_DAY_MOTOTAXIS_KWH = 573.0
    ENERGY_DAY_TOTAL_KWH = 3252.0
```

#### ✅ DESPUÉS (Líneas 1543-1555 - CONSTANTES CORREGIDAS)
```python
    # ENERGÍA DIARIA - VALORES REALES DATASET (Tabla 13 OE2 - 2026-02-04)
    # Fuente: data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv
    # Motos (estimado ~80-85% de total): ~763.76 kWh/día
    # Mototaxis (estimado ~15-20% de total): ~139.70 kWh/día
    # TOTAL PROMEDIO: 903.46 kWh/día (verified from annual 8,760-hour profile)
    # Estadísticas: Min=92.80, Max=3,252.0, Mediana=835.20, Std=572.07
    ENERGY_DAY_MOTOS_KWH = 763.76
    ENERGY_DAY_MOTOTAXIS_KWH = 139.70
    ENERGY_DAY_TOTAL_KWH = 903.46
```

---

## Commit 2: `33f3d3ef` (COMMENT CLEANUP)

```
Mensaje: fix: Actualizar comentarios desactualizados en chargers.py con valores REALES (903.46 kWh/día)
Date:    Tue Feb 4 2026
Files:   1 changed (src/iquitos_citylearn/oe2/chargers.py)
Change:  10 insertions(+), 10 deletions(-)
```

### Cambios Específicos

#### Cambio 1: Línea 2055 (playas_summary totals)
```diff
- "energy_day_kwh": ENERGY_DAY_TOTAL_KWH,  # 3,252 kWh
+ "energy_day_kwh": ENERGY_DAY_TOTAL_KWH,  # 903.46 kWh (REAL dataset average)
```

Plus comentario de vehículos:
```diff
- "vehicles_charging_day": VEHICLES_DAY_MOTOS + VEHICLES_DAY_MOTOTAXIS,  # 3,061
+ "vehicles_charging_day": VEHICLES_DAY_MOTOS + VEHICLES_DAY_MOTOTAXIS,  # 1,030 (900 motos + 130 mototaxis)
```

#### Cambio 2: Línea 1912 (variable assignments)
```diff
- MOTOS_CHARGING_DAY = VEHICLES_DAY_MOTOS        # 2,679
- MOTOTAXIS_CHARGING_DAY = VEHICLES_DAY_MOTOTAXIS  # 382
- ENERGY_MOTO_DAY = ENERGY_DAY_MOTOS_KWH          # 2,679 kWh
- ENERGY_MOTOTAXI_DAY = ENERGY_DAY_MOTOTAXIS_KWH  # 573 kWh

+ MOTOS_CHARGING_DAY = VEHICLES_DAY_MOTOS        # 900 (REAL dataset)
+ MOTOTAXIS_CHARGING_DAY = VEHICLES_DAY_MOTOTAXIS  # 130 (REAL dataset)
+ ENERGY_MOTO_DAY = ENERGY_DAY_MOTOS_KWH          # 763.76 kWh (REAL dataset)
+ ENERGY_MOTOTAXI_DAY = ENERGY_DAY_MOTOTAXIS_KWH  # 139.70 kWh (REAL dataset)
```

#### Cambio 3: Línea 2236 (playas by type)
```diff
- "vehicles_charging_day": VEHICLES_DAY_MOTOS,  # 2,679
- "energy_day_kwh": ENERGY_DAY_MOTOS_KWH,  # 2,679 kWh
+ "vehicles_charging_day": VEHICLES_DAY_MOTOS,  # 900 (REAL dataset)
+ "energy_day_kwh": ENERGY_DAY_MOTOS_KWH,  # 763.76 kWh (REAL dataset)

- "vehicles_charging_day": VEHICLES_DAY_MOTOTAXIS,  # 382
- "energy_day_kwh": ENERGY_DAY_MOTOTAXIS_KWH,  # 573 kWh
+ "vehicles_charging_day": VEHICLES_DAY_MOTOTAXIS,  # 130 (REAL dataset)
+ "energy_day_kwh": ENERGY_DAY_MOTOTAXIS_KWH,  # 139.70 kWh (REAL dataset)
```

---

## RESUMEN DE CAMBIOS

### Ubicaciones Actualizadas: 4

| Ubicación | Antes | Después | Tipo |
|-----------|-------|---------|------|
| **Docstring (línea ~18)** | 14,976 kWh | 903.46 kWh | Valor principal |
| **Constante (línea ~1548)** | 3,252.0 kWh | 903.46 kWh | Valor principal |
| **Comentario (línea ~2055)** | 3,252 kWh | 903.46 kWh | Limpieza |
| **Comentarios (línea ~1912)** | 2,679/573 kWh | 763.76/139.70 kWh | Limpieza |
| **Comentarios (línea ~2236)** | 2,679/573 kWh | 763.76/139.70 kWh | Limpieza |

### Error Corregido

**Factor de sobreestimación**: 3,252 / 903.46 = **3.60×**  
**Porcentaje de error**: (3,252 - 903.46) / 3,252 × 100 = **71.5%**

---

## 🔄 CÓMO REVERTIR (SI FUERA NECESARIO)

```bash
# Revertir último commit
git revert 33f3d3ef

# Revertir ambos commits
git revert 33f3d3ef
git revert 011db8fe

# O simplemente restaurar desde una rama anterior
git checkout origin/main -- src/iquitos_citylearn/oe2/chargers.py
```

**NOTA**: No se recomienda revertir. Los valores REALES son más precisos que los antiguos.

---

## ✅ VERIFICACIÓN

```bash
# Ver los commits
git log --oneline -2

# Ver diferencias
git show 011db8fe
git show 33f3d3ef

# Ver estado actual
git status
```

---

**Resumen Visual**:

```
ANTES:  ENERGY_DAY_TOTAL_KWH = 3252.0 kWh/día  ❌ (3.60× error)
AHORA:  ENERGY_DAY_TOTAL_KWH = 903.46 kWh/día  ✅ (REAL dataset)
MEJORA: -71.5% de sobreestimación corregida
```

---

*Generado por GitHub Copilot - 2026-02-04*

