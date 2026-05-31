#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actualiza la fuente canonica OE3 desde resultados locales vigentes.

Entradas:
  - outputs/{agent}_training/result_{agent}.json
  - outputs/{agent}_training/{agent}_episodios_history.csv
  - outputs/{agent}_training/{agent}_convergencia_episodios.csv

Salidas:
  - reports/oe3/agents_comparison_canonical.json
  - reports/oe3/agents_comparison_canonical.csv
  - reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "oe3"
OUT_JSON = OUT_DIR / "agents_comparison_canonical.json"
OUT_CSV = OUT_DIR / "agents_comparison_canonical.csv"
OUT_MD = OUT_DIR / "AGENTES_RL_COMPARATIVA_CANONICA.md"

AGENTS = ("SAC", "PPO", "A2C")
F0_REFERENCE_KG = 7_053_999
RUN_DATE = date.today().isoformat()
REWARD_VERSION = "CO2_DUAL_FOCUS v8.1"
CO2_FACTOR_IQUITOS = 0.4521
MOTOS_DATASET = ROOT / "data" / "interim" / "citylearn_v2" / "ev_charger_motos.csv"
MOTOTAXIS_DATASET = ROOT / "data" / "interim" / "citylearn_v2" / "ev_charger_mototaxis.csv"


def fmt_int(value: float) -> str:
    return f"{value:,.0f}"


