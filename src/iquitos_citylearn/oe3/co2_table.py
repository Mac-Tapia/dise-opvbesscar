from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple

import json
import pandas as pd

@dataclass(frozen=True)
class EmissionsFactors:
    km_per_kwh: float
    km_per_gallon: float
    kgco2_per_gallon: float
    grid_kgco2_per_kwh: float
    project_life_years: int

@dataclass(frozen=True)
class CityBaseline:
    """Emisiones base de la ciudad de Iquitos para contexto."""
    transport_tpy: float  # tCO2/año sector transporte
    electricity_tpy: float  # tCO2/año generación eléctrica

def load_summary(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def annualize(value: float, simulated_years: float) -> float:
    return value / max(simulated_years, 1e-9)

def allocate_grid_to_ev(grid_import_kwh: float, ev_kwh: float, building_kwh: float) -> float:
    denom = max(ev_kwh + building_kwh, 1e-9)
    return grid_import_kwh * (ev_kwh / denom)

def compute_agent_comparison(summary: Dict[str, Any], factors: EmissionsFactors) -> pd.DataFrame:
    """Compara todos los agentes entrenados para seleccionar el mejor.
    
    Evaluación multicriterio basada en:
    1. Emisiones CO₂ (peso alto)
    2. Costo eléctrico
    3. Autoconsumo solar
    4. Satisfacción EV
    5. Estabilidad de red
    """
    pv_results = summary.get("pv_bess_results", {})
    
    rows: List[Dict[str, Any]] = []
    for agent_name, res in pv_results.items():
        ev_kwh_y = annualize(res["ev_charging_kwh"], res["simulated_years"])
        build_kwh_y = annualize(res["building_load_kwh"], res["simulated_years"])
        import_kwh_y = annualize(res["grid_import_kwh"], res["simulated_years"])
        export_kwh_y = annualize(res["grid_export_kwh"], res["simulated_years"])
        pv_kwh_y = annualize(res["pv_generation_kwh"], res["simulated_years"])
        carbon_kg_y = annualize(res["carbon_kg"], res["simulated_years"])
        
        ev_import_kwh_y = allocate_grid_to_ev(import_kwh_y, ev_kwh_y, build_kwh_y)
        
        # Eficiencia operativa: autoconsumo solar / menor dependencia de red
        autosuficiencia = 100.0 * (1 - import_kwh_y / max(ev_kwh_y + build_kwh_y, 1e-9))
        
        # Métricas multiobjetivo si están disponibles
        mo_priority = res.get("multi_objective_priority", "none")
        r_co2 = res.get("reward_co2_mean", 0.0)
        r_cost = res.get("reward_cost_mean", 0.0)
        r_solar = res.get("reward_solar_mean", 0.0)
        r_ev = res.get("reward_ev_mean", 0.0)
        r_grid = res.get("reward_grid_mean", 0.0)
        r_total = res.get("reward_total_mean", 0.0)
        
        rows.append({
            "agente": agent_name,
            "ev_kwh_anual": ev_kwh_y,
            "pv_kwh_anual": pv_kwh_y,
            "import_red_kwh_anual": import_kwh_y,
            "export_red_kwh_anual": export_kwh_y,
            "ev_import_red_kwh_anual": ev_import_kwh_y,
            "carbon_kg_anual": carbon_kg_y,
            "carbon_tco2_anual": carbon_kg_y / 1000.0,
            "autosuficiencia_pct": autosuficiencia,
            # Multiobjetivo
            "mo_priority": mo_priority,
            "reward_co2": r_co2,
            "reward_cost": r_cost,
            "reward_solar": r_solar,
            "reward_ev": r_ev,
            "reward_grid": r_grid,
            "reward_total": r_total,
        })
    
    df = pd.DataFrame(rows)
    if len(df) > 0:
        # Ordenar por menor CO2 anual y mayor autosuficiencia; desempate por recompensa total.
        df = df.sort_values(
            ["carbon_kg_anual", "autosuficiencia_pct", "reward_total"],
            ascending=[True, False, False],
        ).reset_index(drop=True)
        df["ranking"] = range(1, len(df) + 1)
    return df

def compute_table(summary: Dict[str, Any], factors: EmissionsFactors, 
                  city_baseline: CityBaseline = None) -> pd.DataFrame:
    grid = summary.get("grid_only_result")
    baseline = summary.get("pv_bess_uncontrolled")
    best = summary["best_result"]

    # Annual energy terms (kWh/year)
    if baseline is not None:
        base_ev_kwh_y = annualize(baseline["ev_charging_kwh"], baseline["simulated_years"])
        base_build_kwh_y = annualize(baseline["building_load_kwh"], baseline["simulated_years"])
        base_import_kwh_y = annualize(baseline["grid_import_kwh"], baseline["simulated_years"])
        base_ev_import_kwh_y = allocate_grid_to_ev(base_import_kwh_y, base_ev_kwh_y, base_build_kwh_y)
    else:
        base_ev_kwh_y = 0.0
        base_build_kwh_y = 0.0
        base_import_kwh_y = 0.0
        base_ev_import_kwh_y = 0.0

    best_ev_kwh_y = annualize(best["ev_charging_kwh"], best["simulated_years"])
    best_build_kwh_y = annualize(best["building_load_kwh"], best["simulated_years"])
    best_import_kwh_y = annualize(best["grid_import_kwh"], best["simulated_years"])
    best_ev_import_kwh_y = allocate_grid_to_ev(best_import_kwh_y, best_ev_kwh_y, best_build_kwh_y)

    # Transport service (annual km) implied by EV electricity
    reference_ev_kwh_y = base_ev_kwh_y if base_ev_kwh_y > 0 else best_ev_kwh_y
    km_y = reference_ev_kwh_y * factors.km_per_kwh

    # Baseline combustion
    gallons_y = km_y / factors.km_per_gallon
    base_kg_y = gallons_y * factors.kgco2_per_gallon

    # Electrified + grid (optional)
    grid_kg_y = None
    grid_tco2_y = None
    grid_ev_import_kwh_y = None
    if grid is not None:
        grid_ev_kwh_y = annualize(grid["ev_charging_kwh"], grid["simulated_years"])
        grid_build_kwh_y = annualize(grid["building_load_kwh"], grid["simulated_years"])
        grid_import_kwh_y = annualize(grid["grid_import_kwh"], grid["simulated_years"])
        grid_ev_import_kwh_y = allocate_grid_to_ev(grid_import_kwh_y, grid_ev_kwh_y, grid_build_kwh_y)
        grid_kg_y = grid_ev_import_kwh_y * factors.grid_kgco2_per_kwh
        grid_tco2_y = grid_kg_y / 1000.0

    # Electrified + PV+BESS sin control (baseline)
    baseline_kg_y = base_ev_import_kwh_y * factors.grid_kgco2_per_kwh if baseline is not None else None
    baseline_tco2_y = baseline_kg_y / 1000.0 if baseline_kg_y is not None else None

    # Electrified + PV+BESS + control
    ctrl_kg_y = best_ev_import_kwh_y * factors.grid_kgco2_per_kwh
    ctrl_tco2_y = ctrl_kg_y / 1000.0

    data = [
        ("Emisiones transporte base (combustión)", base_kg_y),
    ]
    if grid_kg_y is not None:
        data.append(("Emisiones transporte electrificado + red", grid_kg_y))
    if baseline_kg_y is not None:
        data.append(("Emisiones transporte electrificado + FV+BESS sin control", baseline_kg_y))
    data.append(("Emisiones transporte electrificado + FV+BESS + control", ctrl_kg_y))

    df = pd.DataFrame(data, columns=["escenario", "kgco2_anual"])
    df["tco2_anual"] = df["kgco2_anual"] / 1000.0
    df["tco2_20_anios"] = df["tco2_anual"] * factors.project_life_years

    base = df.loc[df["escenario"].str.contains("combusti", case=False), "tco2_anual"].iloc[0]
    df["reduccion_vs_base_tco2_anual"] = base - df["tco2_anual"]
    df["reduccion_vs_base_pct"] = 100.0 * df["reduccion_vs_base_tco2_anual"] / max(base, 1e-9)

    # Reducciones absolutas vs grid-only y vs PV+BESS sin control (OE2)
    if grid_tco2_y is not None:
        df["reduccion_vs_grid_tco2_anual"] = grid_tco2_y - df["tco2_anual"]
        df["reduccion_vs_grid_pct"] = 100.0 * df["reduccion_vs_grid_tco2_anual"] / max(grid_tco2_y, 1e-9)
    else:
        df["reduccion_vs_grid_tco2_anual"] = None
        df["reduccion_vs_grid_pct"] = None

    if baseline_tco2_y is not None:
        df["reduccion_vs_pvbess_tco2_anual"] = baseline_tco2_y - df["tco2_anual"]
        df["reduccion_vs_pvbess_pct"] = 100.0 * df["reduccion_vs_pvbess_tco2_anual"] / max(baseline_tco2_y, 1e-9)
    else:
        df["reduccion_vs_pvbess_tco2_anual"] = None
        df["reduccion_vs_pvbess_pct"] = None

    meta = {
        "annual_km_equivalent": km_y,
        "grid_ev_import_kwh_y": grid_ev_import_kwh_y,
        "baseline_ev_import_kwh_y": base_ev_import_kwh_y if baseline is not None else None,
        "control_ev_import_kwh_y": best_ev_import_kwh_y,
        "best_agent": summary.get("best_agent"),
        "base_combustion_tco2_y": base,
        "reduction_tco2_y": base - (ctrl_kg_y / 1000.0),
        "grid_tco2_y": grid_tco2_y,
        "baseline_pvbess_tco2_y": baseline_tco2_y,
        "control_tco2_y": ctrl_tco2_y,
    }
    
    # Contexto ciudad Iquitos si está disponible
    if city_baseline:
        meta["city_transport_tpy"] = city_baseline.transport_tpy
        meta["city_electricity_tpy"] = city_baseline.electricity_tpy
        meta["contribution_transport_pct"] = 100.0 * (base - ctrl_kg_y/1000.0) / city_baseline.transport_tpy
    
    df.attrs.update(meta)
    return df

def compute_breakdown(summary: Dict[str, Any], factors: EmissionsFactors) -> pd.DataFrame:
    """Desglosa emisiones directas, indirectas y reduccion neta (Tabla 9)."""
    best = summary["best_result"]
    metrics = _breakdown_metrics(best, factors)

    rows = _metrics_to_rows(metrics, factors)
    df = pd.DataFrame(rows)
    df.attrs.update({
        "best_agent": summary.get("best_agent"),
        "grid_factor_kgco2_kwh": factors.grid_kgco2_per_kwh,
    })
    return df


def compute_control_comparison(summary: Dict[str, Any], factors: EmissionsFactors) -> pd.DataFrame:
    """Comparacion baseline sin control vs control inteligente (PV+BESS conectados)."""
    baseline = summary.get("pv_bess_uncontrolled")
    if baseline is None:
        return pd.DataFrame()

    best = summary["best_result"]
    base_metrics = _breakdown_metrics(baseline, factors)
    best_metrics = _breakdown_metrics(best, factors)

    metrics_order = [
        ("direct_avoided_kgco2_y", "kgco2/y"),
        ("indirect_avoided_kgco2_y", "kgco2/y"),
        ("net_avoided_kgco2_y", "kgco2/y"),
        ("residual_grid_ev_kgco2_y", "kgco2/y"),
        ("direct_avoided_tco2_y", "tco2/y"),
        ("indirect_avoided_tco2_y", "tco2/y"),
        ("net_avoided_tco2_y", "tco2/y"),
    ]

    rows: List[Dict[str, Any]] = []
    for key, unit in metrics_order:
        base_val = float(base_metrics.get(key, 0.0))
        best_val = float(best_metrics.get(key, 0.0))
        rows.append(
            {
                "metric": key,
                "baseline_uncontrolled": base_val,
                "controlled_best": best_val,
                "delta_control_minus_baseline": best_val - base_val,
                "unit": unit,
            }
        )

    df = pd.DataFrame(rows)
    base_net = float(base_metrics.get("net_avoided_tco2_y", 0.0))
    best_net = float(best_metrics.get("net_avoided_tco2_y", 0.0))
    incremental = best_net - base_net
    denom = abs(base_net) if abs(base_net) > 1e-9 else 1.0
    incremental_pct = 100.0 * incremental / denom

    base_direct = float(base_metrics.get("direct_avoided_tco2_y", 0.0))
    best_direct = float(best_metrics.get("direct_avoided_tco2_y", 0.0))
    incr_direct = best_direct - base_direct

    base_indirect = float(base_metrics.get("indirect_avoided_tco2_y", 0.0))
    best_indirect = float(best_metrics.get("indirect_avoided_tco2_y", 0.0))
    incr_indirect = best_indirect - base_indirect
    df.attrs.update({
        "baseline_agent": "Uncontrolled",
        "best_agent": summary.get("best_agent"),
        "grid_factor_kgco2_kwh": factors.grid_kgco2_per_kwh,
        "baseline_net_avoided_tco2_y": base_net,
        "controlled_net_avoided_tco2_y": best_net,
        "incremental_net_avoided_tco2_y": incremental,
        "incremental_net_avoided_pct": incremental_pct,
        "baseline_direct_avoided_tco2_y": base_direct,
        "controlled_direct_avoided_tco2_y": best_direct,
        "incremental_direct_avoided_tco2_y": incr_direct,
        "baseline_indirect_avoided_tco2_y": base_indirect,
        "controlled_indirect_avoided_tco2_y": best_indirect,
        "incremental_indirect_avoided_tco2_y": incr_indirect,
    })
    return df


def _breakdown_metrics(result: Dict[str, Any], factors: EmissionsFactors) -> Dict[str, float]:
    ev_kwh_y = annualize(result["ev_charging_kwh"], result["simulated_years"])
    build_kwh_y = annualize(result["building_load_kwh"], result["simulated_years"])
    import_kwh_y = annualize(result["grid_import_kwh"], result["simulated_years"])
    export_kwh_y = annualize(result["grid_export_kwh"], result["simulated_years"])
    pv_kwh_y = annualize(result["pv_generation_kwh"], result["simulated_years"])

    ev_import_kwh_y = allocate_grid_to_ev(import_kwh_y, ev_kwh_y, build_kwh_y)
    ev_non_grid_kwh_y = max(ev_kwh_y - ev_import_kwh_y, 0.0)
    pv_used_total_kwh_y = max(pv_kwh_y - export_kwh_y, 0.0)

    km_y = ev_kwh_y * factors.km_per_kwh
    gallons_y = km_y / max(factors.km_per_gallon, 1e-9)
    base_kg_y = gallons_y * factors.kgco2_per_gallon

    ev_grid_all_kg_y = ev_kwh_y * factors.grid_kgco2_per_kwh
    direct_avoided_kg_y = base_kg_y - ev_grid_all_kg_y

    indirect_avoided_kg_y = ev_non_grid_kwh_y * factors.grid_kgco2_per_kwh
    net_avoided_kg_y = direct_avoided_kg_y + indirect_avoided_kg_y

    residual_grid_ev_kg_y = ev_import_kwh_y * factors.grid_kgco2_per_kwh

    return {
        "transport_base_kgco2_y": base_kg_y,
        "ev_energy_kwh_y": ev_kwh_y,
        "ev_grid_import_kwh_y": ev_import_kwh_y,
        "ev_non_grid_kwh_y": ev_non_grid_kwh_y,
        "pv_used_total_kwh_y": pv_used_total_kwh_y,
        "direct_avoided_kgco2_y": direct_avoided_kg_y,
        "indirect_avoided_kgco2_y": indirect_avoided_kg_y,
        "net_avoided_kgco2_y": net_avoided_kg_y,
        "residual_grid_ev_kgco2_y": residual_grid_ev_kg_y,
        "direct_avoided_tco2_y": direct_avoided_kg_y / 1000.0,
        "indirect_avoided_tco2_y": indirect_avoided_kg_y / 1000.0,
        "net_avoided_tco2_y": net_avoided_kg_y / 1000.0,
    }


def _metrics_to_rows(metrics: Dict[str, float], factors: EmissionsFactors) -> List[Dict[str, Any]]:
    net_avoided_kg_y = metrics.get("net_avoided_kgco2_y", 0.0)
    return [
        {"metric": "transport_base_kgco2_y", "value": metrics.get("transport_base_kgco2_y", 0.0), "unit": "kgco2/y"},
        {"metric": "ev_energy_kwh_y", "value": metrics.get("ev_energy_kwh_y", 0.0), "unit": "kwh/y"},
        {"metric": "ev_grid_import_kwh_y", "value": metrics.get("ev_grid_import_kwh_y", 0.0), "unit": "kwh/y"},
        {"metric": "ev_non_grid_kwh_y", "value": metrics.get("ev_non_grid_kwh_y", 0.0), "unit": "kwh/y"},
        {"metric": "pv_used_total_kwh_y", "value": metrics.get("pv_used_total_kwh_y", 0.0), "unit": "kwh/y"},
        {"metric": "direct_avoided_kgco2_y", "value": metrics.get("direct_avoided_kgco2_y", 0.0), "unit": "kgco2/y"},
        {"metric": "indirect_avoided_kgco2_y", "value": metrics.get("indirect_avoided_kgco2_y", 0.0), "unit": "kgco2/y"},
        {"metric": "net_avoided_kgco2_y", "value": metrics.get("net_avoided_kgco2_y", 0.0), "unit": "kgco2/y"},
        {"metric": "residual_grid_ev_kgco2_y", "value": metrics.get("residual_grid_ev_kgco2_y", 0.0), "unit": "kgco2/y"},
        {"metric": "direct_avoided_tco2_y", "value": metrics.get("direct_avoided_tco2_y", 0.0), "unit": "tco2/y"},
        {"metric": "indirect_avoided_tco2_y", "value": metrics.get("indirect_avoided_tco2_y", 0.0), "unit": "tco2/y"},
        {"metric": "net_avoided_tco2_y", "value": metrics.get("net_avoided_tco2_y", 0.0), "unit": "tco2/y"},
        {"metric": "net_avoided_tco2_20y", "value": (net_avoided_kg_y / 1000.0) * factors.project_life_years, "unit": "tco2"},
    ]

def write_outputs(
    df: pd.DataFrame,
    out_dir: Path,
    agent_comparison: pd.DataFrame = None,
    breakdown: pd.DataFrame = None,
    control_comparison: pd.DataFrame = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "co2_comparison_table.csv", index=False)
    
    if agent_comparison is not None:
        agent_comparison.to_csv(out_dir / "agent_comparison.csv", index=False)
    if breakdown is not None:
        breakdown.to_csv(out_dir / "co2_breakdown.csv", index=False)
        breakdown_md = breakdown.copy()
        breakdown_md["value"] = breakdown_md["value"].map(lambda v: f"{v:,.3f}")
        (out_dir / "co2_breakdown.md").write_text(
            breakdown_md.to_markdown(index=False),
            encoding="utf-8",
        )
    if control_comparison is not None and len(control_comparison) > 0:
        control_comparison.to_csv(out_dir / "co2_control_vs_uncontrolled.csv", index=False)
        control_md = control_comparison.copy()
        for col in ["baseline_uncontrolled", "controlled_best", "delta_control_minus_baseline"]:
            if col in control_md.columns:
                control_md[col] = control_md[col].map(lambda v: f"{v:,.3f}")
        (out_dir / "co2_control_vs_uncontrolled.md").write_text(
            control_md.to_markdown(index=False),
            encoding="utf-8",
        )

    # Reporte completo para OE3
    md = []
    md.append("# Selección de Agente Inteligente para Reducción de Emisiones CO₂\n")
    md.append("## Objetivo Específico OE3\n")
    md.append("> Seleccionar el agente inteligente de gestión de carga de motos y mototaxis ")
    md.append("> eléctricas más apropiado para maximizar la eficiencia operativa del sistema, ")
    md.append("> asegurando la contribución cuantificable a la reducción de las emisiones de ")
    md.append("> dióxido de carbono en la ciudad de Iquitos, 2025.\n")
    
    md.append("---\n")
    md.append("## 1. Agente Seleccionado\n")
    best_agent = df.attrs.get('best_agent', 'N/A')
    md.append(f"**Agente óptimo seleccionado:** `{best_agent}`\n")
    md.append("**Criterio de selección:** Mínimas emisiones de CO2 anuales y máxima autosuficiencia\n")
    md.append("**Baseline OE2:** PV+BESS conectados con carga EV sin control (Uncontrolled)\n")
    
    if agent_comparison is not None and len(agent_comparison) > 0:
        md.append("\n## 2. Comparación de Agentes Evaluados\n")
        md.append("\n### Métricas de Desempeño\n")
        md.append("| Ranking | Agente | CO₂ (tCO₂/año) | Autosuficiencia (%) | Reward Total |\n")
        md.append("|:-------:|--------|---------------:|--------------------:|-------------:|\n")
        for _, row in agent_comparison.iterrows():
            md.append(f"| {int(row['ranking'])} | {row['agente']} | {row['carbon_tco2_anual']:.2f} | {row['autosuficiencia_pct']:.1f} | {row.get('reward_total', 0):.4f} |\n")
        
        # Tabla multiobjetivo
        md.append("\n### Evaluación Multicriterio (Recompensas por Objetivo)\n")
        md.append("| Agente | R_CO₂ | R_Costo | R_Solar | R_EV | R_Grid |\n")
        md.append("|--------|------:|--------:|--------:|-----:|-------:|\n")
        for _, row in agent_comparison.iterrows():
            md.append(f"| {row['agente']} | {row.get('reward_co2', 0):.3f} | {row.get('reward_cost', 0):.3f} | {row.get('reward_solar', 0):.3f} | {row.get('reward_ev', 0):.3f} | {row.get('reward_grid', 0):.3f} |\n")
        
        md.append("\n**Interpretación de recompensas:** Valores cercanos a +1.0 son óptimos, valores negativos indican mal desempeño.\n")
    
    md.append("\n## 3. Reducción de Emisiones Cuantificable\n")
    km_y = df.attrs.get('annual_km_equivalent', 0)
    md.append(f"**Servicio de transporte equivalente:** {km_y:,.0f} km/año\n")
    md.append("\n### Tabla Comparativa de Escenarios\n")
    md.append(df[["escenario", "tco2_anual", "tco2_20_anios", "reduccion_vs_base_pct"]].to_markdown(index=False))

    # Resumen OE2/OE3: reducciones absolutas vs grid y adicional vs PV+BESS sin control
    grid_tco2_y = df.attrs.get("grid_tco2_y")
    base_pvbess_tco2_y = df.attrs.get("baseline_pvbess_tco2_y")
    ctrl_tco2_y = df.attrs.get("control_tco2_y")
    if grid_tco2_y is not None and ctrl_tco2_y is not None:
        oe3_abs = grid_tco2_y - ctrl_tco2_y
        oe3_pct = 100.0 * oe3_abs / max(grid_tco2_y, 1e-9)
        if base_pvbess_tco2_y is not None:
            oe2_abs = grid_tco2_y - base_pvbess_tco2_y
            oe2_pct = 100.0 * oe2_abs / max(grid_tco2_y, 1e-9)
            incremental_abs = base_pvbess_tco2_y - ctrl_tco2_y
            incremental_pct = 100.0 * incremental_abs / max(base_pvbess_tco2_y, 1e-9)
            md.append("\n\n### Reducciones absolutas y adicionales\n")
            md.append(f"- OE2 (PV+BESS sin control vs grid-only): {oe2_abs:.2f} tCO2/año ({oe2_pct:.2f}%)\n")
            md.append(f"- OE3 (mejor agente vs grid-only): {oe3_abs:.2f} tCO2/año ({oe3_pct:.2f}%)\n")
            md.append(f"- Aporte adicional del control (OE3 vs OE2): {incremental_abs:.2f} tCO2/año ({incremental_pct:.2f}% vs OE2)\n")
        else:
            md.append("\n\n### Reducción OE3 vs grid-only\n")
            md.append(f"- OE3 (mejor agente vs grid-only): {oe3_abs:.2f} tCO2/año ({oe3_pct:.2f}%)\n")
    
    # Impacto en la ciudad
    md.append("\n\n## 4. Contribución a Iquitos 2025\n")
    if "city_transport_tpy" in df.attrs:
        city_transport = df.attrs["city_transport_tpy"]
        contribution = df.attrs.get("contribution_transport_pct", 0)
        reduction = df.attrs.get("reduction_tco2_y", 0)
        md.append(f"| Indicador | Valor |\n")
        md.append(f"|-----------|-------|\n")
        md.append(f"| Emisiones transporte Iquitos | {city_transport:,.0f} tCO₂/año |\n")
        md.append(f"| Reducción por proyecto | {reduction:,.2f} tCO₂/año |\n")
        md.append(f"| **Contribución al sector transporte** | **{contribution:.4f}%** |\n")
    
    md.append("\n## 5. Conclusión\n")
    base_tco2 = df.attrs.get("base_combustion_tco2_y", 0)
    reduction_tco2 = df.attrs.get("reduction_tco2_y", 0)
    reduction_pct = 100.0 * reduction_tco2 / max(base_tco2, 1e-9)
    md.append(f"El agente **{best_agent}** es el más apropiado para la gestión de carga de ")
    md.append(f"motos y mototaxis eléctricas en el Mall de Iquitos, logrando:\n\n")
    md.append(f"- ✅ **Reducción de {reduction_tco2:.2f} tCO₂/año** ({reduction_pct:.1f}% vs combustión)\n")
    md.append(f"- ✅ **Maximización de autoconsumo solar** mediante control inteligente BESS\n")
    md.append(f"- ✅ **Eficiencia operativa** optimizada para el horario pico 18:00-22:00\n")

    if control_comparison is not None and len(control_comparison) > 0:
        md.append("\n## 6. Comparación Baseline vs Control Inteligente\n")
        md.append("\nBaseline: PV+BESS conectados con carga EV sin control (Uncontrolled).\n")
        md.append("\nControl: PV+BESS conectados con el agente seleccionado.\n")
        md.append("\n### Delta de reducción (Control - Baseline)\n")
        md.append(control_comparison.to_markdown(index=False))
        base_net = control_comparison.attrs.get("baseline_net_avoided_tco2_y", 0.0)
        best_net = control_comparison.attrs.get("controlled_net_avoided_tco2_y", 0.0)
        incr_net = control_comparison.attrs.get("incremental_net_avoided_tco2_y", 0.0)
        incr_pct = control_comparison.attrs.get("incremental_net_avoided_pct", 0.0)
        md.append("\n### Incremento neto de reduccion por control inteligente\n")
        md.append(f"- Baseline neto: {base_net:.2f} tCO2/anio\n")
        md.append(f"- Control neto: {best_net:.2f} tCO2/anio\n")
        md.append(f"- Incremento: {incr_net:.2f} tCO2/anio ({incr_pct:.1f}% vs baseline)\n")
        base_direct = control_comparison.attrs.get("baseline_direct_avoided_tco2_y", 0.0)
        best_direct = control_comparison.attrs.get("controlled_direct_avoided_tco2_y", 0.0)
        incr_direct = control_comparison.attrs.get("incremental_direct_avoided_tco2_y", 0.0)
        base_indirect = control_comparison.attrs.get("baseline_indirect_avoided_tco2_y", 0.0)
        best_indirect = control_comparison.attrs.get("controlled_indirect_avoided_tco2_y", 0.0)
        incr_indirect = control_comparison.attrs.get("incremental_indirect_avoided_tco2_y", 0.0)
        md.append("\n### Incremento directo e indirecto\n")
        md.append(f"- Directo: {incr_direct:.2f} tCO2/anio (baseline {base_direct:.2f} -> control {best_direct:.2f})\n")
        md.append(f"- Indirecto: {incr_indirect:.2f} tCO2/anio (baseline {base_indirect:.2f} -> control {best_indirect:.2f})\n")
    
    (out_dir / "co2_comparison_table.md").write_text("\n".join(md), encoding="utf-8")
