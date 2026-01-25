# INICIO RÁPIDO - PVBESSCAR 2.0

## En 2 minutos

### Paso 1: Ejecutar pipeline (30 segundos)
```bash
cd d:\diseñopvbesscar
python scripts/EJECUTAR_PIPELINE_MAESTRO.py
```

**Resultado esperado:**
```
PIPELINE COMPLETADO EXITOSAMENTE
✓ OE2 Data loaded
✓ Dataset built (8760×394)
✓ Baseline calculated (CO₂=0.0 t/año)
✓ Training ready
```

### Paso 2: Ver resultados
```bash
# Verificar dataset
python -c "
import pandas as pd
obs = pd.read_csv('data/processed/dataset/observations_raw.csv', index_col=0)
print(f'Dataset shape: {obs.shape}')
print('✅ Dataset created successfully')
"

# Verificar baseline
python -c "
import json
with open('data/processed/baseline/baseline_summary.json') as f:
    r = json.load(f)
    print(f'CO2: {r[\"co2_total\"]:.1f} t/año')
    print(f'Cost: \${r[\"cost_total\"]:.2f}/año')
    print('✅ Baseline calculated successfully')
"
```

---

## Si quieres entrenar agentes (opcional)

### Paso 1: Instalar dependencias
```bash
pip install stable-baselines3[extra] gymnasium torch
```

### Paso 2: Entrenar
```bash
python scripts/train_agents_simple.py
```

**Duración:** ~1 hora (CPU) o 5-10 min (GPU)  
**Resultado:** Modelos guardados en `checkpoints/SAC/` y `checkpoints/PPO/`

---

## Referencia Rápida

| Tarea | Comando |
|-------|---------|
| **Pipeline completo** | `python scripts/EJECUTAR_PIPELINE_MAESTRO.py` |
| **Solo cargar OE2** | `python scripts/run_oe2_solar.py` |
| **Solo construir dataset** | `python scripts/run_oe3_build_dataset.py` |
| **Solo calcular baseline** | `python scripts/run_uncontrolled_baseline.py` |
| **Entrenar agentes** | `python scripts/train_agents_simple.py` |
| **Comparar resultados** | `python scripts/run_oe3_co2_table.py` |

---

## Estructura de Carpetas Clave

```
✓ data/interim/oe2/          ← Datos brutos (solar, chargers, BESS, mall)
✓ data/processed/            ← Outputs del pipeline
  ✓ dataset/                 ← Observables 8760×394
  ✓ baseline/                ← CO₂ y costos
  ✓ training/                ← Config para training
✓ checkpoints/               ← Modelos entrenados (SAC, PPO)
✓ scripts/                   ← Scripts principales
  ✓ EJECUTAR_PIPELINE_MAESTRO.py    ← PUNTO DE ENTRADA
  ✓ train_agents_simple.py           ← Training RL
```

---

## ¿Qué hace cada módulo?

### `data_loader.py`
Carga datos OE2:
- Solar: 8,760 horas × 1
- Chargers: 8,760 horas × 128
- BESS: Config estática (2000 kWh, 1200 kW)
- Mall: 8,760 horas × 1 (0 demanda)

### `dataset_constructor.py`
Construye observables para RL:
- Input: Datos OE2
- Output: Observables 8,760×394
- Features: Energy, chargers, time, grid metrics

### `baseline_simulator.py`
Simula sin control inteligente:
- Dispatch: Solar→Chargers→BESS→Grid
- Calcula CO₂ emissions (t/año)
- Calcula costos ($/año)
- Calcula KPIs

### `train_agents_simple.py`
Entrena agentes RL:
- Agentes: SAC, PPO
- Steps: 50,000 cada uno
- Checkpoints: Auto-saved
- Config: Configurable

---

## Solución Rápida de Problemas

### ❌ "Module not found"
```bash
pip install -r requirements.txt
```

### ❌ "OE2 data not found"
Verificar estructura:
```
data/interim/oe2/
├── solar/pv_generation_timeseries.csv
├── chargers/individual_chargers.json
├── chargers/perfil_horario_carga.csv
├── bess/bess_config.json
└── demandamallkwh/demandamallkwh.csv
```

### ❌ "Gym module missing" (al entrenar)
```bash
pip install gymnasium stable-baselines3[extra]
```

### ❌ "GPU out of memory"
En `train_agents_simple.py`, cambiar:
```python
config = TrainingConfig(
    batch_size=64,  # Reducir de 128
    device="cpu"    # O usar "cpu"
)
```

---

## Documentación Completa

| Documento | Para qué |
|-----------|----------|
| `README_FINAL.md` | Resumen ejecutivo |
| `RESUMEN_PROYECTO_LIMPIO.md` | Overview general |
| `CAMBIOS_REALIZADOS.md` | Detalle técnico |
| `COMANDOS_EJECUTABLES.md` | Referencia completa |
| `QUICKSTART.md` | Este archivo |

---

## Próximos Pasos

1. **Ejecuta:** `python scripts/EJECUTAR_PIPELINE_MAESTRO.py`
2. **Verifica:** Outputs en `data/processed/`
3. **(Opcional) Entrena:** `python scripts/train_agents_simple.py`
4. **(Opcional) Analiza:** `python scripts/run_oe3_co2_table.py`

---

## Contacto/Soporte

- Ver documentación: `COMANDOS_EJECUTABLES.md`
- Especificación completa: `.github/copilot-instructions.md`
- Help de módulos: `python -c "from src.iquitos_citylearn.oe3.data_loader import OE2DataLoader; help(OE2DataLoader)"`

---

**¡Listo para empezar!**

```bash
python scripts/EJECUTAR_PIPELINE_MAESTRO.py
```
