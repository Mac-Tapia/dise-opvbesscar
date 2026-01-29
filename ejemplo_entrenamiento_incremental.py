#!/usr/bin/env python3
"""
EJEMPLO: Entrenamiento Incremental desde Checkpoints Existentes
Demuestra cómo reanudar entrenamientos y acumular pasos
"""

from stable_baselines3 import PPO, SAC, A2C
from pathlib import Path
import json

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Checkpoint a reanudar (elegir uno)
AGENT = "PPO"  # Opciones: "SAC", "PPO", "A2C"
CHECKPOINT_DIR = Path("analyses/oe3/training/checkpoints") / AGENT.lower()
CHECKPOINT_PATH = CHECKPOINT_DIR / f"{AGENT.lower()}_final.zip"

# Parámetros de entrenamientos adicionales
STEPS_TO_ADD = 26280  # Puedes cambiar esto según necesites

# ============================================================================
# FUNCIÓN: REANUDAR ENTRENAMIENTO
# ============================================================================

def resume_training(agent_type: str, checkpoint_path: Path, additional_steps: int):
    """
    Reanuda entrenamiento de agente desde checkpoint

    Args:
        agent_type: "SAC", "PPO" o "A2C"
        checkpoint_path: Ruta al archivo .zip del checkpoint
        additional_steps: Pasos adicionales a entrenar

    Nota: reset_num_timesteps=False es CRÍTICO para acumular pasos
    """

    print(f"\n{'=' * 80}")
    print(f"ENTRENAMIENTO INCREMENTAL: {agent_type}")
    print(f"{'=' * 80}\n")

    # 1. Validar checkpoint
    if not checkpoint_path.exists():
        print(f"❌ ERROR: Checkpoint no encontrado: {checkpoint_path}")
        return False

    print(f"✅ Checkpoint encontrado: {checkpoint_path}")

    # 2. Cargar agente desde checkpoint
    print(f"\n📂 Cargando agente {agent_type} desde checkpoint...")

    try:
        # Elegir clase de algoritmo
        AgentClass = {"SAC": SAC, "PPO": PPO, "A2C": A2C}[agent_type]

        # Cargar modelo (nota: env será None, pero eso está ok para cargar estructura)
        agent = AgentClass.load(checkpoint_path)

        print(f"✅ Agente cargado correctamente")
        print(f"   Timesteps actuales: {agent.num_timesteps:,}")
        print(f"   Pasos a entrenar: {additional_steps:,}")
        print(f"   Timesteps nuevos: {agent.num_timesteps + additional_steps:,}")

    except Exception as e:
        print(f"❌ ERROR al cargar agente: {e}")
        return False

    # 3. Mostrar información
    print(f"\n📊 INFORMACIÓN DEL AGENTE:")
    print(f"   Tipo: {agent_type}")
    print(f"   Policy: {agent.policy}")
    print(f"   Learning Rate: {agent.learning_rate}")

    # 4. Preparar para entrenamientos incremental
    print(f"\n🚀 PREPARACIÓN PARA ENTRENAMIENTO INCREMENTAL:")
    print(f"   reset_num_timesteps: False (CRÍTICO - acumula pasos)")
    print(f"   Pasos anteriores: {agent.num_timesteps:,}")
    print(f"   Pasos a agregar: {additional_steps:,}")
    print(f"   Pasos finales: {agent.num_timesteps + additional_steps:,}")

    # 5. (COMENTADO) Reanudar entrenamiento
    # Para usar esto, REQUIERE:
    # - CityLearnEnv correctamente inicializado como 'env'
    # - Los mismos hiperparámetros que el entrenamiento original

    print(f"\n💡 PARA REANUDAR ENTRENAMIENTO, DESCOMENTA EL CÓDIGO ABAJO Y EJECUTA:\n")

    training_code = f"""
# ╔════════════════════════════════════════════════════════════════════════╗
# ║ CÓDIGO PARA EJECUTAR ENTRENAMIENTO INCREMENTAL                        ║
# ╠════════════════════════════════════════════════════════════════════════╣
# ║ PASO 1: Asegúrate de tener CityLearnEnv inicializado                  ║
# ║ PASO 2: Descomentar el código abajo                                   ║
# ║ PASO 3: Ejecutar                                                      ║
# ╚════════════════════════════════════════════════════════════════════════╝

from citylearn.citylearn import CityLearnEnv
import os

# REEMPLAZAR CON TU SCHEMA JSON
SCHEMA_PATH = "outputs/schema_*.json"  # ← Usa tu schema real

# ✅ CRIAR AMBIENTE
print("Creando ambiente...")
env = CityLearnEnv(schema_path=SCHEMA_PATH)

# ✅ CARGAR AGENTE DESDE CHECKPOINT
print(f"Cargando {{'{agent_type}'}} desde checkpoint...")
agent = {AgentClass.__name__}.load(
    "{checkpoint_path}",
    env=env
)

# ✅ REANUDAR ENTRENAMIENTO CON ACUMULACIÓN DE PASOS
print(f"Iniciando entrenamiento incremental...")
print(f"  Pasos actuales: {{agent.num_timesteps:,}}")
print(f"  Pasos a entrenar: {additional_steps:,}")

agent.learn(
    total_timesteps={additional_steps},      # Pasos ADICIONALES
    reset_num_timesteps=False                # ⚠️ NO resetear contador
)

# ✅ GUARDAR NUEVO CHECKPOINT
new_total = agent.num_timesteps
new_checkpoint_path = "{CHECKPOINT_DIR}/{agent_type.lower()}_step_{'{new_total:,}'}.zip"
agent.save(new_checkpoint_path)
print(f"✅ Checkpoint guardado: {{new_checkpoint_path}}")
print(f"   Pasos finales: {{agent.num_timesteps:,}}")

# ✅ (OPCIONAL) ACTUALIZAR ARCHIVO JSON DE DATOS
from scripts.query_training_archive import TrainingArchiveManager

manager = TrainingArchiveManager()
# Aquí puedes actualizar métricas con nuevos valores
manager.update_after_incremental_training("{agent_type}", {{
    "timesteps_finales": agent.num_timesteps,
    # Agregar más métricas aquí si calculaste
}})
    """

    print(training_code)

    # 6. Alternativa simplificada
    print(f"\n🎯 ALTERNATIVA RÁPIDA (Sin datos de entrenamiento):\n")

    simple_code = f"""
# Si solo quieres reanudar sin medir pasos:
from stable_baselines3 import {AgentClass.__name__}

agent = {AgentClass.__name__}.load("{checkpoint_path}", env=env)
agent.learn(total_timesteps={additional_steps}, reset_num_timesteps=False)
agent.save("checkpoint_nuevo.zip")
    """

    print(simple_code)

    return True

