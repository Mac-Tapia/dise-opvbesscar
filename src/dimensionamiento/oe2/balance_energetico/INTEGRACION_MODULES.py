"""
Integración entre módulo BESS y Balance Energético.

Este archivo documenta cómo el módulo balance.py complementa y extiende
las funcionalidades de bess.py para un análisis integral del sistema.
"""

from pathlib import Path
from typing import Optional
import pandas as pd

# Ilustración de la integración
INTEGRATION_MAP = """

RELACIÓN ENTRE MÓDULOS:
════════════════════════════════════════════════════════════════════

┌─ bess.py (Simulación BESS)
│  ├─ Carga solar: load_pv_generation()
│  ├─ Demanda mall: load_mall_demand_real()
│  ├─ Demanda EV: load_ev_demand()
│  ├─ Simula BESS: simulate_bess_operation()
│  └─ Gráfica principal: generate_bess_plots() [4 paneles]
│
├─ balance.py (Balance Energético Integral) ← NUEVO MÓDULO
│  ├─ Carga TODOS los datasets de CityLearn
│  ├─ Integra: Solar + Chargers + Mall + BESS
│  ├─ Calcula flujos globales del sistema
│  ├─ Genera 7 gráficas multiescala
│  └─ Exporta métricas + CSV
│
└─ dataset_builder.py (Validación CityLearn)
   ├─ Valida estructura de datos
   ├─ Mapea columnas automáticamente
   └─ Garantiza consistencia (8,760 horas)

════════════════════════════════════════════════════════════════════

DIFERENCIAS KEY:

                    bess.py              |  balance.py
────────────────────────────────────────────────────────────────
Responsabilidad   Simulación BESS       Análisis integral sistema
Fuentes datos     PV, EV, Mall, BESS    ✓ Todas 4 fuentes CityLearn
Flujos mostrados  Detallado por hora    Múltiples escalas (h,d,m)
Gráficas          4 paneles             7 gráficas especializadas
Métricas          Balance BESS          13 métricas de desempeño
Emisiones CO2     No incluye            Sí (por importación grid)
Autosuficiencia   Implícito             Explícito (%)
Exportación       CSV hora a hora       CSV + 7 PNG profesionales

════════════════════════════════════════════════════════════════════

FLUJO DE DATOS:

1. Carga de archivos:
   data/processed/citylearn/iquitos_ev_mall/
   ├─ Generacionsolar/pv_generation_hourly_citylearn_v2.csv
   ├─ chargers/chargers_real_hourly_2024.csv
   ├─ demandamallkwh/demandamallhorakwh.csv
   └─ electrical_storage_simulation.csv
         ↓
   [load_all_datasets() - balance.py]
         ↓
2. Validación automática:
   - 8,760 filas (1 año) ✓
   - Tipos de datos ✓
   - Columnas válidas ✓
         ↓
   [_extract_column() - búsqueda flexible de columnas]
         ↓
3. Cálculo de balance energético:
   - PV disponible → Demanda (directo)
   - Excedente PV → BESS (carga)
   - BESS descarga → Demanda (complemento)
   - Déficit → Grid (importación)
         ↓
   [calculate_balance() - 14 columnas en DataFrame]
         ↓
4. Análisis de métricas:
   - Generación y demanda anual
   - Cobertura por fuente (%)
   - Autosuficiencia integral
   - Eficiencia PV
   - Emisiones CO2
         ↓
   [_calculate_metrics() - 13 KPIs]
         ↓
5. Visualización multiescala:
   ├─ 5 días representativos (variabilidad)
   ├─ 365 días (tendencia anual)
   ├─ Distribución de fuentes (pie)
   ├─ Cascada energética (flujos)
   ├─ SOC BESS (carga)
   ├─ Emisiones CO2 (impacto)
   └─ Utilización PV mensual (estacionalidad)
         ↓
   [plot_energy_balance() - 7 PNG de alta calidad]
         ↓
6. Exportación de datos:
   ├─ balance_energetico_horario.csv (8,760 filas × 14 cols)
   ├─ 01_balance_5dias.png
   ├─ 02_balance_diario.png
   ├─ 03_distribucion_fuentes.png
   ├─ 04_cascada_energetica.png
   ├─ 05_bess_soc.png
   ├─ 06_emisiones_co2.png
   └─ 07_utilizacion_pv.png
         ↓
   reports/balance_energetico/

════════════════════════════════════════════════════════════════════
"""


