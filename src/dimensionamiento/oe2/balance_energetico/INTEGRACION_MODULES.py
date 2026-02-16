"""
Integracion entre modulo BESS y Balance Energetico.

Este archivo documenta como el modulo balance.py complementa y extiende
las funcionalidades de bess.py para un analisis integral del sistema.
"""

from pathlib import Path
from typing import Optional
import pandas as pd

# Ilustracion de la integracion
INTEGRATION_MAP = """

RELACION ENTRE MODULOS:
====================================================================

+- bess.py (Simulacion BESS)
|  +- Carga solar: load_pv_generation()
|  +- Demanda mall: load_mall_demand_real()
|  +- Demanda EV: load_ev_demand()
|  +- Simula BESS: simulate_bess_operation()
|  +- Grafica principal: generate_bess_plots() [4 paneles]
|
+- balance.py (Balance Energetico Integral) <- NUEVO MODULO
|  +- Carga TODOS los datasets de CityLearn
|  +- Integra: Solar + Chargers + Mall + BESS
|  +- Calcula flujos globales del sistema
|  +- Genera 7 graficas multiescala
|  +- Exporta metricas + CSV
|
+- dataset_builder.py (Validacion CityLearn)
   +- Valida estructura de datos
   +- Mapea columnas automaticamente
   +- Garantiza consistencia (8,760 horas)

====================================================================

DIFERENCIAS KEY:

                    bess.py              |  balance.py
----------------------------------------------------------------
Responsabilidad   Simulacion BESS       Analisis integral sistema
Fuentes datos     PV, EV, Mall, BESS    [OK] Todas 4 fuentes CityLearn
Flujos mostrados  Detallado por hora    Multiples escalas (h,d,m)
Graficas          4 paneles             7 graficas especializadas
Metricas          Balance BESS          13 metricas de desempeno
Emisiones CO2     No incluye            Si (por importacion grid)
Autosuficiencia   Implicito             Explicito (%)
Exportacion       CSV hora a hora       CSV + 7 PNG profesionales

====================================================================

FLUJO DE DATOS:

1. Carga de archivos:
   data/processed/citylearn/iquitos_ev_mall/
   +- Generacionsolar/pv_generation_hourly_citylearn_v2.csv
   +- chargers/chargers_real_hourly_2024.csv
   +- demandamallkwh/demandamallhorakwh.csv
   +- electrical_storage_simulation.csv
         v
   [load_all_datasets() - balance.py]
         v
2. Validacion automatica:
   - 8,760 filas (1 ano) [OK]
   - Tipos de datos [OK]
   - Columnas validas [OK]
         v
   [_extract_column() - busqueda flexible de columnas]
         v
3. Calculo de balance energetico:
   - PV disponible -> Demanda (directo)
   - Excedente PV -> BESS (carga)
   - BESS descarga -> Demanda (complemento)
   - Deficit -> Grid (importacion)
         v
   [calculate_balance() - 14 columnas en DataFrame]
         v
4. Analisis de metricas:
   - Generacion y demanda anual
   - Cobertura por fuente (%)
   - Autosuficiencia integral
   - Eficiencia PV
   - Emisiones CO2
         v
   [_calculate_metrics() - 13 KPIs]
         v
5. Visualizacion multiescala:
   +- 5 dias representativos (variabilidad)
   +- 365 dias (tendencia anual)
   +- Distribucion de fuentes (pie)
   +- Cascada energetica (flujos)
   +- SOC BESS (carga)
   +- Emisiones CO2 (impacto)
   +- Utilizacion PV mensual (estacionalidad)
         v
   [plot_energy_balance() - 7 PNG de alta calidad]
         v
6. Exportacion de datos:
   +- balance_energetico_horario.csv (8,760 filas × 14 cols)
   +- 01_balance_5dias.png
   +- 02_balance_diario.png
   +- 03_distribucion_fuentes.png
   +- 04_cascada_energetica.png
   +- 05_bess_soc.png
   +- 06_emisiones_co2.png
   +- 07_utilizacion_pv.png
         v
   reports/balance_energetico/

====================================================================
"""


def compare_outputs():
    """
    Compara las salidas de bess.py vs balance.py.
    
    bess.py (simulate_bess_operation):
    -----------------------------------
    - Entrada: pv_kwh[], ev_kwh[], mall_kwh[], capacity, power
    - Salida: DataFrame 12 columnas
      * hour, pv_kwh, ev_kwh, mall_kwh
      * pv_used_ev_kwh, pv_used_mall_kwh
      * bess_charge_kwh, bess_discharge_kwh
      * grid_import_ev_kwh, grid_import_mall_kwh
      * grid_export_kwh, soc_percent
    - Grafica: 4 paneles (demanda, balance PV, SOC, BESScarga-descarga)
    
    balance.py (calculate_balance):
    -------------------------------
    - Entrada: 4 archivos CSV (8,760 filas cada uno)
    - Salida: DataFrame 14 columnas + 13 metricas
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
    
    - Metricas (13):
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
    
    - Graficas: 7 especializadas
      * Variabilidad solar (5 dias)
      * Evolucion anual (365 dias)
      * Distribucion de fuentes (pie chart)
      * Cascada energetica (sankey)
      * SOC BESS evolution
      * Emisiones CO2 diarias
      * Utilizacion PV mensual
    """
    pass


def integration_example():
    """
    Ejemplo: Como usar bess.py para simular un escenario especifico
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
    
    # PASO 1: Simulacion especifica con bess.py
    # -----------------------------------------
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
    
    # Generar graficas BESS
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
    
    print("[OK] Simulacion BESS completada")
    print(f"  Self-sufficiency: {metrics_bess['self_sufficiency']*100:.1f}%")
    
    # PASO 2: Validacion integral con balance.py
    # ------------------------------------------
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
    
    print("[OK] Analisis de balance energetico completado")
    print(f"  Autosuficiencia: {system.metrics['self_sufficiency_percent']:.1f}%")
    print(f"  CO2 total: {system.metrics['total_co2_kg']:.0f} kg/ano")
    
    # COMPARACION:
    # ============
    # bess.py: Proporciona control fino sobre parametros de simulacion
    # balance.py: Integra TODA la cadena de datos de CityLearn
    #
    # Ambos contribuyen a diferentes partes del analisis:
    # - bess.py: Especificaciones tecnicas de BESS
    # - balance.py: Impacto sistemico en red electrica
    
    """
    
    print(code)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("INTEGRACION: bess.py ↔ balance.py")
    print("="*70)
    
    print(INTEGRATION_MAP)
    
    print("\n" + "="*70)
    print("COMPARACION DE SALIDAS")
    print("="*70)
    
    compare_outputs()
    
    print("\n" + "="*70)
    print("EJEMPLO DE INTEGRACION")
    print("="*70)
    
    integration_example()
    
    print("\n[OK] Ver archivos para integracion completa")
