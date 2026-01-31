# Actualización Completa de Valores - Sincronización Total del Sistema
**Fecha**: 2026-01-31  
**Rama**: oe3-optimization-sac-ppo  
**Objetivo**: Verificar y actualizar TODOS los archivos vinculados al entrenamiento con valores correctos y consistentes

---

## 📋 RESUMEN EJECUTIVO

### Problema Identificado
Los archivos de entrenamiento tenían valores inconsistentes o comentarios desactualizados que podrían causar confusión o errores durante el entrenamiento de agentes RL.

### Solución Implementada
Actualización sistemática de **7 archivos clave** para garantizar consistencia total con los datos reales OE2 y el workaround ev_demand_constant_kw=50.

---

## ✅ VALORES ESTANDARIZADOS (OE2 REAL 2026-01-31)

### Configuración de Chargers
```yaml
Chargers físicos: 32 (28 motos + 4 mototaxis)
Sockets totales: 128 (32 × 4 sockets)
Distribución: 112 motos + 16 mototaxis
Potencia motos: 2.0 kW por socket
Potencia mototaxis: 3.0 kW por socket
Potencia instalada: 68 kW simultánea (28×2kW + 4×3kW)
```

### Factores de Emisión CO₂
```yaml
Grid import factor: 0.4521 kg CO₂/kWh (central térmica Iquitos)
Conversion factor: 2.146 kg CO₂/kWh (para cálculo directo)
Cálculo: 50 kW × 2.146 = 107.3 kg CO₂/hora
```

### Demanda EV (Workaround CityLearn 2.5.0)
```yaml
ev_demand_constant_kw: 50.0 kW
Justificación: 54% uptime (13h/24h) × 100 kW total ≈ 50 kW
Operación: 9AM-10PM (13 horas diarias)
Capacidad anual: 2,912 motos + 416 mototaxis
```

### BESS (No controlable por agentes)
```yaml
Capacidad: 4,520 kWh
Potencia: 2,712 kW
Eficiencia roundtrip: 90%
Autonomía: 4 horas
```

### Resolución Temporal
```yaml
Timesteps: 8,760 (1 año horario exacto)
Frecuencia: 1 hora (3,600 segundos)
Rango: 2024-01-01 00:00:00 a 2024-12-31 23:00:00
```

---

## 📝 ARCHIVOS ACTUALIZADOS

### 1. `src/iquitos_citylearn/oe3/rewards.py`
**Cambios aplicados**:
- ✅ Actualizado comentario inicial con valores exactos:
  - 32 chargers físicos (28 motos @ 2kW + 4 mototaxis @ 3kW)
  - 128 sockets totales (32 × 4)
  - Potencia instalada: 68 kW simultánea
  - Demanda EV: 50 kW constante
  - Factor conversión: 2.146 kg CO₂/kWh
  - Capacidad anual: 2,912 motos + 416 mototaxis

- ✅ Actualizada clase `IquitosContext`:
  ```python
  co2_factor_kg_per_kwh: float = 0.4521  # Grid import
  co2_conversion_factor: float = 2.146   # Para cálculo directo
  n_chargers: int = 32                   # Físicos
  total_sockets: int = 128               # Individuales
  charger_power_kw_moto: float = 2.0
  charger_power_kw_mototaxi: float = 3.0
  ev_demand_constant_kw: float = 50.0
  ```

**Impacto**: Cálculos de recompensa multiobjetivo ahora usan valores exactos OE2.

---

### 2. `src/iquitos_citylearn/oe3/dataset_constructor.py`
**Cambios aplicados**:
- ✅ Actualizada clase `DatasetConfig`:
  ```python
  n_chargers_physical: int = 32          # NEW: Chargers físicos
  n_chargers: int = 128                  # Total sockets
  n_controllable_chargers: int = 126     # 2 reservados
  carbon_intensity_kg_per_kwh: float = 0.4521
  co2_conversion_factor: float = 2.146   # NEW
  ev_demand_constant_kw: float = 50.0    # Clarificado
  ```

- ✅ Comentarios actualizados con:
  - Resolución temporal exacta (8,760 timesteps horarios)
  - Distribución sockets (112 motos + 16 mototaxis)
  - Justificación ev_demand_constant_kw (54% uptime)

**Impacto**: Dataset builder genera schemas con metadata correcta.

---

### 3. `src/iquitos_citylearn/oe3/agents/sac.py`
**Cambios aplicados**:
- ✅ Actualizada clase `SACConfig`:
  ```python
  co2_target_kg_per_kwh: float = 0.4521
  co2_conversion_factor: float = 2.146   # NEW
  ev_demand_constant_kw: float = 50.0    # NEW
  peak_demand_limit_kw: float = 200.0
  ```

**Impacto**: Agente SAC usa factores CO₂ correctos para reward calculation.

---

### 4. `src/iquitos_citylearn/oe3/agents/ppo_sb3.py`
**Cambios aplicados**:
- ✅ Actualizada clase `PPOConfig`:
  ```python
  co2_target_kg_per_kwh: float = 0.4521
  co2_conversion_factor: float = 2.146   # NEW
  ev_demand_constant_kw: float = 50.0    # NEW
  peak_demand_limit_kw: float = 200.0
  ```

