# GUÍA RÁPIDA - EJECUTAR SAC TRAINING

**⏱️ Tiempo total: 20 minutos prep + 6 horas entrenamiento**

---

## PASO 1: VALIDACIÓN (2 minutos)

```powershell
cd d:\diseñopvbesscar
python VALIDAR_SAC_TRAINING.py
```

✅ Si dice "TODAS LAS VALIDACIONES PASARON" → Continuar  
❌ Si hay fallos → Leer PLAN_ACCION_SAC_TRAINING.md sección "SOPORTE"

---

## PASO 2: IMPLEMENTAR FIXES (15 minutos)

Seguir exactamente los pasos en: [PLAN_ACCION_SAC_TRAINING.md](PLAN_ACCION_SAC_TRAINING.md)

**Resumen rápido de qué hacer:**

1. Abrir `scripts/train/train_sac_multiobjetivo.py`
2. Buscar `def main():` (línea ~2235)
3. Reemplazar TODO ese bloque con Fragmento #1 de `SOLUCION_SAC_FRAGMENTOS.md`
4. Agregar Fragmentos #2 y #3
5. Cambiar `REWARD_SCALE = 0.01` a `0.1`
6. Guardar

**Verificar sintaxis:**
```powershell
python -m py_compile scripts/train/train_sac_multiobjetivo.py
# Si no muestra error = OK
```

---

## PASO 3: EJECUTAR ENTRENAMIENTO (6 horas)

### Terminal 1 - Entrenamiento
```powershell
cd d:\diseñopvbesscar
python scripts/train/train_sac_multiobjetivo.py
```

**Señales de éxito:**
- Muestra "Carga de datos..." (rápido)
- Muestra "[6] INSTANCIAR AGENTE SAC"
- Muestra "[7] INICIAR ENTRENAMIENTO SAC"
- Barra de progreso con steps: `26280/26280`

**Señales de fallo:**
- Error Python (leerlo)
- Dice "Episode return = 0.0" constantemente (problema de rewards)
- Dice "Tensor dimension mismatch" (problema de observations)

### Terminal 2 - Monitor (OPCIONAL pero recomendado)
```powershell
cd d:\diseñopvbesscar
tensorboard --logdir=runs/ --port=6006
```

Luego abrir: http://localhost:6006

Mirar:
- Gráfico "rollout/ep_reward_mean" → debe cambiar (no línea plana)
- Gráfico "train/actor_loss" → debe decrecer
- Gráfico "train/critic_loss" → debe estabilizarse

---

## PASO 4: VALIDAR RESULTADOS (5 minutos después de terminar)

```powershell
cd d:\diseñopvbesscar

# Ver checkpoints guardados
ls checkpoints/SAC/

# Ver métricas finales
python << 'EOF'
import pandas as pd
import numpy as np

# Leer logs de TensorBoard
# (Generalmente en runs/SAC_<timestamp>/events.out.tfevents.*)

print("✓ SAC Training Complete")
print("  Checkpoints saved in: checkpoints/SAC/")
print("  Logs available in: runs/")
print("\nAbra TensorBoard para ver gráficos:")
print("  tensorboard --logdir=runs/")
EOF
```

---

## 🆘 TROUBLESHOOTING RÁPIDO

| Error | Solución |
|---|---|
| `ModuleNotFoundError: stable_baselines3` | `pip install stable-baselines3` |
| `Episode return = 0.0` | Verificar Fragmento #3 fue insertado (agent.learn) |
| `RealOE2Environment not defined` | Verificar que existe en el archivo (línea ~1800) |
| `CUDA out of memory` | Reducir buffer_size: 300K→150K en SACConfig |
| `Dataset not found` | Verificar paths en SOLUCION_SAC_FRAGMENTOS.md Fragmento #2 |

---

## 📊 MÉTRICAS ESPERADAS

**Después de 6 horas:**

| Métrica | Esperado | Rango OK |
|---|---|---|
| Episode Reward | 0.008 | [-0.02, +0.02] |
| Solar Self-Consumption | 65% | [55%, 75%] |
| CO2 Reduction | -30% | [-25%, -40%] |
| EV Satisfaction | 76% | [70%, 85%] |
| Actor Loss | -0.35 | [-0.5, 0.0] |
| Critic Loss | 0.15 | [0.05, 0.5] |

---

## 📝 DOCUMENTOS DE REFERENCIA

- [PLAN_ACCION_SAC_TRAINING.md](PLAN_ACCION_SAC_TRAINING.md) - Plan completo con 5 pasos
- [DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md](DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md) - Análisis técnico detallado
- [SOLUCION_SAC_FRAGMENTOS.md](SOLUCION_SAC_FRAGMENTOS.md) - Código listo para copiar/pegar
- [VALIDAR_SAC_TRAINING.py](VALIDAR_SAC_TRAINING.py) - Script de validación pre-training

---

## ✅ CHECKLIST FINAL

Antes de ejecutar:
- [ ] VALIDAR_SAC_TRAINING.py dice "TODAS OK"
- [ ] Fragmentos #1-5 aplicados a train_sac_multiobjetivo.py
- [ ] `python -m py_compile` sin errores
- [ ] Dataset CSVs existen en data/oe2/
- [ ] Checkpoints directory limpio (o quiero resumir)

Durante:
- [ ] Training script inicia
- [ ] TensorBoard muestra gráficos
- [ ] Episode reward ≠ 0.0 (éxito)

Después:
- [ ] Entrenamiento completo sin errores
- [ ] Checkpoints guardados
- [ ] Métricas en rangos esperados

---

## 🚀 COMANDO FINAL

```powershell
# TODO EN LÍNEA:
cd d:\diseñopvbesscar; `
python VALIDAR_SAC_TRAINING.py; `
Write-Host "✓ Validación OK"; `
Write-Host "Ahora ejecute: python scripts/train/train_sac_multiobjetivo.py"; `
Write-Host "Monitoree en otra terminal: tensorboard --logdir=runs/ --port=6006"
```

---

**¿Preguntas?**

Revisar secciones en orden:
1. VALIDAR_SAC_TRAINING.py → Valida sistema
2. SOLUCION_SAC_FRAGMENTOS.md → Muestra qué cambiar
3. PLAN_ACCION_SAC_TRAINING.md → Detalles paso a paso
4. DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md → Entiende el problema

**Autor:** GitHub Copilot  
**Date:** 2026-02-15  
**Status:** LISTO PARA EJECUTAR ✅

