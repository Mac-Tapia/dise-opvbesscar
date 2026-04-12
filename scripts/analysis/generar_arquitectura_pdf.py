"""
Genera la arquitectura y flujo de trabajo del proyecto pvbesscar en:
  1. HTML interactivo con Mermaid.js (reports/ARQUITECTURA_v2026.html)
  2. PNG de alta resolución con matplotlib (reports/ARQUITECTURA_v2026.png)
  3. PDF multipágina con reportlab (reports/ARQUITECTURA_v2026.pdf)
"""
from __future__ import annotations

from pathlib import Path
import textwrap

# ─── paths ────────────────────────────────────────────────────────────────────
REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

MMD_PIPELINE = REPORTS / "OE2_OE3_PIPELINE_COMPLETO.mmd"
MMD_FLUJO    = REPORTS / "02_FLUJO_TRABAJO_DETALLADO.mmd"

HTML_OUT = REPORTS / "ARQUITECTURA_v2026.html"
PNG_OUT  = REPORTS / "ARQUITECTURA_v2026.png"
PDF_OUT  = REPORTS / "ARQUITECTURA_v2026.pdf"

# ══════════════════════════════════════════════════════════════════════════════
# 1) HTML INTERACTIVO
# ══════════════════════════════════════════════════════════════════════════════
PIPELINE_MMD = MMD_PIPELINE.read_text(encoding="utf-8")
FLUJO_MMD    = MMD_FLUJO.read_text(encoding="utf-8")

