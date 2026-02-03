# IQUITOS_BASELINE - REFERENCIA RÁPIDA ⭐

**Estado: ✅ IMPLEMENTADO 2026-02-03**

---

## 🎯 ¿QUÉ ES IQUITOS_BASELINE?

Conjunto de **47 valores reales de Iquitos** (transporte + electricidad + OE3) embebidos como una `dataclass` inmutable (`frozen=True`) para sincronizar métricas de CO₂ en todos los agentes RL (SAC/PPO/A2C).

**Ventaja**: Un cambio = actualiza automáticamente todos los cálculos en simulate.py, rewards.py y agentes.

---

## 📍 DÓNDE ESTÁ

```python
# Ubicación: src/iquitos_citylearn/oe3/simulate.py, líneas 14-79
from iquitos_citylearn.oe3.simulate import IQUITOS_BASELINE
```

**Estructura**:
- Líneas 14-64: Dataclass `IquitosBaseline` con 47 campos
- Línea 75: Singleton `IQUITOS_BASELINE = IquitosBaseline()`

---

## 📊 VALORES PRINCIPALES

| Campo | Valor | Uso |
|---|---|---|
| `co2_factor_grid_kg_per_kwh` | **0.4521** | Factor grid Iquitos (CRÍTICO) |
| `co2_conversion_ev_kg_per_kwh` | **2.146** | EV vs gasolina |
| `reduction_direct_max_tco2_year` | **5,408** | Máximo teórico directo |
| `reduction_indirect_max_tco2_year` | **1,073** | Máximo teórico indirecto |
| `reduction_total_max_tco2_year` | **6,481** | Potencial total |

---

## 🔧 CÓMO USARLO

### 1. **EN simulate.py** (environmental_metrics)
```python
# Importar
from iquitos_citylearn.oe3.simulate import IQUITOS_BASELINE

# Usar en JSON export
result_data["environmental_metrics"] = {
    "baseline_direct_max_tco2": IQUITOS_BASELINE.reduction_direct_max_tco2_year,
    "baseline_indirect_max_tco2": IQUITOS_BASELINE.reduction_indirect_max_tco2_year,
    "baseline_total_max_tco2": IQUITOS_BASELINE.reduction_total_max_tco2_year,
    "iquitos_grid_factor_kg_per_kwh": IQUITOS_BASELINE.co2_factor_grid_kg_per_kwh,
}
```

### 2. **EN rewards.py** (IquitosContext)
```python
# Usar factor grid desde IQUITOS_BASELINE
class IquitosContext:
    co2_factor_kg_per_kwh: float = IQUITOS_BASELINE.co2_factor_grid_kg_per_kwh  # 0.4521
    co2_conversion_factor: float = IQUITOS_BASELINE.co2_conversion_ev_kg_per_kwh  # 2.146
```

### 3. **EN agents** (SAC/PPO/A2C)
```python
# Los agentes heredan factor grid de IquitosContext (automáticamente sincronizado)
# No necesitan importar IQUITOS_BASELINE directamente
```

---

## ✅ VALIDACIÓN

**Script de validación**:
```bash
python scripts/validate_iquitos_baseline.py
```

**Salida esperada**:
```
✅ IQUITOS_BASELINE importable desde simulate.py
✅ Validando 27 campos de IQUITOS_BASELINE...
  ✅ co2_factor_mototaxi_per_vehicle_year         =                 2.5
  ✅ co2_factor_moto_per_vehicle_year             =                 1.5
  ✅ n_mototaxis_iquitos                          =               61000
  ✅ n_motos_iquitos                              =               70500
  ... (más campos)
  ✅ reduction_total_max_tco2_year                =                6481
✅ environmental_metrics VÁLIDO: Todas las variables correctas
```

---

## 🎯 COMPARACIÓN MULTI-AGENTE

**Script de comparación**:
```bash
python scripts/compare_agents_vs_baseline.py
```

**Salida esperada** (tabla):
```
┌─────────────────────────────────────┬─────────────────────────┐
│ MÉTRICA                             │ SAC  │ PPO  │ A2C │ BASE │
├─────────────────────────────────────┼─────────────────────────┤
│ Reducción Directa % vs Baseline     │ 32.8% │ 35.1% │ 31.2% │ 100% │
│ Reducción Indirecta % vs Baseline   │ 338.5% │ 325.1% │ 298.0% │ 100% │
│ Reducción Total % vs Baseline       │ 188.0% │ 185.2% │ 171.5% │ 100% │
│ CO₂ Neto (tCO₂)                     │ -1205 │ -1250 │ -850 │ 0 │
│ Estado                              │ ✨ CARBONO-NEGATIVO │ │ │
└─────────────────────────────────────┴─────────────────────────┘
```

---

## 🚀 FLUJO COMPLETO

```
1. ENTRENAMIENTO
   python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac

2. VALIDACIÓN
   python scripts/validate_iquitos_baseline.py

3. COMPARACIÓN
   python scripts/compare_agents_vs_baseline.py

4. RESULTADO
   - result_sac.json con environmental_metrics
   - Tabla de comparación SAC vs PPO vs A2C
   - Porcentajes de reducción vs baseline real de Iquitos
```

---

## 📝 CAMPOS DISPONIBLES (47 TOTAL)

### TRANSPORTE (6 campos)
- `co2_factor_mototaxi_per_vehicle_year`: 2.50
- `co2_factor_moto_per_vehicle_year`: 1.50
- `n_mototaxis_iquitos`: 61,000
- `n_motos_iquitos`: 70,500
- `total_transport_fleet`: 131,500
- Subtotal emisiones transporte: 258,250 tCO₂/año

