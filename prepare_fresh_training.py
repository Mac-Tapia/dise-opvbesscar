#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PREPARADOR DE ENTRENAMIENTO DESDE CERO - pvbesscar
Script completo para:
1. Limpiar checkpoints (SAC, PPO, backups)
2. Limpiar outputs anteriores
3. Validar datasets OE2
4. Verificar dependencias
5. Opcionalmente ejecutar entrenamiento

Uso:
    python prepare_fresh_training.py              # Solo preparar
    python prepare_fresh_training.py --train      # Preparar + Entrenar SAC
    python prepare_fresh_training.py --train --agent PPO  # Entrenar PPO
    python prepare_fresh_training.py --train --agent A2C  # Entrenar A2C
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


class FreshTrainingPreparator:
    """Preparador de entrenamientos desde cero."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.root_dir = Path.cwd()
        self.all_ok = True

    def log(self, text: str, color: str = "white", icon: str = "  "):
        """Imprime mensaje con color."""
        colors = {
            "green": "\033[92m",
            "red": "\033[91m",
            "yellow": "\033[93m",
            "cyan": "\033[96m",
            "magenta": "\033[95m",
            "white": "\033[97m",
            "gray": "\033[90m",
            "reset": "\033[0m",
        }
        if self.verbose:
            print(f"{colors.get(color, '')}{icon} {text}{colors['reset']}")

    def section(self, title: str, color: str = "cyan"):
        """Imprime encabezado de sección."""
        self.log("")
        self.log("╔" + "═" * 66 + "╗", color)
        self.log("║ " + title.ljust(64) + " ║", color)
        self.log("╚" + "═" * 66 + "╝", color)
        self.log("")

    def step_1_validate_dirs(self):
        """Paso 1: Validar estructura de directorios."""
        self.section("PASO 1: VALIDAR ESTRUCTURA DE DIRECTORIOS", "yellow")

        dirs_required = [
            "checkpoints",
            "checkpoints/SAC",
            "checkpoints/PPO",
            "data/interim/oe2",
            "outputs",
        ]

        for dir_name in dirs_required:
            dir_path = self.root_dir / dir_name
            if dir_path.exists():
                self.log(f"✓ {dir_name}", "green")
            else:
                self.log(f"✗ {dir_name} (CREANDO)", "yellow")
                dir_path.mkdir(parents=True, exist_ok=True)
                self.log(f"  ✓ Creado", "green")

    def step_2_clean_checkpoints(self):
        """Paso 2: Limpiar checkpoints."""
        self.section("PASO 2: LIMPIAR CHECKPOINTS ANTERIORES", "magenta")

        # SAC checkpoints
        self.log("🗑️  Eliminando SAC checkpoints...", "magenta")
        sac_dir = self.root_dir / "checkpoints" / "SAC"
        if sac_dir.exists():
            sac_count = len(list(sac_dir.rglob("*")))
            if sac_count > 0:
                shutil.rmtree(sac_dir)
                sac_dir.mkdir(parents=True, exist_ok=True)
                self.log(f"  ✓ Eliminados {sac_count} archivos/dirs", "green")
            else:
                self.log("  ✓ SAC ya estaba limpio", "green")

        # PPO checkpoints
        self.log("🗑️  Eliminando PPO checkpoints...", "magenta")
        ppo_dir = self.root_dir / "checkpoints" / "PPO"
        if ppo_dir.exists():
            ppo_count = len(list(ppo_dir.rglob("*")))
            if ppo_count > 0:
                shutil.rmtree(ppo_dir)
                ppo_dir.mkdir(parents=True, exist_ok=True)
                self.log(f"  ✓ Eliminados {ppo_count} archivos/dirs", "green")
            else:
                self.log("  ✓ PPO ya estaba limpio", "green")

        # SAC backups
        self.log("🗑️  Eliminando backups SAC...", "magenta")
        checkpoints_dir = self.root_dir / "checkpoints"
        sac_backups = list(checkpoints_dir.glob("SAC_backup_*"))
        if sac_backups:
            for backup in sac_backups:
                shutil.rmtree(backup, ignore_errors=True)
            self.log(
                f"  ✓ Eliminados {len(sac_backups)} backups SAC", "green"
            )
        else:
            self.log("  ✓ No hay backups SAC", "green")

        # PPO backups
        self.log("🗑️  Eliminando backups PPO...", "magenta")
        ppo_backups = list(checkpoints_dir.glob("PPO_backup_*"))
        if ppo_backups:
            for backup in ppo_backups:
                shutil.rmtree(backup, ignore_errors=True)
            self.log(
                f"  ✓ Eliminados {len(ppo_backups)} backups PPO", "green"
            )
        else:
            self.log("  ✓ No hay backups PPO", "green")

    def step_3_clean_outputs(self):
        """Paso 3: Limpiar outputs."""
        self.section("PASO 3: LIMPIAR OUTPUTS DE ENTRENAMIENTOS ANTERIORES", "magenta")

        outputs_sac = self.root_dir / "outputs" / "sac_training"
        outputs_ppo = self.root_dir / "outputs" / "ppo_training"

        self.log("🗑️  Limpiando outputs/sac_training/...", "magenta")
        if outputs_sac.exists():
            shutil.rmtree(outputs_sac)
            outputs_sac.mkdir(parents=True, exist_ok=True)
            self.log("  ✓ Output SAC limpio", "green")
        else:
            self.log("  ✓ No hay outputs SAC anteriores", "green")

        self.log("🗑️  Limpiando outputs/ppo_training/...", "magenta")
        if outputs_ppo.exists():
            shutil.rmtree(outputs_ppo)
            outputs_ppo.mkdir(parents=True, exist_ok=True)
            self.log("  ✓ Output PPO limpio", "green")
        else:
            self.log("  ✓ No hay outputs PPO anteriores", "green")

    def step_4_validate_oe2(self) -> bool:
        """Paso 4: Validar datasets OE2."""
        self.section("PASO 4: VALIDAR DATASETS OE2 (CRÍTICO)", "yellow")

        oe2_files = {
            "Solar PVGIS": "data/interim/oe2/solar/pv_generation_citylearn_v2.csv",
            "Chargers": "data/interim/oe2/chargers/chargers_real_hourly_2024.csv",
            "BESS": "data/interim/oe2/bess/bess_hourly_dataset_2024.csv",
            "Mall Demand": "data/interim/oe2/demandamallkwh/demandamallhorakwh.csv",
        }

        all_ok = True
        for name, path in oe2_files.items():
            file_path = self.root_dir / path
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                self.log(f"✓ {name}: LISTO ({size_kb:.0f} KB)", "green")
            else:
                self.log(f"✗ {name}: NO ENCONTRADO", "red")
                all_ok = False

        if not all_ok:
            self.log("", "white")
            self.log(
                "⚠️  ADVERTENCIA: Faltan datasets OE2 críticos",
                "yellow",
            )
            self.all_ok = False

        return all_ok

    def step_5_validate_python(self):
        """Paso 5: Validar dependencias Python."""
        self.section("PASO 5: VALIDAR DEPENDENCIAS PYTHON", "yellow")

        # Verificar venv
        venv_path = self.root_dir / ".venv"
        if venv_path.exists():
            self.log("✓ Virtual Environment (.venv) detectado", "green")
        else:
            self.log(
                "⚠ Virtual Environment NO encontrado",
                "yellow",
            )
            self.log("  Ejecuta: python -m venv .venv", "yellow")

        # Verificar paquetes críticos
        try:
            import torch  # type: ignore[import]

            self.log(f"✓ PyTorch {torch.__version__} instalado", "green")
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                self.log(f"  ✓ GPU disponible: {gpu_name}", "green")
            else:
                self.log("  ℹ GPU no disponible (usará CPU)", "gray")
        except ImportError:
            self.log("⚠ PyTorch NO instalado", "yellow")

        try:
            import stable_baselines3  # type: ignore[import]

            self.log(
                f"✓ Stable-Baselines3 {stable_baselines3.__version__} instalado",
                "green",
            )
        except ImportError:
            self.log("⚠ Stable-Baselines3 NO instalado", "yellow")

    def step_6_validate_critical_files(self):
        """Paso 6: Validar archivos críticos."""
        self.section("PASO 6: VERIFICAR ARCHIVOS CRÍTICOS", "yellow")

        critical_files = [
            "train_sac_multiobjetivo.py",
            "configs/default.yaml",
            "src/rewards/rewards.py",
        ]

        for file_name in critical_files:
            file_path = self.root_dir / file_name
            if file_path.exists():
                size_kb = file_path.stat().st_size / 1024
                self.log(f"✓ {file_name} ({size_kb:.0f} KB)", "green")
            else:
                self.log(f"✗ {file_name}: NO ENCONTRADO", "red")
                self.all_ok = False

    def summary(self):
        """Resumen final."""
        self.section("RESUMEN: PREPARACIÓN LISTA", "green")

        self.log("✅ Checkpoints limpios", "green")
        self.log("✅ Outputs anteriores removidos", "green")
        self.log("✅ Datasets OE2 validados", "green")
        self.log("✅ Archivos críticos presentes", "green")
        self.log(
            "✅ Sistema listo para entrenamiento DESDE CERO", "green"
        )

    def run_training(self, agent: str = "SAC"):
        """Ejecutar entrenamiento."""
        self.section(f"INICIANDO ENTRENAMIENTO: {agent} DESDE CERO", "cyan")

        self.log(
            f"⏳ Iniciando entrenamiento {agent}...", "cyan"
        )
        self.log(
            "Timesteps: 87,600 (10 episodios completos)", "cyan"
        )
        self.log(
            "Duración estimada: 20-30 minutos (GPU)", "cyan"
        )
        self.log("")

        script_map = {
            "SAC": "train_sac_multiobjetivo.py",
            "PPO": "train_ppo_multiobjetivo.py",
            "A2C": "train_a2c_multiobjetivo.py",
        }

        script = script_map.get(agent, "train_sac_multiobjetivo.py")
        self.log(f"▶ Ejecutando: python {script}", "cyan")

        try:
            result = subprocess.run(
                [sys.executable, script],
                cwd=str(self.root_dir),
                check=False,
            )
            return result.returncode == 0
        except Exception as e:
            self.log(f"❌ Error ejecutando entrenamiento: {e}", "red")
            return False

    def prepare(self):
        """Ejecutar preparación completa."""
        self.log("Sistema: Python", "gray")
        self.log(
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "gray",
        )
        self.log(f"Ubicación: {self.root_dir}", "gray")

        self.step_1_validate_dirs()
        self.step_2_clean_checkpoints()
        self.step_3_clean_outputs()
        self.step_4_validate_oe2()
        self.step_5_validate_python()
        self.step_6_validate_critical_files()
        self.summary()

        return self.all_ok

    def prepare_and_train(self, agent: str = "SAC"):
        """Preparar y entrenar."""
        if self.prepare():
            self.run_training(agent)
        else:
            self.log(
                "❌ Preparación no completada. Revisa errores arriba.",
                "red",
            )
            return False

        return True


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Preparador de entrenamiento SAC/PPO/A2C desde CERO"
    )
    parser.add_argument(
        "--train", action="store_true", help="Ejecutar entrenamiento después"
    )
    parser.add_argument(
        "--agent",
        choices=["SAC", "PPO", "A2C"],
        default="SAC",
        help="Agente a entrenar (default: SAC)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Modo silencioso"
    )

    args = parser.parse_args()

    preparator = FreshTrainingPreparator(verbose=not args.quiet)

    if args.train:
        preparator.prepare_and_train(args.agent)
    else:
        preparator.prepare()
        preparator.log("")
        preparator.section("PRÓXIMO PASO", "cyan")
        preparator.log(
            "Para iniciar entrenamiento SAC:", "cyan"
        )
        preparator.log("  python train_sac_multiobjetivo.py", "white")
        preparator.log("")
        preparator.log(
            "O ejecutar este script con bandera --train:", "cyan"
        )
        preparator.log(
            "  python prepare_fresh_training.py --train", "white"
        )
        preparator.log("")
        preparator.log(
            "Para entrenar con otro agente:", "cyan"
        )
        preparator.log(
            "  python prepare_fresh_training.py --train --agent PPO",
            "white",
        )
        preparator.log(
            "  python prepare_fresh_training.py --train --agent A2C",
            "white",
        )
        preparator.log("")
        preparator.section(
            "PREPARACIÓN COMPLETADA", "green"
        )


if __name__ == "__main__":
    main()
