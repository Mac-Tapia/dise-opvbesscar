#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audita que OE3 use checkpoints y resultados vigentes.

La auditoria valida:
- `outputs/{agent}_training/result_{agent}.json`
- `checkpoints/{AGENT}_CityLearn/{agent}_final.zip`
- `outputs/{agent}_training/trace_{agent}.csv`
- `outputs/{agent}_training/{agent}_convergencia_episodios.csv`
- `outputs/{agent}_training/{agent}_episodios_history.csv`

No se aceptan rutas bajo `archive`, `archive_previous` ni `archive_v73_obs16`.
"""

from __future__ import annotations

import json
from datetime import date
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "oe3"
OUT_MD = OUT_DIR / "AUDITORIA_FUENTES_CHECKPOINTS_OE3.md"
OUT_JSON = OUT_DIR / "AUDITORIA_FUENTES_CHECKPOINTS_OE3.json"
AGENTS = ("sac", "ppo", "a2c")
ARCHIVE_MARKERS = {"archive", "archive_previous", "archive_v73_obs16"}
RUN_DATE = date.today().isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def has_archive_marker(path: Path) -> bool:
    lowered = {part.lower() for part in path.parts}
    return bool(lowered & ARCHIVE_MARKERS)


def file_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": stat.st_size,
        "last_write_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "uses_archive_path": has_archive_marker(path),
    }


def count_rows(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8")) - 1


def audit_agent(agent: str) -> dict:
    upper = agent.upper()
    result_path = ROOT / "outputs" / f"{agent}_training" / f"result_{agent}.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    output_files = result.get("output_files", {})

    expected_model = ROOT / "checkpoints" / f"{upper}_CityLearn" / f"{agent}_final.zip"
    model_path = Path(output_files.get("model", expected_model))
    trace_path = Path(output_files.get("trace", ROOT / "outputs" / f"{agent}_training" / f"trace_{agent}.csv"))
    convergence_path = ROOT / "outputs" / f"{agent}_training" / f"{agent}_convergencia_episodios.csv"
    episodes_path = ROOT / "outputs" / f"{agent}_training" / f"{agent}_episodios_history.csv"

    # Paths stored in JSON are absolute Windows paths. Normalize them against ROOT only for reporting.
    paths = {
        "result": result_path,
        "model": model_path,
        "expected_model": expected_model,
        "trace": trace_path,
        "convergence": convergence_path,
        "episodes_history": episodes_path,
    }
    for label, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"{upper}: falta {label}: {path}")
        if has_archive_marker(path):
            raise ValueError(f"{upper}: ruta archivada no permitida en {label}: {path}")

    if model_path.resolve() != expected_model.resolve():
        raise ValueError(
            f"{upper}: result JSON apunta a modelo distinto. "
            f"model={model_path}, esperado={expected_model}"
        )

    trace_rows = count_rows(trace_path)
    convergence_rows = count_rows(convergence_path)
    episodes_rows = count_rows(episodes_path)
    full_trace_episodes = trace_rows // 8760
    ignored_trace_rows = trace_rows - full_trace_episodes * 8760

    return {
        "agent": upper,
        "timestamp": result.get("timestamp"),
        "training": {
            "total_timesteps": result.get("training", {}).get("total_timesteps"),
            "episodes_completed": result.get("training", {}).get("episodes_completed"),
            "duration_seconds": result.get("training", {}).get("duration_seconds"),
            "speed_steps_per_second": result.get("training", {}).get("speed_steps_per_second"),
            "device": result.get("training", {}).get("device"),
        },
        "validation": result.get("validation", {}),
        "files": {label: file_info(path) for label, path in paths.items()},
        "row_counts": {
            "trace_rows": trace_rows,
            "trace_full_episodes": full_trace_episodes,
            "trace_rows_ignored_partial": ignored_trace_rows,
            "convergence_rows": convergence_rows,
            "episodes_history_rows": episodes_rows,
        },
        "source_valid": True,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audits = [audit_agent(agent) for agent in AGENTS]
    seccion52 = json.loads(
        (ROOT / "outputs" / "seccion52" / "resultados_seccion52.json").read_text(
            encoding="utf-8"
        )
    )["algoritmos"]
    trace_summary = pd.read_csv(OUT_DIR / "co2_trace_direct_indirect_summary.csv")

    payload = {
        "fecha_actualizacion": RUN_DATE,
        "politica_fuentes": {
            "usar": [
                "checkpoints/{AGENT}_CityLearn/{agent}_final.zip",
                "outputs/{agent}_training/result_{agent}.json",
                "outputs/{agent}_training/trace_{agent}.csv",
                "outputs/{agent}_training/{agent}_convergencia_episodios.csv",
                "outputs/{agent}_training/{agent}_episodios_history.csv",
            ],
            "excluir": sorted(ARCHIVE_MARKERS),
        },
        "auditoria": audits,
        "resultado_guardado_actual": seccion52,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines: list[str] = []
    lines.append("# OE3 - Auditoria de fuentes, checkpoints y resultados")
    lines.append("")
    lines.append(f"**Fecha de actualizacion:** {RUN_DATE}")
    lines.append("")
    lines.append("## Politica de fuentes")
    lines.append("")
    lines.append("Se aceptan solo rutas vigentes de entrenamiento y checkpoints finales:")
    lines.append("")
    lines.append("- `checkpoints/{AGENT}_CityLearn/{agent}_final.zip`")
    lines.append("- `outputs/{agent}_training/result_{agent}.json`")
    lines.append("- `outputs/{agent}_training/trace_{agent}.csv`")
    lines.append("- `outputs/{agent}_training/{agent}_convergencia_episodios.csv`")
    lines.append("- `outputs/{agent}_training/{agent}_episodios_history.csv`")
    lines.append("")
    lines.append("No se usan rutas bajo `archive`, `archive_previous` ni `archive_v73_obs16`.")
    lines.append("")
    lines.append("## Checkpoints y resultados auditados")
    lines.append("")
    lines.append(
        "| Agente | Timestamp result | Checkpoint final | Result JSON | Trace filas | "
        "Episodios trace completos | Filas parciales ignoradas | Estado |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---|")
    for item in audits:
        model = item["files"]["model"]["path"]
        result = item["files"]["result"]["path"]
        rows = item["row_counts"]
        lines.append(
            f"| {item['agent']} | {item['timestamp']} | `{model}` | `{result}` | "
            f"{rows['trace_rows']:,} | {rows['trace_full_episodes']} | "
            f"{rows['trace_rows_ignored_partial']:,} | vigente/no archive |"
        )
    lines.append("")
    lines.append("## Resultado guardado vigente")
    lines.append("")
    lines.append(
        "| Agente | F2 minimo | Episodio F2 | CO2 evitado vs F0 | CV plateau | "
        "Reward validacion | Grid validacion |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for item in audits:
        agent = item["agent"]
        result = seccion52[agent]
        validation = item["validation"]
        lines.append(
            f"| {agent} | {result['f2_minimo_kg']:,.0f} | {result['f2_minimo_ep']} | "
            f"{result['co2_evitado_kg']:,.0f} | {result['cv_plateau_pct']:.3f}% | "
            f"{validation['mean_reward']:,.2f} | {validation['mean_grid_import_kwh']:,.0f} |"
        )
    lines.append("")
    lines.append("## Lectura trace complementaria")
    lines.append("")
    lines.append(
        "| Criterio trace | SAC | PPO | A2C | Ganador parcial |"
    )
    lines.append("|---|---:|---:|---:|---|")
    for criterion, label, column in [
        ("max_total_avoided", "CO2 total evitado maximo", "co2_total_avoided_kg"),
        ("max_direct_avoided", "CO2 directo evitado maximo", "co2_direct_avoided_kg"),
        ("max_indirect_avoided", "CO2 indirecto evitado maximo", "co2_indirect_avoided_kg"),
        ("min_indirect_emitted", "CO2 indirecto residual minimo", "co2_indirect_emitted_kg"),
    ]:
        rows = {
            row.agent: row
            for row in trace_summary[trace_summary["criterion"] == criterion].itertuples()
        }
        maximize = not criterion.startswith("min_")
        winner = max(rows, key=lambda a: getattr(rows[a], column)) if maximize else min(
            rows, key=lambda a: getattr(rows[a], column)
        )
        lines.append(
            f"| {label} | {getattr(rows['SAC'], column):,.0f} | "
            f"{getattr(rows['PPO'], column):,.0f} | {getattr(rows['A2C'], column):,.0f} | "
            f"{winner} |"
        )
    lines.append("")
    lines.append("## Conclusion de auditoria")
    lines.append("")
    lines.append(
        "El SAC auditado corresponde al checkpoint final vigente `checkpoints/SAC_CityLearn/sac_final.zip`; "
        "no se usaron checkpoints antiguos ni archivos archivados. SAC fue comparado con PPO y A2C, "
        "y aunque SAC v8.2 mejora la importacion de red de validacion frente a PPO, todavia queda "
        "por debajo en F2 minimo, CO2 evitado vs F0 y reward de validacion."
    )
    lines.append("")
    lines.append(
        "Para cambiar esta conclusion en una futura corrida, el nuevo SAC debe aparecer como "
        "`outputs/sac_training/result_sac.json`, `checkpoints/SAC_CityLearn/sac_final.zip` y "
        "`checkpoints/SAC_CityLearn/vecnormalize.pkl` fuera de carpetas `archive`."
    )
    lines.append("")
    lines.append(f"- JSON: `{OUT_JSON.relative_to(ROOT).as_posix()}`")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Auditoria generada: {OUT_MD}")
    print(f"JSON generado: {OUT_JSON}")


if __name__ == "__main__":
    main()
