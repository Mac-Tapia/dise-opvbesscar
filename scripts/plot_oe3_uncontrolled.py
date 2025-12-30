from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description="Grafica baseline 'Uncontrolled' (timeseries).")
    ap.add_argument("--csv", default="outputs/oe3/simulations/timeseries_Uncontrolled.csv")
    ap.add_argument("--out", default="analyses/oe3/training/uncontrolled_timeseries.png")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"No se encuentra el CSV baseline: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("CSV vacío, no se genera gráfica.")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    for col in ["grid_import_kwh", "ev_charging_kwh", "building_load_kwh", "pv_generation_kwh"]:
        if col in df.columns:
            ax.plot(df[col].values, label=col)
    ax.set_xlabel("Paso (hora)")
    ax.set_ylabel("Energía (kWh)")
    ax.set_title("Baseline Uncontrolled - Timeseries")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"OK guardado: {out_path}")


if __name__ == "__main__":
    main()