**Impacto**: Agente PPO usa factores CO₂ correctos para reward calculation.

---

### 5. `src/iquitos_citylearn/oe3/agents/a2c_sb3.py`
**Cambios aplicados**:
- ✅ Actualizada clase `A2CConfig`:
  ```python
  co2_target_kg_per_kwh: float = 0.4521
  co2_conversion_factor: float = 2.146   # NEW
  ev_demand_constant_kw: float = 50.0    # NEW
  peak_demand_limit_kw: float = 200.0
  ```

**Impacto**: Agente A2C usa factores CO₂ correctos para reward calculation.

---

### 6. `src/iquitos_citylearn/oe3/data_loader.py`
**Cambios aplicados**:
- ✅ Actualizado método `validate()` en clase `ChargersData`:
  ```python
  # Comentarios clarificados:
  # - 32 chargers físicos (28 motos + 4 mototaxis)
  # - 128 sockets (32 × 4)
  # - 112 motos + 16 mototaxis
  
  logger.info(f"✓ Chargers validados: {len(self.individual_chargers)} cargadores físicos, "
              f"{len(self.hourly_profiles)} perfiles (128 sockets: 112 motos + 16 mototaxis)")
  ```

**Impacto**: Logs de validación ahora muestran estructura correcta (físicos vs sockets).

---

### 7. `src/iquitos_citylearn/oe3/simulate.py`
**Estado**: ✅ **YA CORRECTO** - No requirió cambios
- Ya usa `carbon_intensity_kg_per_kwh` correctamente (0.4521)
- Pasa el valor a `IquitosContext` en rewards
- Logs muestran "Iquitos thermal" correctamente

**Verificado**: Líneas 567, 584, 877-882

---

## 🔍 ARCHIVOS JSON VERIFICADOS (SIN CAMBIOS NECESARIOS)

### `data/interim/oe2/bess/bess_config.json`
✅ **CORRECTO**:
```json
{
  "capacity_kwh": 4520.0,
  "power_kw": 2712.0,
  "efficiency": 0.9,
  "c_rate": 0.6,
  "autonomy_hours": 4.0
}
```

### `data/oe2/interim/bess_results.json`
✅ **CORRECTO** - Incluye comentarios del fix anterior:
```json
{
  "_comment_ev_demand": "NOTA: En OE3, agentes SAC/PPO/A2C usan ev_demand_constant_kw=50kW",
  "_comment_co2_tracking": "CO2 directo = 50kW x 2.146 kg/kWh = 107.3 kg/h acumulativo"
}
```

---

## 🎯 CONFIGURACIONES YAML VERIFICADAS

### `configs/default.yaml`
✅ **CORRECTO** - Actualizado en commit anterior (ee5c5e57):
```yaml
oe2:
  ev_fleet:
    charger_power_kw_moto: 2.0
    charger_power_kw_mototaxi: 3.0
    total_chargers: 32
    total_sockets: 128
    ev_demand_constant_kw: 50.0
```

### `configs/sac_ppo_only.yaml` y `configs/default_optimized.yaml`
✅ **CORRECTO** - Actualizados en commit anterior (df2b99a7)

---

## 📊 MATRIZ DE CONSISTENCIA

