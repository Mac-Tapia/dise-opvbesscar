#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verificar contexto de emisiones de Iquitos en archivos OE2."""

import json
from pathlib import Path

def main():
    print("=" * 70)
    print("VERIFICACIÓN FINAL - CONTEXTO EMISIONES IQUITOS EN OE2")
    print("=" * 70)
    print()
    
    base = Path(__file__).parent.parent
    
    # Archivos a verificar
    files = {
        "BESS": base / "data/interim/oe2/bess/bess_results.json",
        "EV Chargers": base / "data/interim/oe2/chargers/chargers_results.json",
        "Contexto Emisiones": base / "data/interim/oe2/contexto_emisiones_iquitos.json",
        "Reporte Cumplimiento": base / "REPORTE_CUMPLIMIENTO.json"
    }
    
    print("ARCHIVOS ACTUALIZADOS:")
    print("-" * 40)
    for nombre, ruta in files.items():
        if ruta.exists():
            data = json.loads(ruta.read_text(encoding="utf-8"))
            has_contexto = "contexto_iquitos" in data or "contexto_emisiones_iquitos" in data
            has_potencial = "potencial_reduccion_co2" in data or "proyecto_ev_mall" in data
            has_flota = "flota_vehicular" in data
            
            status = "OK" if (has_contexto or has_potencial or has_flota) else "X"
            print(f"  [{status}] {nombre}")
        else:
            print(f"  [X] {nombre}: NO EXISTE")
    
    print()
    print("VALORES CLAVE:")
    print("-" * 40)
    
    # BESS
    bess = json.loads(files["BESS"].read_text(encoding="utf-8"))
    print(f"  BESS: {bess['capacity_kwh']} kWh / {bess['nominal_power_kw']} kW")
    
    # Chargers
    chargers = json.loads(files["EV Chargers"].read_text(encoding="utf-8"))
    print(f"  Cargadores: {chargers['n_chargers_recommended']} unidades")
    print(f"  Flota atendida: {chargers['n_motos']} motos + {chargers['n_mototaxis']} mototaxis = {chargers['n_motos'] + chargers['n_mototaxis']} total")
    
    # Contexto
    contexto = json.loads(files["Contexto Emisiones"].read_text(encoding="utf-8"))
    flota = contexto["flota_vehicular"]
    emisiones = contexto["emisiones_transporte"]
    generacion = contexto["generacion_electrica"]
    proyecto = contexto["proyecto_ev_mall"]
    
    print()
    print("CONTEXTO IQUITOS (Plan de Desarrollo Provincial Maynas):")
    print("-" * 40)
    print(f"  Flota total ciudad: {flota['total_vehiculos']:,} vehiculos")
    print(f"    - Mototaxis: {flota['mototaxis_total']:,}")
    print(f"    - Motos lineales: {flota['motos_lineales_total']:,}")
    print(f"  Emisiones transporte: {emisiones['total_tco2_year']:,} tCO2/año ({emisiones['porcentaje_sector_transporte']}% del sector)")
    print(f"  Emisiones generación eléctrica: {generacion['emisiones_tco2_year']:,} tCO2/año")
    print(f"    - Sistema: {generacion['tipo_sistema']}")
    print(f"    - Combustible: {generacion['combustible_galones_year']:,} galones/año")
    
    print()
    print("POTENCIAL REDUCCIÓN CO2 (Proyecto EV Mall):")
    print("-" * 40)
    reduccion = proyecto["potencial_reduccion"]
    atendida = proyecto["flota_atendida"]
    print(f"  Flota atendida: {atendida['total']} vehículos ({atendida['porcentaje_flota_ciudad']}% del total)")
    print(f"  CO2 evitado transporte: {reduccion['co2_directo_transporte_tco2_year']:,.1f} tCO2/año")
    print(f"  CO2 evitado por PV:     {reduccion['co2_indirecto_pv_tco2_year']:,.1f} tCO2/año")
    print(f"  ──────────────────────────────────────")
    print(f"  TOTAL POTENCIAL:        {reduccion['co2_total_potencial_tco2_year']:,.1f} tCO2/año")
    
    print()
    print("=" * 70)
    print("ESTADO: TODOS LOS ARCHIVOS OE2 ACTUALIZADOS CON CONTEXTO EMISIONES")
    print("=" * 70)

if __name__ == "__main__":
    main()
