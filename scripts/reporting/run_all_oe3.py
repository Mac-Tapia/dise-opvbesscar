#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script maestro OE3 - ejecuta toda la cadena de analisis y actualiza todos los archivos.

Ejecutar desde la raiz del proyecto:
    python scripts/reporting/run_all_oe3.py

Orden de ejecucion:
    1. analizar_co2_trace_oe3.py        - CO2 directo/indirecto desde traces
    2. demostracion_estadistica_oe3.py  - pruebas estadisticas completas
    3. control_operativo_bess_ev_oe3.py - patron BESS/EV/pico por hora
    4. comparativa_agentes_co2_trace.py - figuras comparativas convergencia
    5. generar_tablas_oe3.py            - tablas canonicas PNG

El canonical JSON y el markdown canonico NO se regeneran automaticamente:
se mantienen como fuente versionada y se editan manualmente al reentrenar.
"""
from __future__ import annotations

import runpy
import sys
import time
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCRIPTS: list[tuple[str, Path]] = [
    ("CO2 trace directo/indirecto",   ROOT / "scripts" / "analysis"  / "analizar_co2_trace_oe3.py"),
    ("Estadisticas completas OE3",    ROOT / "scripts" / "analysis"  / "demostracion_estadistica_oe3.py"),
    ("Control operativo BESS/EV",     ROOT / "scripts" / "analysis"  / "control_operativo_bess_ev_oe3.py"),
    ("Comparativa CO2 trace figuras", ROOT / "scripts" / "reporting" / "comparativa_agentes_co2_trace.py"),
    ("Tablas canonicas PNG",          ROOT / "scripts" / "reporting" / "generar_tablas_oe3.py"),
]

EXPECTED_OUTPUTS: list[Path] = [
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

SEP = "-" * 60
SEP2 = "=" * 60


def run_script(name: str, path: Path) -> bool:
    print(f"\n{SEP}")
    print(f"[PASO] {name}")
    print(f"       {path.relative_to(ROOT)}")
    print(SEP)
    t0 = time.time()
    try:
        runpy.run_path(str(path), run_name="__main__")
        print(f"\n  OK completado en {time.time() - t0:.1f}s")
        return True
    except Exception:  # noqa: BLE001
        print("\n  ERROR:")
        traceback.print_exc()
        return False


def verify_outputs() -> tuple[list[Path], list[Path]]:
    ok: list[Path] = []
    missing: list[Path] = []
    for p in EXPECTED_OUTPUTS:
        (ok if p.exists() else missing).append(p)
    return ok, missing


def main() -> None:
    print(f"\n{SEP2}")
    print("RUN ALL OE3 - cadena completa de analisis")
    print(f"Raiz: {ROOT}")
    print(SEP2)

    t_start = time.time()
    step_results: list[tuple[str, bool]] = []

    for name, path in SCRIPTS:
        ok = run_script(name, path)
        step_results.append((name, ok))

    print(f"\n{SEP2}")
    print("VERIFICACION DE ARCHIVOS GENERADOS")
    print(SEP2)
    ok_files, missing_files = verify_outputs()
    for p in ok_files:
        print(f"  OK {p.relative_to(ROOT)}")
    for p in missing_files:
        print(f"  FALTA: {p.relative_to(ROOT)}")

    print(f"\n{SEP2}")
    print("RESUMEN")
    print(SEP2)
    n_ok = sum(1 for _, s in step_results if s)
    n_fail = len(step_results) - n_ok
    for name, s in step_results:
        print(f"  {'OK' if s else 'FAIL'} {name}")
    print(f"\n  Scripts: {n_ok}/{len(step_results)} OK | "
          f"Archivos: {len(ok_files)}/{len(EXPECTED_OUTPUTS)} generados")
    print(f"  Tiempo total: {time.time() - t_start:.1f}s")

    if missing_files:
        print(f"\n  ADVERTENCIA: {len(missing_files)} archivo(s) no generado(s)")
        sys.exit(1)
    if n_fail:
        print(f"\n  ADVERTENCIA: {n_fail} script(s) con error")
        sys.exit(1)

    print("\n  Cadena OE3 completada. Agente seleccionado: A2C")
    print("  Criterio: mayor CO2 evitado (directo+indirecto) + mayor carga EV")
    print(SEP2)


if __name__ == "__main__":
    main()
