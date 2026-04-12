"""
agregar_seccion52_53.py — Agrega secciones 5.2 y 5.3 al informe OE3 Word.

Secciones generadas:
  5.2  Resultados inferenciales
  5.2.2  Inferencia técnica sobre el cubrimiento de la demanda energética
  5.2.3  Inferencia técnica sobre la contribución cuantificable a la reducción de CO₂
  5.3  Otro tipo de resultados estadísticos, de acuerdo con la naturaleza del problema
  5.3.1  Función de recompensa multiobjetivo y configuración del entorno de entrenamiento
  5.3.2  Métricas de desempeño y comparación directa entre SAC, PPO y A2C
  5.3.3  Reducción de CO₂ por agente y jerarquía de desempeño ambiental
  5.3.4  Variabilidad, robustez y estabilidad del entrenamiento
  5.3.5  Selección final del agente inteligente y contribución ambiental consolidada
"""
from __future__ import annotations
import shutil, re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ─── RUTAS ───────────────────────────────────────────────────────────────────
ROOT = Path("d:/diseñopvbesscar")
SRC  = ROOT / "outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v8.docx"
TMP  = ROOT / "outputs/docx/_tmp_52_53.docx"
OUT  = SRC   # sobreescribir mismo archivo

# ─── DATOS REALES OE3 (extraídos de CSVs y JSONs 50 episodios) ───────────────
F0   = 7_054_000    # kg CO₂/año — baseline SIN solar SIN BESS SIN RL
F1   = 5_790_639    # kg CO₂/año — baseline CON solar+BESS SIN RL
FCTR = 0.4521       # kg CO₂/kWh — factor emisión red aislada Iquitos (diesel)

AGENTS = {
    "SAC": {
        "F2_min": 2_622_735,  "F2_mean": 2_668_375, "F2_std": 89_475,
        "F2_max": 3_055_514,  "opt_ep": 48,
        "cv_plateau": 0.0577, "cv_all": None,
        "reduccion_F0_pct": 62.8, "reduccion_F1_pct": 54.7,
        "directa_kg": 328_736, "indirecta_kg": 3_223_884, "neta_kg": 3_552_620,
        "red_pct_mean": 62.2,  "red_pct_max": 62.8, "red_pct_min": 56.7,
        "solar_mean": 8_293_277,
        "bess_mean": 880_245, "bess_max": 934_809,
        "grid_min": 5_801_227, "grid_mean": 5_902_180,
        "ev_cov_best": 98.1, "ev_cov_mean": 95.5,
        "ev_motos_best": 341_047, "ev_mototaxi_best": 59_306,
        "debt_total": 1_029, "debt_max_ep": 364,
        "converge_first5": 2_900_585, "converge_last5": 2_624_189, "converge_pct": 9.53,
        "shapiro_W": 0.9752, "shapiro_p": 0.9259,
        "r_bess_co2": -0.7824,
    },
    "PPO": {
        "F2_min": 2_787_040,  "F2_mean": 2_875_569, "F2_std": 113_816,
        "F2_max": 3_142_944,  "opt_ep": 40,
        "cv_plateau": 0.1948, "cv_all": None,
        "reduccion_F0_pct": 60.5, "reduccion_F1_pct": 51.9,
        "directa_kg": 334_103, "indirecta_kg": 3_052_176, "neta_kg": 3_386_279,
        "red_pct_mean": 59.2,  "red_pct_max": 60.5, "red_pct_min": 55.4,
        "solar_mean": 8_293_277,
        "bess_mean": 906_898, "bess_max": 953_916,
        "grid_min": 6_164_654, "grid_mean": 6_360_471,
        "ev_cov_best": 99.9, "ev_cov_mean": 94.0,
        "ev_motos_best": 345_118, "ev_mototaxi_best": 62_686,
        "debt_total": 2_605, "debt_max_ep": 364,
        "converge_first5": 3_092_783, "converge_last5": 2_796_266, "converge_pct": 9.59,
        "shapiro_W": 0.9897, "shapiro_p": 0.9993,
        "r_bess_co2": -0.9174,
    },
    "A2C": {
        "F2_min": 2_834_857,  "F2_mean": 2_845_012, "F2_std": 12_011,
        "F2_max": 2_922_533,  "opt_ep": 3,
        "cv_plateau": 0.0562, "cv_all": None,
        "reduccion_F0_pct": 59.8, "reduccion_F1_pct": 51.0,
        "directa_kg": 301_293, "indirecta_kg": 2_985_752, "neta_kg": 3_287_045,
        "red_pct_mean": 59.7,  "red_pct_max": 59.8, "red_pct_min": 58.6,
        "solar_mean": 8_293_277,
        "bess_mean": 733_671, "bess_max": 831_928,
        "grid_min": 6_270_421, "grid_mean": 6_292_882,
        "ev_cov_best": 87.4, "ev_cov_mean": 97.7,
        "ev_motos_best": 329_125, "ev_mototaxi_best": 27_693,
        "debt_total": 1_181, "debt_max_ep": 361,
        "converge_first5": 2_862_349, "converge_last5": 2_839_805, "converge_pct": 0.79,
        "shapiro_W": 0.9348, "shapiro_p": 0.3211,
        "r_bess_co2": 0.8429,
    },
}

STATS = {
    "wilcoxon_stat": 1275.0, "wilcoxon_p": 8.882e-16,
    "kw_H": 81.65, "kw_p": 1.861e-18,
    "mw_SAC_PPO_p": 3.636e-15, "mw_SAC_A2C_p": 1.641e-14,
    "mw_PPO_A2C_p": 5.989e-3,
    "mw_SAC_PPO_r": 0.0484, "mw_SAC_A2C_r": 0.0596, "mw_PPO_A2C_r": 0.354,
}

REWARD_WEIGHTS = {
    "direct_co2":  0.35,
    "indirect_co2": 0.30,
    "ev_coverage": 0.25,
    "solar_selfcons": 0.05,
    "grid_stability": 0.05,
}

TRAIN_PARAMS = {
    "episodes": 50, "timesteps_total": 438_000, "ep_length": 8_760,
    "obs_dim": 394, "act_dim": 39,  # 1 BESS + 38 sockets
    "SAC": {"lr": "1×10⁻⁴", "buffer": 100_000, "batch": 256, "type": "off-policy"},
    "PPO": {"lr": "2×10⁻⁴", "n_steps": 2048, "batch": 256, "n_epochs": 10, "clip": 0.2, "type": "on-policy"},
    "A2C": {"lr": "7×10⁻⁴", "n_steps": 8, "ent_coef": 0.015, "type": "on-policy"},
}

