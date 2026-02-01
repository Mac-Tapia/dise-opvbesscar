# 📋 Scripts Esenciales - Pipeline de Entrenamiento OE3

**Última actualización:** 2026-02-01  
**Estado:** ✅ Limpio y optimizado  
**Archivos:** 6 scripts core + 80+ en `archive/`

---

## 🎯 Pipeline Completo (Flujo de Trabajo)

```
┌─────────────────────────────────────────────────────────┐
│ 1. CONSTRUCCIÓN DE DATASET (30-60 seg, GPU opcional)   │
│    python -m scripts.run_oe3_build_dataset             │
│    ├─ Lee OE2 artifacts (solar, chargers, BESS)       │
│    ├─ Genera CityLearn schema                         │
│    └─ Crea 128 charger_simulation_*.csv               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. ENTRENAMIENTO COMPLETO (45-60 min, GPU recomendado) │
│    python -m scripts.run_training_sequence             │
│    ├─ Baseline: uncontrolled (1 min)                  │
│    ├─ SAC: 10 episodes (20-25 min)                    │
│    ├─ PPO: 100,000 timesteps (15-20 min)             │
│    └─ A2C: 50,000 timesteps (10-15 min)              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. RESULTADOS COMPARATIVOS (5-10 seg)                 │
│    python -m scripts.run_oe3_co2_table                 │
│    └─ Genera tabla CO2, gráficas, métricas multiobjetivo│
└─────────────────────────────────────────────────────────┘
```

---

## 📄 Scripts Esenciales Detallados

### **1. `_common.py`** (Utilidad)
**Propósito:** Cargar configuración y validar Python 3.11  
**Uso interno:** Importado por otros scripts  
**Qué hace:**
- Verifica Python 3.11 exactamente
- Carga `config.yaml` + variables de entorno
- Configura rutas del proyecto

```bash
# No ejecutar directamente (es un módulo)
python -c "from scripts._common import load_all"
```

---

### **2. `run_oe3_build_dataset.py`** ✅ **[STEP 1]**
**Propósito:** Construir dataset de CityLearn desde artifacts OE2  
**Entrada:** OE2 artifacts (solar, chargers, BESS, mall demand)  
**Salida:** `processed/citylearn/oe3/schema.json` + 128 CSVs

```bash
# Ejecutar PRIMERO (obligatorio):
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Tiempo: ~30-60 segundos
# GPU: No requerido
```

**Qué hace:**
- ✅ Valida solar timeseries (8,760 horas exactas)
- ✅ Descarga template CityLearn
- ✅ Actualiza PV (4,050 kWp) y BESS (4,520 kWh)
- ✅ Genera 128 archivos charger_simulation_*.csv
- ✅ Configura 5 prioridades de despacho automático

---

### **3. `run_oe3_simulate.py`** 🤖 **[STEP 2 - Agentes]**
**Propósito:** Entrenar agentes RL (SAC, PPO, A2C) o ejecutar baseline  
**Entrada:** Schema de CityLearn  
**Salida:** Checkpoints + timeseries + métricas

```bash
# Baseline (sin RL):
python -m scripts.run_oe3_simulate --agent uncontrolled --config configs/default.yaml

# SAC (off-policy, 10 episodios):
python -m scripts.run_oe3_simulate --agent sac --config configs/default.yaml

# PPO (on-policy, 100k timesteps):
python -m scripts.run_oe3_simulate --agent ppo --config configs/default.yaml --ppo-timesteps 100000

# A2C (on-policy simple, 50k timesteps):
python -m scripts.run_oe3_simulate --agent a2c --config configs/default.yaml --a2c-timesteps 50000

# Todos en paralelo (vía terminal separadas):
# Terminal 1: python -m scripts.run_oe3_simulate --agent sac
# Terminal 2: python -m scripts.run_oe3_simulate --agent ppo
# Terminal 3: python -m scripts.run_oe3_simulate --agent a2c
```

**Parámetros principales:**
```bash
--agent {uncontrolled,sac,ppo,a2c}    # Agente a entrenar
--config PATH                          # Config YAML
--sac-episodes 10                      # SAC episodes (default: 10)
--ppo-timesteps 100000                 # PPO timesteps (default: 100000)
--a2c-timesteps 50000                  # A2C timesteps (default: 50000)
--use-multi-objective                  # Recompensa multiobjetivo (default: True)
--multi-objective-priority {balanced,co2_focus,cost_focus,ev_focus,solar_focus}
--deterministic-eval                   # Evaluación determinística
--sac-device auto                      # GPU: "cuda", "cuda:0", o "cpu"
--ppo-device auto                      # GPU: "cuda", "cuda:0", o "cpu"
--a2c-device cpu                       # A2C: generalmente CPU
--sac-resume-checkpoints               # Reanudar desde último checkpoint
--ppo-resume-checkpoints               # Reanudar desde último checkpoint
--a2c-resume-checkpoints               # Reanudar desde último checkpoint
```

