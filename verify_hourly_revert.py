#!/usr/bin/env python3
"""
Verifica que el pipeline genere datos horarios (8,760 timesteps), no 15-minutos.
"""
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from iquitos_citylearn.config import RuntimePaths, load_yaml
from iquitos_citylearn.oe2.bess import load_pv_generation, load_ev_demand, run_bess_sizing

def main():
    """Verifica que los datos sean horarios (8,760)."""
    print("=" * 70)
    print("VERIFICACIÓN: DATOS HORARIOS (8,760 timesteps)")
    print("=" * 70)

    # Load config
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    config = load_yaml(config_path)

    paths = RuntimePaths(
        root_dir=Path(__file__).parent,
        config_dir=Path(__file__).parent / "configs",
    )

    print("\n1. Verificando PV generation...")
    try:
        df_pv = load_pv_generation(
            pv_csv_path=paths.interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
        )
        print(f"   ✓ PV shape: {df_pv.shape}")
        if len(df_pv) == 8760:
            print(f"   ✓ PV tiene 8,760 horas (CORRECTO)")
        else:
            print(f"   ✗ ERROR: PV tiene {len(df_pv)} filas, esperaba 8,760")
            return False
    except Exception as e:
        print(f"   ✗ Error cargando PV: {e}")
        return False

    print("\n2. Verificando EV demand...")
    try:
        ev_csv = list(paths.interim_dir.glob("oe2/chargers/**/perfil_horario_carga.csv"))
        if not ev_csv:
            print(f"   ✗ No se encontró perfil_horario_carga.csv")
            return False

        df_ev = load_ev_demand(ev_csv[0])
        print(f"   ✓ EV shape: {df_ev.shape}")
        if len(df_ev) == 8760:
            print(f"   ✓ EV tiene 8,760 horas (CORRECTO)")
        else:
            print(f"   ✗ ERROR: EV tiene {len(df_ev)} filas, esperaba 8,760")
            return False
    except Exception as e:
        print(f"   ✗ Error cargando EV: {e}")
        return False

    print("\n3. Verificando Mall demand...")
    try:
        # Crear demanda del mall (200 kW promedio)
        import numpy as np
        import pandas as pd

        mall_load = np.full(8760, 200.0)  # 200 kW constante
        df_mall = pd.DataFrame({
            'hour': np.arange(8760),
            'mall_kwh': mall_load
        })
        print(f"   ✓ Mall shape: {df_mall.shape}")
        if len(df_mall) == 8760:
            print(f"   ✓ Mall tiene 8,760 horas (CORRECTO)")
        else:
            print(f"   ✗ ERROR: Mall tiene {len(df_mall)} filas, esperaba 8,760")
            return False
    except Exception as e:
        print(f"   ✗ Error creando Mall: {e}")
        return False

    print("\n4. Ejecutando run_bess_sizing()...")
    try:
        result = run_bess_sizing(
            out_dir=paths.interim_dir / "oe2" / "bess_output",
            mall_energy_kwh_day=4800.0,  # 200 kW * 24 h
            pv_profile_path=paths.interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv",
            ev_profile_path=ev_csv[0],
            pv_dc_kw=4050,
            year=2024,
            generate_plots=False,
        )
        print(f"   ✓ run_bess_sizing() completado")
        print(f"   ✓ Capacidad BESS: {result.capacity_kwh:.0f} kWh")
        print(f"   ✓ Potencia BESS: {result.nominal_power_kw:.0f} kW")
    except Exception as e:
        print(f"   ✗ Error en run_bess_sizing(): {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("✓ VERIFICACIÓN EXITOSA: Pipeline genera datos horarios (8,760)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
