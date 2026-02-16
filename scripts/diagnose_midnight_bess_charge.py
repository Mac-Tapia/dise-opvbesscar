#!/usr/bin/env python3
"""
Diagnostico: Verificar si hay carga BESS anomala en madrugada (300-600 kWh/h)

El BESS NO deberia cargarse en la madrugada (00:00-05:59):
- EV esta cerrado (cierra a las 22h)
- No hay generacion solar
- La unica carga deberia estar en 06:00-22:59

Carga esperada en madrugada: 0 kWh/h (inactivo)
"""
from pathlib import Path
import pandas as pd
import numpy as np

DATASETS = {
    "BESS OE2": "data/oe2/bess/bess_ano_2024.csv",
    "BESS Interim": "data/interim/oe2/bess/bess_hourly_dataset_2024.csv",
    "BESS Processed": "data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv",
}

MIDNIGHT_HOURS = list(range(0, 6))  # 00:00 - 05:00 (madrugada)

def check_bess_midnight_charge():
    """Verifica si hay carga erronea en madrugada."""
    print("\n" + "=" * 80)
    print("🔍 DIAGNOSTICO: Carga BESS en Madrugada")
    print("=" * 80)
    
    for name, path_str in DATASETS.items():
        path = Path(path_str)
        
        if not path.exists():
            print(f"\n[!]  {name}: Archivo no encontrado ({path})")
            continue
        
        print(f"\n[GRAPH] Analizando: {name}")
        print("-" * 80)
        
        try:
            df = pd.read_csv(path, parse_dates=['datetime'] if 'datetime' in open(path).readline() else False)
            
            # Detectar columna de carga
            charge_cols = [col for col in df.columns if 'bess_charge' in col.lower()]
            grid_bess_cols = [col for col in df.columns if 'grid_to_bess' in col.lower()]
            
            if not charge_cols and not grid_bess_cols:
                print(f"   [!]  No se encontraron columnas de carga BESS")
                print(f"   Columnas disponibles: {', '.join(df.columns[:10])}")
                continue
            
            # Extraer hora de indice o columna datetime
            if 'datetime' in df.columns:
                df['hour'] = pd.to_datetime(df['datetime']).dt.hour
            elif isinstance(df.index, pd.DatetimeIndex):
                df['hour'] = df.index.hour
            else:
                df['hour'] = np.arange(len(df)) % 24
            
            # Revisar madrugada (horas 0-5)
            midnight_df = df[df['hour'].isin(MIDNIGHT_HOURS)]
            
            print(f"   📅 Periodo: {len(df)} horas = {len(df)//24} dias")
            print(f"   🌙 Horas madrugada analizadas: {len(midnight_df)} ({len(midnight_df)//24} dias × 6h)")
            
            for col in charge_cols + grid_bess_cols:
                if col not in df.columns:
                    continue
                
                col_data = df[col]
                midnight_data = midnight_df[col].copy()
                
                # Estadisticas totales
                total_max = col_data.max()
                total_mean = col_data.mean()
                
                # Estadisticas madrugada
                midnight_max = midnight_data.max()
                midnight_mean = midnight_data.mean()
                midnight_nonzero = midnight_data[midnight_data > 0.1].count()
                
                print(f"\n   🔋 Columna: {col}")
                print(f"      Total ano: max={total_max:,.1f} kWh, media={total_mean:.1f} kWh")
                print(f"      Madrugada: max={midnight_max:,.1f} kWh, media={midnight_mean:.2f} kWh")
                print(f"      [!]  Horas con carga > 0.1 kWh en madrugada: {midnight_nonzero}/{len(midnight_data)}")
                
                # ALERTA: Si hay carga significativa
                if midnight_max > 10:
                    print(f"      [X] ERROR: Carga de {midnight_max:,.1f} kWh en madrugada (deberia ser 0)")
                    
                    # Mostrar ejemplos
                    anomalies = midnight_df[midnight_df[col] > 10].copy()
                    anomalies['hour_str'] = anomalies['hour'].apply(lambda h: f"{int(h):02d}:00")
                    if 'datetime' in anomalies.columns:
                        print(f"\n      Ejemplos de anomalias:")
                        for idx, row in anomalies.head(5).iterrows():
                            dt = row.get('datetime', f"Hora {int(row['hour']):02d}:00")
                            print(f"      - {dt}: {row[col]:,.1f} kWh")
                else:
                    print(f"      [OK] OK: Madrugada correctamente inactiva")
        
        except Exception as e:
            print(f"   [X] Error al procesar: {e}")
    
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print("❓ Pregunta: ¿Se debe permitir grid_to_bess en madrugada?")
    print("   NO - El BESS no debe cargarse durante madrugada (00:00-05:59)")
    print("   Razones:")
    print("   1. EV esta cerrado (cierra 22h)")
    print("   2. No hay generacion solar (noche)")
    print("   3. No hay arbitraje tarifario (HFP cubre 0-5h pero sin EV activo)")
    print("   4. Genera picos de consumo grid innecesarios en madrugada")
    print("\n[OK] Correccion: Agregar `if hour_of_day < 6: grid_to_bess[h] = 0` al final de cada funcion")

if __name__ == "__main__":
    check_bess_midnight_charge()