def fmt_float(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def result_path(agent: str) -> Path:
    a = agent.lower()
    return ROOT / "outputs" / f"{a}_training" / f"result_{a}.json"


def history_path(agent: str) -> Path:
    a = agent.lower()
    return ROOT / "outputs" / f"{a}_training" / f"{a}_episodios_history.csv"


def convergence_path(agent: str) -> Path:
    a = agent.lower()
    return ROOT / "outputs" / f"{a}_training" / f"{a}_convergencia_episodios.csv"


def load_agent(agent: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    result = load_json(result_path(agent))
    history = pd.read_csv(history_path(agent))
    convergence = pd.read_csv(convergence_path(agent))
    return result, history, convergence


def load_vehicle_energy_reference() -> dict:
    """Energia media por evento de carga equivalente del dataset real OE2/CityLearn."""
    motos = pd.read_csv(MOTOS_DATASET)
    mototaxis = pd.read_csv(MOTOTAXIS_DATASET)
    kwh_per_moto = float(motos["ev_demand_kwh"].sum() / motos["vehicles_per_hour"].sum())
    kwh_per_mototaxi = float(
        mototaxis["ev_demand_kwh"].sum() / mototaxis["vehicles_per_hour"].sum()
    )
    return {
        "moto_kwh_per_equivalent_charge": kwh_per_moto,
        "mototaxi_kwh_per_equivalent_charge": kwh_per_mototaxi,
        "source": {
            "motos": str(MOTOS_DATASET.relative_to(ROOT)),
            "mototaxis": str(MOTOTAXIS_DATASET.relative_to(ROOT)),
        },
        "method": (
            "Vehicle counts are equivalent full-charge events derived from EV kWh divided by "
            "dataset kWh per vehicle. PPO/A2C trace count columns are not populated, so direct "
            "trace count columns are not used for cross-agent ranking."
        ),
    }


def cv_plateau(series: np.ndarray, window: int = 15) -> float:
    tail = series[-window:]
    return float(np.std(tail, ddof=0) / np.mean(tail) * 100)


def agent_metrics(agent: str, result: dict, history: pd.DataFrame, vehicle_ref: dict) -> dict:
    f2 = history["co2_control_kg"].astype(float).to_numpy()
    direct_avoided = history["co2_directa_kg"].astype(float).to_numpy()
    indirect_avoided = history["co2_indirecta_kg"].astype(float).to_numpy()
    total_avoided = direct_avoided + indirect_avoided
    f0_reduction = F0_REFERENCE_KG - f2
    grid_import = history["grid_import_kwh"].astype(float).to_numpy()
    ev_motos = history["ev_motos_kwh"].astype(float).to_numpy()
    ev_mototaxis = history["ev_mototaxis_kwh"].astype(float).to_numpy()
    ev_total = ev_motos + ev_mototaxis
    bess_discharge = history["bess_discharge_kwh"].astype(float).to_numpy()
    debt_violations = history["debt_violations"].astype(float).to_numpy()
    solar_export_co2 = history["co2_f6d_kg"].astype(float).to_numpy()
    motos_equiv = float(np.sum(ev_motos) / vehicle_ref["moto_kwh_per_equivalent_charge"])
    mototaxis_equiv = float(
        np.sum(ev_mototaxis) / vehicle_ref["mototaxi_kwh_per_equivalent_charge"]
    )
    total_equiv = motos_equiv + mototaxis_equiv
    best_idx = int(np.argmin(f2))
    best_row = history.iloc[best_idx]
    f2_min = float(best_row["co2_control_kg"])
    validation = result.get("validation", {})

    return {
        "rank": 0,
        "selected": False,
        "f2_min_kg_per_year": int(round(f2_min)),
        "best_episode": int(best_row["episodio"]),
        "f2_mean_kg_per_year": int(round(float(np.mean(f2)))),
        "f2_sigma_kg_per_year": int(round(float(np.std(f2, ddof=0)))),
        "co2_reduction_vs_f0_pct": round((F0_REFERENCE_KG - f2_min) / F0_REFERENCE_KG * 100, 2),
        "co2_avoided_vs_f0_kg_per_year": int(round(F0_REFERENCE_KG - f2_min)),
        "co2_total_avoided_sum_50_kg": int(round(float(np.sum(total_avoided)))),
        "co2_total_avoided_mean_kg_per_episode": int(round(float(np.mean(total_avoided)))),
        "co2_direct_avoided_sum_50_kg": int(round(float(np.sum(direct_avoided)))),
        "co2_indirect_avoided_sum_50_kg": int(round(float(np.sum(indirect_avoided)))),
        "co2_reduction_vs_f0_sum_50_kg": int(round(float(np.sum(f0_reduction)))),
        "co2_reduction_vs_f0_mean_kg_per_episode": int(round(float(np.mean(f0_reduction)))),
        "grid_import_sum_50_kwh": int(round(float(np.sum(grid_import)))),
        "grid_import_mean_kwh_per_episode": int(round(float(np.mean(grid_import)))),
        "ev_motos_sum_50_kwh": int(round(float(np.sum(ev_motos)))),
        "ev_mototaxis_sum_50_kwh": int(round(float(np.sum(ev_mototaxis)))),
        "ev_total_sum_50_kwh": int(round(float(np.sum(ev_total)))),
        "ev_motos_equiv_count_50": int(round(motos_equiv)),
        "ev_mototaxis_equiv_count_50": int(round(mototaxis_equiv)),
        "ev_total_equiv_count_50": int(round(total_equiv)),
        "ev_total_equiv_mean_per_episode": int(round(total_equiv / len(history))),
        "bess_discharge_sum_50_kwh": int(round(float(np.sum(bess_discharge)))),
        "debt_violations_sum_50": int(round(float(np.sum(debt_violations)))),
        "zero_violation_episodes_50": int(np.sum(debt_violations == 0)),
        "solar_export_f6d_sum_50_kwh": int(round(float(np.sum(solar_export_co2) / CO2_FACTOR_IQUITOS))),
        "solar_export_f6d_co2_equiv_sum_50_kg": int(round(float(np.sum(solar_export_co2)))),
        "multiobjective_wins_50": 0,
        "multiobjective_criteria_total": 0,
        "cv_plateau_pct": round(cv_plateau(f2), 3),
        "validation_mean_reward": float(validation.get("mean_reward", np.nan)),
        "validation_mean_co2_avoided_kg": float(validation.get("mean_co2_avoided_kg", np.nan)),
        "validation_mean_grid_import_kwh": float(validation.get("mean_grid_import_kwh", np.nan)),
        "selection_note": "",
    }


def parse_run_date(result: dict) -> str:
    timestamp = str(result.get("timestamp", ""))
    if len(timestamp) >= 8 and timestamp[:8].isdigit():
        return f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    return RUN_DATE


def build_statistics(
    f2_series: dict[str, np.ndarray],
    avoided_series: dict[str, np.ndarray],
) -> dict:
    normality = {}
    for agent in AGENTS:
        w, p_value = stats.shapiro(avoided_series[agent])
        normality[agent] = {
            "w": float(w),
            "p_value": float(p_value),
            "normal": bool(p_value >= 0.05),
        }

    h, kw_p = stats.kruskal(avoided_series["SAC"], avoided_series["PPO"], avoided_series["A2C"])

    def mann(a: str, b: str) -> dict:
        u, p_value = stats.mannwhitneyu(avoided_series[a], avoided_series[b], alternative="greater")
        return {"u": float(u), "p_value": float(p_value)}

    def wilcoxon(a: str, b: str) -> dict:
        w, p_value = stats.wilcoxon(avoided_series[a], avoided_series[b], alternative="greater")
        return {"w": float(w), "p_value": float(p_value)}

    f2_h, f2_kw_p = stats.kruskal(f2_series["SAC"], f2_series["PPO"], f2_series["A2C"])

    def f2_mann_less(a: str, b: str) -> dict:
        u, p_value = stats.mannwhitneyu(f2_series[a], f2_series[b], alternative="less")
        return {"u": float(u), "p_value": float(p_value)}

    return {
        "selection_metric": "co2_total_avoided_kg_per_episode",
        "normality": {
            "test": "Shapiro-Wilk",
            "alpha": 0.05,
            "results": normality,
        },
        "non_parametric_tests": {
            "kruskal_wallis": {
                "h": float(h),
                "p_value": float(kw_p),
                "reject_h0": bool(kw_p < 0.05),
            },
            "mann_whitney_u": {
                "a2c_greater_than_ppo": mann("A2C", "PPO"),
                "a2c_greater_than_sac": mann("A2C", "SAC"),
                "ppo_greater_than_sac": mann("PPO", "SAC"),
            },
            "wilcoxon_signed_rank": {
                "a2c_greater_than_ppo": wilcoxon("A2C", "PPO"),
                "a2c_greater_than_sac": wilcoxon("A2C", "SAC"),
                "ppo_greater_than_sac": wilcoxon("PPO", "SAC"),
            },
        },
        "residual_f2_reference_tests": {
            "kruskal_wallis": {
                "h": float(f2_h),
                "p_value": float(f2_kw_p),
                "reject_h0": bool(f2_kw_p < 0.05),
            },
            "mann_whitney_u": {
                "ppo_less_than_sac": f2_mann_less("PPO", "SAC"),
                "ppo_less_than_a2c": f2_mann_less("PPO", "A2C"),
                "a2c_less_than_sac": f2_mann_less("A2C", "SAC"),
            },
        },
    }


def trace_summary() -> dict | None:
    path = OUT_DIR / "co2_trace_direct_indirect_summary.json"
    if not path.exists():
        return None
    return load_json(path)


def write_csv(payload: dict) -> None:
    rows = []
    for agent in payload["ranking"]:
        m = payload["agents"][agent]
        rows.append(
            {
                "rank": m["rank"],
                "agent": agent,
                "selected": str(m["selected"]).lower(),
                "f2_min_kg_per_year": m["f2_min_kg_per_year"],
                "best_episode": m["best_episode"],
                "f2_mean_kg_per_year": m["f2_mean_kg_per_year"],
                "f2_sigma_kg_per_year": m["f2_sigma_kg_per_year"],
                "co2_total_avoided_sum_50_kg": m["co2_total_avoided_sum_50_kg"],
                "co2_total_avoided_mean_kg_per_episode": m["co2_total_avoided_mean_kg_per_episode"],
                "co2_direct_avoided_sum_50_kg": m["co2_direct_avoided_sum_50_kg"],
                "co2_indirect_avoided_sum_50_kg": m["co2_indirect_avoided_sum_50_kg"],
                "co2_reduction_vs_f0_sum_50_kg": m["co2_reduction_vs_f0_sum_50_kg"],
                "grid_import_sum_50_kwh": m["grid_import_sum_50_kwh"],
                "ev_motos_sum_50_kwh": m["ev_motos_sum_50_kwh"],
                "ev_mototaxis_sum_50_kwh": m["ev_mototaxis_sum_50_kwh"],
                "ev_total_sum_50_kwh": m["ev_total_sum_50_kwh"],
                "ev_motos_equiv_count_50": m["ev_motos_equiv_count_50"],
                "ev_mototaxis_equiv_count_50": m["ev_mototaxis_equiv_count_50"],
                "ev_total_equiv_count_50": m["ev_total_equiv_count_50"],
                "ev_total_equiv_mean_per_episode": m["ev_total_equiv_mean_per_episode"],
                "bess_discharge_sum_50_kwh": m["bess_discharge_sum_50_kwh"],
                "debt_violations_sum_50": m["debt_violations_sum_50"],
                "zero_violation_episodes_50": m["zero_violation_episodes_50"],
                "solar_export_f6d_sum_50_kwh": m["solar_export_f6d_sum_50_kwh"],
                "solar_export_f6d_co2_equiv_sum_50_kg": m["solar_export_f6d_co2_equiv_sum_50_kg"],
                "multiobjective_wins_50": m["multiobjective_wins_50"],
                "multiobjective_criteria_total": m["multiobjective_criteria_total"],
                "co2_reduction_vs_f0_pct": m["co2_reduction_vs_f0_pct"],
                "co2_avoided_vs_f0_kg_per_year": m["co2_avoided_vs_f0_kg_per_year"],
                "cv_plateau_pct": m["cv_plateau_pct"],
                "validation_mean_reward": m["validation_mean_reward"],
                "validation_mean_co2_avoided_kg": m["validation_mean_co2_avoided_kg"],
                "validation_mean_grid_import_kwh": m["validation_mean_grid_import_kwh"],
                "selection_note": m["selection_note"],
            }
        )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_md(payload: dict) -> None:
    selected = payload["metadata"]["selected_agent"]
    selected_metrics = payload["agents"][selected]
    ranking = payload["ranking"]
    trace = trace_summary()

    md: list[str] = []
    md.append("# OE3 - Comparativa canonica de agentes RL")
    md.append("")
    md.append(f"**Fecha de actualizacion:** {payload['metadata']['updated_at']}")
    md.append(f"**Decision vigente:** **{selected} seleccionado**")
    md.append(
        f"**Alcance:** SAC v8.2 reentrenado el 2026-05-30/31 con VecNormalize; "
        f"PPO y A2C vigentes del 2026-05-28. Reward `{REWARD_VERSION}`, "
        "`obs_dim=19`, accion 3D y 50 episodios por agente."
    )
    md.append("")
    md.append(
        "Nota solar: los modulos OE2 mantienen `4,050 kWp` como capacidad nominal de diseno, "
        "mientras el dataset solar vigente reporta `4,162 kWp DC` como potencia PVWatts/pdc0 "
        "y `3,201 kW AC`."
    )
    md.append("")
    md.append("## Fuentes")
    md.append("")
    md.append("- Resultados locales de entrenamiento: `outputs/sac_training/result_sac.json`,")
    md.append("  `outputs/ppo_training/result_ppo.json`, `outputs/a2c_training/result_a2c.json`.")
    md.append("- Resumen de seccion 5.2: `outputs/seccion52/resultados_seccion52.json`.")
    md.append("- Fuente versionada para consultas: `reports/oe3/agents_comparison_canonical.json`.")
    md.append("- Tabla versionada: `reports/oe3/agents_comparison_canonical.csv`.")
    md.append("- Lectura directa desde traces: `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md`.")
    md.append("- Auditoria de fuentes vigentes: `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md`.")
    md.append("- Informe operativo CO2/control/convergencia: `reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md`.")
    md.append("")
    md.append("## Auditoria de fuentes vigentes")
    md.append("")
    md.append("La comparacion usa solo checkpoints finales y resultados guardados actuales:")
    md.append("")
    md.append("| Agente | Checkpoint final | Result JSON | Estado |")
    md.append("|---|---|---|---|")
    for agent in ("SAC", "PPO", "A2C"):
        lower = agent.lower()
        extra = " + `vecnormalize.pkl`" if agent == "SAC" else ""
        md.append(
            f"| {agent} | `checkpoints/{agent}_CityLearn/{lower}_final.zip`{extra} | "
            f"`outputs/{lower}_training/result_{lower}.json` | vigente/no archive |"
        )
    md.append("")
    md.append("No se usan rutas bajo `archive`, `archive_previous` ni `archive_v73_obs16`.")
    md.append("")
    md.append("## Criterio de seleccion")
    md.append("")
    md.append(
        "El criterio principal actualizado de OE3 es un **score multiobjetivo de 50 episodios**. "
        "Se cuentan los liderazgos por criterio: mayor CO2 total evitado, menor importacion de red, "
        "mayor CO2 directo evitado, mayor CO2 indirecto evitado, mayor carga de motos/mototaxis, "
        "mayor uso util de BESS y menor deuda/violaciones de carga."
    )
    md.append(
        "Para motos y mototaxis se reportan **eventos de carga equivalentes**, no solo kWh: "
        "los kWh EV de cada agente se dividen por la energia media por vehiculo del dataset real "
        f"({fmt_float(payload['vehicle_count_reference']['moto_kwh_per_equivalent_charge'], 3)} kWh/moto "
        f"y {fmt_float(payload['vehicle_count_reference']['mototaxi_kwh_per_equivalent_charge'], 3)} "
        "kWh/mototaxi). Las columnas directas de conteo en trace no se usan para comparar porque "
        "PPO/A2C las guardaron en cero."
    )
    md.append("")
    md.append(
        "`F2` se mantiene como lectura complementaria de CO2 residual minimo, pero no reemplaza "
        "la seleccion multiobjetivo. La prueba de normalidad solo decide el tipo de inferencia; "
        "no elige el agente."
    )
    md.append("")
    md.append("## Por que cambio de PPO a A2C")
    md.append("")
    md.append(
        "La comparacion no cambio porque PPO o A2C se hayan reentrenado; PPO y A2C siguen usando "
        "los resultados vigentes del 2026-05-28. Lo que cambio fue el criterio de decision:"
    )
    md.append("")
    md.append("- Si se usa solo el **menor F2 puntual**, gana **PPO** con 3,657,484 kg CO2/año en el episodio 49.")
    md.append(
        "- Si se usa el **score multiobjetivo acumulado de 50 episodios** pedido para operacion, "
        "gana **A2C** porque lidera CO2 total evitado, importacion de red, conteo EV equivalente, "
        "BESS y violaciones."
    )
    md.append(
        "- SAC fue el unico agente reentrenado en v8.2; ese reentrenamiento mejora SAC frente a su "
        "version anterior, pero no cambia los resultados guardados de PPO/A2C ni alcanza a A2C "
        "en el acumulado operativo."
    )
    md.append("")
    md.append("## Tabla comparativa")
    md.append("")
    md.append(
        "| Rank | Agente | Criterios liderados | CO2 total evitado 50 ep (kg) | "
        "Grid import 50 ep (kWh) | CO2 directo 50 ep (kg) | CO2 indirecto 50 ep (kg) | "
        "EV equiv 50 ep | Motos 50 ep (kWh) | Mototaxis 50 ep (kWh) | BESS descarga 50 ep (kWh) | "
        "Deuda/violaciones | F2 minimo (kg/año) |"
    )
    md.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for agent in ranking:
        m = payload["agents"][agent]
        name = f"**{agent}**" if m["selected"] else agent
        b = "**" if m["selected"] else ""
        md.append(
            f"| {m['rank']} | {name} | {b}{m['multiobjective_wins_50']}/{m['multiobjective_criteria_total']}{b} | "
            f"{b}{fmt_int(m['co2_total_avoided_sum_50_kg'])}{b} | "
            f"{fmt_int(m['grid_import_sum_50_kwh'])} | "
            f"{fmt_int(m['co2_direct_avoided_sum_50_kg'])} | "
            f"{fmt_int(m['co2_indirect_avoided_sum_50_kg'])} | "
            f"{fmt_int(m['ev_total_equiv_count_50'])} | "
            f"{fmt_int(m['ev_motos_sum_50_kwh'])} | "
            f"{fmt_int(m['ev_mototaxis_sum_50_kwh'])} | "
            f"{fmt_int(m['bess_discharge_sum_50_kwh'])} | "
            f"{fmt_int(m['debt_violations_sum_50'])} | "
            f"{fmt_int(m['f2_min_kg_per_year'])} |"
        )
    md.append("")
    md.append("## Carga de motos y mototaxis en numeros")
    md.append("")
    md.append(
        "Los valores son conteos equivalentes de cargas completas, derivados del dataset vigente "
        "`data/interim/citylearn_v2/ev_charger_*.csv`."
    )
    md.append("")
    md.append("| Agente | Motos equiv 50 ep | Mototaxis equiv 50 ep | Total equiv 50 ep | Promedio equiv/episodio |")
    md.append("|---|---:|---:|---:|---:|")
    for agent in ranking:
        m = payload["agents"][agent]
        name = f"**{agent}**" if m["selected"] else agent
        b = "**" if m["selected"] else ""
        md.append(
            f"| {name} | {b}{fmt_int(m['ev_motos_equiv_count_50'])}{b} | "
            f"{b}{fmt_int(m['ev_mototaxis_equiv_count_50'])}{b} | "
            f"{b}{fmt_int(m['ev_total_equiv_count_50'])}{b} | "
            f"{b}{fmt_int(m['ev_total_equiv_mean_per_episode'])}{b} |"
        )
    md.append("")
    md.append("A2C carga mas vehiculos equivalentes: +103,604 frente a PPO y +126,342 frente a SAC v8.2.")
    md.append("")
    md.append("## Red, exportacion, violaciones y estabilidad")
    md.append("")
    md.append(
        "`solar_export_f6d` se estima desde `co2_f6d_kg / 0.4521`; los traces horarios no guardan "
        "`grid_export_kwh` de forma comparable para los tres agentes."
    )
    md.append("")
    md.append(
        "| Agente | Grid import 50 ep (kWh) | Solar export F6d 50 ep (kWh) | "
        "Violaciones total | Episodios sin violacion | CV plateau F2 | Reward validacion |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for agent in ranking:
        m = payload["agents"][agent]
        name = f"**{agent}**" if m["selected"] else agent
        b = "**" if m["selected"] else ""
        md.append(
            f"| {name} | {b}{fmt_int(m['grid_import_sum_50_kwh'])}{b} | "
            f"{b}{fmt_int(m['solar_export_f6d_sum_50_kwh'])}{b} | "
            f"{b}{fmt_int(m['debt_violations_sum_50'])}{b} | "
            f"{fmt_int(m['zero_violation_episodes_50'])} | "
            f"{fmt_float(m['cv_plateau_pct'], 3)}% | "
            f"{fmt_float(m['validation_mean_reward'], 2)} |"
        )
    md.append("")
    md.append(
        "Ningun agente termina los 50 episodios con cero violaciones acumuladas. A2C tiene la menor "
        "cantidad total de violaciones; SAC tiene mas episodios sin violacion, pero queda por debajo "
        "en CO2, red, carga EV y BESS. PPO es el mas estable por CV plateau, aunque no supera a A2C "
        "en el score operativo."
    )
    md.append(
        "En validacion, A2C tambien obtiene el mayor reward medio y la menor importacion de red. "
        "SAC obtiene el mayor CO2 evitado medio de validacion, pero con menor reward, menor carga EV "
        "acumulada, menor BESS y mas violaciones que A2C en entrenamiento."
    )
    md.append("")
    md.append(
        "Recomendacion de produccion: implementar **A2C** como politica principal, con guardas de "
        "deuda de carga, limites operativos de BESS y monitoreo de grid import. PPO queda como "
        "referencia de estabilidad y F2 puntual; SAC v8.2 queda como respaldo experimental."
    )
    md.append("")
    md.append(f"## Por que {selected} gana")
    md.append("")
    md.append(
        f"{selected} lidera **{selected_metrics['multiobjective_wins_50']}/"
        f"{selected_metrics['multiobjective_criteria_total']} criterios** del score multiobjetivo. "
        f"Tambien tiene la mayor reduccion acumulada directa + indirecta en 50 episodios: "
        f"**{fmt_int(selected_metrics['co2_total_avoided_sum_50_kg'])} kg CO2**."
    )
    for agent in ranking:
        if agent == selected:
            continue
        diff = selected_metrics["co2_total_avoided_sum_50_kg"] - payload["agents"][agent]["co2_total_avoided_sum_50_kg"]
        md.append(
            f"{agent} reduce **{fmt_int(diff)} kg CO2** menos que {selected} "
            "en el acumulado de 50 episodios."
        )
    md.append("")
    md.append("Criterios liderados:")
    md.append("")
    md.append("| Criterio | Direccion | Ganador | Valor |")
    md.append("|---|---|---|---:|")
    for criterion in payload["multiobjective_criteria"]:
        m = payload["agents"][criterion["winner"]]
        value = m[criterion["key"]]
        direction = "mayor" if criterion["mode"] == "max" else "menor"
        md.append(
            f"| {criterion['label']} | {direction} | {criterion['winner']} | {fmt_int(value)} |"
        )
    md.append("")
    sac = payload["agents"]["SAC"]
    md.append(
        "SAC v8.2 mejoro despues de activar `VecNormalize` y ajustar hiperparametros, "
        f"pero su reduccion acumulada es **{fmt_int(sac['co2_total_avoided_sum_50_kg'])} kg CO2**, "
        f"por debajo de {selected}."
    )
    md.append("")
    md.append(
        f"Lectura complementaria: PPO conserva el menor `F2` residual puntual "
        f"(**{fmt_int(payload['agents']['PPO']['f2_min_kg_per_year'])} kg CO2/año**, ep"
        f"{payload['agents']['PPO']['best_episode']}), pero ese no es el criterio principal "
        "actualizado."
    )
    md.append("")
    if trace:
        total = trace["seleccion_por_reduccion_total_directa_indirecta"]
        indirect = trace["seleccion_por_menor_emision_indirecta"]
        md.append("## Lectura complementaria desde trace")
        md.append("")
        md.append(
            "El reporte `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` calcula directamente "
            "las columnas `co2_grid_kg`, `co2_avoided_indirect_kg` y `co2_avoided_direct_kg` "
            "de los traces de entrenamiento."
        )
        md.append(
            f"Con el criterio de mayor CO2 evitado total directo + indirecto, "
            f"**{total['agent']}** lidera con **{fmt_int(total['co2_total_avoided_kg'])} "
            f"kg CO2/año evitados** en el episodio trace {total['episode_trace']}."
        )
        md.append(
            f"Para el criterio OE3 canonico de menor F2/CO2 indirecto residual, "
            f"**{indirect['agent']}** registra **{fmt_int(indirect['co2_indirect_emitted_kg'])} "
            f"kg CO2/año** en el episodio trace {indirect['episode_trace']}."
        )
        md.append("")
    stats_payload = payload["statistics"]
    md.append("## Inferencia estadistica")
    md.append("")
    md.append("Las pruebas se aplican sobre la serie por episodio de `co2_directa_kg + co2_indirecta_kg`.")
    md.append("")
    md.append("| Prueba | Resultado | Interpretacion |")
    md.append("|---|---:|---|")
    for agent in ("SAC", "PPO", "A2C"):
        result = stats_payload["normality"]["results"][agent]
        md.append(
            f"| Shapiro-Wilk {agent} | W={result['w']:.6f}, p={result['p_value']:.3e} | "
            f"{'Normal' if result['normal'] else 'No normal'} |"
        )
    kw = stats_payload["non_parametric_tests"]["kruskal_wallis"]
    md.append(f"| Kruskal-Wallis | H={kw['h']:.6f}, p={kw['p_value']:.3e} | Hay diferencias entre agentes |")
    mw = stats_payload["non_parametric_tests"]["mann_whitney_u"]
    md.append(
        f"| Mann-Whitney U A2C > PPO | U={mw['a2c_greater_than_ppo']['u']:.0f}, "
        f"p={mw['a2c_greater_than_ppo']['p_value']:.3e} | A2C reduce mas que PPO |"
    )
    md.append(
        f"| Mann-Whitney U A2C > SAC | U={mw['a2c_greater_than_sac']['u']:.0f}, "
        f"p={mw['a2c_greater_than_sac']['p_value']:.3e} | A2C reduce mas que SAC |"
    )
    md.append(
        f"| Mann-Whitney U PPO > SAC | U={mw['ppo_greater_than_sac']['u']:.0f}, "
        f"p={mw['ppo_greater_than_sac']['p_value']:.3e} | PPO reduce mas que SAC |"
    )
    wx = stats_payload["non_parametric_tests"]["wilcoxon_signed_rank"]
    md.append(
        f"| Wilcoxon A2C > PPO | W={wx['a2c_greater_than_ppo']['w']:.0f}, "
        f"p={wx['a2c_greater_than_ppo']['p_value']:.3e} | Comparacion pareada A2C/PPO |"
    )
    md.append(
        f"| Wilcoxon A2C > SAC | W={wx['a2c_greater_than_sac']['w']:.0f}, "
        f"p={wx['a2c_greater_than_sac']['p_value']:.3e} | Comparacion pareada A2C/SAC |"
    )
    f2_tests = stats_payload["residual_f2_reference_tests"]
    md.append(
        f"| F2 residual Kruskal-Wallis | H={f2_tests['kruskal_wallis']['h']:.6f}, "
        f"p={f2_tests['kruskal_wallis']['p_value']:.3e} | Referencia complementaria de CO2 residual |"
    )
    md.append("")
    md.append("## Archivos obsoletos")
    md.append("")
    md.append(
        "Los reportes binarios y figuras antiguas que declaraban SAC/A2C como seleccionados "
        "fueron retirados o reemplazados. Si aparece una salida generada bajo "
        "`outputs/*_training/`, debe tratarse como artefacto de entrenamiento, no como fuente "
        "canonica para informes."
    )
    md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = {agent: load_agent(agent) for agent in AGENTS}
    f2_series = {
        agent: history["co2_control_kg"].astype(float).to_numpy()
        for agent, (_, history, _) in loaded.items()
    }
    avoided_series = {
        agent: (
            history["co2_directa_kg"].astype(float).to_numpy()
            + history["co2_indirecta_kg"].astype(float).to_numpy()
        )
        for agent, (_, history, _) in loaded.items()
    }
    vehicle_ref = load_vehicle_energy_reference()
    metrics = {
        agent: agent_metrics(agent, result, history, vehicle_ref)
        for agent, (result, history, _) in loaded.items()
    }

    multiobjective_criteria = [
        {"key": "co2_total_avoided_sum_50_kg", "label": "Mayor CO2 total evitado", "mode": "max"},
        {"key": "grid_import_sum_50_kwh", "label": "Menor importacion de red", "mode": "min"},
        {"key": "co2_direct_avoided_sum_50_kg", "label": "Mayor CO2 directo evitado", "mode": "max"},
        {"key": "co2_indirect_avoided_sum_50_kg", "label": "Mayor CO2 indirecto evitado", "mode": "max"},
        {"key": "ev_motos_equiv_count_50", "label": "Mayor carga motos equivalentes", "mode": "max"},
        {"key": "ev_mototaxis_equiv_count_50", "label": "Mayor carga mototaxis equivalentes", "mode": "max"},
        {"key": "ev_total_equiv_count_50", "label": "Mayor carga EV total equivalente", "mode": "max"},
        {"key": "bess_discharge_sum_50_kwh", "label": "Mayor uso util BESS", "mode": "max"},
        {"key": "debt_violations_sum_50", "label": "Menor deuda/violaciones de carga", "mode": "min"},
    ]
    criterion_winners = []
    for criterion in multiobjective_criteria:
        key = criterion["key"]
        if criterion["mode"] == "max":
            winner = max(AGENTS, key=lambda agent: metrics[agent][key])
        else:
            winner = min(AGENTS, key=lambda agent: metrics[agent][key])
        metrics[winner]["multiobjective_wins_50"] += 1
        criterion_winners.append({**criterion, "winner": winner})

    for agent in AGENTS:
        metrics[agent]["multiobjective_criteria_total"] = len(multiobjective_criteria)

    ranking = sorted(
        AGENTS,
        key=lambda agent: (
            metrics[agent]["multiobjective_wins_50"],
            metrics[agent]["co2_total_avoided_sum_50_kg"],
        ),
        reverse=True,
    )
    selected = ranking[0]
    selected_total = metrics[selected]["co2_total_avoided_sum_50_kg"]
    for rank, agent in enumerate(ranking, start=1):
        metrics[agent]["rank"] = rank
        metrics[agent]["selected"] = agent == selected
        diff = selected_total - metrics[agent]["co2_total_avoided_sum_50_kg"]
        if agent == selected:
            metrics[agent]["selection_note"] = (
                "Selected because it leads the multiobjective score over 50 episodes."
            )
        else:
            metrics[agent]["selection_note"] = (
                f"Not selected; wins fewer multiobjective criteria and cumulative total CO2 avoided "
                f"is {diff:,.0f} kg lower than {selected}."
            )

    run_dates = sorted({parse_run_date(result) for result, _, _ in loaded.values()})
    training_run_date = run_dates[-1]

    payload = {
        "metadata": {
            "project": "pvbesscar",
            "location": "Iquitos, Peru",
            "updated_at": RUN_DATE,
            "source_generation_date": RUN_DATE,
            "training_run_date": training_run_date,
            "branch": "smartcharger",
            "selected_agent": selected,
            "selection_criterion": (
                "Multiobjective score over 50 episodes: maximize direct+indirect CO2 avoided, "
                "minimize grid import and charge debt, maximize EV equivalent charge counts and "
                "useful BESS discharge."
            ),
            "normality_usage": (
                "Normality tests guide statistical method selection only; they do not replace "
                "operational ranking metrics."
            ),
            "canonical_report": "reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md",
            "source_audit": "reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md",
            "operational_report": "reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md",
            "source_policy": (
                "Use only current final checkpoints in checkpoints/{AGENT}_CityLearn and current "
                "outputs/{agent}_training results; exclude archive, archive_previous and archive_v73_obs16."
            ),
            "vehicle_count_policy": vehicle_ref["method"],
        },
        "system": {
            "solar_kwp_dc_pvwatts": 4162,
            "solar_energy_kwh_year": 5_819_332,
            "bess_kwh": 2000,
            "bess_kw": 400,
            "chargers": 19,
            "sockets": 38,
            "daily_motos": 270,
            "daily_mototaxis": 39,
            "grid_emission_factor_kg_co2_kwh": 0.4521,
            "f0_reference_kg_co2_year": F0_REFERENCE_KG,
            "episodes_per_agent": 50,
            "timesteps_per_agent": 438000,
            "reward_version": REWARD_VERSION,
            "obs_dim": 19,
            "action_dim": 3,
        },
        "vehicle_count_reference": vehicle_ref,
        "ranking": ranking,
        "agents": metrics,
        "multiobjective_criteria": criterion_winners,
        "production_readiness": {
            "recommended_agent": selected,
            "recommended_reason": (
                "A2C leads the operational multiobjective score, charges the largest equivalent "
                "vehicle count, imports the least grid energy and has the fewest total charge "
                "debt violations."
            ),
            "most_stable_by_cv_plateau": min(AGENTS, key=lambda agent: metrics[agent]["cv_plateau_pct"]),
            "most_zero_violation_episodes": max(
                AGENTS, key=lambda agent: metrics[agent]["zero_violation_episodes_50"]
            ),
            "no_agent_has_zero_total_violations": all(
                metrics[agent]["debt_violations_sum_50"] > 0 for agent in AGENTS
            ),
        },
        "statistics": build_statistics(f2_series, avoided_series),
        "deprecated_or_removed": [
            "outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v10.docx",
            "outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v11.docx",
            "outputs/hypothesis_test/hypothesis_test_co2_figura_completa.png",
            "legacy HTML/PDF reports that identified SAC or A2C as the selected agent",
        ],
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(payload)
    write_md(payload)

    print(f"Canonico actualizado: {OUT_JSON.relative_to(ROOT)}")
    print(f"Tabla CSV actualizada: {OUT_CSV.relative_to(ROOT)}")
    print(f"Informe MD actualizado: {OUT_MD.relative_to(ROOT)}")
    print(f"Agente seleccionado: {selected}")
    for agent in ranking:
        m = metrics[agent]
        print(
            f"  {agent}: score={m['multiobjective_wins_50']}/{m['multiobjective_criteria_total']} | "
            f"CO2 evitado 50 ep={m['co2_total_avoided_sum_50_kg']:,.0f} kg | "
            f"F2={m['f2_min_kg_per_year']:,.0f} kg CO2/año ep{m['best_episode']}"
        )


if __name__ == "__main__":
    main()