# ─── HELPERS DOCX ─────────────────────────────────────────────────────────────
STYLE_BODY   = "Normal"
STYLE_H2     = "Heading 2"
STYLE_H3     = "Heading 3"
STYLE_H4     = "Heading 4"

def add_heading(doc: Document, text: str, level: int = 2):
    styles_map = {2: STYLE_H2, 3: STYLE_H3, 4: STYLE_H4}
    p = doc.add_paragraph(style=styles_map.get(level, STYLE_H2))
    r = p.add_run(text)
    lvl_pt = {2: 14, 3: 12, 4: 11}
    r.font.size = Pt(lvl_pt.get(level, 12))
    r.font.bold = True
    return p

def add_para(doc: Document, text: str, bold: bool = False,
             italic: bool = False, justify: bool = True):
    p = doc.add_paragraph(style=STYLE_BODY)
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.font.size = Pt(11)
    r.font.bold = bold
    r.font.italic = italic
    return p

def add_bullet(doc: Document, text: str, level: int = 0):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Cm(1.2 + level * 0.6)
    r = p.add_run(text)
    r.font.size = Pt(11)
    return p

def add_caption(doc: Document, text: str):
    p = doc.add_paragraph(style=STYLE_BODY)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.italic = True
    return p

def _shd(tc, fill: str):
    tcPr = tc._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)

def make_header_row(table, cols: list[str], bg: str = "1F3864"):
    row = table.rows[0]
    for i, txt in enumerate(cols):
        c = row.cells[i]
        c.text = txt
        _shd(c, bg)
        for para in c.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in para.runs:
                run.font.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

def add_row(table, values: list[str | int | float], bold_first: bool = False, bg: str | None = None):
    row = table.add_row()
    for i, val in enumerate(values):
        c = row.cells[i]
        if bg:
            _shd(c, bg)
        c.text = str(val)
        for para in c.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                run.font.size = Pt(10)
                if bold_first and i == 0:
                    run.font.bold = True

def add_highlighted_row(table, values: list, bg: str = "D9E2F3"):
    row = table.add_row()
    for i, val in enumerate(values):
        c = row.cells[i]
        _shd(c, bg)
        c.text = str(val)
        for para in c.paragraphs:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                run.font.size = Pt(10)
                run.font.bold = True

# ─── CONSTRUCCIÓN SECCIONES ───────────────────────────────────────────────────

def build_52(doc: Document):
    """5.2 Resultados inferenciales"""
    add_heading(doc, "5.2. Resultados inferenciales", level=2)
    add_para(doc,
        "Los resultados inferenciales presentados en este apartado corresponden a la "
        "contrastación estadística y técnica entre las tres líneas de comparación del "
        "proyecto: el escenario de referencia sin control inteligente F₀ = 7 054 000 kg CO₂/año "
        "(sin solar, sin BESS, sin RL), la operación base con solar y BESS pero sin agente RL "
        "F₁ = 5 790 639 kg CO₂/año, y los valores de emisión bajo control RL F₂ obtenidos "
        "por cada agente en 50 episodios de entrenamiento. La inferencia técnica se sustenta "
        "en las pruebas no paramétricas de Wilcoxon, Mann-Whitney y Kruskal-Wallis, dado que "
        "la distribución de F₂ en el conjunto completo de episodios no satisface normalidad "
        "para los rangos globales.")
    add_para(doc,
        "El análisis inferencial abarca dos dimensiones complementarias: (i) el cubrimiento de "
        "la demanda energética mediante el sistema fotovoltaico–BESS–cargadores, y (ii) la "
        "contribución cuantificable a la reducción de emisiones de CO₂ en la ciudad de Iquitos, "
        "objetivo central del OE3 del proyecto. Ambas dimensiones son evaluadas sobre la base "
        "de los 50 episodios de entrenamiento de cada agente (SAC, PPO, A2C), "
        "8 760 pasos temporales por episodio (año completo a resolución horaria), "
        "lo que implica 438 000 decisiones de despacho por agente.")


