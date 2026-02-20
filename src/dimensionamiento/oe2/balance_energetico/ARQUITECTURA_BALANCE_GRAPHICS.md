# Arquitectura de Generación de Gráficas v5.7
## Responsabilidades Claras por Módulo

---

## 🎯 Responsabilidad Central

### **balance.py = ÚNICO generador de gráficas**
```
BalanceEnergeticoSystem.plot_energy_balance(output_dir)
    ↓
Genera las 16 gráficas PNG
```

### **bess.py = SOLO dimensionamiento**
```
Calcula capacidad BESS, SOC, genera dataset
    ↓
data/oe2/bess/bess_ano_2024.csv (8760 filas, 35 columnas)
    ↓
NO genera gráficas (eso lo hace balance.py)
```

### **regenerate_graphics_v57.py = WRAPPER/punto de entrada**
```
Carga dataset → normaliza columnas → DELEGA a balance.py
```

---

## 📊 Las 16 Gráficas (TODAS en balance.py)

| # | Archivo | Método en balance.py |
|---|---------|----------------------|
| 1 | 00_BALANCE_INTEGRADO_COMPLETO.png | `_plot_integrated_balance()` |
| 2 | 00.1_EXPORTACION_Y_PEAK_SHAVING.png | `_plot_export_and_peak_shaving()` |
| 3 | 00.2_GENERACION_EXPORTACION_INTEGRADA.png | `_plot_grid_export_integrated()` |
| 4 | 00.3_PEAK_SHAVING_INTEGRADO_MALL.png | `_plot_peak_shaving_integrated()` |
| 5 | 00_INTEGRAL_todas_curvas.png | `_plot_integral_curves()` ⭐ |
| 6 | 00.5_FLUJO_ENERGETICO_INTEGRADO.png | `_plot_energy_flow_diagram()` |
| 7 | 01_balance_5dias.png | `_plot_5day_balance()` |
| 8 | 02_balance_diario.png | `_plot_daily_balance()` |
| 9 | 03_distribucion_fuentes.png | `_plot_sources_distribution()` |
| 10 | 04_cascada_energetica.png | `_plot_energy_cascade()` |
| 11 | 05_bess_soc.png | `_plot_bess_soc()` |
| 12 | 05.1_bess_carga_descarga.png | `_plot_bess_charge_discharge()` |
| 13 | 08_pv_exportacion_desglose.png | `_plot_pv_export_breakdown()` |
| 14 | 06_emisiones_co2.png | `_plot_co2_emissions()` |
| 15 | 07_utilizacion_pv.png | `_plot_pv_utilization()` |
| 16 | 99_CAPACIDAD_SOLAR_VALIDACION.png | `_plot_solar_capacity_validation()` |

---

## 🔄 Flujo de Ejecución

```
python scripts/regenerate_graphics_v57.py
        ↓
1. Carga: data/oe2/bess/bess_ano_2024.csv
        ↓
2. Normaliza columnas (19 mappings + 5 derived)
        ↓
3. BalanceEnergeticoSystem(df, config)  [en balance.py]
        ↓
4. .plot_energy_balance(output_dir)     [EN BALANCE.PY]
        ↓
5. Genera 16 PNG files
        ↓
6. Salva en: src/dimensionamiento/oe2/balance_energetico/outputs_demo/
```

---

## ✅ Reglas de Arquitectura

| Módulo | ✓ HACER | ✗ NO HACER |
|--------|---------|----------|
| **balance.py** | Generar TODAS las 16 gráficas | Generar dataset |
| **bess.py** | Calcular BESS, generar dataset | Generar gráficas |
| **regenerate_graphics_v57.py** | Wrapper que carga + prepara datos | Generar gráficas directo |

---

## 📂 Estructura de Directorios

```
src/dimensionamiento/oe2/
├── disenobess/
│   └── bess.py                    ← DATASET (NO gráficas)
│
└── balance_energetico/
    ├── balance.py                 ← GRÁFICAS (16 PNG todas aquí)
    ├── ARQUITECTURA_BALANCE_GRAPHICS.md (este archivo)
    └── outputs_demo/              ← Salida de las 16 gráficas
        ├── 00_BALANCE_INTEGRADO_COMPLETO.png
        ├── 00_INTEGRAL_todas_curvas.png ⭐
        ├── 05.1_bess_carga_descarga.png
        └── ... (13 más)

scripts/
└── regenerate_graphics_v57.py     ← WRAPPER que usa balance.py
```

---

## 🚀 Regenerar Gráficas

```bash
python scripts/regenerate_graphics_v57.py 2>&1
```

Output esperado:
```
✓ Dataset cargado: 8760 filas × 35 columnas
✓ 19 mapeos de columnas aplicados
✓ 5 columnas derivadas creadas
✓ Balance system inicializado
► Delegando a balance.py::BalanceEnergeticoSystem.plot_energy_balance()
  [OK] 00_BALANCE_INTEGRADO_COMPLETO.png
  [OK] 00_INTEGRAL_todas_curvas.png
  [OK] 05.1_bess_carga_descarga.png
  ... (13 más)
✅ REGENERACIÓN COMPLETADA
```

---

## ⚠️ NO HACER

```python
# ❌ NO ejecutar generate_bess_plots() para gráficas de balance
from bess import generate_bess_plots
generate_bess_plots()  # ← INCORRECTO

# ✅ SÍ usar regenerate_graphics_v57.py
python scripts/regenerate_graphics_v57.py  # ← CORRECTO
```

---

## Versiones

- **v5.7** (2026-02-20): Validación solar 8.29 GWh, HP/HFP tarifaria
- **v5.8** (2026-02-20): Archivos arquictectura clarificados
- **v5.9** (2026-02-21): BESS 2,000 kWh, datos correctos en gráficas

---

**Última actualización:** 2026-02-21
**Responsable:** BalanceEnergeticoSystem (balance.py)
**Punto entrada:** regenerate_graphics_v57.py
