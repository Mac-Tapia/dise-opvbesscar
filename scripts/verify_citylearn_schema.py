#!/usr/bin/env python3
"""
Verifica que el dataset CityLearn esté completo y listo para OE3.
"""
import json
from pathlib import Path
import pandas as pd


def verify_schema(dataset_dir: Path) -> bool:
    """Verifica el schema de CityLearn."""
    print("=" * 60)
    print("  VERIFICACIÓN DE DATASET CITYLEARN PARA OE3")
    print("=" * 60)
    
    all_ok = True
    
    # 1. Verificar que existen los schemas
    schemas = ['schema.json', 'schema_pv_bess.json', 'schema_grid_only.json']
    print("\n1. SCHEMAS:")
    for s in schemas:
        path = dataset_dir / s
        exists = path.exists()
        icon = '✓' if exists else '✗'
        print(f"   {icon} {s}")
        if not exists:
            all_ok = False
    
    # 2. Verificar archivos CSV principales
    print("\n2. ARCHIVOS CSV REQUERIDOS:")
    csvs = ['Building_1.csv', 'carbon_intensity.csv', 'pricing.csv', 'weather.csv']
    for c in csvs:
        path = dataset_dir / c
        exists = path.exists()
        icon = '✓' if exists else '✗'
        if exists:
            df = pd.read_csv(path)
            print(f"   {icon} {c} ({len(df)} filas)")
        else:
            print(f"   {icon} {c}")
            all_ok = False
    
    # 3. Cargar y verificar schema principal
    print("\n3. CONFIGURACIÓN PRINCIPAL:")
    schema = json.loads((dataset_dir / 'schema.json').read_text())
    print(f"   central_agent: {schema.get('central_agent')}")
    print(f"   seconds_per_time_step: {schema.get('seconds_per_time_step')}")
    print(f"   simulation_end_time_step: {schema.get('simulation_end_time_step')}")
    
    # 4. Verificar building
    buildings = schema.get('buildings', {})
    print(f"\n4. BUILDINGS: {len(buildings)} definido(s)")
    for bname, b in buildings.items():
        print(f"   Building: {bname}")
        
        # Energy simulation file
        energy_file = b.get('energy_simulation')
        if energy_file:
            ef_path = dataset_dir / energy_file
            if ef_path.exists():
                df_e = pd.read_csv(ef_path)
                print(f"      ✓ energy_simulation: {energy_file} ({len(df_e)} filas)")
            else:
                print(f"      ✗ energy_simulation: {energy_file} NO ENCONTRADO")
                all_ok = False
        
        # PV
        pv = b.get('pv', {})
        pv_power = pv.get('attributes', {}).get('nominal_power', 'N/A')
        print(f"      PV nominal_power: {pv_power} kW")
        
        # BESS
        bess = b.get('electrical_storage', {})
        bess_cap = bess.get('capacity', 'N/A')
        bess_pow = bess.get('nominal_power', 'N/A')
        print(f"      BESS capacity: {bess_cap} kWh")
        print(f"      BESS nominal_power: {bess_pow} kW")
        
        # Chargers
        chargers = b.get('chargers', {})
        print(f"      Chargers: {len(chargers)}")
        for cname, charger in chargers.items():
            charger_file = charger.get('charger_simulation')
            if charger_file:
                cf_path = dataset_dir / charger_file
                exists = cf_path.exists()
                icon = '✓' if exists else '✗'
                print(f"         {icon} {cname}: {charger_file}")
                if not exists:
                    all_ok = False
    
    # 5. Verificar EVs
    evs = schema.get('electric_vehicles_def', {})
    print(f"\n5. VEHÍCULOS ELÉCTRICOS: {len(evs)} definido(s)")
    for ev_name, ev in evs.items():
        battery = ev.get('battery', {}).get('attributes', {})
        cap = battery.get('capacity', 'N/A')
        print(f"   {ev_name}: {cap} kWh")
    
    # 6. Verificar variantes de schema
    print("\n6. COMPARACIÓN DE SCHEMAS:")
    schema_pv_bess = json.loads((dataset_dir / 'schema_pv_bess.json').read_text())
    schema_grid = json.loads((dataset_dir / 'schema_grid_only.json').read_text())
    
    # Extraer valores de PV y BESS
    def get_pv_bess(s):
        b = list(s.get('buildings', {}).values())[0]
        pv = b.get('pv', {}).get('attributes', {}).get('nominal_power', 0)
        bess_cap = b.get('electrical_storage', {}).get('capacity', 0)
        bess_pow = b.get('electrical_storage', {}).get('nominal_power', 0)
        return pv, bess_cap, bess_pow
    
    pv1, cap1, pow1 = get_pv_bess(schema_pv_bess)
    pv2, cap2, pow2 = get_pv_bess(schema_grid)
    
    print(f"   schema_pv_bess.json:")
    print(f"      PV: {pv1} kW, BESS: {cap1} kWh / {pow1} kW")
    print(f"   schema_grid_only.json:")
    print(f"      PV: {pv2} kW, BESS: {cap2} kWh / {pow2} kW")
    
    if pv2 == 0 and cap2 == 0:
        print("   ✓ Grid-only schema correctamente configurado (PV=0, BESS=0)")
    else:
        print("   ⚠ Grid-only schema debería tener PV=0 y BESS=0")
    
    # 7. Intentar cargar CityLearn
    print("\n7. PRUEBA DE CARGA EN CITYLEARN:")
    try:
        from citylearn.citylearn import CityLearnEnv
        env = CityLearnEnv(schema=str(dataset_dir / 'schema.json'))
        print(f"   ✓ CityLearnEnv cargado correctamente")
        print(f"   ✓ Observation space: {env.observation_space}")
        print(f"   ✓ Action space: {env.action_space}")
        env.close()
    except Exception as e:
        print(f"   ✗ Error al cargar CityLearnEnv: {e}")
        all_ok = False
    
    # Resumen
    print("\n" + "=" * 60)
    if all_ok:
        print("  ✅ DATASET LISTO PARA EJECUTAR OE3")
    else:
        print("  ❌ HAY PROBLEMAS EN EL DATASET")
    print("=" * 60)
    
    return all_ok


if __name__ == "__main__":
    dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    verify_schema(dataset_dir)
