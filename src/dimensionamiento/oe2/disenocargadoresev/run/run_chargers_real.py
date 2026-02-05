#!/usr/bin/env python3
"""
Ejecuta el módulo de dimensionamiento de cargadores (chargers.py)
para generar dataset REAL basado en Tabla 13 OE2.

Especificaciones:
- 32 cargadores totales (28 motos + 4 mototaxis)
- 128 sockets (4 por cargador)
- Control individual por agentes RL en CityLearnv2
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dimensionamiento.oe2.disenocargadoresev.chargers import run_charger_sizing


def main():
    print("=" * 80)
    print("GENERACIÓN DE DATASET REAL - CARGADORES EV (Tabla 13 OE2)")
    print("=" * 80)

    # Directorio de salida
    out_dir = Path("data/oe2/chargers")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1] Parámetros de entrada (Tabla 13 OE2 - RECOMENDADO):")
    print(f"    Cargadores Motos: 28 × 2 kW = 56 kW")
    print(f"    Cargadores Mototaxis: 4 × 3 kW = 12 kW")
    print(f"    Sockets totales: 128 (4 por cargador)")
    print(f"    Potencia máxima: 68 kW")
    print(f"    Vehículos/día: 900 motos + 130 mototaxis = 1,030")
    print(f"    Horario: 09:00-22:00 (13 horas)")
    print(f"    Pico: 18:00-22:00 (4 horas)")

    print(f"\n[2] Ejecutando run_charger_sizing()...")

    try:
        result = run_charger_sizing(
            out_dir=out_dir,
            seed=2024,
            # Parámetros Tabla 13 OE2 RECOMENDADO
            n_motos=112,                # 28 cargadores × 4 sockets
            n_mototaxis=16,             # 4 cargadores × 4 sockets
            pe_motos=0.90,              # 90% penetración
            pe_mototaxis=0.90,          # 90% penetración
            fc_motos=0.90,              # 90% factor carga
            fc_mototaxis=0.90,          # 90% factor carga
            peak_share_day=0.60,        # 60% energía en pico
            session_minutes=20.0,       # 20 min/sesión
            utilization=0.85,           # 85% utilización
            charger_power_kw_moto=2.0,       # 2 kW motos
            charger_power_kw_mototaxi=3.0,  # 3 kW mototaxis
            sockets_per_charger=4,      # 4 sockets/cargador
            opening_hour=9,             # 9am
            closing_hour=22,            # 10pm
            km_per_kwh=40.0,
            km_per_gallon=30.0,
            kgco2_per_gallon=2.31,
            grid_carbon_kg_per_kwh=0.4521,  # Iquitos CO₂
            peak_hours=[18, 19, 20, 21],    # Horas pico
            n_scenarios=101,            # 101 escenarios (Tabla 13)
            generate_plots=True,
        )

        print(f"    ✅ Dimensionamiento completado")

        # Extraer escenario recomendado
        if 'escenario_recomendado' in result:
            esc_rec = result['escenario_recomendado']
            print(f"\n[3] Escenario Recomendado:")
            print(f"    Cargadores: {esc_rec['chargers_required']}")
            print(f"    Sockets: {esc_rec['sockets_total']}")
            print(f"    Energía diaria: {esc_rec['energy_day_kwh']:.2f} kWh")
            print(f"    Energía anual: {esc_rec['energy_day_kwh'] * 365:.2f} kWh")
            print(f"    Potencia pico: {esc_rec.get('peak_power_kw', 'N/A')} kW")

        print(f"\n[4] Archivos generados:")
        files = list(out_dir.glob("*.csv"))
        for f in sorted(files)[-5:]:
            size_kb = f.stat().st_size / 1024
            print(f"    ✅ {f.name} ({size_kb:.1f} KB)")

        print(f"\n[5] Directorio de salida:")
        print(f"    {out_dir.absolute()}")

        print(f"\n" + "=" * 80)
        print(f"✅ GENERACIÓN COMPLETADA EXITOSAMENTE")
        print(f"=" * 80)
        print(f"\n✓ Dataset listo para CityLearnv2 (control individual de 128 sockets)")
        print(f"✓ Compatible con agentes RL (SAC/PPO/A2C)")
        print(f"✓ Escenarios calibrados contra Tabla 13 OE2")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
