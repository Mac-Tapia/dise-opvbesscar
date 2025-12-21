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
    run([py, "scripts/run_oe2_solar.py", "--config", args.config])
    run([py, "scripts/run_oe2_chargers.py", "--config", args.config])
    run([py, "scripts/run_oe2_bess.py", "--config", args.config])
    run([py, "scripts/run_oe3_build_dataset.py", "--config", args.config])
    run([py, "scripts/run_oe3_simulate.py", "--config", args.config])
    run([py, "scripts/run_oe3_co2_table.py", "--config", args.config])

if __name__ == "__main__":
    main()
