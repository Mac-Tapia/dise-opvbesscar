"""
Script para actualizar balance_energetico y validar límite de generación solar
Genera gráficas mejoradas con validación de capacidad anual (8.29 GWh)
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

# Constantes
SOLAR_ANNUAL_CAPACITY_KWH = 8_292_514.17  # kWh anuales
SOLAR_ANNUAL_CAPACITY_GWH = 8.29  # GWh
REPORT_DATE = datetime.now().isoformat()

def load_bess_data():
    """Load BESS dataset with all columns"""
    csv_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df
    return None

def validate_solar_capacity(df):
    """Validate that solar generation doesn't exceed annual capacity"""
    
    print('\n' + '='*80)
    print('VALIDACIÓN DE CAPACIDAD SOLAR ANUAL')
    print('='*80)
    
    if df is None or len(df) == 0:
        print('❌ No hay datos para validar')
        return {'status': 'error', 'message': 'No data available'}
    
    # PV generation column
    pv_col = 'pv_kwh'
    if pv_col not in df.columns:
        print(f'⚠️  Column {pv_col} not found, trying alternatives...')
        pv_col = next((col for col in df.columns if 'pv' in col.lower()), None)
        if not pv_col:
            return {'status': 'error', 'message': 'No PV column found'}
    
    # Calculate annual generation
    annual_generated = df[pv_col].sum()
    annual_capacity = SOLAR_ANNUAL_CAPACITY_KWH
    
    # Calculate metrics
    utilization_pct = (annual_generated / annual_capacity) * 100 if annual_capacity > 0 else 0
    surplus_deficit = annual_generated - annual_capacity
    
    print(f'\n📊 ESPECIFICACIONES SOLAR:')
    print(f'   Capacidad anual: {annual_capacity:,.0f} kWh = {SOLAR_ANNUAL_CAPACITY_GWH:.2f} GWh')
    print(f'   Generación real: {annual_generated:,.0f} kWh = {annual_generated/1e6:.2f} GWh')
    print(f'   Utilización:    {utilization_pct:.1f}%')
    print(f'   Diferencia:     {surplus_deficit:+,.0f} kWh')
    
    # Status
    status = 'OK' if utilization_pct <= 100 else 'EXCESO'
    status_symbol = '✓' if status == 'OK' else '⚠️ '
    
    print(f'\n{status_symbol} Status: {status}')
    
    if status == 'EXCESO':
        print(f'   ❌ ADVERTENCIA: Generación excede capacidad en {abs(surplus_deficit):,.0f} kWh')
        print(f'   Reduzca despacho o revisar datos de entrada')
    else:
        print(f'   ✓ Generación dentro de límite de capacidad')
    
    # Horly statistics
    print(f'\n⏱️  ESTADÍSTICAS HORARIAS:')
    pv_hourly = df[pv_col].values
    print(f'   Máximo por hora:    {pv_hourly.max():>12,.2f} kW')
    print(f'   Promedio diario:    {annual_generated/365:>12,.2f} kWh/día')
    print(f'   Horas activas:      {(pv_hourly > 0).sum():>12,d} del {len(df)} h')
    
    return {
        'status': status,
        'annual_capacity_kwh': annual_capacity,
        'annual_generated_kwh': annual_generated,
        'utilization_pct': utilization_pct,
        'surplus_deficit_kwh': surplus_deficit,
        'max_hourly_kw': pv_hourly.max(),
        'avg_daily_kwh': annual_generated / 365,
        'hours_active': (pv_hourly > 0).sum(),
        'total_hours': len(df),
        'message': f'Generación: {annual_generated/1e6:.2f} GWh / {SOLAR_ANNUAL_CAPACITY_GWH:.2f} GWh ({utilization_pct:.1f}%)'
    }