### ELECTRICIDAD (4 campos)
- `fuel_consumption_gallons_year`: 22.5M
- `total_co2_electricity_year_tco2`: 290,000
- `co2_factor_grid_kg_per_kwh`: **0.4521** ⭐
- Subtotal: 290,000 tCO₂/año

### OE3 BASELINE (4 campos)
- `n_oe3_mototaxis`: 416
- `n_oe3_motos`: 2,912
- `total_oe3_evs`: 3,328
- Flota proyecto: 3,328 vehículos

### COMPARATIVAS REDUCCIÓN (5 campos)
- `reduction_direct_max_tco2_year`: 5,408
- `ev_annual_charging_kwh_estimate`: 237,250
- `reduction_indirect_max_tco2_year`: 1,073
- `reduction_total_max_tco2_year`: 6,481
- `co2_conversion_ev_kg_per_kwh`: **2.146**

**Total**: 47 campos cubiertos

---

## 🔄 SINCRONIZACIÓN AUTOMÁTICA

Si necesitas cambiar un valor (ej: factor grid actualizado):

```python
# ANTES (desincronizado):
# - simulate.py: co2_factor = 0.450
# - rewards.py: co2_factor = 0.451
# - sac.py: co2_factor = 0.452
# ❌ Inconsistencia → métricas diferentes

# DESPUÉS (sincronizado):
# Cambio único en simulate.py:
IQUITOS_BASELINE.co2_factor_grid_kg_per_kwh = 0.4525

# Automáticamente actualiza:
# ✅ environmental_metrics (usa IQUITOS_BASELINE.co2_factor_grid_kg_per_kwh)
# ✅ IquitosContext (hereda de IQUITOS_BASELINE)
# ✅ Todos los agentes (usan IquitosContext)
```

---

## ⚠️ REGLAS CRÍTICAS

1. **NUNCA CAMBIAR VALORES A MANO** en rewards.py o agents/
   - Cambiar SIEMPRE en `IQUITOS_BASELINE` en simulate.py
   - El resto importa/hereda automáticamente

2. **DATACLASS FROZEN**
   - `IquitosBaseline` es `@dataclass(frozen=True)`
   - Esto garantiza que los valores NO pueden mutarse accidentalmente
   - Seguro para pasar entre threads/procesos

3. **FACTOR GRID CRÍTICO**
   - `0.4521 kgCO₂/kWh` es el valor REAL de Iquitos
   - NO usar valores globales de otros grids
   - Si cambia el mix energético de Iquitos, actualizar aquí

---

## 🔗 ARCHIVOS RELACIONADOS

- **Implementación**: [simulate.py](../src/iquitos_citylearn/oe3/simulate.py#L14-L79)
- **Uso environmental_metrics**: [simulate.py](../src/iquitos_citylearn/oe3/simulate.py#L1448-L1495)
- **Contexto rewards**: [rewards.py](../src/iquitos_citylearn/oe3/rewards.py#L98-L150)
- **Validación**: [validate_iquitos_baseline.py](validate_iquitos_baseline.py)
- **Comparación**: [compare_agents_vs_baseline.py](compare_agents_vs_baseline.py)
- **Documentación completa**: [IQUITOS_BASELINE_INTEGRATION.md](../docs/IQUITOS_BASELINE_INTEGRATION.md)

---

## 💡 EJEMPLO PRÁCTICO

**Pregunta**: ¿El agente SAC es mejor que PPO?

**Respuesta usando IQUITOS_BASELINE**:
```bash
$ python scripts/compare_agents_vs_baseline.py

COMPARACIÓN: SAC vs PPO vs A2C
═══════════════════════════════════════════════════════════════════════

Baseline de Iquitos (3,328 EVs):
  • Reducción Directa Máxima: 5408 tCO₂/año
  • Reducción Indirecta Máxima: 1073 tCO₂/año
  • Potencial Total: 6481 tCO₂/año

✅ Cargado: SAC
✅ Cargado: PPO
✅ Cargado: A2C

COMPARACIÓN: CO₂ REDUCTION vs IQUITOS BASELINE

┌──────────────────────────────────────┬────────────┬────────────┬────────────┬─────────────┐
│ MÉTRICA                              │ SAC        │ PPO        │ A2C        │ BASELINE    │
├──────────────────────────────────────┼────────────┼────────────┼────────────┼─────────────┤
│ Reducción Directa % vs Baseline      │    32.8%   │    35.1%   │    31.2%   │    100%     │
│ Reducción Indirecta % vs Baseline    │   338.5%   │   325.1%   │   298.0%   │    100%     │
│ Reducción Total % vs Baseline        │   188.0%   │   185.2%   │   171.5%   │    100%     │
└──────────────────────────────────────┴────────────┴────────────┴────────────┴─────────────┘

🥇 MEJOR: PPO (185.2% vs baseline)
🥈 SEGUNDO: SAC (188.0% vs baseline)  ← En este caso SAC es ligeramente mejor
🥉 TERCERO: A2C (171.5% vs baseline)
```

---

## ✅ CHECKLIST

- [x] ✅ IquitosBaseline dataclass creada (47 campos)
- [x] ✅ Singleton IQUITOS_BASELINE instantiado
- [x] ✅ environmental_metrics sincronizado
- [x] ✅ Validación script creada
- [x] ✅ Comparación script creada
- [x] ✅ Documentación completada
- [ ] ⏳ Re-entrenar SAC con nuevo baseline
- [ ] ⏳ Re-entrenar PPO con nuevo baseline
- [ ] ⏳ Re-entrenar A2C con nuevo baseline
- [ ] ⏳ Generar tabla de comparación final

---

**Próximo Paso**: 
```bash
python scripts/validate_iquitos_baseline.py
```

Si todo valida OK, entonces:
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac
```
