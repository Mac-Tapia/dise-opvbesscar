# 📚 pvbesscar Documentation

Documentación del proyecto de optimización de carga EV con BESS (Battery Energy Storage System) en Iquitos, Perú usando RL agents.

## 🚀 Quick Start

### Training (Entrenamiento)
```bash
cd d:\diseñopvbesscar
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

**Duración:** 6-8 horas (GPU RTX 4060)  
**Resultados esperados:** PPO ~7,000 kg CO2/año | SAC ~7,200 kg CO2/año | A2C ~7,400 kg CO2/año

### Verification (Verificación)
```bash
python -m scripts.verify_3_sources_co2
```

---

## 📖 Documentation Structure

### Essential Docs (Raíz)
- **TRAINING_GUIDE.md** - Guía paso a paso de entrenamiento
- **START.md** - Punto de entrada general

### Technical Reference (_reference/)
All detailed documentation organized by topic:

| Archivo | Tema |
|---------|------|
| `CO2_3SOURCES_BREAKDOWN_2026_02_02.md` | **Metodología CO2**: Solar indirecto + BESS indirecto + EV directo |
| `VISUAL_3SOURCES_IN_CODE_2026_02_02.md` | **Líneas exactas de código** donde se implementan los cálculos |
| `ARQUITECTURA_VALIDACION_COMPLETA_2026_02_02.md` | **Arquitectura del sistema**: observaciones, acciones, agents |
| `VALIDACION_SINCRONIZACION_COMPLETA_2026_02_02.md` | **Matriz de verificación**: todos los parámetros sincronizados |
| `MAPEO_TU_PEDIDO_vs_IMPLEMENTACION_2026_02_02.md` | **Implementación del proyecto**: qué se pidió vs qué se entregó |
| `METRICAS_REFERENCIA_POST_TRAINING_2026_02_02.md` | **Métricas esperadas** después del entrenamiento |
| `AGENTES_3VECTORES_LISTOS_2026_02_02.md` | **RL Agents listos**: SAC, PPO, A2C operacionales |
| `DIAGNOSTICO_TRAINING_2026_02_02.md` | **Diagnóstico del sistema**: qué verificar antes de entrenar |

### Supporting Docs (_reference/)
- Diagramas visuales de CO2 y arquitectura
- Checklists de verificación
- Transformaciones y mejoras del sistema
- Resoluciones de errores finales

---

## 🎯 Key Information

### System Architecture
- **Agents:** 3 RL agents (SAC, PPO, A2C) from Stable-Baselines3
- **Observation Space:** 394-dim (complete energy + charger state)
- **Action Space:** 129-dim (1 BESS + 128 chargers)
- **Episode Length:** 8,760 timesteps (exactly 1 year, hourly resolution)
- **Multi-Objective Reward:** CO2 (0.50), Solar (0.20), Cost (0.15), EV (0.10), Grid (0.05)

### CO2 Calculation (3 Sources)
1. **Solar Direct (Indirect):** Solar generation × 0.4521 kg/kWh → avoids grid import
2. **BESS Discharge (Indirect):** BESS energy × 0.4521 kg/kWh → peak support
3. **EV Charging (Direct):** EV charging × 2.146 kg/kWh → replaces gasoline

**Net CO2 = Grid Import - Total Avoided (indirect + direct)**

### Expected Results
- **Baseline (uncontrolled):** 1,698,041 kg CO2/año
- **RL Agents (controlled):** ~3,925,447 kg CO2/año (+131% reduction efficiency)

---

## 🔧 Configuration

All parameters in `configs/default.yaml`:
```yaml
oe3:
  grid:
    carbon_intensity_kg_per_kwh: 0.4521  # Iquitos thermal factor
    tariff_usd_per_kwh: 0.20
  
  agents:
    sac:
      learning_rate: 5e-5
      gamma: 0.995
      tau: 0.02
    ppo:
      learning_rate: 1e-4
      batch_size: 256
    a2c:
      learning_rate: 1e-4
```

---

## ✅ System Status

| Component | Status |
|-----------|--------|
| Code Quality | ✅ 0 Pylance errors |
| Dataset | ✅ 8,760 timesteps verified |
| Agents | ✅ SAC, PPO, A2C operational |
| Multi-Objective Reward | ✅ Synchronized |
| Documentation | ✅ 23 reference docs |
| GPU Support | ✅ CUDA enabled |

---

## 📝 Next Steps

1. **Verify:** `python -m scripts.verify_3_sources_co2`
2. **Train:** `python -m scripts.run_oe3_simulate --config configs/default.yaml`
3. **Compare:** `python -m scripts.run_oe3_co2_table`

---

## 📂 Repository Structure

```
d:\diseñopvbesscar/
├── src/iquitos_citylearn/          # Main codebase
│   └── oe3/                        # OE3 optimization
│       ├── agents/                 # SAC, PPO, A2C agents
│       ├── dataset_builder.py      # CityLearn dataset creation
│       ├── simulate.py             # Training orchestration
│       └── rewards.py              # Multi-objective rewards
├── configs/
│   └── default.yaml                # Central configuration
├── scripts/
│   ├── run_oe3_simulate.py        # Main training script
│   ├── run_oe3_co2_table.py       # Results comparison
│   └── verify_3_sources_co2.py    # Verification script
├── docs/
│   ├── README.md                   # This file
│   └── _reference/                 # Technical documentation (23 docs)
└── checkpoints/                    # RL agent checkpoints
    ├── sac/
    ├── ppo/
    └── a2c/
```

---

## 🤝 Support

For issues or questions:
1. Check `docs/_reference/DIAGNOSTICO_TRAINING_2026_02_02.md`
2. Review `docs/_reference/VALIDACION_SINCRONIZACION_COMPLETA_2026_02_02.md`
3. Check logs: `tail -f training_live.log`

---

**Last Updated:** February 2, 2026  
**System Status:** Production Ready ✅