html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arquitectura PVBESSCAR — v2026</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f5f7fa;
    color: #1a1a2e;
  }}
  header {{
    background: linear-gradient(135deg, #1b5e20 0%, #0d47a1 100%);
    color: white;
    padding: 24px 40px;
    box-shadow: 0 4px 12px rgba(0,0,0,.3);
  }}
  header h1 {{ font-size: 1.8rem; letter-spacing: 1px; }}
  header p  {{ font-size: 0.95rem; opacity: .85; margin-top: 6px; }}
  .badge {{
    display: inline-block;
    background: rgba(255,255,255,.2);
    border: 1px solid rgba(255,255,255,.4);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: .78rem;
    margin-right: 8px;
    margin-top: 10px;
  }}
  nav {{
    background: #1a237e;
    padding: 0 40px;
    display: flex;
    gap: 4px;
  }}
  nav button {{
    background: transparent;
    color: rgba(255,255,255,.75);
    border: none;
    padding: 14px 20px;
    cursor: pointer;
    font-size: .92rem;
    border-bottom: 3px solid transparent;
    transition: all .2s;
  }}
  nav button:hover, nav button.active {{
    color: #fff;
    border-bottom-color: #64b5f6;
    background: rgba(255,255,255,.08);
  }}
  .panel {{ display: none; padding: 32px 40px; }}
  .panel.active {{ display: block; }}
  .section-title {{
    font-size: 1.2rem;
    font-weight: 700;
    color: #1b5e20;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #a5d6a7;
  }}
  .diagram-wrap {{
    background: white;
    border-radius: 12px;
    padding: 28px;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
    overflow-x: auto;
    margin-bottom: 24px;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .kpi-card {{
    background: white;
    border-radius: 10px;
    padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
    border-left: 4px solid #2e7d32;
  }}
  .kpi-card.gold {{ border-left-color: #f9a825; }}
  .kpi-card.blue {{ border-left-color: #1565c0; }}
  .kpi-card.red  {{ border-left-color: #c62828; }}
  .kpi-card.purple {{ border-left-color: #6a1b9a; }}
  .kpi-label {{ font-size: .75rem; color: #666; text-transform: uppercase; letter-spacing: .5px; }}
  .kpi-value {{ font-size: 1.4rem; font-weight: 700; color: #1a1a2e; margin-top: 4px; }}
  .kpi-sub   {{ font-size: .78rem; color: #888; margin-top: 2px; }}
  .agent-table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
    margin-bottom: 24px;
  }}
  .agent-table th {{
    background: #1b5e20;
    color: white;
    padding: 12px 16px;
    text-align: left;
    font-size: .85rem;
  }}
  .agent-table td {{
    padding: 11px 16px;
    border-bottom: 1px solid #f0f0f0;
    font-size: .88rem;
  }}
  .agent-table tr:nth-child(even) td {{ background: #f9fbe7; }}
  .winner {{ background: #fffde7 !important; font-weight: 700; }}
  .stat-box {{
    background: #e8f5e9;
    border-left: 4px solid #43a047;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
    font-size: .9rem;
    line-height: 1.7;
  }}
  footer {{
    background: #1a237e;
    color: rgba(255,255,255,.6);
    text-align: center;
    padding: 18px;
    font-size: .8rem;
    margin-top: 40px;
  }}
</style>
</head>
<body>

<header>
  <h1>🔋 Arquitectura PVBESSCAR — Pipeline OE2 → OE3</h1>
  <p>Sistema de carga inteligente con RL para motos y mototaxis eléctricas — Iquitos, Perú</p>
  <div>
    <span class="badge">📅 12/04/2026</span>
    <span class="badge">🏆 SAC Ganador OE3</span>
    <span class="badge">☀️ 4,050 kWp</span>
    <span class="badge">🔋 2,000 kWh BESS</span>
    <span class="badge">🔌 38 sockets</span>
    <span class="badge">📄 v11 — 594 párrafos</span>
  </div>
</header>

<nav>
  <button class="active" onclick="show('home')">📊 KPIs</button>
  <button onclick="show('pipeline')">🔄 Pipeline Completo</button>
  <button onclick="show('flujo')">📋 Flujo de Trabajo</button>
  <button onclick="show('agentes')">🤖 Ranking Agentes</button>
</nav>

<!-- ═══ PANEL: KPIs ═══════════════════════════════════════════════════════ -->
<div id="home" class="panel active">
  <div class="section-title">📊 Resultados Clave — OE3 Selección de Agente RL (12/04/2026)</div>

  <div class="kpi-grid">
    <div class="kpi-card gold">
      <div class="kpi-label">🏆 Agente Ganador</div>
      <div class="kpi-value">SAC</div>
      <div class="kpi-sub">Soft Actor-Critic — off-policy</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">F₂ Mínimo SAC (ep 48)</div>
      <div class="kpi-value">2,622,734 kg</div>
      <div class="kpi-sub">CO₂/año — emisiones con RL</div>
    </div>
    <div class="kpi-card red">
      <div class="kpi-label">F₀ Baseline Diesel</div>
      <div class="kpi-value">7,054,000 kg</div>
      <div class="kpi-sub">CO₂/año — sin solar, sin RL</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">CO₂ Total Evitado</div>
      <div class="kpi-value">4,431,266 kg</div>
      <div class="kpi-sub">62.8% reducción vs. F₀</div>
    </div>
    <div class="kpi-card blue">
      <div class="kpi-label">Debt Violations SAC</div>
      <div class="kpi-value">0</div>
      <div class="kpi-sub">100% EVs cargados a tiempo</div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-label">BESS Descarga ep.48</div>
      <div class="kpi-value">875,698 kWh</div>
      <div class="kpi-sub">Energía BESS → red EV</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Episodios Entrenados</div>
      <div class="kpi-value">50 × 3</div>
      <div class="kpi-sub">= 1,314,000 pasos totales</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Documento Final</div>
      <div class="kpi-value">v11</div>
      <div class="kpi-sub">594 párrafos | 50 figuras | 6.4 MB</div>
    </div>
  </div>

  <div class="stat-box">
    <strong>🔬 Validación Estadística:</strong><br>
    Kruskal-Wallis H = 81.65, p = 1.86×10⁻¹⁸ → diferencias altamente significativas entre los 3 agentes<br>
    Mann-Whitney SAC vs PPO: p = 3.02×10⁻¹⁶ → SAC estadísticamente superior<br>
    Wilcoxon T = 0, p = 1.78×10⁻¹⁵ → SAC ep.48 vs. baseline confirmado
  </div>

  <div class="stat-box" style="background:#e3f2fd; border-left-color:#1565c0;">
    <strong>📐 Fórmulas CO₂ (§2.2.4 del informe):</strong><br>
    F₀ = Σ(Nᵥ × dᵥ × 365 × FEᵥ) = 7,054,000 kg CO₂/año &nbsp;|&nbsp; FE_ICE_moto = 2.146 kg CO₂/L<br>
    F₁ = (E_EV,base + E_mall) × FE_red = 5,789,814 kg CO₂/año &nbsp;|&nbsp; FE_red = 0.4521 kg CO₂/kWh<br>
    F₂ = E_red,RL × FE_red &nbsp;|&nbsp; E_red(t) = max{"{"}0, E_EV+E_mall−E_solar−E_BESS,desc{"}"}
  </div>
</div>

<!-- ═══ PANEL: PIPELINE ═══════════════════════════════════════════════════ -->
<div id="pipeline" class="panel">
  <div class="section-title">🔄 Pipeline Completo OE2 → OE3 (Actualizado 12/04/2026)</div>
  <div class="diagram-wrap">
    <div class="mermaid">
{PIPELINE_MMD}
    </div>
  </div>
</div>

<!-- ═══ PANEL: FLUJO ══════════════════════════════════════════════════════ -->
<div id="flujo" class="panel">
  <div class="section-title">📋 Flujo de Trabajo Detallado — 9 Etapas</div>
  <div class="diagram-wrap">
    <div class="mermaid">
{FLUJO_MMD}
    </div>
  </div>
</div>

<!-- ═══ PANEL: AGENTES ════════════════════════════════════════════════════ -->
<div id="agentes" class="panel">
  <div class="section-title">🤖 Ranking de Agentes RL — Resultados Reales (50 episodios)</div>

  <table class="agent-table">
    <thead>
      <tr>
        <th>Rank</th>
        <th>Agente</th>
        <th>F₂ mín (kg CO₂/año)</th>
        <th>Episodio óptimo</th>
        <th>Debt Violations</th>
        <th>F₂ media ± std</th>
        <th>BESS desc. (kWh)</th>
        <th>Grid import (kWh)</th>
      </tr>
    </thead>
    <tbody>
      <tr class="winner">
        <td>🏆 1°</td>
        <td><strong>SAC</strong><br><small>Soft Actor-Critic</small></td>
        <td><strong>2,622,734</strong></td>
        <td>ep. 48</td>
        <td>✅ 0</td>
        <td>2,668,375 ± 89,475</td>
        <td>875,698</td>
        <td>5,801,227</td>
      </tr>
      <tr>
        <td>🥈 2°</td>
        <td><strong>PPO</strong><br><small>Proximal Policy Opt.</small></td>
        <td>2,787,039</td>
        <td>ep. 40</td>
        <td>✅ 0</td>
        <td>2,875,569 ± 113,816</td>
        <td>919,033</td>
        <td>6,164,653</td>
      </tr>
      <tr>
        <td>🥉 3°</td>
        <td><strong>A2C</strong><br><small>Advantage Actor-Critic</small></td>
        <td>2,834,857</td>
        <td>ep. 3</td>
        <td>⚠️ 217</td>
        <td>2,845,012 ± 12,011</td>
        <td>744,717</td>
        <td>6,270,421</td>
      </tr>
      <tr style="background:#ffebee;">
        <td>📌 Ref.</td>
        <td><strong>F₁ Solar+BESS</strong><br><small>Sin agente RL</small></td>
        <td>5,789,814</td>
        <td>—</td>
        <td>—</td>
        <td>—</td>
        <td>—</td>
        <td>—</td>
      </tr>
      <tr style="background:#fce4ec;">
        <td>📌 Ref.</td>
        <td><strong>F₀ Baseline Diesel</strong><br><small>Sin solar, sin RL</small></td>
        <td>7,054,000</td>
        <td>—</td>
        <td>—</td>
        <td>—</td>
        <td>—</td>
        <td>—</td>
      </tr>
    </tbody>
  </table>

  <div class="stat-box">
    <strong>🧠 Por qué SAC ganó:</strong><br>
    SAC (off-policy) acumula experiencias en un replay buffer, lo que le permite reutilizar información de episodios anteriores y aprender políticas más estables con menor varianza (σ=89,475 vs σ=113,816 PPO). Su entropía regularizada evita colapsos de política que afectan a A2C (217 violations). Con 50 episodios de entrenamiento completos, SAC convergió en el ep.48 con F₂=2,622,734 kg CO₂/año, evitando 4,431,266 kg CO₂/año (62.8% vs F₀).
  </div>

  <div class="stat-box" style="background:#e8eaf6; border-left-color:#283593;">
    <strong>📋 Infraestructura de carga (OE2):</strong><br>
    19 cargadores × 2 sockets = 38 puntos de carga &nbsp;|&nbsp; Mode 3 — 7.4 kW @ 230V / 32A<br>
    BESS: 2,000 kWh / 400 kW &nbsp;|&nbsp; DoD 80% &nbsp;|&nbsp; η=95% &nbsp;|&nbsp; SOC: 20%–100%<br>
    Solar: 4,050 kWp &nbsp;|&nbsp; FE_red = 0.4521 kg CO₂/kWh &nbsp;|&nbsp; Iquitos, Perú (PVGIS 2024)
  </div>
</div>

<footer>
  pvbesscar — Tesis OE3 Selección Agente RL | Branch: smartcharger | Generado: 12/04/2026
</footer>

<script>
  mermaid.initialize({{ startOnLoad: false, theme: 'default', securityLevel: 'loose' }});

  // Pre-renderizar TODOS los diagramas al cargar (incluyendo paneles ocultos)
  window.addEventListener('load', async () => {{
    const elems = document.querySelectorAll('.mermaid');
    for (const el of elems) {{
      const uid = 'mg' + Math.random().toString(36).slice(2, 9);
      try {{
        const {{svg}} = await mermaid.render(uid, el.textContent.trim());
        el.innerHTML = svg;
      }} catch (e) {{
        el.innerHTML = '<pre style="color:red;background:#fff3f3;padding:12px;border-radius:6px;font-size:12px">Error Mermaid: ' + e.message + '</pre>';
        console.error('Mermaid render error:', uid, e);
      }}
    }}
  }});

  function show(id) {{
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    event.target.classList.add('active');
  }}
</script>
</body>
</html>"""

HTML_OUT.write_text(html_template, encoding="utf-8")
print(f"✅ HTML interactivo: {HTML_OUT}")

# ══════════════════════════════════════════════════════════════════════════════
# 2) PNG + PDF — Diagrama arquitectura con matplotlib
# ══════════════════════════════════════════════════════════════════════════════
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

fig = plt.figure(figsize=(50, 70), facecolor="#f5f7fa")
ax = fig.add_subplot(111)
ax.set_xlim(0, 50)
ax.set_ylim(0, 70)
ax.axis("off")
fig.tight_layout(pad=0.5)

# ─── helpers ──────────────────────────────────────────────────────────────────
_BOXES: dict = {}

def box(ax, x, y, text, facecolor="#ffffff", edgecolor="#333333",
        fontsize=14, bold=False, text_color="#1a1a2e", linewidth=2.0,
        pad=0.25, name=None):
    """Caja auto-ajustada al contorno del texto."""
    weight = "bold" if bold else "normal"
    t = ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
                fontweight=weight, color=text_color, zorder=4,
                multialignment="center", linespacing=1.4,
                bbox=dict(
                    boxstyle=f"round,pad={pad}",
                    facecolor=facecolor,
                    edgecolor=edgecolor,
                    linewidth=linewidth,
                    zorder=3,
                ))
    if name:
        _BOXES[name] = (x, y, t)
    return t

def arrow(ax, x1, y1, x2, y2, color="#555555", lw=2.5, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=22,
                                shrinkA=10, shrinkB=10),
                zorder=5)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.18, my, label, fontsize=11, color=color, zorder=6,
                ha="left", va="center")

def section_bg(ax, x, y, w, h, color, label, label_color="#ffffff"):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.15,rounding_size=0.5",
        facecolor=color, edgecolor=label_color, linewidth=2.5,
        alpha=0.15, zorder=1
    )
    ax.add_patch(patch)
    ax.text(x + 0.3, y + h - 0.4, label, fontsize=14, fontweight="bold",
            color=label_color, va="top", zorder=2, alpha=0.95)

# ─── Título ───────────────────────────────────────────────────────────────────
ax.text(25, 69.4, "ARQUITECTURA PVBESSCAR — Pipeline OE2 → OE3",
        ha="center", va="center", fontsize=24, fontweight="bold",
        color="#1b5e20")
ax.text(25, 68.7, "Sistema de carga inteligente con Aprendizaje por Refuerzo · Iquitos, Peru · 12/04/2026",
        ha="center", va="center", fontsize=13, color="#555555")

# ══════════════════════════════════════════════════════════════════════════════
# FILA 1 — OE2 Datos de entrada  (banda y 63.2 → 68.0)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 63.2, 49.2, 4.8, "#e65100",
           "OE2 — DIMENSIONAMIENTO (Infraestructura) — Datos de entrada", "#e65100")

box(ax,  6.5, 65.6,
    "Solar PV — Datos de entrada\n4,050 kWp DC · E=8,292,514 kWh/año\n200,632 módulos Kyocera KS20\n2 inversores Eaton Xpert1670\nBD: PVGIS 2024 (pvlib-python)",
    "#fff8e1", "#f9a825", fontsize=14, pad=0.28, name="oe2_solar")

box(ax, 18.5, 65.6,
    "BESS — Datos de entrada\n2,000 kWh / 400 kW\nDoD 80% · eta 95%\nBD: Python (datos reales)",
    "#f3e5f5", "#7b1fa2", fontsize=14, pad=0.28, name="oe2_bess")

box(ax, 31.0, 65.6,
    "Cargadores EV — Datos de entrada\n19 cargadores x 2 sockets = 38 puntos\nMode 3 · 7.4 kW/socket\nBD: Python (datos reales)",
    "#e3f2fd", "#1565c0", fontsize=14, pad=0.28, name="oe2_ev")

box(ax, 43.5, 65.6,
    "Mall + EV — Datos de entrada\nDatos historico: max 2,763 kWh/h\nmedia 1,412 kWh/h · 12,368,653 kWh/año\n270 motos + 39 mototaxis · Python",
    "#e8f5e9", "#2e7d32", fontsize=14, pad=0.28, name="oe2_mall")

# ══════════════════════════════════════════════════════════════════════════════
# FILA 2 — Validacion y carga OE2  (banda y 56.5 → 63.0)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 56.5, 49.2, 6.5, "#7b1fa2",
           "VALIDACION Y CARGA OE2  (data_loader.py v5.8)", "#7b1fa2")

box(ax,  4.0, 59.7,
    "data_loader.py v5.8\nCarga 4 datasets OE2\nFallback Interim si\nfalta OE2 primario",
    "#ede7f6", "#7b1fa2", fontsize=13, pad=0.25, name="loader")

box(ax, 13.0, 59.7,
    "Solar PV — PVGIS 2024\n8,760 h horarias\nE=8,292,514 kWh/año\n4,050 kWp DC max 2,887 kW",
    "#fff8e1", "#f9a825", fontsize=13, pad=0.25, name="val_solar")

box(ax, 23.0, 59.7,
    "BESS — Python\n8,760 filas\nSOC en (20 %, 100 %)\n2,000 kWh / 400 kW",
    "#f3e5f5", "#7b1fa2", fontsize=13, pad=0.25, name="val_bess")

box(ax, 33.5, 59.7,
    "Cargadores EV — Python\n38 sockets confirmados\n19 units x 2 Mode 3\n7.4 kW/socket",
    "#e3f2fd", "#1565c0", fontsize=13, pad=0.25, name="val_ev")

box(ax, 43.5, 59.7,
    "Mall + EV — Python\n8,760 filas\nmax 2,763 kWh/h\n309 vehiculos",
    "#e8f5e9", "#2e7d32", fontsize=13, pad=0.25, name="val_mall")

# flechas OE2 → validacion
arrow(ax,  6.5, 63.3, 13.0, 61.6, "#f9a825", lw=2.5)
arrow(ax, 18.5, 63.3, 23.0, 61.6, "#7b1fa2", lw=2.5)
arrow(ax, 31.0, 63.3, 33.5, 61.6, "#1565c0", lw=2.5)
arrow(ax, 43.5, 63.3, 43.5, 61.6, "#2e7d32", lw=2.5)

# ══════════════════════════════════════════════════════════════════════════════
# FILA 3 — Entorno CityLearn v2  (banda y 48.5 → 56.2)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 48.5, 49.2, 7.7, "#2e7d32",
           "ENTORNO CityLearn v2", "#2e7d32")

box(ax,  9.5, 54.2,
    "schema_builder.py\nCSVs + schema JSON\ndata/interim/citylearn_v2/\nenergy_simulation · weather\ncarbon_intensity: 0.4521 kg/kWh",
    "#c8e6c9", "#1b5e20", fontsize=13, pad=0.25, name="schema")

box(ax, 25.0, 54.2,
    "env_factory.py\nCityLearnEnv (BESS + PV + Mall)\n+ IquitosEVChargingWrapper\n+ Monitor(SB3) — compatible PPO/A2C/SAC",
    "#e8f5e9", "#2e7d32", fontsize=13, pad=0.25, name="envfactory")

box(ax, 40.5, 54.2,
    "Espacio de estados OE3\nObs: 16D (CityLearn 11D + EV 5D)\nAccion: 3D — bess [-1,1]\n     ev_motos_frac [0,1]\n     ev_mototaxis_frac [0,1]",
    "#f1f8e9", "#33691e", fontsize=13, pad=0.25, name="space")

box(ax, 25.0, 50.4,
    "CityLearn v2  ·  1 timestep = 1 h  ·  1 episodio = 8,760 pasos = 1 año"
    "     Obs: 16-dim  ·  Accion: 3-dim  ·  CO2_factor = 0.4521 kg CO2/kWh",
    "#e8f5e9", "#2e7d32", fontsize=13, pad=0.22, name="cl_env")

# flechas: val → schema
arrow(ax, 13.0, 57.8,  9.5, 56.1, "#7b1fa2", lw=2.2)
arrow(ax, 23.0, 57.8, 14.5, 56.1, "#7b1fa2", lw=2.2)
arrow(ax, 33.5, 57.8, 21.0, 56.1, "#7b1fa2", lw=2.0)
arrow(ax, 43.5, 57.8, 28.0, 56.1, "#7b1fa2", lw=2.0)
# schema → env_factory
arrow(ax, 16.2, 53.3, 19.8, 53.3, "#1b5e20", lw=2.5)
# env_factory → space
arrow(ax, 30.8, 53.3, 34.2, 53.3, "#2e7d32", lw=2.5)
# env_factory → cl_env
arrow(ax, 25.0, 51.9, 25.0, 51.2, "#2e7d32", lw=2.5)

# ══════════════════════════════════════════════════════════════════════════════
# FILA 4 — Recompensa + Agentes  (banda y 36.5 → 48.2)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 36.5, 49.2, 11.7, "#e65100",
           "RECOMPENSA + ENTRENAMIENTO  (50 episodios x 8,760 pasos)", "#ff6f00")

box(ax, 25.0, 46.3,
    "Recompensa CO2_DUAL_FOCUS v7.0     "
    "w1=0.35 CO2 directo  ·  w2=0.30 CO2 indirecto     "
    "w3=0.25 carga EV  ·  w4=0.05 solar  ·  w5=0.05 red",
    "#fff3e0", "#ff6f00", fontsize=13, pad=0.28, name="reward")

# CityLearn → reward
arrow(ax, 25.0, 49.5, 25.0, 47.4, "#2e7d32", lw=3.0)

box(ax,  7.5, 40.8,
    "SAC — Ganador OE3\nSoft Actor-Critic (off-policy)\n50 eps · F2=2,622,734 kg CO2/año\nep.optimo=48 · Violations=0",
    "#fffde7", "#e65100", fontsize=16, pad=0.32, bold=True, name="sac")

box(ax, 25.0, 40.8,
    "PPO — Segundo\nProximal Policy Opt. (on-policy)\n50 eps · F2=2,787,039 kg CO2/año\nep.optimo=40 · Violations=0",
    "#e3f2fd", "#1565c0", fontsize=16, pad=0.32, name="ppo")

box(ax, 42.5, 40.8,
    "A2C — Tercero\nAdvantage Actor-Critic (on-policy)\n50 eps · F2=2,834,857 kg CO2/año\nep.optimo=3 · Violations=217",
    "#f3e5f5", "#6a1b9a", fontsize=16, pad=0.32, name="a2c")

# reward → cada agente
arrow(ax, 25.0, 45.2,  7.5, 42.8, "#ff6f00", lw=2.8)
arrow(ax, 25.0, 45.2, 25.0, 42.8, "#ff6f00", lw=2.8)
arrow(ax, 25.0, 45.2, 42.5, 42.8, "#ff6f00", lw=2.8)

# ══════════════════════════════════════════════════════════════════════════════
# FILA 5 — Metricas y Checkpoints  (banda y 29.5 → 36.2)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 29.5, 49.2, 6.7, "#c62828",
           "METRICAS Y CHECKPOINTS", "#c62828")

box(ax,  7.5, 33.0,
    "checkpoints/SAC/sac_ep48_best.zip\noutputs/sac_training/ · 11 PNGs",
    "#fce4ec", "#c62828", fontsize=13, pad=0.25, name="ckpt_sac")

box(ax, 25.0, 33.0,
    "checkpoints/PPO/ppo_ep40_best.zip\noutputs/ppo_training/ · 11 PNGs",
    "#e3f2fd", "#1565c0", fontsize=13, pad=0.25, name="ckpt_ppo")

box(ax, 42.5, 33.0,
    "checkpoints/A2C/a2c_ep03_best.zip\noutputs/a2c_training/ · 11 PNGs",
    "#f3e5f5", "#6a1b9a", fontsize=13, pad=0.25, name="ckpt_a2c")

# agentes → checkpoints
arrow(ax,  7.5, 38.8,  7.5, 34.5, "#e65100", lw=2.8)
arrow(ax, 25.0, 38.8, 25.0, 34.5, "#1565c0", lw=2.8)
arrow(ax, 42.5, 38.8, 42.5, 34.5, "#6a1b9a", lw=2.8)

# ══════════════════════════════════════════════════════════════════════════════
# FILA 6 — Validacion estadistica  (banda y 22.5 → 29.2)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 22.5, 49.2, 6.7, "#283593",
           "VALIDACION ESTADISTICA", "#283593")

box(ax, 25.0, 25.9,
    "Kruskal-Wallis H=81.65, p=1.86e-18     "
    "Mann-Whitney SAC vs PPO p=3.02e-16     "
    "Wilcoxon T=0, p=1.78e-15     "
    "CO2 evitado SAC: 4,431,266 kg/año · Reduccion: 62.8 % vs F0",
    "#e8eaf6", "#283593", fontsize=13, pad=0.30, name="stats")

# checkpoints → validacion estadistica
arrow(ax,  7.5, 31.5,  9.5, 27.7, "#c62828", lw=2.5)
arrow(ax, 25.0, 31.5, 25.0, 27.7, "#1565c0", lw=2.5)
arrow(ax, 42.5, 31.5, 40.5, 27.7, "#6a1b9a", lw=2.5)

# ══════════════════════════════════════════════════════════════════════════════
# FILA 7 — Analisis comparativo + hipotesis  (banda y 15.5 → 22.2)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 15.5, 49.2, 6.7, "#f57f17",
           "ANALISIS COMPARATIVO + HIPOTESIS", "#f57f17")

box(ax, 13.5, 19.0,
    "comparative_analysis/ · 10 figs\nconvergencia · varianza · baseline\noutputs/seccion52/ · 5 figs estadisticas",
    "#fff8e1", "#f57f17", fontsize=13, pad=0.28, name="compare")

box(ax, 38.0, 19.0,
    "hypothesis_test/ · Wilcoxon figura completa\ndemostracion_hipotesis/ · panel integrado",
    "#fff8e1", "#e65100", fontsize=13, pad=0.28, name="hypo")

# estadistica → analisis
arrow(ax, 17.0, 23.5, 15.0, 20.6, "#283593", lw=2.5)
arrow(ax, 33.0, 23.5, 36.0, 20.6, "#283593", lw=2.5)

# ══════════════════════════════════════════════════════════════════════════════
# FILA 8 — Documento Tesis  (banda y 7.5 → 15.2)
# ══════════════════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 7.5, 49.2, 7.7, "#1b5e20",
           "DOCUMENTO TESIS — v11 FINAL", "#1b5e20")

box(ax, 25.0, 11.4,
    "INFORME_OE3_SELECCION_AGENTE_RL_v11.docx\n"
    "594 parrafos · 36 tablas · 6,376 KB · 50 figuras insertadas\n"
    "S2.2.4 Bases teoricas GHG (F0, F1, F2, SOC BESS, R(t))"
    "  ·  S4.6.3 Procedimiento OE3 (11 subsecciones)  ·  S5.x Resultados OE2+OE3\n"
    "ANEXO A: 33 figs entrenamiento (SAC/PPO/A2C)  ·  ANEXO B: 10 figs comparativo"
    "  ·  ANEXO C: 7 figs hipotesis",
    "#c8e6c9", "#1b5e20", fontsize=18, pad=0.38, bold=True, name="tesis")

# analisis → tesis
arrow(ax, 13.5, 17.5, 12.0, 13.6, "#f57f17", lw=3.0)
arrow(ax, 38.0, 17.5, 39.5, 13.6, "#e65100", lw=3.0)
# estadistica → tesis (flecha central directa)
arrow(ax, 25.0, 22.5, 25.0, 13.6, "#283593", lw=3.2)

# ── TABLA RESUMEN inferior (y 0.1 → 7.2) ─────────────────────────────────────
section_bg(ax, 0.4, 0.1, 49.2, 7.1, "#37474f",
           "RESUMEN CUANTITATIVO — OE3 (datos reales 12/04/2026)", "#37474f")
rows = [
    ("Metrica",             "SAC ★",      "PPO",        "A2C",        "F1 Solar+BESS", "F0 Diesel"),
    ("F2 min (kg CO2/ano)", "2,622,734",  "2,787,039",  "2,834,857",  "5,789,814",     "7,054,000"),
    ("Reduccion vs. F0",    "62.8%",      "60.5%",      "59.8%",      "17.9%",         "0%"),
    ("Ep. optimo",          "48",         "40",         "3",          "--",            "--"),
    ("Debt violations",     "0 OK",       "0 OK",       "217 WARN",   "--",            "--"),
    ("BESS desc. (kWh)",    "875,698",    "919,033",    "744,717",    "--",            "--"),
]
col_w = [9.2, 7.5, 7.5, 7.5, 7.5, 7.5]
xs    = [0.8, 10.2, 17.7, 25.2, 32.7, 40.2]
header_y = 6.8
row_h    = 1.08

for row_i, row in enumerate(rows):
    y_pos = header_y - row_i * row_h
    for col_i, (cell, cw, cx) in enumerate(zip(row, col_w, xs)):
        fc = "#37474f" if row_i == 0 else ("#fffde7" if col_i == 1 else "#ffffff")
        tc = "white" if row_i == 0 else ("#1a1a2e" if col_i != 1 else "#1b5e20")
        bx = FancyBboxPatch((cx, y_pos - row_h + 0.08), cw - 0.15, row_h - 0.12,
                            boxstyle="round,pad=0.07", facecolor=fc,
                            edgecolor="#cccccc", linewidth=0.8, zorder=3)
        ax.add_patch(bx)
        fw = "bold" if row_i == 0 or col_i == 1 else "normal"
        ax.text(cx + (cw-0.15)/2, y_pos - row_h/2 + 0.05, cell,
                ha="center", va="center", fontsize=12, fontweight=fw,
                color=tc, zorder=4)

# ─── save ─────────────────────────────────────────────────────────────────────
plt.savefig(PNG_OUT, dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print(f"✅ PNG: {PNG_OUT}")

# ══════════════════════════════════════════════════════════════════════════════
# 3) PDF con reportlab
# ══════════════════════════════════════════════════════════════════════════════
from reportlab.lib.pagesizes import A4, portrait
from reportlab.platypus import (SimpleDocTemplate, Image, Spacer, Paragraph,
                                 Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

PAGE = portrait(A4)  # A4 retrato
doc = SimpleDocTemplate(
    str(PDF_OUT),
    pagesize=PAGE,
    rightMargin=1.5*cm, leftMargin=1.5*cm,
    topMargin=1.5*cm, bottomMargin=1.5*cm,
)

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "TitleBig", parent=styles["Title"],
    fontSize=20, leading=26, spaceAfter=6,
    textColor=colors.HexColor("#1b5e20"), alignment=TA_CENTER
)
sub_style = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontSize=11, spaceAfter=10, textColor=colors.HexColor("#555555"),
    alignment=TA_CENTER
)
h2_style = ParagraphStyle(
    "H2Style", parent=styles["Heading2"],
    fontSize=14, textColor=colors.HexColor("#1565c0"),
    spaceBefore=12, spaceAfter=6
)
body_style = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=11, leading=15, spaceAfter=10
)

# tabla KPIs
kpi_data = [
    ["Métrica", "SAC ★ (Ganador)", "PPO (2°)", "A2C (3°)", "F₁ Solar+BESS", "F₀ Diesel"],
    ["F₂ mín (kg CO₂/año)", "2,622,734", "2,787,039", "2,834,857", "5,789,814", "7,054,000"],
    ["Reducción vs. F₀",    "62.8%",      "60.5%",     "59.8%",     "17.9%",     "0%"],
    ["Episodio óptimo",      "48",         "40",         "3",          "—",         "—"],
    ["Debt violations",      "0 ✅",       "0 ✅",       "217 ⚠️",    "—",         "—"],
    ["BESS descarga (kWh)",  "875,698",    "919,033",    "744,717",    "—",         "—"],
    ["Grid import (kWh)",    "5,801,227",  "6,164,653",  "6,270,421",  "—",         "—"],
    ["F₂ media (kg/año)",    "2,668,375",  "2,875,569",  "2,845,012",  "—",         "—"],
    ["Desv. estándar F₂",   "89,475",     "113,816",    "12,011",     "—",         "—"],
]
GREEN  = colors.HexColor("#1b5e20")
LGRE   = colors.HexColor("#c8e6c9")
LBLU   = colors.HexColor("#e3f2fd")
GOLD   = colors.HexColor("#fffde7")
WHITE  = colors.white
GREY   = colors.HexColor("#f5f5f5")

kpi_ts = TableStyle([
    ("BACKGROUND", (0,0), (-1,0), GREEN),
    ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
    ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",   (0,0), (-1,0), 11),
    ("FONTSIZE",   (0,1), (-1,-1), 9),
    ("ALIGN",      (0,0), (-1,-1), "CENTER"),
    ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ("FONTNAME",   (0,1), (0,-1), "Helvetica-Bold"),
    ("BACKGROUND", (1,1), (1,-1), GOLD),
    ("BACKGROUND", (0,1), (0,-1), GREY),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GREY]),
    ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
])

stat_data = [
    ["Prueba Estadística", "Resultado", "Interpretación"],
    ["Kruskal-Wallis",     "H=81.65, p=1.86×10⁻¹⁸", "Diferencias altamente significativas entre los 3 agentes (α=0.05)"],
    ["Mann-Whitney SAC vs PPO", "p=3.02×10⁻¹⁶", "SAC estadísticamente superior a PPO en reducción CO₂"],
    ["Wilcoxon ep.48 vs baseline", "T=0, p=1.78×10⁻¹⁵", "SAC ep.48 confirma reducción CO₂ vs. F₁ Solar+BESS"],
]
stat_ts = TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#283593")),
    ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
    ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE",   (0,0), (-1,0), 11),
    ("FONTSIZE",   (0,1), (-1,-1), 9),
    ("FONTNAME",   (0,1), (0,-1), "Helvetica-Bold"),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#e8eaf6"), WHITE]),
    ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#9fa8da")),
    ("ALIGN",      (0,0), (-1,-1), "LEFT"),
    ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
])

pw = PAGE[0] - 3*cm  # page width usable

story = [
    Paragraph("ARQUITECTURA PVBESSCAR — Pipeline OE2 → OE3", title_style),
    Paragraph(
        "Sistema de carga inteligente con Aprendizaje por Refuerzo para motos y mototaxis eléctricas — Iquitos, Perú · 12/04/2026",
        sub_style),

    Paragraph("1. Diagrama de Arquitectura Completa", h2_style),
    Image(str(PNG_OUT), width=pw, height=min(pw * 35.7/25.2, PAGE[1] - 4*cm)),  # A4 retrato

    Spacer(1, 0.4*cm),
    Paragraph("2. Resultados Comparativos — 3 Agentes RL (50 episodios cada uno)", h2_style),
    Table(kpi_data,
          colWidths=[pw*0.22, pw*0.14, pw*0.14, pw*0.14, pw*0.17, pw*0.17],
          style=kpi_ts, repeatRows=1),

    Spacer(1, 0.4*cm),
    Paragraph("3. Validación Estadística", h2_style),
    Table(stat_data,
          colWidths=[pw*0.2, pw*0.22, pw*0.56],
          style=stat_ts, repeatRows=1),

    Spacer(1, 0.3*cm),
    Paragraph(
        "Conclusión OE3: El agente SAC (Soft Actor-Critic, off-policy) es el óptimo para el sistema PVBESSCAR. "
        "Con F₂=2,622,734 kg CO₂/año en el episodio 48, evita 4,431,266 kg CO₂/año "
        "(62.8% de reducción vs. F₀=7,054,000 kg CO₂/año baseline diésel). "
        "Las pruebas estadísticas no paramétricas confirman la superioridad con p&lt;0.001 en todos los criterios. "
        "Documento tesis: INFORME_OE3_SELECCION_AGENTE_RL_v11.docx (594 párrafos, 36 tablas, 50 figuras).",
        body_style),
]

doc.build(story)
print(f"✅ PDF: {PDF_OUT}")
print()
print("═══════════════════════════════════════════════════")
print("GENERACIÓN COMPLETA:")
print(f"  HTML → {HTML_OUT}")
print(f"  PNG  → {PNG_OUT}")
print(f"  PDF  → {PDF_OUT}")
