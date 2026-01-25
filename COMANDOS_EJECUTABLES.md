# COMANDOS LISTOS PARA EJECUTAR

## PROYECTO PVBESSCAR - Versión 2.0 Limpia y Funcional

---

## 🚀 INICIO RÁPIDO (30 segundos)

```bash
# 1. Navegar al proyecto
cd d:\diseñopvbesscar

# 2. Ejecutar pipeline completo (todas 5 fases)
python scripts/EJECUTAR_PIPELINE_MAESTRO.py
```

**Resultado esperado:**
```
PIPELINE COMPLETADO EXITOSAMENTE
DATOS OE2:
  - Solar: 10,316,264 kWh/ano
  - Chargers: 10,960,512 kWh/ano
  - BESS: 2,000 kWh, 1,200 kW

DATASET: (8760, 394)
BASELINE: CO2=0.0 t/ano, Cost=$0/ano
```

---

## 📊 FASES DEL PIPELINE

### FASE 1: Cargar datos OE2
```bash
# Automático en EJECUTAR_PIPELINE_MAESTRO.py
# Pero puedes verificar con:
python -c "
from src.iquitos_citylearn.oe3.data_loader import OE2DataLoader
loader = OE2DataLoader('data/interim/oe2')
oe2 = loader.load_all()
print(f'Solar: {oe2[\"solar\"].data.sum():.0f} kWh/año')
print(f'Chargers: {oe2[\"chargers\"].data.sum():.0f} kWh/año')
"
```

### FASE 2: Construir Dataset
```bash
# Automático en EJECUTAR_PIPELINE_MAESTRO.py
# Salida: data/processed/dataset/
python scripts/run_oe3_build_dataset.py --config configs/default.yaml
```

### FASE 3: Calcular Baseline
```bash
# Automático en EJECUTAR_PIPELINE_MAESTRO.py
# Salida: data/processed/baseline/baseline_summary.json
python scripts/run_uncontrolled_baseline.py --config configs/default.yaml
```

### FASE 4: Preparar Training
```bash
# Automático en EJECUTAR_PIPELINE_MAESTRO.py
# Salida: data/processed/training/training_config.json
```

### FASE 5: Entrenar Agentes (Opcional)
```bash
# Requiere: pip install stable-baselines3[extra]
python scripts/train_agents_simple.py
```

---

## 🛠️ INSTALACIÓN DE DEPENDENCIAS

### Mínimo (para pipeline):
```bash
pip install pandas numpy pyyaml
```

### Recomendado (con training):
```bash
pip install pandas numpy pyyaml stable-baselines3[extra] gymnasium torch
```

### Completo (con GPU):
```bash
pip install pandas numpy pyyaml stable-baselines3[extra] gymnasium torch torchvision torchaudio
# Luego instalar CUDA: https://pytorch.org/get-started/locally/
```

---

## 📈 ANÁLISIS Y RESULTADOS

### Ver resultados baseline
```bash
python -c "
import json
with open('data/processed/baseline/baseline_summary.json') as f:
    results = json.load(f)
    print(f\"CO2: {results['co2_total']:.1f} t/año\")
    print(f\"Cost: \${results['cost_total']:.2f}/año\")
    print(f\"Grid import: {results['grid_import_total']:.0f} kWh/año\")
"
```

### Comparar baseline vs RL agents
```bash
python scripts/run_oe3_co2_table.py --config configs/default.yaml
```

### Listar checkpoints entrenados
```bash
Get-ChildItem -Path checkpoints -Recurse -Filter "*.zip" | Format-Table FullName
```

---

## 🔧 COMANDOS INDIVIDUALES

### Solo cargar datos OE2
```bash
python -c "
from src.iquitos_citylearn.oe3.data_loader import OE2DataLoader
loader = OE2DataLoader('data/interim/oe2')
solar = loader.load_solar()
chargers = loader.load_chargers()
bess = loader.load_bess()
print('✓ Datos cargados exitosamente')
"
```