def compare_outputs():
    """
    Compara las salidas de bess.py vs balance.py.
    
    bess.py (simulate_bess_operation):
    ───────────────────────────────────
    - Entrada: pv_kwh[], ev_kwh[], mall_kwh[], capacity, power
    - Salida: DataFrame 12 columnas
      * hour, pv_kwh, ev_kwh, mall_kwh
      * pv_used_ev_kwh, pv_used_mall_kwh
      * bess_charge_kwh, bess_discharge_kwh
      * grid_import_ev_kwh, grid_import_mall_kwh
      * grid_export_kwh, soc_percent
    - Gráfica: 4 paneles (demanda, balance PV, SOC, BESScarga-descarga)
    
    balance.py (calculate_balance):
    ───────────────────────────────
    - Entrada: 4 archivos CSV (8,760 filas cada uno)
    - Salida: DataFrame 14 columnas + 13 métricas
      * hour, pv_generation_kw, ev_demand_kw, mall_demand_kw
      * total_demand_kw
      * pv_to_demand_kw (PV directo)
      * pv_surplus_kw (excedente PV)
      * pv_to_bess_kw, pv_to_grid_kw
      * bess_charge_kw, bess_discharge_kw
      * bess_to_demand_kw
      * demand_from_grid_kw
      * bess_soc_percent
      * co2_from_grid_kg
    
    - Métricas (13):
      * total_pv_kwh, total_demand_kwh, total_grid_import_kwh
      * total_bess_discharge_kwh, total_pv_to_demand_kwh
      * total_pv_waste_kwh
      * self_sufficiency_percent (NUEVO)
      * pv_coverage_percent (NUEVO)
      * bess_coverage_percent (NUEVO)
      * grid_coverage_percent (NUEVO)
      * pv_utilization_percent (NUEVO)
      * total_co2_kg (NUEVO)
      * co2_per_kwh (NUEVO)
    
    - Gráficas: 7 especializadas
      * Variabilidad solar (5 días)
      * Evolución anual (365 días)
      * Distribución de fuentes (pie chart)
      * Cascada energética (sankey)
      * SOC BESS evolution
      * Emisiones CO2 diarias
      * Utilización PV mensual
    """
    pass


def integration_example():
    """
    Ejemplo: Cómo usar bess.py para simular un escenario específico
    y luego validarlo con balance.py en el contexto CityLearn completo.
    """
    
    code = """
    from pathlib import Path
    import pandas as pd
    from src.dimensionamiento.oe2.disenobess.bess import (
        load_pv_generation,
        load_ev_demand,
        load_mall_demand_real,
        simulate_bess_operation,
        generate_bess_plots,
    )
    from src.dimensionamiento.oe2.balance_energetico import (
        BalanceEnergeticoSystem,
        BalanceEnergeticoConfig,
    )
    
    # PASO 1: Simulación específica con bess.py
    # ─────────────────────────────────────────
    pv_path = Path("data/processed/citylearn/iquitos_ev_mall/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
    ev_path = Path("data/processed/citylearn/iquitos_ev_mall/chargers/chargers_real_hourly_2024.csv")
    mall_path = Path("data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv")
    
    # Cargar
    df_pv = load_pv_generation(pv_path)
    df_ev = load_ev_demand(ev_path)
    df_mall = load_mall_demand_real(mall_path)
    
    # Simular BESS
    df_bess_sim, metrics_bess = simulate_bess_operation(
        pv_kwh=df_pv['pv_kwh'].values,
        ev_kwh=df_ev['ev_kwh'].values,
        mall_kwh=df_mall['mall_kwh'].values,
        capacity_kwh=940.0,   # v5.2: 940 kWh (exclusivo EV, 100% cobertura)
        power_kw=342.0,       # v5.2: 342 kW
        dod=0.80,
        efficiency=0.95,
    )
    
    # Generar gráficas BESS
    generate_bess_plots(
        df_bess_sim,
        capacity_kwh=940.0,   # v5.2
        power_kw=342.0,       # v5.2
        dod=0.80,
        c_rate=0.36,
        mall_kwh_day=df_mall['mall_kwh'].mean(),
        ev_kwh_day=df_ev['ev_kwh'].mean(),
        pv_kwh_day=df_pv['pv_kwh'].mean(),
        out_dir=Path("data/interim/oe2"),
    )
    
    print("✓ Simulación BESS completada")
    print(f"  Self-sufficiency: {metrics_bess['self_sufficiency']*100:.1f}%")
    
    # PASO 2: Validación integral con balance.py
    # ──────────────────────────────────────────
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
        pv_capacity_kwp=4050.0,
        bess_capacity_kwh=940.0,   # v5.2: 940 kWh (exclusivo EV, 100% cobertura)
        bess_power_kw=342.0,       # v5.2: 342 kW
        dod=0.80,
        efficiency_roundtrip=0.95,
    )
    
    system = BalanceEnergeticoSystem(config)
    
    if system.load_all_datasets():
        system.calculate_balance()
        system.print_summary()
        system.plot_energy_balance(Path("reports/balance_energetico"))
    
    print("✓ Análisis de balance energético completado")
    print(f"  Autosuficiencia: {system.metrics['self_sufficiency_percent']:.1f}%")
    print(f"  CO2 total: {system.metrics['total_co2_kg']:.0f} kg/año")
    
    # COMPARACIÓN:
    # ════════════
    # bess.py: Proporciona control fino sobre parámetros de simulación
    # balance.py: Integra TODA la cadena de datos de CityLearn
    #
    # Ambos contribuyen a diferentes partes del análisis:
    # - bess.py: Especificaciones técnicas de BESS
    # - balance.py: Impacto sistémico en red eléctrica
    
    """
    
    print(code)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("INTEGRACIÓN: bess.py ↔ balance.py")
    print("="*70)
    
    print(INTEGRATION_MAP)
    
    print("\n" + "="*70)
    print("COMPARACIÓN DE SALIDAS")
    print("="*70)
    
    compare_outputs()
    
    print("\n" + "="*70)
    print("EJEMPLO DE INTEGRACIÓN")
    print("="*70)
    
    integration_example()
    
    print("\n✓ Ver archivos para integración completa")
