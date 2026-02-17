# PPO Entropía FIX v7.3 - Resumen de cambios

## Problem
Los valores de entropía de PPO **NO se guardaban** en `timeseries_ppo.csv` y `trace_ppo.csv`, causando que la visualización de entropía (`ppo_entropy.png`) no tuviera datos precisos.

## Solution
Implementada comunicación entre callbacks mediante diccionario global `GLOBAL_PPO_METRICS`, similar a `GLOBAL_ENERGY_VALUES`.

## Cambios realizados en `scripts/train/train_ppo_multiobjetivo.py`

### 1. Agregar diccionario global (línea 1454-1461)
```python
GLOBAL_PPO_METRICS = {
    'current_entropy': 0.0,
    'current_approx_kl': 0.0,
    'current_clip_fraction': 0.0,
    'current_policy_loss': 0.0,
    'current_value_loss': 0.0,
    'current_explained_variance': 0.0
}
```

### 2. DetailedLoggingCallback._on_step() (línea 1586-1594)
Lee métricas PPO desde GLOBAL_PPO_METRICS:
```python
entropy_val = float(GLOBAL_PPO_METRICS.get('current_entropy', 0.0))
approx_kl_val = float(GLOBAL_PPO_METRICS.get('current_approx_kl', 0.0))
# ... etc
```

### 3. Agregadas columnas a trace_record (línea 1716-1722)
```python
'entropy': entropy_val,
'approx_kl': approx_kl_val,
'clip_fraction': clip_fraction_val,
'policy_loss': policy_loss_val,
'value_loss': value_loss_val,
'explained_variance': explained_variance_val,
```

### 4. Agregadas columnas a timeseries_record (línea 1764-1770)
Mismas 6 columnas en `ts_record` para que `timeseries_ppo.csv` las contenga

### 5. PPOMetricsCallback._on_step() (línea 2142-2152)
Actualiza GLOBAL_PPO_METRICS:
```python
GLOBAL_PPO_METRICS['current_entropy'] = ppo_metrics.get('entropy', 0.0)
GLOBAL_PPO_METRICS['current_approx_kl'] = ppo_metrics.get('approx_kl', 0.0)
# ... etc
```

## Resultado
✅ **timeseries_ppo.csv** ahora contiene:
- entropy
- approx_kl
- clip_fraction
- policy_loss
- value_loss
- explained_variance

✅ **trace_ppo.csv** ahora contiene:
- entropy
- approx_kl
- clip_fraction
- policy_loss
- value_loss
- explained_variance

## Cómo verificar

### Opción 1: Script de validación completo
```bash
python verify_ppo_entropy.py
```

Este script verifica:
- Columnas de entropía presentes en CSVs
- Valores NO son todos ceros
- Estadísticas de entropía (min, max, mean, std)
- Decaimiento de entropía por episodio
- Muestra de datos de ejemplo

### Opción 2: Test rápido (ya pasado)
```bash
python test_ppo_entropy_fix.py
```

## Próximos pasos

1. **Ejecutar entrenamiento PPO**:
   ```bash
   python scripts/train/train_ppo_multiobjetivo.py
   ```

2. **Verificar que entropía se guardó**:
   ```bash
   python verify_ppo_entropy.py
   ```

3. **Analizar gráfico de entropía**:
   ```
   outputs/ppo_training/ppo_entropy.png
   ```

## Notas técnicas

### Patrón de comunicación entre callbacks
```
PPOMetricsCallback (calcula entropía cada n_steps)
        ↓ (escribe a)
GLOBAL_PPO_METRICS
        ↑ (lee de)
DetailedLoggingCallback (guarda en CSV cada step)
```

Este patrón es robusto con `VecNormalize` y otros wrappers que pueden aislar callbacks.

### Métricas de diagnóstico ahora disponibles
- **entropy**: Cuánta exploración mantiene el agente
- **approx_kl**: Cuánto cambió la política (regularización)
- **clip_fraction**: % de samples donde se aplicó clipping
- **policy_loss**: Pérdida del actor
- **value_loss**: Pérdida del crítico
- **explained_variance**: Qué tan bien predice el value function

### Interpretación de valores esperados
- **entropy**: Decrece gradualmente (0.5 → 0.1) durante entrenamiento
- **approx_kl**: Típicamente 0.01-0.05 (si > 0.2 hay problema)
- **clip_fraction**: Típicamente 0.1-0.3 (si > 0.5 hay sobre-clipping)
- **policy_loss**: Idealmente negativo y decrece
- **explained_variance**: Cerca de 1.0 (>0 es bueno, <0 es malo)

## Referencias
- Stable-Baselines3 Logger: https://stable-baselines3.readthedocs.io/
- PPO Paper: Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
