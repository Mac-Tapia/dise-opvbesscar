# 🚀 LISTO PARA ENTRENAMIENTO - PRÓXIMOS PASOS

## ✅ ESTADO ACTUAL

Todas las correcciones de tipo están **COMPLETADAS** y **VERIFICADAS**.
El sistema está **100% LISTO** para entrenar agentes RL.

---

## 🎯 PASOS SIGUIENTES

### 1️⃣ ENTRENAMIENTO SAC (Recomendado: Más rápido converge)

```bash
python scripts/run_agent_sac.py
```

**Parámetros predeterminados (desde config.yaml):**
- Episodes: 3
- Device: auto (GPU si disponible)
- Checkpoint frequency: 1000 steps
- Learning rate: 5e-5

**Salida esperada:**
- Checkpoints guardados en: `checkpoints/sac/`
- Resultados en: `outputs/agents/sac/`
- Timeseries en: `outputs/oe3_simulations/timeseries_sac.csv`

---

### 2️⃣ ENTRENAMIENTO PPO (Alternativa: Más estable)

```bash
python scripts/run_agent_ppo.py
```

**Parámetros predeterminados:**
- Timesteps: 100000
- N-steps: 1024
- Device: auto
- Checkpoint frequency: 1000 steps

**Salida esperada:**
- Checkpoints guardados en: `checkpoints/ppo/`
- Resultados en: `outputs/agents/ppo/`

---

### 3️⃣ ENTRENAMIENTO A2C (Alternativa: Más simple)

```bash
python scripts/run_agent_a2c.py
```

**Parámetros predeterminados:**
- Timesteps: 100000
- N-steps: 2048
- Device: auto (soporta GPU muy bien)
- Checkpoint frequency: 1000 steps

**Salida esperada:**
- Checkpoints guardados en: `checkpoints/a2c/`
- Resultados en: `outputs/agents/a2c/`

---

## 📊 VALIDACIÓN POST-ENTRENAMIENTO

Después de cada entrenamiento, ejecutar validación de datos técnicos:

```bash
# Validar datos SAC
python scripts/validate_sac_technical_data.py

# Validar datos A2C
python scripts/validate_a2c_technical_data.py
```

**Verifica:**
- ✅ Archivos generados correctamente
- ✅ DataFrames tienen 8760 registros (1 año completo)
- ✅ Columnas requeridas presentes
- ✅ Valores dentro de rangos esperados

---

## 🔍 MONITOREO EN VIVO

Mientras se ejecuta entrenamiento, puedes monitorear progreso:

```bash
# Monitor live training
python scripts/monitor_training_live.py
```

Actualiza cada 5 segundos mostrando:
- Episodios completados
- Reward promedio
- Steps totales
- Convergencia estimada

---

## 📈 COMPARAR RESULTADOS

Después de completar entrenamientos, comparar agentes:

```bash
# Comparar todos los agentes vs baselines
python scripts/compare_all_results.py
```

**Genera:**
- Tabla comparativa CO₂
- Gráficos de convergencia
- Análisis de mejora vs baseline
- Exporta a: `outputs/comparison/`

---

## 🧪 DIAGNÓSTICOS DISPONIBLES

En cualquier momento, ejecutar diagnósticos:

```bash
# A2C pre-training diagnostic
python scripts/diagnose_a2c_data_generation.py

# SAC pre-training diagnostic
python scripts/diagnose_sac_data_generation.py
```

Verifica:
- ✅ Simulador carga correctamente
- ✅ Agentes importan correctamente
- ✅ Dataset CityLearn presente
- ✅ Config multiobjetivo válida
- ✅ Directorios accesibles

---

## ⚙️ CONFIGURACIÓN PERSONALIZADA

Para cambiar parámetros de entrenamiento, editar:

```yaml
# configs/default.yaml

oe3:
  agents:
    sac:
      episodes: 3                    # Cambiar número de episodios
      learning_rate: 5e-5            # Cambiar tasa de aprendizaje
      batch_size: 512                # Cambiar tamaño de batch
    
    ppo:
      train_timesteps: 100000        # Cambiar total de timesteps
      n_steps: 1024                  # Cambiar n-steps
      learning_rate: 3e-4            # Cambiar tasa de aprendizaje
    
    a2c:
      train_timesteps: 100000        # Cambiar total de timesteps
      n_steps: 2048                  # Cambiar n-steps
      learning_rate: 1e-4            # Cambiar tasa de aprendizaje
```

