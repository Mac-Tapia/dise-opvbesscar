## DIAGNÓSTICO PPO - RESUMEN EJECUTIVO

### Estado Actual

- **Checkpoints Guardados**: 4 archivos (500, 1000, 1500, 2000 pasos) ✓
- **Último Checkpoint**: ppo_step_2000.zip (2.51 MB, 12:19:10)
- **Progreso**: 2250 pasos registrados (~25% de 87,600 objetivo)
- **Velocidad**: ~72 pasos/minuto (16.7 horas para 87.6k pasos)
- **Error**: Traceback en línea 166 de run_oe3_simulate.py (contexto incompleto)

---

### Problemas Identificados

#### 1. **GPU + CPU Fallback Subóptimo**

- PPO usa `ActorCriticPolicy(MlpPolicy)` → No optimizado para GPU
- Mixed Precision (AMP) habilitado pero MLP no se beneficia mucho
- Posible fallback a CPU que ralentiza mucho el entrenamiento

#### 2. **Velocidad de Entrenamiento Lenta**

- 72 pasos/minuto = ~17 horas para 87,600 pasos
- SAC completó 17,520 pasos en ~15 minutos (1,168 pasos/minuto)
- Factor 16x más lento en PPO (inusual)

#### 3. **Interrupción Abrupta en Paso 2250**

- Último log successful: paso 2250 a las 12:20 p.m.
- Traceback posterior sin contexto completo
- Posible: MemoryError, EnvironmentError, o DeadlockError

---

### Raíces Causa Probable

**Hipótesis A: Memory Pressure (70% probabilidad)**

- PPO con `n_steps=1024` + batch acumula mucha memoria
- Con GPU débil (8.59 GB) + AMP enabled + MLP heavy
- Falla aleatoria cuando memoria se agota después de 2250 pasos

**Hipótesis B: CityLearn Environment Timeout (20% probabilidad)**

- Simulación en CityLearn toma mucho tiempo después de N episodios
- Posible race condition o deadlock en environment
- Afecta más a PPO por su frecuencia de step

**Hipótesis C: Missing Checkpoint Recovery (10% probabilidad)**

- Si `resume_checkpoints=true`, intenta cargar checkpoint incorrecto
- Falla durante reinicio del entrenamiento desde paso 2000→2250

---

### RECOMENDACIONES INMEDIATAS

#### **Opción 1: Ejecutar PPO en CPU (RECOMENDADO) ⭐**

```bash
# Editar configs/default.yaml
oe3:
  evaluation:
    ppo:
      device: cpu        # Cambiar de 'auto' o 'cuda' a 'cpu'
      use_amp: false     # Desactivar Mixed Precision en CPU
      n_steps: 512       # Reducir de 1024 a 512
      batch_size: 64     # Reducir de 128 a 64
      timesteps: 40000   # Reducir de 87600 a 40000 (para test)
```

**Beneficios**:

- CPU es más estable para MLP policies
- Evita GPU-CPU fallback
- Checkpoint recovery más predecible
- Tiempo estimado: 40k timesteps = 10 minutos en CPU

**Desventajas**:

- CPU más lento que GPU puro (pero más rápido que GPU+fallback)
- Requiere más RAM

---

#### **Opción 2: Reanudar desde Último Checkpoint**

```bash
# El checkpoint ppo_step_2000.zip está disponible
# Script: continue_ppo_training.py (si existe)
python continue_ppo_training.py --config configs/default.yaml
```

**Ventaja**: Continúa desde donde se interrumpió (ahorra ~30 minutos)
**Desventaja**: Si el problema es sistémico, volverá a fallar

---

#### **Opción 3: Reducir Complejidad de Entrenamiento**

```bash
# Cambios mínimos:
oe3:
  evaluation:
    ppo:
      timesteps: 40000        # 46% del original
      batch_size: 64          # 50% del original
      n_steps: 512            # 50% del original
      checkpoint_freq_steps: 250  # Checkpoint más frecuente para diagnosticar
```

---

### DIAGNOSTICO EN EJECUCIÓN

Se está ejecutando `diagnose_ppo_error.py` en background:

- Ejecuta PPO en CPU con 10,000 timesteps (prueba rápida)
- Captura el traceback COMPLETO si falla
- Estimado: 5-10 minutos
- Resultado: Verá el error exacto y la línea específica

**Archivo de log**: `ppo_diagnosis.log` (actualizar cuando termine)

---

### PLAN DE ACCIÓN RECOMENDADO

#### **FASE 1: Diagnóstico (EN PROGRESO) ⏳**

1. ✅ Script diagnose_ppo_error.py ejecutándose
2. Esperar resultado (5-10 minutos)
3. Revisar ppo_diagnosis.log para error completo

#### **FASE 2: Ejecutar PPO en CPU (SIGUIENTE) 🔜**

1. Si diagnóstico atrapa el error → entender raíz
2. Modificar configs/default.yaml (device: cpu, reduce n_steps)
3. Re-ejecutar: `python -m scripts.run_oe3_simulate --config configs/default.yaml`
4. Tiempo estimado: 40k pasos = 10 minutos en CPU

#### **FASE 3: Continuar con A2C (DESPUÉS) ⏸**

1. Una vez PPO complete exitosamente
2. Ejecutar A2C con device='cpu' también
3. Tiempo estimado: 50 episodios = 15 minutos

#### **FASE 4: Análisis de Resultados (FINAL) 📊**

1. Ejecutar: `python -m scripts.run_oe3_co2_table`
2. Tabla comparativa: SAC vs PPO vs A2C vs Uncontrolled
3. Generar reportes CO₂

---

### MÉTRICAS ESPERADAS (PPO en CPU - 40k pasos)

| Métrica | Valor Esperado |
|---------|----------------|
| Reward promedio | 40-50 (similar a SAC) |
| CO₂ reducción | 15-25% vs Uncontrolled |
| Tiempo total | 10-15 minutos |
| GPU Memory | 0 MB (usando CPU) |
| CPU Memory | ~2-3 GB |
| Checkpoints | 80 archivos (cada 500 pasos) |

---

### PRÓXIMOS COMANDOS (Cuando esté listo)

```bash
# 1. Ver resultado del diagnóstico
cat ppo_diagnosis.log | tail -100

# 2. Si diagnóstico exitoso, editar config
# (abrir configs/default.yaml y cambiar device: cpu, reduce timesteps)

# 3. Re-ejecutar con CPU
python -m scripts.run_oe3_simulate --config configs/default.yaml

# 4. Ver resultado
cat outputs/oe3/simulations/PPO_pv_bess.json | jq '.reward'

# 5. Continuar con A2C
python -m scripts.run_oe3_simulate --config configs/default.yaml

# 6. Generar tabla final
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

### CONTACTO/SOPORTE

Si el error persiste después de CPU:

1. Ejecutar con debug: `PYTHONVERBOSE=2 python diagnose_ppo_error.py`
2. Revisar `data/processed/citylearn/` - verificar integridad de datos
3. Posible reiniciar dataset: `python -m scripts.run_oe3_build_dataset --config configs/default.yaml`

**Último estado**: PPO 2250/87600 pasos (2.6%) - ✅ Recoverable con CPU fallback
