# Iquitos – OE2 + OE3 (CityLearn con EV)

Este repositorio integra:

- **OE2 (dimensionamiento)**: perfil FV anual (pvlib/clear-sky), selección de cargadores (motos/mototaxis) y dimensionamiento BESS a partir de excedentes diarios FV.
- **OE3 (operación)**: dataset **CityLearn** con **EV + FV + BESS**, simulación con agentes CityLearn (Uncontrolled, BasicEVRBC y SAC) y generación de **tabla final de reducción CO₂** (anual y a 20 años).

---

## 1) Requisitos

- Python 3.10+
- VSCode recomendado
- Dependencias: ver `requirements.txt`

Instalación:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## 2) Ejecutar el pipeline completo

```bash
python scripts/run_pipeline.py --config configs/default.yaml
```

Salida principal:

- OE2 artefactos: `data/interim/oe2/...`
- Dataset CityLearn generado: `data/processed/citylearn/<name>/`
- Simulaciones OE3: `data/interim/oe3/simulations/`
- Tabla final CO₂: `reports/oe3/co2_comparison_table.csv` y `reports/oe3/co2_comparison_table.md`

---

## 3) Ejecutar por etapas

### OE2
```bash
python scripts/run_oe2_solar.py --config configs/default.yaml
python scripts/run_oe2_chargers.py --config configs/default.yaml
python scripts/run_oe2_bess.py --config configs/default.yaml
```

### OE3
```bash
python scripts/run_oe3_build_dataset.py --config configs/default.yaml
python scripts/run_oe3_simulate.py --config configs/default.yaml
python scripts/run_oe3_co2_table.py --config configs/default.yaml
```

---

## 4) Notas operativas

- **CityLearn dataset plantilla con EV**: se descarga automáticamente usando `citylearn.data.DataSet.get_dataset(...)` y luego se sobreescribe con perfiles OE2.
- Se generan dos esquemas para la comparación de emisiones:
  - `schema_grid_only.json`: sin FV ni BESS (solo red + EV).
  - `schema_pv_bess.json`: con FV + BESS.
- La tabla CO₂ asigna emisiones de red al transporte electrificado mediante **reparto proporcional** entre consumo del edificio y consumo EV (ver `src/iquitos_citylearn/oe3/co2_table.py`).

---

## 5) Configuración

Ajusta parámetros en `configs/default.yaml`:

- FV: `oe2.solar.target_dc_kw`, `oe2.solar.target_annual_kwh`
- Cargadores: `oe2.ev_fleet.*`
- BESS: `oe2.bess.*`
- Intensidad de carbono: `oe3.grid.carbon_intensity_kg_per_kwh`
- Factores transporte: `oe3.emissions.*`