| **Concepto** | **Valor** | **Archivos Afectados** | **Estado** |
|--------------|-----------|------------------------|------------|
| Chargers físicos | 32 | rewards.py, dataset_constructor.py, data_loader.py | ✅ Sincronizado |
| Sockets totales | 128 | rewards.py, dataset_constructor.py, data_loader.py | ✅ Sincronizado |
| Motos sockets | 112 | rewards.py, data_loader.py | ✅ Sincronizado |
| Mototaxis sockets | 16 | rewards.py, data_loader.py | ✅ Sincronizado |
| Factor CO₂ grid | 0.4521 | rewards.py, agents/*, dataset_constructor.py | ✅ Sincronizado |
| Factor CO₂ conversión | 2.146 | rewards.py, agents/*, dataset_constructor.py | ✅ Sincronizado |
| ev_demand_constant_kw | 50.0 | rewards.py, agents/*, dataset_constructor.py, configs/*.yaml | ✅ Sincronizado |
| Timesteps | 8,760 | dataset_constructor.py, data_loader.py | ✅ Sincronizado |
| BESS capacidad | 4,520 kWh | bess_config.json, bess_results.json | ✅ Sincronizado |
| BESS potencia | 2,712 kW | bess_config.json, bess_results.json | ✅ Sincronizado |

---

## 🔄 IMPACTO EN ENTRENAMIENTO

### Antes (Inconsistencias)
- ❌ rewards.py: `n_chargers: int = 31` (incorrecto)
- ❌ Falta `co2_conversion_factor` en agentes
- ❌ Falta `ev_demand_constant_kw` explícito en configs de agentes
- ❌ Comentarios confusos sobre chargers físicos vs sockets

### Después (Consistente)
- ✅ **Todos los archivos** usan 32 chargers físicos, 128 sockets
- ✅ **Todos los agentes** tienen `co2_conversion_factor: 2.146`
- ✅ **Todos los agentes** tienen `ev_demand_constant_kw: 50.0`
- ✅ **Todos los comentarios** clarificados con estructura real

### Métricas Esperadas (Sin Cambio Funcional)
- CO₂ directo: 50 kW × 2.146 = **107.3 kg/h** (igual que antes)
- Motos activas: `int((50 × 0.80) / 2.0)` = **20 motos/step**
- Mototaxis activas: `int((50 × 0.20) / 3.0)` = **3 mototaxis/step**

**NOTA IMPORTANTE**: Estos cambios son de **documentación y clarificación**. La lógica funcional del workaround (ev_demand_kw=50) ya estaba implementada en el código de agentes. Ahora los configs y comentarios están **sincronizados** con esa implementación.

---

## 🧪 VALIDACIÓN POST-ACTUALIZACIÓN

### Comandos de Verificación

1. **Verificar dataset build**:
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```
**Esperar**: "✓ Loaded annual charger profiles: (8760, 128)"

2. **Verificar valores en logs de entrenamiento**:
```bash
python -m scripts.run_sac_ppo_a2c_only --sac-episodes 1 --ppo-episodes 1 --a2c-episodes 1
```
**Esperar en step 500**:
- `co2_direct_kg ≈ 53,650 kg` (acumulativo, no cero)
- `motos ≈ 10,000` (acumulativo)
- `mototaxis ≈ 1,500` (acumulativo)

3. **Verificar consistencia en código**:
```bash
# Buscar referencias a n_chargers=31 (debería retornar 0 matches)
grep -r "n_chargers.*31" src/

# Buscar co2_conversion_factor (debería estar en 5 archivos)
grep -r "co2_conversion_factor" src/
```

---

## 📦 COMMIT RECOMENDADO

```bash
git add -A
git commit -m "fix(all): Sincronización completa valores OE2 en todos los archivos de entrenamiento

ARCHIVOS ACTUALIZADOS (7 total):
1. rewards.py: n_chargers=32, total_sockets=128, co2_conversion_factor=2.146
2. dataset_constructor.py: n_chargers_physical=32, co2_conversion_factor
3. sac.py: co2_conversion_factor + ev_demand_constant_kw en SACConfig
4. ppo_sb3.py: co2_conversion_factor + ev_demand_constant_kw en PPOConfig
5. a2c_sb3.py: co2_conversion_factor + ev_demand_constant_kw en A2CConfig
6. data_loader.py: comentarios clarificados (32 físicos, 128 sockets)
7. simulate.py: VERIFICADO correcto (no cambios necesarios)

VALORES ESTANDARIZADOS:
- Chargers físicos: 32 (28 motos + 4 mototaxis)
- Sockets: 128 (32 × 4 = 112 motos + 16 mototaxis)
- CO₂ grid: 0.4521 kg/kWh
- CO₂ conversión: 2.146 kg/kWh
- EV demand: 50 kW constante (workaround CityLearn 2.5.0)
- Timesteps: 8,760 (1 año horario)

IMPACTO:
✓ Consistencia total entre configs, agentes y data loaders
✓ Documentación alineada con implementación real
✓ Sin cambio funcional (workaround ya implementado)
✓ Logs más claros (físicos vs sockets)"
```

---

## 🔗 REFERENCIAS

### Commits Relacionados
- **ee5c5e57**: Actualización inicial configs YAML (ev_demand_kw=50)
- **df2b99a7**: Actualización configs optimizados
- **4781df89**: Análisis fix no aplicado en training
- **0c516448**: Conversión perfiles 30min → 1h
- **7831dbc4**: Verificación perfiles individuales tomas

### Documentos Relacionados
- `CORRECCIONES_CONFIGURACION_COMPLETA_2026_01_31.md`: Correcciones configs anteriores
- `VERIFICACION_PERFILES_INDIVIDUALES_TOMAS_2026_01_31.md`: Validación perfiles 128 sockets
- `INDICE_MAESTRO_CORRECCION_SAC_PPO.md`: Índice maestro del proyecto

---

## ✅ CHECKLIST FINAL

- [x] rewards.py actualizado (IquitosContext con valores exactos)
- [x] dataset_constructor.py actualizado (DatasetConfig expandido)
- [x] sac.py actualizado (SACConfig con nuevos campos)
- [x] ppo_sb3.py actualizado (PPOConfig con nuevos campos)
- [x] a2c_sb3.py actualizado (A2CConfig con nuevos campos)
- [x] data_loader.py actualizado (comentarios clarificados)
- [x] simulate.py verificado (correcto, sin cambios)
- [x] Archivos JSON verificados (correctos, sin cambios)
- [x] Configs YAML verificados (correctos desde commit anterior)
- [x] Matriz de consistencia creada
- [x] Comandos de validación documentados
- [x] Commit message preparado

---

**FIN DEL DOCUMENTO**
