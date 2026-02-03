# ✅ CHECKLIST - PRÓXIMA EJECUCIÓN DE TRAINING (2026-02-02)

## 🎯 Objetivo
Re-ejecutar SAC con fixes aplicados y validar que:
- reward_avg sea ~0.178 (no 17.8)
- actor_loss sea ~-50 a -100 (no -9927)
- critic_loss sea ~10 a 50 (no 20273)
- CO₂ neto disminuya vs baseline

---

## ✅ PRE-TRAINING CHECKLIST

### Verificaciones de Código
- [x] Fix removido: `float(r) * 100.0` → `float(r)` en sac.py línea 739
- [x] CO₂ 3-component implementado en simulate.py
- [x] BESS dataset cargado (4,520 kWh, 2,712 kW)
- [x] 128 chargers individuales en acción space
- [x] Multiobjetivo ponderación: CO₂ 0.50, Solar 0.20, Otros 0.30

### Verificaciones de Config
- [x] configs/default.yaml tiene valores correctos
- [x] GRID_CARBON_INTENSITY_KG_PER_KWH = 0.4521
- [x] EV_CO2_CONVERSION_KG_PER_KWH = 2.146
- [x] SAC learning_rate = 5e-5 (puede reducir a 2e-5 si losses persisten)

### Dependencias
- [x] CityLearn v2.5.0+ instalado
- [x] stable-baselines3 >= 2.0.0
- [x] torch/cuda disponible para SAC
- [x] Dataset generado en `data/processed/citylearn/iquitos_ev_mall/`

---

## 🚀 PROCEDIMIENTO DE EJECUCIÓN

### Paso 1: Verificar que fixes están aplicados
```bash
# En VS Code: Abrir src/iquitos_citylearn/oe3/agents/sac.py
# Verificar línea 739: reward_val = float(r)  (SIN × 100)
```

### Paso 2: Limpiar checkpoints viejos (OPCIONAL - si quieres desde cero)
```bash
# Mantener checkpoints para resumir, O:
# rm -r checkpoints/sac/*
```

### Paso 3: Ejecutar training
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### Paso 4: Monitorear logs en tiempo real
Buscar patrones:
```
[SAC] paso XXXXX | reward_avg=0.XXX | actor_loss=-XX | critic_loss=XX
[CO₂ BREAKDOWN] SAC Agent Results
[CO₂ INDIRECTO] Grid import: X kg
[CO₂ DIRECTO]   EV reduction: X kg
[CO₂ NETO]      Actual footprint: X kg
```

---

## 📊 MÉTRICAS ESPERADAS

### Recompensa (Debe normalizarse)
| Métrica | Antes (INCORRECTO) | Después (CORRECTO) | Status |
|---------|-----|-----|--------|
| reward_avg | 17.8233 | ~0.178 | 🟡 A verificar |
| actor_loss | -9,927.18 | -50 a -100 | 🟡 A verificar |
| critic_loss | 20,273.58 | 10 a 50 | 🟡 A verificar |

### CO₂ (Debe persistir)
| Métrica | Valor OE2 | Status |
|--------|-----------|--------|
| co2_indirecto_kg | 1,031,541 | ✅ Verificado |
| co2_directo_evitado_kg | 294,109 | ✅ Verificado |
| co2_neto_kg | 737,432 | ✅ Verificado |

---

## 🚨 TROUBLESHOOTING

### Si reward_avg SIGUE siendo 17.8 o muy alto:
1. Verificar que el fix esté en línea 739 de sac.py
2. Ejecutar: `grep -n "float(r) \* 100" src/iquitos_citylearn/oe3/agents/*.py`
   - Debe estar VACÍO
3. Limpiar Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
4. Reiniciar Pylance: `Ctrl+Shift+P` → "Pylance: Restart"

### Si actor_loss SIGUE explodiendo:
1. Reducir learning_rate: 5e-5 → 2e-5 en configs/default.yaml
2. Aumentar gradient clipping: 10.0 → 5.0
3. Verificar que observation space está normalizado

### Si CO₂ neto es incorrecto:
1. Verificar que `_extract_net_grid_kwh()` está retornando valores correctos
2. Verificar que `_extract_ev_charging_kwh()` está contando bien
3. Revisar que solar × 0.4521 = co2_indirecto

---

## 📈 CRITERIOS DE ÉXITO

**Episodio 1 (Baseline - sin RL):**
- ✅ reward_avg entre -1 y 0 (bien, indica demanda no controlada)
- ✅ CO₂ neto ~5.3M kg (match con OE2 baseline)
- ✅ Grid import alto (sin PV directo)

**Episodio 2 (SAC - con RL):**
- ✅ reward_avg convergiendo positivamente (>0.1)
- ✅ CO₂ neto disminuyendo (<5M kg)
- ✅ Grid import bajando (~1.8M kWh)
- ✅ Solar utilización aumentando (>60%)

**Episodio 3 (PPO - con RL):**
- ✅ Similar a SAC o mejor
- ✅ Losses más estables

**Final:**
- ✅ CO₂ reducción neta: 25-35% vs baseline
- ✅ Solar utilización: 60-70%
- ✅ EV satisfacción: >85%

---

## 📝 DOCUMENTACIÓN POS-TRAINING

Después de completar training, crear:

1. **results_sac.json** - Métricas finales de SAC
2. **timeseries_sac.csv** - Serie horaria completa
3. **trace_sac.csv** - Detalle de acciones y observaciones
4. **RESULTADOS_FINALES_2026_02_02.md** - Reporte ejecutivo

---

## 🔗 Referencias Rápidas

| Aspecto | Ubicación |
|--------|-----------|
| CO₂ Constants | `src/iquitos_citylearn/config.py` línea 32-34 |
| Multiobjetivo Weights | `src/iquitos_citylearn/oe3/rewards.py` línea 90-130 |
| SAC Callback | `src/iquitos_citylearn/oe3/agents/sac.py` línea 728-750 |
| CO₂ Calculation | `src/iquitos_citylearn/oe3/simulate.py` línea 1030-1062 |
| Dataset | `data/processed/citylearn/iquitos_ev_mall/` |
| Config | `configs/default.yaml` |

---

## ✅ SIGN-OFF

**Fixes aplicados:** ✅ SI  
**Testing recomendado:** ✅ SI  
**Ready to train:** ✅ YES

**Ejecutar con confianza:**
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml 2>&1 | tee training.log
```

---

**Fecha:** 2026-02-02  
**Preparado por:** GitHub Copilot  
**Status:** 🟢 LISTO PARA EJECUCIÓN
