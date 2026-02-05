"""
Script para generar perfil de generación solar HORARIO para 2024.
Salida: data/oe2/Generacionsolar/
Columnas: Fecha, Hora, Energía (kWh), Potencia (kW), Temperatura (°C), Densidad Luminosa (W/m²)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Importar directamente del módulo sin pasar por __init__
import importlib.util
spec = importlib.util.spec_from_file_location(
    "solar_pvlib",
    Path(__file__).parent / "src" / "dimensionamiento" / "oe2" / "solar_pvlib.py"
)
solar_pvlib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solar_pvlib)

PVSystemConfig = solar_pvlib.PVSystemConfig
build_pv_timeseries_sandia = solar_pvlib.build_pv_timeseries_sandia
IQUITOS_PARAMS = solar_pvlib.IQUITOS_PARAMS

import pandas as pd
import numpy as np


def main():
    """Genera perfil de generación solar horario y lo guarda en CSV."""

    print("=" * 80)
    print("  GENERACIÓN DE PERFIL SOLAR HORARIO - IQUITOS 2024")
    print("=" * 80)

    # Crear directorio de salida
    output_dir = Path("data/oe2/Generacionsolar")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n✓ Directorio de salida: {output_dir.absolute()}")

    # Configuración del sistema PV
    config = PVSystemConfig(
        latitude=float(IQUITOS_PARAMS["lat"]),
        longitude=float(IQUITOS_PARAMS["lon"]),
        timezone=str(IQUITOS_PARAMS["tz"]),
        altitude=float(IQUITOS_PARAMS["alt"]),
        area_total_m2=float(IQUITOS_PARAMS["area_total_m2"]),
        factor_diseno=float(IQUITOS_PARAMS["factor_diseno"]),
        tilt=float(IQUITOS_PARAMS["surface_tilt"]),
        azimuth=float(IQUITOS_PARAMS["surface_azimuth"]),
    )

    print("\n[1/3] Ejecutando simulación solar...")
    print("      - Resolución: HORARIA (3600 segundos)")
    print("      - Año: 2024")
    print("      - Ubicación: Iquitos, Perú (-3.75°, -73.25°)")
    print("      - Sistema: 4,050 kWp solar")

    # Ejecutar simulación PV con resolución HORARIA (3600 segundos)
    results, metadata = build_pv_timeseries_sandia(
        year=2024,
        config=config,
        target_dc_kw=4050.0,  # Potencia DC objetivo
        target_ac_kw=3201.0,  # Potencia AC objetivo
        target_annual_kwh=8_000_000.0,  # 8 GWh objetivo anual
        seconds_per_time_step=3600,  # ← HORARIO (NO 15 minutos)
        selection_mode="manual",
    )

    print(f"      ✓ Simulación completada: {len(results)} registros horarios")

    # Verificar que tenemos datos horarios (8760 registros para 365 días × 24 horas)
    if len(results) != 8760:
        print(f"\n⚠️  ADVERTENCIA: Se esperaban 8,760 registros horarios (365 días × 24 h)")
        print(f"    Se obtuvieron {len(results)} registros")
        if len(results) == 35040:
            print("    Detectado: Datos a 15 minutos en lugar de horarios")
            print("    Remuestreando a resolución horaria...")
            results = results.resample("h").mean()

    print("\n[2/3] Preparando dataframe con columnas requeridas...")

    # Crear dataframe con columnas requeridas
    df_output = pd.DataFrame()

    # 1. Fechas y horas (enero a diciembre)
    df_output['Fecha'] = pd.to_datetime(results.index).date
    df_output['Hora'] = pd.to_datetime(results.index).hour
    df_output['Fecha_Hora'] = results.index.strftime('%Y-%m-%d %H:00')

    # 2. Energía en kWh (por hora)
    df_output['Energia_kWh'] = results['ac_energy_kwh'].values

    # 3. Potencia en kW (por hora)
    df_output['Potencia_kW'] = results['ac_power_kw'].values

    # 4. Temperatura en °C
    if 'temp_air_c' in results.columns:
        df_output['Temperatura_C'] = results['temp_air_c'].values
    else:
        print(f"      ⚠️  Columna 'temp_air_c' no encontrada. Columnas disponibles: {results.columns.tolist()}")
        df_output['Temperatura_C'] = np.nan

    # 5. Densidad luminosa (GHI - Global Horizontal Irradiance en W/m²)
    if 'ghi_wm2' in results.columns:
        df_output['Densidad_Luminosa_Wm2'] = results['ghi_wm2'].values
    else:
        print(f"      ⚠️  Columna 'ghi_wm2' no encontrada.")
        df_output['Densidad_Luminosa_Wm2'] = np.nan

    # 6. Tiempo en horas (índice 0-8759)
    df_output['Tiempo_Hora'] = range(len(df_output))

    # Reordenar columnas lógicamente
    df_output = df_output[[
        'Fecha_Hora',
        'Fecha',
        'Hora',
        'Tiempo_Hora',
        'Energia_kWh',
        'Potencia_kW',
        'Temperatura_C',
        'Densidad_Luminosa_Wm2',
    ]]

    print(f"      ✓ Dataframe creado: {len(df_output)} registros × {len(df_output.columns)} columnas")
    print(f"      ✓ Columnas: {', '.join(df_output.columns.tolist())}")

    # Estadísticas rápidas
    print("\n[3/3] Guardando resultados...")
    print(f"\n      📊 ESTADÍSTICAS RÁPIDAS:")
    print(f"         Energía total anual:     {df_output['Energia_kWh'].sum():>12,.1f} kWh")
    print(f"         Potencia promedio:        {df_output['Potencia_kW'].mean():>12,.1f} kW")
    print(f"         Potencia máxima:          {df_output['Potencia_kW'].max():>12,.1f} kW")
    print(f"         Temperatura promedio:     {df_output['Temperatura_C'].mean():>12,.1f} °C")
    print(f"         Densidad luminosa máx:    {df_output['Densidad_Luminosa_Wm2'].max():>12,.1f} W/m²")

    # Guardar CSV principal
    csv_path = output_dir / "generacion_solar_2024_horaria.csv"
    df_output.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n      ✓ CSV guardado: {csv_path.absolute()}")

    # Guardar resumen estadístico
    summary_path = output_dir / "estadisticas_generacion.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("ESTADÍSTICAS DE GENERACIÓN SOLAR - IQUITOS 2024\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Periodo: Enero 1 - Diciembre 31, 2024 (8,760 horas)\n")
        f.write(f"Resolución: Horaria (1 hora)\n\n")
        f.write(f"ENERGÍA:\n")
        f.write(f"  Total anual:              {df_output['Energia_kWh'].sum():>12,.1f} kWh\n")
        f.write(f"  Promedio diario:          {df_output['Energia_kWh'].sum()/365:>12,.1f} kWh/día\n")
        f.write(f"  Máximo horario:           {df_output['Energia_kWh'].max():>12,.1f} kWh\n")
        f.write(f"  Mínimo horario:           {df_output['Energia_kWh'].min():>12,.1f} kWh\n\n")
        f.write(f"POTENCIA:\n")
        f.write(f"  Promedio:                 {df_output['Potencia_kW'].mean():>12,.1f} kW\n")
        f.write(f"  Máxima:                   {df_output['Potencia_kW'].max():>12,.1f} kW\n")
        f.write(f"  Mínima:                   {df_output['Potencia_kW'].min():>12,.1f} kW\n\n")
        f.write(f"TEMPERATURA:\n")
        f.write(f"  Promedio:                 {df_output['Temperatura_C'].mean():>12,.1f} °C\n")
        f.write(f"  Máxima:                   {df_output['Temperatura_C'].max():>12,.1f} °C\n")
        f.write(f"  Mínima:                   {df_output['Temperatura_C'].min():>12,.1f} °C\n\n")
        f.write(f"DENSIDAD LUMINOSA (GHI):\n")
        f.write(f"  Promedio:                 {df_output['Densidad_Luminosa_Wm2'].mean():>12,.1f} W/m²\n")
        f.write(f"  Máxima:                   {df_output['Densidad_Luminosa_Wm2'].max():>12,.1f} W/m²\n")
        f.write(f"  Mínima:                   {df_output['Densidad_Luminosa_Wm2'].min():>12,.1f} W/m²\n")

    print(f"      ✓ Estadísticas guardadas: {summary_path.absolute()}")

    # Guardar también formato Excel si es posible
    try:
        excel_path = output_dir / "generacion_solar_2024_horaria.xlsx"
        df_output.to_excel(excel_path, index=False, sheet_name='Solar_2024')
        print(f"      ✓ Excel guardado: {excel_path.absolute()}")
    except ImportError:
        print("      ⚠️  openpyxl no instalado, saltando Excel")

    print("\n" + "=" * 80)
    print("  ✅ GENERACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print(f"\nArchivos generados en: {output_dir.absolute()}")
    print(f"  • generacion_solar_2024_horaria.csv - Datos completos")
    print(f"  • estadisticas_generacion.txt - Resumen estadístico")
    if (output_dir / "generacion_solar_2024_horaria.xlsx").exists():
        print(f"  • generacion_solar_2024_horaria.xlsx - Formato Excel")

    # Mostrar primeras y últimas filas
    print(f"\n📋 PREVIEW DE DATOS (primeras 5 filas):")
    print(df_output.head(5).to_string(index=False))
    print(f"\n📋 ÚLTIMAS 5 FILAS:")
    print(df_output.tail(5).to_string(index=False))

    return df_output


if __name__ == "__main__":
    try:
        df = main()
        print("\n✨ Proceso completado sin errores.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
