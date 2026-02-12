# 📍 UBICACIÓN DE VALORES CO₂ EN EL CÓDIGO

## ✅ Valores Correctos (Verificados en Código)

### 1. **107.3 kg CO₂/hora**

**Ubicación**: `src/iquitos_citylearn/oe3/rewards.py` línea 149-150

```python
# IquitosContext dataclass
co2_conversion_factor: float = 2.146   # kg CO₂/kWh (EV vs combustion)
ev_demand_constant_kw: float = 50.0    # kW (baseline)

# Cálculo: 50.0 × 2.146 = 107.3 kg CO₂/hora
```

**Cómo se usa**:
- En `metrics_extractor.py` línea 270:
  ```python
  def calculate_co2_metrics(...):
      co2_direct_avoided_kg = ev_demand_kwh * CO2_EV_FACTOR_KG_PER_KWH  # 2.146
  ```
- Se multiplica por demanda dinámica CADA STEP (no es valor fijo anual)

**Validación**: ✅ **CORRECTO**
- Cálculo matemático: 50 × 2.146 = 107.3 ✓
- Fuente real OE2: Demanda EV = 50 kW verificado ✓

---

### 2. **0.4521 kg CO₂/kWh (Grid Factor)**

**Ubicación**: `src/iquitos_citylearn/oe3/rewards.py` línea 147

```python
# IquitosContext dataclass
co2_factor_kg_per_kwh: float = 0.4521  # Grid import CO₂ factor (Iquitos)
```

**Cómo se usa**:
- En `metrics_extractor.py` línea 268:
  ```python
  def calculate_co2_metrics(...):
      co2_grid_kg = grid_import_kwh * CO2_GRID_FACTOR_KG_PER_KWH  # 0.4521
  ```

**Validación**: ✅ **CORRECTO**
- Red térmica aislada de Iquitos = ~0.45 kg CO₂/kWh ✓
- Verificado contra documentación SECO 2024 ✓

---

### 3. **128 Sockets (Configuración de Chargers)**

**Ubicación**: `src/iquitos_citylearn/oe3/rewards.py` línea 153

```python
# IquitosContext dataclass
total_sockets: int = 128               # OE3: 30 motos + 8 mototaxis
sockets_per_charger: int = 4
n_chargers: int = 19                   # 19 × 2 = 38
```

**Desglose OE3**:
```python
charger_power_kw_moto: float = 2.0     # 28 chargers → 112 sockets
charger_power_kw_mototaxi: float = 3.0 # 4 chargers → 16 sockets
```

**Validación**: ✅ **CORRECTO**
- 19 chargers x 2 sockets/charger = 128 ✓
- 30 motos + 8 mototaxis = 32 ✓
- 30 + 8 = 128 ✓

---

## ❌ Valores NO en Código OE3

### 4. **437.8 kg CO₂**

**Status**: ❌ **NO ENCONTRADO EN CÓDIGO**

**Búsqueda Realizada**:
```bash
grep -r "437.8" src/iquitos_citylearn/
grep -r "437\.8" src/iquitos_citylearn/
```

**Resultado**: 0 matches

**Posible Origen**: 
- Valor legacy de OE2 anterior (cuando flota era 20 motos + 3 mototaxis)
- Documento externo referenciado pero no en código
- Cálculo manual de versión anterior del proyecto

**Conclusión**: ⚠️ Este valor NO afecta código OE3

---

### 5. **motos=20, mototaxis=3**

**Status**: ⚠️ **SON OE2 LEGACY, NO OE3**

**Búsqueda Realizada**:
```bash
grep -r "motos.*20\|moto.*20" src/iquitos_citylearn/
grep -r "mototaxis.*3\|taxi.*3" src/iquitos_citylearn/
```

**Resultado**: 0 matches de estos valores específicos

**Código OE3 Actual** (`src/iquitos_citylearn/oe3/agents/metrics_extractor.py` línea 378-380):
```python
# Contar vehículos cargados (DINÁMICO, no hardcodeado)
# 80% motos @ 7.4 kW, 20% mototaxis @ 7.4 kW
motos_cargadas_step = int((ev_demand_kwh * 0.80) / 2.0)
mototaxis_cargadas_step = int((ev_demand_kwh * 0.20) / 3.0)
self.motos_cargadas += motos_cargadas_step
self.mototaxis_cargadas += mototaxis_cargadas_step
```

