"""
================================================================================
TRANSITION MANAGER - MANEJO ROBUSTO DE TRANSICIONES ENTRE ENTRENAMIENTOS

Objetivo: Garantizar transiciones sin atascos entre SAC → PPO → A2C

Características:
1. Cleanup de memoria después de cada entrenamiento
2. Validación de estado antes de transicionar
3. Reset seguro del environment
4. Manejo de errores sin deadlock
5. Logging detallado para debugging
================================================================================
"""

from __future__ import annotations

import gc
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Tuple
import traceback

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TransitionState:
    """Estado de la transición entre agentes."""
    from_agent: str
    to_agent: str
    timestamp: float
    checkpoint_loaded: bool = False
    memory_freed: bool = False
    env_reset: bool = False
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def is_healthy(self) -> bool:
        """Verifica si la transición fue exitosa."""
        return (
            self.checkpoint_loaded and
            self.memory_freed and
            self.env_reset and
            len(self.errors) == 0
        )

    def add_error(self, error: str) -> None:
        """Registra un error en la transición."""
        if self.errors is None:
            self.errors = []
        self.errors.append(error)
        logger.error("[TRANSITION ERROR] %s → %s: %s", self.from_agent, self.to_agent, error)


class TransitionManager:
    """Maneja transiciones seguras entre entrenamientos.

    Coordina:
    1. Cleanup de agentes anteriores
    2. Validación de checkpoints
    3. Reset de environment
    4. Transición a nuevo agente
    """

    def __init__(self, env: Any, checkpoint_base_dir: Optional[Path] = None):
        self.env = env
        self.checkpoint_base_dir = checkpoint_base_dir or Path("checkpoints")
        self.current_agent: Optional[Any] = None
        self.previous_agent: Optional[Any] = None
        self.transition_history: list[TransitionState] = []

    # =========================================================================
    # LIMPIEZA DE MEMORIA Y RECURSOS
    # =========================================================================

    def cleanup_agent(self, agent: Any, agent_name: str) -> dict[str, Any]:
        """Limpia recursos de un agente de forma segura.

        Args:
            agent: Agente a limpiar (SACAgent, PPOAgent, A2CAgent)
            agent_name: Nombre del agente para logging

        Returns:
            Dict con estado de limpieza
        """
        results = {
            "agent_name": agent_name,
            "model_deleted": False,
            "env_deleted": False,
            "gc_collected": 0,
            "errors": [],
        }

        logger.info("[CLEANUP] Iniciando limpieza de %s", agent_name)

        # 1. Limpiar modelo (SB3)
        try:
            if hasattr(agent, "model") and agent.model is not None:
                logger.debug("[CLEANUP] Liberando modelo SB3...")
                # Detach model from GPU/memory
                if hasattr(agent.model, "policy"):
                    del agent.model.policy
                if hasattr(agent.model, "actor"):
                    del agent.model.actor
                if hasattr(agent.model, "critic"):
                    del agent.model.critic
                if hasattr(agent.model, "critic_target"):
                    del agent.model.critic_target

                # Delete model itself
                del agent.model
                agent.model = None
                results["model_deleted"] = True
                logger.debug("[CLEANUP] ✓ Modelo liberado")
        except Exception as e:
            err_msg = f"Error liberando modelo: {e}"
            errors_list: list[str] = results["errors"]  # type: ignore
            errors_list.append(err_msg)
            logger.warning("[CLEANUP] %s", err_msg)

        # 2. Limpiar environment wrapper
        try:
            if hasattr(agent, "wrapped_env") and agent.wrapped_env is not None:
                logger.debug("[CLEANUP] Liberando wrapped environment...")
                if hasattr(agent.wrapped_env, "close"):
                    agent.wrapped_env.close()
                del agent.wrapped_env
                agent.wrapped_env = None
                results["env_deleted"] = True
                logger.debug("[CLEANUP] ✓ Environment wrapper liberado")
        except Exception as e:
            err_msg = f"Error liberando wrapped_env: {e}"
            errors_list = results["errors"]  # type: ignore
            errors_list.append(err_msg)
            logger.warning("[CLEANUP] %s", err_msg)

        # 3. Limpiar historiales
        try:
            if hasattr(agent, "training_history"):
                agent.training_history.clear()
            logger.debug("[CLEANUP] ✓ Historial limpiado")
        except Exception as e:
            logger.warning("[CLEANUP] Error limpiando historial: %s", e)

        # 4. Garbage collection
        try:
            logger.debug("[CLEANUP] Ejecutando garbage collection...")
            gc.collect()
            results["gc_collected"] = 1
            logger.debug("[CLEANUP] ✓ Garbage collection ejecutado")
        except Exception as e:
            err_msg = f"Error en garbage collection: {e}"
            errors_list = results["errors"]  # type: ignore
            errors_list.append(err_msg)
            logger.warning("[CLEANUP] %s", err_msg)

        # 5. GPU cleanup si está disponible
        try:
            import torch
            if torch.cuda.is_available():
                logger.debug("[CLEANUP] Limpiando GPU memory...")
                torch.cuda.empty_cache()
                logger.debug("[CLEANUP] ✓ GPU memory limpiado")
        except (ImportError, RuntimeError) as e:
            logger.debug("[CLEANUP] GPU cleanup skipped: %s", e)

        elapsed = time.time()
        logger.info("[CLEANUP] ✓ Limpieza de %s completada en %.2fs", agent_name, elapsed)

        return results

    # =========================================================================
    # VALIDACIÓN DE ESTADO
    # =========================================================================

    def validate_env_state(self) -> dict[str, Any]:
        """Valida el estado actual del environment.

        Returns:
            Dict con estado del environment
        """
        state: dict[str, Any] = {
            "env_exists": self.env is not None,
            "env_type": type(self.env).__name__,
            "has_buildings": False,
            "has_action_space": False,
            "has_observation_space": False,
            "errors": [],
        }

        try:
            if hasattr(self.env, "buildings"):
                state["has_buildings"] = len(self.env.buildings) > 0 if self.env.buildings else False

            if hasattr(self.env, "action_space"):
                state["has_action_space"] = self.env.action_space is not None

            if hasattr(self.env, "observation_space"):
                state["has_observation_space"] = self.env.observation_space is not None
        except Exception as e:
            errors_list = state["errors"]  # type: ignore
            errors_list.append(f"Error validando env: {e}")

        return state

    def validate_checkpoint(self, checkpoint_path: Path) -> dict[str, Any]:
        """Valida que un checkpoint sea accesible y legible.

        Args:
            checkpoint_path: Ruta del checkpoint

        Returns:
            Dict con validación
        """
        validation: dict[str, Any] = {
            "path": str(checkpoint_path),
            "exists": checkpoint_path.exists(),
            "readable": False,
            "size_mb": 0.0,
            "is_valid": False,
            "errors": [],
        }

        try:
            if not checkpoint_path.exists():
                errors_list = validation["errors"]  # type: ignore
                errors_list.append(f"Checkpoint no existe: {checkpoint_path}")
                return validation

            if not checkpoint_path.is_file():
                errors_list = validation["errors"]  # type: ignore
                errors_list.append(f"No es archivo: {checkpoint_path}")
                return validation

            # Check file is readable
            if not checkpoint_path.stat().st_size > 0:
                errors_list = validation["errors"]  # type: ignore
                errors_list.append(f"Archivo vacío: {checkpoint_path}")
                return validation

            # Check file extension (should be .zip for SB3)
            if checkpoint_path.suffix not in [".zip", ".pkl"]:
                errors_list = validation["errors"]  # type: ignore
                errors_list.append(f"Extensión inesperada: {checkpoint_path.suffix}")
                return validation

            validation["readable"] = True
            validation["size_mb"] = checkpoint_path.stat().st_size / (1024 * 1024)
            validation["is_valid"] = True

        except Exception as e:
            errors_list = validation["errors"]  # type: ignore
            errors_list.append(f"Error validando checkpoint: {e}")

        return validation

    # =========================================================================
    # RESET DEL ENVIRONMENT
    # =========================================================================

    def reset_environment(self) -> dict[str, Any]:
        """Hace reset seguro del environment.

        Returns:
            Dict con resultado del reset
        """
        reset_result: dict[str, Any] = {
            "reset_success": False,
            "obs_shape": None,
            "errors": [],
        }

        try:
            logger.info("[RESET ENV] Iniciando reset...")

            # Attempt reset with timeout
            if not hasattr(self.env, "reset"):
                errors_list = reset_result["errors"]  # type: ignore
                errors_list.append("Environment no tiene método reset()")
                return reset_result

            obs, info = self.env.reset()
            reset_result["reset_success"] = True

            # Validate observation
            if isinstance(obs, (list, tuple)):
                reset_result["obs_shape"] = f"Tuple of {len(obs)} arrays"
            elif isinstance(obs, np.ndarray):
                reset_result["obs_shape"] = obs.shape
            else:
                reset_result["obs_shape"] = type(obs).__name__

            logger.info("[RESET ENV] ✓ Reset exitoso. Obs shape: %s", reset_result["obs_shape"])

        except Exception as e:
            err_msg = f"Error en reset: {type(e).__name__}: {e}"
            errors_list = reset_result["errors"]  # type: ignore
            errors_list.append(err_msg)
            logger.error("[RESET ENV] ✗ %s", err_msg)
            logger.debug("[RESET ENV] Traceback:\n%s", traceback.format_exc())

        return reset_result

    # =========================================================================
    # TRANSICIÓN ENTRE AGENTES
    # =========================================================================

    def transition(
        self,
        from_agent: Any,
        from_name: str,
        to_name: str,
        validate_checkpoint: bool = True,
    ) -> TransitionState:
        """Ejecuta transición segura entre agentes.

        Args:
            from_agent: Agente anterior (puede ser None)
            from_name: Nombre del agente anterior
            to_name: Nombre del nuevo agente
            validate_checkpoint: Si validar checkpoint del nuevo agente

        Returns:
            TransitionState con resultado
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("[TRANSITION] %s → %s", from_name, to_name)
        logger.info("=" * 80)
        logger.info("")

        state = TransitionState(
            from_agent=from_name,
            to_agent=to_name,
            timestamp=time.time(),
        )

        # Fase 1: Validar environment
        logger.info("[TRANSITION] Fase 1/4: Validar environment...")
        try:
            env_state = self.validate_env_state()
            if not env_state["env_exists"]:
                state.add_error("Environment no existe")
                return state
            logger.info("[TRANSITION] ✓ Environment válido")
        except Exception as e:
            state.add_error(f"Error validando env: {e}")
            return state

        # Fase 2: Cleanup del agente anterior
        logger.info("[TRANSITION] Fase 2/4: Cleanup de agente anterior...")
        try:
            if from_agent is not None:
                cleanup_results = self.cleanup_agent(from_agent, from_name)
                if cleanup_results["errors"]:
                    for err in cleanup_results["errors"]:
                        state.add_error(err)
                    logger.warning(
                        "[TRANSITION] ⚠ Cleanup con %d errores",
                        len(cleanup_results["errors"])
                    )
                else:
                    logger.info("[TRANSITION] ✓ Cleanup completado")
            else:
                logger.info("[TRANSITION] ℹ Sin agente anterior (primera transición)")
        except Exception as e:
            state.add_error(f"Error en cleanup: {e}")
            logger.error("[TRANSITION] ✗ Error en cleanup: %s", e)

        # Fase 3: Reset del environment
        logger.info("[TRANSITION] Fase 3/4: Reset del environment...")
        try:
            reset_result = self.reset_environment()
            errors_in_reset: list[str] = reset_result["errors"]  # type: ignore
            if errors_in_reset:
                for err in errors_in_reset:
                    state.add_error(err)
            else:
                state.env_reset = True
                logger.info("[TRANSITION] ✓ Environment reset exitoso")
        except Exception as e:
            state.add_error(f"Error reseteando env: {e}")
            logger.error("[TRANSITION] ✗ Error en reset: %s", e)

        # Fase 4: Validar checkpoint del nuevo agente
        if validate_checkpoint:
            logger.info("[TRANSITION] Fase 4/4: Validar checkpoint de %s...", to_name)
            try:
                checkpoint_dir = self.checkpoint_base_dir / to_name.lower()
                if checkpoint_dir.exists():
                    final_ckpt = checkpoint_dir / f"{to_name.lower()}_final.zip"
                    if final_ckpt.exists():
                        ckpt_validation = self.validate_checkpoint(final_ckpt)
                        if ckpt_validation["is_valid"]:
                            logger.info(
                                "[TRANSITION] ✓ Checkpoint válido (%.2f MB)",
                                ckpt_validation["size_mb"]
                            )
                            state.checkpoint_loaded = True
                        else:
                            errors_in_ckpt: list[str] = ckpt_validation["errors"]  # type: ignore
                            for err in errors_in_ckpt:
                                state.add_error(err)
                            logger.warning("[TRANSITION] ⚠ Checkpoint inválido")
                    else:
                        logger.info("[TRANSITION] ℹ Checkpoint final no existe (primera ejecución)")
                else:
                    logger.info("[TRANSITION] ℹ Directorio de checkpoints no existe (primera ejecución)")
            except Exception as e:
                state.add_error(f"Error validando checkpoint: {e}")
                logger.warning("[TRANSITION] ⚠ Error validando checkpoint: %s", e)
        else:
            logger.info("[TRANSITION] Fase 4/4: Validación de checkpoint deshabilitada")
            state.checkpoint_loaded = True

        # Marcar limpieza de memoria completada
        state.memory_freed = (len([e for e in state.errors if "memory" in e.lower()]) == 0)

        # Resumen
        logger.info("")
        logger.info("=" * 80)
        logger.info("[TRANSITION RESULTADO] %s → %s", from_name, to_name)
        logger.info("=" * 80)
        if state.is_healthy():
            logger.info("[TRANSITION] ✅ TRANSICIÓN EXITOSA")
        else:
            logger.warning("[TRANSITION] ⚠ TRANSICIÓN CON PROBLEMAS:")
            for error in state.errors:
                logger.warning("  - %s", error)
        logger.info("  from_agent: %s", from_name)
        logger.info("  to_agent: %s", to_name)
        logger.info("  checkpoint_loaded: %s", state.checkpoint_loaded)
        logger.info("  memory_freed: %s", state.memory_freed)
        logger.info("  env_reset: %s", state.env_reset)
        logger.info("  total_errors: %d", len(state.errors))
        logger.info("=" * 80)
        logger.info("")

        self.transition_history.append(state)
        self.current_agent = from_name

        return state

    def get_transition_summary(self) -> dict[str, Any]:
        """Retorna resumen de todas las transiciones."""
        summary: dict[str, Any] = {
            "total_transitions": len(self.transition_history),
            "successful": 0,
            "warnings": 0,
            "failed": 0,
            "transitions": [],
        }

        for state in self.transition_history:
            transition_info: dict[str, Any] = {
                "from_agent": state.from_agent,
                "to_agent": state.to_agent,
                "status": "✅ OK" if state.is_healthy() else "⚠ WARNINGS" if state.errors else "❌ FAILED",
                "error_count": len(state.errors) if state.errors else 0,
            }
            transitions_list: list[dict[str, Any]] = summary["transitions"]  # type: ignore
            transitions_list.append(transition_info)

            successful_count: int = summary["successful"]  # type: ignore
            warnings_count: int = summary["warnings"]  # type: ignore
            failed_count: int = summary["failed"]  # type: ignore

            if state.is_healthy():
                summary["successful"] = successful_count + 1
            elif state.errors:
                summary["warnings"] = warnings_count + 1
            else:
                summary["failed"] = failed_count + 1

        return summary


def create_transition_manager(
    env: Any,
    checkpoint_base_dir: Optional[Path] = None,
) -> TransitionManager:
    """Factory function para crear un TransitionManager."""
    return TransitionManager(env, checkpoint_base_dir or Path("checkpoints"))
