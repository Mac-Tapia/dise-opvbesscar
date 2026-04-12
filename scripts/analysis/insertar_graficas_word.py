"""
Inserta todas las gráficas de entrenamiento, análisis comparativo y demostración
de hipótesis en el documento INFORME_OE3_SELECCION_AGENTE_RL_v10.docx → v11.

Organización:
  ANEXO A — Gráficas de Entrenamiento por Agente
    A.1  SAC — Soft Actor-Critic
    A.2  PPO — Proximal Policy Optimization
    A.3  A2C — Advantage Actor-Critic
  ANEXO B — Análisis Comparativo entre Agentes
  ANEXO C — Demostración de Hipótesis de Investigación

Uso:
    python scripts/analysis/insertar_graficas_word.py
"""

from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SRC  = Path("outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v10.docx")
DEST = Path("outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v11.docx")

IMG_W_FULL  = Inches(5.8)   # ancho figura de página completa
IMG_W_LARGE = Inches(5.2)   # ancho figura grande
IMG_W_MED   = Inches(4.8)   # ancho figura mediana

# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

def page_break(doc: Document) -> None:
    p = doc.add_paragraph()
    run = p.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    run._r.append(br)


def heading(doc: Document, text: str, level: int) -> None:
    doc.add_heading(text, level=level)


