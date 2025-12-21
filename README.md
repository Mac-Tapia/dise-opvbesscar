# Iquitos 2025 – OE2 + OE3

## Reducción de Emisiones CO₂ mediante Energía Solar y Gestión de Carga EV

**Proyecto:** Dimensionamiento y gestión inteligente de motos/mototaxis eléctricas para reducir emisiones de CO₂ en Iquitos.

**Ubicación:** Iquitos, Perú (lat: -3.7°, lon: -73.2°)  
**Año objetivo:** 2025

---

## 📋 Objetivos del Proyecto

### **OE.2 - Dimensionamiento de Infraestructura**

✅ Dimensionar generación solar (FV), almacenamiento (BESS) y cargadores para motos/mototaxis eléctricas

### **OE.3 - Algoritmos de Control**

✅ Seleccionar algoritmo de gestión de carga (Uncontrolled, RBC, PPO, SAC) que minimize emisiones CO₂

---

## 📦 Componentes

- **OE2**: Perfil FV anual (pvlib/clear-sky), dimensionamiento BESS, configuración cargadores para flota eléctrica
- **OE3**: Dataset CityLearn (EV + FV + BESS), simulación multi-agente, análisis de reducción CO₂ (anual + 20 años)

---

## 1️⃣ Instalación y Requisitos

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
