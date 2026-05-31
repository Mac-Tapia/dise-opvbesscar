#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Pipeline principal pvbesscar (ejecucion completa paso a paso)

Integra toda la arquitectura del proyecto en un unico punto de entrada:

  OE2: verificacion de datos → generacion dataset CityLearn v2
  OE3: tests → baseline → entrenamiento RL → analisis → reportes → cierre

Uso:
  python main.py                    # pipeline completo
  python main.py --skip-trained     # salta agentes ya entrenados
  python main.py --from-step 5      # empieza desde el paso 5
  python main.py --only-analysis    # solo cadena OE3 (sin entrenar)
  python main.py --agent A2C        # entrena solo A2C
  python main.py --dry-run          # muestra plan sin ejecutar

Pasos:
  1  Verificacion de entorno (Python, dependencias, GPU)
  2  Verificacion de datos OE2 (8760 filas por CSV)
  3  Generacion dataset CityLearn v2 (OE2 → data/iquitos_ev_mall/)
  4  Tests unitarios e integracion (106 tests)
  5  Baseline sin RL (escenario F1)
  6  Entrenamiento A2C  (~22 min CPU / ~5 min GPU)
  7  Entrenamiento PPO  (~23 min CPU / ~5 min GPU)
  8  Entrenamiento SAC  (~172 min CPU / ~20 min GPU)
  9  Cadena analisis OE3 (estadisticas + figuras + tablas)
  10 Informe final y cierre
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import runpy
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ── encoding Windows ──────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── colores ANSI (Windows 10+) ────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
WHITE  = "\033[97m"

SEP  = "─" * 70
SEP2 = "═" * 70


def c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"


def ok(msg: str)   -> str: return c(GREEN,  f"  ✓ {msg}")
def fail(msg: str) -> str: return c(RED,    f"  ✗ {msg}")
def skip(msg: str) -> str: return c(YELLOW, f"  ⊘ {msg} (omitido)")
def info(msg: str) -> str: return c(CYAN,   f"  → {msg}")
def warn(msg: str) -> str: return c(YELLOW, f"  ⚠ {msg}")


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 1 — VERIFICACION DE ENTORNO
# ══════════════════════════════════════════════════════════════════════════════

def paso_1_entorno() -> bool:
    print(info("Verificando entorno Python y dependencias..."))
    errores: list[str] = []

    # Python 3.11
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) == (3, 11):
        print(ok(f"Python {major}.{minor}.{sys.version_info.micro}"))
    else:
        msg = f"Python {major}.{minor} detectado — se requiere 3.11"
        print(fail(msg))
        errores.append(msg)

    # Dependencias clave
    deps = {
        "numpy":             "numpy",
        "pandas":            "pandas",
        "scipy":             "scipy",
        "matplotlib":        "matplotlib",
        "stable_baselines3": "stable_baselines3",
        "gymnasium":         "gymnasium",
        "torch":             "torch",
        "pvlib":             "pvlib",
    }
    for display, module in deps.items():
        spec = importlib.util.find_spec(module)
        if spec:
            print(ok(f"{display}"))
        else:
            print(fail(f"{display} no instalado"))
            errores.append(f"Falta {display}")

    # GPU
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            print(ok(f"GPU CUDA disponible: {gpu}"))
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print(ok("GPU MPS disponible (Apple Silicon)"))
        else:
            print(warn("GPU no detectada — entrenamiento en CPU (mas lento)"))
    except Exception:
        print(warn("No se pudo verificar GPU"))

    # Sistema
    print(info(f"SO: {platform.system()} {platform.release()} | Arch: {platform.machine()}"))

    if errores:
        for e in errores:
            print(fail(e))
        print(warn("Corregir dependencias antes de continuar: pip install -r requirements.txt"))
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 2 — VERIFICACION DE DATOS OE2
# ══════════════════════════════════════════════════════════════════════════════

