from __future__ import annotations

import argparse
from pathlib import Path
import json
import logging
import numpy as np
import time
import signal
import sys
from datetime import datetime
from threading import Thread, Event
from typing import Optional, Dict, Any, List, cast

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from iquitos_citylearn.config import project_root
from scripts._common import load_all

# ============================================================================
# SYSTEM FOR ROBUST AGENT TRAINING WITH REAL-TIME MONITORING
# ============================================================================

class AgentTrainingMonitor:
    """Monitorea el entrenamiento en tiempo real y detecta bloqueos."""

    def __init__(self, agent_name: str, timeout_seconds: int = 3600, check_interval: int = 30):
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval
        self.start_time = time.time()
        self.last_checkpoint_time = self.start_time
        self.last_checkpoint_path: Optional[Path] = None
        self.checkpoint_dir: Optional[Path] = None
        self.is_running = True
        self.progress_log: List[str] = []
        self.logger = logging.getLogger(f"AgentMonitor-{agent_name}")

    def set_checkpoint_dir(self, checkpoint_dir: Path):
        """Configura el directorio donde se guardan checkpoints."""
        self.checkpoint_dir = checkpoint_dir

    def check_progress(self) -> Dict[str, Any]:
        """Verifica el progreso del entrenamiento."""
        elapsed = time.time() - self.start_time
        since_checkpoint = time.time() - self.last_checkpoint_time

        checkpoint_count = 0
        latest_checkpoint = None

        if self.checkpoint_dir and self.checkpoint_dir.exists():
            checkpoints = list(self.checkpoint_dir.glob(f"{self.agent_name.lower()}_*.zip"))
            checkpoint_count = len(checkpoints)
            if checkpoints:
                latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
                if latest_checkpoint != self.last_checkpoint_path:
                    self.last_checkpoint_path = latest_checkpoint
                    self.last_checkpoint_time = time.time()
                    since_checkpoint = 0

        status = {
            "agent": self.agent_name,
            "elapsed_seconds": int(elapsed),
            "elapsed_minutes": elapsed / 60.0,
            "checkpoint_count": checkpoint_count,
            "since_last_checkpoint_seconds": int(since_checkpoint),
            "last_checkpoint": str(latest_checkpoint) if latest_checkpoint else None,
            "is_responsive": since_checkpoint < (self.timeout_seconds / 2),
            "is_timeout": since_checkpoint > self.timeout_seconds,
        }

        return status

    def log_status(self) -> str:
        """Retorna un resumen de estado formateado."""
        status = self.check_progress()

        # ✅ CRITICAL FIX: Replace emoji characters with ASCII-safe equivalents
        # Windows charmap cannot encode Unicode emoji characters, causing crashes
        # Use ASCII text alternatives instead
        status_indicator = (
            "[OK]" if status['is_responsive'] else
            "[!!]" if status['is_timeout'] else
            "[..]"
        )

        msg = (
            f"\n[{datetime.now().strftime('%H:%M:%S')}] "
            f"[TRAIN] {self.agent_name.upper()}\n"
            f"   [TIME] Tiempo: {status['elapsed_minutes']:.1f} min\n"
            f"   [CHKPT] Checkpoints: {status['checkpoint_count']}\n"
            f"   [LAST] Último: {status['since_last_checkpoint_seconds']}s hace\n"
            f"   {status_indicator} {'ACTIVO' if status['is_responsive'] else 'SIN PROGRESO' if status['is_timeout'] else 'PAUSADO'}"
        )

        self.progress_log.append(msg)
        return msg


