#!/usr/bin/env python3
"""
Verificación de vinculación de bess.py con chargers.py y solar_pvlib.py

Este script verifica que:
1. Los archivos de salida de chargers.py y solar_pvlib.py existen
2. Los valores calculados son consistentes
3. bess.py puede leer correctamente los datos
4. Los parámetros de configuración están alineados
"""

import json
from pathlib import Path
import pandas as pd

# Colores para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_file_exists(path: Path, description: str) -> bool:
    """Verifica si un archivo existe."""
    exists = path.exists()
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    print(f"  {status} {description}: {path}")
    return exists


def check_value(actual, expected, tolerance, description: str) -> bool:
    """Verifica si un valor está dentro de la tolerancia."""
    if expected == 0:
        match = actual == 0
    else:
        diff_pct = abs(actual - expected) / expected * 100
        match = diff_pct <= tolerance

    status = f"{GREEN}✓{RESET}" if match else f"{RED}✗{RESET}"
    print(f"  {status} {description}: {actual:.2f} (esperado: {expected:.2f})")
    return match


def main():
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  VERIFICACIÓN DE VINCULACIÓN: bess.py ↔ chargers.py ↔ solar_pvlib.py{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

    base_dir = Path("data/interim/oe2")

    all_checks_passed = True

    # ======================================================================
    # 1. Verificar archivos de salida de CHARGERS
    # ======================================================================
    print(f"{BOLD}[1] ARCHIVOS DE SALIDA - CHARGERS{RESET}")

    chargers_dir = base_dir / "chargers"
    chargers_files = {
        "Resultados JSON": chargers_dir / "chargers_results.json",
        "Perfil horario carga": chargers_dir / "perfil_horario_carga.csv",
        "Perfiles individuales": chargers_dir / "chargers_hourly_profiles.csv",
    }

    for desc, path in chargers_files.items():
        if not check_file_exists(path, desc):
            all_checks_passed = False

    # ======================================================================
    # 2. Verificar archivos de salida de SOLAR
    # ======================================================================
    print(f"\n{BOLD}[2] ARCHIVOS DE SALIDA - SOLAR{RESET}")

    solar_dir = base_dir / "solar"
    solar_files = {
        "Resultados JSON": solar_dir / "solar_results.json",
        "Perfil 24h": solar_dir / "pv_profile_24h.csv",
        "Timeseries completa": solar_dir / "pv_generation_timeseries.csv",
    }

    for desc, path in solar_files.items():
        if not check_file_exists(path, desc):
            all_checks_passed = False

    # ======================================================================
    # 3. Verificar valores en archivos JSON
    # ======================================================================
    print(f"\n{BOLD}[3] CONSISTENCIA DE VALORES{RESET}")

    # Cargar resultados
    chargers_json = chargers_dir / "chargers_results.json"
    solar_json = solar_dir / "solar_results.json"

    if chargers_json.exists() and solar_json.exists():
        with open(chargers_json) as f:
            ch_data = json.load(f)
        with open(solar_json) as f:
            sol_data = json.load(f)

        # Valores esperados de CHARGERS
        print("\n  Valores de CHARGERS:")
        ev_energy_day = ch_data["esc_rec"]["energy_day_kwh"]
        n_chargers = ch_data["n_chargers_recommended"]
        peak_power = ch_data["peak_power_kw"]

        print(f"    • Energía diaria EV: {ev_energy_day:.0f} kWh")
        print(f"    • Cargadores recomendados: {n_chargers}")
        print(f"    • Potencia pico: {peak_power:.0f} kW")
        print(f"    • Potencia instalada total: {ch_data.get('potencia_total_instalada_kw', 272):.0f} kW")

        # Valores esperados de SOLAR
        print("\n  Valores de SOLAR:")
        pv_dc_kw = sol_data["target_dc_kw"]
        pv_annual_kwh = sol_data["annual_kwh"]
        pv_daily_kwh = pv_annual_kwh / 365
        capacity_factor = sol_data["capacity_factor"]

        print(f"    • Capacidad DC: {pv_dc_kw:.0f} kWp")
        print(f"    • Energía anual: {pv_annual_kwh/1e6:.3f} GWh")
        print(f"    • Energía diaria promedio: {pv_daily_kwh:.0f} kWh")
        print(f"    • Factor de capacidad: {capacity_factor*100:.1f}%")

    else:
        print(f"  {RED}✗ No se pueden verificar valores (archivos JSON faltantes){RESET}")
        all_checks_passed = False

    # ======================================================================
    # 4. Verificar datos en archivos CSV
    # ======================================================================
    print(f"\n{BOLD}[4] VERIFICACIÓN DE DATOS CSV{RESET}")

    # Perfil horario EV
    ev_profile_path = chargers_dir / "perfil_horario_carga.csv"
    if ev_profile_path.exists():
        df_ev = pd.read_csv(ev_profile_path)

        # Verificar columnas necesarias
        required_cols = {'hour', 'energy_kwh'}
        has_cols = required_cols.issubset(set(df_ev.columns))

        if has_cols:
            print(f"  {GREEN}✓{RESET} Perfil EV tiene columnas correctas: {list(df_ev.columns)}")

            ev_total = df_ev['energy_kwh'].sum()
            expected_ev = ev_energy_day if 'ev_energy_day' in locals() else 3252.0

            if check_value(ev_total, expected_ev, 1.0, "Energía total EV en CSV"):
                pass
            else:
                all_checks_passed = False
        else:
            print(f"  {RED}✗{RESET} Perfil EV falta columnas: {df_ev.columns.tolist()}")
            all_checks_passed = False

    # Perfil solar 24h
    pv_profile_path = solar_dir / "pv_profile_24h.csv"
    if pv_profile_path.exists():
        df_pv = pd.read_csv(pv_profile_path)

        # Verificar columnas necesarias
        required_cols_pv = {'hour', 'pv_kwh'}
        has_cols_pv = required_cols_pv.issubset(set(df_pv.columns))

        if has_cols_pv:
            print(f"  {GREEN}✓{RESET} Perfil PV tiene columnas correctas: {list(df_pv.columns)}")

            pv_total = df_pv['pv_kwh'].sum()
            expected_pv = pv_daily_kwh if 'pv_daily_kwh' in locals() else 22036.0

            if check_value(pv_total, expected_pv, 1.0, "Energía total PV en CSV (24h)"):
                pass
            else:
                all_checks_passed = False
        else:
            print(f"  {RED}✗{RESET} Perfil PV falta columnas: {df_pv.columns.tolist()}")
            all_checks_passed = False

    # ======================================================================
    # 5. Verificar compatibilidad con bess.py
    # ======================================================================
    print(f"\n{BOLD}[5] COMPATIBILIDAD CON bess.py{RESET}")

    # Verificar que bess.py puede leer los archivos
    try:
        # Simular carga desde bess.py
        from src.iquitos_citylearn.oe2.bess import load_ev_demand, load_pv_generation

        print(f"  {GREEN}✓{RESET} Funciones de bess.py importadas correctamente")

        # Probar carga de EV
        if ev_profile_path.exists():
            df_test_ev = load_ev_demand(ev_profile_path, year=2024)
            ev_loaded = df_test_ev['ev_kwh'].sum() / (len(df_test_ev) / 24)
            print(f"  {GREEN}✓{RESET} load_ev_demand() lee correctamente: {ev_loaded:.0f} kWh/día")

        # Probar carga de PV (timeseries)
        pv_timeseries_path = solar_dir / "pv_generation_timeseries.csv"
        if pv_timeseries_path.exists():
            df_test_pv = load_pv_generation(pv_timeseries_path)
            pv_loaded = df_test_pv['pv_kwh'].sum() / (len(df_test_pv) / 8760)
            print(f"  {GREEN}✓{RESET} load_pv_generation() lee correctamente: {pv_loaded:.0f} kWh/día")

    except Exception as e:
        print(f"  {RED}✗{RESET} Error al importar/ejecutar funciones de bess.py: {e}")
        all_checks_passed = False

    # ======================================================================
    # 6. Verificar script de ejecución
    # ======================================================================
    print(f"\n{BOLD}[6] SCRIPT DE EJECUCIÓN{RESET}")

    bess_script = Path("scripts/run_oe2_bess.py")
    if check_file_exists(bess_script, "Script run_oe2_bess.py"):
        # Verificar que usa las rutas correctas
        content = bess_script.read_text(encoding='utf-8')

        checks = {
            "pv_profile_path": "pv_profile_24h.csv" in content or "pv_generation_timeseries.csv" in content,
            "ev_profile_path": "perfil_horario_carga.csv" in content,
            "mall_demand_path": "demanda_mall" in content or "demandamall" in content,
        }

        for check_name, passed in checks.items():
            status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
            print(f"  {status} Script usa {check_name}")
            if not passed:
                all_checks_passed = False
    else:
        all_checks_passed = False

    # ======================================================================
    # RESUMEN FINAL
    # ======================================================================
    print(f"\n{BOLD}{'='*70}{RESET}")
    if all_checks_passed:
        print(f"{GREEN}{BOLD}✓ TODAS LAS VERIFICACIONES PASARON{RESET}")
        print(f"\n{GREEN}bess.py está correctamente vinculado con chargers.py y solar_pvlib.py{RESET}")
        print(f"\nPuedes ejecutar:")
        print(f"  python scripts/run_oe2_bess.py --config configs/default.yaml")
    else:
        print(f"{RED}{BOLD}✗ ALGUNAS VERIFICACIONES FALLARON{RESET}")
        print(f"\n{YELLOW}Revisa los errores anteriores y ejecuta de nuevo:{RESET}")
        print(f"  python scripts/run_oe2_chargers.py   # Generar datos EV")
        print(f"  python scripts/run_oe2_solar.py      # Generar datos PV")
        print(f"  python VERIFICACION_VINCULACION_BESS.py  # Verificar nuevamente")
    print(f"{BOLD}{'='*70}{RESET}\n")

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    exit(main())
