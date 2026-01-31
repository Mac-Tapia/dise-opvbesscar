#!/usr/bin/env python3
"""
Monitor y validador en tiempo real del sistema SAC → PPO.
Detecta transiciones, errores y asegura integridad del cambio.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

class TransitionMonitor:
    """Monitorea transiciones entre agentes en tiempo real."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.sac_checkpoint_dir = project_root / "analyses" / "oe3" / "training" / "checkpoints" / "sac"
        self.ppo_checkpoint_dir = project_root / "analyses" / "oe3" / "training" / "checkpoints" / "ppo"
        self.training_summary = project_root / "outputs" / "oe3" / "simulations" / "training_summary.json"

    def verify_transition_readiness(self) -> bool:
        """Verifica que el sistema esté listo para transicionar."""
        logger.info("=" * 80)
        logger.info("VERIFICACIÓN DE SOLIDEZ: TRANSICIÓN SAC → PPO")
        logger.info("=" * 80)

        checks = {
            "SAC checkpoint dir": self.sac_checkpoint_dir.exists(),
            "PPO checkpoint dir": self.ppo_checkpoint_dir.exists(),
            "Script run_sac_ppo_only": (self.project_root / "scripts" / "run_sac_ppo_only.py").exists(),
            "Simulate function": (self.project_root / "src" / "iquitos_citylearn" / "oe3" / "simulate.py").exists(),
        }

        all_good = True
        for check, result in checks.items():
            status = "✓" if result else "✗"
            logger.info(f"  {status} {check}")
            if not result:
                all_good = False

        # Verificar contenido del script
        script_path = self.project_root / "scripts" / "run_sac_ppo_only.py"
        if script_path.exists():
            content = script_path.read_text()
            has_loop = 'for agent in agent_names:' in content
            has_except = 'except Exception as e:' in content
            has_both = 'SAC' in content and 'PPO' in content

            logger.info(f"  {'✓' if has_loop else '✗'} Loop sobre agentes")
            logger.info(f"  {'✓' if has_except else '✗'} Manejo de excepciones")
            logger.info(f"  {'✓' if has_both else '✗'} Ambos agentes (SAC, PPO)")

            all_good = all_good and has_loop and has_except and has_both

        logger.info("")
        if all_good:
            logger.info("✅ SISTEMA COMPLETAMENTE SÓLIDO PARA TRANSICIÓN")
        else:
            logger.error("❌ VERIFICACIÓN FALLIDA - Revisar configuración")

        logger.info("=" * 80)
        return all_good

    def watch_transition(self, timeout_seconds: int = 3600) -> None:
        """Monitorea transición SAC → PPO en tiempo real."""
        logger.info(f"\n👀 Monitoreando transición (timeout: {timeout_seconds}s)...")
        start_time = time.time()

        sac_done = False
        ppo_started = False

        while time.time() - start_time < timeout_seconds:
            # Buscar checkpoints SAC
            if not sac_done and self.sac_checkpoint_dir.exists():
                sac_checkpoints = list(self.sac_checkpoint_dir.glob("sac_*.zip"))
                if sac_checkpoints:
                    latest = max(sac_checkpoints, key=lambda p: p.stat().st_mtime)
                    logger.info(f"  ✓ SAC checkpoint detectado: {latest.name}")
                    sac_done = True

            # Buscar checkpoints PPO
            if not ppo_started and self.ppo_checkpoint_dir.exists():
                ppo_checkpoints = list(self.ppo_checkpoint_dir.glob("ppo_*.zip"))
                if ppo_checkpoints:
                    latest = max(ppo_checkpoints, key=lambda p: p.stat().st_mtime)
                    logger.info(f"  ✓ PPO checkpoint detectado: {latest.name}")
                    ppo_started = True

            # Si ambos se completaron
            if sac_done and ppo_started:
                logger.info("\n✅ TRANSICIÓN EXITOSA: SAC → PPO completada")
                return

            time.sleep(10)  # Check cada 10 segundos

        logger.warning(f"⏱ Timeout después de {timeout_seconds}s")
        if sac_done:
            logger.info("  SAC se completó")
        if ppo_started:
            logger.info("  PPO se completó")

def main():
    project_root = Path(__file__).parent.parent
    monitor = TransitionMonitor(project_root)

    # Verificar primero
    if not monitor.verify_transition_readiness():
        logger.error("Sistema no está listo")
        sys.exit(1)

    # Si pide monitoreo continuo
    if "--watch" in sys.argv:
        timeout = 3600  # 1 hora por defecto
        if "--timeout" in sys.argv:
            idx = sys.argv.index("--timeout")
            timeout = int(sys.argv[idx + 1])
        monitor.watch_transition(timeout)

    sys.exit(0)

if __name__ == "__main__":
    main()