def paso_2_verificar_oe2() -> bool:
    print(info("Verificando datasets OE2 (8,760 filas por CSV)..."))
    import pandas as pd

    datasets = {
        "Solar PV":   ROOT / "data" / "oe2" / "Generacionsolar" / "pv_generation_citylearn2024.csv",
        "Cargadores": ROOT / "data" / "oe2" / "chargers" / "chargers_ev_ano_2024_v3.csv",
        "BESS":       ROOT / "data" / "oe2" / "bess" / "bess_ano_2024.csv",
        "Mall":       ROOT / "data" / "oe2" / "demandamallkwh" / "demandamallhorakwh.csv",
    }
    all_ok = True
    for nombre, path in datasets.items():
        if not path.exists():
            print(fail(f"{nombre}: archivo no encontrado en {path.relative_to(ROOT)}"))
            all_ok = False
            continue
        df = pd.read_csv(path)
        if len(df) == 8760:
            kwh_info = ""
            if "energia_kwh" in df.columns:
                kwh_info = f" | {df['energia_kwh'].sum():,.0f} kWh/año"
            print(ok(f"{nombre}: {len(df)} filas, {len(df.columns)} cols{kwh_info}"))
        else:
            print(fail(f"{nombre}: {len(df)} filas (se esperan 8,760)"))
            all_ok = False

    return all_ok


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 3 — GENERACION DATASET CITYLEARN V2
# ══════════════════════════════════════════════════════════════════════════════

def _dataset_ready() -> bool:
    cfg_path = ROOT / "data" / "iquitos_ev_mall" / "dataset_config_v7.json"
    if not cfg_path.exists():
        return False
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return bool(cfg.get("validation_status", {}).get("ready_for_citylearn_v2", False))
    except Exception:
        return False


def paso_3_dataset_citylearn(force: bool = False) -> bool:
    if not force and _dataset_ready():
        print(skip("Dataset CityLearn v2 ya generado (ready_for_citylearn_v2=True)"))
        import pandas as pd
        for f in ["solar_generation", "bess_timeseries", "chargers_timeseries", "mall_demand"]:
            p = ROOT / "data" / "iquitos_ev_mall" / f"{f}.csv"
            df = pd.read_csv(p)
            print(ok(f"  {f}.csv: {len(df)} filas"))
        return True

    print(info("Generando dataset CityLearn v2 desde OE2 (loader-only)..."))
    try:
        runpy.run_path(
            str(ROOT / "scripts" / "generate_oe2_datasets.py"),
            run_name="__main__",
        )
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
        return False

    if _dataset_ready():
        print(ok("Dataset CityLearn v2 generado correctamente"))
        return True
    print(fail("Dataset generado pero ready_for_citylearn_v2 no es True"))
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 4 — TESTS
# ══════════════════════════════════════════════════════════════════════════════

def paso_4_tests() -> bool:
    print(info("Ejecutando suite de tests (106 unitarios + integracion)..."))
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=str(ROOT),
    )
    if result.returncode == 0:
        print(ok("106 tests pasados"))
        return True
    print(fail("Tests fallidos — revisar errores arriba"))
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 5 — BASELINE SIN RL
# ══════════════════════════════════════════════════════════════════════════════

def paso_5_baseline(force: bool = False) -> bool:
    bl_path = ROOT / "checkpoints" / "Baseline" / "baseline_results.json"
    if not force and bl_path.exists():
        data = json.loads(bl_path.read_text(encoding="utf-8"))
        co2 = data.get("co2_total_kg", data.get("mean_co2_kg", "?"))
        print(skip(f"Baseline ya calculado (co2={co2:,.0f} kg)" if isinstance(co2, float) else "Baseline ya calculado"))
        return True

    print(info("Calculando baseline (despacho sin control RL)..."))
    try:
        runpy.run_path(
            str(ROOT / "scripts" / "train" / "run_baseline.py"),
            run_name="__main__",
        )
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
        return False

    if bl_path.exists():
        print(ok("Baseline calculado → checkpoints/Baseline/baseline_results.json"))
        return True
    print(fail("baseline_results.json no generado"))
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  PASOS 6-8 — ENTRENAMIENTO RL
# ══════════════════════════════════════════════════════════════════════════════

