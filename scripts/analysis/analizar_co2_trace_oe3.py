#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analiza CO2 directo e indirecto desde traces OE3.

El analisis usa directamente los CSV de entrenamiento:

- outputs/sac_training/trace_sac.csv
- outputs/ppo_training/trace_ppo.csv
- outputs/a2c_training/trace_a2c.csv

Los episodios se reconstruyen por bloques de 8760 horas porque algunos traces
guardan una columna episode incompleta o incluyen un episodio parcial final.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[2]
ROWS_PER_EPISODE = 8760
AGENTS = ("sac", "ppo", "a2c")
OUT_DIR = BASE / "reports" / "oe3"
OUT_MD = OUT_DIR / "CO2_DIRECTO_INDIRECTO_TRACE_OE3.md"
OUT_CSV = OUT_DIR / "co2_trace_direct_indirect_summary.csv"
OUT_JSON = OUT_DIR / "co2_trace_direct_indirect_summary.json"


def fmt_num(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def fmt_int(value: float) -> str:
    return f"{value:,.0f}"


def load_episode_summary(agent: str) -> tuple[pd.DataFrame, dict]:
    path = BASE / "outputs" / f"{agent}_training" / f"trace_{agent}.csv"
    df = pd.read_csv(path)
    required = {
        "co2_grid_kg",
        "co2_avoided_indirect_kg",
        "co2_avoided_direct_kg",
        "solar_generation_kwh",
        "ev_charging_kwh",
        "grid_import_kwh",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} no contiene columnas requeridas: {missing}")

    df = df.copy()
    df["episode_trace"] = (np.arange(len(df)) // ROWS_PER_EPISODE) + 1
    df["row_in_episode_trace"] = (np.arange(len(df)) % ROWS_PER_EPISODE) + 1

    grouped = df.groupby("episode_trace").agg(
        rows=("co2_grid_kg", "size"),
        co2_indirect_emitted_kg=("co2_grid_kg", "sum"),
        co2_indirect_avoided_kg=("co2_avoided_indirect_kg", "sum"),
        co2_direct_avoided_kg=("co2_avoided_direct_kg", "sum"),
        solar_generation_kwh=("solar_generation_kwh", "sum"),
        ev_charging_kwh=("ev_charging_kwh", "sum"),
        grid_import_kwh=("grid_import_kwh", "sum"),
        reward_sum=("reward", "sum"),
    )
    grouped = grouped[grouped["rows"] == ROWS_PER_EPISODE].copy()
    grouped["agent"] = agent.upper()
    grouped["episode_trace"] = grouped.index.astype(int)
    grouped["co2_total_avoided_kg"] = (
        grouped["co2_indirect_avoided_kg"] + grouped["co2_direct_avoided_kg"]
    )
    grouped["co2_net_trace_balance_kg"] = (
        grouped["co2_indirect_emitted_kg"] - grouped["co2_total_avoided_kg"]
    )

    quality = {
        "source": str(path.relative_to(BASE)).replace("\\", "/"),
        "rows_total": int(len(df)),
        "episodes_full": int(len(grouped)),
        "rows_ignored_partial_episode": int(len(df) - len(grouped) * ROWS_PER_EPISODE),
        "episode_column_unique_values": int(df["episode"].nunique()) if "episode" in df else None,
        "episode_reconstruction": "bloques secuenciales de 8760 filas",
    }
    return grouped.reset_index(drop=True), quality


def best_row(df: pd.DataFrame, column: str, maximize: bool) -> pd.Series:
    idx = df[column].idxmax() if maximize else df[column].idxmin()
    return df.loc[idx]


def rank_rows(rows: list[pd.Series], column: str, maximize: bool) -> list[pd.Series]:
    return sorted(rows, key=lambda row: row[column], reverse=maximize)


def row_record(row: pd.Series, criterion: str) -> dict:
    return {
        "criterion": criterion,
        "agent": row["agent"],
        "episode_trace": int(row["episode_trace"]),
        "co2_indirect_emitted_kg": float(row["co2_indirect_emitted_kg"]),
        "co2_indirect_avoided_kg": float(row["co2_indirect_avoided_kg"]),
        "co2_direct_avoided_kg": float(row["co2_direct_avoided_kg"]),
        "co2_total_avoided_kg": float(row["co2_total_avoided_kg"]),
        "co2_net_trace_balance_kg": float(row["co2_net_trace_balance_kg"]),
        "grid_import_kwh": float(row["grid_import_kwh"]),
        "ev_charging_kwh": float(row["ev_charging_kwh"]),
        "solar_generation_kwh": float(row["solar_generation_kwh"]),
    }


def md_table(records: list[dict], value_column: str, value_label: str) -> list[str]:
    lines = [
        "| Rank | Agente | Episodio trace | Criterio | Valor criterio | "
        "CO2 total evitado | CO2 ind. evitado | CO2 dir. evitado | CO2 ind. emitido |",
        "|---:|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for rank, item in enumerate(records, start=1):
        lines.append(
            "| "
            f"{rank} | {item['agent']} | {item['episode_trace']} | "
            f"{value_label} | "
            f"{fmt_int(item[value_column])} | "
            f"{fmt_int(item['co2_total_avoided_kg'])} | "
            f"{fmt_int(item['co2_indirect_avoided_kg'])} | "
            f"{fmt_int(item['co2_direct_avoided_kg'])} | "
            f"{fmt_int(item['co2_indirect_emitted_kg'])} |"
        )
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summaries: list[pd.DataFrame] = []
    quality: dict[str, dict] = {}
    for agent in AGENTS:
        summary, info = load_episode_summary(agent)
        summaries.append(summary)
        quality[agent.upper()] = info

    all_episodes = pd.concat(summaries, ignore_index=True)

    best_total = [
        best_row(df, "co2_total_avoided_kg", maximize=True) for df in summaries
    ]
    best_direct = [
        best_row(df, "co2_direct_avoided_kg", maximize=True) for df in summaries
    ]
    best_indirect_avoided = [
        best_row(df, "co2_indirect_avoided_kg", maximize=True) for df in summaries
    ]
    best_indirect_emitted = [
        best_row(df, "co2_indirect_emitted_kg", maximize=False) for df in summaries
    ]
    best_net_balance = [
        best_row(df, "co2_net_trace_balance_kg", maximize=False) for df in summaries
    ]

    rankings = {
        "total_avoided_direct_plus_indirect": [
            row_record(row, "max_total_avoided")
            for row in rank_rows(best_total, "co2_total_avoided_kg", maximize=True)
        ],
        "direct_avoided": [
            row_record(row, "max_direct_avoided")
            for row in rank_rows(best_direct, "co2_direct_avoided_kg", maximize=True)
        ],
        "indirect_avoided": [
            row_record(row, "max_indirect_avoided")
            for row in rank_rows(best_indirect_avoided, "co2_indirect_avoided_kg", maximize=True)
        ],
        "indirect_emitted_min": [
            row_record(row, "min_indirect_emitted")
            for row in rank_rows(best_indirect_emitted, "co2_indirect_emitted_kg", maximize=False)
        ],
        "trace_net_balance_min": [
            row_record(row, "min_trace_net_balance")
            for row in rank_rows(best_net_balance, "co2_net_trace_balance_kg", maximize=False)
        ],
    }

    selected_total = rankings["total_avoided_direct_plus_indirect"][0]
    selected_indirect_emitted = rankings["indirect_emitted_min"][0]
    selected_direct = rankings["direct_avoided"][0]
    selected_indirect_avoided = rankings["indirect_avoided"][0]

    summary_rows = []
    for criterion, records in rankings.items():
        for rank, item in enumerate(records, start=1):
            summary_rows.append({"rank": rank, **item})
    pd.DataFrame(summary_rows).to_csv(OUT_CSV, index=False)

    payload = {
        "fecha_actualizacion": "2026-05-30",
        "fuente": "outputs/*_training/trace_*.csv",
        "metodologia": {
            "episodio_completo_horas": ROWS_PER_EPISODE,
            "episodios_usados_por_agente": 50,
            "episodios_parciales": "ignorados",
            "co2_total_avoided_kg": "co2_avoided_indirect_kg + co2_avoided_direct_kg",
            "co2_net_trace_balance_kg": "co2_grid_kg - co2_total_avoided_kg",
        },
        "quality": quality,
        "seleccion_por_reduccion_total_directa_indirecta": selected_total,
        "seleccion_por_menor_emision_indirecta": selected_indirect_emitted,
        "seleccion_por_mayor_reduccion_directa": selected_direct,
        "seleccion_por_mayor_reduccion_indirecta": selected_indirect_avoided,
        "rankings": rankings,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md: list[str] = []
    md.append("# OE3 - Reporte CO2 directo e indirecto desde trace")
    md.append("")
    md.append("**Fecha de actualizacion:** 2026-05-30")
    md.append("**Fuente:** `outputs/*_training/trace_*.csv`")
    md.append("")
    md.append("## Decision")
    md.append("")
    md.append(
        f"Segun el criterio de **mayor CO2 evitado total** "
        f"(`co2_avoided_indirect_kg + co2_avoided_direct_kg`), "
        f"el mejor agente es **{selected_total['agent']}** en el episodio trace "
        f"**{selected_total['episode_trace']}**, con "
        f"**{fmt_int(selected_total['co2_total_avoided_kg'])} kg CO2/año evitados**."
    )
    md.append("")
    md.append(
        f"Si el criterio es **menor CO2 indirecto emitido por importacion de red** "
        f"(`co2_grid_kg`), el mejor agente sigue siendo "
        f"**{selected_indirect_emitted['agent']}**, episodio trace "
        f"**{selected_indirect_emitted['episode_trace']}**, con "
        f"**{fmt_int(selected_indirect_emitted['co2_indirect_emitted_kg'])} kg CO2/año**."
    )
    md.append("")
    md.append("## Metodologia")
    md.append("")
    md.append("- Se reconstruyeron episodios por bloques de 8760 horas.")
    md.append("- Se usaron solo episodios completos; los episodios parciales finales se ignoraron.")
    md.append("- `co2_grid_kg` se interpreta como CO2 indirecto emitido por red electrica.")
    md.append("- `co2_avoided_indirect_kg` se interpreta como CO2 indirecto evitado.")
    md.append("- `co2_avoided_direct_kg` se interpreta como CO2 directo evitado.")
    md.append("- `co2_total_avoided_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg`.")
    md.append("")
    md.append("## Ranking por CO2 evitado total")
    md.append("")
    md.extend(
        md_table(
            rankings["total_avoided_direct_plus_indirect"],
            "co2_total_avoided_kg",
            "CO2 total evitado",
        )
    )
    md.append("")
    md.append("## Ranking por CO2 directo evitado")
    md.append("")
    md.extend(
        md_table(
            rankings["direct_avoided"],
            "co2_direct_avoided_kg",
            "CO2 dir. evitado",
        )
    )
    md.append("")
    md.append("## Ranking por CO2 indirecto evitado")
    md.append("")
    md.extend(
        md_table(
            rankings["indirect_avoided"],
            "co2_indirect_avoided_kg",
            "CO2 ind. evitado",
        )
    )
    md.append("")
    md.append("## Ranking por menor CO2 indirecto emitido")
    md.append("")
    md.extend(
        md_table(
            rankings["indirect_emitted_min"],
            "co2_indirect_emitted_kg",
            "CO2 ind. emitido",
        )
    )
    md.append("")
    md.append("## Calidad de datos trace")
    md.append("")
    md.append("| Agente | Filas totales | Episodios completos | Filas ignoradas | Observacion |")
    md.append("|---|---:|---:|---:|---|")
    for agent in ("SAC", "PPO", "A2C"):
        info = quality[agent]
        note = "OK"
        if info["rows_ignored_partial_episode"]:
            note = "se ignoro episodio parcial final"
        if agent == "A2C":
            note = "columna episode no incrementa; episodios reconstruidos"
        md.append(
            f"| {agent} | {info['rows_total']:,} | {info['episodes_full']} | "
            f"{info['rows_ignored_partial_episode']:,} | {note} |"
        )
    md.append("")
    md.append("## Conclusiones")
    md.append("")
    md.append(
        f"- Para reduccion combinada directa + indirecta desde trace, "
        f"**{selected_total['agent']}** es el mejor agente."
    )
    md.append(
        f"- Para CO2 directo evitado aislado, **{selected_direct['agent']}** lidera con "
        f"{fmt_int(selected_direct['co2_direct_avoided_kg'])} kg CO2/año."
    )
    md.append(
        f"- Para CO2 indirecto evitado aislado, **{selected_indirect_avoided['agent']}** lidera con "
        f"{fmt_int(selected_indirect_avoided['co2_indirect_avoided_kg'])} kg CO2/año."
    )
    md.append(
        f"- Para el criterio F2/CO2 indirecto residual minimo, **{selected_indirect_emitted['agent']}** "
        f"se mantiene como mejor agente."
    )
    md.append("")
    md.append("## Archivos generados")
    md.append("")
    md.append(f"- `{OUT_MD.relative_to(BASE).as_posix()}`")
    md.append(f"- `{OUT_CSV.relative_to(BASE).as_posix()}`")
    md.append(f"- `{OUT_JSON.relative_to(BASE).as_posix()}`")
    md.append("")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"Reporte generado: {OUT_MD}")
    print(f"CSV generado: {OUT_CSV}")
    print(f"JSON generado: {OUT_JSON}")
    print(
        "Mejor por CO2 evitado total: "
        f"{selected_total['agent']} ep {selected_total['episode_trace']} "
        f"({fmt_int(selected_total['co2_total_avoided_kg'])} kg CO2/año)"
    )
    print(
        "Mejor por menor CO2 indirecto emitido: "
        f"{selected_indirect_emitted['agent']} ep {selected_indirect_emitted['episode_trace']} "
        f"({fmt_int(selected_indirect_emitted['co2_indirect_emitted_kg'])} kg CO2/año)"
    )


if __name__ == "__main__":
    main()
