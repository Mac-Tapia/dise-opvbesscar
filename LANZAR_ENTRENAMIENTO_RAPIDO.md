# 🚀 GUÍA RÁPIDA - LANZAR ENTRENAMIENTO

## Inicio Rápido (2 minutos)

```bash
# 1. Activar entorno (si existe)
.venv\Scripts\activate

# 2. Lanzar entrenamiento con validaciones automáticas
python scripts/launch_training.py
```

**Eso es todo**. El script hará:
- ✅ Validación de sistema
- ✅ Auditoría de pipeline
- ✅ Confirmación de usuario
- ✅ Lanzamiento de entrenamiento OE3

---

## Opciones Avanzadas

### Validar antes de entrenar (opcional)

```bash
# Auditoría integral del pipeline
python scripts/audit_training_pipeline.py

# Validación pre-entrenamiento
python scripts/validate_training_readiness.py
```

### Lanzar entrenamiento directo (sin validación)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### Opciones de entrenamiento

```bash
# Skip dataset building (si ya existe)
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset

# Skip baseline calculation
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-baseline

# Resume from checkpoints (automático)
python -m scripts.run_oe3_simulate --config configs/default.yaml  # Continúa si hay checkpoints
```

---

## Estado del Sistema

**Última Verificación**: 2026-01-26 23:35:00

```
✅ Python 3.11 verificado
✅ Schema integridad: 8760 timesteps, 128 chargers, 4050 kWp, 1200 kW
✅ Config consistencia: SAC/PPO/A2C configurados
✅ Directorios escribibles: checkpoints/{SAC,PPO,A2C}
✅ Dataset completo: OE2 artifacts presentes
✅ Imports funcionales: NumPy, Pandas, PyYAML, Stable-Baselines3, PyTorch
```

**Resultado**: ✅ **SISTEMA LISTO PARA ENTRENAMIENTO**

Ver [VERIFICACION_FINAL_SISTEMA_LISTO.md](VERIFICACION_FINAL_SISTEMA_LISTO.md) para detalles completos.

---

## Monitoreo Durante Entrenamiento

```bash
# En otra terminal, monitorear logs
tail -f outputs/oe3_simulations/training_log.txt

# Verificar checkpoints guardados
ls -lh checkpoints/SAC/
ls -lh checkpoints/PPO/
ls -lh checkpoints/A2C/
```

---

## Resultados

Después del entrenamiento, los resultados estarán en:

```
outputs/oe3_simulations/
├── simulation_summary.json       # Comparación CO₂, cost, rewards
├── training_log.txt              # Log completo
├── {agent}_results.csv           # Timeseries por agente
└── {agent}_checkpoint_metadata.json
```

---

## Troubleshooting Rápido

| Error | Solución |
|-------|----------|
| "Python 3.11 required" | `python --version` debe ser 3.11.x |
| "Module not found" | `pip install -r requirements-training.txt` |
| "CUDA out of memory" | Reducir batch_size en config, o usar CPU |
| "Schema missing episode_time_steps" | ✅ REPARADO - ejecuta validación |

---

## Información de Agentes

**SAC** (Soft Actor-Critic)
- Off-policy: Sample-efficient
- Ideal para: Rewards dispersos
- Tiempo: ~5-10 min/episode (GPU)

**PPO** (Proximal Policy Optimization)
- On-policy: Estable, convergencia confiable
- Ideal para: Entrenamiento estable
- Tiempo: ~10-15 min/episode (GPU)

**A2C** (Advantage Actor-Critic)
- On-policy: Simple, baseline rápido
- Ideal para: Comparación rápida
- Tiempo: ~5-10 min/episode (GPU)

---

## ¿Preguntas?

Ver documentación completa:
- [VERIFICACION_FINAL_SISTEMA_LISTO.md](VERIFICACION_FINAL_SISTEMA_LISTO.md) - Estado completo del sistema
- [INDICE_MAESTRO_DOCUMENTACION.md](INDICE_MAESTRO_DOCUMENTACION.md) - Índice de toda la documentación
- [QUICKSTART.md](QUICKSTART.md) - Inicio rápido del proyecto

**Estado de Garantía**: ✅ Sistema probado y verificado  
**Última actualización**: 2026-01-26 23:35:00