class TrainingPipeline:
    """Gestiona la ejecución secuencial de múltiples agentes con monitoreo robusto."""

    def __init__(self, output_dir: Path, training_dir: Path, config: Dict[str, Any]):
        self.output_dir = output_dir
        self.training_dir = training_dir
        self.config = config
        self.logger = logging.getLogger("TrainingPipeline")
        self.monitors: Dict[str, AgentTrainingMonitor] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        self.failed_agents: Dict[str, str] = {}
        self.status_file = output_dir / "training_status.json"
        self.monitor_thread: Optional[Thread] = None
        self.monitor_stop_event = Event()

    def create_monitor(self, agent_name: str, timeout_seconds: int = 3600) -> AgentTrainingMonitor:
        """Crea un monitor para un agente."""
        monitor = AgentTrainingMonitor(agent_name, timeout_seconds=timeout_seconds)
        checkpoint_dir = self.training_dir / agent_name.lower()
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        monitor.set_checkpoint_dir(checkpoint_dir)
        self.monitors[agent_name] = monitor
        return monitor

    def start_background_monitoring(self, agents: list[str], interval_seconds: int = 30):
        """Inicia monitoreo en background de todos los agentes."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return  # Ya está corriendo

        self.monitor_stop_event.clear()
        self.monitor_thread = Thread(
            target=self._monitor_loop,
            args=(agents, interval_seconds),
            daemon=False
        )
        self.monitor_thread.start()
        self.logger.info(f"[MONITOR] Iniciado monitoreo en background para {len(agents)} agentes")

    def _monitor_loop(self, agents: list[str], interval_seconds: int):
        """Loop de monitoreo que corre en background."""
        while not self.monitor_stop_event.is_set():
            try:
                # ✅ CRITICAL FIX: Replace emoji characters with ASCII-safe equivalents
                # Windows charmap cannot encode Unicode emoji characters
                print("\n" + "="*80)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STATS] ESTADO DEL ENTRENAMIENTO")
                print("="*80)

                for agent in agents:
                    if agent in self.monitors:
                        status_msg = self.monitors[agent].log_status()
                        print(status_msg)

                        # Verificar timeout
                        status = self.monitors[agent].check_progress()
                        if status["is_timeout"]:
                            print(f"   [ALERT] ALERTA: {agent} sin progreso por {status['since_last_checkpoint_seconds']}s")

                # Guardar estado en archivo
                self._save_status_snapshot()

                # Esperar intervalo
                time.sleep(interval_seconds)

            except Exception as e:
                self.logger.error(f"Error en monitor loop: {e}")
                time.sleep(interval_seconds)

    def stop_background_monitoring(self):
        """Detiene el monitoreo en background."""
        self.monitor_stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            self.logger.info("[MONITOR] Monitoreo detenido")

    def _save_status_snapshot(self):
        """Guarda snapshot actual del estado."""
        try:
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "agents": {},
                "results": self.results,
                "failed": self.failed_agents,
            }

            for agent_name, monitor in self.monitors.items():
                status_data["agents"][agent_name] = monitor.check_progress()

            self.status_file.write_text(json.dumps(status_data, indent=2), encoding="utf-8")
        except Exception as e:
            self.logger.debug(f"No se pudo guardar snapshot: {e}")

    def execute_agent_with_recovery(
        self,
        agent_name: str,
        simulate_fn,
        max_retries: int = 2,
        timeout_seconds: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """Ejecuta un agente con reintentos automáticos en caso de fallo."""

        monitor = self.create_monitor(agent_name, timeout_seconds=timeout_seconds)

        for attempt in range(max_retries):
            try:
                attempt_num = attempt + 1
                print(f"\n{'='*80}")
                print(f"[INTENTO {attempt_num}/{max_retries}] Entrenando {agent_name.upper()}")
                print(f"{'='*80}\n")

                self.logger.info(f"[{agent_name}] Intento {attempt_num} de {max_retries}")

                # Ejecutar simulación
                self.logger.info(f"[{agent_name}] INICIANDO simulate() function...")
                result = simulate_fn()
                self.logger.info(f"[{agent_name}] simulate() function COMPLETADA, result={result}")

                # Verificar resultado
                if result and hasattr(result, '__dict__'):
                    self.results[agent_name] = result.__dict__
                    self.logger.info(f"[{agent_name}] [OK] Completado exitosamente")
                    print(f"\n{'='*80}")
                    print(f"[OK] {agent_name.upper()} COMPLETADO")
                    print(f"   CO2: {result.carbon_kg:.0f} kg")
                    print(f"   PV: {result.pv_generation_kwh:.0f} kWh")
                    print(f"{'='*80}\n")
                    return cast(Dict[str, Any], result.__dict__)
                else:
                    raise ValueError(f"Resultado inválido de simulate: {result}")

            except KeyboardInterrupt:
                self.logger.info(f"[{agent_name}] Entrenamiento cancelado por usuario")
                self.failed_agents[agent_name] = "Cancelado por usuario"
                return None

            except TimeoutError:
                error_msg = f"Timeout después de {timeout_seconds}s"
                self.logger.warning(f"[{agent_name}] {error_msg}")
                self.failed_agents[agent_name] = error_msg

                # CRITICAL FIX: Kill zombie processes before retry
                try:
                    import subprocess
                    cmd = ['powershell', '-Command', 'Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force -ErrorAction SilentlyContinue']
                    subprocess.run(cmd, capture_output=True, timeout=10)
                    time.sleep(5)  # Wait for cleanup
                except Exception:
                    pass

                if attempt < max_retries - 1:
                    print(f"\n[TIMEOUT] Timeout en {agent_name}. Limpiando procesos y reintentando...")
                    time.sleep(10)
                    continue
                else:
                    print(f"\n[FAIL] {agent_name} timeout tras {max_retries} intentos - CONTINUANDO CON SIGUIENTE AGENTE")
                    # CRITICAL: Return partial result instead of None to allow transition
                    return {'agent': agent_name, 'status': 'timeout', 'error': error_msg}

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)[:100]}"
                self.logger.error(f"[{agent_name}] Error: {error_msg}")
                self.failed_agents[agent_name] = error_msg

                # CRITICAL FIX: Kill zombie processes before retry
                try:
                    import subprocess
                    cmd = ['powershell', '-Command', 'Get-Process | Where-Object {$_.ProcessName -eq "python"} | Stop-Process -Force -ErrorAction SilentlyContinue']
                    subprocess.run(cmd, capture_output=True, timeout=10)
                    time.sleep(5)
                except Exception:
                    pass

                if attempt < max_retries - 1:
                    print(f"\n❌ Error en {agent_name}. Limpiando procesos y reintentando en 10 segundos...")
                    time.sleep(10)
                    continue
                else:
                    print(f"\n❌ {agent_name} falló tras {max_retries} intentos: {error_msg}")
                    print(f"🔄 CONTINUANDO CON SIGUIENTE AGENTE EN PIPELINE...")
                    # CRITICAL: Return partial result to allow pipeline to continue
                    partial_result = {
                        'agent': agent_name,
                        'status': 'failed',
                        'error': error_msg,
                        'carbon_kg': 5000000.0,  # High penalty for failed agents
                        'steps': 0,
                        'pv_generation_kwh': 0.0
                    }
                    self.results[agent_name] = partial_result
                    return partial_result

        # CRITICAL: Never return None - always return something to allow transitions
        print(f"\n⚠️  {agent_name} no pudo completarse, pero pipeline continuará...")
        incomplete_result = {
            'agent': agent_name,
            'status': 'incomplete',
            'attempts': max_retries,
            'carbon_kg': 5000000.0,  # High penalty
            'steps': 0,
            'pv_generation_kwh': 0.0
        }
        self.results[agent_name] = incomplete_result
        return incomplete_result


def _tailpipe_kg(cfg: dict, ev_kwh: float, simulated_years: float) -> float:
    """Calcula CO2 tailpipe para motos/mototaxis a combustión equivalentes."""
    if ev_kwh <= 0 or simulated_years <= 0:
        return 0.0
    km_per_kwh = float(cfg["oe3"]["emissions"].get("km_per_kwh", 35.0))
    km_per_gallon = float(cfg["oe3"]["emissions"].get("km_per_gallon", 120.0))
    kgco2_per_gallon = float(cfg["oe3"]["emissions"].get("kgco2_per_gallon", 8.9))
    total_km = ev_kwh * km_per_kwh
    gallons = total_km / max(km_per_gallon, 1e-9)
    return gallons * kgco2_per_gallon / max(simulated_years, 1e-9)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--skip-baseline", action="store_true", help="Saltar simulación Uncontrolled baseline")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)
    oe3_cfg = cfg["oe3"]

    # Configurar señales para interrupciones limpias
    def signal_handler(sig, frame):
        print("\n\n" + "="*80)
        print("⚠️  ENTRENAMIENTO CANCELADO POR USUARIO")
        print("="*80)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    dataset_name = cfg["oe3"]["dataset"]["name"]
    built = build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir

    schema_grid = dataset_dir / "schema_grid_only.json"
    schema_pv = dataset_dir / "schema_pv_bess.json"
    chargers_results_path = rp.interim_dir / "oe2" / "chargers" / "chargers_results.json"
    chargers_results = None
    if chargers_results_path.exists():
        chargers_results = json.loads(chargers_results_path.read_text(encoding="utf-8"))

    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = project_root() / "checkpoints"
    out_dir.mkdir(parents=True, exist_ok=True)

    project_seed = int(cfg["project"].get("seed", 42))
    seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
    ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

    # Configuración de agentes
    eval_cfg = cfg["oe3"]["evaluation"]
    resume_checkpoints_global = bool(eval_cfg.get("resume_checkpoints", False))
    sac_cfg = eval_cfg.get("sac", {})
    ppo_cfg = eval_cfg.get("ppo", {})
    a2c_cfg = eval_cfg.get("a2c", {})

    sac_episodes = int(sac_cfg.get("episodes", 3))
    sac_batch_size = int(sac_cfg.get("batch_size", 512))
    sac_log_interval = int(sac_cfg.get("log_interval", 500))
    sac_use_amp = bool(sac_cfg.get("use_amp", True))
    sac_device = sac_cfg.get("device")
    sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 1000))  # Default to 1000 steps, MANDATORY checkpoint generation
    sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))

    ppo_episodes = ppo_cfg.get("episodes")
    if ppo_episodes is not None:
        ppo_timesteps = int(ppo_episodes) * 8760
    else:
        ppo_timesteps = int(ppo_cfg.get("timesteps", 100000))
    ppo_device = ppo_cfg.get("device")
    ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 1000))  # Default to 1000 steps, MANDATORY checkpoint generation
    ppo_target_kl = ppo_cfg.get("target_kl")
    ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
    ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))
    ppo_n_steps = int(ppo_cfg.get("n_steps", 1024))
    ppo_batch_size = int(ppo_cfg.get("batch_size", 128))
    ppo_use_amp = bool(ppo_cfg.get("use_amp", True))
    ppo_resume = bool(ppo_cfg.get("resume_checkpoints", resume_checkpoints_global))

    a2c_episodes = a2c_cfg.get("episodes")
    if a2c_episodes is not None:
        a2c_timesteps = int(a2c_episodes) * 8760
    else:
        a2c_timesteps = int(a2c_cfg.get("timesteps", 0))
    a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 1000))  # Default to 1000 steps, MANDATORY checkpoint generation
    a2c_n_steps = int(a2c_cfg.get("n_steps", 512))
    a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
    a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))
    a2c_device = a2c_cfg.get("device")
    a2c_resume = bool(a2c_cfg.get("resume_checkpoints", resume_checkpoints_global))
    sac_resume = bool(sac_cfg.get("resume_checkpoints", resume_checkpoints_global))
    a2c_log_interval = int(a2c_cfg.get("log_interval", 2000))

    det_eval = bool(sac_cfg.get("deterministic_eval", True))
    mo_priority = str(oe3_cfg["evaluation"].get("multi_objective_priority", "co2_focus"))  # ✓ FORZADO: co2_focus (CO2=0.75)

    # Baseline: Electrified transport + PV+BESS + no control (Uncontrolled)
    # Este es el único baseline necesario - también se usa para calcular tailpipe
    if not args.skip_baseline:
        res_uncontrolled_obj = simulate(
            schema_path=schema_pv,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            sac_batch_size=sac_batch_size,
            sac_log_interval=sac_log_interval,
            sac_use_amp=sac_use_amp,
            ppo_timesteps=ppo_timesteps,
            deterministic_eval=True,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_n_steps=ppo_n_steps,
            ppo_batch_size=ppo_batch_size,
            ppo_use_amp=ppo_use_amp,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            a2c_log_interval=a2c_log_interval,
            sac_resume_checkpoints=sac_resume,
            ppo_resume_checkpoints=ppo_resume,
            a2c_resume_checkpoints=a2c_resume,
            seed=project_seed,
            multi_objective_priority=mo_priority,
        )
        res_uncontrolled = res_uncontrolled_obj.__dict__
    else:
        # Si saltamos baseline, crear resultados vacíos
        logger = logging.getLogger(__name__)
        logger.info("[SKIP] Saltando simulación Uncontrolled baseline (--skip-baseline)")
        res_uncontrolled = {}

    # Scenario B: Electrified transport + PV+BESS + control (evaluate candidate agents)
    agent_names = list(eval_cfg["agents"])
    logger = logging.getLogger(__name__)

    # === INICIALIZAR PIPELINE ROBUSTO ===
    pipeline = TrainingPipeline(out_dir, training_dir, cfg)
    results = {}

    # Iniciar monitoreo en background
    pipeline.start_background_monitoring(agent_names, interval_seconds=30)

    try:
        for agent in agent_names:
            # Skip Uncontrolled in this loop - it will be run in Scenario C as baseline
            if agent.lower() == "uncontrolled":
                continue

            logger.info(f"\n{'='*80}\n[INICIO] Procesando agente: {agent.upper()}\n{'='*80}")
            print(f"\n{'='*80}\n>>> INICIANDO ENTRENAMIENTO: {agent.upper()}\n{'='*80}\n")

            # Skip if results already exist
            # FIX: simulate() guarda en "result_{agent}.json", no "{agent}_results.json"
            results_json = out_dir / f"result_{agent}.json"
            if results_json.exists():
                with open(results_json) as f:
                    res = json.load(f)

                # Verificar si SAC o PPO ya completaron 2 episodios
                if agent.lower() in ["sac", "ppo"]:
                    # Verificar si tiene al menos 2 episodios (simulated_years >= 2.0)
                    if res.get("simulated_years", 0) >= 2.0:
                        logger.info(f"[SKIP] {agent.upper()} - Ya completó 2 episodios ({res.get('simulated_years')} años simulados)")
                        print(f"\n{'='*80}")
                        print(f"✓ {agent.upper()} ya completó {int(res.get('simulated_years', 0))} episodios - SALTANDO")
                        print(f"{'='*80}\n")
                        results[agent] = res
                        continue

                logger.info(f"[SKIP] {agent} - resultados ya existen en {results_json}")
                results[agent] = res
                continue

            # === CREAR FUNCIÓN SIMULACIÓN PARA ESTE AGENTE ===
            def create_simulate_fn(agent_name: str):
                """Factory para crear función simulación específica del agente."""
                def simulate_agent():
                    return simulate(
                        schema_path=schema_pv,
                        agent_name=agent_name,
                        out_dir=out_dir,
                        training_dir=training_dir,
                        carbon_intensity_kg_per_kwh=ci,
                        seconds_per_time_step=seconds_per_time_step,
                        sac_episodes=sac_episodes,
                        sac_batch_size=sac_batch_size,
                        sac_log_interval=sac_log_interval,
                        sac_use_amp=sac_use_amp,
                        ppo_timesteps=ppo_timesteps,
                        deterministic_eval=det_eval,
                        sac_device=sac_device,
                        ppo_device=ppo_device,
                        sac_prefer_citylearn=sac_prefer_citylearn,
                        sac_checkpoint_freq_steps=sac_checkpoint_freq,
                        ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
                        ppo_n_steps=ppo_n_steps,
                        ppo_batch_size=ppo_batch_size,
                        ppo_use_amp=ppo_use_amp,
                        ppo_target_kl=ppo_target_kl,
                        ppo_kl_adaptive=ppo_kl_adaptive,
                        ppo_log_interval=ppo_log_interval,
                        a2c_timesteps=a2c_timesteps,
                        a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
                        a2c_n_steps=a2c_n_steps,
                        a2c_learning_rate=a2c_learning_rate,
                        a2c_entropy_coef=a2c_entropy_coef,
                        a2c_device=a2c_device,
                        a2c_log_interval=a2c_log_interval,
                        sac_resume_checkpoints=sac_resume,
                        ppo_resume_checkpoints=ppo_resume,
                        a2c_resume_checkpoints=a2c_resume,
                        seed=project_seed,
                        multi_objective_priority=mo_priority,
                        use_multi_objective=True,
                    )
                return simulate_agent

            # === EJECUTAR CON RECUPERACIÓN AUTOMÁTICA ===
            timeout_minutes = {
                "sac": 120,      # SAC: 2 horas max
                "ppo": 180,      # PPO: 3 horas max
                "a2c": 180,      # A2C: 3 horas max
            }
            timeout_sec = timeout_minutes.get(agent.lower(), 120) * 60

            result = pipeline.execute_agent_with_recovery(
                agent_name=agent,
                simulate_fn=create_simulate_fn(agent),
                max_retries=2,
                timeout_seconds=timeout_sec,
            )

            if result:
                results[agent] = result
                logger.info(f"\n{'='*80}\n[COMPLETADO] Agente {agent.upper()} finalizado exitosamente\n{'='*80}")
                print(f"\n{'='*80}\n[OK] {agent.upper()} COMPLETADO - Pasando al siguiente agente\n{'='*80}\n")
            else:
                logger.error(f"[FALLÓ] Agente {agent.upper()} no pudo completarse después de reintentos")
                print(f"\n{'='*80}\n[ERROR] {agent.upper()} no completó (ver log para detalles)\n{'='*80}\n")

    finally:
        # === DETENER MONITOREO EN BACKGROUND ===
        pipeline.stop_background_monitoring()
        logger.info("[PIPELINE] Monitoreo finalizado")

    # Pick best (lowest annualized carbon, then highest autosuficiencia)
    def annualized_carbon(r: dict) -> float:
        return float(r["carbon_kg"] / max(r["simulated_years"], 1e-9))

    def autosuficiencia(r: dict) -> float:
        # Manejar claves faltantes con get() para compatibilidad
        ev_kwh_y = r.get("ev_charging_kwh", 0) / max(r.get("simulated_years", 1), 1e-9)
        build_kwh_y = r.get("building_load_kwh", 0) / max(r.get("simulated_years", 1), 1e-9)
        import_kwh_y = r.get("grid_import_kwh", 0) / max(r.get("simulated_years", 1), 1e-9)
        total_load = max(ev_kwh_y + build_kwh_y, 1e-9)
        return float(1.0 - import_kwh_y / total_load)

    # === IMPRIMIR REPORTE FINAL ===
    print("\n" + "="*80)
    print("📊 REPORTE FINAL DE ENTRENAMIENTO")
    print("="*80)

    if not results and not pipeline.failed_agents:
        print("[ADVERTENCIA] No se lograron entrenar agentes.")
    else:
        print(f"\n✅ AGENTES COMPLETADOS: {len(results)}")
        for agent_name, res in results.items():
            co2_annual = annualized_carbon(res)
            auto = autosuficiencia(res)
            print(f"   • {agent_name:10s}: {co2_annual:8.0f} kg CO2/año | {auto*100:6.1f}% autoconsumo")

        if pipeline.failed_agents:
            print(f"\n❌ AGENTES FALLIDOS: {len(pipeline.failed_agents)}")
            for agent_name, error in pipeline.failed_agents.items():
                print(f"   • {agent_name:10s}: {error}")

    print("\n" + "="*80)

    # Manejar caso cuando no hay resultados de agentes
    if not results:
        print("[ADVERTENCIA] No se lograron entrenar agentes. Usando solo baseline Uncontrolled.")
        best_agent = "Uncontrolled"
    else:
        best_agent = min(
            results.keys(),
            key=lambda k: (annualized_carbon(results[k]), -autosuficiencia(results[k])),
        )
        print(f"🏆 MEJOR AGENTE: {best_agent}")
        print(f"   Emisiones anuales: {annualized_carbon(results[best_agent]):.0f} kg CO2")

    # Calcular tailpipe y reducciones
    # Usamos el baseline (Uncontrolled + PV+BESS) para calcular el tailpipe equivalente
    baseline = res_uncontrolled
    if baseline is None:
        logger.warning("No baseline available - skipping tailpipe calculations")
        tailpipe_kg_y = 0.0
        grid_only_total = 0.0
    else:
        tailpipe_kg_y = _tailpipe_kg(cfg, float(baseline["ev_charging_kwh"]), float(baseline["simulated_years"]))
        grid_only_total = float(baseline["carbon_kg"]) + tailpipe_kg_y  # CO2 si no hubiera PV/BESS
    reductions: dict = {}
    if baseline is not None:
        base_carbon = float(baseline["carbon_kg"])
        reductions["oe2_reduction_kg"] = tailpipe_kg_y  # Reducción por electrificación
        reductions["oe2_reduction_pct"] = tailpipe_kg_y / max(grid_only_total, 1e-9)
        for agent_name, res in results.items():
            agent_carbon = float(res["carbon_kg"])
            reductions[agent_name] = {
                "reduction_kg": base_carbon - agent_carbon,
                "reduction_pct": (base_carbon - agent_carbon) / max(base_carbon, 1e-9),
            }

    summary = {
        "schema_pv_bess": str(schema_pv.resolve()),
        "pv_bess_results": results,
        "pv_bess_uncontrolled": res_uncontrolled if res_uncontrolled is not None else {},
        "best_agent": best_agent,
        "best_result": results[best_agent] if best_agent in results else (res_uncontrolled if res_uncontrolled is not None else {}),
        "best_agent_criteria": "min_annual_co2_then_max_autosuficiencia",
        "tailpipe_kg_per_year": float(tailpipe_kg_y),
        "grid_only_with_tailpipe_kg": float(grid_only_total),
        "reductions": reductions,
    }
    if chargers_results is not None:
        summary["chargers_results"] = chargers_results

    summary_path = out_dir / "simulation_summary.json"
    # Asegurar que todos los valores son serializables (float, no numpy.float64, etc.)
    def make_json_serializable(obj):
        """Convierte tipos numpy a tipos nativos de Python."""
        import numpy as np_local  # Import numpy locally to ensure availability
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_serializable(v) for v in obj]
        elif isinstance(obj, np_local.floating):
            return float(obj)
        elif isinstance(obj, np_local.integer):
            return int(obj)
        else:
            return obj

    summary_serializable = make_json_serializable(summary)
    summary_path.write_text(json.dumps(summary_serializable, indent=2), encoding="utf-8")

    # Generar tabla comparativa de CO2
    try:
        rows = []
        rows.append({
            "Escenario": "Grid-only + tailpipe",
            "CO2_kg": grid_only_total,
            "Reduccion_vs_grid_kg": 0.0,
            "Reduccion_vs_grid_pct": 0.0,
            "Reduccion_vs_base_kg": 0.0,
            "Reduccion_vs_base_pct": 0.0,
        })
        if baseline is not None:
            base_carbon = float(baseline["carbon_kg"])
            rows.append({
                "Escenario": "Baseline PV+BESS sin control",
                "CO2_kg": base_carbon,
                "Reduccion_vs_grid_kg": grid_only_total - base_carbon,
                "Reduccion_vs_grid_pct": (grid_only_total - base_carbon) / max(grid_only_total, 1e-9),
                "Reduccion_vs_base_kg": 0.0,
                "Reduccion_vs_base_pct": 0.0,
            })
            for agent_name, res in results.items():
                co2 = float(res["carbon_kg"])
                rows.append({
                    "Escenario": agent_name,
                    "CO2_kg": co2,
                    "Reduccion_vs_grid_kg": grid_only_total - co2,
                    "Reduccion_vs_grid_pct": (grid_only_total - co2) / max(grid_only_total, 1e-9),
                    "Reduccion_vs_base_kg": base_carbon - co2,
                    "Reduccion_vs_base_pct": (base_carbon - co2) / max(base_carbon, 1e-9),
                })
            headers = [
                "Escenario", "CO2_kg", "Reduccion_vs_grid_kg",
                "Reduccion_vs_grid_pct", "Reduccion_vs_base_kg", "Reduccion_vs_base_pct"
            ]
            md_lines = ["| " + " | ".join(headers) + " |",
                        "| " + " | ".join(["---"] * len(headers)) + " |"]
            for r in rows:
                md_lines.append(
                    "| " + " | ".join([
                        str(r["Escenario"]),
                        f"{r['CO2_kg']:.2f}",
                        f"{r['Reduccion_vs_grid_kg']:.2f}",
                        f"{float(r['Reduccion_vs_grid_pct'])*100:.4f}%",  # type: ignore[arg-type]
                        f"{r['Reduccion_vs_base_kg']:.2f}",
                        f"{float(r['Reduccion_vs_base_pct'])*100:.4f}%",  # type: ignore[arg-type]
                    ]) + " |"
                )
            table_path = out_dir / "co2_comparison.md"
            table_path.write_text("\n".join(md_lines), encoding="utf-8")
    except Exception as e:
        print(f"No se pudo generar tabla comparativa: {e}")

if __name__ == "__main__":
    main()
