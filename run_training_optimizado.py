#!/usr/bin/env python3
"""
COMANDOS PARA ACTIVAR ENTRENAMIENTO OPTIMIZADO
===============================================

Este archivo documenta los comandos exactos para entrenar
cada agente con hiperparámetros optimizados para RTX 4060.

Configuraciones generadas automáticamente y basadas en:
- Arquitectura: SAC (512×512), PPO (512×512), A2C (512×512)
- Batch sizes: 256 (SAC), 64 (PPO), 64 (A2C)
- Memoria GPU: ~7-8 GB de RTX 4060
- Velocidad esperada: 30-45 min/ep (SAC), 15-25 min/ep (PPO), 10-15 min/ep (A2C)
"""

print(__doc__)

import subprocess
import sys
from pathlib import Path

def run_command(cmd, desc):
    """Ejecutar comando con descripción."""
    print(f"\n{'='*80}")
    print(f"EJECUTANDO: {desc}")
    print(f"{'='*80}")
    print(f"Comando: {cmd}\n")
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"✓ {desc} COMPLETADO\n")
    else:
        print(f"✗ {desc} FALLÓ (exit code {result.returncode})\n")
    return result.returncode == 0

# Cambiar al directorio del proyecto
project_dir = Path(__file__).parent
print(f"Directorio del proyecto: {project_dir}\n")

# Verificar que estamos en el entorno virtual correcto
if not (project_dir / ".venv").exists():
    print("❌ ERROR: Entorno virtual .venv no encontrado")
    print("  Crear con: python -m venv .venv")
    sys.exit(1)

print("✓ Entorno virtual encontrado\n")

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    OPCIONES DE ENTRENAMIENTO DISPONIBLES                 ║
╠════════════════════════════════════════════════════════════════════════════╣

OPCION 1: ENTRENAR SOLO SAC (Más rápido, prueba GPU)
  Comando: python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5
  Duración: ~3-5 horas
  GPU: 4GB disponibles para otros trabajos

OPCION 2: ENTRENAR SOLO PPO
  Comando: python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes 3
  Duración: ~1-2 horas
  GPU: 2.5GB disponibles

OPCION 3: ENTRENAR SOLO A2C (Más rápido)
  Comando: python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes 3
  Duración: ~1-1.5 horas
  GPU: 2GB disponibles

OPCION 4: ENTRENAR LOS 3 EN SECUENCIA (RECOMENDADO)
  Ejecutar SAC → PPO → A2C uno tras otro
  Duración total: ~5-8 horas
  Resultado: Comparativa completa de los 3 agentes

OPCION 5: ENTRENAR TODOS JUNTOS (PARALELO - Solo si tienes 2+ GPUs)
  Requiere: 2 GPUs NVIDIA o similar
  ⚠️ NO RECOMENDADO para RTX 4060 (solo 8GB total)

╠════════════════════════════════════════════════════════════════════════════╣
║                         CONFIGURACION RECOMENDADA                         ║
╠════════════════════════════════════════════════════════════════════════════╣

OPCION BALANCE (4-6 horas, recomendado para producción):

  1. SAC: 5 episodios (off-policy = más muestras reutilizadas)
     → Aprenderá a optimizar con datos limitados

  2. PPO: 3 episodios (on-policy = gradientes estables)
     → Mejor para ajuste fino sobre estrategia SAC

  3. A2C: 3 episodios (simple baseline rápido)
     → Validar que arquitectura simple también funciona

Total: 11 episodios × 8,760 timesteps = 96,360 muestras

RESULTADOS ESPERADOS:
  - CO₂ baseline: ~10,200 kg/año
  - CO₂ SAC:      ~7,500 kg/año  (-26%)
  - CO₂ PPO:      ~7,200 kg/año  (-29%)
  - CO₂ A2C:      ~7,800 kg/año  (-24%)

╚════════════════════════════════════════════════════════════════════════════╝

¿CUAL OPCION DESEAS EJECUTAR?
  1. SAC solamente
  2. PPO solamente
  3. A2C solamente
  4. Secuencia SAC → PPO → A2C (RECOMENDADO)
  5. Crear script personalizado

Ingresa el número (1-5) o "exit" para salir:
""")

choice = input("> ").strip().lower()

commands = {
    "1": ("SAC", "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5"),
    "2": ("PPO", "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes 3"),
    "3": ("A2C", "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes 3"),
    "4": ("Secuencia SAC→PPO→A2C", None),
}

if choice == "exit":
    print("\n✓ Saliendo...")
    sys.exit(0)

if choice in ["1", "2", "3"]:
    desc, cmd = commands[choice]
    success = run_command(cmd, f"Entrenamiento {desc}")
    sys.exit(0 if success else 1)

elif choice == "4":
    print("\nEjecutando secuencia completa: SAC → PPO → A2C\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║ ETAPA 1: SAC (Off-Policy, ~3-5 horas)                                    ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")

    success1 = run_command(
        "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5",
        "Entrenamiento SAC"
    )

    if not success1:
        print("❌ SAC falló, abortando secuencia")
        sys.exit(1)

    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print("║ ETAPA 2: PPO (On-Policy, ~1-2 horas)                                     ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")

    success2 = run_command(
        "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes 3",
        "Entrenamiento PPO"
    )

    if not success2:
        print("❌ PPO falló, abortando secuencia")
        sys.exit(1)

    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print("║ ETAPA 3: A2C (On-Policy Baseline, ~1-1.5 horas)                          ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")

    success3 = run_command(
        "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes 3",
        "Entrenamiento A2C"
    )

    if success1 and success2 and success3:
        print("\n" + "="*80)
        print("✓✓✓ TODOS LOS ENTRENAMIENTOS COMPLETADOS EXITOSAMENTE ✓✓✓")
        print("="*80)
        print("\nResultados disponibles en: outputs/oe3_simulations/")
        print("Tabla comparativa: python -m scripts.run_oe3_co2_table --config configs/default.yaml")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ Algunos entrenamientos fallaron")
        print("="*80)
        sys.exit(1)

elif choice == "5":
    print("\nCreando script personalizado de entrenamiento...\n")

    print("¿Cuántos episodios para SAC? (default: 5): ", end="")
    sac_ep = input().strip() or "5"

    print("¿Cuántos episodios para PPO? (default: 3): ", end="")
    ppo_ep = input().strip() or "3"

    print("¿Cuántos episodios para A2C? (default: 3): ", end="")
    a2c_ep = input().strip() or "3"

    script_content = f"""#!/usr/bin/env python3
# Script personalizado de entrenamiento
# Generado automáticamente

import subprocess
import sys

cmds = [
    ("SAC ({sac_ep} eps)", f"python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes {sac_ep}"),
    ("PPO ({ppo_ep} eps)", f"python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes {ppo_ep}"),
    ("A2C ({a2c_ep} eps)", f"python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes {a2c_ep}"),
]

for desc, cmd in cmds:
    print(f"\\n[EJECUTANDO] {{desc}}")
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        print(f"ERROR en {{desc}}")
        sys.exit(1)

print("\\n✓ Entrenamiento completo exitoso!")
"""

    script_path = project_dir / "run_training_custom.py"
    with open(script_path, "w") as f:
        f.write(script_content)

    print(f"\n✓ Script creado: {script_path}")
    print(f"  Ejecutar con: python {script_path}")
    sys.exit(0)

else:
    print("❌ Opción inválida")
    sys.exit(1)
