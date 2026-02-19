# TUNING DE HIPERPARÁMETROS PARA SAC
## Sistema de Optimización Automática v2.0

> **Última actualización:** 2026-02-19  
> **Estado:** ✅ OPERATIVO - Listo para testing

---

## 📋 Resumen

Este sistema implementa **3 algoritmos de búsqueda** para optimizar automáticamente los hiperparámetros de SAC (Soft Actor-Critic):

| Algoritmo | Velocidad | Calidad | Mejor Para | Complejidad |
|-----------|-----------|---------|-----------|-------------|
| **Grid Search** | 🟡 Lento | ⭐⭐⭐ Excelente | Espacios pequeños (<1000 combos) | O(grid_size) |
| **Random Search** | 🟢 Rápido | ⭐⭐ Bueno | Espacios grandes (>10K combos) | O(n_samples) |
| **Bayesian Opt** | 🟡 Moderado | ⭐⭐⭐⭐ Óptimo | Explotación inteligente (RECOMENDADO) | O(n × GP_fitting) |

---

## 🚀 Instalación Rápida

```bash
# Ya implementado en:
# - src/agents/sac_hyperparameter_tuner.py (motor de búsqueda)
# - scripts/train/run_sac_hyperparameter_tuning.py (script ejecutable)

# No hay dependencias adicionales (usa scipy, numpy, pandas ya instalados)
```

---

## 💻 Modo de Uso

### 1. BAYESIAN OPTIMIZATION (RECOMENDADO)
```bash
cd d:\diseñopvbesscar

# Ejecución básica (30 iteraciones)
python scripts/train/run_sac_hyperparameter_tuning.py --method bayesian

# Con opciones personalizadas
python scripts/train/run_sac_hyperparameter_tuning.py \
  --method bayesian \
  --num-iterations 50 \
  --episodes 15  # Entrenar 15 episodios por config (defecto: 2 para testing)

# Modo TEST (simula sin entrenar)
python scripts/train/run_sac_hyperparameter_tuning.py --method bayesian --test
```

**Salida esperada:**
```
================================================================================
BAYESIAN OPTIMIZATION HYPERPARAMETER TUNING
================================================================================
Iteraciones completadas: 30/30

Mejor configuración encontrada:
  Score: 87.3/100
  LR=2.5e-04 | Buf=400K | τ=0.0050
  CO2 Evitado: 1,050,000 kg
  Reward: 4.25

Mejora respecto a baseline: +15.2%
================================================================================
```

### 2. GRID SEARCH (exhaustivo)
```bash
# Probar 50 configs sistematicamente (de ~390K posibles)
python scripts/train/run_sac_hyperparameter_tuning.py \
  --method grid \
  --max-configs 50 \
  --episodes 5

# Con modo test
python scripts/train/run_sac_hyperparameter_tuning.py --method grid --max-configs 20 --test
```

### 3. RANDOM SEARCH (exploratorio)
```bash
# Samplear 50 configs aleatorias
python scripts/train/run_sac_hyperparameter_tuning.py \
  --method random \
  --num-samples 50 \
  --episodes 3
```

---

## 📊 Salidas Generadas

Todas las salidas se guardan en `outputs/hyperparameter_tuning/`:

```
outputs/hyperparameter_tuning/
├── bayesian_opt_20260219_133022.csv        # Todos los entrenamientos + métricas
├── config_optimal_20260219_133022.json     # Mejor config (JSON)
├── grid_search_20260219_134500.csv         # Solo si usas Grid Search
└── random_search_20260219_133500.csv       # Solo si usas Random Search
```

### CSV con Resultados

```csv
learning_rate,buffer_size,batch_size,tau,gamma,...,score,co2_avoided_kg,avg_episode_reward
0.0001,100000,64,0.005,0.99,...,87.3,1050000,4.25
0.00003,400000,128,0.01,0.99,...,84.1,990000,3.80
...
```

**Columnas principales:**
- `learning_rate`, `buffer_size`, `batch_size`, etc. → Hiperparámetros
- `score` → Score agregado (0-100) para comparación rápida
- `co2_avoided_kg` → Métrica clave: CO2 evitado anual
- `avg_episode_reward` → Reward promedio por episodio
- `solar_utilization_pct` → % de solar utilizado
- `grid_import_kwh` → Importación grid (menor es mejor)
- `ev_satisfaction_pct` → Vehículos cargados al 100%
- `convergence_speed` → Steps para alcanzar mejor reward
- `stability` → Varianza de rewards (menor = más estable)