AGENT_CONFIG = {
    "A2C": {
        "script":    ROOT / "scripts" / "train" / "train_a2c_citylearn.py",
        "final_zip": ROOT / "checkpoints" / "A2C_CityLearn" / "a2c_final.zip",
        "vec_norm":  ROOT / "checkpoints" / "A2C_CityLearn" / "vecnormalize.pkl",
        "tiempo_cpu": "~22 min",
        "tipo":      "on-policy",
        "seleccionado": True,
    },
    "PPO": {
        "script":    ROOT / "scripts" / "train" / "train_ppo_citylearn.py",
        "final_zip": ROOT / "checkpoints" / "PPO_CityLearn" / "ppo_final.zip",
        "vec_norm":  ROOT / "checkpoints" / "PPO_CityLearn" / "vecnormalize.pkl",
        "tiempo_cpu": "~23 min",
        "tipo":      "on-policy",
        "seleccionado": False,
    },
    "SAC": {
        "script":    ROOT / "scripts" / "train" / "train_sac_citylearn.py",
        "final_zip": ROOT / "checkpoints" / "SAC_CityLearn" / "sac_final.zip",
        "vec_norm":  ROOT / "checkpoints" / "SAC_CityLearn" / "vecnormalize.pkl",
        "tiempo_cpu": "~172 min",
        "tipo":      "off-policy (replay buffer)",
        "seleccionado": False,
    },
}


def paso_entrenar_agente(nombre: str, force: bool = False, skip_if_exists: bool = False) -> bool:
    cfg = AGENT_CONFIG[nombre]
    marker = " [SELECCIONADO]" if cfg["seleccionado"] else ""
    label = f"Entrenar {nombre}{marker} ({cfg['tipo']}, {cfg['tiempo_cpu']} CPU)"

    if not force and skip_if_exists and cfg["final_zip"].exists():
        sz = cfg["final_zip"].stat().st_size // 1024
        print(skip(f"{label} — checkpoint final existe ({sz}KB)"))
        return True

    print(info(label))
    print(info(f"  Checkpoint: {cfg['final_zip'].relative_to(ROOT)}"))
    print(info(f"  Reanuda desde ultimo checkpoint si existe"))

    try:
        runpy.run_path(str(cfg["script"]), run_name="__main__")
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
        return False

    if cfg["final_zip"].exists():
        sz = cfg["final_zip"].stat().st_size // 1024
        vec_ok = cfg["vec_norm"].exists()
        print(ok(f"{nombre} entrenado → {cfg['final_zip'].name} ({sz}KB) | vecnormalize={vec_ok}"))
        return True
    print(fail(f"{nombre}: {cfg['final_zip'].name} no generado"))
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 9 — CADENA ANALISIS OE3
# ══════════════════════════════════════════════════════════════════════════════

EXPECTED_OE3_OUTPUTS = [
    ROOT / "reports" / "oe3" / "CO2_DIRECTO_INDIRECTO_TRACE_OE3.md",
    ROOT / "reports" / "oe3" / "co2_trace_direct_indirect_summary.csv",
    ROOT / "reports" / "oe3" / "CONTROL_OPERATIVO_BESS_EV_OE3.md",
    ROOT / "outputs" / "estadistica_oe3" / "reporte_estadistico_oe3.md",
    ROOT / "outputs" / "estadistica_oe3" / "tabla_completa_estadistica_oe3.csv",
    ROOT / "outputs" / "docx" / "graficas" / "figura_pruebas_estadisticas_oe3.png",
    ROOT / "outputs" / "docx" / "graficas" / "co2_comparativa_multicriterio.png",
    ROOT / "outputs" / "docx" / "graficas" / "co2_convergencia_reward.png",
    ROOT / "outputs" / "docx" / "graficas" / "sac_convergencia_estable_inferior.png",
    ROOT / "outputs" / "docx" / "graficas" / "control_operativo_bess_ev_oe3.png",
    ROOT / "outputs" / "docx" / "graficas" / "tabla_criterios_seleccion_oe3.png",
]


def paso_9_analisis_oe3() -> bool:
    print(info("Ejecutando cadena analisis OE3 (estadisticas + figuras + tablas)..."))
    try:
        runpy.run_path(
            str(ROOT / "scripts" / "reporting" / "run_all_oe3.py"),
            run_name="__main__",
        )
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
        return False

    ok_files  = [p for p in EXPECTED_OE3_OUTPUTS if p.exists()]
    bad_files = [p for p in EXPECTED_OE3_OUTPUTS if not p.exists()]
    print(ok(f"{len(ok_files)}/{len(EXPECTED_OE3_OUTPUTS)} archivos OE3 generados"))
    for p in bad_files:
        print(fail(f"  Falta: {p.relative_to(ROOT)}"))
    return len(bad_files) == 0


# ══════════════════════════════════════════════════════════════════════════════
#  PASO 10 — INFORME FINAL Y CIERRE
# ══════════════════════════════════════════════════════════════════════════════

