"""
Convierte reports/ARQUITECTURA_v2026.html a PDF para el Anexo D.

Uso:
  python scripts/analysis/generar_arquitectura_pdf.py            # A4 completo
  python scripts/analysis/generar_arquitectura_pdf.py --pipeline-a3  # Solo pipeline en A3 horizontal
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[2]
SRC_HTML = ROOT / "reports" / "ARQUITECTURA_v2026.html"
OUT_PDF  = ROOT / "reports" / "ARQUITECTURA_v2026.pdf"
OUT_PDF_PIPELINE_A3 = ROOT / "reports" / "ARQUITECTURA_v2026_Pipeline_A3.pdf"

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str:
    for p in CHROME_PATHS:
        if Path(p).exists():
            return p
    raise FileNotFoundError("No se encontro Chrome/Edge.")


def build_print_html(html: str) -> str:
    """Transforma el HTML con pestanas en un HTML lineal para PDF A4 completo."""
    html = re.sub(r'<!-- PORTADA ANEXO.*?</div>\s*\n', '', html, flags=re.DOTALL)
    html = re.sub(r'<nav>.*?</nav>', '', html, flags=re.DOTALL)
    html = re.sub(
        r'class="panel(?: active)?"',
        'class="panel" style="display:block;padding:28px 40px 40px;"',
        html,
    )
    for pid in ("pipeline", "flujo", "agentes"):
        html = html.replace(
            f'id="{pid}" class="panel"',
            f'id="{pid}" class="panel" style="display:block;padding:28px 40px 40px;page-break-before:always;"',
        )
    html = html.replace('.panel-print-title { display: none; }', '.panel-print-title { display: block; }')
    html = html.replace('background: #eef1f6;', 'background: white;')

    cover = """
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;page-break-after:always;padding:60mm 20mm 40mm;
  font-family:'Segoe UI',system-ui,Arial,sans-serif;">
  <div style="font-size:10pt;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:3px;margin-bottom:10mm;">ANEXO D</div>
  <h2 style="font-size:22pt;font-weight:800;color:#0d2b45;line-height:1.3;margin-bottom:8mm;">
    Arquitectura del Sistema PVBESSCAR<br>Pipeline OE2 &rarr; OE3
  </h2>
  <p style="font-size:11pt;color:#4b5563;line-height:1.7;max-width:120mm;">
    Sistema de carga inteligente con Reinforcement Learning para motos y mototaxis electricas.
    Optimizacion de 38 sockets de carga (4,050 kWp solar + 2,000 kWh BESS) mediante
    agentes SAC / PPO / A2C en entorno CityLearn v2.
  </p>
  <div style="margin-top:14mm;font-size:9pt;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:6mm;width:100%;">
    <strong>Tesis:</strong> Seleccion de Agente RL para Reduccion de CO2 &mdash; Iquitos, Peru &nbsp;&middot;&nbsp;
    <strong>Documento:</strong> v11 &mdash; 594 parrafos, 36 tablas &nbsp;&middot;&nbsp;
    <strong>Fecha:</strong> 12 / 04 / 2026 &nbsp;&middot;&nbsp;
    <strong>Branch:</strong> smartcharger
  </div>
</div>
"""
    html = html.replace('<header>', cover + '\n<header>', 1)
    return html


def build_pipeline_a3_html(html: str) -> str:
    """Extrae SOLO el panel #pipeline para exportar en A3 landscape."""
    html = re.sub(r'<!-- PORTADA ANEXO.*?</div>\s*\n', '', html, flags=re.DOTALL)
    html = re.sub(r'<nav>.*?</nav>', '', html, flags=re.DOTALL)
    # Ocultar todos los paneles menos pipeline
    html = re.sub(
        r'class="panel(?: active)?"',
        'class="panel" style="display:none;"',
        html,
    )
    # Mostrar solo el pipeline con estilos A3
    html = html.replace(
        'id="pipeline" class="panel"',
        'id="pipeline" class="panel" style="display:block !important;padding:20px 32px 32px;"',
    )
    # Etiqueta de sección visible
    html = html.replace('.panel-print-title { display: none; }', '.panel-print-title { display: block; }')
    html = html.replace('background: #eef1f6;', 'background: white;')
    # Inyectar @page A3 landscape al inicio del <style>
    a3_page = "@page { size: A3 landscape; margin: 12mm 15mm; }\n"
    html = html.replace('<style>', '<style>\n' + a3_page, 1)
    # Reducir fuentes para A3
    html = html.replace(
        '.pipeline-wrap {',
        '.pipeline-wrap { box-shadow: none !important; border: 1pt solid #e2e8f0; /* a3 */'
    )
    return html


def _run_chrome(chrome: str, in_path: str, out_pdf: Path) -> None:
    cmd = [
        chrome,
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={out_pdf}",
        "--print-to-pdf-no-header", "--no-margins",
        "--run-all-compositor-stages-before-draw",
        f"file:///{in_path}",
    ]
    print("Generando PDF...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    time.sleep(3)
    if out_pdf.exists():
        kb = out_pdf.stat().st_size / 1024
        print(f"PDF generado: {out_pdf.name} ({kb:.1f} KB)")
        print(f"  Ruta: {out_pdf}")
    else:
        print("ERROR: PDF no generado")
        if result.stderr:
            print("STDERR:", result.stderr[:400])
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera PDF de ARQUITECTURA_v2026.html")
    parser.add_argument(
        "--pipeline-a3", action="store_true",
        help="Exportar solo el panel Pipeline en A3 landscape (ARQUITECTURA_v2026_Pipeline_A3.pdf)"
    )
    args = parser.parse_args()

    chrome = find_chrome()
    print(f"Navegador: {chrome}")
    src = SRC_HTML.read_text(encoding="utf-8")
    print(f"HTML leido: {len(src):,} bytes")

    if args.pipeline_a3:
        print("Modo: Pipeline A3 landscape")
        pdf_html = build_pipeline_a3_html(src)
        out_pdf = OUT_PDF_PIPELINE_A3
    else:
        print("Modo: A4 completo (portada + 4 secciones)")
        pdf_html = build_print_html(src)
        out_pdf = OUT_PDF

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(pdf_html)
        tmp_path = tmp.name
    print(f"HTML temporal: {tmp_path}")

    _run_chrome(chrome, tmp_path, out_pdf)
    Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