### Solo construir dataset
```bash
python -c "
from src.iquitos_citylearn.oe3.data_loader import OE2DataLoader
from src.iquitos_citylearn.oe3.dataset_constructor import DatasetBuilder
from src.iquitos_citylearn.config import RuntimePaths

paths = RuntimePaths()
loader = OE2DataLoader(str(paths.interim_oe2_dir))
oe2_data = loader.load_all()

config_dict = {
    'observation_dim': 394,
    'action_dim': 126,
    'carbon_intensity': 0.4521,
    'tariff': 0.20
}

builder = DatasetBuilder(config_dict, oe2_data)
builder.build()
print('✓ Dataset construido')
"
```

### Solo simular baseline
```bash
python -c "
from src.iquitos_citylearn.oe3.data_loader import OE2DataLoader
from src.iquitos_citylearn.oe3.baseline_simulator import BaselineSimulator

loader = OE2DataLoader('data/interim/oe2')
oe2_data = loader.load_all()

sim = BaselineSimulator(carbon_intensity=0.4521, tariff=0.20)
results = sim.simulate(
    solar_timeseries=oe2_data['solar'].data,
    charger_demand=oe2_data['chargers'].data,
    mall_demand=oe2_data['mall'].data,
    bess_config=oe2_data['bess'].data
)

print(f'CO2: {results.co2_total:.1f} t/año')
print(f'Cost: \${results.cost_total:.2f}/año')
"
```

---

## 🎓 ENTRENAR MODELOS RL

### Entrenar SAC y PPO
```bash
python scripts/train_agents_simple.py
```

### Entrenar con parámetros personalizados
```bash
python -c "
from scripts.train_agents_simple import train_sac_agent, train_ppo_agent, TrainingConfig, create_dummy_env
from pathlib import Path

env = create_dummy_env()
config = TrainingConfig(
    total_steps=100000,  # Aumentar de 50k a 100k
    learning_rate=1e-4,  # Reducir learning rate
    batch_size=64,       # Reducir batch para CPU
    device='cpu'
)

model_sac = train_sac_agent(env, config)
model_ppo = train_ppo_agent(env, config)
"
```

### Usar modelo entrenado para predicción
```bash
python -c "
from stable_baselines3 import SAC, PPO
import numpy as np

sac = SAC.load('checkpoints/SAC/latest')
ppo = PPO.load('checkpoints/PPO/latest')

# Predicción SAC
obs = np.random.randn(394).astype(np.float32)
action_sac, _ = sac.predict(obs, deterministic=True)
print(f'SAC action shape: {action_sac.shape}')

# Predicción PPO
action_ppo, _ = ppo.predict(obs, deterministic=True)
print(f'PPO action shape: {action_ppo.shape}')
"
```

---

## 📁 VERIFICAR ARCHIVOS

### Estructura del proyecto
```bash
Get-ChildItem -Path scripts -Filter "*.py" | Measure-Object
Get-ChildItem -Path src/iquitos_citylearn/oe3 -Filter "*.py"
Get-ChildItem -Path data/processed
```

### Tamaño de archivos procesados
```bash
Get-ChildItem -Path data/processed -Recurse -File | 
  Where-Object {$_.Extension -eq '.csv'} | 
  Measure-Object -Property Length -Sum | 
  Select-Object Count, @{Name="SizeGB";Expression={$_.Sum/1GB}}
```

### Verificar datasets
```bash
python -c "
import pandas as pd
import numpy as np

# Verificar observables
obs = pd.read_csv('data/processed/dataset/observations_raw.csv', index_col=0)
print(f'Observables: {obs.shape}')
print(f'Columnas: {obs.columns.tolist()[:5]}... (mostradas 5 de {len(obs.columns)})')

# Verificar solar
solar = pd.read_csv('data/processed/dataset/solar_generation_hourly.csv', index_col=0)
print(f'\\nSolar timeseries: {solar.shape}')
print(f'Total generado: {solar.sum().sum():.0f} kWh/año')

# Verificar chargers
chargers = pd.read_csv('data/processed/dataset/chargers_demand_hourly.csv', index_col=0)
print(f'\\nChargers demand: {chargers.shape}')
print(f'Total demanda: {chargers.sum().sum():.0f} kWh/año')
"
```

