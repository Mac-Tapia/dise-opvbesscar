# 📑 ÍNDICE DE DOCUMENTACIÓN - ENTRENAMIENTO RL

**Actualizado**: Enero 25, 2026

---

## 🎯 COMIENZA AQUÍ

### Para Empezar Rápido (5-10 min)

1. Leer: [TRAINING_READY.md](TRAINING_READY.md) - Resumen ejecutivo
2. Ejecutar: `python src/iquitos_citylearn/oe3/agents/validate_training_env.py`
3. Entrenar: `python scripts/train_quick.py --device cuda --episodes 5`

### Para Entrenamiento Completo

1. Leer: [TRAINING_CHECKLIST.md](TRAINING_CHECKLIST.md) - Checklist de
validación
2. Seguir: Step-by-step en el checklist
3. Entrenar: `python scripts/train_agents_serial.py --device cuda --episodes 50`

---

<!-- markdownlint-disable MD013 -->
## 📚 DOCUMENTACIÓN PRINCIPAL | Documento | Propósito | Tiempo | |-----------|-----------|--------|
|[TRAINING_READY.md](TRAINING_READY.md)|Resumen ejecutivo y estado actual|5 min|
|[TRAINING_CHECKLIST.md](TRAINING_CHECKLIST.md)|Validación paso-a-paso (10 pasos)|10-20 min|
|[QUICK_REFERENCE_TRAINING.py](QUICK_REFERENCE_TRAINING.py)|Copy-paste commands + FAQ|5 min| |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| ---

## 🔧 MEJORAS IMPLEMENTADAS

### Archivos Mejorados

<!-- markdownlint-disable MD013 -->
```bash
✓ src/iquitos_citylearn/oe3/agents/__init__.py
  - Device detection unificada
  - Imports mejorados

✓ src/iquitos_citylearn/oe3/agents/ppo_sb3.py
  - Docstrings mejorados

✓ src/iquitos_citylearn/oe3/agents/sac.py
  - Logging mejorado
  - Error handling robusto

✓ src/iquitos_citylearn/oe3/agents/a2c_sb3.py
  - Logging mejorado
  - Error handling robusto
```bash
<!-- markdownlint-enable MD013 -->...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🚀 COMANDOS PRINCIPALES

### Validación Pre-Entrenamiento

<!-- markdownlint-disable MD013 -->
```bash
python src/iquitos_citylearn/oe3/agents/validate_training_env.py
```bash
<!-- markdownlint-enable MD013 -->

### Entrenamiento Rápido (5 episodios, ~5 min)

<!-- markdownlint-disable MD013 -->
```bash
python scripts/train_quick.py --device cuda --episodes 5
```bash
<!-- markdownlint-enable MD013 -->

### Entrenamiento Completo (50 episodios, ~1-2 horas)

<!-- markdownlint-disable MD013 -->
```bash...
```

[Ver código completo en GitHub]bash
python scripts/monitor_training_live_2026.py
```bash
<!-- markdownlint-enable MD013 -->

### Ver Resultados

<!-- markdownlint-disable MD013 -->
```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 ESTADO ACTUAL

