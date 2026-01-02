#!/usr/bin/env python3
"""Script definitivo para verificar y ejecutar el entrenamiento con checkpoints."""
import logging
import sys
from pathlib import Path

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("training_verification.log", mode="w", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 80)
    logger.info("VERIFICACIÓN Y EJECUCIÓN DE ENTRENAMIENTO CON CHECKPOINTS")
    logger.info("=" * 80)
    
    # 1. Verificar configuración
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from scripts._common import load_all
    
    cfg, rp = load_all(Path("configs/default.yaml"))
    eval_cfg = cfg["oe3"]["evaluation"]
    
    logger.info("\n[1] CONFIGURACIÓN DE CHECKPOINTS:")
    for agent in ["sac", "ppo", "a2c"]:
        agent_cfg = eval_cfg.get(agent, {})
        freq = agent_cfg.get("checkpoint_freq_steps", "NO DEFINIDO")
        logger.info(f"  {agent.upper()}: checkpoint_freq_steps = {freq}")
    
    # 2. Crear directorios de checkpoint OBLIGATORIOS
    training_dir = rp.analyses_dir / "oe3" / "training"
    checkpoint_dirs = {
        "sac": training_dir / "checkpoints" / "sac",
        "ppo": training_dir / "checkpoints" / "ppo",
        "a2c": training_dir / "checkpoints" / "a2c",
    }
    
    logger.info("\n[2] CREANDO DIRECTORIOS DE CHECKPOINTS:")
    for agent, cp_dir in checkpoint_dirs.items():
        cp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"  {agent.upper()}: {cp_dir} - {'EXISTE' if cp_dir.exists() else 'ERROR'}")
    
    # 3. Verificar archivos de agentes
    logger.info("\n[3] VERIFICANDO ARCHIVOS DE AGENTES:")
    agent_files = [
        "src/iquitos_citylearn/oe3/agents/sac.py",
        "src/iquitos_citylearn/oe3/agents/ppo_sb3.py",
        "src/iquitos_citylearn/oe3/agents/a2c_sb3.py",
        "src/iquitos_citylearn/oe3/simulate.py",
        "scripts/run_oe3_simulate.py",
    ]
    for f in agent_files:
        path = Path(f)
        if path.exists():
            # Verificar sintaxis
            import py_compile
            try:
                py_compile.compile(str(path), doraise=True)
                logger.info(f"  ✓ {f} - OK")
            except py_compile.PyCompileError as e:
                logger.error(f"  ✗ {f} - ERROR DE SINTAXIS: {e}")
                return False
        else:
            logger.error(f"  ✗ {f} - NO EXISTE")
            return False
    
    # 4. Verificar que los agentes están en la lista
    agents_list = eval_cfg.get("agents", [])
    logger.info(f"\n[4] AGENTES A ENTRENAR: {agents_list}")
    
    # 5. Importar y verificar módulos
    logger.info("\n[5] IMPORTANDO MÓDULOS:")
    try:
        from iquitos_citylearn.oe3.agents.sac import SACAgent, make_sac, SACConfig
        logger.info("  ✓ SAC importado correctamente")
    except Exception as e:
        logger.error(f"  ✗ Error importando SAC: {e}")
        return False
    
    try:
        from iquitos_citylearn.oe3.agents.ppo_sb3 import PPOAgent, make_ppo
        logger.info("  ✓ PPO importado correctamente")
    except Exception as e:
        logger.error(f"  ✗ Error importando PPO: {e}")
        return False
    
    try:
        from iquitos_citylearn.oe3.agents.a2c_sb3 import A2CAgent, make_a2c
        logger.info("  ✓ A2C importado correctamente")
    except Exception as e:
        logger.error(f"  ✗ Error importando A2C: {e}")
        return False
    
    # 6. Verificar SACConfig tiene los campos correctos
    logger.info("\n[6] VERIFICANDO SACConfig:")
    test_config = SACConfig(
        checkpoint_dir=str(checkpoint_dirs["sac"]),
        checkpoint_freq_steps=1000,
    )
    logger.info(f"  checkpoint_dir: {test_config.checkpoint_dir}")
    logger.info(f"  checkpoint_freq_steps: {test_config.checkpoint_freq_steps}")
    
    if test_config.checkpoint_dir is None:
        logger.error("  ✗ ERROR: checkpoint_dir es None!")
        return False
    if test_config.checkpoint_freq_steps == 0:
        logger.error("  ✗ ERROR: checkpoint_freq_steps es 0!")
        return False
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ TODAS LAS VERIFICACIONES PASARON")
    logger.info("=" * 80)
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✓ Verificación completada exitosamente.")
        print("  Ejecuta el entrenamiento con:")
        print("  python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset")
    else:
        print("\n✗ Verificación falló. Revisa los errores arriba.")
        sys.exit(1)
