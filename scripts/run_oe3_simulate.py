from __future__ import annotations

import argparse
import json
import os
import sys
import time
import subprocess
import threading
from pathlib import Path

from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from iquitos_citylearn.utils.logging import setup_logging
from scripts._common import load_all


def _ensure_repo_venv(repo_root: Path) -> Path:
    """Evita que se lance con el Python global en vez de la venv. Devuelve el python esperado."""
    exe = Path(sys.executable).resolve()
    venv_candidates = [
        repo_root / ".venv" / "Scripts" / "python.exe",  # Windows
        repo_root / ".venv" / "bin" / "python",          # *nix
    ]
    expected = next((p for p in venv_candidates if p.exists()), None)
    # Fallback check: ensure we are running from .venv path even if Unicode path mismatch.
    exe_str = str(exe).lower()
    in_venv = ".venv" in exe_str
    if expected and exe != expected:
        print(f"[ABORT] Usa la venv: {expected} (actual: {exe})")
        sys.exit(1)
    if expected and not in_venv:
        print(f"[ABORT] Python actual no es de la venv (.venv): {exe}")
        sys.exit(1)
    return expected or exe


def _acquire_lock(lock_path: Path) -> None:
    """Bloquea ejecuciones paralelas del entrenamiento OE3."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        print(f"[ABORT] Entrenamiento OE3 ya en curso (lock: {lock_path}). Borra el lock si es un residuo.")
        sys.exit(1)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")


def _kill_global_pythons() -> None:
    """Elimina procesos python.exe que no sean la venv actual."""
    try:
        ps_script = (
            "$me = {pid}; "
            "Get-CimInstance Win32_Process "
            "| Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne $me -and $_.ExecutablePath -notlike '*\\.venv\\*' } "
            "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        ).format(pid=os.getpid())
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=False, capture_output=True, text=True)
    except Exception:
        pass


def _start_global_killer_daemon() -> threading.Event | None:
    """Inicia un hilo que mata python.exe fuera de la venv mientras corre el entrenamiento."""
    try:
        import psutil  # type: ignore
    except Exception:
        return None

    stop_event = threading.Event()
    current_pid = os.getpid()

    def _worker() -> None:
        while not stop_event.is_set():
            try:
                for proc in psutil.process_iter(attrs=["pid", "exe", "name"]):
                    pid = proc.info.get("pid")
                    if pid is None or pid == current_pid:
                        continue
                    name = (proc.info.get("name") or "").lower()
                    exe = (proc.info.get("exe") or "").lower()
                    if "python" not in name:
                        continue
                    if ".venv" in exe:
                        continue
                    try:
                        proc.terminate()
                    except Exception:
                        pass
            except Exception:
                pass
            stop_event.wait(2.0)

    threading.Thread(target=_worker, daemon=True).start()
    return stop_event


def _abort_if_other_run_oe3_venv() -> None:
    """Aborta si ya hay otra instancia del script corriendo en la venv."""
    try:
        ps_script = (
            "$me = {pid}; "
            "$procs = Get-CimInstance Win32_Process "
            "| Where-Object { $_.Name -eq 'python.exe' -and $_.ProcessId -ne $me -and $_.ExecutablePath -like '*\\.venv\\*' -and $_.CommandLine -like '*scripts.run_oe3_simulate*' }; "
            "if ($procs) { Write-Output \"BLOCK $($procs[0].ProcessId)\" }"
        ).format(pid=os.getpid())
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout and "BLOCK" in result.stdout:
            pid = result.stdout.strip().split()[-1]
            print(f"[ABORT] Ya hay otra instancia en venv (PID {pid}).")
            sys.exit(1)
    except Exception:
        pass


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    _ensure_repo_venv(repo_root)
    _kill_global_pythons()
    killer = _start_global_killer_daemon()
    _abort_if_other_run_oe3_venv()
    lock_path = repo_root / "analyses" / "oe3" / "training" / "run.lock"
    _acquire_lock(lock_path)

    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/default.yaml")
        ap.add_argument(
            "--agent",
            default=None,
            help=(
                "Nombre del agente a ejecutar (SAC, PPO, A2C, Uncontrolled, etc.). "
                "Si se pasa, reemplaza la lista de agents del YAML."
            ),
        )
        args = ap.parse_args()

        setup_logging()
        cfg, rp = load_all(args.config)

        built = build_citylearn_dataset(
            cfg=cfg,
            raw_dir=rp.raw_dir,
            interim_dir=rp.interim_dir,
            processed_dir=rp.processed_dir,
        )

        dataset_dir = built.dataset_dir
        schema_grid = dataset_dir / "schema_grid_only.json"
        schema_pv = dataset_dir / "schema_pv_bess.json"

        out_dir = rp.outputs_dir / "oe3" / "simulations"
        training_dir = rp.analyses_dir / "oe3" / "training"
        out_dir.mkdir(parents=True, exist_ok=True)
        training_dir.mkdir(parents=True, exist_ok=True)
        progress_dir = training_dir / "progress"
        progress_dir.mkdir(parents=True, exist_ok=True)

        project_seed = int(cfg["project"].get("seed", 42))
        seconds_per_time_step = int(cfg["project"]["seconds_per_time_step"])
        ci = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])

        # Configuración de agentes
        eval_cfg = cfg["oe3"]["evaluation"]
        agent_override = args.agent
        if agent_override:
            eval_cfg = {**eval_cfg, "agents": [agent_override]}
            cfg = json.loads(json.dumps(cfg))
            cfg["oe3"]["evaluation"] = eval_cfg
        sac_cfg = eval_cfg.get("sac", {})
        ppo_cfg = eval_cfg.get("ppo", {})
        a2c_cfg = eval_cfg.get("a2c", {})

        sac_episodes = int(sac_cfg.get("episodes", 5))
        sac_device = sac_cfg.get("device")
        sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 0))
        sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))

        ppo_episodes = ppo_cfg.get("episodes")
        if ppo_episodes is not None:
            ppo_timesteps = int(ppo_episodes) * 8760
        else:
            ppo_timesteps = int(ppo_cfg.get("timesteps", 100000))
        ppo_device = ppo_cfg.get("device")
        ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 0))
        ppo_target_kl = ppo_cfg.get("target_kl")
        ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
        ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))

        a2c_episodes = a2c_cfg.get("episodes")
        if a2c_episodes is not None:
            a2c_timesteps = int(a2c_episodes) * 8760
        else:
            a2c_timesteps = int(a2c_cfg.get("timesteps", 0))
        a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 0))
        a2c_n_steps = int(a2c_cfg.get("n_steps", 256))
        a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
        a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))
        a2c_device = a2c_cfg.get("device")

        det_eval = bool(sac_cfg.get("deterministic_eval", True))

        # Scenario A: Electrified transport + grid only
        res_grid = simulate(
            schema_path=schema_grid,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            deterministic_eval=True,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            seed=project_seed,
        )

        # Scenario B: Electrified transport + PV+BESS + control (evaluate candidate agents)
        agent_names = list(eval_cfg["agents"])
        results = {}
        for agent in agent_names:
            if agent.lower() == "uncontrolled":
                # Uncontrolled with PV+BESS is not the reporting scenario requested,
                # but we keep it for diagnostics.
                pass

            res = simulate(
                schema_path=schema_pv,
                agent_name=agent,
                out_dir=out_dir,
                training_dir=training_dir,
                carbon_intensity_kg_per_kwh=ci,
                seconds_per_time_step=seconds_per_time_step,
                sac_episodes=sac_episodes,
                ppo_timesteps=ppo_timesteps,
                deterministic_eval=det_eval,
                sac_device=sac_device,
                ppo_device=ppo_device,
                sac_prefer_citylearn=sac_prefer_citylearn,
                sac_checkpoint_freq_steps=sac_checkpoint_freq,
                ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
                ppo_target_kl=ppo_target_kl,
                ppo_kl_adaptive=ppo_kl_adaptive,
                ppo_log_interval=ppo_log_interval,
                a2c_timesteps=a2c_timesteps,
                a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
                a2c_n_steps=a2c_n_steps,
                a2c_learning_rate=a2c_learning_rate,
                a2c_entropy_coef=a2c_entropy_coef,
                a2c_device=a2c_device,
                seed=project_seed,
            )
            results[agent] = res.__dict__

        # Scenario C: Electrified transport + PV+BESS + no control (baseline)
        res_uncontrolled = simulate(
            schema_path=schema_pv,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=ci,
            seconds_per_time_step=seconds_per_time_step,
            sac_episodes=sac_episodes,
            ppo_timesteps=ppo_timesteps,
            deterministic_eval=True,
            sac_prefer_citylearn=sac_prefer_citylearn,
            sac_checkpoint_freq_steps=sac_checkpoint_freq,
            ppo_checkpoint_freq_steps=ppo_checkpoint_freq,
            ppo_target_kl=ppo_target_kl,
            ppo_kl_adaptive=ppo_kl_adaptive,
            ppo_log_interval=ppo_log_interval,
            a2c_timesteps=a2c_timesteps,
            a2c_checkpoint_freq_steps=a2c_checkpoint_freq,
            a2c_n_steps=a2c_n_steps,
            a2c_learning_rate=a2c_learning_rate,
            a2c_entropy_coef=a2c_entropy_coef,
            a2c_device=a2c_device,
            seed=project_seed,
        )

        # Pick best (lowest annualized carbon, then highest autosuficiencia)
        def annualized_carbon(r: dict) -> float:
            return r["carbon_kg"] / max(r["simulated_years"], 1e-9)

        def autosuficiencia(r: dict) -> float:
            ev_kwh_y = r["ev_charging_kwh"] / max(r["simulated_years"], 1e-9)
            build_kwh_y = r["building_load_kwh"] / max(r["simulated_years"], 1e-9)
            import_kwh_y = r["grid_import_kwh"] / max(r["simulated_years"], 1e-9)
            return 1.0 - import_kwh_y / max(ev_kwh_y + build_kwh_y, 1e-9)

        best_agent = min(
            results.keys(),
            key=lambda k: (annualized_carbon(results[k]), -autosuficiencia(results[k])),
        )
        summary = {
            "schema_grid_only": str(schema_grid.resolve()),
            "schema_pv_bess": str(schema_pv.resolve()),
            "grid_only_result": res_grid.__dict__,
            "pv_bess_results": results,
            "pv_bess_uncontrolled": res_uncontrolled.__dict__,
            "best_agent": best_agent,
            "best_result": results[best_agent],
            "best_agent_criteria": "min_annual_co2_then_max_autosuficiencia",
        }

        (out_dir / "simulation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    finally:
        if killer is not None:
            killer.set()
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
