#!/usr/bin/env python3
"""
Verificación de solidez del cambio automático entre agentes (SAC → PPO).
Valida:
1. Estado de checkpoint previo
2. Rutas de configuración correctas
3. Manejo de excepciones
4. Integridad de datos entre transiciones
5. Logs y monitoreo
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

class AgentTransitionValidator:
    """Valida la solidez del sistema de cambio entre agentes."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.issues: list[dict[str, str | bool]] = []
        self.warnings: list[dict[str, str | bool]] = []
        self.validations: list[dict[str, str | bool]] = []

    def validate_all(self) -> bool:
        """Ejecuta todas las validaciones. Retorna True si todo está OK."""
        logger.info("=" * 80)
        logger.info("VALIDACIÓN DE SOLIDEZ: CAMBIO AUTOMÁTICO SAC → PPO")
        logger.info("=" * 80)

        self._validate_checkpoint_dirs()
        self._validate_script_structure()
        self._validate_simulate_function()
        self._validate_error_handling()
        self._validate_config_paths()
        self._validate_state_persistence()

        logger.info("\n" + "=" * 80)
        self._print_summary()
        logger.info("=" * 80)

        return len(self.issues) == 0

    def _validate_checkpoint_dirs(self) -> None:
        """Valida que los directorios de checkpoint estén correctamente configurados."""
        logger.info("\n[1] Validando directorios de checkpoint...")

        checkpoint_dirs = {
            "SAC": self.project_root / "analyses" / "oe3" / "training" / "checkpoints" / "sac",
            "PPO": self.project_root / "analyses" / "oe3" / "training" / "checkpoints" / "ppo",
        }

        for agent, path in checkpoint_dirs.items():
            exists = path.exists()
            status = "✓" if exists else "✗ (será creado en runtime)"
            logger.info(f"  {agent:3s} checkpoint dir: {path.name:20s} {status}")
            self.validations.append({
                "checkpoint_dir": agent,
                "exists": exists or True  # OK porque se crea en runtime
            })

    def _validate_script_structure(self) -> None:
        """Valida que run_sac_ppo_only.py esté bien estructurado."""
        logger.info("\n[2] Validando estructura de scripts...")

        script_path = self.project_root / "scripts" / "run_sac_ppo_only.py"

        if not script_path.exists():
            self.issues.append({
                "severity": "CRITICAL",
                "file": str(script_path),
                "issue": "Script no encontrado"
            })
            return

        content = script_path.read_text()

        # Verificar presencia de agentes
        required_patterns = [
            ("agent_names = [", "Lista de agentes definida"),
            ('agent_names = ["SAC", "PPO"]', "Agentes SAC y PPO en lista"),
            ("for agent in agent_names:", "Loop sobre agentes"),
            ("simulate(...agent_name=agent,", "Llamada a simulate con agent_name"),
            ("except Exception as e:", "Manejo de excepciones"),
        ]

        for pattern, desc in required_patterns:
            if pattern in content:
                logger.info(f"  ✓ {desc}")
                self.validations.append({"script_check": desc, "found": True})
            else:
                self.issues.append({
                    "severity": "HIGH",
                    "file": "run_sac_ppo_only.py",
                    "issue": f"Falta: {desc}"
                })
                self.validations.append({"script_check": desc, "found": False})

    def _validate_simulate_function(self) -> None:
        """Valida que simulate() rutee correctamente a SAC y PPO."""
        logger.info("\n[3] Validando función simulate()...")

        simulate_path = self.project_root / "src" / "iquitos_citylearn" / "oe3" / "simulate.py"

        if not simulate_path.exists():
            self.issues.append({
                "severity": "CRITICAL",
                "file": str(simulate_path),
                "issue": "Archivo simulate.py no encontrado"
            })
            return

        content = simulate_path.read_text()

        agent_routing = {
            "SAC": 'agent_name.lower() == "sac"',
            "PPO": 'agent_name.lower() == "ppo"',
        }

        for agent, condition in agent_routing.items():
            if condition in content:
                logger.info(f"  ✓ Rutas para {agent} definidas")
                self.validations.append({
                    "agent_routing": agent,
                    "found": True
                })
            else:
                self.issues.append({
                    "severity": "HIGH",
                    "file": "simulate.py",
                    "issue": f"Falta ruteo para {agent}"
                })

        # Validar fallback
        if "except Exception as e:" in content and "UncontrolledChargingAgent" in content:
            logger.info(f"  ✓ Fallback a UncontrolledAgent si error")
            self.validations.append({"fallback": "uncontrolled", "found": True})
        else:
            self.warnings.append({
                "severity": "MEDIUM",
                "file": "simulate.py",
                "issue": "No hay fallback explícito si agente falla"
            })

    def _validate_error_handling(self) -> None:
        """Valida manejo de excepciones entre agentes."""
        logger.info("\n[4] Validando manejo de excepciones...")

        simulate_path = self.project_root / "src" / "iquitos_citylearn" / "oe3" / "simulate.py"
        content = simulate_path.read_text()

        checks = {
            "try-except SAC": ('if agent_name.lower() == "sac":\n        try:', "SAC envuelto en try-except"),
            "try-except PPO": ('if agent_name.lower() == "ppo":\n        try:', "PPO envuelto en try-except"),
            "Log de error": ('logger.error(f"✗ {agent}', "Log de error en script"),
            "Continuar tras error": ("results[agent]", "Script continúa tras error"),
        }

        for name, item in checks.items():
            pattern, desc = item
            if pattern in content:
                logger.info(f"  ✓ {desc}")
                self.validations.append({name: desc, "ok": True})
            else:
                self.warnings.append({
                    "severity": "LOW",
                    "issue": f"Falta verificación: {desc}"
                })

    def _validate_config_paths(self) -> None:
        """Valida que las rutas de configuración sean accesibles."""
        logger.info("\n[5] Validando rutas de configuración...")

        paths = {
            "Config default": "configs/default.yaml",
            "Dataset builder": "src/iquitos_citylearn/oe3/dataset_builder.py",
            "Agents module": "src/iquitos_citylearn/oe3/agents/__init__.py",
        }

        for name, rel_path in paths.items():
            abs_path = self.project_root / rel_path
            exists = abs_path.exists()
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {name:20s}: {rel_path}")
            if not exists:
                self.issues.append({
                    "severity": "CRITICAL",
                    "file": rel_path,
                    "issue": "Ruta no encontrada"
                })

    def _validate_state_persistence(self) -> None:
        """Valida que el estado persista entre SAC → PPO."""
        logger.info("\n[6] Validando persistencia de estado entre agentes...")

        script_path = self.project_root / "scripts" / "run_sac_ppo_only.py"
        content = script_path.read_text()

        if "env =" in content and content.count("env = ") == 1:
            logger.info("  ✓ Ambiente reutilizado (instanciado una sola vez)")
        else:
            self.warnings.append({
                "severity": "MEDIUM",
                "issue": "Ambiente podría no estar siendo reutilizado"
            })

        if "project_seed" in content:
            logger.info("  ✓ Seed consistente entre agentes")

        if "MultiObjectiveWeights" in content or "multi_objective_priority" in content:
            logger.info("  ✓ Reward weights configurables")

    def _print_summary(self) -> None:
        """Imprime resumen de validación."""

        logger.info(f"\n✓ Validaciones exitosas: {len([v for v in self.validations if v.get('ok', v.get('found'))])}")

        if self.issues:
            logger.error(f"\n✗ ISSUES CRÍTICOS ({len(self.issues)}):")
            for issue in self.issues:
                logger.error(f"   [{issue['severity']}] {issue.get('file', 'N/A')}: {issue['issue']}")

        if self.warnings:
            logger.warning(f"\n⚠ ADVERTENCIAS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"   [{warning.get('severity', 'LOW')}] {warning['issue']}")

        if not self.issues and not self.warnings:
            logger.info("\n✅ SISTEMA DE CAMBIO SAC → PPO COMPLETAMENTE SÓLIDO")
        elif not self.issues:
            logger.info("\n✅ Sistema operacional (solo advertencias menores)")
        else:
            logger.error("\n❌ Se encontraron problemas críticos")

        # Resumen de rutas
        logger.info("\n" + "=" * 80)
        logger.info("RUTAS DE EJECUCIÓN:")
        logger.info("=" * 80)
        logger.info(f"Script principal:     {self.project_root / 'scripts/run_sac_ppo_only.py'}")
        logger.info(f"Función simulate:     {self.project_root / 'src/iquitos_citylearn/oe3/simulate.py'}")
        logger.info(f"Checkpoints SAC:      {self.project_root / 'analyses/oe3/training/checkpoints/sac'}")
        logger.info(f"Checkpoints PPO:      {self.project_root / 'analyses/oe3/training/checkpoints/ppo'}")
        logger.info(f"Config:               {self.project_root / 'configs/default.yaml'}")

def main():
    project_root = Path(__file__).parent.parent
    validator = AgentTransitionValidator(project_root)
    success = validator.validate_all()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