# ============================================================================
# FUNCIÓN: MOSTRAR INFORMACIÓN DE CHECKPOINTS
# ============================================================================

def show_checkpoint_info():
    """Muestra información disponible de todos los checkpoints"""

    print(f"\n{'=' * 80}")
    print("INFORMACIÓN DISPONIBLE DE CHECKPOINTS")
    print(f"{'=' * 80}\n")

    archive_path = Path("training_results_archive.json")

    if not archive_path.exists():
        print("❌ No encontrado: training_results_archive.json")
        return

    with open(archive_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("📦 CHECKPOINTS DISPONIBLES:\n")

    for agent, agent_data in data["agents"].items():
        cm = agent_data["checkpoint_management"]
        fm = agent_data["final_metrics"]

        print(f"🔸 {agent.upper()}")
        print(f"   Estado: {agent_data['status']}")
        print(f"   Directorio: {cm['checkpoint_directory']}")
        print(f"   Final: {cm['final_checkpoint']}")
        print(f"   Checkpoints guardados: {cm['checkpoints_saved']}")
        print(f"   Frecuencia: Cada {cm['checkpoint_frequency_steps']} pasos")
        print(f"   Resumible: {'✅ Sí' if cm['can_resume_training'] else '❌ No'}")
        print(f"   Timesteps actuales: {agent_data['training_configuration']['total_timesteps']:,}")
        print(f"   Reward final: {fm['reward_final']}")
        print()

# ============================================================================
# FUNCIÓN: VALIDAR ENTORNO
# ============================================================================

def validate_environment():
    """Valida que archivos necesarios existan"""

    print(f"\n{'=' * 80}")
    print("VALIDACIÓN DE AMBIENTE")
    print(f"{'=' * 80}\n")

    files_to_check = [
        ("training_results_archive.json", "Datos consolidados"),
        ("scripts/query_training_archive.py", "Utilidad de consultas"),
        ("TABLA_COMPARATIVA_FINAL_CORREGIDA.md", "Tabla comparativa"),
    ]

    all_ok = True

    for filepath, description in files_to_check:
        exists = Path(filepath).exists()
        status = "✅" if exists else "❌"
        print(f"{status} {description}: {filepath}")
        if not exists:
            all_ok = False

    print()

    # Checkpoints
    print("📁 CHECKPOINTS:\n")

    for agent in ["SAC", "PPO", "A2C"]:
        checkpoint_dir = Path("analyses/oe3/training/checkpoints") / agent.lower()
        if checkpoint_dir.exists():
            num_files = len(list(checkpoint_dir.glob("*.zip")))
            final_exists = (checkpoint_dir / f"{agent.lower()}_final.zip").exists()
            print(f"✅ {agent}: {checkpoint_dir}")
            print(f"   Archivos: {num_files}, Final: {'✅' if final_exists else '❌'}")
        else:
            print(f"❌ {agent}: Directorio no encontrado")
            all_ok = False

    print()

    if all_ok:
        print("✅ AMBIENTE VALIDADO - TODO OK PARA ENTRENAMIENTOS")
    else:
        print("⚠️ AMBIENTE INCOMPLETO - Revisa archivos faltantes")

    return all_ok

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys

    print("\n🚀 UTILIDAD DE ENTRENAMIENTO INCREMENTAL\n")

    # Paso 1: Validar ambiente
    if not validate_environment():
        print("\n❌ Ambiente incompleto. Abortando.")
        sys.exit(1)

    # Paso 2: Mostrar info de checkpoints
    show_checkpoint_info()

    # Paso 3: Demostrar resumición (sin ejecutar entrenamiento real)
    print("\n" + "=" * 80)
    print("DEMOSTRACIÓN: CÓMO REANUDAR ENTRENAMIENTO")
    print("=" * 80)

    resume_training(AGENT, CHECKPOINT_PATH, STEPS_TO_ADD)

    # Paso 4: Instrucciones finales
    print(f"\n{'=' * 80}")
    print("PRÓXIMOS PASOS")
    print(f"{'=' * 80}\n")

    print("1. CONSULTAR DATOS:")
    print("   python scripts/query_training_archive.py summary\n")

    print("2. PREPARAR ENTRENAMIENTO:")
    print(f"   python scripts/query_training_archive.py prepare {AGENT} 52560\n")

    print("3. EJECUTAR (descomentar código template arriba)\n")

    print("4. ACTUALIZAR DATOS:")
    print("   (Código incluido en template)\n")

    print("=" * 80)

