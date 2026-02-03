#!/usr/bin/env python3
"""
================================================================================
SCRIPT: ensure_smooth_transitions.py
PROPOSITO: Asegurar transiciones automáticas fluidas entre agentes SAC → PPO → A2C
CRÍTICO: Evitar que el pipeline se atasque entre agentes
================================================================================
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

def get_completed_agents() -> Set[str]:
    """Obtener agentes completados desde sus archivos result.json."""
    outputs_dir = Path("outputs/oe3_simulations")
    completed: Set[str] = set()

    for agent in ["SAC", "PPO", "A2C", "uncontrolled"]:
        result_file = outputs_dir / f"result_{agent}.json"
        if result_file.exists():
            try:
                data = json.loads(result_file.read_text(encoding="utf-8"))
                if data.get("steps", 0) >= 8760:  # Full episode completed
                    completed.add(agent)
                    print(f"   ✅ {agent}: Completado ({data.get('steps', 0)} steps)")
                else:
                    print(f"   ⏸️ {agent}: Incompleto ({data.get('steps', 0)} steps)")
            except Exception as e:
                print(f"   ❌ {agent}: Error leyendo result ({e})")
        else:
            print(f"   ⏳ {agent}: No iniciado (sin result.json)")

    return completed

def get_training_processes() -> List[int]:
    """Obtener PIDs de procesos de entrenamiento Python."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Select-Object -ExpandProperty Id"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = [int(line.strip()) for line in result.stdout.strip().split('\n') if line.strip().isdigit()]
            return pids
        return []
    except Exception:
        return []

def kill_zombie_processes() -> None:
    """Eliminar procesos zombie de entrenamiento."""
    pids = get_training_processes()
    if not pids:
        print("   ✅ No hay procesos Python activos")
        return

    print(f"   🔄 Eliminando {len(pids)} procesos Python: {pids}")
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                         capture_output=True, timeout=10)
        except Exception:
            pass

    # Verificar eliminación
    time.sleep(2)
    remaining = get_training_processes()
    if remaining:
        print(f"   ⚠️ Procesos restantes: {remaining}")
    else:
        print("   ✅ Todos los procesos eliminados")

def check_pipeline_status() -> Dict[str, Any]:
    """Verificar estado completo del pipeline."""
    completed: Set[str] = get_completed_agents()
    training_pids: List[int] = get_training_processes()

    # Determinar siguiente agente
    next_agent: Optional[str] = None
    if "SAC" not in completed:
        next_agent = "SAC"
    elif "PPO" not in completed:
        next_agent = "PPO"
    elif "A2C" not in completed:
        next_agent = "A2C"

    return {
        "completed": completed,
        "training_pids": training_pids,
        "next_agent": next_agent,
        "pipeline_stuck": len(training_pids) == 0 and next_agent is not None,
        "all_complete": next_agent is None
    }

def ensure_transition_continuity() -> bool:
    """Asegurar que las transiciones automáticas funcionen correctamente."""
    print("\n🔄 VERIFICANDO CONTINUIDAD DE TRANSICIONES")
    print("="*80)

    status: Dict[str, Any] = check_pipeline_status()

    print("\n📊 ESTADO ACTUAL:")
    completed: Set[str] = status['completed']  # type: ignore
    completed_str: str = ', '.join(completed) if completed else 'Ninguno'
    print(f"   ✅ Completados: {completed_str}")
    training_pids: List[int] = status['training_pids']  # type: ignore
    print(f"   🔧 Procesos activos: {len(training_pids)} PIDs: {training_pids}")
    next_agent: Optional[str] = status['next_agent']  # type: ignore
    next_agent_str: str = str(next_agent) if next_agent else 'TODOS COMPLETADOS'
    print(f"   ➡️ Siguiente agente: {next_agent_str}")
    stuck: bool = status['pipeline_stuck']  # type: ignore
    stuck_str: str = 'Sí' if stuck else 'NO'
    print(f"   💨 Pipeline atascado: {stuck_str}")

    # CASO 1: Pipeline atascado → Relanzar
    if stuck:
        print("\n🚨 PIPELINE ATASCADO → Relanzando automáticamente")
        kill_zombie_processes()
        return False  # Indica que necesita relanzar

    # CASO 2: Procesos activos pero posible problema de transición
    elif training_pids and len(completed) > 0:
        print("\n✅ PIPELINE FUNCIONANDO (transición en progreso)")
        print(f"   Agentes completados: {completed}")
        print(f"   Siguiente: {next_agent}")
        return True

    # CASO 3: Todo completado
    elif status['all_complete']:  # type: ignore
        print("\n🎉 PIPELINE COMPLETADO")
        print("   Todos los agentes (SAC, PPO, A2C) han terminado")
        return True

    # CASO 4: Pipeline funcionando normalmente
    else:
        print(f"\n✅ PIPELINE FUNCIONANDO NORMALMENTE")
        if next_agent:
            print(f"   Siguiente: {next_agent}")
        return True

