"""
PUNTO DE ENTRADA: Regenerar TODAS las gráficas de balance energético v5.7
═══════════════════════════════════════════════════════════════════════════

RESPONSABILIDAD:
  Este script ACTÚA COMO WRAPPER que:
  1. Carga dataset desde data/oe2/bess/bess_ano_2024.csv
  2. Normaliza columnas (mapeos automáticos)
  3. DELEGA generación de gráficas AL MÓDULO balance.py

  ⭐ TODA la lógica de gráficas está en:
     src/dimensionamiento/oe2/balance_energetico/balance.py
     Clase: BalanceEnergeticoSystem.plot_energy_balance()

  ✗ Este script NO genera gráficas directamente
  ✓ Este script usa balance.py para generar las 16 gráficas

FLUJO:
  regenerate_graphics_v57.py (wrapper)
    ↓
  carga dataset desde data/oe2/bess/bess_ano_2024.csv
    ↓
  normaliza columnas (19 mappings + 5 derived)
    ↓
  BalanceEnergeticoSystem(df, config) ← en balance.py
    ↓
  .plot_energy_balance(output_dir) ← GENERA las 16 gráficas
    ↓
  saved to: src/dimensionamiento/oe2/balance_energetico/outputs_demo/

VALIDACIÓN INCLUIDA:
- Capacidad solar anual (8.29 GWh)
- Validación de despacho vs generación
- Gráficas con límite de capacidad
- Información completa HP/HFP tarifaria

USO:
  python scripts/regenerate_graphics_v57.py
"""

import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem, BalanceEnergeticoConfig

