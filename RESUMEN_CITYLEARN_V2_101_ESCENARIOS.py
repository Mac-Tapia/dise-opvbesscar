#!/usr/bin/env python3
"""
Resumen Visual - 101 Escenarios CityLearn v2
Muestra estadísticas de perfil solar único + 101 escenarios de demanda
"""

import pandas as pd
import json
from pathlib import Path

def mostrar_resumen():
    """Muestra resumen completo de escenarios generados"""

    root = Path(__file__).parent
    output_dir = root / "data" / "oe2" / "citylearn_v2_101_escenarios"
    metadata_file = output_dir / "citylearn_v2_metadata.json"
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    # Cargar perfil solar
    solar_file = root / "data" / "oe2" / "perfiles_solares" / "perfil_solar_15min_anual.csv"
    solar_df = pd.read_csv(solar_file)

    print("\n" + "="*90)
    print("RESUMEN: 101 ESCENARIOS PARA CITYLEARN V2")
    print("="*90)

    print(f"\nPERFIL SOLAR (UNICO - IGUAL PARA TODOS)")
    print("-" * 90)
    print(f"  Archivo:                perfil_solar_15min_anual.csv")
    print(f"  Ubicación:              Iquitos, Perú (-3.75°, -73.25°)")
    print(f"  Resolución:             15 minutos")
    print(f"  Período:                1 año (365 días)")
    print(f"  Timesteps:              {len(solar_df):,}")
    print(f"  Energía anual:          {solar_df['pv_energy_kwh'].sum():,.0f} kWh")
    print(f"  Potencia máxima:        {solar_df['pv_power_kw'].max():.2f} kW")
    print(f"  Potencia promedio:      {solar_df['pv_power_kw'].mean():.2f} kW")

    print(f"\nESTADÍSTICAS DE 101 ESCENARIOS DE DEMANDA")
    print("-" * 90)

    escenarios = metadata['escenarios']

    # Calcular estadísticas
    demandas = [e['demanda_anual_kwh'] for e in escenarios]
    demanda_min = min(demandas)
    demanda_max = max(demandas)
    demanda_prom = sum(demandas) / len(demandas)

    print(f"  Total escenarios:       {metadata['total_escenarios']}")
    print(f"  Demanda mínima:         {demanda_min:,.0f} kWh/año (Escenario 001)")
    print(f"  Demanda máxima:         {demanda_max:,.0f} kWh/año (Escenario 101)")
    print(f"  Demanda promedio:       {demanda_prom:,.0f} kWh/año")
    print(f"  Ratio Solar/Demanda:    {solar_df['pv_energy_kwh'].sum() / demanda_max:.1f}x (mín) a {solar_df['pv_energy_kwh'].sum() / demanda_min:.1f}x (máx)")

    print(f"\nDISTRIBUCIÓN POR RANGO")
    print("-" * 90)

    ranges = [
        ("BAJO", 0, 20),
        ("BAJO-MEDIO", 20, 40),
        ("MEDIO", 40, 60),
        ("MEDIO-ALTO", 60, 80),
        ("ALTO", 80, 101)
    ]

    for nombre, inicio, fin in ranges:
        subset = escenarios[inicio:fin]
        subset_demandas = [e['demanda_anual_kwh'] for e in subset]
        subset_min = min(subset_demandas)
        subset_max = max(subset_demandas)
        subset_prom = sum(subset_demandas) / len(subset_demandas)

        print(f"  {nombre:15s} (Esc {inicio+1:3d}-{fin:3d}): {subset_min:>8,.0f} - {subset_max:>8,.0f} kWh/año (prom: {subset_prom:>8,.0f})")

    print(f"\nARCHIVOS GENERADOS")
    print("-" * 90)
    print(f"  Ubicación:              {output_dir.name}/")
    print(f"  Archivos CSV:           101 × escenario_###_citylearn.csv")
    print(f"  Tamaño total:           ~182 MB")
    print(f"  Metadatos:              citylearn_v2_metadata.json")
    print(f"  Documentación:          README.md")

    print(f"\nCARACTERÍSTICAS DE CADA ESCENARIO")
    print("-" * 90)
    print(f"  Columnas:               timestamp, hour, minute, day, pv_power_kw, pv_energy_kwh, demand_kw, demand_kwh")
    print(f"  Timesteps:              {metadata['timesteps_por_escenario']:,}")
    print(f"  Período:                {metadata['dias']} días")
    print(f"  Resolución:             {metadata['resolucion_minutos']} minutos")
    print(f"  Generación solar:       IGUAL para todos 101 escenarios")
    print(f"  Demanda:                DIFERENTE para cada escenario")

    print(f"\nESTRUCTURA PARA CITYLEARN V2")
    print("-" * 90)
    print(f"""
    Cada escenario proporciona:

    [ENTRADA]
    - timestamp        : Tiempo en ISO 8601 (UTC-5)
    - hour/minute/day  : Información temporal
    - pv_power_kw      : Generación solar instantánea (igual para todos)
    - demand_kw        : Demanda de cargadores (varía por escenario)

    [CONTROL BESS]
    - BESS Capacidad   : 1,632 kWh
    - BESS Potencia    : 593 kW
    - Factor descarga  : 80%

    [OBJETIVO AGENTE]
    - Minimizar costo operativo
    - Balancear solar + demanda
    - Optimizar ciclos BESS
    """)

    print(f"\nINDICES DE DEMANDA REPRESENTATIVOS")
    print("-" * 90)

    # Mostrar algunos escenarios clave
    indices_key = [0, 20, 50, 70, 100]
    for idx in indices_key:
        e = escenarios[idx]
        print(f"  Escenario {e['numero']:3d}: {e['demanda_anual_kwh']:>8,.0f} kWh/año | Max: {e['demanda_max_kw']:>7.2f} kW | Prom: {e['demanda_promedio_kw']:>6.2f} kW")

    print(f"\nPRÓXIMOS PASOS")
    print("-" * 90)
    print(f"  1. Cargar escenarios en CityLearn v2")
    print(f"  2. Entrenar agentes RL (SAC, PPO, A2C)")
    print(f"  3. Validar convergencia en todos los escenarios")
    print(f"  4. Analizar performance BESS por rango de demanda")
    print(f"  5. Optimizar parámetros control")

    print(f"\nESTADÍSTICAS ADICIONALES")
    print("-" * 90)

    # Cargar un escenario para mostrar estadísticas
    primer_csv = output_dir / "escenario_001_citylearn.csv"
    escenario_df = pd.read_csv(primer_csv)

    print(f"  Energía solar diaria (promedio):    {solar_df['pv_energy_kwh'].sum() / 365:>10.2f} kWh")
    print(f"  Energía demanda diaria (esc 001):   {escenario_df['demand_kwh'].sum() / 365:>10.2f} kWh")
    print(f"  Energía demanda diaria (esc 101):   {escenarios[100]['demanda_anual_kwh'] / 365:>10.2f} kWh")
    print(f"  Ratio pico solar/demanda (esc 001): {solar_df['pv_power_kw'].max() / escenario_df['demand_kw'].max():>10.2f}x")

    print(f"\n" + "="*90)
    print("ESTADO: LISTO PARA ENTRENAR EN CITYLEARN V2")
    print("="*90 + "\n")

if __name__ == "__main__":
    try:
        mostrar_resumen()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