**Duración estimada (GPU RTX 4060):**
- Uncontrolled: ~10 segundos
- SAC 10 episodes: ~20-25 minutos
- PPO 100k timesteps: ~15-20 minutos
- A2C 50k timesteps: ~10-15 minutos
- **Total (todos 4): ~50-70 minutos**

---

### **4. `run_training_sequence.py`** 🚀 **[STEP 2 - Orquestación]**
**Propósito:** Ejecutar pipeline completo (dataset + todos los agentes)  
**Entrada:** Config YAML  
**Salida:** Dataset + 4 agentes entrenados + resultados

```bash
# Ejecutar PIPELINE COMPLETO (recomendado):
python -m scripts.run_training_sequence --config configs/default.yaml

# Tiempo total: ~50-70 minutos (GPU)
# Incluye: dataset → uncontrolled → SAC → PPO → A2C
```

**Qué hace (secuencial):**
1. ✅ `run_oe3_build_dataset` - Construir dataset
2. ✅ `run_oe3_simulate --agent uncontrolled` - Baseline
3. ✅ `run_oe3_simulate --agent sac` - SAC training
4. ✅ `run_oe3_simulate --agent ppo` - PPO training
5. ✅ `run_oe3_simulate --agent a2c` - A2C training
6. ✅ `run_oe3_co2_table` - Generar tabla comparativa

---

### **5. `run_uncontrolled_baseline.py`** 📊 **[STEP 2 - Baseline]**
**Propósito:** Ejecutar baseline sin control inteligente  
**Entrada:** Schema de CityLearn  
**Salida:** Métricas baseline (CO2 sin optimización)

```bash
# Ejecutar SOLO baseline (para referencia):
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Tiempo: ~10 segundos
# GPU: No requerido
```

**Resultados esperados (Iquitos, thermal grid):**
- CO₂: ~5,710,257 kg/año (sin control)
- Solar utilization: ~40%
- Grid import: ~4,975 MWh/año

---

### **6. `run_oe3_co2_table.py`** 📈 **[STEP 3]**
**Propósito:** Generar tabla comparativa de agentes  
**Entrada:** Timeseries de simulaciones  
**Salida:** Tabla CO2, gráficas, métricas multiobjetivo

```bash
# Generar RESULTADOS COMPARATIVOS:
python -m scripts.run_oe3_co2_table --config configs/default.yaml

# Tiempo: ~5-10 segundos
# GPU: No requerido

# Genera:
# ├─ outputs/oe3_simulations/CO2_COMPARISON_TABLE.csv
# ├─ outputs/oe3_simulations/co2_comparison_chart.png
# ├─ outputs/oe3_simulations/agents_comparison_metrics.json
# └─ analyses/multi_objective_comparison.md
```

**Tabla típica (Iquitos):**
```
Agent              CO₂ (kg/año)    Reduction    Solar (%)    Cost (USD)    Reward
──────────────────────────────────────────────────────────────────────────────
Uncontrolled    5,710,257       0.0%        40.0%       $180,000      0.00
SAC             4,280,119      -25.0%       65.2%       $140,000      0.68
PPO             4,120,000      -27.8%       68.1%       $132,000      0.72
A2C             4,380,000      -23.3%       62.5%       $138,000      0.65
```

---

## 🎓 Flujo de Trabajo Completo (Guía Paso a Paso)

### **Opción A: Pipeline Completo (Recomendado - 50-70 min)**
```bash
# 1 comando = todo automático
python -m scripts.run_training_sequence --config configs/default.yaml
```

### **Opción B: Paso a Paso (Manual - 70-90 min)**
```bash
# PASO 1: Construir dataset (30-60 seg)
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# PASO 2: Ejecutar agentes en paralelo (terminal separadas)
# Terminal 1:
python -m scripts.run_oe3_simulate --agent uncontrolled

# Terminal 2:
python -m scripts.run_oe3_simulate --agent sac --sac-episodes 10

# Terminal 3:
python -m scripts.run_oe3_simulate --agent ppo --ppo-timesteps 100000

# Terminal 4:
python -m scripts.run_oe3_simulate --agent a2c --a2c-timesteps 50000

# PASO 3: Generar resultados (10 seg)
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

### **Opción C: Agentes Individuales (Debugging - Variable)**
```bash
# Solo baseline (10 seg):
python -m scripts.run_oe3_simulate --agent uncontrolled

# Solo SAC rápido (2 episodes, 5 min):
python -m scripts.run_oe3_simulate --agent sac --sac-episodes 2

# Solo PPO rápido (10k timesteps, 2 min):
python -m scripts.run_oe3_simulate --agent ppo --ppo-timesteps 10000

# Solo A2C rápido (5k timesteps, 1 min):
python -m scripts.run_oe3_simulate --agent a2c --a2c-timesteps 5000

