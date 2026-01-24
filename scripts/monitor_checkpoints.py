#!/usr/bin/env python3
"""Monitor checkpoints del entrenamiento RL."""

import os
import time
from datetime import datetime
from pathlib import Path


def resolve_checkpoint_dir() -> Path:
    """Resolve checkpoint directory for container or host execution."""
    env_dir = os.environ.get("CHECKPOINT_DIR")
    if env_dir:
        return Path(env_dir)

    in_container = Path("/.dockerenv").exists()
    base_root = Path("/app") if in_container else Path(__file__).resolve().parent.parent
    return base_root / "outputs" / "oe3" / "checkpoints"


def format_header(checkpoint_dir: Path) -> str:
    """Create monitor header text."""
    header_lines = [
        "==============================",
        " MONITOR DE CHECKPOINTS (RL) ",
        "==============================",
        f"Directorio: {checkpoint_dir}",
        "",
    ]
    return "\n".join(header_lines)


def main() -> None:
    """Run checkpoint monitor loop."""
    checkpoint_dir = resolve_checkpoint_dir()
    agents = ["SAC", "PPO", "A2C"]

    while True:
        os.system("clear" if os.name != "nt" else "cls")
        print(format_header(checkpoint_dir))
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitoreo Checkpoints RL\n")

        for agent in agents:
            agent_dir = checkpoint_dir / agent
            print(f"Agente: {agent}")

            if not agent_dir.exists():
                print("   Pendiente - directorio no creado\n")
                continue

            checkpoints = sorted(agent_dir.glob(f"{agent}_step_*.zip"))
            final_ckpt = agent_dir / f"{agent}_final.zip"

            if checkpoints:
                latest = checkpoints[-1]
                size_mb = latest.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(latest.stat().st_mtime)
                step = int(latest.stem.split("_")[-1])

                print(f"   Ultimo checkpoint: Step {step}")
                print(f"   Tamano: {size_mb:.2f} MB")
                print(f"   Modificado: {mod_time.strftime('%H:%M:%S')}")
                print(f"   Total checkpoints: {len(checkpoints)}")

            if final_ckpt.exists():
                size_mb = final_ckpt.stat().st_size / (1024 * 1024)
                print(f"   Checkpoint FINAL guardado: {size_mb:.2f} MB")

            print()

        print("-" * 60)
        print("Presiona Ctrl+C para salir | Actualizando cada 5 segundos...")

        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nMonitor detenido")
            break


if __name__ == "__main__":
    main()
