# 🚀 QUICK REFERENCE: OE2 → PPO Data Chain

## TL;DR - Lo más importante

**Estado:** ✅ LISTO PARA ENTRENAR PPO

```bash
# Verificar cadena completa (2 min)
python scripts/demo_cadena_completa.py
python scripts/quick_validate_ppo.py

# Entrenar PPO (2-3 horas)
python -m scripts.run_agent_ppo --config configs/default.yaml

# Ver resultados
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## 📊 Arquitectura de Datos (Mapa Mental)

```
OE2 Raw Data (4 Fuentes)
│
├─ pv_generation_timeseries.csv (8,760 h, solar)
├─ demandamallhorakwh.csv (8,785 h, mall)
├─ bess_simulation_hourly.csv (8,760 h, BESS)
└─ individual_chargers.json (32 chargers → 128 tomas)
│
↓ [dataset_builder.py - FIX APPLIED]
│
CityLearn Format
│
├─ Building_1.csv (solar + mall)
├─ electrical_storage_simulation.csv (BESS)
├─ charger_simulation_001.csv → 128.csv ✅
└─ schema.json (128 charger refs) ✅✅✅
│
↓ [simulate.py]
│
PPO Training
│
├─ Observation: 394-dim (solar, mall, BESS, 128 chargers, time)
├─ Action: 129-dim (1 BESS + 128 chargers) ✅
└─ Reward: Multiobjetivo (CO₂, solar, cost, EV, grid)
```

---

## 🔍 Verificación Rápida

### ¿128 chargers en schema?
```bash
python scripts/check_chargers.py
# Expected: ✅ Chargers en schema: 128/128
```

### ¿Todos los archivos CSV?
```bash
ls data/processed/citylearn/iquitos_ev_mall/charger_simulation_*.csv | wc -l
# Expected: 128
```

### ¿BESS sincronizado?
```bash
python scripts/validate_complete_chain_oe2_to_ppo.py
# Expected: Phase 3 BESS SYNC: 0.0 kWh diferencia
```

---

## 📈 Métricas Esperadas

| Métrica | Baseline | Target PPO |
|---------|----------|-----------|
| Grid Import | 420k kWh | 300-350k kWh (-20% a -30%) |
| CO₂ Grid | 190k kg | 133-142k kg (-30% to -40%) |
| Solar Use | 40% | 60-65% (+20%) |

---

## 🐛 Si algo falla...

### Error: "32 chargers en schema"
```bash
# Rebuild dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Check result
python scripts/check_chargers.py  # Should show 128/128
```

### Error: "action space mismatch"
```bash
# Check schema chargers count
python scripts/quick_validate_ppo.py  # Should show 129-dim action
```

### Error: "solar data corrupted"
```bash
# Verify source
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); print(f'Rows: {len(df)}, Sum: {df.ac_power_kw.sum():,.0f} kWh')"
# Expected: Rows: 8760, Sum: 8,030,119 kWh
```

---

## 📁 Archivos Críticos

```
dataset_builder.py (1,562 líneas)
├─ L676: total_devices = 32 × 4 = 128 ✅ [FIX APPLIED]
├─ L685-698: Force empty chargers dict ✅
├─ L707-770: Socket mapping logic ✅
├─ L1507-1520: Schema charger refs ✅
└─ L1534-1560: BESS validation ✅

simulate.py
├─ Loads CityLearn env with 128 chargers ✅
├─ Creates 129-dim action space ✅
└─ Handles multi-objective reward ✅

schema.json (generated)
├─ 128 charger references ✅
├─ BESS configuration ✅
└─ Solar PV 4,162 kWp ✅
```

---

## 🎓 Entender la Arquitectura

**¿Por qué 32 chargers → 128 tomas?**

```
OE2 Real World:
  32 Physical Chargers
  Each charger has 4 sockets (tomas)
  
CityLearn Simulation:
  1 charger_simulation_*.csv por SOCKET
  No por charger físico
  
PPO Control:
  PPO controla cada SOCKET independientemente
  129 acciones: 1 BESS + 128 charger setpoints
```

**¿Por qué control individual?**

Razones operacionales:
- Priorizar carga de EVs urgentes
- Balancear motos vs mototaxis
- Responder a picos de demanda
- Maximizar autoconsumo solar

---

## 📊 Post-Training Analysis

### Ver resultados de entrenamiento
```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

### Outputs esperados
```
outputs/oe3_simulations/
├─ result_ppo.json (métricas PPO)
├─ timeseries_ppo.csv (temporal PPO)
├─ trace_ppo.csv (detalle PPO)
└─ co2_comparison_table.csv (comparativa vs baseline)
```

### Comparación Manual
```bash
# Baseline CO₂
grep "carbon_kg" outputs/oe3_simulations/result_uncontrolled.json

# PPO CO₂
grep "carbon_kg" outputs/oe3_simulations/result_ppo.json

# Improvement % = (baseline - ppo) / baseline × 100
```

---

## 🔄 Workflow Típico

```
1. Verificar Cadena (1 min)
   python scripts/demo_cadena_completa.py
   ↓
2. Entrenar PPO (2-3 h)
   python -m scripts.run_agent_ppo --config configs/default.yaml
   ↓
3. Analizar Resultados (5 min)
   python -m scripts.run_oe3_co2_table --config configs/default.yaml
   ↓
4. Comparar vs Baseline (1 min)
   # Manually compare outputs/oe3_simulations/result_*.json
```

---

## ✅ Checklist Pre-Training

- [ ] Solar 8,760 rows ✅
- [ ] Mall data integrado ✅
- [ ] BESS sync perfecto ✅
- [ ] 128/128 chargers en schema ✅
- [ ] 128/128 CSV files exist ✅
- [ ] PPO action space 129-dim ✅
- [ ] Dataset validation 7/7 PASS ✅
- [ ] Configs/default.yaml correct ✅

Si todo es ✅, ejecutar:
```bash
python -m scripts.run_agent_ppo --config configs/default.yaml
```

---

## 📞 Troubleshooting Links

| Problema | Solución |
|----------|----------|
| Chargers: 32 instead 128 | [VERIFICACION_CADENA_COMPLETA_2026-02-04.md](VERIFICACION_CADENA_COMPLETA_2026-02-04.md) |
| PPO action dimension | [RESUMEN_EJECUTIVO_2026-02-04.md](RESUMEN_EJECUTIVO_2026-02-04.md) |
| Dataset build errors | [dataset_builder.py#L676](src/iquitos_citylearn/oe3/dataset_builder.py#L676) |
| Solar data validation | [scripts/demo_cadena_completa.py#L30](scripts/demo_cadena_completa.py#L30) |

---

**Last Updated:** 2026-02-04  
**System Status:** ✅ Production Ready  
**Next Step:** `python -m scripts.run_agent_ppo --config configs/default.yaml`