def validate_dispatch_vs_capacity(df):
    """Validate that dispatch (soaking) of PV doesn't exceed generation"""
    
    print('\n' + '='*80)
    print('VALIDACIÓN DE DESPACHO VS GENERACIÓN SOLAR')
    print('='*80)
    
    if df is None:
        return None
    
    # PV related columns - ALL possible dispatch paths
    pv_dispatch_cols = {
        'to_ev': ['pv_to_ev_kwh', 'pv_to_ev'],
        'to_bess': ['pv_to_bess_kwh', 'pv_to_bess'],
        'to_mall': ['pv_to_mall_kwh', 'pv_to_mall'],
        'curtailed': ['pv_curtailed_kwh', 'pv_curtailed'],
        'grid_export': ['grid_export_kwh', 'grid_export']  # Also counts as dispatch
    }
    
    # Find columns that exist
    pv_dispatch_actual = {}
    for key, cols in pv_dispatch_cols.items():
        actual_col = next((c for c in cols if c in df.columns), None)
        if actual_col:
            pv_dispatch_actual[key] = actual_col
    
    if not pv_dispatch_actual:
        print('⚠️  No PV dispatch columns found')
        return None
    
    print(f'\n📊 DESPACHO SOLAR - Destinos:')
    dispatch_totals = {}
    for key, col in pv_dispatch_actual.items():
        total = df[col].sum()
        dispatch_totals[key] = total
        print(f'   {key:20s}: {total:>15,.0f} kWh')
    
    # Check if dispatch matches generation
    pv_generation_col = next((c for c in ['pv_kwh', 'pv'] if c in df.columns), 'pv_kwh')
    pv_generation_total = df[pv_generation_col].sum()
    dispatch_sum = sum(dispatch_totals.values())
    balance = pv_generation_total - dispatch_sum
    
    print(f'\n🔄 BALANCE ENERGÉTICO:')
    print(f'   Generación total:  {pv_generation_total:>15,.0f} kWh')
    print(f'   Despacho total:    {dispatch_sum:>15,.0f} kWh')
    print(f'   Balance:           {balance:>15,.0f} kWh')
    
    balance_pct = (dispatch_sum / pv_generation_total * 100) if pv_generation_total > 0 else 0
    print(f'   Balance %:         {balance_pct:>14.1f}%')
    
    # Allow for small rounding errors
    balance_ok = abs(balance) < 10000  # Allow 10 MWh rounding error
    
    if balance_ok:
        if abs(balance) < 1000:
            print(f'\n✓ Balance energético PERFECTO (diferencia < 1 MWh)')
        else:
            print(f'\n✓ Balance energético validado (diferencia: {abs(balance)/1e6:.1f} MWh)')
    else:
        print(f'\n⚠️ Discrepancia significativa detectada: {balance/1e6:.1f} MWh')
    
    return {
        'generation_kwh': pv_generation_total,
        'dispatch_kwh': dispatch_sum,
        'dispatch_details': dispatch_totals,
        'balance_kwh': balance,
        'balance_pct': balance_pct,
        'balance_ok': balance_ok
    }