def caption(doc: Document, text: str) -> None:
    """Inserta un pie de figura en itálica centrado."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)


def body(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    p.style = doc.styles["Normal"]


def insert_fig(doc: Document, path: str | Path, cap: str,
               width: Inches = IMG_W_LARGE) -> bool:
    """Inserta imagen si existe; retorna True si fue insertada."""
    p = Path(path)
    if not p.exists():
        print(f"  [SKIP] No existe: {p}")
        return False
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    run.add_picture(str(p), width=width)
    caption(doc, cap)
    doc.add_paragraph()   # espacio entre figuras
    return True


def section_intro(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    p.style = doc.styles["Normal"]
    doc.add_paragraph()

# ---------------------------------------------------------------------------
# CONTENIDO AGENTE SAC
# ---------------------------------------------------------------------------
SAC_INTRO = (
    "El Soft Actor-Critic (SAC) es un algoritmo off-policy basado en maximización de entropía, "
    "entrenado durante 50 episodios completos (8,760 pasos cada uno = 438,000 pasos totales) "
    "sobre el entorno CityLearn v2. Las siguientes figuras muestran la evolución de las "
    "principales métricas de entrenamiento a lo largo de los 50 episodios, incluyendo la "
    "convergencia de la función de recompensa, el perfil de emisiones CO₂, el balance "
    "energético y las métricas de satisfacción de la flota EV."
)

SAC_FIGS = [
    ("outputs/sac_training/sac_co2_oe3_episodios.png",        IMG_W_FULL,
     "Figura A.1.1. SAC — Evolución de F₂ (CO₂ controlado, kg/año) a lo largo de 50 episodios. "
     "Episodio óptimo: ep 48, F₂ = 2,622,734 kg CO₂/año."),

    ("outputs/sac_training/sac_convergencia_recompensas.png",  IMG_W_FULL,
     "Figura A.1.2. SAC — Convergencia de la función de recompensa multiobjetivo R(t) por episodio. "
     "La curva muestra la mejora progresiva del agente en la optimización conjunta de CO₂ y EV."),

    ("outputs/sac_training/sac_balance_energetico_episodios.png", IMG_W_FULL,
     "Figura A.1.3. SAC — Balance energético por episodio: generación solar, descarga BESS, "
     "importación de red e importación residual. Evidencia el desplazamiento de red diésel."),

    ("outputs/sac_training/sac_ev_metricas_episodios.png",     IMG_W_FULL,
     "Figura A.1.4. SAC — Métricas de satisfacción de la flota EV por episodio: energía entregada "
     "a motos y mototaxis, y tasa de deuda energética incumplida (debt violations = 0 en ep 48)."),

    ("outputs/sac_training/sac_dashboard.png",                 IMG_W_FULL,
     "Figura A.1.5. SAC — Dashboard de entrenamiento consolidado: recompensa, CO₂, energía EV, "
     "solar, BESS y red, presentados en panel único para el episodio óptimo 48."),

    ("outputs/sac_training/sac_actor_loss.png",                IMG_W_MED,
     "Figura A.1.6. SAC — Pérdida del actor (actor loss) a lo largo del entrenamiento. "
     "Valores negativos indican aprendizaje activo de política dirigida a minimizar CO₂."),

    ("outputs/sac_training/sac_critic_loss.png",               IMG_W_MED,
     "Figura A.1.7. SAC — Pérdida del crítico (critic loss). Converge hacia valores bajos, "
     "indicando estimaciones estables del valor Q."),

    ("outputs/sac_training/sac_ent_coef.png",                  IMG_W_MED,
     "Figura A.1.8. SAC — Coeficiente de entropía α (temperatura), ajustado automáticamente. "
     "Su decrecimiento refleja la transición de exploración a explotación."),

    ("outputs/sac_training/sac_ent_coef_loss.png",             IMG_W_MED,
     "Figura A.1.9. SAC — Pérdida del coeficiente de entropía. Confirma la regulación "
     "automática del balance exploración-explotación durante el entrenamiento."),

    ("outputs/sac_training/kpi_dashboard.png",                 IMG_W_FULL,
     "Figura A.1.10. SAC — Dashboard de KPIs operativos: factor de carga, pico diario, "
     "ramping de red, emisiones CO₂, costo eléctrico y consumo total."),

    ("outputs/sac_training/kpi_carbon_emissions.png",          IMG_W_LARGE,
     "Figura A.1.11. SAC — KPI de emisiones de CO₂ por episodio: evolución de la reducción "
     "de Scope 2 lograda por el agente a lo largo del entrenamiento."),
]

# ---------------------------------------------------------------------------
# CONTENIDO AGENTE PPO
# ---------------------------------------------------------------------------
PPO_INTRO = (
    "El Proximal Policy Optimization (PPO) es un algoritmo on-policy con clipping de razón "
    "de probabilidad, que actualizó su política exclusivamente con trayectorias generadas "
    "en el episodio inmediatamente anterior. Fue entrenado durante 50 episodios (438,000 "
    "pasos totales) y alcanzó su óptimo en el episodio 40, con F₂ = 2,787,039 kg CO₂/año."
)

PPO_FIGS = [
    ("outputs/ppo_training/ppo_co2_oe3_episodios.png",          IMG_W_FULL,
     "Figura A.2.1. PPO — Evolución de F₂ (CO₂ controlado, kg/año) a lo largo de 50 episodios. "
     "Episodio óptimo: ep 40, F₂ = 2,787,039 kg CO₂/año."),

    ("outputs/ppo_training/ppo_convergencia_recompensas.png",    IMG_W_FULL,
     "Figura A.2.2. PPO — Convergencia de la función de recompensa multiobjetivo R(t) por episodio. "
     "El plateau es alcanzado entre ep 36–50 con CV = 0.1948 %."),

    ("outputs/ppo_training/ppo_balance_energetico_episodios.png", IMG_W_FULL,
     "Figura A.2.3. PPO — Balance energético por episodio: importación de red 6,164,653 kWh/año "
     "en ep 40, mayor que SAC (5,801,227 kWh) por la menor capacidad de despacho BESS."),

    ("outputs/ppo_training/ppo_ev_metricas_episodios.png",       IMG_W_FULL,
     "Figura A.2.4. PPO — Métricas de satisfacción de la flota EV por episodio. "
     "Cero violaciones de deuda energética en episodio óptimo 40."),

    ("outputs/ppo_training/ppo_dashboard.png",                   IMG_W_FULL,
     "Figura A.2.5. PPO — Dashboard de entrenamiento consolidado para el episodio óptimo 40."),

    ("outputs/ppo_training/ppo_value_metrics.png",               IMG_W_LARGE,
     "Figura A.2.6. PPO — Métricas de función de valor (value loss). "
     "Estabilidad mayor que A2C, lo que explica el segundo lugar en el ranking OE3."),

    ("outputs/ppo_training/ppo_entropy.png",                     IMG_W_MED,
     "Figura A.2.7. PPO — Entropía de política. Su decrecimiento confirma la convergencia "
     "hacia una política determinista de despacho solar+BESS."),

    ("outputs/ppo_training/ppo_clip_fraction.png",               IMG_W_MED,
     "Figura A.2.8. PPO — Fracción de clipping: porcentaje de actualizaciones limitadas por ε. "
     "Valores bajos indican actualizaciones conservadoras (sin saltos de política)."),

    ("outputs/ppo_training/ppo_kl_divergence.png",               IMG_W_MED,
     "Figura A.2.9. PPO — Divergencia KL entre política antigua y nueva. "
     "Confirma que el algoritmo mantiene el constraint proximal durante el entrenamiento."),

    ("outputs/ppo_training/kpi_dashboard.png",                   IMG_W_FULL,
     "Figura A.2.10. PPO — Dashboard de KPIs operativos: factor de carga, pico diario, "
     "ramping de red, emisiones CO₂, costo eléctrico y consumo total."),

    ("outputs/ppo_training/kpi_carbon_emissions.png",            IMG_W_LARGE,
     "Figura A.2.11. PPO — KPI de emisiones de CO₂ por episodio."),
]

# ---------------------------------------------------------------------------
# CONTENIDO AGENTE A2C
# ---------------------------------------------------------------------------
A2C_INTRO = (
    "El Advantage Actor-Critic (A2C) es el algoritmo sincrónico de la familia actor-crítico "
    "on-policy. Al no disponer de buffer de repetición de experiencias, su convergencia es "
    "más rápida al inicio pero más sensible a la varianza del gradiente. Fue entrenado "
    "durante 50 episodios (438,000 pasos totales) y alcanzó su óptimo en el episodio 3 "
    "(fase inicial de entrenamiento), con F₂ = 2,834,857 kg CO₂/año y 217 violaciones "
    "residuales de deuda energética EV."
)

A2C_FIGS = [
    ("outputs/a2c_training/a2c_co2_oe3_episodios.png",          IMG_W_FULL,
     "Figura A.3.1. A2C — Evolución de F₂ (CO₂ controlado, kg/año) a lo largo de 50 episodios. "
     "Episodio óptimo: ep 3, F₂ = 2,834,857 kg CO₂/año. La estabilidad posterior (σ=12,011 kg) "
     "indica convergencia rápida pero sin mejora adicional."),

    ("outputs/a2c_training/a2c_convergencia_recompensas.png",    IMG_W_FULL,
     "Figura A.3.2. A2C — Convergencia de la función de recompensa multiobjetivo R(t) por episodio. "
     "Plateau alcanzado desde ep 3, CV = 0.0562 % (el más bajo de los tres agentes)."),

    ("outputs/a2c_training/a2c_balance_energetico_episodios.png", IMG_W_FULL,
     "Figura A.3.3. A2C — Balance energético por episodio: importación de red 6,270,421 kWh/año "
     "en ep óptimo 3. Descarga BESS más baja (744,717 kWh vs SAC 875,698 kWh)."),

    ("outputs/a2c_training/a2c_ev_metricas_episodios.png",       IMG_W_FULL,
     "Figura A.3.4. A2C — Métricas de satisfacción de la flota EV. Se observan las 217 "
     "violaciones en el episodio óptimo 3, explicadas por la convergencia prematura."),

    ("outputs/a2c_training/a2c_dashboard.png",                   IMG_W_FULL,
     "Figura A.3.5. A2C — Dashboard de entrenamiento consolidado para el episodio óptimo 3."),

    ("outputs/a2c_training/a2c_policy_loss.png",                 IMG_W_MED,
     "Figura A.3.6. A2C — Pérdida de política (policy loss). Presenta mayor varianza que "
     "SAC/PPO, consistente con la ausencia de buffer de experiencias."),

    ("outputs/a2c_training/a2c_value_loss.png",                  IMG_W_MED,
     "Figura A.3.7. A2C — Pérdida de función de valor (value loss). Su no convergencia "
     "hacia cero explica el menor desempeño relativo frente a SAC y PPO."),

    ("outputs/a2c_training/a2c_entropy.png",                     IMG_W_MED,
     "Figura A.3.8. A2C — Entropía de política. La caída abrupta temprana confirma la "
     "convergencia prematura al episodio 3 sin exploración adicional posterior."),

    ("outputs/a2c_training/a2c_explained_variance.png",          IMG_W_MED,
     "Figura A.3.9. A2C — Varianza explicada por el crítico. "
     "Valores más bajos que PPO reflejan estimaciones del valor de estado menos precisas."),

    ("outputs/a2c_training/kpi_dashboard.png",                   IMG_W_FULL,
     "Figura A.3.10. A2C — Dashboard de KPIs operativos."),

    ("outputs/a2c_training/kpi_carbon_emissions.png",            IMG_W_LARGE,
     "Figura A.3.11. A2C — KPI de emisiones de CO₂ por episodio."),
]

# ---------------------------------------------------------------------------
# ANÁLISIS COMPARATIVO
# ---------------------------------------------------------------------------
COMP_INTRO = (
    "El análisis comparativo entre los tres agentes (SAC, PPO y A2C) permite identificar "
    "las diferencias en desempeño ambiental, estabilidad de convergencia, estrategia de "
    "despacho energético y satisfacción de la flota EV. Las siguientes figuras presentan "
    "la comparativa directa sobre los 50 episodios de entrenamiento."
)

COMP_FIGS = [
    ("outputs/comparative_analysis/training/convergence_all_agents.png", IMG_W_FULL,
     "Figura B.1. Convergencia de los tres agentes (SAC, PPO, A2C) — F₂ (kg CO₂/año) "
     "por episodio. SAC alcanza el mínimo absoluto en ep 48; A2C converge en ep 3; "
     "PPO mantiene descenso sostenido hasta ep 40."),

    ("outputs/comparative_analysis/training/variance_comparison.png",    IMG_W_FULL,
     "Figura B.2. Comparación de varianza entre agentes — distribución de F₂ en el "
     "plateau (ep 36–50). SAC: σ=89,475 kg; PPO: σ=113,816 kg; A2C: σ=12,011 kg. "
     "La baja varianza de A2C refleja estancamiento, no estabilidad de calidad."),

    ("outputs/comparative_analysis/training/statistical_justification_table.png", IMG_W_FULL,
     "Figura B.3. Tabla de justificación estadística de las diferencias entre agentes. "
     "Kruskal-Wallis H=81.65, p=1.86×10⁻¹⁸; Mann-Whitney SAC<PPO: U=121, r=0.90; "
     "SAC<A2C: U=149, r=0.88; PPO<A2C: U=885, r=0.29."),

    ("outputs/comparative_analysis/01_reward_comparison.png",           IMG_W_FULL,
     "Figura B.4. Comparativa de función de recompensa multiobjetivo R(t) — SAC vs PPO vs A2C. "
     "El SAC exhibe la mayor recompensa acumulada, consistente con su estrategia off-policy."),

    ("outputs/comparative_analysis/02_co2_comparison.png",              IMG_W_FULL,
     "Figura B.5. Comparativa directa de F₂ (CO₂ controlado, kg CO₂/año) entre los tres "
     "agentes. Diferencia SAC–PPO: 164,305 kg/año; SAC–A2C: 212,123 kg/año."),

    ("outputs/comparative_analysis/03_grid_comparison.png",             IMG_W_FULL,
     "Figura B.6. Comparativa de importación residual de red eléctrica (kWh/año) — "
     "SAC: 5,801,227 kWh; PPO: 6,164,653 kWh; A2C: 6,270,421 kWh. "
     "Menor importación SAC → menor Scope 2."),

    ("outputs/comparative_analysis/04_solar_utilization.png",           IMG_W_FULL,
     "Figura B.7. Comparativa de utilización solar (kWh/año) entre agentes. "
     "Los tres agentes aprovechan ~8,292–8,294 MWh/año de generación PV, "
     "evidenciando similar autoconsumo solar con diferente despacho BESS."),

    ("outputs/comparative_analysis/05_ev_charging_comparison.png",      IMG_W_FULL,
     "Figura B.8. Comparativa de energía entregada a la flota EV (kWh/año). "
     "SAC: 400,352 kWh; PPO: 407,803 kWh; A2C: 356,817 kWh. "
     "A2C entrega menos energía EV, explicando sus 217 violaciones de deuda."),

    ("outputs/comparative_analysis/06_performance_dashboard.png",       IMG_W_FULL,
     "Figura B.9. Dashboard de desempeño comparativo: panel consolidado de todas las "
     "métricas clave (CO₂, BESS, solar, red, EV, recompensa) para SAC, PPO y A2C."),

    ("outputs/comparative_analysis/07_oe3_baseline_comparison.png",     IMG_W_FULL,
     "Figura B.10. Comparativa de los tres agentes vs líneas base F₁ (sin RL) y F₀ "
     "(contrafactual ICE). Confirma que todos los agentes superan significativamente "
     "la baseline no controlada (Wilcoxon T=0, p=1.78×10⁻¹⁵)."),
]

# ---------------------------------------------------------------------------
# DEMOSTRACIÓN DE HIPÓTESIS
# ---------------------------------------------------------------------------
HIP_INTRO = (
    "La hipótesis de investigación del proyecto establece que la integración de un agente "
    "de aprendizaje por refuerzo profundo en la gestión del sistema PVBESSCAR produce una "
    "reducción cuantificable y estadísticamente significativa de las emisiones de CO₂ en "
    "la ciudad de Iquitos. Las siguientes figuras presentan la evidencia estadística que "
    "permite rechazar la hipótesis nula H₀ (F₂ ≥ F₁) y aceptar la hipótesis alternativa "
    "H₁ (F₂ < F₁), con α = 0.001."
)

HIP_FIGS = [
    ("outputs/seccion52/fig1_convergencia_agentes.png",             IMG_W_FULL,
     "Figura C.1. Curvas de convergencia de F₂ por agente (50 episodios). "
     "Evidencia la reducción progresiva de emisiones CO₂ con el aprendizaje RL. "
     "Base para el análisis inferencial sobre F₁ vs F₂."),

    ("outputs/seccion52/fig2_distribucion_normalidad.png",          IMG_W_FULL,
     "Figura C.2. Distribución de F₂ en el plateau (ep 36–50) con prueba de normalidad "
     "Shapiro-Wilk: SAC W=0.9752 (p=0.9259), PPO W=0.9897 (p=0.9993), "
     "A2C W=0.9348 (p=0.3211). Los tres grupos son normales en el plateau."),

    ("outputs/seccion52/fig3_varianza_robustez.png",                IMG_W_FULL,
     "Figura C.3. Análisis de varianza y robustez: boxplot de F₂ por agente "
     "en los 50 episodios. El Test de Kruskal-Wallis rechaza H₀ de igualdad "
     "con H=81.65, p=1.86×10⁻¹⁸ (α=0.001)."),

    ("outputs/seccion52/fig4_bess_grid_estrategia.png",             IMG_W_FULL,
     "Figura C.4. Estrategia de despacho BESS vs importación de red por agente. "
     "SAC: mayor descarga BESS (875,698 kWh) → menor importación red (5,801,227 kWh). "
     "Pearson r(BESS, CO₂) = −0.7824 para SAC confirma relación inversa significativa."),

    ("outputs/seccion52/fig4_co2_comparacion_mensual.png",          IMG_W_FULL,
     "Figura C.5. Comparación mensual de emisiones CO₂ entre F₁ (baseline) y F₂ "
     "(agente SAC óptimo ep 48). La reducción es consistente en todos los meses "
     "del año, confirmando que no es un artefacto estacional."),

    ("outputs/hypothesis_test/hypothesis_test_co2_figura_completa.png", IMG_W_FULL,
     "Figura C.6. Prueba de hipótesis completa: comparación estadística F₁ vs F₂ "
     "para los tres agentes. Wilcoxon signed-rank T=0, p=1.78×10⁻¹⁵ (one-tailed). "
     "RECHAZO de H₀ con α=0.001 para todos los agentes."),

    ("outputs/demostracion_hipotesis/fig_demostracion_hipotesis_completa.png", IMG_W_FULL,
     "Figura C.7. Demostración integrada de la hipótesis: panel con F₀, F₁, F₂ por agente, "
     "ΔCO₂ total evitado (4,431,266 kg CO₂/año con SAC), intervalos de confianza y "
     "árbol de decisión multicriterio OE3. Confirma el cumplimiento del OE3."),
]

# ---------------------------------------------------------------------------
# ENSAMBLADO PRINCIPAL
# ---------------------------------------------------------------------------

def main() -> None:
    doc = Document(str(SRC))
    total_before = len(doc.paragraphs)
    print(f"v10: {total_before} párrafos, {len(doc.tables)} tablas")

    fig_ok   = 0
    fig_skip = 0

    # ────────────────────────────────────────────────────────────────────────
    # PÁGINA DE INICIO DEL ANEXO
    # ────────────────────────────────────────────────────────────────────────
    page_break(doc)
    heading(doc, "ANEXO: Gráficas de Entrenamiento, Análisis Comparativo y Demostración de Hipótesis", level=1)
    body(doc, (
        "Este anexo reúne la totalidad de las gráficas generadas durante la fase de "
        "entrenamiento OE3, el análisis comparativo entre los tres agentes candidatos "
        "(SAC, PPO y A2C) y la demostración estadística de la hipótesis de investigación. "
        "Todas las figuras se obtuvieron de los datos reales de entrenamiento (50 episodios "
        "× 8,760 pasos por agente = 438,000 pasos totales) ejecutados entre el 11 y 12 de "
        "abril de 2026 sobre el entorno CityLearn v2 con la infraestructura PVBESSCAR de Iquitos, Perú."
    ))

    # ────────────────────────────────────────────────────────────────────────
    # ANEXO A — ENTRENAMIENTO POR AGENTE
    # ────────────────────────────────────────────────────────────────────────
    page_break(doc)
    heading(doc, "ANEXO A — Gráficas de Entrenamiento por Agente", level=1)

    # --- A.1 SAC ---
    heading(doc, "A.1. SAC — Soft Actor-Critic (agente ganador OE3)", level=2)
    section_intro(doc, SAC_INTRO)
    for path, width, cap_text in SAC_FIGS:
        ok = insert_fig(doc, path, cap_text, width)
        if ok: fig_ok += 1
        else:  fig_skip += 1

    # --- A.2 PPO ---
    page_break(doc)
    heading(doc, "A.2. PPO — Proximal Policy Optimization (segundo lugar OE3)", level=2)
    section_intro(doc, PPO_INTRO)
    for path, width, cap_text in PPO_FIGS:
        ok = insert_fig(doc, path, cap_text, width)
        if ok: fig_ok += 1
        else:  fig_skip += 1

    # --- A.3 A2C ---
    page_break(doc)
    heading(doc, "A.3. A2C — Advantage Actor-Critic (tercer lugar OE3)", level=2)
    section_intro(doc, A2C_INTRO)
    for path, width, cap_text in A2C_FIGS:
        ok = insert_fig(doc, path, cap_text, width)
        if ok: fig_ok += 1
        else:  fig_skip += 1

    # ────────────────────────────────────────────────────────────────────────
    # ANEXO B — ANÁLISIS COMPARATIVO
    # ────────────────────────────────────────────────────────────────────────
    page_break(doc)
    heading(doc, "ANEXO B — Análisis Comparativo entre Agentes", level=1)
    section_intro(doc, COMP_INTRO)
    for path, width, cap_text in COMP_FIGS:
        ok = insert_fig(doc, path, cap_text, width)
        if ok: fig_ok += 1
        else:  fig_skip += 1

    # ────────────────────────────────────────────────────────────────────────
    # ANEXO C — DEMOSTRACIÓN DE HIPÓTESIS
    # ────────────────────────────────────────────────────────────────────────
    page_break(doc)
    heading(doc, "ANEXO C — Demostración de Hipótesis de Investigación", level=1)
    section_intro(doc, HIP_INTRO)
    for path, width, cap_text in HIP_FIGS:
        ok = insert_fig(doc, path, cap_text, width)
        if ok: fig_ok += 1
        else:  fig_skip += 1

    # ────────────────────────────────────────────────────────────────────────
    # GUARDAR
    # ────────────────────────────────────────────────────────────────────────
    doc.save(str(DEST))
    total_after = len(doc.paragraphs)
    print(f"v11: {total_after} párrafos → +{total_after - total_before} párrafos agregados")
    print(f"✅ Figuras insertadas: {fig_ok}  |  Omitidas (no encontradas): {fig_skip}")
    print(f"✅ Guardado: {DEST}")


if __name__ == "__main__":
    main()
