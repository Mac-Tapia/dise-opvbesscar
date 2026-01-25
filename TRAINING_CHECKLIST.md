# ✅ Checklist Pre-Entrenamiento

Verifica todos estos items antes de iniciar el entrenamiento RL.

## 1. Entorno

- [ ] Python 3.10+ activado (`.venv\Scripts\activate` en Windows)
- [ ] Dependencias instaladas: `pip install -r requirements.txt`
- [ ] GPU disponible (opcional): `python -c "import torch;
  - print(torch.cuda.is_available())"`

## 2. Datos OE2

- [ ] Solar timeseries existe:
  - `data/interim/oe2/solar/pv_generation_timeseries.csv`
  - [ ] Contiene exactamente 8,760 filas (1 año horario)
  - [ ] Columnas: hora, potencia_kw
- [ ] Chargers profile existe:
  - `data/interim/oe2/chargers/perfil_horario_carga.csv`
  - [ ] Contiene 24 filas (horas del día)
  - [ ] Columnas: hora, carga_kw
- [ ] Individual chargers JSON existe:
  - `data/interim/oe2/chargers/individual_chargers.json`
  - [ ] Contiene 32 chargers (28 motos + 4 mototaxis)
  - [ ] Cada charger tiene 4 sockets

## 3. Configuración

- [ ] `configs/default.yaml` editado y válido
  - [ ] `oe2.dispatch_rules.enabled: true`
  - [ ] `oe3.rewards.co2_weight: 0.50`
  - [ ] `oe3.grid.carbon_intensity_kg_per_kwh: 0.4521`
  - [ ] `oe3.grid.tariff_usd_per_kwh: 0.20`

## 4. Dataset CityLearn

- [ ] Ejecutar builder si no existe:

  ```bash
  python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```bash

- [ ] Validar schema: `outputs/schema_*.json` debe existir
  - [ ] Contains `buildings` key
  - [ ] Contains `climate_zones` key
  - [ ] Charger simulations incluidas

## 5. Agentes

- [ ] Imports funcionales:

  ```bash
  python -c "from iquitos_citylearn.oe3.agents import PPOAgent, SACAgent, A2CAgent; print('OK')"
```bash

- [ ] Device detectado:

  ```bash
  python -c "from iquitos_citylearn.oe3.agents import detect_device; print(detect_device())"
```bash

## 6. Rewards & Observables

- [ ] Rewards normalizadas (suma pesos = 1.0):

  ```bash
  python -c "from iquitos_citylearn.oe3.rewards import MultiObjectiveWeights; w=MultiObjectiveWeights(); print(f'Sum={w.co2+w.cost+w.solar+w.ev_satisfaction+w.grid_stability:.2f}')"
```bash

- [ ] Observables enriquecidos disponibles:
  - [ ] `src/iquitos_citylearn/oe3/enriched_observables.py` contiene lógica

## 7. Checkpoints

- [ ] Directorio de checkpoints limpio o inexistente:

  ```bash
  rm -r checkpoints/  # o en PowerShell: Remove-Item -Recurse checkpoints
```bash

- [ ] O aceptar reanudar desde checkpoint existente (opcional)

## 8. Validación Pre-Entrenamiento

Ejecuta validación automática:

```bash
python src/iquitos_citylearn/oe3/agents/validate_training_env.py
```bash

Debe mostrar:

```bash
✓ Agents imported successfully
✓ Rewards imported successfully
✓ GPU available: (device name)
✓ Checkpoint dir: (path)
✓ All checks passed! Ready to train.
```bash

## 9. Entrenamiento

Iniciar entrenamiento con:

```bash
# Validación rápida (5 episodios, ~5 min)
python scripts/train_quick.py --device cuda --episodes 5

# O entrenamiento serial completo (50 episodios, ~50 min)
python scripts/train_agents_serial.py --device cuda --episodes 50
```bash

Monitorear progreso en otra terminal:

```bash
python scripts/monitor_training_live_2026.py
```bash

## 10. Post-Entrenamiento

- [ ] Checkpoints guardados en `checkpoints/{SAC,PPO,A2C}/`
- [ ] Logs en `analyses/logs/`
- [ ] Comparativa: `python -m scripts.run_oe3_co2_table --config
  - configs/default.yaml`
- [ ] Resultado: `COMPARACION_BASELINE_VS_RL.txt`

---

## 🚀 Quick Start (Todos en Orden)

```bash
# 1. Setup
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Validar datos OE2
python -c "import pandas as pd; print('Solar rows:', len(pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv')))"

# 3. Build dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# 4. Validar entorno
python src/iquitos_citylearn/oe3/agents/validate_training_env.py

# 5. Entrenar
python scripts/train_quick.py --device cuda --episodes 5

# 6. Monitorear (otra terminal)
python scripts/monitor_training_live_2026.py

# 7. Comparar resultados
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```bash

---

## ⚠️ Problemas Comunes

| Problema | Solución |
|----------|----------|
| "Schema not found" | Ejecutar `run_oe3_build_dataset` primero |
| "128 chargers not found" | Validar `data/interim/oe2/chargers/individual_chargers.json`... |
| "GPU out of memory" | Reducir `n_steps` en config; usar `--device cpu` |
| "Reward NaN" | Verificar weights sum ~1.0; check obs scaling |
| "Import error agents" | Verificar `src/` en PYTHONPATH |
| "Checkpoint load failed" | Limpiar `checkpoints/` o... |

---

**Status**: Actualizado Ene 25, 2026