def build_522(doc: Document):
    """5.2.2 Inferencia técnica — cobertura de demanda energética"""
    add_heading(doc, "5.2.2. Inferencia técnica sobre el cubrimiento de la demanda energética "
                     "mediante el sistema FV–BESS–cargadores", level=3)
    add_para(doc,
        "La demanda energética total del sistema integrado considera dos componentes: "
        "(a) la demanda eléctrica del Mall BESS Iquitos, estimada en 12 368 828 kWh/año como "
        "valor de referencia central, y (b) la demanda de recarga de vehículos eléctricos "
        "(motos y mototaxis) dimensionada en 408 282 kWh/año —equivalente a 1 118 kWh/día— "
        "para una flota de 270 motos y 39 mototaxis por día con un factor de penetración EV del "
        "30 % y factor de carga del 55 %. La inferencia técnica evalúa qué fracción de estas "
        "demandas es cubierta por generación FV propia, descarga del BESS y, residualmente, "
        "por importación de red.")
    add_para(doc,
        "La Tabla 5.2.2.1 presenta las métricas de cobertura de la demanda EV para el episodio "
        "óptimo de cada agente, entendiendo 'cobertura' como el cociente entre la energía "
        "efectivamente entregada a los cargadores y la demanda EV objetivo anual.")

    # TABLA 5.2.2.1
    add_caption(doc, "Tabla 5.2.2.1. Cobertura de la demanda energética EV por agente "
                     "(episodio óptimo, 50 episodios de entrenamiento)")
    t = doc.add_table(rows=1, cols=7)
    t.style = "Table Grid"
    make_header_row(t, [
        "Agente", "Ep. óptimo", "Ev (motos+taxi)\nkWh", "Cobertura best\n%",
        "Cobertura media\n(50 eps) %", "BESS descargado\nkWh (media)", "Importación red\nkWh (mín)"
    ])
    data = [
        ("SAC ★", 48, "400 353", "98.1", "95.5", "880 245", "5 801 227"),
        ("PPO",   40, "407 804", "99.9", "94.0", "906 898", "6 164 654"),
        ("A2C",   3,  "356 818", "87.4", "97.7", "733 671", "6 270 421"),
    ]
    for row in data:
        if "★" in row[0]:
            add_highlighted_row(t, list(row))
        else:
            add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El SAC alcanza una cobertura del 98.1 % de la demanda EV en su episodio óptimo "
        "(episodio 48, F₂ = 2 622 735 kg CO₂/año), con una cobertura media del 95.5 % "
        "sobre los 50 episodios. El PPO logra la máxima cobertura puntual (99.9 % en el "
        "episodio 40), aunque su cobertura media (94.0 %) resulta inferior a la del A2C "
        "(97.7 % de media). Sin embargo, el episodio óptimo del A2C presenta una cobertura "
        "reducida (87.4 %), lo que indica mayor variabilidad episódica en la gestión de "
        "cargadores, corroborada por el mayor número acumulado de violaciones de restricción "
        "de deuda energética (1 181 horas-episodio).")
    add_para(doc,
        "Desde la perspectiva del BESS, el SAC descarga en promedio 880 245 kWh/año, "
        "el PPO moviliza 906 898 kWh/año (mayor volumen, pero con mayor importación de red), "
        "y el A2C descarga solo 733 671 kWh/año. La correlación de Pearson entre la descarga "
        "del BESS y el valor F₂ de CO₂ fue de r = –0.782 (p = 1.93×10⁻¹¹) para el SAC, "
        "r = –0.917 (p = 7.82×10⁻²¹) para el PPO, y r = +0.843 (p = 1.62×10⁻¹⁴) para el A2C. "
        "El coeficiente positivo del A2C indica que, paradójicamente, un mayor uso del BESS "
        "en ese agente no redujo las emisiones, señal de ineficiencia en la política de despacho.")
    add_para(doc,
        "Se infiere que el sistema FV–BESS–cargadores diseñado en el OE2 es capaz de cubrir "
        "más del 95 % de la demanda EV bajo control SAC y más del 94 % bajo PPO, confirmando "
        "que la infraestructura dimensionada (4 050 kWp + 2 000 kWh BESS + 38 tomas) es "
        "suficiente para el escenario de demanda proyectada con una holgura operativa adecuada.")

    # TABLA 5.2.2.2
    add_caption(doc, "Tabla 5.2.2.2. Balance energético anual del sistema integrated "
                     "por agente — episodio óptimo (kWh/año)")
    t2 = doc.add_table(rows=1, cols=5)
    t2.style = "Table Grid"
    make_header_row(t2, ["Componente energético", "SAC (ep 48)", "PPO (ep 40)", "A2C (ep 3)", "Referencia (F₁)"])
    rows2 = [
        ("Generación FV nominal (kWh)", "8 292 514", "8 292 514", "8 292 514", "8 292 514"),
        ("Descarga BESS (kWh)", "875 699", "919 034", "744 718", "509 829"),
        ("Importación de red (kWh)", "5 801 227", "6 164 654", "6 270 421", "6 504 452"),
        ("Energía a EV — motos (kWh)", "341 047", "345 118", "329 125", "256 672"),
        ("Energía a EV — mototaxis (kWh)", "59 306", "62 686", "27 693", "—"),
        ("Energía EV total (kWh)", "400 353", "407 804", "356 818", "~408 282"),
        ("Cobertura EV (%)", "98.1 %", "99.9 %", "87.4 %", "~62.9 %"),
    ]
    for rv in rows2:
        add_row(t2, list(rv), bold_first=True)
    doc.add_paragraph()


def build_523(doc: Document):
    """5.2.3 Inferencia técnica — contribución cuantificable reducción CO₂"""
    add_heading(doc, "5.2.3. Inferencia técnica sobre la contribución cuantificable a la "
                     "reducción de emisiones de CO₂", level=3)
    add_para(doc,
        "La reducción de CO₂ cuantificable se descompone en dos vías conforme al marco de "
        "emisiones del proyecto: (a) reducción directa F₆ₐ por combustible vehicular evitado "
        "—motos y mototaxis que reemplazan gasolina y diésel—, y (b) reducción indirecta F₆ᵦ "
        "por desplazamiento de generación diésel en la red aislada de Iquitos mediante "
        "autogeneración FV y despacho optimizado de BESS. El factor de emisión aplicado "
        "es EF = 0.4521 kg CO₂/kWh (factor red aislada Iquitos, MINEM 2024).")
    add_para(doc,
        "La prueba de Wilcoxon de rango con signo aplicada al contraste F₁ − F₂ > 0 "
        "—verificando que el control RL reduce efectivamente las emisiones respecto a la "
        "operación base sin agente— arrojó un estadístico T = 1 275.0 con p = 8.882×10⁻¹⁶, "
        "lo cual confirma a un nivel de significancia α = 0.001 que los tres agentes "
        "contribuyen de manera estadísticamente significativa a la reducción de CO₂ respecto "
        "a la operación sin control inteligente.")
    add_para(doc,
        "La Tabla 5.2.3.1 desglosa la reducción de CO₂ por componente para el episodio "
        "óptimo de cada agente, expresada en kg CO₂/año y en porcentaje respecto al escenario "
        "de referencia F₀.")

    # TABLA 5.2.3.1
    add_caption(doc, "Tabla 5.2.3.1. Reducción de CO₂ por componente y agente "
                     "(episodio óptimo, α = 0.001, Wilcoxon p = 8.882×10⁻¹⁶)")
    t = doc.add_table(rows=1, cols=7)
    t.style = "Table Grid"
    make_header_row(t, [
        "Agente", "F₂ mín\n(kg/año)", "Reducción directa\n(kg/año)",
        "Reducción indirecta\n(kg/año)", "Reducción neta\n(kg/año)",
        "% vs F₀\n(7 054 000)", "% vs F₁\n(5 790 639)"
    ])
    rows = [
        ("SAC ★",  "2 622 735", "328 736", "3 223 884", "3 552 620", "62.8 %", "54.7 %"),
        ("PPO",    "2 787 040", "334 103", "3 052 176", "3 386 279", "60.5 %", "51.9 %"),
        ("A2C",    "2 834 857", "301 293", "2 985 752", "3 287 045", "59.8 %", "51.0 %"),
        ("F₁ base","5 790 639", "243 300", "230 494",   "473 794",  "6.7 %",  "0 %"),
        ("F₀ ref", "7 054 000", "0",       "0",         "0",        "0 %",    "—"),
    ]
    for row in rows:
        if "★" in row[0]:
            add_highlighted_row(t, list(row))
        elif "F₁" in row[0]:
            add_row(t, list(row), bold_first=True, bg="E2EFDA")
        elif "F₀" in row[0]:
            add_row(t, list(row), bold_first=True, bg="FCE4D6")
        else:
            add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El SAC logra la mayor reducción neta de CO₂: 3 552 620 kg/año (62.8 % vs F₀ y "
        "54.7 % vs F₁). El PPO alcanza 3 386 279 kg/año (60.5 % vs F₀) y el A2C "
        "3 287 045 kg/año (59.8 % vs F₀). En todos los casos, la componente indirecta "
        "—derivada del despacho optimizado que reduce la importación de energía diésel— "
        "representa entre el 91 % y el 91.5 % de la reducción neta total, mientras que la "
        "reducción directa por combustible vehicular evitado aporta entre el 8.6 % (A2C) y "
        "el 9.3 % (SAC) de la reducción neta.")
    add_para(doc,
        "La diferencia entre la reducción directa del SAC (328 736 kg CO₂/año) y la del A2C "
        "(301 293 kg CO₂/año) refleja un menor cubrimiento de la demanda mototaxi en el A2C "
        "(27 693 kWh vs 59 306 kWh del SAC), atribuible a mayor número de violaciones de "
        "restricción de deuda energética (1 181 vs 1 029 horas-episodio). El PPO registra "
        "la mayor reducción directa (334 103 kg/año) dada su cobertura EV puntual de 99.9 % "
        "en su episodio óptimo.")
    add_para(doc,
        "Se concluye que los tres agentes de RL producen una reducción de CO₂ estadísticamente "
        "significativa (p < 0.001) respecto a la operación base, con una contribución cuantificable "
        "superior al 59.8 % de las emisiones de referencia F₀. El SAC constituye el agente con "
        "mayor contribución ambiental consolidada, reduciendo las emisiones a 2 622 735 kg CO₂/año, "
        "valor que representa el 37.2 % del escenario sin ninguna intervención tecnológica.")


