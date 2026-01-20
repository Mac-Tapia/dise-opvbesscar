# RESUMEN DE LIMPIEZA Y CORRECCIONES

## Fecha: 2026-01-18

## ACCIONES REALIZADAS

### 1. Verificación de Datos Reales ✅

- Confirmado: **128 cargadores** (112 Playa_Motos + 16 Playa_Mototaxis)
- Archivo: `data/interim/oe2/chargers/individual_chargers.json`
- Datasets: 101 escenarios (baseline + 100 Monte Carlo)

### 2. Limpieza de Scripts Duplicados ✅

Scripts eliminados (usaban datos DUMMY):

- `train_sac_gpu_simple.py`
- `train_sac_correcto.py`
- `train_sac_visible.py`
- `train_sac_real_128chargers.py`
- `train_v2_fresh.py`
- `train_v2_gpu_fresh.py`

Scripts conservados (funcionales):

- `train_tier2_v2_from_scratch.py`
- `train_tier2_v2_gpu.py`

### 3. Checkpoints Dummy Eliminados ✅

- Eliminado: `analyses/oe3/training/checkpoints_v2_fresh/`
- Razón: Entrenados con datos aleatorios, no con 128 cargadores reales

### 4. Script Robusto Creado ✅

- **Archivo**: `train_gpu_robusto.py`
- Características:
  - Verifica GPU automáticamente
  - Verifica datos reales (112+16=128)
  - Usa `simulate()` oficial del proyecto
  - Soporta resume de checkpoints
  - Configurable por número de episodios

### 5. Script de Test Creado ✅

- **Archivo**: `test_citylearn_env.py`
- Verifica que el entorno CityLearn funciona correctamente

## PROBLEMA IDENTIFICADO

El entrenamiento anterior usaba un **SimpleEnv/DummyEnv** con:

```python
obs = np.random.randn(131).astype(np.float32)  # DATOS ALEATORIOS
reward = float(np.sum(action) / 128.0)  # REWARD FALSO
```

En lugar del entorno CityLearn real con:

- 926 observaciones por paso
- 130 acciones (128 chargers + 2 storage)
- Rewards multiobjetivo (CO2, costo, solar, EV, grid)

## ENTRENAMIENTO CORRECTO EN PROGRESO

Ejecutar con:

```bash
python scripts/run_oe3_simulate.py --skip-dataset
```

Métricas observadas:

- R_total: 0.2889
- R_CO2: 0.6087
- R_cost: 0.2531

## CONFIGURACIÓN ACTUAL (configs/default.yaml)

```yaml
oe3:
  evaluation:
    sac:
      episodes: 2
      batch_size: 32768
      device: cuda
      checkpoint_freq_steps: 100
```

## PRÓXIMOS PASOS

1. Esperar a que termine el entrenamiento SAC actual
2. Verificar checkpoints generados en `analyses/oe3/training/checkpoints/`
3. Continuar con PPO y A2C si es necesario
4. Comparar métricas contra baseline uncontrolled

## ARCHIVOS IMPORTANTES

| Archivo | Propósito |
|---------|-----------|
| `scripts/run_oe3_simulate.py` | Script oficial de entrenamiento |
| `train_gpu_robusto.py` | Script simplificado con verificaciones |
| `test_citylearn_env.py` | Prueba del entorno |
| `configs/default.yaml` | Configuración principal |
| `data/interim/oe2/chargers/individual_chargers.json` | 128 cargadores |
