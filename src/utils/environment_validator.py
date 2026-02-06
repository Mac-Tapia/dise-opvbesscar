# ============================================================================
# VALIDADOR DE AMBIENTE - ASEGURA QUE SIEMPRE ESTÁS EN .venv
# ============================================================================
# Uso: from src.utils.environment_validator import validate_venv_active
#      validate_venv_active()

import sys
from pathlib import Path

def validate_venv_active() -> bool:
    """
    Valida que Python se está ejecutando desde .venv
    Lanza excepción si no está en el ambiente correcto
    """
    python_exe = Path(sys.executable)
    project_root = Path(__file__).parent.parent.parent  # src/utils/environment_validator.py -> proyecto
    venv_path = project_root / ".venv"

    # Verificar que .venv existe
    if not venv_path.exists():
        raise RuntimeError(
            f"❌ AMBIENTE NO ENCONTRADO: {venv_path}\n"
            f"   Por favor crea el ambiente con: python -m venv .venv"
        )

    # Verificar que Python está en .venv
    venv_scripts = venv_path / "Scripts"
    if not str(python_exe).lower().startswith(str(venv_scripts).lower()):
        raise RuntimeError(
            f"❌ ERROR: No estás ejecutando desde .venv\n"
            f"   Python actual: {python_exe}\n"
            f"   Expected: {venv_scripts}\n"
            f"\n"
            f"   SOLUCIÓN: Activa .venv primero:\n"
            f"   .venv\\Scripts\\Activate.ps1  (PowerShell)\n"
            f"   O usa scripts/run_training.ps1 que lo hace automáticamente"
        )

    return True

def get_venv_info() -> dict:
    """Retorna información del ambiente actual"""
    python_exe = Path(sys.executable)
    return {
        "python_exe": str(python_exe),
        "python_version": sys.version,
        "in_venv": "Scripts" in str(python_exe) or ".venv" in str(python_exe),
        "venv_path": str(Path(sys.executable).parent.parent),
    }

# Auto-validar al importar (solo si está en main o entrenamiento)
if __name__ == "__main__":
    validate_venv_active()
    info = get_venv_info()
    print("✅ AMBIENTE VALIDADO:")
    for k, v in info.items():
        print(f"   {k}: {v}")
