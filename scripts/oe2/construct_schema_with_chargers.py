#!/usr/bin/env python3
"""
CONSTRUCCION DE ESQUEMA CITYLEARN CON 128 CHARGERS
Integra los cargadores dimensionados en el esquema CityLearn
con observables y control por playa.

Ejecucion: python construct_schema_with_chargers.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "=" * 100)
print("CONSTRUCCION DE ESQUEMA CITYLEARN CON 128 CHARGERS")
print("=" * 100)
print(f"Fecha: {datetime.now().isoformat()}\n")

# CARGAR CONFIG Y CHARGERS
print("[1/3] Cargar configuracion y chargers...")
try:
    from scripts._common import load_all
    cfg, rp = load_all("configs/default.yaml")

    # Cargar chargers individuales (array de 128 chargers)
    chargers_file = rp.interim_dir / "oe2" / "chargers" / "individual_chargers.json"
    with open(chargers_file) as f:
        chargers = json.load(f)

    # Cargar metadata de resultados
    results_file = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"
    with open(results_file) as f:
        chargers_data = json.load(f)
    # Desglose
    motos_chargers = [c for c in chargers if c.get("playa") == "Playa_Motos"]
    mototaxis_chargers = [c for c in chargers if c.get("playa") == "Playa_Mototaxis"]
    total_sockets = len(chargers)
    n_chargers = len(chargers)

    print(f"OK: Config y {n_chargers} chargers cargados")
    print(f"  • Playa Motos: {len(motos_chargers)} chargers, {sum(c.get('sockets', 0) for c in motos_chargers)} sockets")
    print(f"  • Playa Mototaxis: {len(mototaxis_chargers)} chargers, {sum(c.get('sockets', 0) for c in mototaxis_chargers)} sockets")
    print(f"  • Total sockets: {total_sockets}\n")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# CARGAR SCHEMA BASE
print("[2/3] Cargar schema base de CityLearn...")
try:
    dataset_dir = rp.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"]
    dataset_dir.mkdir(parents=True, exist_ok=True)

    schema_base = rp.raw_dir / "citylearn_templates" / "schema.json"

    with open(schema_base) as f:
        schema = json.load(f)

    print(f"OK: Schema base cargado")
    print(f"  • Path: {schema_base}")
    print(f"  • Edificios: {len(schema.get('buildings', []))}\n")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# ENRIQUECER SCHEMA CON OBSERVABLES DE CHARGERS
print("[3/3] Enriquecer schema con 128 chargers...")
try:
    # Anadir observables para chargers en cada edificio
    schema["observations"]["ev_charging_power_total_kw"] = {
        "active": True,
        "shared_in_central_agent": True
    }
    schema["observations"]["ev_charging_power_playa_motos_kw"] = {
        "active": True,
        "shared_in_central_agent": True
    }
    schema["observations"]["ev_charging_power_playa_mototaxis_kw"] = {
        "active": True,
        "shared_in_central_agent": True
    }

    # Anadir para cada charger individual
    for charger in chargers:
        charger_id = charger.get("charger_id", "unknown")
        obs_name = f"charger_{charger_id}_power_kw"
        schema["observations"][obs_name] = {
            "active": True,
            "shared_in_central_agent": False
        }

    print(f"OK: Schema enriquecido")
    print(f"  • Nuevos observables agregados: 3 (totales) + {len(chargers)} (individuales)")
    print(f"  • Total observables: {len(schema.get('observations', {}))}\n")

    # GUARDAR SCHEMA ENRIQUECIDO
    output_schema = dataset_dir / "schema_with_128_chargers.json"
    with open(output_schema, 'w') as f:
        json.dump(schema, f, indent=2)

    print(f"✓ Schema guardado en: {output_schema}\n")

    charger_metadata = {
        "version": "1.0",
        "date_created": datetime.now().isoformat(),
        "total_chargers": len(chargers),
        "total_sockets": total_sockets,
        "playas": {
            "Playa_Motos": {
                "chargers": len(motos_chargers),
                "sockets": sum(c.get("sockets", 0) for c in motos_chargers),
                "total_power_kw": sum(c.get("power_kw", 0) * c.get("sockets", 0) for c in motos_chargers),
                "charger_ids": [c.get("charger_id") for c in motos_chargers]
            },
            "Playa_Mototaxis": {
                "chargers": len(mototaxis_chargers),
                "sockets": sum(c.get("sockets", 0) for c in mototaxis_chargers),
                "total_power_kw": sum(c.get("power_kw", 0) * c.get("sockets", 0) for c in mototaxis_chargers),
                "charger_ids": [c.get("charger_id") for c in mototaxis_chargers]
            }
        },
        "chargers_by_id": {c.get("charger_id"): {
            "playa": c.get("playa"),
            "power_kw": c.get("power_kw"),
            "sockets": c.get("sockets")
        } for c in chargers}
    }

    charger_meta_file = dataset_dir / "charger_metadata.json"
    with open(charger_meta_file, 'w') as f:
        json.dump(charger_metadata, f, indent=2)

    print(f"✓ Metadata de chargers guardada en: {charger_meta_file}\n")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# RESUMEN FINAL
print("=" * 100)
print("RESUMEN: CONSTRUCION DE ESQUEMA CON 128 CHARGERS")
print("=" * 100)

print("\nPlaya Motos (87.5% del sistema):")
print(f"  • {len(motos_chargers)} cargadores")
print(f"  • {sum(c.get('sockets', 0) for c in motos_chargers)} sockets (4 por charger)")
print(f"  • Potencia: {sum(c.get('power_kw', 0) * c.get('sockets', 0) for c in motos_chargers):.0f} kW total")
print(f"  • Tipo: 2 kW por socket (motos)")

print("\nPlaya Mototaxis (12.5% del sistema):")
print(f"  • {len(mototaxis_chargers)} cargadores")
print(f"  • {sum(c.get('sockets', 0) for c in mototaxis_chargers)} sockets (4 por charger)")
print(f"  • Potencia: {sum(c.get('power_kw', 0) * c.get('sockets', 0) for c in mototaxis_chargers):.0f} kW total")
print(f"  • Tipo: 3 kW por socket (mototaxis)")

print("\nSistema total:")
print(f"  • {len(chargers)} cargadores")
print(f"  • {total_sockets} sockets (tomas de carga)")

# Obtener potencia pico y energia del archivo de resultados
esc_rec = chargers_data.get("esc_rec", {})
peak_power = esc_rec.get("peak_sessions_per_hour", 0) * 2.5  # Aproximacion
daily_energy = esc_rec.get("energy_day_kwh", 0)

print(f"  • ~{peak_power:.0f} kW potencia pico")
print(f"  • ~{daily_energy:.0f} kWh energia diaria")

print("\nArchivos de salida:")
print(f"  ✓ {output_schema}")
print(f"  ✓ {charger_meta_file}")

print("\nProximo paso:")
print("  python train_v2_fresh.py")
print("    • Usara schema_with_128_chargers.json")
print("    • Integrara 128 chargers en simulacion")
print("    • Control por playa: ev_charging_power_playa_motos_kw y ev_charging_power_playa_mototaxis_kw")

print("\n" + "=" * 100 + "\n")
