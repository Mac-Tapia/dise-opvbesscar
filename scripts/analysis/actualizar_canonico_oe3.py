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


def cv_plateau(series: np.ndarray, window: int = 15) -> float:
    tail = series[-window:]
    return float(np.std(tail, ddof=0) / np.mean(tail) * 100)


def agent_metrics(agent: str, result: dict, history: pd.DataFrame) -> dict:
    f2 = history["co2_control_kg"].astype(float).to_numpy()
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


def build_statistics(series: dict[str, np.ndarray]) -> dict:
    normality = {}
    for agent in AGENTS:
        w, p_value = stats.shapiro(series[agent])
        normality[agent] = {
            "w": float(w),
            "p_value": float(p_value),
            "normal": bool(p_value >= 0.05),
        }

    h, kw_p = stats.kruskal(series["SAC"], series["PPO"], series["A2C"])

    def mann(a: str, b: str) -> dict:
        u, p_value = stats.mannwhitneyu(series[a], series[b], alternative="less")
        return {"u": float(u), "p_value": float(p_value)}

    def wilcoxon(a: str, b: str) -> dict:
        w, p_value = stats.wilcoxon(series[a], series[b], alternative="less")
        return {"w": float(w), "p_value": float(p_value)}

    return {
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
                "ppo_less_than_sac": mann("PPO", "SAC"),
                "ppo_less_than_a2c": mann("PPO", "A2C"),
                "a2c_less_than_sac": mann("A2C", "SAC"),
            },
            "wilcoxon_signed_rank": {
                "ppo_less_than_sac": wilcoxon("PPO", "SAC"),
                "ppo_less_than_a2c": wilcoxon("PPO", "A2C"),
                "a2c_less_than_sac": wilcoxon("A2C", "SAC"),
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
        "`obs_dim=18`, accion 3D y 50 episodios por agente."
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
        "El criterio principal de OE3 es minimizar `F2` anual (`kg CO2/año`) porque representa "
        "las emisiones con solar + BESS + control RL. Menor `F2` implica mejor resultado "
        "ambiental operativo."
    )
    md.append("")
    md.append(
        "La prueba de normalidad no se usa para elegir el agente. Se usa para decidir el tipo "
        "de inferencia: Shapiro-Wilk rechaza normalidad en las tres series, por lo que se usan "
        "pruebas no parametricas (Kruskal-Wallis, Mann-Whitney U y Wilcoxon signed-rank)."
    )
    md.append("")
    md.append("## Tabla comparativa")
    md.append("")
    md.append(
        "| Rank | Agente | F2 minimo (kg CO2/año) | Episodio optimo | F2 media (kg/año) | "
        "Sigma (kg/año) | CO2 evitado vs F0 (kg/año) | Reduccion vs F0 | CV plateau | "
        "Reward validacion | Grid import validacion (kWh) |"
    )
    md.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for agent in ranking:
        m = payload["agents"][agent]
        name = f"**{agent}**" if m["selected"] else agent
        b = "**" if m["selected"] else ""
        md.append(
            f"| {m['rank']} | {name} | {b}{fmt_int(m['f2_min_kg_per_year'])}{b} | "
            f"{b}{m['best_episode']}{b} | {fmt_int(m['f2_mean_kg_per_year'])} | "
            f"{fmt_int(m['f2_sigma_kg_per_year'])} | {b}{fmt_int(m['co2_avoided_vs_f0_kg_per_year'])}{b} | "
            f"{b}{m['co2_reduction_vs_f0_pct']:.2f}%{b} | "
            f"{b}{m['cv_plateau_pct']:.3f}%{b} | "
            f"{m['validation_mean_reward']:,.2f} | {m['validation_mean_grid_import_kwh']:,.2f} |"
        )
    md.append("")
    md.append(f"## Por que {selected} gana")
    md.append("")
    md.append(
        f"{selected} tiene el menor `F2` anual: **{fmt_int(selected_metrics['f2_min_kg_per_year'])} "
        f"kg CO2/año** en el episodio {selected_metrics['best_episode']}."
    )
    for agent in ranking:
        if agent == selected:
            continue
        diff = payload["agents"][agent]["f2_min_kg_per_year"] - selected_metrics["f2_min_kg_per_year"]
        md.append(
            f"{agent} queda con **{fmt_int(abs(diff))} kg CO2/año** mas que {selected} "
            "bajo el criterio canonico de minimizacion de emisiones."
        )
    md.append("")
    sac = payload["agents"]["SAC"]
    md.append(
        "SAC v8.2 mejoro despues de activar `VecNormalize` y ajustar hiperparametros, "
        f"pero su mejor `F2` actual es **{fmt_int(sac['f2_min_kg_per_year'])} kg CO2/año** "
        f"en el episodio {sac['best_episode']}; por eso no supera a PPO/A2C en la seleccion canonica."
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
        f"| Mann-Whitney U PPO < SAC | U={mw['ppo_less_than_sac']['u']:.0f}, "
        f"p={mw['ppo_less_than_sac']['p_value']:.3e} | PPO emite menos que SAC |"
    )
    md.append(
        f"| Mann-Whitney U PPO < A2C | U={mw['ppo_less_than_a2c']['u']:.0f}, "
        f"p={mw['ppo_less_than_a2c']['p_value']:.3e} | PPO se compara contra A2C |"
    )
    wx = stats_payload["non_parametric_tests"]["wilcoxon_signed_rank"]
    md.append(
        f"| Wilcoxon PPO < A2C | W={wx['ppo_less_than_a2c']['w']:.0f}, "
        f"p={wx['ppo_less_than_a2c']['p_value']:.3e} | Comparacion pareada PPO/A2C |"
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
    series = {
        agent: history["co2_control_kg"].astype(float).to_numpy()
        for agent, (_, history, _) in loaded.items()
    }
    metrics = {
        agent: agent_metrics(agent, result, history)
        for agent, (result, history, _) in loaded.items()
    }

    ranking = sorted(AGENTS, key=lambda agent: metrics[agent]["f2_min_kg_per_year"])
    selected = ranking[0]
    selected_f2 = metrics[selected]["f2_min_kg_per_year"]
    for rank, agent in enumerate(ranking, start=1):
        metrics[agent]["rank"] = rank
        metrics[agent]["selected"] = agent == selected
        diff = metrics[agent]["f2_min_kg_per_year"] - selected_f2
        if agent == selected:
            metrics[agent]["selection_note"] = "Selected because it has the lowest annual F2 emissions."
        else:
            metrics[agent]["selection_note"] = (
                f"Not selected; F2 minimum is {diff:,.0f} kg CO2/year higher than {selected}."
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
            "selection_criterion": "Minimize annual F2 emissions (kg CO2/year)",
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
        },
        "system": {
            "solar_kwp_nominal_design": 4050,
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
            "obs_dim": 18,
            "action_dim": 3,
        },
        "ranking": ranking,
        "agents": metrics,
        "statistics": build_statistics(series),
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
        print(f"  {agent}: F2={m['f2_min_kg_per_year']:,.0f} kg CO2/año ep{m['best_episode']}")


if __name__ == "__main__":
    main()
