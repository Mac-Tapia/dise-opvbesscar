"""
Diagnosticar y corregir el dataset BESS
Verifica inconsistencias de carga/descarga
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def diagnose_bess():
    """Diagnosticar dataset BESS actual"""
    
    bess_file = Path("data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv")
    metadata_file = Path("data/processed/citylearn/iquitos_ev_mall/bess_metadata.json")
    
    if not bess_file.exists():
        print("ERROR: bess_ano_2024.csv no existe")
        return False
    
    print("\n" + "="*80)
    print("DIAGNOSTICO DEL DATASET BESS")
    print("="*80)
    
    # Cargar CSV
    df = pd.read_csv(bess_file)
    print(f"\n[1] Estructura CSV:")
    print(f"    Filas: {len(df)}")
    print(f"    Columnas: {list(df.columns)}")
    print(f"    Tipo de datos:\n{df.dtypes}\n")
    
    # Mostrar primeras 10 filas
    print("[2] Primeras 10 filas:")
    print(df.head(10).to_string())
    
    print("\n[3] Estadisticas de columnas:")
    print(f"    SOC kWh - Min: {df['soc_kwh'].min():.1f}, Max: {df['soc_kwh'].max():.1f}, Mean: {df['soc_kwh'].mean():.1f}")
    print(f"    SOC % - Min: {df['soc_pct'].min():.2f}, Max: {df['soc_pct'].max():.2f}, Mean: {df['soc_pct'].mean():.2f}")
    print(f"    Power Charge - Min: {df['power_charge_kw'].min():.2f}, Max: {df['power_charge_kw'].max():.2f}")
    print(f"    Power Discharge - Min: {df['power_discharge_kw'].min():.2f}, Max: {df['power_discharge_kw'].max():.2f}")
    
    # Analisis problematico
    print("\n[4] ANALISIS PROBLEMATICO:")
    
    total_charge = df['power_charge_kw'].sum()
    total_discharge = df['power_discharge_kw'].sum()
    
    print(f"    Total energía cargada (suma directa): {total_charge:,.0f} kWh")
    print(f"    Total energía descargada (suma directa): {total_discharge:,.0f} kWh")
    print(f"    Ratio Descarga/Carga: {total_discharge/total_charge if total_charge > 0 else 'N/A':.1f}x")
    
    # Verificar logica fisica
    print("\n[5] VERIFICACION FISICA:")
    print(f"    BESS Capacidad: 1,700 kWh")
    print(f"    SOC Inicial (hora 0): {df.iloc[0]['soc_kwh']:.1f} kWh ({df.iloc[0]['soc_pct']:.2f}%)")
    print(f"    SOC Final (hora 8759): {df.iloc[-1]['soc_kwh']:.1f} kWh ({df.iloc[-1]['soc_pct']:.2f}%)")
    
    soc_change = df.iloc[-1]['soc_kwh'] - df.iloc[0]['soc_kwh']
    print(f"    Cambio SOC final-inicial: {soc_change:.1f} kWh")
    
    # Verificar balance energetico
    print("\n[6] BALANCE ENERGETICO (sin considerar eficiencia):")
    net_balance = total_charge - total_discharge
    print(f"    Cargado: {total_charge:,.0f} kWh")
    print(f"    Descargado: {total_discharge:,.0f} kWh")
    print(f"    Balance neto (sin eficiencia): {net_balance:,.0f} kWh")
    print(f"    Balance esperado (SOC final - SOC inicial): {soc_change:.0f} kWh")
    
    if abs(net_balance - soc_change) > 1:
        print(f"    ⚠ ERROR: Balance energetico NO CUADRA")
        print(f"    Diferencia: {abs(net_balance - soc_change):.0f} kWh")
    else:
        print(f"    ✓ Balance energetico correcto")
    
    # Detectar horas problematicas
    print("\n[7] DETECCION DE ANOMALIAS:")
    
    # Horas donde carga Y descarga simultaneamente
    both = (df['power_charge_kw'] > 0) & (df['power_discharge_kw'] > 0)
    if both.sum() > 0:
        print(f"    ⚠ {both.sum()} horas con carga Y descarga simultaneamente (INCORRECTO)")
        print(f"    Primeras 5 anomalias:")
        for idx in df[both].head(5).index:
            row = df.iloc[idx]
            print(f"       {row['timestamp']}: Carga={row['power_charge_kw']:.1f} kW, Descarga={row['power_discharge_kw']:.1f} kW")
    
    # Cambios abruptos de SOC
    soc_changes = df['soc_kwh'].diff()
    max_change = soc_changes.max()
    min_change = soc_changes.min()
    print(f"    SOC cambio max por hora: {max_change:.2f} kWh")
    print(f"    SOC cambio min por hora: {min_change:.2f} kWh")
    
    if max_change > 342 or min_change < -342:
        print(f"    ⚠ Cambios excesivos en SOC (potencia max es 342 kW)")
    
    # Metadata
    if metadata_file.exists():
        print(f"\n[8] METADATA:")
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        print(f"    Energia cargada (metadata): {metadata.get('energy_charged_kwh', 'N/A'):,.0f} kWh")
        print(f"    Energia descargada (metadata): {metadata.get('energy_discharged_kwh', 'N/A'):,.0f} kWh")
    
    print("\n" + "="*80)
    print("RECOMENDACIONES DE CORRECCION:")
    print("="*80)
    
    if total_discharge > total_charge:
        print("⚠ PROBLEMA CRITICO: Se descarga más energia de la que se carga")
        print("   Causa probable: El script original está acumulando incorrectamente")
        print("   Solucion: Reconstruir el dataset desde cero con logica revisada")
    
    return {
        'total_charge': total_charge,
        'total_discharge': total_discharge,
        'soc_change': soc_change,
        'soc_initial': df.iloc[0]['soc_kwh'],
        'soc_final': df.iloc[-1]['soc_kwh'],
        'has_errors': total_discharge > total_charge or both.sum() > 0
    }

if __name__ == '__main__':
    result = diagnose_bess()