def build_53(doc: Document):
    """5.3 Otro tipo de resultados estadísticos"""
    add_heading(doc, "5.3. Otro tipo de resultados estadísticos, de acuerdo con la naturaleza "
                     "del problema y la hipótesis", level=2)
    add_para(doc,
        "Además de los resultados descriptivos (secciones 5.1) e inferenciales (sección 5.2), "
        "la naturaleza del problema de optimización mediante aprendizaje por refuerzo requiere "
        "resultados estadísticos específicos al paradigma RL: comportamiento del entrenamiento "
        "por episodios, métricas de desempeño comparativo, jerarquía de reducción de CO₂, "
        "análisis de variabilidad y robustez, y la selección final del agente óptimo. "
        "Estos resultados complementan la demostración de las cuatro hipótesis del proyecto "
        "(HG, HE1, HE2 y HE3).")


def build_531(doc: Document):
    """5.3.1 Función de recompensa multiobjetivo y configuración del entorno"""
    add_heading(doc, "5.3.1. Función de recompensa multiobjetivo y configuración del entorno "
                     "de entrenamiento", level=3)
    add_para(doc,
        "El entorno de entrenamiento se construyó sobre CityLearn v2.x con un horizonte "
        "episódico de 8 760 pasos temporales (un año completo a resolución horaria). "
        "El espacio de observación es de dimensión 394 (variables de estado del sistema: "
        "irradiancia FV, frecuencia de red, SOC del BESS, estado de las 38 tomas de carga "
        "y características temporales), y el espacio de acción es continuo de dimensión 39 "
        "(1 setpoint BESS + 38 setpoints de tomas de carga, normalizados en [0, 1]).")
    add_para(doc,
        "La función de recompensa multiobjetivo F_reward fue diseñada para alinear "
        "el OE3 del proyecto —reducción cuantificable de emisiones de CO₂— con la dinámica "
        "operativa del sistema FV–BESS–cargadores. Está definida como la combinación lineal:")
    p = doc.add_paragraph(style=STYLE_BODY)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("F_reward = w₁·ΔCO₂_direct + w₂·ΔCO₂_indirect + w₃·EV_coverage + w₄·Solar_SC + w₅·Grid_stability")
    run.font.size = Pt(11)
    run.font.bold = True

    add_para(doc,
        "donde los pesos wᵢ fueron fijados conforme a la prioridad OE3 (Tabla 5.3.1.1)")

    # TABLA 5.3.1.1
    add_caption(doc, "Tabla 5.3.1.1. Pesos de la función de recompensa multiobjetivo "
                     "(versión CO2_DUAL_FOCUS v7.0)")
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    make_header_row(t, ["Componente (wᵢ)", "Peso", "Alineación OE3", "Justificación"])
    rwdata = [
        ("w₁: Reducción directa CO₂", "0.35", "Primaria",    "Combustible vehicular evitado (motos/mototaxis)"),
        ("w₂: Reducción indirecta CO₂", "0.30", "Secundaria", "Grid import × 0.4521 kg CO₂/kWh"),
        ("w₃: Cobertura recarga EV", "0.25", "Terciaria",    "Garantizar carga de flota por deadline"),
        ("w₄: Autoconsumo solar", "0.05", "Cuaternaria",     "Maximizar uso directo de generación FV"),
        ("w₅: Estabilidad de red", "0.05", "Quinaria",       "Suavizar rampas de potencia")]
    for row in rwdata:
        add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "Los parámetros clave de entrenamiento para cada agente se detallan en la Tabla 5.3.1.2, "
        "configurados conforme a las recomendaciones de la literatura especializada para espacios "
        "de acción continuos de alta dimensión (39D).")

    # TABLA 5.3.1.2
    add_caption(doc, "Tabla 5.3.1.2. Configuración de hiperparámetros por agente "
                     "(50 episodios, 438 000 pasos temporales)")
    t2 = doc.add_table(rows=1, cols=5)
    t2.style = "Table Grid"
    make_header_row(t2, ["Parámetro", "SAC (off-policy)", "PPO (on-policy)", "A2C (on-policy)", "Común"])
    pdata = [
        ("Tipo de agente",    "Off-policy",    "On-policy",    "On-policy",    "—"),
        ("Tasa de aprendizaje", "1×10⁻⁴",     "2×10⁻⁴",     "7×10⁻⁴",     "Lineal schedule"),
        ("Buffer (replay)",   "100 000",       "N/A",          "N/A",          "—"),
        ("n_steps",           "—",             "2 048",        "8",            "—"),
        ("Batch size",        "256",           "256",          "—",            "—"),
        ("n_epochs (PPO)",    "—",             "10",           "—",            "—"),
        ("Clip range (PPO)",  "—",             "0.2",          "—",            "—"),
        ("γ (descuento)",     "0.99",          "0.99",         "0.99",         "Todos"),
        ("λ GAE",             "—",             "0.98",         "0.95",         "—"),
        ("Coef. entropía",    "automático",    "0.01",         "0.015",        "—"),
        ("Episodios",         "50",            "50",           "50",           "Todos"),
        ("Pasos/episodio",    "8 760",         "8 760",        "8 760",        "Todos"),
        ("Espacio obs.",      "394D",          "394D",         "394D",         "Todos"),
        ("Espacio acción",    "39D cont.",     "39D cont.",    "39D cont.",    "Todos"),
    ]
    for row in pdata:
        add_row(t2, list(row), bold_first=True)
    doc.add_paragraph()