def launch_training_pipeline() -> Optional[subprocess.Popen[str]]:
    """Lanzar el pipeline completo de entrenamiento."""
    print("\n🚀 LANZANDO PIPELINE DE ENTRENAMIENTO")
    print("="*80)

    cmd = [
        sys.executable,
        "scripts/run_oe3_simulate.py",
        "--config", "configs/default.yaml",
        "--skip-baseline",  # Ya tenemos baseline
    ]

    print(f"Comando: {' '.join(cmd)}")
    print("⏳ Iniciando entrenamiento completo SAC → PPO → A2C...")

    try:
        # Lanzar en modo no-bloqueante
        process: subprocess.Popen[str] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        print(f"✅ Pipeline iniciado (PID: {process.pid})")
        return process

    except Exception as e:
        print(f"❌ Error lanzando pipeline: {e}")
        return None


def monitor_transitions(max_wait_minutes: int = 120) -> None:
    """Monitorear transiciones automáticas durante el entrenamiento."""
    print(f"\n👁️ MONITOREANDO TRANSICIONES (máximo {max_wait_minutes} minutos)")
    print("="*80)

    start_time = time.time()
    last_status: Optional[Dict[str, Any]] = None

    while (time.time() - start_time) < (max_wait_minutes * 60):
        current_status: Dict[str, Any] = check_pipeline_status()

        # Solo reportar cambios
        if current_status != last_status:
            completed: Set[str] = current_status['completed']  # type: ignore
            next_agent: Optional[str] = current_status['next_agent']  # type: ignore

            print(f"\n[{time.strftime('%H:%M:%S')}] CAMBIO DE ESTADO:")
            print(f"   Completados: {', '.join(completed) if completed else 'Ninguno'}")
            print(f"   Siguiente: {next_agent or 'TODOS COMPLETADOS'}")

            all_complete: bool = current_status['all_complete']  # type: ignore
            if all_complete:
                print("\n🎉 MONITOREO COMPLETADO - Todos los agentes terminaron")
                return

            last_status = current_status

        # Verificar si pipeline está atascado
        pipeline_stuck: bool = current_status['pipeline_stuck']  # type: ignore
        if pipeline_stuck:
            print(f"\n⚠️ PIPELINE POTENCIALMENTE ATASCADO")
            print(f"   Siguiente agente: {current_status['next_agent']}")
            print(f"   Procesos activos: {len(current_status['training_pids'])}")
            print("   🔄 Esperando a que continúe...")

        time.sleep(30)

    print("\n⏱️ TIMEOUT ALCANZADO")


def main() -> bool:
    """Función principal - Asegurar transiciones automáticas correctas."""
    print("\n🎯 ASEGURANDO TRANSICIÓN AUTOMÁTICA CORRECTA")
    print("="*80)
    print(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Verificar estado actual y tomar acción
    continuity_ok: bool = ensure_transition_continuity()

    if not continuity_ok:
        # Pipeline necesita relanzarse
        print("\n🔄 RELANZANDO PIPELINE PARA CORREGIR TRANSICIONES")
        process: Optional[subprocess.Popen[str]] = launch_training_pipeline()
        if process:
            # Monitorear las transiciones
            monitor_transitions()
            return True
        else:
            print("❌ No se pudo relanzar el pipeline")
            return False
    else:
        print("\n✅ TRANSICIONES AUTOMÁTICAS FUNCIONANDO CORRECTAMENTE")
        # Si hay procesos activos, monitorear por si acaso
        status: Dict[str, Any] = check_pipeline_status()
        training_pids: List[int] = status['training_pids']  # type: ignore
        all_complete_bool: bool = status['all_complete']  # type: ignore
        if training_pids and not all_complete_bool:
            print("👁️ Monitoreando pipeline activo...")
            monitor_transitions()
        return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Monitoreo interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)
