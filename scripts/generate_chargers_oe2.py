#!/usr/bin/env python
"""Generate OE2 chargers JSON file if not exists."""

import json
from pathlib import Path


def create_default_chargers():
    """Create default charger configuration for Iquitos."""
    chargers = []

    # 28 chargers @ 2kW (motos)
    for i in range(28):
        chargers.append({
            "id": i,
            "nombre": f"Cargador Motos {i+1}",
            "tipo": "moto",
            "tipo_especifico": "moto_110cc",
            "potencia_max_kw": 2.0,
            "voltaje_v": 220,
            "corriente_max_a": 10.0,
            "baterias_simultáneas": 4,
            "energía_por_batería_kwh": 3.5,
            "tiempo_carga_h": 6,
            "ubicacion": f"Zona A - Puesto {i+1}",
            "estado": "operativo"
        })

    # 4 chargers @ 3kW (mototaxis)
    for i in range(28, 32):
        chargers.append({
            "id": i,
            "nombre": f"Cargador Mototaxis {i-27}",
            "tipo": "mototaxi",
            "tipo_especifico": "mototaxi_250cc",
            "potencia_max_kw": 3.0,
            "voltaje_v": 220,
            "corriente_max_a": 15.0,
            "baterias_simultáneas": 4,
            "energía_por_batería_kwh": 10.0,
            "tiempo_carga_h": 4,
            "ubicacion": f"Zona B - Puesto {i-27}",
            "estado": "operativo"
        })

    return chargers


# Create directory if needed
output_dir = Path("data/interim/oe2/chargers")
output_dir.mkdir(parents=True, exist_ok=True)

# Generate chargers
chargers = create_default_chargers()

# Save to JSON
output_file = output_dir / "individual_chargers.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(chargers, f, indent=2, ensure_ascii=False)

print(f"✅ Created {len(chargers)} chargers in {output_file}")
print(f"   28 motos @ 2kW")
print(f"   4 mototaxis @ 3kW")
print(f"   Total: 32 chargers = 128 sockets (4 per charger)")