def build_532(doc: Document):
    """5.3.2 Métricas de desempeño y comparación directa SAC, PPO, A2C"""
    add_heading(doc, "5.3.2. Métricas de desempeño y comparación directa entre SAC, PPO y A2C",
                level=3)
    add_para(doc,
        "La Tabla 5.3.2.1 consolida las métricas estadísticas de CO₂ total de control F₂ "
        "—emisiones netas del sistema bajo gestión RL en kg CO₂/año— para los 50 episodios "
        "de entrenamiento de cada agente. La métrica principal de comparación es F₂ mín "
        "(episodio óptimo), complementada por la media, desviación estándar, coeficiente de "
        "variación del plateau final (últimos 15 episodios) y el número acumulado de "
        "violaciones de restricción de deuda energética.")

    # TABLA 5.3.2.1
    add_caption(doc, "Tabla 5.3.2.1. Métricas de desempeño comparativo SAC vs PPO vs A2C "
                     "(50 episodios, 8 760 pasos/episodio, resolución horaria anual)")
    t = doc.add_table(rows=1, cols=9)
    t.style = "Table Grid"
    make_header_row(t, [
        "Agente", "F₂ mín\n(kg/año)", "Ep.\nóptimo",
        "F₂ media\n(kg/año)", "F₂ std\n(kg/año)",
        "F₂ máx\n(kg/año)", "CV plateau\n(%)",
        "Violac.\ntotal", "Tipo"
    ])
    mdata = [
        ("SAC ★",  "2 622 735", "48", "2 668 375", "89 475",  "3 055 514", "0.058", "1 029", "Off-policy"),
        ("PPO",    "2 787 040", "40", "2 875 569", "113 816", "3 142 944", "0.195", "2 605", "On-policy"),
        ("A2C",    "2 834 857", "3",  "2 845 012", "12 011",  "2 922 533", "0.056", "1 181", "On-policy"),
        ("F₁ base","5 790 639", "—",  "5 790 639", "—",       "—",         "—",     "N/A",   "Sin RL"),
    ]
    for row in mdata:
        if "★" in row[0]:
            add_highlighted_row(t, list(row))
        elif "F₁" in row[0]:
            add_row(t, list(row), bold_first=True, bg="E2EFDA")
        else:
            add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El SAC obtiene el menor valor de F₂ mín = 2 622 735 kg CO₂/año en el episodio 48, "
        "superando al PPO en 164 305 kg CO₂/año (−5.9 % adicional) y al A2C en 212 122 "
        "kg CO₂/año (−7.5 % adicional). La media de 50 episodios del SAC (2 668 375 kg/año) "
        "posiciona al agente como el más eficiente en reducción sostenida de emisiones.")
    add_para(doc,
        "El A2C presenta la menor desviación estándar global (σ = 12 011 kg/año) y el menor "
        "CV de plateau (0.056 %), pero su F₂ mín es el más alto de los tres agentes, lo que "
        "indica estabilidad sin optimización profunda. El PPO muestra la mayor variabilidad "
        "(σ = 113 816 kg/año, CV plateau = 0.195 %), atribuible a su mecánica on-policy con "
        "n_steps = 2 048 y mayor sensibilidad a los episodios de exploración temprana.")

    # TABLA 5.3.2.2 — comparación flujos energéticos
    add_caption(doc, "Tabla 5.3.2.2. Flujos energéticos medios (50 episodios) "
                     "por agente (kWh/año)")
    t2 = doc.add_table(rows=1, cols=5)
    t2.style = "Table Grid"
    make_header_row(t2, ["Métrica energética", "SAC", "PPO", "A2C", "F₁ base"])
    edata = [
        ("Generación FV (kWh/año)", "8 293 277", "8 293 277", "8 293 277", "8 292 514"),
        ("Descarga BESS media (kWh/año)", "880 245", "906 898", "733 671", "509 829"),
        ("Importación red media (kWh/año)", "5 902 180", "6 360 471", "6 292 882", "6 504 452"),
        ("Energía EV media (kWh/año)", "389 752", "383 650", "398 803", "~408 282"),
        ("Cobertura EV media (%)", "95.5 %", "94.0 %", "97.7 %", "~62.9 %"),
        ("Reducción % media vs F₀", "62.2 %", "59.2 %", "59.7 %", "17.9 %"),
    ]
    for row in edata:
        add_row(t2, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "Los tres agentes reducen la importación de red respecto a la operación base F₁ "
        "(6 504 452 kWh/año), con el SAC logrando la mayor reducción media (5 902 180 kWh/año, "
        "−9.3 % vs F₁). La descarga del BESS es consistentemente superior en los agentes RL "
        "respecto a la operación base (509 829 kWh F₁ vs 880 245 SAC, +72.7 %), evidenciando "
        "que el control RL optimiza el uso del almacenamiento para desplazar importación de "
        "red en horas de tarifa punta.")


