#!/usr/bin/env python3
"""
VERIFICACION Y GENERACION DE DATOS BESS
========================================

Verifica que todos los datos necesarios para OE3 training estén generados.
Si falta el perfil BESS horario, lo genera automáticamente.

Genera:
- bess_operation_profile.csv (8,760 horas/año)
- bess_config.json (configuración BESS)
- bess_schema.json (schema para CityLearn)
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

def verify_and_generate_bess_data():
    """Verifica datos OE2 y genera BESS profile si falta."""

    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║        VERIFICACION Y GENERACION DE DATOS BESS PARA OE3                   ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    # Directorios
    oe2_dir = Path("data/interim/oe2")
    bess_dir = oe2_dir / "bess"
    solar_dir = oe2_dir / "solar"
    chargers_dir = oe2_dir / "chargers"

    bess_dir.mkdir(parents=True, exist_ok=True)

    # Archivos esperados
    print("\n[1] VERIFICACION DE ARCHIVOS")
    print("=" * 80)

    files_status = {}

    # Solar
    solar_file = solar_dir / "pv_generation_timeseries.csv"
    files_status['Solar'] = {
        'path': solar_file,
        'exists': solar_file.exists(),
        'required': True
    }
    print(f"  {'✓' if solar_file.exists() else '✗'} Solar: {solar_file}")
    if solar_file.exists():
        df_solar = pd.read_csv(solar_file)
        print(f"      Filas: {len(df_solar)}, Columnas: {list(df_solar.columns)}")

    # Chargers
    chargers_file = chargers_dir / "individual_chargers.json"
    files_status['Chargers'] = {
        'path': chargers_file,
        'exists': chargers_file.exists(),
        'required': True
    }
    print(f"  {'✓' if chargers_file.exists() else '✗'} Chargers: {chargers_file}")
    if chargers_file.exists():
        with open(chargers_file) as f:
            chargers = json.load(f)
        print(f"      Items: {len(chargers)}")

    # BESS Config
    bess_config_file = bess_dir / "bess_config.json"
    files_status['BESS Config'] = {
        'path': bess_config_file,
        'exists': bess_config_file.exists(),
        'required': True
    }
    print(f"  {'✓' if bess_config_file.exists() else '✗'} BESS Config: {bess_config_file}")
    if bess_config_file.exists():
        with open(bess_config_file) as f:
            bess_config = json.load(f)
        print(f"      Capacity: {bess_config.get('capacity_kwh')} kWh")
        print(f"      Power: {bess_config.get('power_kw')} kW")

    # BESS Profile (hourly operation)
    bess_profile_file = bess_dir / "bess_operation_profile.csv"
    files_status['BESS Profile'] = {
        'path': bess_profile_file,
        'exists': bess_profile_file.exists(),
        'required': False
    }
    print(f"  {'✓' if bess_profile_file.exists() else '✗'} BESS Profile: {bess_profile_file}")
    if bess_profile_file.exists():
        df_profile = pd.read_csv(bess_profile_file)
        print(f"      Filas: {len(df_profile)}, Columnas: {list(df_profile.columns)}")

    # Check all required files
    print("\n[2] ESTADO GENERAL")
    print("=" * 80)
    required_exist = all(
        fs['exists'] for fs in files_status.values()
        if fs['required']
    )

    if required_exist:
        print("✓ Todos los archivos requeridos existen")
    else:
        print("✗ Faltan archivos requeridos:")
        for name, fs in files_status.items():
            if fs['required'] and not fs['exists']:
                print(f"   - {name}: {fs['path']}")
        return False

    # Generate BESS profile if missing
    print("\n[3] GENERACION DE PERFIL BESS HORARIO")
    print("=" * 80)

    if not bess_profile_file.exists():
        print(f"\n⚠ BESS profile no existe. Generando...")

        # Load solar data to understand generation pattern
        df_solar = pd.read_csv(solar_file)

        # Crear perfil de operación BESS (8,760 horas)
        hours = np.arange(8760)

        # Parámetros BESS del config
        if bess_config_file.exists():
            with open(bess_config_file) as f:
                bess_cfg = json.load(f)
        else:
            bess_cfg = {
                'capacity_kwh': 2000,
                'power_kw': 1200,
                'efficiency': 0.92,
                'min_soc': 0.1,
                'max_soc': 1.0
            }

        capacity = bess_cfg.get('capacity_kwh', 2000)
        power = bess_cfg.get('power_kw', 1200)
        efficiency = bess_cfg.get('efficiency', 0.92)
        min_soc = bess_cfg.get('min_soc', 0.1)
        max_soc = bess_cfg.get('max_soc', 1.0)

        # Simulación de SOC basada en patrón solar
        soc_array = np.zeros(8760)
        soc_array[0] = 0.5  # SOC inicial 50%

        # Solar pattern: higher at midday, low at night
        # Estimado: horas 6-18 tienen solar, 19-5 sin solar
        hour_of_day = hours % 24

        # Carga durante el día cuando hay solar (9-17)
        # Descarga durante la noche (19-7)
        for h in range(1, 8760):
            current_hour = h % 24
            prev_soc = soc_array[h-1]

            if 9 <= current_hour <= 17:
                # Cargar desde solar (pequeños incrementos)
                delta_soc = 0.01  # 1% por hora
            elif 19 <= current_hour or current_hour <= 7:
                # Descargar para EV nocturno (2% por hora)
                delta_soc = -0.02
            else:
                # Transición (pequeño cambio)
                delta_soc = -0.005

            new_soc = prev_soc + delta_soc
            new_soc = np.clip(new_soc, min_soc, max_soc)
            soc_array[h] = new_soc

        # Generar variables derivadas
        charge_power = np.zeros(8760)
        discharge_power = np.zeros(8760)

        for h in range(1, 8760):
            delta_soc = soc_array[h] - soc_array[h-1]

            if delta_soc > 0:
                # Cargando
                charge_power[h] = delta_soc * capacity
                discharge_power[h] = 0
            else:
                # Descargando
                discharge_power[h] = -delta_soc * capacity
                charge_power[h] = 0

        # Crear DataFrame
        df_bess = pd.DataFrame({
            'hour': hours,
            'hour_of_day': hour_of_day,
            'soc_percent': soc_array * 100,
            'soc_kwh': soc_array * capacity,
            'charge_power_kw': charge_power,
            'discharge_power_kw': discharge_power,
            'charge_energy_kwh': charge_power,  # 1 hora = 1 kWh por kW
            'discharge_energy_kwh': discharge_power,
        })

        # Guardar
        df_bess.to_csv(bess_profile_file, index=False)
        print(f"✓ BESS profile generado: {bess_profile_file}")
        print(f"  Filas: {len(df_bess)}, Columnas: {list(df_bess.columns)}")
        print(f"  SOC medio: {soc_array.mean()*100:.1f}%")
        print(f"  Carga total: {charge_power.sum():.1f} kWh/año")
        print(f"  Descarga total: {discharge_power.sum():.1f} kWh/año")
    else:
        print(f"✓ BESS profile ya existe: {bess_profile_file}")
        df_bess = pd.read_csv(bess_profile_file)
        print(f"  Verificado: {len(df_bess)} filas")

    # Generate/verify BESS config JSON
    print("\n[4] CONFIGURACION BESS JSON")
    print("=" * 80)

    if not bess_config_file.exists():
        print(f"⚠ BESS config no existe. Creando...")

        bess_config = {
            "system_name": "Eaton Xpert 1670 - Iquitos BESS",
            "capacity_kwh": 2000.0,
            "power_kw": 1200.0,
            "efficiency": 0.92,
            "min_soc": 0.1,
            "max_soc": 1.0,
            "depth_of_discharge": 0.9,
            "roundtrip_efficiency": 0.92,
            "response_time_s": 0.5,
            "degradation_rate_yearly": 0.01,
            "round_trip_efficiency_percent": 92.0,
            "battery_chemistry": "Lithium-ion",
            "warranty_years": 10,
            "cycle_life": 4500
        }

        with open(bess_config_file, 'w') as f:
            json.dump(bess_config, f, indent=2)

        print(f"✓ BESS config creado: {bess_config_file}")
    else:
        print(f"✓ BESS config ya existe: {bess_config_file}")
        with open(bess_config_file) as f:
            bess_config = json.load(f)

    print(f"  Capacity: {bess_config['capacity_kwh']} kWh")
    print(f"  Power: {bess_config['power_kw']} kW")
    print(f"  Efficiency: {bess_config['efficiency']*100:.0f}%")

    # Generate BESS schema JSON for CityLearn
    print("\n[5] SCHEMA BESS PARA CITYLEARN")
    print("=" * 80)

    bess_schema_file = bess_dir / "bess_schema.json"

    bess_schema = {
        "building_name": "EV_Charging_Mall_Iquitos",
        "electrical_storage": {
            "type": "Battery",
            "capacity_kwh": float(bess_config['capacity_kwh']),
            "power_kw": float(bess_config['power_kw']),
            "efficiency_round_trip": float(bess_config['roundtrip_efficiency']),
            "initial_soc_percent": 50.0,
            "minimum_soc_percent": float(bess_config['min_soc'] * 100),
            "maximum_soc_percent": float(bess_config['max_soc'] * 100),
            "depth_of_discharge": float(bess_config['depth_of_discharge']),
            "response_time_seconds": float(bess_config['response_time_s']),
            "characteristics": {
                "chemistry": bess_config['battery_chemistry'],
                "warranty_years": int(bess_config['warranty_years']),
                "cycle_life": int(bess_config['cycle_life']),
                "annual_degradation": float(bess_config['degradation_rate_yearly'])
            }
        },
        "photovoltaic": {
            "type": "Rooftop",
            "capacity_kw": 4050,
            "inverter_efficiency": 0.97,
            "soiling_loss_percent": 2.0,
            "temperature_coefficient": -0.004
        },
        "control": {
            "dispatch_mode": "optimization",
            "objective": "minimize_co2",
            "weights": {
                "co2": 0.50,
                "solar_utilization": 0.20,
                "cost": 0.15,
                "ev_satisfaction": 0.10,
                "grid_stability": 0.05
            }
        },
        "data_paths": {
            "bess_profile": str(bess_profile_file.resolve()),
            "solar_generation": str(solar_file.resolve()),
            "chargers_config": str(chargers_file.resolve())
        }
    }

    with open(bess_schema_file, 'w') as f:
        json.dump(bess_schema, f, indent=2)

    print(f"✓ BESS schema creado: {bess_schema_file}")

    # Resumen
    print("\n[6] RESUMEN FINAL")
    print("=" * 80)

    print("\n✓ ARCHIVOS GENERADOS/VERIFICADOS:")
    print(f"  ✓ Solar: {solar_file} ({len(df_solar)} rows)")
    print(f"  ✓ Chargers: {chargers_file} ({len(chargers)} items)")
    print(f"  ✓ BESS Profile: {bess_profile_file} ({len(df_bess)} rows)")
    print(f"  ✓ BESS Config: {bess_config_file}")
    print(f"  ✓ BESS Schema: {bess_schema_file}")

    print("\n✓ RESUMEN DE DATOS BESS:")
    print(f"  Capacity: {bess_config['capacity_kwh']:.0f} kWh")
    print(f"  Power: {bess_config['power_kw']:.0f} kW")
    print(f"  Eficiencia round-trip: {bess_config['roundtrip_efficiency']*100:.0f}%")
    print(f"  SOC medio: {df_bess['soc_percent'].mean():.1f}%")
    print(f"  SOC min/max: {df_bess['soc_percent'].min():.1f}% / {df_bess['soc_percent'].max():.1f}%")
    print(f"  Carga total anual: {df_bess['charge_energy_kwh'].sum():.0f} kWh")
    print(f"  Descarga total anual: {df_bess['discharge_energy_kwh'].sum():.0f} kWh")

    # Ciclos diarios
    if bess_config['capacity_kwh'] > 0:
        cycles_per_day = df_bess['charge_energy_kwh'].sum() / bess_config['capacity_kwh'] / 365
        print(f"  Ciclos/día: {cycles_per_day:.2f}")

    print("\n✓ SISTEMA OE2 COMPLETO Y LISTO PARA OE3 TRAINING")
    print("=" * 80)

    return True

if __name__ == "__main__":
    success = verify_and_generate_bess_data()

    if not success:
        print("\n❌ Error durante verificación/generación")
        exit(1)
    else:
        print("\n✅ Verificación completada exitosamente\n")
        exit(0)
