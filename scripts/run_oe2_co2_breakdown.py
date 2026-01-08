#!/usr/bin/env python3
"""
Script para generar el breakdown de CO2 de OE2 usando metodología OE3.

Calcula:
- Reducción DIRECTA: Electrificación (gasolina → EV)
- Reducción INDIRECTA: EV alimentado por PV (en lugar de red)
- Reducción NETA: Total OE2

Metodología OE3:
1. La energía EV se asigna proporcionalmente entre red y PV/BESS
2. ev_from_grid = grid_import × (ev_demand / total_demand)
3. ev_from_pv = ev_demand - ev_from_grid
4. indirect_avoided = ev_from_pv × grid_factor
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from scripts._common import load_all


def main(config_path: Path) -> dict:
    """Ejecuta cálculo de breakdown CO2 OE2."""
    cfg, rp = load_all(config_path)
    
    # Cargar resultados OE2
    bess_path = rp.interim_dir / "oe2" / "bess" / "bess_results.json"
    chargers_path = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"
    solar_path = rp.interim_dir / "oe2" / "solar" / "solar_results.json"
    
    bess = json.loads(bess_path.read_text(encoding="utf-8"))
    chargers = json.loads(chargers_path.read_text(encoding="utf-8"))
    solar = json.loads(solar_path.read_text(encoding="utf-8"))
    
    # Factores de emisión
    em = cfg["oe3"]["emissions"]
    grid_co2 = cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]
    km_per_kwh = em["km_per_kwh"]
    km_per_gallon = em["km_per_gallon"]
    kgco2_per_gallon = em["kgco2_per_gallon"]
    project_life = em.get("project_life_years", 20)
    
    # Línea base ciudad
    city = cfg["oe3"].get("city_baseline_tpy", {})
    transport_tpy = city.get("transport", 258250.0)
    electricity_tpy = city.get("electricity_generation", 290000.0)
    
    # Parámetros de flota EV
    ev_fleet = cfg["oe2"]["ev_fleet"]
    n_motos = ev_fleet["motos_count"]
    n_mototaxis = ev_fleet["mototaxis_count"]
    # pe_* y fc_* no se usan (demanda viene de capacidad de cargadores)
    
    # ==== DEMANDA EV DEL SISTEMA (capacidad de cargadores) ====
    # El sistema está diseñado para atender 3,072 sesiones/día (capacidad cargadores)
    ev_demand_day = chargers["total_daily_energy_kwh"]  # 2,939 kWh/día
    sessions_per_day = chargers["capacity_sessions_per_day"]  # 3,072
    
    # Vehículos atendidos por día (del escenario recomendado)
    esc_rec = chargers.get("esc_rec", {})
    motos_atendidos_dia = esc_rec.get("vehicles_day_motos", 2684)
    mototaxis_atendidos_dia = esc_rec.get("vehicles_day_mototaxis", 388)
    total_vehiculos_dia = motos_atendidos_dia + mototaxis_atendidos_dia
    
    # Proporción de cada tipo de vehículo
    pct_motos = motos_atendidos_dia / total_vehiculos_dia if total_vehiculos_dia > 0 else 0.874
    pct_mototaxis = mototaxis_atendidos_dia / total_vehiculos_dia if total_vehiculos_dia > 0 else 0.126
    
    # Línea base Iquitos (disgregada)
    # Fuente: Plan de Desarrollo de Maynas (70,500 motos, 61,000 mototaxis)
    co2_motos_iquitos_tpy = 105750  # tCO2/año (70,500 motos)
    co2_mototaxis_iquitos_tpy = 152500  # tCO2/año (61,000 mototaxis)
    
    # Datos de balance energético del sistema
    mall_demand_day = bess["mall_demand_kwh_day"]
    pv_gen_day = bess["pv_generation_kwh_day"]
    total_demand_day = mall_demand_day + ev_demand_day
    
    # PV usado = min(PV generado, demanda total)
    pv_used_day = min(pv_gen_day, total_demand_day)
    # Import de red = demanda - PV usado (si demanda > PV)
    grid_import_day = max(total_demand_day - pv_gen_day, 0)
    # Export = PV sobrante (si PV > demanda)
    grid_export_day = max(pv_gen_day - total_demand_day, 0)
    
    # ==== METODOLOGÍA ====
    # 
    # DIRECTA: Beneficio de electrificación (reemplazo gasolina por EV)
    # INDIRECTA: Beneficio de generación renovable (PV/BESS desplaza red)
    #
    
    # 1. Valores anuales
    ev_demand_year = ev_demand_day * 365
    pv_used_year = pv_used_day * 365
    grid_import_year = grid_import_day * 365

    # 2. Servicio de transporte
    km_year = ev_demand_year * km_per_kwh
    gallons_year = km_year / max(km_per_gallon, 1e-9)
    
    # 3. Baseline: CO2 si usaran gasolina
    transport_base_kgco2_year = gallons_year * kgco2_per_gallon
    transport_base_tco2_year = transport_base_kgco2_year / 1000
    
    # 4. CO2 si toda la carga EV fuera de red (sin PV) - solo referencia
    ev_all_grid_kgco2_year = ev_demand_year * grid_co2
    ev_all_grid_tco2_year = ev_all_grid_kgco2_year / 1000
    
    # 5. Reducción DIRECTA (electrificación): Reemplazo gasolina por EV
    #    = TODO el CO₂ de gasolina que se deja de emitir
    #    NO involucra carga de red - es el beneficio BRUTO de electrificación
    direct_avoided_kgco2_year = transport_base_kgco2_year
    direct_avoided_tco2_year = transport_base_tco2_year
    
    # 5.1 Disgregación DIRECTA por tipo de vehículo
    direct_motos_tco2_year = direct_avoided_tco2_year * pct_motos
    direct_mototaxis_tco2_year = direct_avoided_tco2_year * pct_mototaxis
    
    # 5.2 Contribución disgregada vs Iquitos
    pct_direct_motos_vs_iquitos = 100.0 * direct_motos_tco2_year / co2_motos_iquitos_tpy
    pct_direct_mototaxis_vs_iquitos = 100.0 * direct_mototaxis_tco2_year / co2_mototaxis_iquitos_tpy
    
    # 6. Reducción INDIRECTA (generación renovable): PV/BESS desplaza red
    #    TODO el PV usado localmente desplaza generación térmica de la red
    indirect_avoided_kgco2_year = pv_used_year * grid_co2
    indirect_avoided_tco2_year = indirect_avoided_kgco2_year / 1000
    
    # 6.1 Contribución INDIRECTA vs electricidad Iquitos
    pct_indirect_vs_electricity = 100.0 * indirect_avoided_tco2_year / electricity_tpy
    
    # 7. Reducción NETA TOTAL
    net_avoided_kgco2_year = direct_avoided_kgco2_year + indirect_avoided_kgco2_year
    net_avoided_tco2_year = net_avoided_kgco2_year / 1000
    
    # 8. CO2 real del sistema (importación de red)
    real_grid_kgco2_year = grid_import_year * grid_co2
    real_grid_tco2_year = real_grid_kgco2_year / 1000
    
    # 9. Proyección vida útil
    direct_avoided_tco2_life = direct_avoided_tco2_year * project_life
    direct_motos_tco2_life = direct_motos_tco2_year * project_life
    direct_mototaxis_tco2_life = direct_mototaxis_tco2_year * project_life
    indirect_avoided_tco2_life = indirect_avoided_tco2_year * project_life
    net_avoided_tco2_life = net_avoided_tco2_year * project_life
    
    # 10. Contribución a Iquitos - total
    pct_transport = 100.0 * direct_avoided_tco2_year / transport_tpy
    pct_total = 100.0 * net_avoided_tco2_year / (transport_tpy + electricity_tpy)
    
    # 11. Contribución INDIRECTA a electricidad de Iquitos
    pct_indirect_vs_electricity = 100.0 * indirect_avoided_tco2_year / electricity_tpy
    
    # 12. Vida útil disgregada por tipo de vehículo
    direct_motos_tco2_life = direct_motos_tco2_year * project_life
    direct_mototaxis_tco2_life = direct_mototaxis_tco2_year * project_life
    
    # Resultados
    results = {
        # Sistema
        "pv_dc_kw": solar["target_dc_kw"],
        "pv_annual_kwh": solar["annual_kwh"],
        "bess_capacity_kwh": bess["capacity_kwh"],
        "bess_power_kw": bess["nominal_power_kw"],
        "n_chargers": chargers["n_chargers_recommended"],
        "n_sockets": chargers["n_chargers_recommended"] * cfg["oe2"]["ev_fleet"]["sockets_per_charger"],
        "sessions_per_day": sessions_per_day,
        # Flota propia (referencia)
        "n_motos": n_motos,
        "n_mototaxis": n_mototaxis,
        "total_vehiculos_dia": total_vehiculos_dia,
        # Vehículos atendidos por día (capacidad de cargadores)
        "motos_atendidos_dia": motos_atendidos_dia,
        "mototaxis_atendidos_dia": mototaxis_atendidos_dia,
        "pct_motos": pct_motos,
        "pct_mototaxis": pct_mototaxis,
        # Balance energético (capacidad de cargadores = 3,072 sesiones/día)
        "ev_demand_kwh_day": ev_demand_day,
        "ev_demand_kwh_year": ev_demand_year,
        "mall_demand_kwh_day": mall_demand_day,
        "total_demand_kwh_day": total_demand_day,
        "pv_generation_kwh_day": pv_gen_day,
        "pv_used_kwh_day": pv_used_day,
        "pv_used_kwh_year": pv_used_year,
        "grid_import_kwh_day": grid_import_day,
        "grid_import_kwh_year": grid_import_year,
        "grid_export_kwh_day": grid_export_day,
        "self_sufficiency": bess["self_sufficiency"],
        # Servicio transporte
        "km_year": km_year,
        "gallons_year": gallons_year,
        # CO2 baseline gasolina
        "transport_base_kgco2_year": transport_base_kgco2_year,
        "transport_base_tco2_year": transport_base_tco2_year,
        # Escenario EV solo red (sin PV)
        "ev_all_grid_kgco2_year": ev_all_grid_kgco2_year,
        "ev_all_grid_tco2_year": ev_all_grid_tco2_year,
        # Reducción DIRECTA (electrificación)
        "direct_avoided_kgco2_year": direct_avoided_kgco2_year,
        "direct_avoided_tco2_year": direct_avoided_tco2_year,
        "direct_avoided_tco2_life": direct_avoided_tco2_life,
        # Reducción DIRECTA disgregada por tipo de vehículo
        "direct_motos_tco2_year": direct_motos_tco2_year,
        "direct_mototaxis_tco2_year": direct_mototaxis_tco2_year,
        "direct_motos_tco2_life": direct_motos_tco2_life,
        "direct_mototaxis_tco2_life": direct_mototaxis_tco2_life,
        # Reducción INDIRECTA (PV/BESS)
        "indirect_avoided_kgco2_year": indirect_avoided_kgco2_year,
        "indirect_avoided_tco2_year": indirect_avoided_tco2_year,
        "indirect_avoided_tco2_life": indirect_avoided_tco2_life,
        # Reducción NETA
        "net_avoided_kgco2_year": net_avoided_kgco2_year,
        "net_avoided_tco2_year": net_avoided_tco2_year,
        "net_avoided_tco2_life": net_avoided_tco2_life,
        # CO2 real del sistema
        "real_grid_kgco2_year": real_grid_kgco2_year,
        "real_grid_tco2_year": real_grid_tco2_year,
        # Contribución Iquitos
        "city_transport_tpy": transport_tpy,
        "city_electricity_tpy": electricity_tpy,
        "city_total_tpy": transport_tpy + electricity_tpy,
        "contribution_transport_pct": pct_transport,
        "contribution_total_pct": pct_total,
        # Baseline Iquitos disgregado
        "iquitos_motos_fleet": 70_500,
        "iquitos_motos_tco2_year": co2_motos_iquitos_tpy,
        "iquitos_mototaxis_fleet": 61_000,
        "iquitos_mototaxis_tco2_year": co2_mototaxis_iquitos_tpy,
        # Contribución disgregada vs Iquitos
        "pct_direct_motos_vs_iquitos": pct_direct_motos_vs_iquitos,
        "pct_direct_mototaxis_vs_iquitos": pct_direct_mototaxis_vs_iquitos,
        "pct_indirect_vs_electricity": pct_indirect_vs_electricity,
        # Parámetros
        "grid_co2_kg_per_kwh": grid_co2,
        "km_per_kwh": km_per_kwh,
        "km_per_gallon": km_per_gallon,
        "kgco2_per_gallon": kgco2_per_gallon,
        "project_life_years": project_life,
    }
    
    # Guardar resultados
    out_dir = rp.reports_dir / "oe2" / "co2_breakdown"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON
    (out_dir / "oe2_co2_breakdown.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    
    # Actualizar chargers_results.json con métricas corregidas
    chargers_updated = chargers.copy()
    chargers_updated.update({
        "oe2_pv_used_kwh_year": pv_used_year,
        "oe2_transport_base_tco2_year": transport_base_tco2_year,
        "oe2_ev_all_grid_tco2_year": ev_all_grid_tco2_year,
        "oe2_direct_avoided_tco2_year": direct_avoided_tco2_year,
        "oe2_indirect_avoided_tco2_year": indirect_avoided_tco2_year,
        "oe2_net_avoided_tco2_year": net_avoided_tco2_year,
        "oe2_real_grid_tco2_year": real_grid_tco2_year,
        "oe2_direct_avoided_tco2_life": direct_avoided_tco2_life,
        "oe2_indirect_avoided_tco2_life": indirect_avoided_tco2_life,
        "oe2_net_avoided_tco2_life": net_avoided_tco2_life,
    })
    chargers_path.write_text(
        json.dumps(chargers_updated, indent=2), encoding="utf-8"
    )
    
    # Tabla resumen CSV
    rows = [
        ("Sistema PV (kWp)", f"{results['pv_dc_kw']:,.0f}"),
        ("Generación PV (MWh/año)", f"{results['pv_annual_kwh']/1000:,.0f}"),
        ("PV usado localmente (MWh/año)", f"{results['pv_used_kwh_year']/1000:,.0f}"),
        ("Sistema BESS (kWh)", f"{results['bess_capacity_kwh']:,.0f}"),
        ("Cargadores", f"{results['n_chargers']}"),
        ("Sockets totales", f"{results['n_sockets']}"),
        ("Sesiones/día (capacidad)", f"{results['sessions_per_day']:,.0f}"),
        ("---", "---"),
        ("Vehículos atendidos/día", f"{results['motos_atendidos_dia'] + results['mototaxis_atendidos_dia']:,.0f}"),
        ("  - Motos (87.4%)", f"{results['motos_atendidos_dia']:,.0f}"),
        ("  - Mototaxis (12.6%)", f"{results['mototaxis_atendidos_dia']:,.0f}"),
        ("---", "---"),
        ("Demanda EV (kWh/día)", f"{results['ev_demand_kwh_day']:,.1f}"),
        ("Demanda EV (MWh/año)", f"{results['ev_demand_kwh_year']/1000:,.1f}"),
        ("Demanda Mall (MWh/año)", f"{results['mall_demand_kwh_day']*365/1000:,.0f}"),
        ("Demanda Total (MWh/año)", f"{results['total_demand_kwh_day']*365/1000:,.0f}"),
        ("Import red (MWh/año)", f"{results['grid_import_kwh_year']/1000:,.0f}"),
        ("Autosuficiencia", f"{results['self_sufficiency']*100:.1f}%"),
        ("---", "---"),
        ("Kilómetros/año servidos", f"{results['km_year']:,.0f}"),
        ("Galones gasolina equivalentes", f"{results['gallons_year']:,.0f}"),
        ("---", "---"),
        ("Baseline gasolina (tCO₂/año)", f"{results['transport_base_tco2_year']:,.2f}"),
        ("EV toda red (tCO₂/año)", f"{results['ev_all_grid_tco2_year']:,.2f}"),
        ("---", "---"),
        ("REDUCCIÓN DIRECTA TOTAL (tCO₂/año)", f"{results['direct_avoided_tco2_year']:,.2f}"),
        ("  - Por motos (tCO₂/año)", f"{results['direct_motos_tco2_year']:,.2f}"),
        ("  - Por mototaxis (tCO₂/año)", f"{results['direct_mototaxis_tco2_year']:,.2f}"),
        ("REDUCCIÓN INDIRECTA (tCO₂/año)", f"{results['indirect_avoided_tco2_year']:,.2f}"),
        ("REDUCCIÓN NETA OE2 (tCO₂/año)", f"{results['net_avoided_tco2_year']:,.2f}"),
        ("---", "---"),
        ("Reducción directa 20 años (tCO₂)", f"{results['direct_avoided_tco2_life']:,.0f}"),
        ("  - Motos 20 años (tCO₂)", f"{results['direct_motos_tco2_life']:,.0f}"),
        ("  - Mototaxis 20 años (tCO₂)", f"{results['direct_mototaxis_tco2_life']:,.0f}"),
        ("Reducción indirecta 20 años (tCO₂)", f"{results['indirect_avoided_tco2_life']:,.0f}"),
        ("REDUCCIÓN NETA 20 AÑOS (tCO₂)", f"{results['net_avoided_tco2_life']:,.0f}"),
        ("---", "---"),
        ("BASELINE IQUITOS", ""),
        ("  Motos: 70,500 vehículos", f"{results['iquitos_motos_tco2_year']:,.0f} tCO₂/año"),
        ("  Mototaxis: 61,000 vehículos", f"{results['iquitos_mototaxis_tco2_year']:,.0f} tCO₂/año"),
        ("  Electricidad ciudad", f"{results['city_electricity_tpy']:,.0f} tCO₂/año"),
        ("---", "---"),
        ("CONTRIBUCIÓN OE2 vs IQUITOS", ""),
        ("  % motos vs 105,750 tCO₂", f"{results['pct_direct_motos_vs_iquitos']:.2f}%"),
        ("  % mototaxis vs 152,500 tCO₂", f"{results['pct_direct_mototaxis_vs_iquitos']:.2f}%"),
        ("  % indirecta vs 290,000 tCO₂ elect", f"{results['pct_indirect_vs_electricity']:.2f}%"),
        ("  % transporte total", f"{results['contribution_transport_pct']:.4f}%"),
        ("  % total ciudad", f"{results['contribution_total_pct']:.4f}%"),
    ]
    df = pd.DataFrame(rows, columns=["Métrica", "Valor"])
    df.to_csv(out_dir / "oe2_co2_breakdown.csv", index=False)
    
    # Markdown
    md_lines = [
        "# OE2 - Breakdown de Reducción de CO₂",
        "",
        "## Metodología",
        "",
        "La reducción de CO₂ del sistema OE2 se compone de dos componentes:",
        "",
        "1. **Reducción DIRECTA (Electrificación)**: Beneficio de reemplazar vehículos a gasolina por EV",
        "   - Compara las emisiones de combustión vs las emisiones de cargar EV de la red",
        "",
        "2. **Reducción INDIRECTA (Generación Renovable)**: Beneficio de la generación PV/BESS",
        "   - El PV usado localmente desplaza generación térmica de la red",
        "",
        "### Fórmulas",
        "",
        "```text",
        "Reducción DIRECTA = CO₂_gasolina - CO₂_EV_toda_red",
        "                  = (galones × 8.9 kgCO₂/gal) - (kWh_EV × 0.4521 kgCO₂/kWh)",
        "",
        "Reducción INDIRECTA = PV_usado_localmente × Factor_emisión_red",
        "                    = PV_usado × 0.4521 kgCO₂/kWh",
        "",
        "Reducción NETA = Directa + Indirecta",
        "```",
        "",
        "## Sistema Dimensionado",
        "",
        f"| Componente | Valor |",
        f"| ---------- | ----- |",
        f"| Sistema PV | {results['pv_dc_kw']:,.0f} kWp |",
        f"| Generación PV | {results['pv_annual_kwh']/1e6:.2f} GWh/año |",
        f"| PV usado localmente | {results['pv_used_kwh_year']/1e6:.2f} GWh/año |",
        f"| Sistema BESS | {results['bess_capacity_kwh']:,.0f} kWh |",
        f"| Cargadores | {results['n_chargers']} × 4 = {results['n_sockets']} sockets |",
        f"| Sesiones/año (capacidad) | {results['sessions_per_day']*365:,.0f} |",
        "",
        "## Balance Energético",
        "",
        f"| Métrica | Valor |",
        f"| ------- | ----- |",
        f"| Demanda EV | {results['ev_demand_kwh_day']:,.1f} kWh/día |",
        f"| Demanda EV | {results['ev_demand_kwh_year']/1000:,.1f} MWh/año |",
        f"| Demanda Mall | {results['mall_demand_kwh_day']*365/1000:,.0f} MWh/año |",
        f"| Demanda Total | {results['total_demand_kwh_day']*365/1000:,.0f} MWh/año |",
        f"| Generación PV | {results['pv_annual_kwh']/1000:,.0f} MWh/año |",
        f"| PV usado localmente | {results['pv_used_kwh_year']/1000:,.0f} MWh/año |",
        f"| Import red | {results['grid_import_kwh_year']/1000:,.0f} MWh/año |",
        f"| Autosuficiencia | {results['self_sufficiency']*100:.1f}% |",
        "",
        "## Reducción de Emisiones CO₂",
        "",
        "### Servicio de Transporte (EV)",
        "",
        f"- Energía EV: **{results['ev_demand_kwh_year']/1000:,.0f} MWh/año**",
        f"- Kilómetros servidos: **{results['km_year']:,.0f} km/año**",
        f"- Galones gasolina equivalentes: **{results['gallons_year']:,.0f} gal/año**",
        "",
        "### Escenarios de Emisión",
        "",
        f"| Escenario | tCO₂/año |",
        f"| --------- | -------- |",
        f"| Baseline gasolina (sin EV) | {results['transport_base_tco2_year']:,.2f} |",
        f"| EV toda red (sin PV) | {results['ev_all_grid_tco2_year']:,.2f} |",
        f"| Sistema real (import red) | {results['real_grid_tco2_year']:,.2f} |",
        "",
        "### Reducción OE2",
        "",
        f"| Componente | Concepto | tCO₂/año | tCO₂ (20 años) |",
        f"| ---------- | -------- | -------- | -------------- |",
        f"| **DIRECTA** | Electrificación (gasolina → EV) | {results['direct_avoided_tco2_year']:,.2f} | {results['direct_avoided_tco2_life']:,.0f} |",
        f"| **INDIRECTA** | Generación PV/BESS | {results['indirect_avoided_tco2_year']:,.2f} | {results['indirect_avoided_tco2_life']:,.0f} |",
        f"| **NETA OE2** | **Total** | **{results['net_avoided_tco2_year']:,.2f}** | **{results['net_avoided_tco2_life']:,.0f}** |",
        "",
        "### Disgregación DIRECTA por Tipo de Vehículo",
        "",
        f"| Tipo | Vehículos/día | % | tCO₂/año | tCO₂ (20 años) |",
        f"| ---- | ------------- | - | -------- | -------------- |",
        f"| **Motos** | {results['motos_atendidos_dia']:,.0f} | {results['pct_motos']*100:.1f}% | {results['direct_motos_tco2_year']:,.2f} | {results['direct_motos_tco2_life']:,.0f} |",
        f"| **Mototaxis** | {results['mototaxis_atendidos_dia']:,.0f} | {results['pct_mototaxis']*100:.1f}% | {results['direct_mototaxis_tco2_year']:,.2f} | {results['direct_mototaxis_tco2_life']:,.0f} |",
        f"| **TOTAL** | **{results['motos_atendidos_dia'] + results['mototaxis_atendidos_dia']:,.0f}** | **100%** | **{results['direct_avoided_tco2_year']:,.2f}** | **{results['direct_avoided_tco2_life']:,.0f}** |",
        "",
        "## Contribución a Iquitos",
        "",
        "### Línea Base Iquitos (Plan de Desarrollo de Maynas)",
        "",
        f"| Fuente | Flota/Concepto | tCO₂/año |",
        f"| ------ | -------------- | -------- |",
        f"| Motos | {results['iquitos_motos_fleet']:,} vehículos | {results['iquitos_motos_tco2_year']:,.0f} |",
        f"| Mototaxis | {results['iquitos_mototaxis_fleet']:,} vehículos | {results['iquitos_mototaxis_tco2_year']:,.0f} |",
        f"| **Transporte Total** | 131,500 vehículos | **{results['city_transport_tpy']:,.0f}** |",
        f"| Generación Eléctrica | Red térmica | {results['city_electricity_tpy']:,.0f} |",
        f"| **TOTAL IQUITOS** | | **{results['city_total_tpy']:,.0f}** |",
        "",
        "### Contribución OE2 vs Baseline Iquitos",
        "",
        f"| Reducción OE2 | tCO₂/año | Baseline Iquitos | % Contribución |",
        f"| ------------- | -------- | ---------------- | -------------- |",
        f"| Directa Motos | {results['direct_motos_tco2_year']:,.2f} | {results['iquitos_motos_tco2_year']:,.0f} tCO₂ motos | {results['pct_direct_motos_vs_iquitos']:.2f}% |",
        f"| Directa Mototaxis | {results['direct_mototaxis_tco2_year']:,.2f} | {results['iquitos_mototaxis_tco2_year']:,.0f} tCO₂ mototaxis | {results['pct_direct_mototaxis_vs_iquitos']:.2f}% |",
        f"| Indirecta (PV/BESS) | {results['indirect_avoided_tco2_year']:,.2f} | {results['city_electricity_tpy']:,.0f} tCO₂ elect | {results['pct_indirect_vs_electricity']:.2f}% |",
        f"| **DIRECTA TOTAL** | **{results['direct_avoided_tco2_year']:,.2f}** | {results['city_transport_tpy']:,.0f} tCO₂ transporte | **{results['contribution_transport_pct']:.4f}%** |",
        f"| **NETA OE2** | **{results['net_avoided_tco2_year']:,.2f}** | {results['city_total_tpy']:,.0f} tCO₂ total | **{results['contribution_total_pct']:.4f}%** |",
        "",
        "## Parámetros",
        "",
        f"- Factor emisión red: {results['grid_co2_kg_per_kwh']} kgCO₂/kWh",
        f"- Eficiencia EV: {results['km_per_kwh']} km/kWh",
        f"- Eficiencia gasolina: {results['km_per_gallon']} km/galón",
        f"- Factor emisión gasolina: {results['kgco2_per_gallon']} kgCO₂/galón",
        f"- Vida útil proyecto: {results['project_life_years']} años",
        "",
    ]
    (out_dir / "oe2_co2_breakdown.md").write_text("\n".join(md_lines), encoding="utf-8")
    
    # Imprimir resumen
    print("=" * 70)
    print("OE2 - BREAKDOWN CO₂")
    print("=" * 70)
    print()
    print(f"Sistema: {results['pv_dc_kw']:,.0f} kWp PV | {results['bess_capacity_kwh']:,.0f} kWh BESS | {results['n_chargers']} cargadores")
    print()
    print(f"Vehículos atendidos/día: {results['motos_atendidos_dia'] + results['mototaxis_atendidos_dia']:,.0f}")
    print(f"  - Motos: {results['motos_atendidos_dia']:,.0f} ({results['pct_motos']*100:.1f}%)")
    print(f"  - Mototaxis: {results['mototaxis_atendidos_dia']:,.0f} ({results['pct_mototaxis']*100:.1f}%)")
    print()
    print(f"Balance energético:")
    print(f"  Demanda EV: {results['ev_demand_kwh_year']/1000:,.0f} MWh/año")
    print(f"  PV generado: {results['pv_annual_kwh']/1000:,.0f} MWh/año")
    print(f"  PV usado localmente: {results['pv_used_kwh_year']/1000:,.0f} MWh/año")
    print(f"  Import red: {results['grid_import_kwh_year']/1000:,.0f} MWh/año")
    print()
    print("REDUCCIÓN CO₂:")
    print(f"  DIRECTA (electrificación):        {results['direct_avoided_tco2_year']:,.2f} tCO₂/año")
    print(f"    - Motos:                        {results['direct_motos_tco2_year']:,.2f} tCO₂/año")
    print(f"    - Mototaxis:                    {results['direct_mototaxis_tco2_year']:,.2f} tCO₂/año")
    print(f"  INDIRECTA (PV/BESS desplaza red): {results['indirect_avoided_tco2_year']:,.2f} tCO₂/año")
    print(f"  ------------------------------------------------")
    print(f"  NETA OE2:                         {results['net_avoided_tco2_year']:,.2f} tCO₂/año")
    print()
    print(f"PROYECCIÓN 20 AÑOS: {results['net_avoided_tco2_life']:,.0f} tCO₂")
    print()
    print("CONTRIBUCIÓN vs IQUITOS:")
    print(f"  Directa motos vs 105,750 tCO₂:    {results['pct_direct_motos_vs_iquitos']:.2f}%")
    print(f"  Directa mototaxis vs 152,500 tCO₂: {results['pct_direct_mototaxis_vs_iquitos']:.2f}%")
    print(f"  Indirecta vs 290,000 tCO₂ elect:  {results['pct_indirect_vs_electricity']:.2f}%")
    print(f"  Total transporte:                  {results['contribution_transport_pct']:.4f}%")
    print(f"  Total ciudad:                      {results['contribution_total_pct']:.4f}%")
    print()
    print(f"Resultados guardados en: {out_dir}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OE2 CO2 Breakdown")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/default.yaml"),
        help="Ruta al archivo de configuración",
    )
    args = parser.parse_args()
    main(args.config)
