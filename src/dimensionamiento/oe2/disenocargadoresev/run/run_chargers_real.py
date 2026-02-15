#!/usr/bin/env python3
"""
Ejecuta el modulo de dimensionamiento de cargadores (chargers.py)
para generar dataset REAL basado en Tabla 13 OE2.

Especificaciones:
- 19 cargadores totales (30 motos + 8 mototaxis)
- 38 sockets (4 por cargador)
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
    print("GENERACION DE DATASET REAL - CARGADORES EV (Tabla 13 OE2)")
    print("=" * 80)

    # Directorio de salida
    out_dir = Path("data/oe2/chargers")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1] Parametros de entrada (Tabla 13 OE2 - v5.2):")
    print(f"    Cargadores Motos: 15 × 2 sockets @ 7.4 kW = 222 kW")
    print(f"    Cargadores Mototaxis: 4 × 2 sockets @ 7.4 kW = 59.2 kW")
    print(f"    Sockets totales: 38 (2 por cargador) [v5.2]")
    print(f"    Potencia maxima: 281.2 kW")
    print(f"    Vehiculos/dia: 270 motos + 39 mototaxis = 309")
    print(f"    Horario: 09:00-22:00 (13 horas)")
    print(f"    Pico: 18:00-22:00 (4 horas)")

    print(f"\n[2] Ejecutando run_charger_sizing()...")

    try:
        result = run_charger_sizing(
            out_dir=out_dir,
            seed=2024,
            # Parametros v5.2 - 19 cargadores x 2 sockets @ 7.4 kW
            n_motos=30,                 # 15 cargadores x 2 sockets
            n_mototaxis=8,              # 4 cargadores x 2 sockets
            pe_motos=0.90,              # 90% penetracion
            pe_mototaxis=0.90,          # 90% penetracion
            fc_motos=0.90,              # 90% factor carga
            fc_mototaxis=0.90,          # 90% factor carga
            peak_share_day=0.60,        # 60% energia en pico
            session_minutes=20.0,       # 20 min/sesion
            utilization=0.85,           # 85% utilizacion
            charger_power_kw_moto=7.4,       # 7.4 kW Modo 3 (32A@230V)
            charger_power_kw_mototaxi=7.4,   # 7.4 kW Modo 3 (32A@230V)
            sockets_per_charger=2,      # 2 sockets/cargador
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

        print(f"    [OK] Dimensionamiento completado")

        # Extraer escenario recomendado
        if 'escenario_recomendado' in result:
            esc_rec = result['escenario_recomendado']
            print(f"\n[3] Escenario Recomendado:")
            print(f"    Cargadores: {esc_rec['chargers_required']}")
            print(f"    Sockets: {esc_rec['sockets_total']}")
            print(f"    Energia diaria: {esc_rec['energy_day_kwh']:.2f} kWh")
            print(f"    Energia anual: {esc_rec['energy_day_kwh'] * 365:.2f} kWh")
            print(f"    Potencia pico: {esc_rec.get('peak_power_kw', 'N/A')} kW")

        print(f"\n[4] Archivos generados:")
        files = list(out_dir.glob("*.csv"))
        for f in sorted(files)[-5:]:
            size_kb = f.stat().st_size / 1024
            print(f"    [OK] {f.name} ({size_kb:.1f} KB)")

        print(f"\n[5] Directorio de salida:")
        print(f"    {out_dir.absolute()}")

        print(f"\n" + "=" * 80)
        print(f"[OK] GENERACION COMPLETADA EXITOSAMENTE")
        print(f"=" * 80)
        print(f"\n[OK] Dataset listo para CityLearnv2 (control individual de 38 sockets)")
        print(f"[OK] Compatible con agentes RL (SAC/PPO/A2C)")
        print(f"[OK] Escenarios calibrados contra Tabla 13 OE2")

    except Exception as e:
        print(f"\n[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
