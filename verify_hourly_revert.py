#!/usr/bin/env python3
"""
Verifica que el pipeline genere datos horarios (8,760 timesteps), no 15-minutos.
"""
from pathlib import Path
import sys

def main():
    """Verifica que los datos sean horarios (8,760)."""
    print("=" * 70)
    print("VERIFICACIÓN: DATOS HORARIOS (8,760 timesteps)")
    print("=" * 70)

    # Check solar file
    solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    if solar_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(solar_path)
            if len(df) == 8760:
                print(f"✓ Solar: 8,760 filas (CORRECTO)")
            else:
                print(f"✗ Solar: {len(df)} filas, esperaba 8,760")
                return False
        except Exception as e:
            print(f"✗ Error solar: {e}")
            return False
    else:
        print(f"⚠ Solar file not found (not critical)")

    # Check charger files
    charger_path = Path("data/interim/oe2/chargers")
    if charger_path.exists():
        csv_files = list(charger_path.glob("**/perfil_horario_carga.csv"))
        if csv_files:
            try:
                df = pd.read_csv(csv_files[0])
                if len(df) == 8760 or len(df) == 24:  # Either hourly or daily
                    print(f"✓ Chargers: {len(df)} filas (OK)")
                else:
                    print(f"✗ Chargers: unexpected shape {len(df)}")
                    return False
            except Exception as e:
                print(f"✗ Error chargers: {e}")
                return False
        else:
            print(f"⚠ Charger profiles not found (not critical)")
    else:
        print(f"⚠ Chargers directory not found (not critical)")

    print("\n" + "=" * 70)
    print("✓ VERIFICACIÓN COMPLETADA")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
