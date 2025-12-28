#!/usr/bin/env python3
"""
Resumen rápido de OE2: PV (pv_pvlib), cargadores y BESS, con reducción de CO2.

Lee los artefactos generados en data/interim/oe2 y muestra los valores clave.
"""
from __future__ import annotations

import json
from pathlib import Path

# Agregar scripts al path para reutilizar load_all
import sys
SCRIPT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_ROOT))

from _common import load_all


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    cfg, rp = load_all("configs/default.yaml")

    ci_kg_kwh = float(cfg.get("oe3", {}).get("grid", {}).get("carbon_intensity_kg_per_kwh", 0.45))

    solar_path = rp.interim_dir / "oe2" / "solar" / "solar_results.json"
    chargers_path = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"
    bess_path = rp.interim_dir / "oe2" / "bess" / "bess_results.json"

    solar = load_json(solar_path)
    chargers = load_json(chargers_path)
    bess = load_json(bess_path)

    # PV
    pv_ac_kw = solar.get("target_ac_kw", 0.0)
    pv_dc_kw = solar.get("target_dc_kw", 0.0)
    pv_annual_kwh = solar.get("annual_kwh", 0.0)
    pv_daily_kwh = pv_annual_kwh / 365.0 if pv_annual_kwh else 0.0

    # Chargers (escenario recomendado)
    esc_rec = chargers.get("esc_rec", {})
    ev_energy_day = esc_rec.get("energy_day_kwh", chargers.get("total_daily_energy_kwh", 0.0))
    ev_peak_kw = chargers.get("peak_power_kw", 0.0)
    chargers_n = int(chargers.get("n_chargers_recommended", 0))

    # BESS (última corrida)
    bess_cap = bess.get("capacity_kwh", 0.0)
    bess_power = bess.get("nominal_power_kw", 0.0)
    bess_import = bess.get("grid_import_kwh_day", 0.0)
    bess_export = bess.get("grid_export_kwh_day", 0.0)
    bess_self = bess.get("self_sufficiency", 0.0)

    # CO2
    co2_pv_annual_kg = pv_annual_kwh * ci_kg_kwh
    co2_pv_annual_t = co2_pv_annual_kg / 1000.0
    co2_pv_daily_kg = pv_daily_kwh * ci_kg_kwh

    print("\n=== RESUMEN OE2 ===\n")
    print("[PV pv_pvlib]")
    print(f"  Potencia AC/DC: {pv_ac_kw:,.1f} kW / {pv_dc_kw:,.1f} kW")
    print(f"  Energia anual:  {pv_annual_kwh:,.0f} kWh/año ({pv_daily_kwh:,.0f} kWh/día)")
    print(f"  CO2 evitado (grid {ci_kg_kwh} kg/kWh): {co2_pv_annual_t:,.1f} t/año ({co2_pv_daily_kg:,.0f} kg/día)")

    print("\n[Cargadores]")
    print(f"  Cargadores recomendados: {chargers_n}  | Pico potencia: {ev_peak_kw:,.0f} kW")
    print(f"  Energia EV diaria:       {ev_energy_day:,.0f} kWh/día")

    print("\n[BESS]")
    print(f"  Capacidad/Potencia: {bess_cap:,.0f} kWh / {bess_power:,.0f} kW")
    print(f"  Autosuficiencia:    {bess_self*100:,.1f}%")
    print(f"  Importación red:    {bess_import:,.0f} kWh/día")
    print(f"  Exportación red:    {bess_export:,.0f} kWh/día")

    print("\nArchivos fuente:")
    print(f"  PV:       {solar_path}")
    print(f"  Chargers: {chargers_path}")
    print(f"  BESS:     {bess_path}")
    print("")


if __name__ == "__main__":
    main()