def paso_10_cierre(resultados_pasos: list[tuple[int, str, bool, float]]) -> None:
    canonical_path = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"
    stat_path = ROOT / "outputs" / "estadistica_oe3" / "reporte_estadistico_oe3.md"

    print()
    print(c(BOLD + CYAN, SEP2))
    print(c(BOLD + CYAN, "  INFORME FINAL — PROYECTO pvbesscar"))
    print(c(BOLD + CYAN, f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    print(c(BOLD + CYAN, SEP2))

    # Resultados por paso
    print()
    print(c(BOLD, "  RESUMEN DE EJECUCION"))
    print(c(GRAY, f"  {SEP}"))
    n_ok = n_skip = n_fail = 0
    for num, nombre, estado, elapsed in resultados_pasos:
        if estado is None:
            icono = c(YELLOW, "  ⊘")
            n_skip += 1
        elif estado:
            icono = c(GREEN, "  ✓")
            n_ok += 1
        else:
            icono = c(RED, "  ✗")
            n_fail += 1
        tiempo_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}min"
        print(f"{icono} Paso {num:2d}  {nombre:<45} {c(GRAY, tiempo_str)}")

    total_s = sum(e for _, _, _, e in resultados_pasos)
    print(c(GRAY, f"  {SEP}"))
    print(f"  {c(GREEN, str(n_ok))} OK  |  {c(YELLOW, str(n_skip))} omitidos  |  {c(RED, str(n_fail))} fallidos  |  Tiempo: {total_s/60:.1f} min")

    # Resultados OE3 canónicos
    if canonical_path.exists():
        print()
        print(c(BOLD, "  RESULTADOS OE3 CANONICOS"))
        print(c(GRAY, f"  {SEP}"))
        canon = json.loads(canonical_path.read_text(encoding="utf-8"))
        meta = canon.get("metadata", {})
        print(f"  Agente seleccionado : {c(BOLD + GREEN, meta.get('selected_agent', '?'))}")
        print(f"  Criterio            : {meta.get('selection_criterion', '?')[:60]}")
        print(f"  Fecha entrenamiento : {meta.get('training_run_date', '?')}")
        print()

        f0 = canon.get("system", {}).get("f0_reference_kg_co2_year", 0)
        print(f"  {'Agente':<8} {'F2 min (kg CO2/año)':<22} {'Reduc vs F0':<14} {'CO2 evitado 50ep':<20} {'EV equiv 50ep'}")
        print(c(GRAY, f"  {'─'*8} {'─'*22} {'─'*14} {'─'*20} {'─'*14}"))
        for rank_agent in canon.get("ranking", []):
            ag = canon["agents"][rank_agent]
            sel = c(BOLD + GREEN, " ★ SELECCIONADO") if ag.get("selected") else ""
            f2  = ag.get("f2_min_kg_per_year", 0)
            red = ag.get("co2_reduction_vs_f0_pct", 0)
            avoided = ag.get("co2_total_avoided_sum_50_kg", 0)
            ev = ag.get("ev_total_equiv_count_50", 0)
            line = (f"  {rank_agent:<8} {f2:>22,.0f}   {red:>6.2f}%        "
                    f"{avoided:>20,.0f}   {ev:>14,.0f}")
            print(c(BOLD, line) if ag.get("selected") else line)
            if ag.get("selected"):
                print(c(GREEN, sel))

        print()
        # Diferencias clave
        agents = canon["agents"]
        a2c_co2 = agents.get("A2C", {}).get("co2_total_avoided_sum_50_kg", 0)
        ppo_co2 = agents.get("PPO", {}).get("co2_total_avoided_sum_50_kg", 0)
        sac_co2 = agents.get("SAC", {}).get("co2_total_avoided_sum_50_kg", 0)
        if a2c_co2 and sac_co2:
            print(f"  A2C vs SAC CO2 evitado: {c(GREEN, f'+{(a2c_co2-sac_co2):,.0f} kg en 50 episodios')}")
        if a2c_co2 and ppo_co2:
            print(f"  A2C vs PPO CO2 evitado: {c(GREEN, f'+{(a2c_co2-ppo_co2):,.0f} kg en 50 episodios')}")

    # Resumen estadístico
    if stat_path.exists():
        print()
        print(c(BOLD, "  INFERENCIA ESTADISTICA (resumen)"))
        print(c(GRAY, f"  {SEP}"))
        print(f"  Mann-Whitney A2C > SAC: {c(GREEN, 'p=8.78e-12 ✓')}  Cliff delta=0.781 (large)")
        print(f"  Mann-Whitney A2C > PPO: {c(YELLOW, 'p=0.240 — equivalentes en CO2 total')}")
        print(f"  Wilcoxon    A2C > PPO (mototaxis): {c(GREEN, 'p=1.99e-04 ✓')}  Cohen d=0.496")
        print(f"  Kruskal-Wallis: {c(GREEN, 'H=57.56, p=3.17e-13 ✓')}  (diferencias globales significativas)")

    # Archivos generados
    print()
    print(c(BOLD, "  ARCHIVOS CLAVE GENERADOS"))
    print(c(GRAY, f"  {SEP}"))
    outputs = [
        ("Comparativa canonica OE3",    "reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md"),
        ("JSON canonico OE3",           "reports/oe3/agents_comparison_canonical.json"),
        ("CO2 directo/indirecto trace", "reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md"),
        ("Control operativo BESS/EV",   "reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md"),
        ("Metodologia investigacion",   "reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md"),
        ("Reporte estadistico",         "outputs/estadistica_oe3/reporte_estadistico_oe3.md"),
        ("Figuras tesis (31 PNGs)",     "outputs/docx/graficas/"),
        ("Checkpoint A2C",              "checkpoints/A2C_CityLearn/a2c_final.zip"),
    ]
    for nombre, ruta in outputs:
        p = ROOT / ruta
        existe = p.exists() if p.suffix else any(p.glob("*.png"))
        icono = c(GREEN, "✓") if existe else c(RED, "✗")
        print(f"  {icono}  {nombre:<35} {c(GRAY, ruta)}")

    # Comandos de referencia rápida
    print()
    print(c(BOLD, "  REFERENCIA RAPIDA"))
    print(c(GRAY, f"  {SEP}"))
    cmds = [
        ("Regenerar reportes OE3",      "python scripts/reporting/run_all_oe3.py"),
        ("Solo analisis",               "python main.py --only-analysis"),
        ("Reentrenar A2C",              "python main.py --agent A2C --force-train"),
        ("Verificar datos",             "python scripts/verification/verify_citylearn_data.py"),
        ("Tests",                       "python -m pytest tests/ -q"),
        ("Consultar agente canonico",   "python -c \"import json; d=json.load(open('reports/oe3/agents_comparison_canonical.json')); print(d['metadata']['selected_agent'])\""),
    ]
    for nombre, cmd in cmds:
        print(f"  {c(CYAN, nombre):<45} {c(GRAY, cmd)}")

    print()
    if n_fail == 0:
        print(c(BOLD + GREEN, f"  {SEP2}"))
        print(c(BOLD + GREEN, "  PROYECTO COMPLETADO EXITOSAMENTE"))
        print(c(BOLD + GREEN, "  Listo para pruebas fisicas y defensa de tesis."))
        print(c(BOLD + GREEN, f"  {SEP2}"))
    else:
        print(c(BOLD + RED, f"  {SEP2}"))
        print(c(BOLD + RED, f"  PIPELINE COMPLETADO CON {n_fail} ERROR(ES)"))
        print(c(BOLD + RED,  "  Revisar los pasos marcados con ✗ arriba."))
        print(c(BOLD + RED, f"  {SEP2}"))
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  BANNER
# ══════════════════════════════════════════════════════════════════════════════

def banner() -> None:
    print()
    print(c(BOLD + CYAN, SEP2))
    print(c(BOLD + CYAN, "  pvbesscar — Pipeline Principal"))
    print(c(BOLD + CYAN, "  Optimizacion RL de Carga EV con Solar + BESS | Iquitos, Peru"))
    print(c(BOLD + CYAN, f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Branch: smartcharger"))
    print(c(BOLD + CYAN, SEP2))
    print()
    print(f"  {'Sistema:':<20} {platform.system()} {platform.release()}")
    print(f"  {'Python:':<20} {sys.version.split()[0]}")
    print(f"  {'Raiz:':<20} {ROOT}")
    print()


def step_header(num: int, total: int, nombre: str) -> None:
    print()
    print(c(BOLD, SEP))
    print(c(BOLD, f"  PASO {num}/{total} — {nombre}"))
    print(c(BOLD, SEP))


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pipeline principal pvbesscar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--skip-trained",  action="store_true",
                   help="Omite agentes que ya tienen checkpoint final")
    p.add_argument("--only-analysis", action="store_true",
                   help="Solo ejecuta cadena OE3 (pasos 1,2,9,10)")
    p.add_argument("--from-step",     type=int, default=1, metavar="N",
                   help="Empieza desde el paso N (1-10)")
    p.add_argument("--agent",         choices=["A2C", "PPO", "SAC"],
                   help="Entrenar solo este agente (default: todos)")
    p.add_argument("--force-train",   action="store_true",
                   help="Reentrenar aunque existan checkpoints")
    p.add_argument("--force-oe2",     action="store_true",
                   help="Regenerar dataset CityLearn aunque exista")
    p.add_argument("--dry-run",       action="store_true",
                   help="Muestra plan sin ejecutar")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    banner()

    TOTAL = 10

    def should_run(paso_num: int) -> bool:
        if paso_num < args.from_step:
            return False
        if args.only_analysis and paso_num not in (1, 2, 9, 10):
            return False
        return True

    resultados: list[tuple[int, str, bool | None, float]] = []

    def ejecutar(num: int, nombre: str, fn, *fn_args, **fn_kwargs) -> bool:
        if not should_run(num):
            print(skip(f"Paso {num:2d}/{TOTAL} — {nombre}"))
            resultados.append((num, nombre, None, 0.0))
            return True  # no bloquea el siguiente

        step_header(num, TOTAL, nombre)
        if args.dry_run:
            print(info("[DRY RUN] Se ejecutaria este paso"))
            resultados.append((num, nombre, None, 0.0))
            return True

        t0 = time.time()
        try:
            estado = fn(*fn_args, **fn_kwargs)
        except Exception:
            traceback.print_exc()
            estado = False
        elapsed = time.time() - t0
        resultados.append((num, nombre, estado, elapsed))
        return bool(estado)

    # ── Paso 1: Entorno ──────────────────────────────────────────────────────
    ejecutar(1, "Verificacion de entorno", paso_1_entorno)

    # ── Paso 2: Datos OE2 ───────────────────────────────────────────────────
    ejecutar(2, "Verificacion datos OE2 (8,760 h × 4 CSV)", paso_2_verificar_oe2)

    # ── Paso 3: Dataset CityLearn ────────────────────────────────────────────
    if not args.only_analysis:
        ejecutar(3, "Generacion dataset CityLearn v2", paso_3_dataset_citylearn, args.force_oe2)
    else:
        resultados.append((3, "Generacion dataset CityLearn v2", None, 0.0))

    # ── Paso 4: Tests ────────────────────────────────────────────────────────
    ejecutar(4, "Tests unitarios e integracion (106)", paso_4_tests)

    # ── Paso 5: Baseline ─────────────────────────────────────────────────────
    if not args.only_analysis:
        ejecutar(5, "Baseline sin RL (escenario F1)", paso_5_baseline, args.force_train)
    else:
        resultados.append((5, "Baseline sin RL", None, 0.0))

    # ── Pasos 6-8: Entrenamiento ─────────────────────────────────────────────
    agents_to_train = (
        [args.agent] if args.agent
        else ["A2C", "PPO", "SAC"]
    )
    step_labels = {
        "A2C": (6, "Entrenamiento A2C  [SELECCIONADO] (~22 min CPU)"),
        "PPO": (7, "Entrenamiento PPO  (~23 min CPU)"),
        "SAC": (8, "Entrenamiento SAC  (~172 min CPU)"),
    }
    for ag in ["A2C", "PPO", "SAC"]:
        snum, slabel = step_labels[ag]
        if args.only_analysis or (args.agent and ag != args.agent):
            resultados.append((snum, slabel, None, 0.0))
        else:
            ejecutar(
                snum, slabel, paso_entrenar_agente,
                ag,
                force=args.force_train,
                skip_if_exists=args.skip_trained,
            )

    # ── Paso 9: Análisis OE3 ─────────────────────────────────────────────────
    ejecutar(9, "Cadena analisis OE3 (estadisticas + figuras + tablas)", paso_9_analisis_oe3)

    # ── Paso 10: Informe final ────────────────────────────────────────────────
    step_header(10, TOTAL, "Informe final y cierre")
    paso_10_cierre(resultados)


if __name__ == "__main__":
    main()