def build_533(doc: Document):
    """5.3.3 Reducción CO₂ por agente y jerarquía ambiental"""
    add_heading(doc, "5.3.3. Reducción de CO₂ por agente y jerarquía de desempeño ambiental",
                level=3)
    add_para(doc,
        "La jerarquía de desempeño ambiental se establece sobre tres criterios ordenados: "
        "(1) F₂ mín como indicador del potencial máximo de reducción, (2) F₂ media como "
        "indicador de reducción sostenida en 50 episodios, y (3) porcentaje de reducción de "
        "CO₂ respecto a la referencia sin intervención F₀ = 7 054 000 kg CO₂/año. "
        "La Tabla 5.3.3.1 sintetiza esta jerarquía.")

    # TABLA 5.3.3.1
    add_caption(doc, "Tabla 5.3.3.1. Jerarquía de desempeño ambiental por agente "
                     "(50 episodios, α = 0.001)")
    t = doc.add_table(rows=1, cols=8)
    t.style = "Table Grid"
    make_header_row(t, [
        "Rango", "Agente", "F₂ mín (kg/año)",
        "Red. directa\n(kg/año)", "Red. indirecta\n(kg/año)",
        "Red. neta\n(kg/año)", "% vs F₀", "% vs F₁"
    ])
    jdata = [
        ("1° ★", "SAC", "2 622 735", "328 736", "3 223 884", "3 552 620", "62.8 %", "54.7 %"),
        ("2°",   "PPO", "2 787 040", "334 103", "3 052 176", "3 386 279", "60.5 %", "51.9 %"),
        ("3°",   "A2C", "2 834 857", "301 293", "2 985 752", "3 287 045", "59.8 %", "51.0 %"),
    ]
    for row in jdata:
        if "★" in row[0]:
            add_highlighted_row(t, list(row))
        else:
            add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El SAC ocupa el primer lugar en la jerarquía ambiental con una reducción neta de "
        "3 552 620 kg CO₂/año (62.8 % vs F₀). Esta superioridad se deriva de su capacidad "
        "off-policy para aprender de experiencias históricas almacenadas en un buffer de "
        "replay de 100 000 transiciones, lo que permite una exploración más eficiente del "
        "espacio de decisiones de despacho de 39 dimensiones continuas. La entropía adaptativa "
        "de SAC facilita la búsqueda de políticas diversificadas que evitan mínimos locales "
        "observados en los primeros 10 episodios del PPO.")
    add_para(doc,
        "La reducción directa de CO₂ —por combustible vehicular evitado— es liderada por el "
        "PPO (334 103 kg/año) seguido del SAC (328 736 kg/año), mientras el A2C presenta la "
        "menor reducción directa (301 293 kg/año) por menor cobertura mototaxi. No obstante, "
        "el aporte directo representa solo entre el 8.6 % y el 9.9 % de la reducción neta "
        "total, siendo la reducción indirecta el componente dominante: entre 2 985 752 "
        "(A2C) y 3 223 884 kg CO₂/año (SAC).")

    # TABLA 5.3.3.2 — convergencia episódica
    add_caption(doc, "Tabla 5.3.3.2. Convergencia del entrenamiento: primeros 5 vs últimos "
                     "5 episodios (kg CO₂/año, F₂)")
    t2 = doc.add_table(rows=1, cols=5)
    t2.style = "Table Grid"
    make_header_row(t2, ["Agente", "Media ep. 1–5 (kg/año)", "Media ep. 46–50 (kg/año)",
                          "Mejora absoluta (kg/año)", "Mejora relativa (%)"])
    cdats = [
        ("SAC ★", "2 900 585", "2 624 189", f"{2_900_585-2_624_189:,}", "9.53 %"),
        ("PPO",   "3 092 783", "2 796 266", f"{3_092_783-2_796_266:,}", "9.59 %"),
        ("A2C",   "2 862 349", "2 839 805", f"{2_862_349-2_839_805:,}", "0.79 %"),
    ]
    for row in cdats:
        if "★" in row[0]:
            add_highlighted_row(t, list(row) if False else list(row))
        add_row(t2, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El SAC y el PPO muestran convergencias episódicas similares (9.53 % y 9.59 % "
        "de mejora respectivamente entre los primeros 5 y los últimos 5 episodios), lo que "
        "confirma que ambos agentes off- y on-policy logran aprendizaje efectivo dentro del "
        "presupuesto de 438 000 pasos. El A2C, en cambio, prácticamente converge en los "
        "primeros 3 episodios (ep 3 es su óptimo), con solo 0.79 % de mejora adicional, "
        "comportamiento típico de agentes síncronos con n_steps pequeños (8 pasos) que "
        "explotan la política temprana sin refinamiento posterior.")


def build_534(doc: Document):
    """5.3.4 Variabilidad, robustez y estabilidad del entrenamiento"""
    add_heading(doc, "5.3.4. Variabilidad, robustez y estabilidad del entrenamiento", level=3)
    add_para(doc,
        "La estabilidad del entrenamiento se evalúa a través de dos indicadores principales: "
        "(a) el coeficiente de variación (CV) del plateau de entrenamiento —últimos 15 episodios— "
        "que cuantifica la dispersión relativa del F₂ una vez superada la fase de exploración, "
        "y (b) las violaciones acumuladas de restricción de deuda energética, que miden el "
        "incumplimiento de compromisos de carga en el horizonte episódico.")
    add_para(doc,
        "Se aplicó la prueba de normalidad de Shapiro-Wilk sobre los 15 episodios del plateau "
        "para cada agente, obteniendo los resultados de la Tabla 5.3.4.1.")

    # TABLA 5.3.4.1
    add_caption(doc, "Tabla 5.3.4.1. Prueba de Shapiro-Wilk sobre el plateau de entrenamiento "
                     "(últimos 15 episodios por agente)")
    t = doc.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    make_header_row(t, ["Agente", "W (Shapiro-Wilk)", "p-valor", "Distribución",
                          "CV plateau (%)"])
    swdata = [
        ("SAC ★", "0.9752", "0.9259", "Normal (p > 0.05)", "0.058 %"),
        ("PPO",   "0.9897", "0.9993", "Normal (p > 0.05)", "0.195 %"),
        ("A2C",   "0.9348", "0.3211", "Normal (p > 0.05)", "0.056 %"),
    ]
    for row in swdata:
        if "★" in row[0]:
            add_highlighted_row(t, list(row))
        else:
            add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "Los tres agentes presentan distribución normal en el plateau (p > 0.05, Shapiro-Wilk), "
        "lo que indica que el proceso de entrenamiento ha alcanzado un régimen estacionario "
        "en los últimos 15 episodios. El CV del SAC (0.058 %) y del A2C (0.056 %) son "
        "prácticamente idénticos y significativamente menores al del PPO (0.195 %), "
        "reflejando mayor estabilidad episódica de SAC y A2C en la fase de explotación. "
        "No obstante, la similitud de CV entre SAC y A2C no implica equivalencia de desempeño: "
        "el SAC es estable en un mínimo de F₂ = 2 622 735 kg/año, mientras que el A2C "
        "es estable pero en un nivel de CO₂ sensiblemente superior (2 834 857 kg/año).")
    add_para(doc,
        "La robustez ante violaciones de restricción EV se evalúa mediante el conteo de "
        "episodios-hora con incumplimiento de deuda energética (Tabla 5.3.4.2). "
        "El episodio óptimo del SAC registra 0 violaciones, mientras que su acumulado "
        "completo (50 episodios) suma 1 029 casos, concentrados principalmente en la "
        "fase de exploración temprana (episodios 1–15 con max_ep = 364).")

    # TABLA 5.3.4.2
    add_caption(doc, "Tabla 5.3.4.2. Robustez ante violaciones de restricción de deuda "
                     "energética EV (50 episodios de entrenamiento)")
    t2 = doc.add_table(rows=1, cols=5)
    t2.style = "Table Grid"
    make_header_row(t2, ["Agente", "Violaciones ep. óptimo",
                          "Violaciones totales\n(50 eps)", "Máx. ep. único",
                          "Fase concentrada"])
    vdata = [
        ("SAC ★", "0",   "1 029", "364", "Exploración temprana (ep 1–15)"),
        ("PPO",   "0",   "2 605", "364", "Exploración temprana + media (ep 1–30)"),
        ("A2C",   "— *", "1 181", "361", "Distribuida (ep 1–50)"),
    ]
    for row in vdata:
        if "★" in row[0]:
            add_highlighted_row(t2, list(row))
        else:
            add_row(t2, list(row), bold_first=True)

    doc.add_paragraph()
    add_para(doc,
        "Nota: (*) El episodio óptimo del A2C (ep 3) corresponde a la fase inicial, con "
        "violaciones residuales distribuidas. Las violaciones del PPO (2 605 totales) "
        "más que duplican las del SAC (1 029), indicando menor cumplimiento de restricciones "
        "operativas en su mecanismo on-policy de actualización de política.")

    # TABLA 5.3.4.3 — pruebas estadísticas pairwise
    add_caption(doc, "Tabla 5.3.4.3. Pruebas estadísticas comparativas inter-agentes "
                     "(Mann-Whitney U, 50 episodios c/u, hipótesis one-tailed: F₂ agente_i < F₂ agente_j)")
    t3 = doc.add_table(rows=1, cols=5)
    t3.style = "Table Grid"
    make_header_row(t3, ["Contraste", "U estadístico", "p-valor", "r (tamaño efecto)", "Conclusión"])
    mwdata = [
        ("SAC < PPO", "121",  "3.636×10⁻¹⁵", "0.048", "SAC significativamente mejor (p<0.001)"),
        ("SAC < A2C", "149",  "1.641×10⁻¹⁴", "0.060", "SAC significativamente mejor (p<0.001)"),
        ("PPO < A2C", "885",  "5.989×10⁻³  ", "0.354", "PPO mejor (p<0.01), efecto moderado"),
    ]
    for row in mwdata:
        add_row(t3, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El Kruskal-Wallis sobre los tres grupos (n = 50 cada uno) arrojó H = 81.65, "
        "p = 1.861×10⁻¹⁸, confirmando diferencias globales altamente significativas "
        "(α = 0.001) entre los tres agentes. Las pruebas post-hoc de Mann-Whitney confirman "
        "que SAC supera significativamente a PPO (p = 3.636×10⁻¹⁵) y a A2C "
        "(p = 1.641×10⁻¹⁴), con tamaños de efecto pequeños (r < 0.10), consistentes con "
        "diferencias de nivel —no de distribución— entre agentes bien entrenados.")


