from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _ensure_repo_venv(repo_root: Path) -> None:
    """Evita ejecutar el pipeline con el Python global en lugar de la venv."""
    exe = Path(sys.executable).resolve()
    venv_candidates = [
        repo_root / ".venv" / "Scripts" / "python.exe",  # Windows
        repo_root / ".venv" / "bin" / "python",          # *nix
    ]
    expected = next((p for p in venv_candidates if p.exists()), None)
    if expected and exe != expected:
        print(f"[ABORT] Usa la venv: {expected} (actual: {exe})")
        sys.exit(1)


def run(cmd: list[str]) -> None:
    print("\n$", " ".join(cmd))
    subprocess.check_call(cmd)

def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    _ensure_repo_venv(repo_root)

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
