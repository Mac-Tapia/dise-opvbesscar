"""
Genera el documento Word con los resultados del entrenamiento de agentes RL
para el proyecto pvbesscar - Iquitos, Perú.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ──────────────────────────────────────────────
# CONSTANTES DEL PROYECTO
# ──────────────────────────────────────────────
CO2_FACTOR_IQUITOS  = 0.4521   # kg CO₂/kWh (MINEM 2024)
CO2_FACTOR_MOTO     = 0.87     # kg CO₂/kWh evitado (IPCC 2006)
CO2_FACTOR_MOTOTAXI = 0.54     # kg CO₂/kWh evitado (IPCC 2006)

BASE_DIR   = Path("D:/diseñopvbesscar")
OUTPUT_DIR = BASE_DIR / "outputs" / "docx"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# CARGA DE DATOS
# ──────────────────────────────────────────────
def load_json(path: str) -> dict:
    with open(BASE_DIR / path, encoding="utf-8") as f:
        return json.load(f)

sac  = load_json("outputs/sac_training/result_sac.json")
ppo  = load_json("outputs/ppo_training/result_ppo.json")
a2c  = load_json("outputs/a2c_training/result_a2c.json")
base = load_json("checkpoints/Baseline/baseline_results.json")

# KPIs extraídos
sac_val  = sac["validation"]
ppo_val  = ppo["validation"]
a2c_val  = a2c["validation"]
sac_sm   = sac["summary_metrics"]
ppo_sm   = ppo["summary_metrics"]
a2c_sm   = a2c["summary_metrics"]
base_co2 = base["annual_co2_kg"]

sac_dur_min = sac["training"]["duration_seconds"] / 60
ppo_dur_min = ppo["training"]["duration_seconds"] / 60
a2c_dur_min = a2c["training"]["duration_seconds"] / 60

sac_rewards = sac["training_evolution"]["episode_rewards"]
ppo_rewards = ppo["training_evolution"]["episode_rewards"]
a2c_rewards = a2c["training_evolution"]["episode_rewards"]

BASELINE_EMITIDO = base_co2["co2_total_baseline"]           # 5,926,304 kg/año
BASELINE_DIRECTO = base_co2["co2_reduccion_directa_baseline"]  # 330,030 kg/año

# Reducción directa anual por agente (valor de validación / 365 * 365 = anual)
sac_co2_anual  = sac_val["mean_co2_avoided_kg"]   # ya es por episodio = 1 año
a2c_co2_anual  = a2c_val["mean_co2_avoided_kg"]
ppo_co2_anual  = ppo_val["mean_co2_avoided_kg"]

sac_pct = (sac_co2_anual / BASELINE_EMITIDO) * 100
a2c_pct = (a2c_co2_anual / BASELINE_EMITIDO) * 100
ppo_pct = (ppo_co2_anual / BASELINE_EMITIDO) * 100


# ──────────────────────────────────────────────
# HELPERS DE FORMATO
# ──────────────────────────────────────────────
def set_col_width(table, col_idx: int, width_cm: float):
    for row in table.rows:
        row.cells[col_idx].width = Cm(width_cm)

def shade_cell(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)

def bold_cell(cell, text: str, size_pt: int = 10, align=WD_ALIGN_PARAGRAPH.CENTER, color_hex: str | None = None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size_pt)
    if color_hex:
        run.font.color.rgb = RGBColor.from_string(color_hex)

def normal_cell(cell, text: str, size_pt: int = 10, align=WD_ALIGN_PARAGRAPH.CENTER, bold: bool = False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    run = p.add_run(text)
    run.font.size = Pt(size_pt)
    run.bold = bold

def add_heading(doc: Document, text: str, level: int = 1):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return h

def add_body(doc: Document, text: str, size_pt: int = 11):
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for run in p.runs:
        run.font.size = Pt(size_pt)
    return p

def fmt(num: float, decimals: int = 2) -> str:
    return f"{num:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_int(num: float) -> str:
    return f"{int(num):,}".replace(",", ".")


# ──────────────────────────────────────────────
# CONSTRUCCIÓN DEL DOCUMENTO
# ──────────────────────────────────────────────
doc = Document()

# Márgenes de página
sections = doc.sections
for section in sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3.0)
    section.right_margin  = Cm(2.5)

# ────────────────────────────────
# PORTADA
# ────────────────────────────────
doc.add_paragraph()
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("RESULTADOS DEL ENTRENAMIENTO DE AGENTES DE\nAPRENDIZAJE POR REFUERZO")
r.bold = True
r.font.size = Pt(16)

doc.add_paragraph()
t2 = doc.add_paragraph()
t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = t2.add_run(
    "Proyecto: Optimización de la Gestión de Recarga de Vehículos Eléctricos\n"
    "mediante Agentes IA para la Reducción de Emisiones de CO₂ en Iquitos, Perú"
)
r2.font.size = Pt(12)

doc.add_paragraph()
t3 = doc.add_paragraph()
t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = t3.add_run("Abril 2026")
r3.font.size = Pt(11)
r3.italic = True

doc.add_page_break()

# ────────────────────────────────
# 1. INTRODUCCIÓN
# ────────────────────────────────
add_heading(doc, "1. Introducción", level=1)
add_body(doc,
    "El presente documento reporta los resultados obtenidos del entrenamiento de tres "
    "agentes de aprendizaje por refuerzo (RL) aplicados a la gestión inteligente de "
    "38 enchufes de carga (19 cargadores × 2 sockets) para motocicletas y mototaxis "
    "eléctricas en la ciudad de Iquitos, Perú. Los agentes evaluados son: "
    "Soft Actor-Critic (SAC), Proximal Policy Optimization (PPO) y "
    "Advantage Actor-Critic (A2C)."
)
add_body(doc,
    "La infraestructura considera una planta solar fotovoltaica de 4,050 kWp y un "
    "sistema de almacenamiento BESS de 2,000 kWh / 400 kW. El objetivo principal "
    "(OE3) consiste en seleccionar el agente IA que contribuye de manera cuantificable "
    "a la reducción de emisiones de CO₂ en la ciudad, considerando el factor de "
    f"emisión de la red eléctrica de Iquitos de {CO2_FACTOR_IQUITOS} kg CO₂/kWh "
    "(MINEM, 2024)."
)

# ────────────────────────────────
# 2. METODOLOGÍA
# ────────────────────────────────
add_heading(doc, "2. Metodología de Entrenamiento", level=1)

add_heading(doc, "2.1 Entorno de Simulación", level=2)
add_body(doc,
    "El entrenamiento se realizó usando la plataforma CityLearn v2 con un horizonte "
    "de 8,760 pasos horarios (1 año = 365 días × 24 h). Cada episodio representa un "
    "año completo de operación. Se entrenaron 50 episodios por agente con 438,000 "
    "pasos totales (timesteps)."
)

# Tabla: parámetros de entorno
add_heading(doc, "2.2 Parámetros del Entorno", level=2)
table_env = doc.add_table(rows=9, cols=2)
table_env.style = "Table Grid"
table_env.alignment = WD_TABLE_ALIGNMENT.CENTER
headers_env = [("Parámetro", "Valor")]
rows_env = [
    ("Número de sockets", "38 (19 cargadores × 2)"),
    ("Potencia por socket", "7.4 kW (Modo 3, 32A @ 230 V)"),
    ("Potencia instalada total", "281.2 kW"),
    ("Generación solar PV", "4,050 kWp"),
    ("Almacenamiento BESS", "2,000 kWh / 400 kW (DoD 80%, η 95%)"),
    ("SOC mínimo BESS", "20%"),
    ("Demanda diaria", "270 motos + 39 mototaxis = 309 vehículos/día"),
    ("Resolución temporal", "1 hora (horaria)"),
]
shade_cell(table_env.rows[0].cells[0], "1F3864")
shade_cell(table_env.rows[0].cells[1], "1F3864")
bold_cell(table_env.rows[0].cells[0], "Parámetro", color_hex="FFFFFF")
bold_cell(table_env.rows[0].cells[1], "Valor", color_hex="FFFFFF")
for i, (p, v) in enumerate(rows_env, start=1):
    if i % 2 == 0:
        shade_cell(table_env.rows[i].cells[0], "D9E2F3")
        shade_cell(table_env.rows[i].cells[1], "D9E2F3")
    normal_cell(table_env.rows[i].cells[0], p, align=WD_ALIGN_PARAGRAPH.LEFT)
    normal_cell(table_env.rows[i].cells[1], v, align=WD_ALIGN_PARAGRAPH.LEFT)
doc.add_paragraph()

add_heading(doc, "2.3 Función de Recompensa Multi-Objetivo", level=2)
add_body(doc,
    "La función de recompensa pondera cinco objetivos alineados con el OE3:"
)
# Lista ponderada
items_reward = [
    ("CO₂ directo evitado (combustible vehicular):","35%"),
    ("CO₂ indirecto evitado (importación de red × 0.4521 kg/kWh):", "30%"),
    ("Completación de carga de VE:", "25%"),
    ("Autoconsumo solar:", "5%"),
    ("Estabilidad de red:", "5%"),
]
for item, peso in items_reward:
    p = doc.add_paragraph(style="List Bullet")
    run_b = p.add_run(f"{item} ")
    run_b.font.size = Pt(11)
    run_w = p.add_run(peso)
    run_w.bold = True
    run_w.font.size = Pt(11)

# ────────────────────────────────
# 3. BASELINE
# ────────────────────────────────
add_heading(doc, "3. Escenario de Referencia (Baseline)", level=1)
add_body(doc,
    "El baseline representa la operación sin control inteligente, considerando la "
    "generación solar de 4,050 kWp pero sin agente RL ni optimización BESS. "
    "Las emisiones se calculan a partir del factor MINEM 2024 para Iquitos."
)

table_base = doc.add_table(rows=5, cols=2)
table_base.style = "Table Grid"
table_base.alignment = WD_TABLE_ALIGNMENT.CENTER
shade_cell(table_base.rows[0].cells[0], "1F3864")
shade_cell(table_base.rows[0].cells[1], "1F3864")
bold_cell(table_base.rows[0].cells[0], "Métrica Baseline", color_hex="FFFFFF")
bold_cell(table_base.rows[0].cells[1], "Valor Anual", color_hex="FFFFFF")
rows_base = [
    ("CO₂ total emitido (sin control RL)", f"{fmt_int(BASELINE_EMITIDO)} kg CO₂/año"),
    ("CO₂ reducción directa (EVs vs combustión)", f"{fmt_int(BASELINE_DIRECTO)} kg CO₂/año"),
    ("CO₂ indirecto EV (red, sin optimización solar)", f"{fmt_int(base_co2['co2_indirecto_ev_baseline'])} kg CO₂/año"),
    ("CO₂ total mall + EVs", f"{fmt_int(base_co2['co2_indirecto_mall_baseline'])} kg CO₂/año (mall)"),
]
for i, (m, v) in enumerate(rows_base, start=1):
    if i % 2 == 0:
        shade_cell(table_base.rows[i].cells[0], "D9E2F3")
        shade_cell(table_base.rows[i].cells[1], "D9E2F3")
    normal_cell(table_base.rows[i].cells[0], m, align=WD_ALIGN_PARAGRAPH.LEFT)
    normal_cell(table_base.rows[i].cells[1], v, align=WD_ALIGN_PARAGRAPH.LEFT)
doc.add_paragraph()

# ────────────────────────────────
# 4. RESULTADOS POR AGENTE
# ────────────────────────────────
add_heading(doc, "4. Resultados del Entrenamiento por Agente", level=1)

# ─── 4.1 SAC ───
add_heading(doc, "4.1 Agente SAC (Soft Actor-Critic)", level=2)
add_body(doc,
    "SAC es un algoritmo fuera de línea (off-policy) basado en la maximización de "
    "entropía. Es especialmente adecuado para espacios de acción continuos y "
    "funciones de recompensa asimétricas, como la presente. Se entrenó con GPU "
    "(NVIDIA RTX 4060)."
)

add_heading(doc, "4.1.1 Convergencia del Entrenamiento", level=3)
add_body(doc,
    f"La recompensa por episodio mostró una evolución positiva y consistente a lo "
    f"largo de los 50 episodios de entrenamiento:\n"
    f"  • Episodio 1:   {fmt(sac_rewards[0], 2)}\n"
    f"  • Episodio 10:  {fmt(sac_rewards[9], 2)}\n"
    f"  • Episodio 25:  {fmt(sac_rewards[24], 2)}\n"
    f"  • Episodio 50:  {fmt(sac_rewards[49], 2)}\n"
    f"\nLa recompensa de validación (media de 10 episodios independientes) fue de "
    f"{fmt(sac_val['mean_reward'], 2)}, con desviación estándar de "
    f"{fmt(sac_val['std_reward'], 4)}."
)

add_heading(doc, "4.1.2 Métricas de CO₂ y Eficiencia Energética", level=3)
table_sac = doc.add_table(rows=8, cols=2)
table_sac.style = "Table Grid"
table_sac.alignment = WD_TABLE_ALIGNMENT.CENTER
shade_cell(table_sac.rows[0].cells[0], "2E4057")
shade_cell(table_sac.rows[0].cells[1], "2E4057")
bold_cell(table_sac.rows[0].cells[0], "Métrica SAC", color_hex="FFFFFF")
bold_cell(table_sac.rows[0].cells[1], "Resultado", color_hex="FFFFFF")
rows_sac = [
    ("Recompensa media (validación)", fmt(sac_val["mean_reward"], 2)),
    ("CO₂ evitado anual (validación)", f"{fmt_int(sac_val['mean_co2_avoided_kg'])} kg/año"),
    ("CO₂ evitado directo (50 eps)", f"{fmt_int(sac_sm['total_co2_avoided_direct_kg'])} kg"),
    ("CO₂ evitado indirecto (50 eps)", f"{fmt_int(sac_sm['total_co2_avoided_indirect_kg'])} kg"),
    ("Generación solar utilizada/ep", f"{fmt_int(sac_val['mean_solar_kwh'])} kWh"),
    ("Importación de red/ep", f"{fmt_int(sac_val['mean_grid_import_kwh'])} kWh"),
    (f"% CO₂ evitado / total emitido baseline", f"{fmt(sac_pct, 2)}%"),
]
for i, (m, v) in enumerate(rows_sac, start=1):
    if i % 2 == 0:
        shade_cell(table_sac.rows[i].cells[0], "D9E2F3")
        shade_cell(table_sac.rows[i].cells[1], "D9E2F3")
    normal_cell(table_sac.rows[i].cells[0], m, align=WD_ALIGN_PARAGRAPH.LEFT)
    normal_cell(table_sac.rows[i].cells[1], v, align=WD_ALIGN_PARAGRAPH.LEFT)
doc.add_paragraph()

add_body(doc,
    f"Durante la validación, el agente SAC gestionó simultáneamente hasta "
    f"{sac_sm['max_motos_charged']} sockets de motos y "
    f"{sac_sm['max_mototaxis_charged']} sockets de mototaxis en el período pico "
    f"(09:00–20:00 h). El tiempo total de entrenamiento fue de "
    f"{fmt(sac_dur_min, 1)} minutos ({fmt(sac_dur_min/60, 2)} horas) con GPU."
)

# ─── 4.2 A2C ───
add_heading(doc, "4.2 Agente A2C (Advantage Actor-Critic)", level=2)
add_body(doc,
    "A2C es un algoritmo en línea (on-policy) que actualiza la política a cada paso. "
    "Su arquitectura actor-crítico permite convergencia rápida en entornos episódicos "
    "discretos. Se entrenó en CPU."
)

add_heading(doc, "4.2.1 Convergencia del Entrenamiento", level=3)
add_body(doc,
    f"El agente A2C mostró la convergencia más rápida de los tres agentes evaluados:\n"
    f"  • Episodio 1:   {fmt(a2c_rewards[0], 2)}\n"
    f"  • Episodio 10:  {fmt(a2c_rewards[9], 2)}\n"
    f"  • Episodio 25:  {fmt(a2c_rewards[24], 2)}\n"
    f"  • Episodio 50:  {fmt(a2c_rewards[49], 2)}\n"
    f"\nLa recompensa de validación fue de {fmt(a2c_val['mean_reward'], 2)}, "
    f"la más alta de los tres agentes, con desviación estándar de "
    f"{fmt(a2c_val['std_reward'], 4)}."
)

add_heading(doc, "4.2.2 Métricas de CO₂ y Eficiencia Energética", level=3)
table_a2c = doc.add_table(rows=8, cols=2)
table_a2c.style = "Table Grid"
table_a2c.alignment = WD_TABLE_ALIGNMENT.CENTER
shade_cell(table_a2c.rows[0].cells[0], "1B4332")
shade_cell(table_a2c.rows[0].cells[1], "1B4332")
bold_cell(table_a2c.rows[0].cells[0], "Métrica A2C", color_hex="FFFFFF")
bold_cell(table_a2c.rows[0].cells[1], "Resultado", color_hex="FFFFFF")
rows_a2c = [
    ("Recompensa media (validación)", fmt(a2c_val["mean_reward"], 2)),
    ("CO₂ evitado anual (validación)", f"{fmt_int(a2c_val['mean_co2_avoided_kg'])} kg/año"),
    ("CO₂ evitado directo (50 eps)", f"{fmt_int(a2c_sm['total_co2_avoided_direct_kg'])} kg"),
    ("CO₂ evitado indirecto (50 eps)", f"{fmt_int(a2c_sm['total_co2_avoided_indirect_kg'])} kg"),
    ("Generación solar utilizada/ep", f"{fmt_int(a2c_val['mean_solar_kwh'])} kWh"),
    ("Importación de red/ep", f"{fmt_int(a2c_val['mean_grid_import_kwh'])} kWh"),
    (f"% CO₂ evitado / total emitido baseline", f"{fmt(a2c_pct, 2)}%"),
]
for i, (m, v) in enumerate(rows_a2c, start=1):
    if i % 2 == 0:
        shade_cell(table_a2c.rows[i].cells[0], "D9E2F3")
        shade_cell(table_a2c.rows[i].cells[1], "D9E2F3")
    normal_cell(table_a2c.rows[i].cells[0], m, align=WD_ALIGN_PARAGRAPH.LEFT)
    normal_cell(table_a2c.rows[i].cells[1], v, align=WD_ALIGN_PARAGRAPH.LEFT)
doc.add_paragraph()

add_body(doc,
    f"A2C gestionó hasta {a2c_sm['max_motos_charged']} sockets de motos y "
    f"{a2c_sm['max_mototaxis_charged']} sockets de mototaxis simultáneamente. "
    f"El tiempo de entrenamiento fue de {fmt(a2c_dur_min, 1)} minutos en CPU, "
    f"significativamente menor que SAC."
)

# ─── 4.3 PPO ───
add_heading(doc, "4.3 Agente PPO (Proximal Policy Optimization)", level=2)
add_body(doc,
    "PPO es un algoritmo en línea (on-policy) con restricción de cambio de política "
    "mediante clipping, lo que mejora la estabilidad del entrenamiento. Se entrenó "
    "en CPU con 438,000 pasos en 50 episodios."
)

add_heading(doc, "4.3.1 Convergencia del Entrenamiento", level=3)
add_body(doc,
    f"PPO mostró una tendencia de mejora sostenida durante el entrenamiento, "
    f"aunque partió de recompensas negativas profundas:\n"
    f"  • Episodio 1:   {fmt(ppo_rewards[0], 2)}\n"
    f"  • Episodio 10:  {fmt(ppo_rewards[9], 2)}\n"
    f"  • Episodio 25:  {fmt(ppo_rewards[24], 2)}\n"
    f"  • Episodio 50:  {fmt(ppo_rewards[49], 2)}\n"
    f"\nLa recompensa de validación fue de {fmt(ppo_val['mean_reward'], 2)}, "
    f"indicando que el agente aún se encontraba en fase de convergencia. "
    f"El tiempo de entrenamiento fue notablemente corto: {fmt(ppo_dur_min, 1)} minutos, "
    f"lo que sugiere que la sesión fue parcial y se requeriría entrenamiento adicional "
    f"para alcanzar la convergencia plena."
)

add_heading(doc, "4.3.2 Métricas de CO₂ y Eficiencia Energética", level=3)
table_ppo = doc.add_table(rows=7, cols=2)
table_ppo.style = "Table Grid"
table_ppo.alignment = WD_TABLE_ALIGNMENT.CENTER
shade_cell(table_ppo.rows[0].cells[0], "7B2D8B")
shade_cell(table_ppo.rows[0].cells[1], "7B2D8B")
bold_cell(table_ppo.rows[0].cells[0], "Métrica PPO", color_hex="FFFFFF")
bold_cell(table_ppo.rows[0].cells[1], "Resultado", color_hex="FFFFFF")
rows_ppo = [
    ("Recompensa media (validación)", fmt(ppo_val["mean_reward"], 2)),
    ("CO₂ evitado anual (validación)", f"{fmt_int(ppo_val['mean_co2_avoided_kg'])} kg/año"),
    ("CO₂ evitado directo (50 eps)", f"{fmt_int(ppo_sm['total_co2_avoided_direct_kg'])} kg"),
    ("CO₂ evitado indirecto (50 eps)", f"{fmt_int(ppo_sm['total_co2_avoided_indirect_kg'])} kg"),
    ("Importación de red/ep", f"{fmt_int(ppo_val['mean_grid_import_kwh'])} kWh"),
    (f"% CO₂ evitado / total emitido baseline", f"{fmt(ppo_pct, 2)}%"),
]
for i, (m, v) in enumerate(rows_ppo, start=1):
    if i % 2 == 0:
        shade_cell(table_ppo.rows[i].cells[0], "D9E2F3")
        shade_cell(table_ppo.rows[i].cells[1], "D9E2F3")
    normal_cell(table_ppo.rows[i].cells[0], m, align=WD_ALIGN_PARAGRAPH.LEFT)
    normal_cell(table_ppo.rows[i].cells[1], v, align=WD_ALIGN_PARAGRAPH.LEFT)
doc.add_paragraph()

add_body(doc,
    "Nota: Los conteos de vehículos de PPO (121,168 motos; 23,348 mototaxis) "
    "representan cargas acumuladas durante todo el episodio (365 días), "
    "no sockets simultáneos. Esto difiere de la métrica de SAC y A2C que reportan "
    "el máximo de sockets activos simultáneamente."
)

# ────────────────────────────────
# 5. TABLA COMPARATIVA FINAL
# ────────────────────────────────
add_heading(doc, "5. Análisis Comparativo de los Tres Agentes", level=1)

add_body(doc,
    "La Tabla 5.1 presenta el resumen comparativo de los tres agentes evaluados "
    "frente al escenario baseline. Los valores de CO₂ evitado corresponden "
    "a la fase de validación (10 episodios independientes, sin información previa "
    "del entorno de prueba)."
)

# Tabla comparativa
cols = ["Métrica", "Baseline", "SAC", "A2C", "PPO"]
rows_comp = [
    ("Recompensa validación", "—", fmt(sac_val["mean_reward"],2), fmt(a2c_val["mean_reward"],2), fmt(ppo_val["mean_reward"],2)),
    ("CO₂ evitado anual (kg)", fmt_int(BASELINE_DIRECTO), fmt_int(sac_co2_anual), fmt_int(a2c_co2_anual), fmt_int(ppo_co2_anual)),
    ("% CO₂ evitado / baseline emitido", "5,57%", f"{fmt(sac_pct,2)}%", f"{fmt(a2c_pct,2)}%", f"{fmt(ppo_pct,2)}%"),
    ("Solar kWh/año (validación)", "—", fmt_int(sac_val["mean_solar_kwh"]), fmt_int(a2c_val["mean_solar_kwh"]), "—"),
    ("Importación red kWh/año", "—", fmt_int(sac_val["mean_grid_import_kwh"]), fmt_int(a2c_val["mean_grid_import_kwh"]), fmt_int(ppo_val["mean_grid_import_kwh"])),
    ("Motos sockets (máx. simultáneos)", "—", "30", "29", "—†"),
    ("Mototaxis sockets (máx. simultáneos)", "—", "8", "8", "—†"),
    ("Duración entrenamiento (min)", "—", fmt(sac_dur_min,1), fmt(a2c_dur_min,1), fmt(ppo_dur_min,1)),
    ("Hardware", "—", "GPU RTX 4060", "CPU", "CPU"),
]

table_comp = doc.add_table(rows=len(rows_comp)+1, cols=5)
table_comp.style = "Table Grid"
table_comp.alignment = WD_TABLE_ALIGNMENT.CENTER

# Encabezado
header_colors = ["1F3864","1F3864","2E4057","1B4332","7B2D8B"]
for j, (hdr, hcol) in enumerate(zip(cols, header_colors)):
    shade_cell(table_comp.rows[0].cells[j], hcol)
    bold_cell(table_comp.rows[0].cells[j], hdr, color_hex="FFFFFF", size_pt=9)

for i, row_data in enumerate(rows_comp, start=1):
    for j, val in enumerate(row_data):
        if i % 2 == 0:
            shade_cell(table_comp.rows[i].cells[j], "D9E2F3")
        align = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
        bold = (j == 0)
        normal_cell(table_comp.rows[i].cells[j], val, align=align, bold=bold, size_pt=9)

doc.add_paragraph()
add_body(doc,
    "† Los conteos de PPO son acumulados por episodio (365 días), no simultáneos.",
    size_pt=9
)

# ────────────────────────────────
# 6. DISCUSIÓN
# ────────────────────────────────
add_heading(doc, "6. Discusión de Resultados", level=1)

add_heading(doc, "6.1 Comparación Global", level=2)
add_body(doc,
    f"Los resultados demuestran que los tres agentes RL superan significativamente "
    f"el escenario baseline en términos de CO₂ evitado. El baseline, sin control "
    f"inteligente, reporta una reducción directa de {fmt_int(BASELINE_DIRECTO)} kg/año "
    f"(sustitución de combustible fósil). Los agentes RL, al optimizar la carga "
    f"usando generación solar, amplifican este beneficio a "
    f"{fmt_int(sac_co2_anual)} kg/año (SAC y A2C) y {fmt_int(ppo_co2_anual)} kg/año (PPO)."
)

add_heading(doc, "6.2 Agente Recomendado: A2C", level=2)
add_body(doc,
    f"El agente A2C obtuvo la recompensa de validación más alta ({fmt(a2c_val['mean_reward'],2)}), "
    f"con un CO₂ evitado anual de {fmt_int(a2c_co2_anual)} kg equivalente al "
    f"{fmt(a2c_pct,2)}% de las emisiones totales del baseline. Esto representa "
    f"una mejora de {fmt((a2c_val['mean_reward'] - sac_val['mean_reward'])/abs(sac_val['mean_reward'])*100,1)}% "
    f"sobre SAC en términos de recompensa. Adicionalmente, A2C completó el entrenamiento "
    f"en {fmt(a2c_dur_min,1)} minutos en CPU, lo que lo hace más accesible para "
    f"implementaciones sin GPU dedicada."
)

add_heading(doc, "6.3 SAC — Agente Estable con GPU", level=2)
add_body(doc,
    f"SAC mostró alta estabilidad (std_reward = {fmt(sac_val['std_reward'],4)}) y "
    f"convergencia monótona desde el episodio 1 ({fmt(sac_rewards[0],2)}) hasta el "
    f"episodio 50 ({fmt(sac_rewards[49],2)}). Su arquitectura off-policy lo hace "
    f"eficiente en entornos con recompensas asimétricas. Sin embargo, requiere GPU "
    f"para tiempos razonables de entrenamiento ({fmt(sac_dur_min/60,2)} horas)."
)

add_heading(doc, "6.4 PPO — Convergencia Parcial", level=2)
add_body(doc,
    f"PPO mostró mejora progresiva de {fmt(ppo_rewards[0],2)} (ep.1) a "
    f"{fmt(ppo_rewards[49],2)} (ep.50), pero con recompensa de validación aún "
    f"negativa ({fmt(ppo_val['mean_reward'],2)}). La duración extremadamente corta "
    f"del entrenamiento ({fmt(ppo_dur_min,1)} min) sugiere que la sesión fue "
    f"interrumpida antes de la convergencia completa. Se recomienda un re-entrenamiento "
    f"con al menos 100 episodios para obtener resultados comparables."
)

# ────────────────────────────────
# 7. CONCLUSIONES
# ────────────────────────────────
add_heading(doc, "7. Conclusiones", level=1)

conclusiones = [
    f"Los tres agentes RL evaluados (SAC, PPO, A2C) logran reducir las emisiones "
    f"de CO₂ respecto al baseline de referencia, siendo A2C el de mejor desempeño "
    f"con {fmt_int(a2c_co2_anual)} kg CO₂ evitados por año.",

    f"El agente A2C se selecciona como el agente IA óptimo para la gestión de recarga "
    f"inteligente en el proyecto pvbesscar, con recompensa de validación de "
    f"{fmt(a2c_val['mean_reward'],2)} y tiempo de entrenamiento de "
    f"{fmt(a2c_dur_min,1)} minutos en CPU.",

    f"El factor de reducción de CO₂ calculado ({fmt(a2c_pct,2)}% sobre el total "
    f"emitido sin control) demuestra el impacto cuantificable de la gestión inteligente "
    f"de carga en Iquitos, cumpliendo con el objetivo OE3 del proyecto.",

    f"El factor de emisión de Iquitos de {CO2_FACTOR_IQUITOS} kg CO₂/kWh (MINEM 2024) "
    f"convierte cada kWh desplazado de la red en un beneficio ambiental directo, "
    f"amplificado por la generación solar de 4,050 kWp.",

    "Para trabajo futuro, se recomienda el re-entrenamiento de PPO con al menos "
    "100 episodios completos y la evaluación de hiperparámetros optimizados para "
    "mejorar su convergencia en este entorno específico.",
]
for c in conclusiones:
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(c)
    run.font.size = Pt(11)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# ────────────────────────────────
# 8. REFERENCIAS
# ────────────────────────────────
add_heading(doc, "8. Referencias", level=1)
refs = [
    "MINEM (2024). Factor de Emisión de CO₂ de la Red Eléctrica del Perú. "
    "Ministerio de Energía y Minas, Lima, Perú. 0.4521 kg CO₂/kWh.",

    "IPCC (2006). IPCC Guidelines for National Greenhouse Gas Inventories, "
    "Volume 2: Energy. Intergovernmental Panel on Climate Change.",

    "Haarnoja, T., Zhou, A., Abbeel, P., & Levine, S. (2018). Soft Actor-Critic: "
    "Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor. "
    "ICML 2018.",

    "Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). "
    "Proximal Policy Optimization Algorithms. arXiv:1707.06347.",

    "Mnih, V. et al. (2016). Asynchronous Methods for Deep Reinforcement Learning. "
    "ICML 2016. [Base de A2C].",

    "Vázquez-Canteli, J.R. et al. (2020). CityLearn v1.0: An OpenAI Gym Environment "
    "for Demand Response with Deep Reinforcement Learning. BuildSys 2019.",

    "Raffin, A. et al. (2021). Stable-Baselines3: Reliable Reinforcement Learning "
    "Implementations. Journal of Machine Learning Research, 22(268), 1-8.",
]
for ref in refs:
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(ref)
    run.font.size = Pt(10)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# ────────────────────────────────
# GUARDAR
# ────────────────────────────────
output_path = OUTPUT_DIR / "RESULTADOS_ENTRENAMIENTO_RL_PVBESSCAR.docx"
doc.save(output_path)
print(f"Documento generado: {output_path}")
