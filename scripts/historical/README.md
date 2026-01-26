# scripts/historical/ - Archived Development Scripts

This folder contains archived Python and shell scripts used during development phases. These scripts are not part of the current active pipeline but are preserved for reference and historical tracking.

**Date Archived:** 2026-01-26  
**Total Scripts Archived:** 48

---

## 📂 Contents by Category

### Deprecated Orchestration (1)
```
EJECUTAR_COMPLETO.py              - Superseded by EJECUTAR_PIPELINE_MAESTRO.py
```

### Training Continuation Scripts (4)
```
continue_sac_training.py           - Resume SAC training from checkpoint
continue_ppo_training.py           - Resume PPO training from checkpoint
continue_a2c_training.py           - Resume A2C training from checkpoint
auto_ppo_then_a2c.py              - Sequential PPO→A2C launcher
```

### Experimental Training Variations (6)
```
ppo_simple_train.py               - Simplified PPO training
ppo_train_no_callback.py          - PPO without callbacks
train_agents_simple.py            - Simple multi-agent training
train_agents_serial.py            - Serial training (Python version)
train_complete_agents.py          - Complete training pipeline variant
launch_a2c_after_ppo.py           - Sequential training launcher
retrain_sac_with_solar.py         - Retraining with solar integration
```

### Monitoring Variants (7)
```
monitor_sac_checkpoint.py         - SAC checkpoint monitoring (duplicate)
monitor_sac_sin_interrupciones.py - Uninterrupted SAC monitoring variant
monitor_training_live.py          - Older version of live monitoring
monitor_ppo_progress.py           - PPO-specific progress tracking
monitor_a2c_launch.py             - A2C launch monitoring
MONITOR_GRAFICAS_ENTRENAMIENTO.py - Graphics-based training monitor
MONITOR_GRAFICAS_SIMPLIFICADO.py  - Simplified graphics monitor
```

### Data Fixes & Transformations (5)
```
fix_charger_csvs.py               - One-time charger CSV fix
fix_oe2_data_integration.py       - OE2 data integration fixes
transform_mall_demand_hourly.py   - Mall demand hourly transformation
verify_agentes.py                 - Agent verification check
```

### Verification & Validation (5)
```
verificar_configuraciones_maxima_potencia.py  - Max power configuration check
verificar_datos_reales_anio.py                - Real annual data verification
verificar_oe2_en_entrenamiento.py            - OE2 training verification
verificar_parametros_oe2_detallados.py       - Detailed OE2 parameter check
VERIFICACION_OBJETIVO_PRINCIPAL.py           - Main objective verification
```

### Analysis & Comparison (5)
```
compare_baseline_vs_agents.py     - Baseline vs agent comparison
compare_baseline_vs_retrain.py    - Baseline vs retrained agents
analizar_demanda_mall_con_control.py - Mall demand with control analysis
audit_oe2_oe3_connectivity.py     - OE2-OE3 connectivity audit
debug_env.py                      - Environment debugging utility
```

### Server & Deployment Variants (5)
```
run_web_server.py                 - Old web server variant
run_oe1_location.py               - Deprecated OE1 location support
run_oe2_solar_plots.py            - Solar plotting utility
fastapi_final.py                  - Old FastAPI variant
fastapi_server_clean.py           - Alternate FastAPI server
fastapi_websocket_server.py       - WebSocket server experimental
```

### Utilities & Maintenance (4)
```
setup_and_train.py                - Setup and training combo script
show_pipeline_report.py           - Pipeline report display
simulador_interactivo.py          - Interactive simulator utility
dashboard_realtime.py             - Real-time dashboard variant
update_docs.py                    - Documentation update script
update_graphics_and_docs.py       - Graphics and docs update script
```

### Shell Scripts (4)
```
monitor_sac.ps1                   - PowerShell SAC monitoring
monitor_sac_start.ps1             - PowerShell SAC startup
monitor_sac_vivo.ps1              - PowerShell live SAC monitoring
train_agents_serial.ps1           - PowerShell serial training
```

---

## 🔍 Why Archived?

These scripts served specific purposes during development:

1. **Experimental Variations** - Training attempts with different configurations (best practices now documented)
2. **One-Time Fixes** - Data corrections no longer needed after pipeline improvements
3. **Monitoring Duplicates** - Multiple variants of monitoring created during optimization (consolidated into monitor_training_live_2026.py)
4. **Legacy Code** - Superseded by improved versions (e.g., EJECUTAR_PIPELINE_MAESTRO.py)
5. **Checkpoint Resume** - Manual checkpoint continuation (now handled by checkpoint manager)

---

## ✅ Current Active Scripts (18 in ../scripts/)

**Essential Pipeline:**
- run_oe2_solar.py
- run_oe2_chargers.py
- run_oe2_bess.py
- run_oe2_co2_breakdown.py
- run_oe3_build_dataset.py
- run_oe3_simulate.py
- run_oe3_co2_table.py
- run_uncontrolled_baseline.py

**Monitoring & Dashboard:**
- monitor_training_live_2026.py
- monitor_checkpoints.py
- monitor_training_progress.py
- monitor_live.py
- dashboard_pro.py

**Orchestration & API:**
- EJECUTAR_PIPELINE_MAESTRO.py
- _common.py
- build_dataset.py
- fastapi_server.py
- run_api.py

---

## 📚 Usage

To access an archived script:

```bash
python scripts/historical/continue_sac_training.py --config configs/default.yaml
```

**Note:** These scripts may depend on outdated data formats or package versions. Verify compatibility before running.

---

## 📊 Consolidation Summary

| Category | Files | Status |
|----------|-------|--------|
| Deprecated Orchestration | 1 | Archived |
| Training Variants | 13 | Archived |
| Monitoring Variants | 7 | Archived |
| Data Fixes | 5 | Archived |
| Verification | 5 | Archived |
| Analysis | 5 | Archived |
| Servers | 6 | Archived |
| Utilities | 6 | Archived |
| Shell Scripts | 4 | Archived |
| **Total Archived** | **48** | **✓** |

---

## 🔗 Related Files

- **Active Scripts:** See [../scripts/](../) for current pipeline
- **Root Archive:** See [../../historical/](../../historical/) for root-level scripts
- **Development Standards:** See [../../CONTRIBUTING.md](../../CONTRIBUTING.md)
- **Commands Reference:** See [../../COMANDOS_EJECUTABLES.md](../../COMANDOS_EJECUTABLES.md)

