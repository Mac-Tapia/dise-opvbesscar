"""
Convierte reports/ARQUITECTURA_v2026.html a PDF para el Anexo D.

Genera un HTML lineal (sin pestanas JS) con portada de Anexo
y lo convierte a PDF usando Chrome headless.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[2]
SRC_HTML = ROOT / "reports" / "ARQUITECTURA_v2026.html"
OUT_PDF  = ROOT / "reports" / "ARQUITECTURA_v2026.pdf"

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
    """Transforma el HTML con pestanas en un HTML lineal para PDF."""
    # Quitar portada de Anexo interactiva si existe
    html = re.sub(r'<!-- PORTADA ANEXO.*?</div>\s*\n', '', html, flags=re.DOTALL)
    # Eliminar nav
    html = re.sub(r'<nav>.*?</nav>', '', html, flags=re.DOTALL)
    # Hacer todos los panels visibles
    html = re.sub(
        r'class="panel(?: active)?"',
        'class="panel" style="display:block;padding:28px 40px 40px;"',
        html,
    )
    # Salto de pagina antes de cada panel excepto el primero (home)
    for pid in ("pipeline", "flujo", "agentes"):
        html = html.replace(
            f'id="{pid}" class="panel"',
            f'id="{pid}" class="panel" style="display:block;padding:28px 40px 40px;page-break-before:always;"',
        )
    # Mostrar etiquetas de seccion
    html = html.replace('.panel-print-title { display: none; }', '.panel-print-title { display: block; }')
    # Fondo blanco
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


def main() -> None:
    chrome = find_chrome()
    print(f"Navegador: {chrome}")
    src = SRC_HTML.read_text(encoding="utf-8")
    print(f"HTML leido: {len(src):,} bytes")
    pdf_html = build_print_html(src)

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(pdf_html)
        tmp_path = tmp.name
    print(f"HTML temporal: {tmp_path}")

    cmd = [
        chrome,
        "--headless=new", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={OUT_PDF}",
        "--print-to-pdf-no-header", "--no-margins",
        "--run-all-compositor-stages-before-draw",
        f"file:///{tmp_path}",
    ]
    print("Generando PDF...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    time.sleep(3)
    Path(tmp_path).unlink(missing_ok=True)

    if OUT_PDF.exists():
        kb = OUT_PDF.stat().st_size / 1024
        print(f"PDF generado: {OUT_PDF.name} ({kb:.1f} KB)")
        print(f"  Ruta: {OUT_PDF}")
    else:
        print("ERROR: PDF no generado")
        if result.stderr:
            print("STDERR:", result.stderr[:400])
        sys.exit(1)


if __name__ == "__main__":
    main()