### JSON con Mejor Configuración

```json
{
  "learning_rate": 0.00025,
  "buffer_size": 400000,
  "batch_size": 64,
  "tau": 0.005,
  "gamma": 0.99,
  "ent_coef": "auto",
  "target_entropy": -20,
  "train_freq": 2,
  "net_arch_hidden": 384,
  "network_arch": [384, 384],
  "metadata": {
    "score": 87.3,
    "co2_avoided_kg": 1050000,
    "avg_episode_reward": 4.25,
    "timestamp": "2026-02-19T13:30:22"
  }
}
```

---

## 🔧 Integración con train_sac.py

Una vez encontrados los mejores hiperparámetros, usar en `train_sac.py`:

```python
# En scripts/train/train_sac.py, cerca de la creación del agente:

# ANTES (parametros por defecto)
sac_config = SACConfig.for_gpu()

# DESPUES (usar mejores hiperparámetros)
sac_config = SACConfig(
    learning_rate=0.00025,        # De tuning
    buffer_size=400_000,          # De tuning
    batch_size=64,                # De tuning
    tau=0.005,                    # De tuning
    gamma=0.99,                   # De tuning
    ent_coef='auto',              # De tuning
    target_entropy=-20,           # De tuning
    train_freq=(2, 'step'),       # De tuning
    policy_kwargs={'net_arch': dict(pi=[384, 384], qf=[384, 384])}  # De tuning
)
```

---

## 📈 Espacio de Búsqueda

Los algoritmos prueban estos rangos de hiperparámetros:

```python
{
    'learning_rate': [1e-5, 3e-5, 1e-4, 3e-4, 1e-3],
    'buffer_size': [50K, 100K, 200K, 400K, 1M],
    'batch_size': [32, 64, 128, 256, 512],
    'tau': [0.001, 0.005, 0.01, 0.02],
    'gamma': [0.90, 0.95, 0.99],
    'ent_coef': ['auto', 0.05, 0.1, 0.2, 0.5],
    'target_entropy': [-50, -20, -10, -5],
    'train_freq': [1, 2, 4, 8],
    'net_arch_hidden': [128, 256, 384, 512]
}

# Total: 5×5×5×4×3×5×4×4×4 = 96,000 combinaciones posibles
```

---

## 📊 Métricas de Evaluación

Cada configuración se evalúa en:

### Métricas Principales
1. **CO2 Evitado** (50% peso) → `co2_avoided_kg`
   - Solar + BESS vs Grid
   - Objetivo: Maximizar

2. **Reward Promedio** (20% peso) → `avg_episode_reward`
   - Promedio sobre episodios compl
   - Objetivo: Maximizar

3. **Velocidad de Convergencia** (15% peso) → `convergence_speed`
   - Steps para alcanzar 80% del reward final
   - Objetivo: Minimizar

4. **Estabilidad** (10% peso) → `stability`
   - Varianza de rewards (menor = mejor)
   - Objetivo: Minimizar

5. **Solar Utilization** (5% peso) → `solar_utilization_pct`
   - % de energía solar usada (no desperdiciada)
   - Objetivo: Maximizar

### Cálculo del Score
```
Score = 0.50 × CO2_score + 0.20 × Reward_score + 0.15 × Convergence_score + 
        0.10 × Stability_score + 0.05 × Solar_score
```

Escala: 0-100 (100 = óptimo)

---

## 🎯 Estrategias Recomendadas

### Para Problema Iquitos EV
**Recomendación: Bayesian Optimization**
- ✅ Converge en 30-50 iteraciones
- ✅ Usa información de entrenamientos previos
- ✅ Balanza explotación vs exploración
- ✅ Mejor relación calidad/tiempo

**Tiempo estimado:** ~60 horas (con GPU RTX 4060)

### Grid Search
**Cuándo usar:**
- Espacio de búsqueda pequeño (<1000 combos)
- Necesitas garantizar optimalidad global
- Tienes suficiente tiempo de cómputo

**Tiempo estimado:** ~100 horas (50 configs × 2h cada)

### Random Search
**Cuándo usar:**
- Espacio muy grande (>10K combos)
- Necesitas resultados "buenos" rápido
- No hay correlación clara entre parámetros

**Tiempo estimado:** ~40 horas (50 muestras × 0.8h cada)

---

## 🧪 Modo Test

Para verificar que todo funciona sin entrenar:

```bash
# Test de Bayesian (genera datos simulados)
python scripts/train/run_sac_hyperparameter_tuning.py --method bayesian --num-iterations 5 --test

# Test de Grid
python scripts/train/run_sac_hyperparameter_tuning.py --method grid --max-configs 10 --test

# Test de Random
python scripts/train/run_sac_hyperparameter_tuning.py --method random --num-samples 10 --test
```

**Salida (sin GPU/entrenamiento):**
```
===============================================================================
BAYESIAN OPTIMIZATION HYPERPARAMETER TUNING
===============================================================================
Iteraciones completadas: 5/5

Mejor configuración encontrada:
  Score: 45.2/100 (simulado)
  LR=1e-03 | Buf=100K | τ=0.0050
  CO2 Evitado: 1,050,300 kg (simulado)
  Reward: 2.13 (simulado)

Mejora respecto a baseline: +12.3%
===============================================================================

[EXPORT] Resultados guardados en: outputs/hyperparameter_tuning/bayesian_opt_...csv
[SAVE] Mejor config salvada en: outputs/hyperparameter_tuning/config_optimal_...json
```

---

## 🔍 Detalles Técnicos

### Grid Search
```
For learning_rate in [1e-5, 3e-5, 1e-4, 3e-4, 1e-3]:
  For buffer_size in [50K, 100K, 200K, 400K, 1M]:
    For batch_size in [32, 64, 128, 256, 512]:
      ... (todas las otras dimensiones)
      Entrenar SAC con esta config
      Registrar métricas
      Guardar resultado
```

**Complejidad:**
- Configs: 96,000 posibles
- Ajuste práctico: Tomar ~50 mejores candidatos
- Tiempo: O(n × 2h) = 100 horas para 50 configs

### Bayesian Optimization
```
1. Muestrear 5 configs aleatorias inicialmente
   → Entrenar SAC con cada una
   
2. Para iteraciones 6-30:
   a) Ajustar Gaussian Process a datos observados
   b) Calcular Expected Improvement (EI) para cada
   c) Seleccionar config con EI máximo
   d) Entrenar SAC
   e) Actualizar GP con nuevo resultado
```

**Ventaja:** Inteligencia adaptativa
- Después de iter 1: Explora espacios malos
- Después de iter 15: Se concentra en "buenas regiones"
- Después de iter 30: Refinamiento fino del óptimo local

---

## 📝 Ejemplo Completo

```bash
# 1. Ejecutar tuning (30 iteraciones, modo test para ver que funciona)
python scripts/train/run_sac_hyperparameter_tuning.py --method bayesian --test

# 2. Ver resultados
cat outputs/hyperparameter_tuning/bayesian_opt_*.csv | head -10

# 3. Usar mejores parámetros en train_sac.py
# (Copiar valores de config_optimal_*.json a SACConfig)

# 4. Entrenar SAC final con mejores parámetros
python scripts/train/train_sac.py

# 5. Comparar: baseline vs optimizado
# Esperar mejora de ~15-25% en CO2 evitado
```

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| "No module named sac_hyperparameter_tuner" | `cd d:\diseñopvbesscar && pip install -e .` |
| Script muy lento | Usar `--test` primero, luego reducir `--episodes` o `--num-iterations` |
| Memoria insuficiente | Reducir `--max-configs` o `--num-iterations` |
| Error de tipo en float/int | Ya manejado en TrainingResult.to_dict() |
| GPU out of memory | Reducir `batch_size` en espacio de búsqueda |

---

## 📚 Referencias

1. **Control Teórico:**
   - Haarnoja et al. (2018): Soft Actor-Critic Algorithm
   - Rasmussen & Williams: Gaussian Processes for ML

2. **Tuning Práctico:**
   - Bergstra & Bengio (2012): Random Search vs Grid Search
   - Lizotte (2008): Bayesian Optimization and Adaptive ...

3. **Problema Iquitos:**
   - `docs/PROYECTO_LISTO_PRODUCCION_v72.md`
   - `00_COMIENZA_AQUI.md`

---

## ✅ Checklist Pre-Ejecución

- [ ] Datasets disponibles: `data/iquitos_ev_mall/` (solar, chargers, mall, BESS)
- [ ] GPU disponible o suficiente CPU/RAM
- [ ] Python 3.8+ con dependencias instaladas
- [ ] Espacio en disco: ~5 GB para results
- [ ] Tiempo disponible: 30-100 horas según método
- [ ] Modo test ejecutado exitosamente

---

**¿Preguntas?** Ver `scripts/train/run_sac_hyperparameter_tuning.py` para detalles de implementación.

**Última ejecución exitosa:** 2026-02-19 (Modo Test ✅)
