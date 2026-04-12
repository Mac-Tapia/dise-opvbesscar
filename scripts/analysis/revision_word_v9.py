"""
Revisión completa de redacción del Word v8 → v9
Proyecto pvbesscar – Tesis OE3 Selección Agente RL

CAMBIOS:
1. Corregir "episodio 49" → "episodio 48" (ep óptimo SAC verificado en CSV)
2. Corregir "A2C Ep 4" → "Ep 3" en tabla criterios 4.6.3.6
3. Corregir sec. 5.2 "PPO queda tercero" → "A2C queda tercero" (rewrite párrafo)
4. Reescribir secciones 1–9 (intro) en prosa académica natural para tesis
5. Mejorar fluidez y coherencia en todas las conclusiones (C1-C6)

DATOS VERIFICADOS (outputs/sac_training/sac_episodios_history.csv – 11/04/2026 23:44):
  SAC  → F2_min = 2,622,734 kg CO₂/año, ep=48, violations=0
  PPO  → F2_min = 2,787,039 kg CO₂/año, ep=40, violations=0
  A2C  → F2_min = 2,834,857 kg CO₂/año, ep=3 , violations=217
  Kruskal-Wallis H=81.65 p=1.86e-18
  Wilcoxon T=0 p=1.78e-15
  F0 = 7,054,000  F1_media = 5,789,814  EF = 0.4521 kg/kWh
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

SRC  = Path("outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v8.docx")
DEST = Path("outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v9.docx")

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def replace_text_in_paragraph(para, old: str, new: str):
    """Reemplaza texto manteniendo el formato del primer run."""
    full = para.text
    if old not in full:
        return False
    # Consolidar texto en el primer run y borrar el resto
    if para.runs:
        para.runs[0].text = full.replace(old, new)
        for r in para.runs[1:]:
            r.text = ""
    return True


def set_paragraph_text(para, text: str, bold: bool = False, italic: bool = False):
    """Reemplaza todo el contenido del párrafo con texto nuevo."""
    # Limpiar todos los runs
    for run in para.runs:
        run.text = ""
    if para.runs:
        r = para.runs[0]
    else:
        r = para.add_run()
    r.text = text
    r.bold = bold
    r.italic = italic


# ─────────────────────────────────────────────────────────────────────────────
# Correcciones puntuales de datos
# ─────────────────────────────────────────────────────────────────────────────

def fix_episode_numbers(doc: Document) -> int:
    """Corrige referencias a 'episodio 49' por 'episodio 48' (SAC óptimo real)."""
    count = 0
    patterns = [
        ("episodio 49",   "episodio 48"),
        ("Episodio 49",   "Episodio 48"),
        ("Ep 49",         "Ep 48"),
        ("ep 49",         "ep 48"),
        ("episodio ├│ptimo Ep 49", "episodio ├│ptimo Ep 48"),
        # A2C correct episode
        ("mejor episodio (Ep 4)", "mejor episodio (Ep 3)"),
        ("Ep 4)",               "Ep 3)"),
        ("ep 4 sugiere",         "ep 3 sugiere"),
    ]
    for para in doc.paragraphs:
        for old, new in patterns:
            if replace_text_in_paragraph(para, old, new):
                count += 1
    # Also fix in table cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for old, new in patterns:
                        if replace_text_in_paragraph(para, old, new):
                            count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Reescritura secciones 1–9 en prosa académica
# ─────────────────────────────────────────────────────────────────────────────

# Mapa: índice del párrafo en el documento v8 → texto nuevo en prosa
# Los textos de reemplazo están escritos en prosa académica formal en español.

PROSE_REPLACEMENTS: dict[int, str] = {

    # ── Sección 1: Objetivo OE3 ────────────────────────────────────────────

    9: (
        "El Objetivo Específico 3 (OE3) del proyecto PVBESSCAR establece la necesidad de "
        "seleccionar el agente de inteligencia artificial más apropiado para gestionar "
        "la recarga de motos y mototaxis eléctricas de manera que contribuya de forma "
        "cuantificable a la reducción de emisiones de dióxido de carbono en la ciudad de "
        "Iquitos, Perú. Esta selección se realiza mediante simulación en entorno CityLearn v2 "
        "con datos reales del año 2024, comparando tres algoritmos de aprendizaje por refuerzo "
        "profundo: Soft Actor-Critic (SAC), Proximal Policy Optimization (PPO) y Advantage "
        "Actor-Critic (A2C), todos entrenados durante 50 episodios completos (438,000 pasos "
        "temporales) sobre la infraestructura dimensionada en OE2."
    ),

    11: (
        "La infraestructura energética simulada corresponde al contexto real de Iquitos, Perú, "
        "para el año 2024. El sistema fotovoltaico (FV) cuenta con 4,050 kWp instalados, que "
        "generan 8,292,514 kWh/año según la simulación pvlib con datos PVGIS. El sistema de "
        "almacenamiento en baterías (BESS) tiene una capacidad de 2,000 kWh y una potencia de "
        "400 kW, operando con profundidad de descarga del 80 % y eficiencia de ida y vuelta del "
        "95 %. La infraestructura de carga eléctrica comprende 19 unidades × 2 sockets = "
        "38 sockets en Modo 3 IEC 62196-2 a 7.4 kW/socket (32 A, 230 V monofásico), con una "
        "potencia instalada total de 281.2 kW. La demanda diaria EV asciende a 270 motos + "
        "39 mototaxis, constituyendo 309 vehículos/día con una demanda energética anual de "
        "408,282 kWh/año. El factor de emisión de la red eléctrica aislada de Iquitos, "
        "reportado por el MINEM, es de 0.4521 kg CO₂/kWh, generado en su totalidad por "
        "plantas a diésel. Los factores de emisión vehicular por combustión interna utilizados "
        "como contrafactual son 0.87 kg CO₂/km para motocicletas de gasolina y "
        "0.54 kg CO₂/km para mototaxis a diésel, conforme a las directrices IPCC 2006 Tier 2."
    ),

    # Eliminar los párrafos sueltos de infraestructura (12-18) reemplazándolos con ""
    12: "",
    13: "",
    14: "",
    15: "",
    16: "",
    17: "",
    18: "",

    # ── Sección 2: Marco de Cuantificación ────────────────────────────────

    21: (
        "La cuantificación de emisiones de CO₂ sigue las definiciones del GHG Protocol "
        "Corporate Standard (WRI/WBCSD, 2015) e ISO 14064-1:2018, alineadas con la "
        "metodología de Mohammed et al. (2026) y la arquitectura de cómputo implementada "
        "en co2_formulas.py del proyecto. Se definen tres escenarios de referencia: F0 "
        "(contrafactual sin proyecto, flota ICE), F1 (flota eléctrica con solar + BESS, "
        "sin control RL) y F2 (flota eléctrica con solar + BESS + agente RL). La "
        "contribución cuantificable del agente RL corresponde a la diferencia ΔCO₂_RL = "
        "F1 − F2, descompuesta en reducción directa (combustible vehicular evitado) e "
        "indirecta (importación de red diésel desplazada por el despacho óptimo "
        "solar + BESS)."
    ),

    # ── Sección 3: Resultados por Agente ──────────────────────────────────

    47: (
        "En esta sección se presentan los resultados de la fase de evaluación para los "
        "tres agentes entrenados durante 50 episodios (438,000 pasos temporales cada uno) "
        "sobre el entorno CityLearn v2, utilizando el dataset OE2 de Iquitos 2024. Los "
        "resultados se expresan en términos de la variable F2 (CO₂ controlado, "
        "kg CO₂/año), que es la métrica principal del OE3, y se complementan con el "
        "balance energético anual (solar, BESS, importación de red) y el número de "
        "incumplimientos de deuda energética EV (debt_violations). Cada agente fue "
        "evaluado en su episodio óptimo —aquel en que se minimiza F2— y los resultados "
        "se presentan comparativamente en la Tabla 4."
    ),

    49: (
        "El agente SAC (Soft Actor-Critic), algoritmo off-policy basado en maximización "
        "de entropía, alcanzó F2 = 2,622,734 kg CO₂/año en el episodio óptimo 48, "
        "con cero incumplimientos de deuda energética. En términos absolutos, el SAC "
        "evita 4,431,266 kg CO₂/año respecto al escenario sin proyecto (F0), "
        "equivalente a una reducción del 62.8 % sobre la línea base contrafactual."
    ),

    51: (
        "El agente PPO (Proximal Policy Optimization), algoritmo on-policy con "
        "clipping de gradiente, obtuvo F2 = 2,787,039 kg CO₂/año en el episodio "
        "óptimo 40, sin incumplimientos de deuda energética, logrando una reducción "
        "del 60.5 % respecto a F0 (4,266,961 kg CO₂/año evitados)."
    ),

    53: (
        "El agente A2C (Advantage Actor-Critic), algoritmo on-policy sincrónico, "
        "registró F2 = 2,834,857 kg CO₂/año en el episodio óptimo 3. A pesar de "
        "alcanzar su mínimo en etapas tempranas del entrenamiento, presentó 217 "
        "incumplimientos de deuda energética en ese episodio, lo que limita su "
        "idoneidad para despliegue en producción. La reducción lograda fue del "
        "59.8 % respecto a F0 (4,219,143 kg CO₂/año evitados)."
    ),

    # ── Sección 4: Tabla Comparativa – Ranking ────────────────────────────

    57: (
        "La Tabla 4 presenta el ranking OE3 de los tres agentes ordenados por el "
        "criterio principal de minimización de F2 (menor CO₂ controlado en el "
        "episodio óptimo). El criterio secundario de desempate es el mayor valor de "
        "recompensa acumulada. El agente con el menor F2 cumple de manera más efectiva "
        "el OE3, puesto que maximiza el desplazamiento de generación diésel por energía "
        "solar y BESS gestionada inteligentemente. La Tabla consolida F2 mínimo, "
        "porcentaje de reducción vs F0 y F1, y las métricas de robustez operacional "
        "(debt violations y cobertura EV media)."
    ),

    # ── Sección 5: Análisis del Agente Ganador: SAC ───────────────────────

    61: (
        "El agente SAC (Soft Actor-Critic) obtiene la mayor reducción de emisiones de "
        "CO₂ de los tres agentes evaluados, siendo seleccionado como el agente óptimo "
        "para cumplir el OE3. Su arquitectura off-policy con replay buffer de 100,000 "
        "transiciones y el principio de máxima entropía le permiten explorar "
        "eficientemente el espacio de acciones continuo de 39 dimensiones "
        "(1 BESS + 38 sockets), aprendiendo políticas de despacho robustas a lo largo "
        "de los 50 episodios de entrenamiento."
    ),

    63: (
        "En su episodio óptimo (episodio 48 de 50), el SAC alcanza F2 = 2,622,734 kg "
        "CO₂/año, representando una reducción del 62.8 % respecto al escenario "
        "contrafactual F0 (7,054,000 kg CO₂/año) y del 54.7 % respecto a la línea "
        "base F1 (5,789,814 kg CO₂/año). La CO₂ total evitado asciende a "
        "3,552,619 kg/año descomponiendo en 328,736 kg de reducción directa "
        "(desplazamiento de combustible vehicular) y 3,223,883 kg de reducción "
        "indirecta (desplazamiento de generación diésel de red). La importación "
        "de red en este episodio es de solo 5,801,227 kWh/año frente a los "
        "12,776,934 kWh/año de la operación sin solar ni BESS."
    ),

    64: "",
    65: "",
    66: (
        "El episodio óptimo 48 alcanzado por el SAC al término de las 50 iteraciones "
        "evidencia que el algoritmo off-policy continuó explorando y mejorando sus "
        "políticas hasta los episodios finales del entrenamiento, a diferencia del A2C "
        "(cuyo mínimo ocurre en el episodio 3) y del PPO (episodio 40). El episodio 48 "
        "presenta además cero incumplimientos de deuda energética EV, lo que garantiza "
        "el cubrimiento completo de la demanda de carga de motos y mototaxis. La "
        "descarga del BESS fue de 875,698 kWh/año, con una generación solar de "
        "8,292,514 kWh/año aprovechada mediante la estrategia solar-priority."
    ),
    67: "",
    68: "",
    69: (
        "La mejora progresiva del SAC a lo largo de los 50 episodios (de "
        "3,055,514 kg CO₂/año en el episodio 1 a 2,622,734 kg CO₂/año en el "
        "episodio 48, equivalente a una convergencia del 14.1 %) confirma la "
        "capacidad del algoritmo para aprender y refinar continuamente su política "
        "de despacho de energía. Esta característica es consecuencia directa del "
        "mecanismo de replay de experiencia off-policy de SAC, que reutiliza "
        "transacciones pasadas de manera eficiente."
    ),

    # ── Sección 5.1: SAC vs PPO ───────────────────────────────────────────

    72: (
        "PPO (Proximal Policy Optimization) ocupa el segundo lugar en el ranking "
        "OE3 con F2 = 2,787,039 kg CO₂/año en su episodio óptimo 40, superado por "
        "el SAC en 164,305 kg CO₂/año. Aunque PPO converge de manera estable "
        "gracias al mecanismo de clipping de la razón de probabilidad (ε = 0.2), "
        "su naturaleza on-policy limita la eficiencia muestral: aprende únicamente "
        "de la interacción más reciente, descartando la experiencia acumulada de "
        "episodios anteriores. Esto se refleja en una mejora de convergencia del "
        "7.89 % entre el episodio 1 (3,029,400 kg/año) y el episodio 50 "
        "(2,790,249 kg/año), inferior a la del SAC (14.1 %)."
    ),

    73: "",
    74: "",
    75: (
        "La ventaja del SAC sobre el PPO en el OE3 asciende a 164,305 kg CO₂/año "
        "menos de emisiones controladas, equivalente a 2.3 puntos porcentuales "
        "adicionales de reducción. Esta diferencia es estadísticamente significativa "
        "(Mann-Whitney U = 121, p = 3.636 × 10⁻¹⁵, d = 2.43 — efecto gigante), "
        "confirmando que la ventaja del SAC no es producto de la variabilidad "
        "estocástica del entrenamiento sino de su superior capacidad de aprendizaje "
        "en espacios de acción continuos y multidimensionales."
    ),
    76: "",
    77: "",

    # ── Sección 5.2: Por qué A2C queda tercero ────────────────────────────
    # IMPORTANTE: El título de la sección (heading) SE REEMPLAZA EN OTRO PASO
    80: (
        "El agente A2C (Advantage Actor-Critic) ocupa el tercer lugar en el "
        "ranking OE3, con F2 = 2,834,857 kg CO₂/año en su episodio óptimo 3. "
        "Aunque A2C presenta la menor desviación estándar global entre los tres agentes "
        "(σ = 12,011 kg/año, CV global = 0.42 %), su mínimo de emisiones es el "
        "más alto de los tres porque el algoritmo alcanzó su mejor desempeño en las "
        "fases tempranas del entrenamiento (episodio 3) y no logró mejoras posteriores "
        "significativas: la variación entre el episodio 1 (2,922,533 kg/año) y el "
        "episodio 50 (2,838,665 kg/año) fue de apenas 2.87 %. Adicionalmente, el "
        "episodio óptimo del A2C registró 217 incumplimientos de deuda energética EV, "
        "frente a cero del SAC y cero del PPO en sus episodios óptimos respectivos, "
        "lo que indica que la política A2C no garantiza la cobertura completa de la "
        "demanda de carga vehicular en ese escenario. El menor volumen de descarga "
        "del BESS (744,717 kWh/año en el mejor episodio, frente a 875,698 kWh/año "
        "del SAC) sugiere que A2C no aprovecha plenamente el almacenamiento energético "
        "para desplazar la importación de red diésel."
    ),

    # ── Sección 7: Discusión ──────────────────────────────────────────────

    87: (
        "Los tres agentes de aprendizaje por refuerzo profundo evaluados —SAC, PPO y "
        "A2C— demuestran que la integración de control inteligente sobre la "
        "infraestructura solar + BESS + cargadores EV produce una reducción "
        "estadísticamente significativa de las emisiones de CO₂ de la red diésel "
        "de Iquitos, en comparación con la operación base sin agente RL. La prueba "
        "de Wilcoxon de rangos con signo (T = 0, p = 1.776 × 10⁻¹⁵) rechaza con "
        "nivel de confianza del 99.9 % la hipótesis nula de que el control RL no "
        "mejora el escenario F1, validando así la hipótesis general del proyecto "
        "(HG) y las hipótesis específicas HE1–HE3."
    ),

    89: (
        "El SAC (Soft Actor-Critic, off-policy) obtuvo la mayor reducción de CO₂ "
        "de la red (F2_min = 2,622,734 kg CO₂/año, reducción del 62.8 % vs F0), "
        "con el episodio óptimo en la iteración 48 de 50 y cero incumplimientos de "
        "deuda energética. Su exploración de máxima entropía y el buffer de replay "
        "de 100,000 transiciones le confieren la mayor eficiencia muestral del "
        "conjunto evaluado, siendo el algoritmo más adecuado para espacios de "
        "acción continuos y alta dimensionalidad como el presente (39 dimensiones)."
    ),

    90: (
        "El PPO (Proximal Policy Optimization, on-policy) se posiciona en segundo "
        "lugar con F2_min = 2,787,039 kg CO₂/año (reducción del 60.5 % vs F0, "
        "episodio óptimo 40, cero violation). Su convergencia estable, con un "
        "coeficiente de variación de plateau del 0.195 %, lo convierte en una "
        "opción válida para entornos con restricciones de memoria donde no es "
        "posible mantener un buffer de replay de gran tamaño."
    ),

    91: (
        "El A2C (Advantage Actor-Critic, on-policy sincrónico) ocupa el tercer lugar "
        "con F2_min = 2,834,857 kg CO₂/año (reducción del 59.8 % vs F0, "
        "episodio óptimo 3). Si bien presenta la menor variabilidad estocástica "
        "(σ = 12,011 kg/año), su mínimo de emisiones fue alcanzado en el episodio "
        "inicial y no se mejoró significativamente (convergencia del 2.87 % en "
        "50 episodios), y presentó 217 incumplimientos de deuda energética en ese "
        "episodio, indicando que su política no garantiza la cobertura total de la "
        "demanda EV en el episodio óptimo."
    ),

    92: (
        "La reducción directa de CO₂ —derivada de la electrificación vehicular y "
        "no del algoritmo— es comparable entre los tres agentes: PPO reporta "
        "334,103 kg, SAC 328,736 kg y A2C 301,293 kg CO₂/año evitados en sus "
        "episodios óptimos. La variación obedece a las diferencias en cobertura "
        "de la demanda mototaxi: el A2C entrega solo 27,693 kWh a mototaxis frente "
        "a los 59,305 kWh del SAC, lo que reduce su reducción directa. La componente "
        "indirecta —desplazamiento de importación de red diésel mediante gestión "
        "solar + BESS— es donde el SAC supera claramente a PPO y A2C "
        "(3,223,883 vs 3,052,175 vs 2,985,752 kg CO₂/año), siendo la diferencia "
        "determinante en la selección del agente."
    ),

    # ── Sección 8: Conclusiones ───────────────────────────────────────────

    95: (
        "Con base en la evaluación cuantitativa de los tres agentes de aprendizaje por "
        "refuerzo profundo sobre el entorno CityLearn v2 con el dataset OE2 de "
        "Iquitos 2024 —solar 4,050 kWp, BESS 2,000 kWh, 38 sockets EV Mode 3— "
        "y el protocolo estadístico no paramétrico aplicado a los 50 episodios de "
        "entrenamiento (438,000 pasos temporales cada uno), se establecen las "
        "siguientes conclusiones:"
    ),

    97: (
        "[C1] El agente SAC es el más apropiado para cumplir el OE3, con F2 = "
        "2,622,734 kg CO₂/año (reducción del 62.8 % vs F0, episodio óptimo 48/50, "
        "cero incumplimientos de deuda EV). Su superioridad frente a PPO "
        "(164,305 kg CO₂/año menos) y frente a A2C (212,123 kg CO₂/año menos) es "
        "estadísticamente significativa a nivel α = 0.001."
    ),

    98: (
        "[C2] La contribución cuantificable total del sistema PVBESSCAR gestionado "
        "por el agente SAC es de 4,431,266 kg CO₂/año respecto al escenario "
        "contrafactual sin proyecto (F0 = 7,054,000 kg CO₂/año), equivalente a "
        "4,431.3 tCO₂/año. Esta reducción se descompone en 328,736 kg CO₂/año "
        "de reducción directa (reemplazo de combustión interna vehicular por "
        "VEs eléctricos) y 3,223,883 kg CO₂/año de reducción indirecta "
        "(desplazamiento de importación de red diésel mediante solar + BESS + RL). "
        "Respecto a F1, el aporte exclusivo del agente RL es de 3,167,080 kg CO₂/año "
        "(54.7 %)."
    ),

    99: (
        "[C3] Las fórmulas de cuantificación CO₂ implementadas en co2_formulas.py "
        "(F0, F1, F2) son consistentes con el GHG Protocol Corporate Standard e "
        "ISO 14064-1, con el factor de emisión verificado MINEM Iquitos "
        "(0.4521 kg CO₂/kWh) y el esquema de emisiones directas e indirectas "
        "conforme a la Scope 1/Scope 2 del GHG Protocol. La trazabilidad y "
        "auditabilidad de los cálculos es completa."
    ),

    100: (
        "[C4] El PPO es el segundo agente más efectivo (F2 = 2,787,039 kg CO₂/año, "
        "reducción del 60.5 % vs F0), constituyendo una opción viable para "
        "entornos de hardware con memoria RAM limitada que no permiten un buffer "
        "de replay de gran tamaño. Su coeficiente de variación de plateau "
        "(CV = 0.195 %) indica convergencia estable."
    ),

    101: (
        "[C5] El A2C ocupa el tercer lugar (F2 = 2,834,857 kg CO₂/año, "
        "reducción del 59.8 % vs F0). Aunque presenta la menor variabilidad "
        "estocástica global (σ = 12,011 kg/año), su mínimo se alcanza en las "
        "etapas tempranas del entrenamiento (episodio 3) sin mejoras posteriores "
        "significativas, y el episodio óptimo registra 217 incumplimientos de "
        "deuda EV. Un entrenamiento extendido (>100 episodios) podría mejorar "
        "su convergencia y reducir las violaciones."
    ),

    102: (
        "[C6] La contribución cuantificable del agente SAC a la reducción de CO₂ "
        "en Iquitos es de 3,223,883 kg CO₂/año indirecta (red diésel desplazada) "
        "más 328,736 kg CO₂/año directa (electrificación vehicular), sumando "
        "3,552,619 kg CO₂/año de reducción total neta. Frente al escenario "
        "completo sin proyecto (F0 ICE), la reducción total del sistema "
        "PVBESSCAR es de 4,431,266 kg CO₂/año (4,431.3 tCO₂/año)."
    ),

    104: (
        "RECOMENDACIÓN FINAL OE3: Implementar el agente SAC para la gestión de "
        "la infraestructura de carga inteligente de motos y mototaxis eléctricas "
        "en Iquitos. El SAC obtiene la menor F2 (2,622,734 kg CO₂/año), la mayor "
        "reducción vs F0 (62.8 %), cero incumplimientos de deuda EV en el episodio "
        "óptimo, la mejor convergencia (14.1 %) y la superioridad estadística "
        "sobre PPO (d = 2.43) y A2C (d = 2.21) con p < 10⁻¹³ en ambas "
        "comparaciones par a par. La contribución ambiental cuantificable del "
        "sistema completo PVBESSCAR con agente SAC es de 4,431.3 tCO₂/año evitadas "
        "respecto al escenario sin proyecto, cumpliéndose el OE3 del proyecto."
    ),

    # ── Sección 5.1 intro ────────────────────────────────────────────────

    193: (
        "El Objetivo Específico 2 (OE2) del proyecto PVBESSCAR comprende el "
        "dimensionamiento integral de la infraestructura de generación solar "
        "fotovoltaica (FV), almacenamiento en baterías (BESS) y cargadores de "
        "vehículos eléctricos (EV) para el mall de Iquitos, conforme a las "
        "especificaciones técnicas del año 2024. Los resultados de OE2 "
        "constituyen los artefactos de datos de entrada para el entorno CityLearn v2 "
        "utilizado en OE3: la serie temporal de generación solar de 8,760 horas "
        "(pv_generation_timeseries.csv), los perfiles de demanda EV horaria "
        "(chargers_ev_ano_2024_v3.csv) y la configuración del BESS "
        "(bess_ano_2024.csv). Los siguientes subapartados presentan los resultados "
        "descriptivos del dimensionamiento de cada subsistema."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Corrección del title de la subsección 5.2 (PPO → A2C queda tercero)
# ─────────────────────────────────────────────────────────────────────────────

def fix_section_titles(doc: Document) -> int:
    count = 0
    fixes = [
        ("Por qu├® PPO queda tercero",  "5.2. Por qué A2C queda tercero"),
        ("Por qu├® PPO queda en tercer", "5.2. Por qué A2C queda tercero"),
        ("PPO queda tercero",           "A2C queda tercero"),
    ]
    for para in doc.paragraphs:
        for old, new in fixes:
            if old in para.text:
                set_paragraph_text(para, new, bold=(para.style.name.startswith("Heading")))
                count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"Abriendo {SRC} …")
    doc = Document(str(SRC))

    total_paras = len(doc.paragraphs)
    print(f"  Párrafos: {total_paras} | Tablas: {len(doc.tables)}")

    # 1. Corregir episodio 49 → 48 y A2C Ep 4 → Ep 3
    n_ep = fix_episode_numbers(doc)
    print(f"  [1] Correcciones episodio: {n_ep} cambios")

    # 2. Corregir título sección PPO tercero
    n_title = fix_section_titles(doc)
    print(f"  [2] Correcciones títulos de sección: {n_title} cambios")

    # 3. Reescritura de párrafos en prosa académica
    n_prose = 0
    for idx, new_text in PROSE_REPLACEMENTS.items():
        if idx >= total_paras:
            print(f"  [WARN] Índice {idx} fuera de rango ({total_paras} párrafos)")
            continue
        para = doc.paragraphs[idx]
        old_preview = para.text[:60] if para.text else "(vacío)"
        if new_text == "":
            # Eliminar párrafo vaciándolo (no podemos borrar directamente con python-docx)
            for run in para.runs:
                run.text = ""
            if para.runs:
                para.runs[0].text = ""
            else:
                para.add_run("")
        else:
            set_paragraph_text(para, new_text)
        n_prose += 1
        print(f"  [3.{idx}] «{old_preview[:50]}» → prosa reescrita")

    # 4. Verificar que el ep SAC dice "48" en sección 4.6.3.7
    for para in doc.paragraphs:
        if "episodio 49" in para.text or "Ep 49" in para.text or "ep 49" in para.text:
            print(f"  [WARN] Aún hay referencia a 'episodio 49': {para.text[:80]}")

    # Guardar
    doc.save(str(DEST))
    print(f"\n✅ Guardado: {DEST}")
    print(f"   Párrafos procesados para reescritura: {n_prose}")
    print(f"   Correcciones de episodio: {n_ep}")
    print(f"   Correcciones de título: {n_title}")


if __name__ == "__main__":
    main()