# Con reanudar checkpoints (si existen):
python -m scripts.run_oe3_simulate --agent sac --sac-resume-checkpoints
```

---

## 📂 Archivos de Entrada/Salida

### **Entrada (OE2 Artifacts):**
```
data/interim/oe2/
├── solar/pv_generation_timeseries.csv          (8,760 horas, SIN 15-min)
├── chargers/individual_chargers.json           (32 chargers)
├── chargers/perfil_horario_carga.csv          (perfil 24h)
├── chargers/chargers_hourly_profiles_annual.csv (8,760 × 128)
├── bess/bess_results.json                      (capacidad, potencia)
└── demandamallkwh/demanda_mall_horaria_anual.csv (8,760 horas)
```

### **Salida (Resultados):**
```
outputs/oe3_simulations/
├── timeseries_uncontrolled.csv                 (energía por hora)
├── timeseries_sac.csv                          (energía por hora)
├── timeseries_ppo.csv                          (energía por hora)
├── timeseries_a2c.csv                          (energía por hora)
├── trace_sac.csv                               (observaciones + acciones)
├── trace_ppo.csv
├── trace_a2c.csv
├── CO2_COMPARISON_TABLE.csv                    (tabla resumen)
├── co2_comparison_chart.png                    (gráfica comparativa)
└── agents_comparison_metrics.json

checkpoints/
├── sac/
│   ├── sac_step_1000.zip
│   ├── sac_step_2000.zip
│   └── sac_final.zip
├── ppo/
│   ├── ppo_step_1000.zip
│   └── ppo_final.zip
└── a2c/
    └── a2c_final.zip
```

---

## 🚨 Errores Comunes y Soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| "Solar timeseries MUST be exactly 8,760 rows" | Datos PVGIS 15-min (52,560 filas) | `df.set_index('time').resample('h').mean()` |
| "128 chargers not found" | Falta individual_chargers.json | Verificar `data/interim/oe2/chargers/` |
| "Python 3.11 EXACTAMENTE es requerido" | Python 3.12+ instalado | Instalar Python 3.11 exactamente |
| "CUDA out of memory" | GPU insuficiente (SAC/PPO) | `--sac-device cpu` o reducir batch_size |
| "Reward NaN/Inf" | Config multiobjetivo inválida | Verificar pesos suman 1.0 en `rewards.py` |
| "Cannot load checkpoint" | Agente/config cambió | Entrenar desde cero (sin `--*-resume-checkpoints`) |

---

## 📊 Configuración Recomendada

### **Para Desarrollo (Rápido, 10-15 min):**
```bash
python -m scripts.run_training_sequence \
  --config configs/default.yaml \
  --sac-episodes 2 \
  --ppo-timesteps 10000 \
  --a2c-timesteps 5000
```

### **Para Producción (Completo, 50-70 min):**
```bash
python -m scripts.run_training_sequence \
  --config configs/default.yaml \
  --use-multi-objective \
  --multi-objective-priority co2_focus \
  --sac-resume-checkpoints \
  --ppo-resume-checkpoints \
  --a2c-resume-checkpoints
```

### **Para GPU Optimizado:**
```bash
python -m scripts.run_training_sequence \
  --config configs/default.yaml \
  --sac-device cuda:0 \
  --ppo-device cuda:0 \
  --a2c-device cpu  # A2C es más eficiente en CPU
```

---

## ✅ Checklist de Ejecución

```
ANTES DE ENTRENAR:
☐ Python 3.11 exactamente instalado
☐ OE2 artifacts en data/interim/oe2/
☐ Solar timeseries es 8,760 horas (NO 15-min)
☐ Chargers JSON y perfil cargados
☐ BESS results en oe2/bess/
☐ Mall demand en oe2/demandamallkwh/
☐ GPU disponible (recomendado pero no obligatorio)

EJECUCIÓN:
☐ python -m scripts.run_oe3_build_dataset (primero)
☐ Verificar data/processed/citylearn/oe3/schema.json existe
☐ python -m scripts.run_training_sequence (completo)
  O ejecutar agentes individuales en paralelo
☐ python -m scripts.run_oe3_co2_table (al final)

VERIFICACIÓN:
☐ Tabla CO2 mostrada en outputs/oe3_simulations/
☐ Gráficas generadas correctamente
☐ Checkpoints guardados en checkpoints/
☐ Métricas multiobjetivo registradas
```

---

## 📞 Referencias Rápidas

- **Config:** [configs/default.yaml](../configs/default.yaml)
- **Copilot Instructions:** [.github/copilot-instructions.md](../.github/copilot-instructions.md)
- **Flujo Completo:** [FLUJO_TRABAJO_TRAINING_ACTUAL.md](../FLUJO_TRABAJO_TRAINING_ACTUAL.md)
- **Checklist:** [CHECKLIST_ENTRENAMIENTO.md](../CHECKLIST_ENTRENAMIENTO.md)

---

**Última limpieza:** 2026-02-01  
**Estado:** ✅ 6 scripts esenciales + 80+ archivados  
**Listo para:** Entrenamiento inmediato