def regenerate_graphics():
    """Regenerar TODAS las gráficas de balance energético
    
    NOTA: Este proceso usa BalanceEnergeticoSystem (balance.py) que es
          el ÚNICO responsable de generar las 16 gráficas.
          
    FLUJO:
      1. Carga dataset (data/oe2/bess/bess_ano_2024.csv)
      2. Normaliza columnas (balance.py espera ciertos nombres)
      3. DELEGA a balance.py: BalanceEnergeticoSystem.plot_energy_balance()
      4. balance.py genera TODAS las 16 gráficas
      5. Salva en outputs_demo/
    """
    
    print('\n' + '#'*80)
    print('# REGENERACIÓN DE GRÁFICAS DE BALANCE ENERGÉTICO v5.7')
    print('#'*80)
    
    # Load dataset - USING ORIGINAL CORRECT SOURCE
    print('\n📂 Cargando dataset...')
    csv_path = Path('data/oe2/bess/bess_ano_2024.csv')
    
    if not csv_path.exists():
        print(f'❌ No se encontró: {csv_path}')
        print(f'   Dataset original requerido')
        return False
    
    df = pd.read_csv(csv_path)
    print(f'✓ Dataset cargado: {len(df)} filas × {len(df.columns)} columnas')
    
    # ADAPTADOR NORMALIZACIÓN: Mapeo automático inteligente
    print('\n🔄 Normalizando columnas del dataset original...')
    
    # Estrategia: mapeo exhaustivo + derivados inteligentes
    mapping = {
        # Energía solar
        'pv_kwh': 'pv_generation_kw',
        # Demandas
        'ev_kwh': 'ev_demand_kw',
        'mall_kwh': 'mall_demand_kw',
        'load_kwh': 'load_kw',
        # BESS - Energía (kWh) -> También crear como kW
        'bess_energy_stored_hourly_kwh': ['bess_charge_kwh', 'bess_charge_kw'],
        'bess_energy_delivered_hourly_kwh': ['bess_discharge_kwh', 'bess_discharge_kw'],
        'bess_action_kwh': 'bess_action_kw',
        # BESS - Flujos
        'bess_to_ev_kwh': 'bess_to_ev_kw',
        'bess_to_mall_kwh': 'bess_to_mall_kw',
        # Grid
        'grid_import_kwh': 'grid_import_kw',
        'grid_export_kwh': 'grid_export_kw',
        'grid_import_ev_kwh': 'grid_import_ev_kw',
        'grid_import_mall_kwh': 'grid_import_mall_kw',
        'mall_grid_import_kwh': 'demand_from_grid_kw',
        # PV a cargas
        'pv_to_ev_kwh': 'pv_to_ev_kw',
        'pv_to_bess_kwh': 'pv_to_bess_kw',
        'pv_to_mall_kwh': 'pv_to_mall_kw',
        # SOC 
        'soc_percent': 'soc_percent',
        'soc_kwh': 'soc_kwh',
    }
    
    for src, dst in mapping.items():
        if src in df.columns:
            # Si dst es lista, mapear a todas las columnas en la lista
            if isinstance(dst, list):
                for d in dst:
                    if d not in df.columns:
                        df[d] = df[src]
                        print(f'  ✓ {src} → {d}')
            else:
                if dst not in df.columns:
                    df[dst] = df[src]
                    print(f'  ✓ {src} → {dst}')
    
    # POST-PROCESAR: Asegurar columnas críticas existan
    required_cols = ['pv_generation_kw', 'ev_demand_kw', 'mall_demand_kw', 
                     'bess_charge_kw', 'bess_discharge_kw', 'demand_from_grid_kw',
                     'soc_percent', 'total_demand_kw']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f'\n⚠️  Columnas derivadas faltantes (creando automáticamente):')
        # Crear grid_import si no existe: sum(grid_import_ev + grid_import_mall)
        if 'demand_from_grid_kw' not in df.columns and 'grid_import_kwh' in df.columns:
            df['demand_from_grid_kw'] = df['grid_import_kwh']
            print(f'  ✓ demand_from_grid_kw := grid_import_kwh')
        # Total demand = EV + MALL
        if 'total_demand_kw' not in df.columns:
            if 'ev_demand_kw' in df.columns and 'mall_demand_kw' in df.columns:
                df['total_demand_kw'] = df['ev_demand_kw'] + df['mall_demand_kw']
                print(f'  ✓ total_demand_kw := ev_demand_kw + mall_demand_kw')
        # BESS SOC aliases
        if 'bess_soc_percent' not in df.columns and 'soc_percent' in df.columns:
            df['bess_soc_percent'] = df['soc_percent']
            print(f'  ✓ bess_soc_percent := soc_percent')
        # PV a demanda (directo)
        if 'pv_to_demand_kw' not in df.columns:
            if 'pv_to_ev_kw' in df.columns and 'pv_to_mall_kw' in df.columns:
                df['pv_to_demand_kw'] = df['pv_to_ev_kw'] + df['pv_to_mall_kw']
                print(f'  ✓ pv_to_demand_kw := pv_to_ev_kw + pv_to_mall_kw')
        # PV a grid (exportación)
        if 'pv_to_grid_kw' not in df.columns and 'grid_export_kw' in df.columns:
            df['pv_to_grid_kw'] = df['grid_export_kw']
            print(f'  ✓ pv_to_grid_kw := grid_export_kw')
        # CO2 desde grid (grid_import * 0.4521 kg CO2/kWh)
        if 'co2_from_grid_kg' not in df.columns and 'grid_import_kw' in df.columns:
            df['co2_from_grid_kg'] = df['grid_import_kw'] * 0.4521
            print(f'  ✓ co2_from_grid_kg := grid_import_kw × 0.4521')
    
    print(f'  Dataset normalizado: {len(df.columns)} columnas disponibles')
    
    # Create config with updated solar capacity
    print('\n⚙️  Configurando sistema...')
    config = BalanceEnergeticoConfig(
        pv_capacity_kwp=4050.0,
        pv_annual_capacity_kwh=8_292_514.17,  # Capacidad real de solar_pvlib
        bess_capacity_kwh=2000.0,  # FIXED v5.8: Cambié de 1700 a 2000
        bess_power_kw=400.0,
        tariff_hp_soles_kwh=0.45,
        tariff_hfp_soles_kwh=0.28
    )
    
    # Initialize graphics system
    print('\n🎨 Inicializando generador de gráficas...')
    print('   ↓ Usando: BalanceEnergeticoSystem (balance.py)')
    graphics = BalanceEnergeticoSystem(df, config)
    
    # Generate graphics - DELEGAR A balance.py
    print('\n📊 Generando TODAS las gráficas via balance.py...')
    print('   ► balance.py::BalanceEnergeticoSystem.plot_energy_balance()')
    print('   ► Esto genera 16 PNG files...')
    output_dir = Path(__file__).parent.parent / 'src/dimensionamiento/oe2/balance_energetico/outputs_demo'
    output_dir.mkdir(parents=True, exist_ok=True)
    graphics.plot_energy_balance(output_dir)
    
    print('\n' + '='*80)
    print('✅ REGENERACIÓN COMPLETADA')
    print('='*80)
    print(f'\n📂 Gráficas guardadas en: {output_dir}')
    print(f'   Total archivos: {len(list(output_dir.glob("*.png")))} imágenes PNG')
    
    # List generated files
    print('\n📋 Archivos generados:')
    for png_file in sorted(output_dir.glob('*.png')):
        file_size_mb = png_file.stat().st_size / 1024 / 1024
        print(f'   ✓ {png_file.name} ({file_size_mb:.1f} MB)')
    
    return True

if __name__ == '__main__':
    success = regenerate_graphics()
    exit(0 if success else 1)