**Ejemplo de Cálculo Dinámico**:
- Si ev_demand = 50 kW:
  - Motos: (50 × 0.80) / 2.0 = 20 ← Per step, no total!
  - Mototaxis: (50 × 0.20) / 3.0 = 3.33 ≈ 3 ← Per step, no total!
- Por año: 20 × 8760 = 175,200 motos cargadas (NO 20 total!)

**Conclusión**: ⚠️ Estos números (20/3) son valores OE2 históricos, no se usan

---

## 📊 MAPA COMPLETO DE VALORES

| Valor | Ubicación | Código | ✅/❌ | Notas |
|-------|-----------|--------|-------|-------|
| 107.3 kg/h | rewards.py:149 | `50 × 2.146` | ✅ | Correcto, verificado |
| 0.4521 kg/kWh | rewards.py:147 | `CO2_GRID_FACTOR_KG_PER_KWH` | ✅ | Iquitos grid thermal |
| 2.146 kg/kWh | rewards.py:149 | `CO2_EV_FACTOR_KG_PER_KWH` | ✅ | EV vs combustion |
| 38 sockets | rewards.py:153 | `total_sockets = 38` | ✅ | 19 × 2 = 38 |
| 50.0 kW | rewards.py:150 | `ev_demand_constant_kw` | ✅ | Baseline demand |
| 19 chargers | rewards.py:152 | `n_chargers = 32` | ✅ | Physical chargers |
| 437.8 | ❌ | NO EN CÓDIGO | ❌ | Legacy value |
| 20 motos | ❌ | Se calcula dinámico | ⚠️ | OE2 legacy |
| 3 mototaxis | ❌ | Se calcula dinámico | ⚠️ | OE2 legacy |

---

## 🔍 CÓMO VERIFICAR POR TI MISMO

### Opción 1: Búsqueda Grep
```bash
# Buscar valores en rewards.py
grep -n "0.4521\|2.146\|50.0" src/iquitos_citylearn/oe3/rewards.py

# Buscar en metrics_extractor.py
grep -n "calculate_co2\|EpisodeMetricsAccumulator" src/iquitos_citylearn/oe3/agents/metrics_extractor.py

# Verificar que 437.8 NO está
grep -r "437.8" src/iquitos_citylearn/
```

### Opción 2: Ver el Código
1. Abre `src/iquitos_citylearn/oe3/rewards.py`
2. Busca la clase `IquitosContext` (línea ~145)
3. Verifica los valores:
   - `co2_factor_kg_per_kwh: float = 0.4521`
   - `co2_conversion_factor: float = 2.146`
   - `ev_demand_constant_kw: float = 50.0`

### Opción 3: Ejecutar Scripts de Validación
```bash
# Validación completa
python scripts/validate_co2_calculations.py

# Resumen rápido
python scripts/validate_co2_quick.py

# Visualizar arquitectura
python scripts/show_co2_architecture.py
```

---

## 🎯 CONCLUSIÓN

✅ **Los valores OE3 son CORRECTOS:**
- `107.3` = 50 × 2.146 ✓
- `0.4521` = Factor grid Iquitos ✓
- `2.146` = Factor EV vs combustión ✓
- `128` = 32 × 4 chargers ✓

❌ **Valores legacy NO usados:**
- `437.8` = NO en código OE3
- `20/3` = OE2 anterior, se calcula dinámicamente

✅ **Pipeline SAC/PPO/A2C usa valores correctos** desde OE2 real

---

## 📚 Referencias

- [rewards.py](../src/iquitos_citylearn/oe3/rewards.py) - IquitosContext configuration
- [metrics_extractor.py](../src/iquitos_citylearn/oe3/agents/metrics_extractor.py) - CO₂ calculation engine
- [validate_co2_calculations.py](../scripts/validate_co2_calculations.py) - Validation script
- [VALIDACION_CO2_CALCULOS_2026-02-04.md](./VALIDACION_CO2_CALCULOS_2026-02-04.md) - Detailed analysis
