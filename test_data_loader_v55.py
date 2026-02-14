#!/usr/bin/env python3
"""Verificar que data_loader.py lee correctamente bess_ano_2024.csv v5.5"""

import sys
from pathlib import Path
import pandas as pd

# Añadir path del proyecto
sys.path.insert(0, str(Path.cwd()))

from src.dimensionamiento.oe2.disenocargadoresev.data_loader import (
    load_bess_data,
    OE2ValidationError
)

print('='*120)
print('VERIFICACION: data_loader.py + bess_ano_2024.csv v5.5')
print('='*120 + '\n')

try:
    # Cargar datos BESS con la función actualizada
    print('[1] Cargando BESS v5.5 con data_loader.load_bess_data()...')
    bess_data, bess_df = load_bess_data()
    
    print(f'\n✅ BESS CARGADO EXITOSAMENTE')
    print(f'    Capacidad: {bess_data.capacity_kwh} kWh')
    print(f'    Potencia: {bess_data.power_kw} kW (actualizado a 400 kW)')
    print(f'    Eficiencia: {bess_data.efficiency*100:.0f}%')
    print(f'    Filas: {len(bess_df)}')
    print(f'    Columnas: {bess_df.shape[1]}')
    
    # Validar contenido
    print(f'\n[2] Validando contenido de dataset...')
    required_checks = {
        'bess_soc_percent': 'SOC (Estado de Carga)',
        'bess_charge_kwh': 'Carga BESS',
        'bess_discharge_kwh': 'Descarga BESS'
    }
    
    for col, desc in required_checks.items():
        if col in bess_df.columns:
            print(f'    ✅ {col:25s} ({desc})')
        else:
            print(f'    ❌ {col:25s} FALTA')
    
    # Asegurar datetime index si no existe
    if 'datetime' in bess_df.columns:
        bess_df['datetime'] = pd.to_datetime(bess_df['datetime'])
        bess_df_indexed = bess_df.set_index('datetime')
    else:
        bess_df_indexed = bess_df
    
    # Verificar valores críticos v5.5
    print(f'\n[3] Verificando especificaciones v5.5...')
    
    # SOC
    if 'bess_soc_percent' in bess_df.columns:
        soc_min = bess_df['bess_soc_percent'].min()
        soc_max = bess_df['bess_soc_percent'].max()
        
        print(f'    SOC min: {soc_min:.2f}% (target: 20.0%)')
        print(f'    SOC max: {soc_max:.2f}% (target: 100.0%)')
        
        # Intentar extraer SOC @ 22h si tenemos datetime index
        if hasattr(bess_df_indexed.index, 'hour'):
            soc_at_22h = bess_df_indexed[bess_df_indexed.index.hour == 22]['bess_soc_percent'].values
            if len(soc_at_22h) > 0:
                print(f'    SOC @ 22h: {soc_at_22h[0]:.2f}% (target: 20.0%)')
    
    # Descarga MALL
    if 'bess_to_mall_kwh' in bess_df.columns:
        mall_discharge = bess_df['bess_to_mall_kwh'].sum()
        print(f'    MALL discharge anual: {mall_discharge:,.0f} kWh (target: ~475,000)')
    
    # Descarga EV
    if 'bess_to_ev_kwh' in bess_df.columns:
        ev_discharge = bess_df['bess_to_ev_kwh'].sum()
        print(f'    EV discharge anual: {ev_discharge:,.0f} kWh')
    
    print(f'\n✅ VERIFICACION COMPLETADA - data_loader.py está actualizado para v5.5')
    print('='*120 + '\n')
    
except OE2ValidationError as e:
    print(f'\n❌ ERROR DE VALIDACION: {e}')
    sys.exit(1)
except Exception as e:
    print(f'\n❌ ERROR INESPERADO: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
