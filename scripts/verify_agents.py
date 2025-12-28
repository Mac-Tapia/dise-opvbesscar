#!/usr/bin/env python3
"""
Script para verificar que todos los agentes OE3 funcionan correctamente.

Verifica:
1. Importación correcta de cada agente
2. Creación de instancias con mock environment
3. Interfaz de predict/act
4. Generación de acciones válidas
5. Aprendizaje (para agentes que lo soportan)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to Python path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from typing import Any, List, Optional
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MockActionSpace:
    """Mock de gymnasium.spaces.Box para testing."""
    
    def __init__(self, low: float = -1.0, high: float = 1.0, shape: tuple = (4,)):
        self.low = np.full(shape, low, dtype=np.float32)
        self.high = np.full(shape, high, dtype=np.float32)
        self.shape = shape
    
    def sample(self) -> np.ndarray:
        return np.random.uniform(self.low, self.high).astype(np.float32)


class MockEnv:
    """Mock de CityLearnEnv para testing de agentes."""
    
    def __init__(self, n_buildings: int = 1, n_actions_per_building: int = 4):
        self.n_buildings = n_buildings
        self.n_actions_per_building = n_actions_per_building
        
        # Action space (lista de Box para CityLearn centralizado)
        self.action_space = [
            MockActionSpace(shape=(n_actions_per_building,))
            for _ in range(n_buildings)
        ]
        
        # Action names (importante para RBC y NoControl)
        self.action_names = [
            [
                "electric_vehicle_charger_0",
                "electric_vehicle_charger_1", 
                "electrical_storage",
                "other_action",
            ]
            for _ in range(n_buildings)
        ]
        
        # Action dimension (fallback para NoControl)
        self.action_dimension = [(n_actions_per_building,) for _ in range(n_buildings)]
        
        self.observation_space = [
            MockActionSpace(shape=(20,))  # Mock de observaciones
            for _ in range(n_buildings)
        ]
        
        self.time_step = 0
    
    def reset(self) -> tuple:
        """Reset del environment."""
        self.time_step = 0
        obs = [np.random.randn(20).astype(np.float32) for _ in range(self.n_buildings)]
        info = {}
        return obs, info
    
    def step(self, action: Any) -> tuple:
        """Step del environment."""
        self.time_step += 1
        obs = [np.random.randn(20).astype(np.float32) for _ in range(self.n_buildings)]
        reward = [np.random.randn() for _ in range(self.n_buildings)]
        terminated = self.time_step >= 100
        truncated = False
        info = {}
        return obs, reward, terminated, truncated, info
    
    def close(self):
        """Cerrar environment."""
        pass


def verify_agent_import(agent_name: str) -> bool:
    """Verifica que el agente se puede importar."""
    try:
        if agent_name == "UncontrolledChargingAgent":
            from iquitos_citylearn.oe3.agents import UncontrolledChargingAgent
            return True
        elif agent_name == "NoControlAgent":
            from iquitos_citylearn.oe3.agents import NoControlAgent
            return True
        elif agent_name == "BasicRBCAgent":
            from iquitos_citylearn.oe3.agents import BasicRBCAgent
            return True
        elif agent_name == "SACAgent":
            from iquitos_citylearn.oe3.agents import SACAgent
            return True
        elif agent_name == "PPOAgent":
            from iquitos_citylearn.oe3.agents import PPOAgent
            return True
        elif agent_name == "A2CAgent":
            from iquitos_citylearn.oe3.agents import A2CAgent
            return True
        else:
            logger.error(f"Agente desconocido: {agent_name}")
            return False
    except ImportError as e:
        logger.error(f"Error importando {agent_name}: {e}")
        return False


def verify_agent_creation(agent_name: str, env: MockEnv) -> Optional[Any]:
    """Verifica que el agente se puede crear."""
    try:
        if agent_name == "UncontrolledChargingAgent":
            from iquitos_citylearn.oe3.agents import UncontrolledChargingAgent
            agent = UncontrolledChargingAgent(env)
            return agent
        elif agent_name == "NoControlAgent":
            from iquitos_citylearn.oe3.agents import make_no_control
            agent = make_no_control(env)
            return agent
        elif agent_name == "BasicRBCAgent":
            from iquitos_citylearn.oe3.agents import make_basic_ev_rbc
            agent = make_basic_ev_rbc(env)
            return agent
        elif agent_name == "SACAgent":
            from iquitos_citylearn.oe3.agents import make_sac, SACConfig
            config = SACConfig(
                episodes=1,
                batch_size=32,
                learning_rate=3e-4,
                device="cpu",
            )
            agent = make_sac(env, config=config)
            return agent
        elif agent_name == "PPOAgent":
            from iquitos_citylearn.oe3.agents import make_ppo, PPOConfig
            config = PPOConfig(
                train_steps=100,
                n_steps=32,
                batch_size=16,
                device="cpu",
            )
            agent = make_ppo(env, config=config)
            return agent
        elif agent_name == "A2CAgent":
            from iquitos_citylearn.oe3.agents import make_a2c, A2CConfig
            config = A2CConfig(
                train_steps=100,
                n_steps=32,
                device="cpu",
            )
            agent = make_a2c(env, config=config)
            return agent
        else:
            logger.error(f"Agente desconocido: {agent_name}")
            return None
    except Exception as e:
        logger.error(f"Error creando {agent_name}: {e}")
        return None


def verify_agent_predict(agent: Any, env: MockEnv) -> bool:
    """Verifica que el agente puede generar acciones."""
    try:
        obs, _ = env.reset()
        
        # Verificar método predict
        if hasattr(agent, "predict"):
            action = agent.predict(obs, deterministic=True)
        elif hasattr(agent, "act"):
            action = agent.act(obs)
        else:
            logger.error("Agente no tiene método predict() ni act()")
            return False
        
        # Validar formato de acción
        if not isinstance(action, list):
            logger.error(f"Acción debe ser lista, recibido: {type(action)}")
            return False
        
        if len(action) != len(env.action_space):
            logger.error(f"Longitud de acción incorrecta: {len(action)} vs {len(env.action_space)}")
            return False
        
        # Validar cada sub-acción
        for i, (act, space) in enumerate(zip(action, env.action_space)):
            if isinstance(act, list):
                act = np.array(act)
            
            if not isinstance(act, (list, np.ndarray)):
                logger.error(f"Sub-acción {i} debe ser lista o array, recibido: {type(act)}")
                return False
            
            act_arr = np.array(act)
            if act_arr.shape[0] != space.shape[0]:
                logger.error(f"Sub-acción {i} tiene forma incorrecta: {act_arr.shape} vs {space.shape}")
                return False
        
        logger.info(f"  ✓ predict() genera acciones válidas")
        return True
        
    except Exception as e:
        logger.error(f"Error en predict(): {e}")
        return False


def verify_agent_episode(agent: Any, env: MockEnv, n_steps: int = 10) -> bool:
    """Verifica que el agente puede ejecutar un episodio completo."""
    try:
        obs, _ = env.reset()
        
        for step in range(n_steps):
            if hasattr(agent, "predict"):
                action = agent.predict(obs, deterministic=True)
            elif hasattr(agent, "act"):
                action = agent.act(obs)
            else:
                return False
            
            obs, reward, terminated, truncated, _ = env.step(action)
            
            if terminated or truncated:
                break
        
        logger.info(f"  ✓ Episodio de {step + 1} pasos ejecutado correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error ejecutando episodio: {e}")
        return False


def verify_agent_learn(agent: Any, agent_name: str) -> bool:
    """Verifica el método learn() para agentes de RL."""
    try:
        # Solo agentes de RL tienen learn()
        if agent_name in ["SACAgent", "PPOAgent", "A2CAgent"]:
            if not hasattr(agent, "learn"):
                logger.error("Agente de RL debe tener método learn()")
                return False
            logger.info(f"  ✓ Método learn() disponible")
        else:
            # Agentes baseline no requieren learn()
            if hasattr(agent, "learn"):
                agent.learn(episodes=0)  # Debe ser no-op
            logger.info(f"  ✓ Agente baseline (no requiere learn)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error verificando learn(): {e}")
        return False


def verify_agent(agent_name: str) -> bool:
    """Verificación completa de un agente."""
    logger.info(f"\n{'='*60}")
    logger.info(f"VERIFICANDO: {agent_name}")
    logger.info(f"{'='*60}")
    
    # 1. Verificar importación
    if not verify_agent_import(agent_name):
        logger.error(f"✗ {agent_name}: Fallo en importación")
        return False
    logger.info(f"  ✓ Importación exitosa")
    
    # 2. Crear mock environment
    env = MockEnv(n_buildings=1, n_actions_per_building=4)
    
    # 3. Verificar creación
    agent = verify_agent_creation(agent_name, env)
    if agent is None:
        logger.error(f"✗ {agent_name}: Fallo en creación")
        return False
    logger.info(f"  ✓ Instancia creada correctamente")
    
    # 4. Verificar predict
    if not verify_agent_predict(agent, env):
        logger.error(f"✗ {agent_name}: Fallo en predict()")
        return False
    
    # 5. Verificar episodio completo
    if not verify_agent_episode(agent, env, n_steps=10):
        logger.error(f"✗ {agent_name}: Fallo ejecutando episodio")
        return False
    
    # 6. Verificar learn
    if not verify_agent_learn(agent, agent_name):
        logger.error(f"✗ {agent_name}: Fallo en learn()")
        return False
    
    logger.info(f"✅ {agent_name}: TODAS LAS VERIFICACIONES PASARON")
    return True


def main():
    """Verificación de todos los agentes."""
    logger.info("="*60)
    logger.info("  VERIFICACIÓN DE AGENTES OE3")
    logger.info("="*60)
    
    # Lista de agentes a verificar
    agents_to_verify = [
        "UncontrolledChargingAgent",  # Baseline original
        "NoControlAgent",              # Baseline alternativo
        "BasicRBCAgent",               # Rule-based controller
        "SACAgent",                    # RL: Soft Actor-Critic
        "PPOAgent",                    # RL: Proximal Policy Optimization
        "A2CAgent",                    # RL: Advantage Actor-Critic
    ]
    
    results = {}
    for agent_name in agents_to_verify:
        try:
            success = verify_agent(agent_name)
            results[agent_name] = success
        except Exception as e:
            logger.error(f"Error verificando {agent_name}: {e}")
            results[agent_name] = False
    
    # Resumen
    logger.info("\n" + "="*60)
    logger.info("  RESUMEN DE VERIFICACIÓN")
    logger.info("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for agent_name, success in results.items():
        icon = "✅" if success else "❌"
        logger.info(f"  {icon} {agent_name}")
    
    logger.info(f"\n  Total: {passed}/{total} agentes pasaron la verificación")
    
    if passed == total:
        logger.info("\n  🎉 TODOS LOS AGENTES FUNCIONAN CORRECTAMENTE")
        return 0
    else:
        logger.error(f"\n  ⚠️  {total - passed} AGENTE(S) FALLARON")
        return 1


if __name__ == "__main__":
    sys.exit(main())
