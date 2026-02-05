# OE3 DATASET CITYLEARN V2 - GUIA RAPIDA

**Estado**: ✅ LISTO PARA TRAINING

---

## 📊 QUE SE CONSTRUYO

Integracion completa de datos OE2 (Solar, Chargers, BESS, Mall) en formato CityLearn v2:

```
src/citylearnv2/dataset/
├── schema.json                  ← Configuracion CityLearn v2
└── dataset/
    ├── solar_generation.csv     ← PVGIS real (8,292,514 kWh/ano)
    ├── charger_load.csv         ← 128 chargers (112 + 16)
    └── mall_load.csv            ← 100 kW constant
```

---

## ✅ VALIDACION

Ejecuta para verificar integridad:
```bash
python validate_oe3_dataset.py
```

Expected output:
```
✓ Solar: 8760 rows, 8,292,514 kWh annual
✓ Chargers: 8760 rows × 128
✓ Mall: 8760 rows, 876,000 kWh annual
✓ Schema-CSV charger count matches: 128
✅ ALL VALIDATIONS PASSED
```

---

## 🚀 TRAINING AGENTES RL

### Option 1: Train SAC (Recomendado para CO2)
```bash
python -m scripts.run_oe3_simulate --agent sac --config configs/default.yaml
```
Expected: CO2 ~140,000 kg/ano (-26% vs baseline)

### Option 2: Train PPO
```bash
python -m scripts.run_oe3_simulate --agent ppo --config configs/default.yaml
```
Expected: CO2 ~135,000 kg/ano (-29% vs baseline)

### Option 3: Train A2C
```bash
python -m scripts.run_oe3_simulate --agent a2c --config configs/default.yaml
```
Expected: CO2 ~144,000 kg/ano (-24% vs baseline)

### Option 4: Compare Baselines
```bash
python -m scripts.run_dual_baselines --config configs/default.yaml
```
Compare: CON SOLAR vs SIN SOLAR

---

## 📈 ESPECIFICACIONES

| Aspecto | Valor |
|---|---|
| Timesteps | 8,760 (horario, 1 ano completo) |
| Observacion dim | 394 (estado + sensores) |
| Accion dim | 129 (1 BESS + 128 chargers) |
| Solar anual | 8,292,514 kWh (PVGIS real) |
| Chargers | 128 (112 motos 2kW + 16 mototaxis 3kW) |
| Mall | 100 kW constant |
| BESS | 4,520 kWh, 2,000 kW |
| Carbon intensity | 0.4521 kg CO2/kWh (Iquitos grid) |

---

## 📁 ARCHIVOS CLAVE

1. **build_oe3_dataset.py** - Builder script (ejecutado)
2. **validate_oe3_dataset.py** - Validador
3. **src/citylearnv2/dataset/schema.json** - Config CityLearn v2
4. **src/citylearnv2/dataset/dataset/*.csv** - Data files

---

## 🎯 RESULTADOS ESPERADOS

Despues de 50 episodios de training:

| Agente | CO2 (kg) | Solar % | vs Baseline |
|--------|---|---|---|
| Baseline (sin RL) | 190,000 | 45% | - |
| SAC | 140,000 | 65% | -26% |
| PPO | 135,000 | 68% | -29% |
| A2C | 144,000 | 60% | -24% |

---

## 🔍 INSPECCIONAR DATOS

### Ver primeras filas solares
```bash
python -c "import pandas as pd; df=pd.read_csv('src/citylearnv2/dataset/dataset/solar_generation.csv'); print(df.head())"
```

### Verificar energia anual
```bash
python -c "import pandas as pd; df=pd.read_csv('src/citylearnv2/dataset/dataset/solar_generation.csv'); print(f'Annual: {df.iloc[:,1].sum():.0f} kWh')"
```

### Revisar schema.json
```bash
python -c "import json; print(json.dumps(json.load(open('src/citylearnv2/dataset/schema.json')), indent=2))"
```

---

## ⚡ TROUBLESHOOTING

**"FileNotFoundError: schema.json not found"**
- Ejecuta `python build_oe3_dataset.py` primero

**"Charger count mismatch"**
- Ejecuta `python validate_oe3_dataset.py`

**"Validation failed"**
- Check CSV files exist en `src/citylearnv2/dataset/dataset/`
- Verify 8,760 rows en cada CSV

---

**LISTO PARA OE3 TRAINING** ✅