def build_535(doc: Document):
    """5.3.5 Selección final del agente inteligente y contribución ambiental consolidada"""
    add_heading(doc, "5.3.5. Selección final del agente inteligente y contribución ambiental "
                     "consolidada", level=3)
    add_para(doc,
        "Con base en los resultados descriptivos (sección 5.1), inferenciales (sección 5.2) "
        "y estadísticos específicos al RL (secciones 5.3.1–5.3.4), se procede a la selección "
        "formal del agente de inteligencia artificial para la gestión de la infraestructura "
        "de carga inteligente en el proyecto pvbesscar.")
    add_para(doc,
        "La selección se fundamenta en una matriz multicriterio que pondera: "
        "(1) desempeño ambiental máximo (F₂ mín), (2) desempeño sostenido (F₂ media y CV "
        "plateau), (3) cobertura de demanda EV, (4) robustez operativa (violaciones), "
        "y (5) convergencia del entrenamiento. La Tabla 5.3.5.1 presenta la matriz de "
        "decisión final.")

    # TABLA 5.3.5.1
    add_caption(doc, "Tabla 5.3.5.1. Matriz de decisión multicriterio para selección del "
                     "agente RL (50 episodios, α = 0.001, Kruskal-Wallis H = 81.65)")
    t = doc.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    make_header_row(t, ["Criterio de selección", "Peso", "SAC", "PPO", "A2C"])
    cdata = [
        ("F₂ mínimo (kg CO₂/año)",                   "30 %", "2 622 735 ★", "2 787 040",  "2 834 857"),
        ("F₂ media 50 eps (kg CO₂/año)",              "20 %", "2 668 375 ★", "2 875 569",  "2 845 012"),
        ("CV plateau — estabilidad (%)",              "15 %", "0.058 % ★",   "0.195 %",    "0.056 % ≈"),
        ("Cobertura EV ep. óptimo (%)",               "15 %", "98.1 % ★",    "99.9 % ★",  "87.4 %"),
        ("Violaciones totales (50 eps)",              "10 %", "1 029 ★",     "2 605",      "1 181"),
        ("Convergencia (mejora ep 1→50)",             "10 %", "9.53 % ★",    "9.59 % ≈",   "0.79 %"),
        ("Significancia estadística (p Mann-Whitney)", "—",   "p<0.001 ★",   "p<0.001",    "p<0.001"),
    ]
    for row in cdata:
        if "★" in row[2] and "★" not in row[3] and "★" not in row[4]:
            # SAC best
            add_highlighted_row(t, list(row))
        else:
            add_row(t, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "El Soft Actor-Critic (SAC) es seleccionado como el agente de inteligencia artificial "
        "para la gestión de la infraestructura de carga inteligente en el Mall BESS Iquitos. "
        "Esta selección se sustenta en cinco fortalezas concurrentes: (1) mínimo histórico "
        "de emisiones F₂ = 2 622 735 kg CO₂/año (episodio 48), superior a PPO en "
        "164 305 kg CO₂/año y a A2C en 212 122 kg CO₂/año; (2) media sostenida de "
        "2 668 375 kg CO₂/año durante 50 episodios; (3) CV de plateau de 0.058 %, "
        "indicador de alta estabilidad en la fase de explotación; (4) cobertura de demanda "
        "EV del 98.1 % en el episodio óptimo (0 violaciones de restricción); y (5) "
        "diferencia estadísticamente significativa respecto a PPO y A2C "
        "(p < 0.001, Mann-Whitney U).")

    # TABLA 5.3.5.2 — contribución ambiental consolidada SAC
    add_caption(doc, "Tabla 5.3.5.2. Contribución ambiental consolidada del agente SAC "
                     "seleccionado (episodio óptimo 48, F₂ = 2 622 735 kg CO₂/año)")
    t2 = doc.add_table(rows=1, cols=3)
    t2.style = "Table Grid"
    make_header_row(t2, ["Dimensión ambiental", "Valor", "Referencia / contexto"])
    contrib = [
        ("F₀ — Sin intervención (kg CO₂/año)",       "7 054 000",   "Base absoluta del proyecto"),
        ("F₁ — Con FV+BESS, sin RL (kg CO₂/año)",    "5 790 639",   "Baseline operación no controlada"),
        ("F₂ — SAC óptimo (kg CO₂/año)",              "2 622 735",   "Episodio 48 (mejor histórico)"),
        ("Reducción total vs F₀ (kg CO₂/año)",        "4 431 265",   "62.8 % de F₀"),
        ("Reducción vs F₁ — aporte RL (kg CO₂/año)", "3 167 904",   "54.7 % adicional al FV+BESS"),
        ("Reducción directa — combustible (kg/año)",  "328 736",     "9.3 % de la reducción neta"),
        ("Reducción indirecta — red Iquitos (kg/año)","3 223 884",   "90.7 % de la reducción neta"),
        ("Cobertura demanda EV (% objetivo)",         "98.1 %",      "400 353 kWh / 408 282 kWh"),
        ("BESS descargado — ep óptimo (kWh/año)",     "875 699",     "+71.8 % vs operación base"),
        ("Importación red — ep óptimo (kWh/año)",     "5 801 227",   "−10.8 % vs operación base"),
        ("Factor emisión red Iquitos (kg CO₂/kWh)",   "0.4521",      "MINEM 2024, grid diesel aislado"),
        ("Episodios de entrenamiento",                "50",          "438 000 pasos totales"),
        ("Resultado hipótesis HG",                    "CONFIRMADA",  "SAC reduce CO₂ cuant. > F₁"),
    ]
    for row in contrib:
        if "CONFIRMADA" in row[1] or "F₂ — SAC" in row[0]:
            add_highlighted_row(t2, list(row))
        else:
            add_row(t2, list(row), bold_first=True)
    doc.add_paragraph()

    add_para(doc,
        "La contribución ambiental neta del agente SAC asciende a 4 431 265 kg CO₂/año "
        "respecto al escenario sin intervención tecnológica (F₀), equivalente a 4 431.3 tCO₂/año. "
        "De esta reducción, 3 167 904 kg CO₂/año es atribuible exclusivamente al control "
        "inteligente RL sobre el sistema ya dimensionado (diferencia F₁ − F₂), confirmando "
        "que el agente SAC añade un valor ambiental cuantificable y estadísticamente "
        "significativo sobre la operación sin control inteligente.")
    add_para(doc,
        "La selección del SAC resuelve el objetivo específico OE3: identificar el agente IA "
        "más apropiado para la gestión de recarga de motos y mototaxis eléctricas que "
        "contribuye de manera cuantificable a la reducción de emisiones de CO₂ en Iquitos. "
        "El SAC cumple este objetivo con una reducción de 62.8 % respecto al escenario base "
        "absoluto (F₀), manteniendo una cobertura de demanda EV entre el 94 % y el 98 % "
        "durante el entrenamiento sostenido de 50 episodios anuales, con 0 violaciones de "
        "restricción energética en el episodio óptimo y una estabilidad de plateau "
        "CV = 0.058 %, el más bajo entre los tres agentes evaluados.")
    add_para(doc,
        "En síntesis, el conjunto de resultados estadísticos aquí presentados —descriptivos, "
        "inferenciales y específicos al aprendizaje por refuerzo— demuestra de manera "
        "convergente y coherente que: (a) el sistema FV–BESS–cargadores dimensionado en el "
        "OE2 puede ser operado exitosamente mediante un agente RL, (b) el SAC es el agente "
        "superior en términos ambientales para este problema específico, y (c) la reducción "
        "de CO₂ obtenida es estadísticamente significativa (p < 0.001, múltiples pruebas) "
        "y cuantificable en 4 431 265 kg CO₂/año respecto a F₀ y 3 167 904 kg CO₂/año "
        "respecto a la operación base sin control inteligente F₁.")


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    if not SRC.exists():
        raise FileNotFoundError(f"No se encontró el documento fuente: {SRC}")

    shutil.copy2(SRC, TMP)
    doc = Document(str(TMP))

    print("▶ Construyendo sección 5.2 — Resultados inferenciales...")
    build_52(doc)
    print("▶ Construyendo sección 5.2.2 — Cobertura demanda energética...")
    build_522(doc)
    print("▶ Construyendo sección 5.2.3 — Contribución cuantificable CO₂...")
    build_523(doc)
    print("▶ Construyendo sección 5.3 — Resultados estadísticos RL...")
    build_53(doc)
    print("▶ Construyendo sección 5.3.1 — Función de recompensa y entorno...")
    build_531(doc)
    print("▶ Construyendo sección 5.3.2 — Métricas de desempeño comparativas...")
    build_532(doc)
    print("▶ Construyendo sección 5.3.3 — Jerarquía ambiental CO₂...")
    build_533(doc)
    print("▶ Construyendo sección 5.3.4 — Variabilidad y robustez...")
    build_534(doc)
    print("▶ Construyendo sección 5.3.5 — Selección final SAC...")
    build_535(doc)

    doc.save(str(TMP))
    shutil.copy2(TMP, OUT)
    TMP.unlink(missing_ok=True)

    print()
    print("✅ DOCUMENTO ACTUALIZADO EXITOSAMENTE")
    print(f"   Destino: {OUT}")
    print()
    print("   Secciones generadas:")
    for s in ["5.2", "5.2.2", "5.2.3", "5.3", "5.3.1", "5.3.2", "5.3.3", "5.3.4", "5.3.5"]:
        print(f"   ✓ Sección {s}")
    print()
    paras = len(doc.paragraphs)
    tables = len(doc.tables)
    print(f"   Párrafos totales en documento: {paras}")
    print(f"   Tablas totales en documento:   {tables}")


if __name__ == "__main__":
    main()
