from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd: list[str]) -> None:
    print("\n$", " ".join(cmd))
    subprocess.check_call(cmd)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()

    py = sys.executable
    run([py, "-m", "scripts.run_oe2_solar", "--config", args.config])
    run([py, "-m", "scripts.run_oe2_chargers", "--config", args.config])
    run([py, "-m", "scripts.run_oe1_location", "--config", args.config])
    run([py, "-m", "scripts.run_oe2_bess", "--config", args.config])
    run([py, "-m", "scripts.run_oe3_build_dataset", "--config", args.config])
    run([py, "-m", "scripts.run_oe3_simulate", "--config", args.config])
    run([py, "-m", "scripts.run_oe3_co2_table", "--config", args.config])

if __name__ == "__main__":
    main()