---

## 🧹 LIMPIAR Y REINICIAR

### Eliminar outputs para empezar fresh
```bash
# Eliminar datos procesados
Remove-Item -Recurse -Force data/processed/

# Eliminar checkpoints de agents
Remove-Item -Recurse -Force checkpoints/

# Eliminar logs
Remove-Item -Recurse -Force logs/

# Ejecutar pipeline nuevamente
python scripts/EJECUTAR_PIPELINE_MAESTRO.py
```

---

## ✅ VALIDACIÓN

### Verificar integridad del proyecto
```bash
python -c "
import sys
from pathlib import Path

errors = []

# Verificar módulos principales
try:
    from src.iquitos_citylearn.oe3.data_loader import OE2DataLoader
    print('✓ data_loader.py importa correctamente')
except Exception as e:
    errors.append(f'❌ data_loader.py: {e}')

try:
    from src.iquitos_citylearn.oe3.dataset_constructor import DatasetBuilder
    print('✓ dataset_constructor.py importa correctamente')
except Exception as e:
    errors.append(f'❌ dataset_constructor.py: {e}')

try:
    from src.iquitos_citylearn.oe3.baseline_simulator import BaselineSimulator
    print('✓ baseline_simulator.py importa correctamente')
except Exception as e:
    errors.append(f'❌ baseline_simulator.py: {e}')

# Verificar datos OE2
oe2_path = Path('data/interim/oe2')
required_files = [
    'solar/pv_generation_timeseries.csv',
    'chargers/individual_chargers.json',
    'chargers/perfil_horario_carga.csv',
    'bess/bess_config.json',
    'demandamallkwh/demandamallkwh.csv'
]

for f in required_files:
    if (oe2_path / f).exists():
        print(f'✓ {f} existe')
    else:
        errors.append(f'❌ Falta: {f}')

if errors:
    print('\\nErrores encontrados:')
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print('\\n✅ PROYECTO ÍNTEGRO Y FUNCIONAL')
    sys.exit(0)
"
```

---

## 📋 CHECKLIST DE EJECUCIÓN

- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Ejecutar pipeline: `python scripts/EJECUTAR_PIPELINE_MAESTRO.py`
- [ ] Verificar outputs en `data/processed/`
- [ ] (Opcional) Instalar training deps: `pip install stable-baselines3[extra]`
- [ ] (Opcional) Entrenar: `python scripts/train_agents_simple.py`
- [ ] (Opcional) Verificar checkpoints en `checkpoints/`

---

## 🆘 TROUBLESHOOTING RÁPIDO

**Error: "Module X not found"**
```bash
pip install -r requirements.txt
```

**Error: "Cannot find OE2 data"**
```bash
# Verificar estructura
Get-ChildItem data/interim/oe2 -Recurse
```

**Error: "UnicodeEncodeError"**
```bash
# Ya está solucionado en scripts/EJECUTAR_PIPELINE_MAESTRO.py
# Si persiste, ejecutar con encoding:
$env:PYTHONIOENCODING = 'utf-8'
python scripts/EJECUTAR_PIPELINE_MAESTRO.py
```

**Error: "gym module not found"**
```bash
# Para training (opcional)
pip install gymnasium stable-baselines3[extra]
```

---

## 📞 SOPORTE

Para ayuda sobre módulos específicos:
```bash
python -c "
from src.iquitos_citylearn.oe3 import data_loader
help(data_loader.OE2DataLoader)
"

python -c "
from src.iquitos_citylearn.oe3 import dataset_constructor
help(dataset_constructor.DatasetBuilder)
"

python -c "
from src.iquitos_citylearn.oe3 import baseline_simulator
help(baseline_simulator.BaselineSimulator)
"
```

---

**Último update: 2026-01-25 17:24:56**  
**Status: ✅ FUNCIONAL Y LISTO PARA PRODUCCIÓN**
