#!/usr/bin/env python3
"""
Combine perfil solar único con 101 escenarios de demanda para CityLearn v2
Genera archivos CSV con estructura: timestamp, pv_power_kw, demand_kw
"""

import sys
import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent

def combinar_solar_con_demanda():
    """
    Combina perfil solar único con 101 escenarios de demanda
    Genera 101 archivos CSV listos para CityLearn v2
    """

    print("\n" + "="*80)
    print("COMBINADOR PERFIL SOLAR + 101 ESCENARIOS DE DEMANDA")
    print("="*80)

    # Cargar perfil solar
    solar_file = PROJECT_ROOT / "data" / "oe2" / "perfiles_solares" / "perfil_solar_15min_anual.csv"
    if not solar_file.exists():
        print(f"ERROR: No encontrado {solar_file}")
        return False

    pv_df = pd.read_csv(solar_file)
    print(f"\nPerfil solar cargado: {len(pv_df):,} registros")
    print(f"Resolución: 15 minutos")

    # Cargar escenarios de demanda
    demand_dir = PROJECT_ROOT / "data" / "oe2" / "escenarios_101" / "perfiles_15min"
    if not demand_dir.exists():
        print(f"ERROR: No encontrado {demand_dir}")
        return False

    # Listar todos los escenarios de demanda (motos)
    demand_files = sorted(demand_dir.glob("escenario_*_motos.csv"))
    print(f"\nEscenarios de demanda encontrados: {len(demand_files)}")

    if len(demand_files) == 0:
        print("ERROR: No se encontraron escenarios de demanda")
        return False

    # Crear directorio de salida
    output_dir = PROJECT_ROOT / "data" / "oe2" / "citylearn_v2_101_escenarios"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nComenzando combinación de escenarios...")
    print("="*80)

    escenarios_metadata = []
    pv_anual = pv_df['pv_energy_kwh'].sum()

    # Procesar cada escenario
    for idx, demand_file in enumerate(demand_files, 1):
        escenario_num = f"{idx:03d}"

        try:
            # Cargar demanda
            demand_df = pd.read_csv(demand_file)

            # Validar que tenemos el mismo número de timesteps
            if len(demand_df) != len(pv_df):
                # Si no coinciden, usar resampling para alinear
                # Crear índice de tiempo para ambos
                if len(pv_df) < len(demand_df):
                    # Interpolar PV para que coincida con demanda
                    pv_temp = pv_df.copy()
                    pv_temp = pv_temp.reindex(range(len(demand_df)), method='ffill')
                else:
                    # Recortar demanda para que coincida con PV
                    demand_df = demand_df.iloc[:len(pv_df)].reset_index(drop=True)
            else:
                pv_temp = pv_df.copy()

            # Crear archivo combinado
            combined = pd.DataFrame({
                'timestamp': pv_temp['timestamp'].iloc[:len(demand_df)].values,
                'hour': pv_temp['hour'].iloc[:len(demand_df)].values,
                'minute': pv_temp['minute'].iloc[:len(demand_df)].values,
                'day': pv_temp['day'].iloc[:len(demand_df)].values,
                'pv_power_kw': pv_temp['pv_power_kw'].iloc[:len(demand_df)].values,
                'pv_energy_kwh': pv_temp['pv_energy_kwh'].iloc[:len(demand_df)].values,
                'demand_kw': demand_df['power_kw'].values,
                'demand_kwh': demand_df['energy_kwh'].values,
            })

            # Guardar
            output_file = output_dir / f"escenario_{escenario_num}_citylearn.csv"
            combined.to_csv(output_file, index=False)

            # Estadísticas
            energy_anual = demand_df['energy_kwh'].sum()
            demand_max = demand_df['power_kw'].max()
            pv_anual = pv_df['pv_energy_kwh'].sum()

            escenarios_metadata.append({
                "numero": int(escenario_num),
                "nombre": f"Escenario_{escenario_num}",
                "demanda_anual_kwh": float(energy_anual),
                "demanda_max_kw": float(demand_max),
                "demanda_promedio_kw": float(demand_df['power_kw'].mean()),
                "generacion_solar_kwh": float(pv_anual),
                "timesteps": len(combined),
                "archivo": str(output_file.name)
            })

            if idx % 20 == 0 or idx == 1:
                print(f"[{idx:3d}/101] Escenario {escenario_num} OK - Demanda: {energy_anual:,.0f} kWh/año")

        except Exception as e:
            print(f"ERROR Escenario {escenario_num}: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"COMPLETADO: {len(escenarios_metadata)} escenarios generados")
    print(f"{'='*80}")

    # Guardar metadatos
    metadata = {
        "total_escenarios": len(escenarios_metadata),
        "resolucion_minutos": 15,
        "timesteps_por_escenario": len(pv_df),
        "dias": 365,
        "año": 2024,
        "generacion_solar_unica": True,
        "directorio_salida": str(output_dir),
        "descripcion": "101 escenarios con MISMO perfil solar único y DIFERENTE demanda de cargadores",
        "escenarios": escenarios_metadata
    }

    metadata_file = output_dir / "citylearn_v2_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nMetadatos guardados: {metadata_file}")

    # Resumen por rango
    ranges = [
        ("Escenarios 1-20 (BAJO)", 0, 20),
        ("Escenarios 21-40 (BAJO-MEDIO)", 20, 40),
        ("Escenarios 41-60 (MEDIO)", 40, 60),
        ("Escenarios 61-80 (MEDIO-ALTO)", 60, 80),
        ("Escenarios 81-101 (ALTO)", 80, 101)
    ]

    print("\nRESUMEN POR RANGO:")
    print("-" * 80)
    for nombre, inicio, fin in ranges:
        subset = escenarios_metadata[inicio:fin]
        if subset:
            demanda_promedio = sum(s['demanda_anual_kwh'] for s in subset) / len(subset)
            demanda_min = min(s['demanda_anual_kwh'] for s in subset)
            demanda_max = max(s['demanda_anual_kwh'] for s in subset)
            print(f"{nombre:30s} | Demanda: {demanda_min:,.0f} - {demanda_max:,.0f} kWh/año (promedio: {demanda_promedio:,.0f})")

    print(f"\nGeneracion solar (igual para todos): {pv_anual:,.0f} kWh/año")

    return True

if __name__ == "__main__":
    print("\nCOMBINANDO PERFIL SOLAR CON 101 ESCENARIOS")

    try:
        success = combinar_solar_con_demanda()

        if success:
            print("\nRESULTADO: EXITO")
            print("Archivos listos para entrenar en CityLearn v2")
        else:
            print("\nRESULTADO: ERROR")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