<!-- markdownlint-disable MD013 -->
```bash
✅ Agentes importables: PPOAgent, SACAgent, A2CAgent
✅ Device detection: CUDA/MPS/CPU auto-detect
✅ Rewards normalizados: ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🎓 GUÍAS POR CASO DE USO

### "Quiero entrenar rápido para verificar que funciona"

1. Lee: [TRAINING_READY.md](TRAINING_READY.md)
2. Ejecuta: `python scripts/train_quick.py --device cuda --episodes 5`
3. Tiempo: ~5-10 minutos

### "Quiero entrenamiento completo con resultados"

1. Lee: [TRAINING_CHECKLIST.md](TRAINING_CHECKLIST.md)
2. Sigue pasos 1-7
3. Ejecuta: `python scripts/train_agents_serial.py --device cuda --episodes 50`
4. Tiempo: ~1-2 horas

### "Tengo un problema o error"

1. Consulta: [QUICK_REFERENCE_TRAINING.py](QUICK_REFERENCE_TRAINING.py) -
sección "TROUBLESHOOTING"
2. O: [AGENTS_IMPROVEMENTS_SUMMARY.md](AGENTS_IMPROVEMENTS_SUMMARY.md) - tabla
de problemas

### "Quiero entender los cambios"

1. Lee: [AGENTS_IMPROVEMENTS_SUMMARY.md](AGENTS_IMPROVEMENTS_SUMMARY.md)
2. Revisa: `git diff` (si está en git)

### "Quiero ajustar parámetros"

1. Consulta: [QUICK_REFERENCE_TRAINING.py](QUICK_REFERENCE_TRAINING.py) -
sección "PARÁMETROS AJUSTABLES"
2. Edita: `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` etc.
3. Reentrana: `python scripts/train_quick.py --device cuda --episodes 5`

---

## 🔗 DOCUMENTACIÓN RELACIONADA

### Archivos del Proyecto

- [README.md](README.md) - Descripción general del proyecto
- [.github/copilot-instructions.md](.github/copilot-instructions.md) -
  - Instrucciones para agentes IA (630 líneas, exhaustivo)
- [configs/default.yaml](configs/default.yaml) - Configuración de parámetros
  - OE2/OE3

### Código Fuente Clave

- [src/iquitos_citylearn/oe3/agents/](src/iquitos_citylearn/oe3/agents/) -
  - Agentes RL
- [src/iquitos_citylearn/oe3/rewards.py](src/iquitos_citylearn/oe3/rewards.py)
  - - Función de recompensas
- [src/iquitos_citylearn/oe3/dataset_builder.py][url1]
- - Constructor de dataset

### Scripts Útiles

- [scripts/train_quick.py](scripts/train_quick.py) - Entrenamiento rápido ✨
  - NUEVO
- [scripts/train_agents_serial.py](scripts/train_agents_serial.py) -
  - Entrenamiento serial
- [scripts/monitor_training_live_2026.py](scripts/monitor_training_live_2026.py)
- - Monitor de progreso
- [scripts/run_oe3_build_dataset.py](scripts/run_oe3_build_dataset.py) -
  - Constructor de dataset

---

## ✨ DESTACADOS NUEVOS

### 🆕 Utilities Centralizadas

Archivo: `src/iquitos_citylearn/oe3/agents/agent_utils.py`

- Validación de espacios
- Wrapping de observaciones
- Normalización/scaling
- Manejo de checkpoints
- 150+ líneas de utilidades

### 🆕 Validación Automática

Archivo: `src/iquitos_citylearn/oe3/agents/validate_training_env.py`

- Verifica 4 puntos clave
- Reportes visuales
- Exit codes para automatización
- 100+ líneas

### 🆕 Script de Entrenamiento Mejorado

Archivo: `scripts/train_quick.py`

- Validación integrada
- Auto-búsqueda de schema
- Reportes detallados
- Guardado de resultados JSON
- 250+ líneas

---

## 📈 MÉTRICAS ESPERADAS

<!-- markdownlint-disable MD013 -->
Después de entrenamiento con 50 episodios: | Métrica | Baseline | SAC | PPO | A2C | |---------|----------|-----|-----|-----| | CO₂ emissions | 10,200 kg | 7,500 kg | 7,200 kg | 7,800 kg | | Reducción CO₂ | 0% | -26% | -29% | -24% | | Solar utilization | 40% | 65% | 68% | 60% | | Training time/ep | N/A | 1 hr | 1 hr | 45 min | ---

## ⚡ QUICK START (Una Línea)

<!-- markdownlint-disable MD013 -->
```bash
<details>
<summary>python -m venv .venv && .venv\Scripts\Activate.ps1 && pip install -r requirement...</summary>

python -m venv .venv && .venv\Scripts\Activate.ps1 && pip install -r requirements.txt -q && python src/iquitos_citylearn/oe3/agents/validate_training_env.py && python scripts/train_quick.py --device cuda --episodes 5

</details>
```bash
<!-- markdownlint-enable MD013 -->

---

## 🎯 Próximas Acciones

- [ ] Leer [TRAINING_READY.md](TRAINING_READY.md)
- [ ] Ejecutar validación: `python
  - src/iquitos_citylearn/oe3/agents/validate_training_env.py`
- [ ] Iniciar entrenamiento: `python scripts/train_quick.py --device cuda
  - --episodes 5`
- [ ] Monitorear: `python scripts/monitor_training_live_2026.py`
- [ ] Ver resultados: `python -m scripts.run_oe3_co2_table`

---

**Estado**: ✅ **LISTO PARA ENTRENAMIENTO**

Consulta [TRAINING_READY.md](TRAINING_READY.md) para comenzar ahora.


[url1]: src/iquitos_citylearn/oe3/dataset_builder.py