def create_validation_report(df):
    """Create comprehensive validation report"""
    
    capacity_validation = validate_solar_capacity(df)
    dispatch_validation = validate_dispatch_vs_capacity(df)
    
    # Create report
    report = {
        'timestamp': REPORT_DATE,
        'solar_annual_capacity_kwh': SOLAR_ANNUAL_CAPACITY_KWH,
        'solar_annual_capacity_gwh': SOLAR_ANNUAL_CAPACITY_GWH,
        'capacity_validation': capacity_validation,
        'dispatch_validation': dispatch_validation,
        'dataset_info': {
            'rows': len(df),
            'hours_annual': len(df),
            'columns': len(df.columns),
            'columns_list': list(df.columns)
        }
    }
    
    # Save report
    report_path = Path('outputs/validation_solar_capacity_v57.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f'\n💾 Reporte guardado: {report_path}')
    
    return report

def plot_capacity_comparison(df):
    """Plot actual generation vs annual capacity"""
    
    if df is None or 'pv_kwh' not in df.columns:
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Monthly generation vs capacity
    df_temp = df.copy()
    df_temp['month'] = (np.arange(len(df)) // (24 * 30.4)).astype(int) + 1
    
    monthly_gen = df_temp.groupby('month')['pv_kwh'].sum()
    monthly_capacity = SOLAR_ANNUAL_CAPACITY_KWH / 12
    
    months = sorted(monthly_gen.index)  # Use actual months from data
    ax1.bar(months, monthly_gen.values, color='#FFD700', alpha=0.7, edgecolor='orange', linewidth=2, label='Generación real')
    ax1.axhline(y=monthly_capacity, color='red', linestyle='--', linewidth=2.5, label=f'Capacidad promedio mensual ({monthly_capacity:,.0f} kWh)')
    
    ax1.set_xlabel('Mes', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Energía (kWh)', fontsize=11, fontweight='bold')
    ax1.set_title('Generación Solar Mensual vs Capacidad', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_xticks(months)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1e6)}M'))
    
    # Cumulative generation vs capacity curve
    cumulative_gen = df['pv_kwh'].cumsum()
    linear_capacity = np.linspace(0, SOLAR_ANNUAL_CAPACITY_KWH, len(df))
    hours = np.arange(len(df))
    
    ax2.plot(hours, cumulative_gen.values, color='#FFD700', linewidth=2.5, label='Generación acumulada real', marker='.', markersize=1)
    ax2.plot(hours, linear_capacity, color='red', linestyle='--', linewidth=2.5, label=f'Línea de capacidad ({SOLAR_ANNUAL_CAPACITY_GWH:.2f} GWh/año)')
    
    # Fill between if exceeded
    diff = cumulative_gen.values - linear_capacity
    if (diff > 0).any():
        ax2.fill_between(hours[diff > 0], 0, cumulative_gen.values[diff > 0], color='red', alpha=0.2, label='Exceso (si existe)')
    else:
        ax2.fill_between(hours, cumulative_gen.values, linear_capacity, color='green', alpha=0.1, label='Capacidad disponible')
    
    ax2.set_xlabel('Hora del año', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Energía acumulada (kWh)', fontsize=11, fontweight='bold')
    ax2.set_title('Curva Acumulada: Generación vs Capacidad Anual', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x/1e6)}M'))
    
    plt.tight_layout()
    
    # Save figure
    output_path = Path('reports/balance_energetico/99_CAPACIDAD_SOLAR_VALIDACION.png')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'\n✓ Gráfica guardada: {output_path}')

def main():
    print('\n' + '#'*80)
    print('# VALIDACIÓN DE BALANCE ENERGÉTICO Y CAPACIDAD SOLAR v5.7')
    print('#'*80)
    
    # Load data
    print('\n📂 Cargando datos...')
    df = load_bess_data()
    
    if df is None:
        print('❌ No se pudo cargar el dataset')
        return False
    
    print(f'✓ Dataset cargado: {len(df)} filas × {len(df.columns)} columnas')
    
    # Validate capacity
    print('\n📋 Ejecutando validaciones...')
    report = create_validation_report(df)
    
    # Create visualization
    print('\n🎨 Generando gráficas...')
    plot_capacity_comparison(df)
    
    # Summary
    print('\n' + '='*80)
    print('✅ VALIDACIÓN COMPLETADA')
    print('='*80)
    print(f'\n📊 Capacidad solar anual: {SOLAR_ANNUAL_CAPACITY_KWH:,.0f} kWh ({SOLAR_ANNUAL_CAPACITY_GWH:.2f} GWh)')
    if report['capacity_validation']['status'] == 'OK':
        print(f'✓ Generación dentro de límite: {report["capacity_validation"]["annual_generated_kwh"]:,.0f} kWh ({report["capacity_validation"]["utilization_pct"]:.1f}%)')
    else:
        print(f'⚠️ ADVERTENCIA: Generación excede capacidad')
    
    return True

if __name__ == '__main__':
    main()
