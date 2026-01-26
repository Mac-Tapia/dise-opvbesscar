#!/usr/bin/env python3
"""
Verificacion: Generacion de 2 datasets de playas de estacionamiento
- Playa_Motos: 28 cargadores (2 kW) = 112 tomas individuales
- Playa_Mototaxis: 4 cargadores (3 kW) = 16 tomas individuales
"""

import sys
import json
from pathlib import Path
import pandas as pd


def verify_playas_datasets():
    """Verificar la generación correcta de datasets de playas."""

    print("\n" + "=" * 80)
    print("VERIFICACION: DATASETS DE 2 PLAYAS DE ESTACIONAMIENTO")
    print("=" * 80)

    oe2_chargers_path = Path("data/interim/oe2/chargers")

    if not oe2_chargers_path.exists():
        print(f"\n[ERROR] Directorio {oe2_chargers_path} no existe")
        return False

    print(f"\n[PASO 1] Verificando estructura de playas en {oe2_chargers_path}")
    print("=" * 80)

    # 1. Verificar archivo de cargadores individuales
    individual_chargers_file = oe2_chargers_path / "individual_chargers.json"

    if not individual_chargers_file.exists():
        print(f"\n[ERROR] Archivo {individual_chargers_file.name} no existe")
        return False

    with open(individual_chargers_file) as f:
        chargers = json.load(f)

    print(f"\n[OK] individual_chargers.json cargado")
    print(f"    Total de cargadores: {len(chargers)}")

    # Separar por playa
    playa_motos = [c for c in chargers if c.get('playa') == 'Playa_Motos']
    playa_mototaxis = [c for c in chargers if c.get('playa') == 'Playa_Mototaxis']

    print(f"\n    Playa_Motos: {len(playa_motos)} cargadores individuales (tomas)")
    print(f"    Playa_Mototaxis: {len(playa_mototaxis)} cargadores individuales (tomas)")
    print(f"    Total: {len(playa_motos) + len(playa_mototaxis)} tomas")

    # Verificar potencias
    moto_powers = set(c.get('power_kw') for c in playa_motos)
    mototaxi_powers = set(c.get('power_kw') for c in playa_mototaxis)

    print(f"\n    Potencias Playa_Motos: {moto_powers}")
    print(f"    Potencias Playa_Mototaxis: {mototaxi_powers}")

    # Validar estructura esperada
    status = True
    errors = []

    if len(playa_motos) != 112:
        errors.append(f"Playa_Motos: esperado 112 tomas, obtenido {len(playa_motos)}")
        status = False
    else:
        print(f"\n[OK] Playa_Motos: 112 tomas = 28 cargadores × 4 sockets")

    if len(playa_mototaxis) != 16:
        errors.append(f"Playa_Mototaxis: esperado 16 tomas, obtenido {len(playa_mototaxis)}")
        status = False
    else:
        print(f"[OK] Playa_Mototaxis: 16 tomas = 4 cargadores × 4 sockets")

    if moto_powers != {2.0}:
        errors.append(f"Playa_Motos: esperado potencia 2.0 kW, obtenido {moto_powers}")
        status = False
    else:
        print(f"[OK] Potencia Playa_Motos: 2.0 kW/toma")

    if mototaxi_powers != {3.0}:
        errors.append(f"Playa_Mototaxis: esperado potencia 3.0 kW, obtenido {mototaxi_powers}")
        status = False
    else:
        print(f"[OK] Potencia Playa_Mototaxis: 3.0 kW/toma")

    # Mostrar errores si existen
    if errors:
        print(f"\n[ERRORES DETECTADOS]:")
        for err in errors:
            print(f"  - {err}")

    # 2. Verificar perfil horario de carga
    print(f"\n[PASO 2] Verificando perfil horario de carga")
    print("=" * 80)

    profile_file = oe2_chargers_path / "perfil_horario_carga.csv"

    if profile_file.exists():
        df_profile = pd.read_csv(profile_file)
        print(f"\n[OK] {profile_file.name} cargado")
        print(f"    Filas: {len(df_profile)} (esperado 8,760 para 1 año horario)")
        print(f"    Columnas: {list(df_profile.columns)}")

        # Mostrar primeras y últimas filas
        print(f"\n    Primeras 3 filas:")
        print(df_profile.head(3).to_string())
        print(f"\n    Últimas 3 filas:")
        print(df_profile.tail(3).to_string())

        if len(df_profile) != 8760:
            print(f"\n[WARNING] Se esperaba 8,760 filas (1 año horario), se obtuvieron {len(df_profile)}")
    else:
        print(f"\n[WARNING] {profile_file.name} no existe (será generado por pipeline)")

    # 3. Resumen de estructura de datos
    print(f"\n[PASO 3] Resumen de estructura de playas")
    print("=" * 80)

    print(f"\nPlaya_Motos (Estacionamiento de Motos):")
    print(f"  - Cantidad de cargadores: 28")
    print(f"  - Sockets por cargador: 4")
    print(f"  - Total de tomas/outlets: 112")
    print(f"  - Potencia por toma: 2.0 kW")
    print(f"  - Potencia total instalada: 224 kW (112 × 2.0)")
    print(f"  - Tipo de vehículo: Motos eléctricas")
    print(f"  - Batería típica: 2.0 kWh")

    print(f"\nPlaya_Mototaxis (Estacionamiento de Mototaxis):")
    print(f"  - Cantidad de cargadores: 4")
    print(f"  - Sockets por cargador: 4")
    print(f"  - Total de tomas/outlets: 16")
    print(f"  - Potencia por toma: 3.0 kW")
    print(f"  - Potencia total instalada: 48 kW (16 × 3.0)")
    print(f"  - Tipo de vehículo: Mototaxis")
    print(f"  - Batería típica: 4.0 kWh")

    print(f"\nTOTAL SISTEMA:")
    print(f"  - Cargadores totales: 32")
    print(f"  - Tomas totales: 128")
    print(f"  - Potencia total instalada: 272 kW")
    print(f"  - Horario operación: 09:00 - 22:00 (13 horas)")
    print(f"  - Horario pico: 18:00 - 22:00 (4 horas)")

    # 4. Validar integración OE2/OE3
    print(f"\n[PASO 4] Validacion de integración OE2 → OE3 (CityLearn)")
    print("=" * 80)

    print(f"\nDataset CityLearn v2 esperado:")
    print(f"  - 128 charger_simulation_XXX.csv files")
    print(f"    * Cada archivo con 8,760 filas (1 año horario)")
    print(f"    * Columnas: hour (0-8759), load_kw (potencia demandada)")
    print(f"  - 1 building CSV (Mall_Iquitos)")
    print(f"    * Energía solar: 8,760 horas")
    print(f"    * Demanda BESS: 8,760 horas")
    print(f"  - Observation space CityLearn v2: 534-dim")
    print(f"    * Building energy metrics")
    print(f"    * 128 charger states (power, occupancy, battery)")
    print(f"    * Time features (hour, month, day-of-week)")
    print(f"  - Action space CityLearn v2: 126-dim")
    print(f"    * 126 charger power setpoints (2 reserved)")

    print(f"\n[RESUMEN DE VERIFICACION]")
    print("=" * 80)

    if status:
        print(f"\n[OK] ESTRUCTURA DE PLAYAS VALIDADA CORRECTAMENTE")
        print(f"     ✓ Playa_Motos: 112 tomas (28 cargadores × 4)")
        print(f"     ✓ Playa_Mototaxis: 16 tomas (4 cargadores × 4)")
        print(f"     ✓ Total: 128 tomas, 32 cargadores, 272 kW")
        print(f"\n[LISTO] Para generar datasets horarios (8,760 timesteps):")
        print(f"     python scripts/run_full_pipeline.py")
        return True
    else:
        print(f"\n[ERROR] Algunos problemas detectados. Ver arriba.")
        return False


def main():
    """Main entry point."""
    success = verify_playas_datasets()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