Después de cambiar config, entrenamiento auto-detecta nuevos parámetros.

---

## 🔄 REANUDAR ENTRENAMIENTOS

Si entrenamientos se interrumpen, pueden reanudarse desde último checkpoint:

```bash
# Reanudar SAC desde último checkpoint
python scripts/run_agent_sac.py --resume

# Reanudar PPO desde último checkpoint
python scripts/run_agent_ppo.py --resume

# Reanudar A2C desde último checkpoint
python scripts/run_agent_a2c.py --resume
```

Checkpoints se guardan automáticamente cada 1000 steps.

---

## 📊 RESULTADOS ESPERADOS (Basados en OE2 Real)

### Baseline (Sin control RL):
- **CO₂ Grid Import:** ~190,000 kg/año (con solar)
- **Solar Utilization:** ~40%
- **Grid Independence:** ~25%

### Agentes RL (Esperado después de entrenamiento):
- **SAC:** CO₂ ~-26% vs baseline (carbono-negativo)
- **PPO:** CO₂ ~-29% vs baseline (carbono-negativo)
- **A2C:** CO₂ ~-24% vs baseline (carbono-negativo)

---

## 🐛 TROUBLESHOOTING

### Error: "BESS configuration not found"
```bash
# Reconstruir dataset
python scripts/run_oe3_build_dataset.py --config configs/default.yaml
```

### Error: "CityLearn environment not loaded"
```bash
# Validar dataset
python scripts/validate_dataset.py
```

### Error: "GPU out of memory"
Editar `configs/default.yaml`:
```yaml
training:
  device: "cpu"  # Cambiar de auto a cpu
```

### Error: "Checkpoint mismatch"
```bash
# Limpiar checkpoints antiguos y reiniciar
rm -r checkpoints/sac/*.zip
python scripts/run_agent_sac.py  # Empezará desde cero
```

---

## 📝 LOGS Y MONITOREO

**Logs guardados en:**
- `logs/` - Archivo de logs general
- `outputs/oe3_simulations/` - Resultados por agente
- `checkpoints/` - Checkpoints de entrenamiento

**Monitorear en tiempo real:**
```bash
tail -f logs/*.log
```

---

## ✅ CHECKLIST PRE-ENTRENAMIENTO

Antes de ejecutar entrenamiento, verificar:

- [ ] ✅ Todos los diagnósticos pasan (9/9)
- [ ] ✅ Dataset CityLearn presente
- [ ] ✅ Config YAML válido
- [ ] ✅ Espacio en disco disponible (>50GB recomendado)
- [ ] ✅ Python 3.11 correcto
- [ ] ✅ GPU/CPU disponible (opcional pero recomendado)

---

## 🎯 COMANDOS RÁPIDOS

```bash
# Diagnóstico rápido
python scripts/diagnose_sac_data_generation.py && python scripts/diagnose_a2c_data_generation.py

# Entrenar todos los agentes secuencialmente
python scripts/train_sac_production.py && python scripts/train_ppo_production.py && python scripts/train_a2c_production.py

# Comparar resultados
python scripts/compare_all_results.py

# Generar reporte CO2
python scripts/run_oe3_co2_table.py --config configs/default.yaml
```

---

## 📞 SOPORTE

Si encuentras problemas:

1. **Revisar logs:** `logs/` directory
2. **Ejecutar diagnósticos:** Verificar que pasen 9/9
3. **Validar dataset:** `python scripts/validate_dataset.py`
4. **Limpiar caché:** `rm -r __pycache__ .pylance`

---

## 🎉 ¡LISTO PARA ENTRENAR!

Todo está preparado. Elige tu agente preferido y comienza:

```bash
# Opción 1: SAC (recomendado, converge rápido)
python scripts/run_agent_sac.py

# Opción 2: PPO (estable, buen rendimiento)
python scripts/run_agent_ppo.py

# Opción 3: A2C (simple, usa GPU bien)
python scripts/run_agent_a2c.py
```

---

**Última validación:** 2026-02-04 00:51:52  
**Status:** ✅ PRODUCTION READY  
**Próximo paso:** Ejecutar entrenamiento de tu agente preferido

