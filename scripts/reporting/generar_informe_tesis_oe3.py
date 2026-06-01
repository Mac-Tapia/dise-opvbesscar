#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_informe_tesis_oe3.py
Genera el Informe de Tesis OE3 en formato Word (.docx) con todos los
capítulos, tablas estadísticas, figuras y resultados actualizados.

Fuentes de datos (siempre las más recientes):
  reports/oe3/agents_comparison_canonical.json
  reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md
  outputs/estadistica_oe3/reporte_estadistico_oe3.md
  reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md
  outputs/docx/graficas/*.png
  reports/oe3/COSTOS_ESTABILIDAD_OE3.md
  reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md
  outputs/estadistica_oe3/costos_estabilidad_consolidado.csv

Salida: outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT    = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "docx"
OUT_DIR.mkdir(parents=True, exist_ok=True)
GRAFICAS = ROOT / "outputs" / "docx" / "graficas"
TODAY = datetime.now().strftime("%Y-%m-%d")

AGENTS = ["A2C", "PPO", "SAC"]
AGENT_COLORS = {"A2C": (33, 150, 243), "PPO": (255, 152, 0), "SAC": (76, 175, 80)}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def h1(doc: Document, text: str) -> None:
    p = doc.add_heading(text, level=1)
    p.runs[0].font.size = Pt(16)
    p.runs[0].font.color.rgb = RGBColor(0x1A, 0x23, 0x7E)


def h2(doc: Document, text: str) -> None:
    p = doc.add_heading(text, level=2)
    p.runs[0].font.size = Pt(13)
    p.runs[0].font.color.rgb = RGBColor(0x0D, 0x47, 0xA1)


def h3(doc: Document, text: str) -> None:
    p = doc.add_heading(text, level=3)
    p.runs[0].font.size = Pt(11)


def body(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    p.runs[0].font.size = Pt(11) if p.runs else None


def fig(doc: Document, path: Path, caption: str, width: float = 14.0) -> None:
    if path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(path), width=Cm(width))
        cap = doc.add_paragraph(caption)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].font.size = Pt(9)
        cap.runs[0].italic = True
    else:
        doc.add_paragraph(f"[Figura no disponible: {path.name}]").runs[0].italic = True


def table_simple(doc: Document, headers: list[str], rows: list[list], title: str = "") -> None:
    if title:
        doc.add_paragraph(title).runs[0].bold = True
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        hdr[i].paragraphs[0].runs[0].bold = True
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        r = t.add_row().cells
        for i, val in enumerate(row):
            r[i].text = str(val)
            r[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()


# ─── Carga de datos ───────────────────────────────────────────────────────────

def load_canonical() -> dict:
    p = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_episodios(agent: str) -> pd.DataFrame | None:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"{agent.lower()}_episodios_history.csv"
    return pd.read_csv(p) if p.exists() else None


def load_robustez(agent: str) -> dict:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"{agent.lower()}_robustez_estocastica.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_result(agent: str) -> dict:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"result_{agent.lower()}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_costos() -> pd.DataFrame | None:
    p = ROOT / "outputs" / "estadistica_oe3" / "costos_estabilidad_consolidado.csv"
    return pd.read_csv(p) if p.exists() else None


# ─── Capítulos ────────────────────────────────────────────────────────────────

def cap_portada(doc: Document, canon: dict) -> None:
    doc.add_paragraph()
    t = doc.add_paragraph("UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER; t.runs[0].bold = True; t.runs[0].font.size = Pt(14)
    t = doc.add_paragraph("Facultad de Ingeniería Industrial")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER; t.runs[0].font.size = Pt(12)
    doc.add_paragraph()
    t = doc.add_paragraph("INFORME DE TESIS — OBJETIVO ESPECÍFICO 3 (OE3)")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER; t.runs[0].bold = True; t.runs[0].font.size = Pt(16)
    doc.add_paragraph()
    t = doc.add_paragraph(
        "Selección del Mejor Agente de Aprendizaje por Refuerzo para Optimización\n"
        "de Carga EV con Reducción de CO₂ en Sistema Fotovoltaico-BESS\n"
        "Red Aislada de Iquitos, Perú"
    )
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER; t.runs[0].font.size = Pt(13)
    doc.add_paragraph()
    meta_sel = canon.get("metadata", {}).get("selected_agent", "A2C")
    t = doc.add_paragraph(f"Agente Seleccionado: {meta_sel}")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER; t.runs[0].bold = True
    t.runs[0].font.size = Pt(14); t.runs[0].font.color.rgb = RGBColor(0x1B, 0x5E, 0x20)
    doc.add_paragraph()
    t = doc.add_paragraph(f"Autor: MAC TAPIA, mac.tapia@unmsm.edu.pe")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = doc.add_paragraph(f"Fecha: {TODAY}")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = doc.add_paragraph("Branch: smartcharger | obs_dim=19 | CO2_DUAL_FOCUS v8.1")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER; t.runs[0].font.size = Pt(9); t.runs[0].italic = True
    doc.add_page_break()


def cap_introduccion(doc: Document) -> None:
    h1(doc, "1. INTRODUCCIÓN")
    body(doc,
         "El presente informe documenta los resultados del Objetivo Específico 3 (OE3) de "
         "la tesis de investigación: selección del mejor agente de Aprendizaje por Refuerzo "
         "(RL) para controlar la carga de vehículos eléctricos (EV) minimizando las emisiones "
         "de CO₂ en la microrred aislada de Iquitos, Loreto, Perú.")
    h2(doc, "1.1 Contexto del sistema")
    table_simple(doc,
        ["Componente", "Especificación", "Fuente"],
        [
            ["Solar PV",     "4,162 kWp DC / 3,201 kW AC",    "OE2 solar_pvlib.py + PVGIS TMY"],
            ["Energía solar","5,819,332 kWh/año (5.82 GWh)",  "PR=83.5%, yield=1,398 kWh/kWp"],
            ["BESS",         "2,000 kWh / 400 kW (LFP)",      "OE2 bess.py v5.3, DoD 80%"],
            ["Cargadores EV","19 × 2 sockets = 38 puntos",    "OE2 chargers.py v5.4"],
            ["Flota EV",     "270 motos + 39 mototaxis/día",   "Estudio demanda OE2"],
            ["Red eléctrica","0.4521 kg CO₂/kWh (diesel)",    "MINEM 2024, Electro Oriente"],
            ["Tarifa HP",    "0.45 S./kWh (18-23h)",           "OSINERGMIN Res. 047-2024-OS/CD"],
            ["Tarifa HFP",   "0.28 S./kWh",                   "OSINERGMIN Res. 047-2024-OS/CD"],
        ],
        "Tabla 1.1 — Especificaciones del sistema pvbesscar")
    h2(doc, "1.2 Espacio de observación y acción (obs_dim=19)")
    body(doc,
         "El entorno CityLearn v2 expone 19 dimensiones de observación al agente RL, "
         "organizadas en tres grupos:")
    table_simple(doc,
        ["Grupo", "Dimensiones", "Variables"],
        [
            ["Base CityLearn (12D)", "[0-11]",
             "month, hour, day_type, temp, irr_diff, irr_dir, carbon_intensity, "
             "non_shiftable_load, solar_gen, bess_soc, net_elec, electricity_pricing"],
            ["EV state (5D)", "[12-16]",
             "motos_demand_norm, mototaxis_demand_norm, motos_debt_norm, "
             "mototaxis_debt_norm, hour_sin"],
            ["Tarifa (2D)", "[17-18]", "tarifa_norm (HP/HFP), is_hora_punta"],
        ],
        "Tabla 1.2 — Espacio de observación 19D (incluye electricity_pricing — nuevo)")
    doc.add_page_break()


def cap_metodologia(doc: Document) -> None:
    h1(doc, "2. METODOLOGÍA DE INVESTIGACIÓN")
    h2(doc, "2.1 Diseño de investigación del proyecto")
    table_simple(doc,
        ["Aspecto", "Clasificación", "Justificación y sustento"],
        [
            ["Enfoque", "Cuantitativo",
             "Cobertura, demanda, PV, BESS, cargadores, energía EV, grid import, costos, CO₂ y métricas RL son variables numéricas (Hernández Sampieri et al. 2014)."],
            ["Tipo", "Aplicada",
             "Resuelve el problema práctico de diseñar una infraestructura de carga inteligente EV+BESS+solar y su control RL para reducir CO₂ en Iquitos (Murillo Vargas 2010; Arias 2012)."],
            ["Nivel", "Explicativo-causal",
             "Explica cómo la infraestructura y la estrategia de control modifican CO₂, carga EV, grid import y BESS bajo condiciones controladas (Hernández Sampieri et al. 2014; Tamayo y Tamayo 2003)."],
            ["Diseño único", "Cuasi-experimental por simulación",
             "OE1, OE2 y OE3 son etapas del mismo diseño: ubicación, dimensionamiento y comparación RL en simulación controlada (Campbell & Stanley 1966; Law 2015; Montgomery 2017)."],
            ["VI", "Infraestructura de carga inteligente EV+BESS+solar con estrategia RL",
             "OE1 fija ubicación; OE2 dimensiona PV/BESS/cargadores; OE3 manipula SAC, PPO y A2C como tratamientos comparables."],
            ["VD medidas", "Resultados ambientales y operativos", "CO₂ total evitado, carga EV motos+mototaxis, grid import y BESS descarga."],
            ["Variables controladas", "Condiciones de simulación", "Solar 5,819 GWh, BESS 2,000 kWh/400 kW y factor CO₂ 0.4521 kg/kWh."],
            ["Muestra", "n=50 episodios/agente", "N=150 total; saturación estadística verificada por CV plateau <0.5%."],
            ["Entorno simulación", "CityLearn v2.5.0 + IquitosEVChargingWrapper", "obs_dim=19, acción 3D y trazabilidad reproducible."],
        ],
        "Tabla 2.1 — Diseño metodológico único del proyecto")
    h2(doc, "2.2 Función de recompensa multiobjetivo — CO2_DUAL_FOCUS v8.1")
    table_simple(doc,
        ["Componente", "Peso", "Descripción"],
        [
            ["W_DIRECT_CO2",   "0.20", "CO₂ directo evitado: ICE→EV (transporte)"],
            ["W_INDIRECT_CO2", "0.30", "CO₂ indirecto: grid_import × 0.4521 kg/kWh"],
            ["W_EV_COMPLETE",  "0.35", "Satisfacción EV: motos + mototaxis sin deuda"],
            ["W_BESS_SOLAR",   "0.07", "BESS carga desde solar, no diesel nocturno"],
            ["W_SOLAR",        "0.04", "Autoconsumo PV directo"],
            ["W_GRID_STABLE",  "0.02", "Suavizado rampas grid_import"],
            ["W_COST",         "0.02", "Costo tarifario OSINERGMIN HP/HFP"],
            ["TOTAL",          "1.00", "CO2_DUAL_FOCUS v8.1 (fuente única: ev_charging_wrapper.py)"],
        ],
        "Tabla 2.2 — Pesos reward CO2_DUAL_FOCUS v8.1")
    h2(doc, "2.3 Agentes RL evaluados")
    table_simple(doc,
        ["Agente", "Tipo", "Hiperparámetros clave", "Tiempo GPU"],
        [
            ["A2C", "On-policy (Advantage Actor-Critic)", "lr=7e-4, n_steps=512, γ=0.90, ent_coef=0.01", "22.5 min"],
            ["PPO", "On-policy (Proximal Policy Optimization)", "lr=cosine, batch=256, n_epochs=10, γ=0.88, clip=0.2", "23.5 min"],
            ["SAC", "Off-policy (Soft Actor-Critic)", "lr=1e-4, buffer=87,600, batch=512, τ=0.01, γ=0.95", "186.8 min"],
        ],
        "Tabla 2.3 — Agentes RL: tipo y configuración GPU")
    h2(doc, "2.4 Cadena estadística inferencial")
    body(doc,
         "Se aplica la cadena inferencial completa sobre n=50 episodios por agente (N=150 total), "
         "con 18 variables dependientes cubriendo los 7 componentes del reward multiobjetivo:")
    body(doc,
         "Shapiro-Wilk (normalidad) → Kruskal-Wallis (global) → Dunn Bonferroni (post-hoc) → "
         "Mann-Whitney U (independiente, one-tailed) → Wilcoxon signed-rank (pareado) → "
         "Cohen d + Cliff delta (tamaño efecto) → Bootstrap IC 95% (B=10,000)")
    doc.add_page_break()


def cap_oe2(doc: Document) -> None:
    h1(doc, "3. OE2 — DIMENSIONAMIENTO Y DATASETS")
    h2(doc, "3.1 Pipeline OE2 → CityLearn v2")
    body(doc,
         "El pipeline OE2 genera 7 datasets individuales que alimentan CityLearn v2. "
         "La cadena de actualización es automática: al ejecutar main.py, los pasos 1-6 "
         "regeneran todos los datos desde cero garantizando valores reales.")
    table_simple(doc,
        ["Dataset OE2", "Fuente", "CityLearn v2 (data/interim/)", "Observación"],
        [
            ["solar_generation.csv", "solar_pvlib.py (PVGIS TMY)", "energy_simulation.csv (solar_generation W/kWp)", "4,162 kWp DC → 5,819,332 kWh/año"],
            ["mall_demand.csv", "demandamallhorakwh.csv (externo)", "energy_simulation.csv (non_shiftable_load)", "12,369,000 kWh/año"],
            ["co2_emissions.csv", "MINEM 2024", "carbon_intensity.csv (0.3904–0.6345 kg/kWh)", "Estacional HP/HFP diesel Iquitos"],
            ["tariffs_osinergmin.csv", "Res. 047-2024-OS/CD", "pricing.csv (electricity_pricing)", "HP=0.46 / HFP=0.29 S./kWh — NUEVO obs"],
            ["chargers_timeseries.csv", "chargers.py (38 sockets)", "ev_charger_motos/mototaxis.csv", "30 motos + 8 mototaxis"],
            ["bess_timeseries.csv", "bess.py (OE2)", "Wrapper directo (SOC, dispatch)", "2,000 kWh / 400 kW"],
        ],
        "Tabla 3.1 — Datasets OE2 → CityLearn v2 (todos vinculados automáticamente)")
    h2(doc, "3.2 CO₂ factor variable — Red aislada Iquitos")
    body(doc,
         "El factor CO₂ de la red eléctrica aislada de Iquitos varía estacionalmente "
         "por la dependencia de generación diesel (Electro Oriente S.A.):")
    table_simple(doc,
        ["Temporada", "Período", "Factor base", "Factor HP (18-23h)", "Factor HFP"],
        [
            ["Lluviosa", "Dic-May", "0.39 kg/kWh", "0.63 kg/kWh (×1.35)", "0.39 kg/kWh"],
            ["Seca",     "Jun-Nov", "0.47 kg/kWh", "0.63 kg/kWh (×1.35)", "0.47 kg/kWh"],
            ["Media anual", "2024", "0.4521 kg/kWh (MINEM)", "—", "—"],
        ],
        "Tabla 3.2 — Factor CO₂ estacional Iquitos (señal observable: carbon_intensity)")
    doc.add_page_break()


def cap_resultados_entrenamiento(doc: Document, canon: dict) -> None:
    h1(doc, "4. OE3 — RESULTADOS DEL ENTRENAMIENTO")
    h2(doc, "4.1 Robustez estocástica final (50 episodios/agente)")
    rows = []
    for ag in AGENTS:
        rob = load_robustez(ag)
        res = load_result(ag)
        u10 = rob.get("ultimos_10", {})
        tr  = res.get("training", {})
        v   = res.get("validation", {})
        rows.append([
            ag,
            f"{tr.get('duration_seconds',0)/60:.1f} min",
            str(rob.get("convergence_episode", "?")),
            f"{rob.get('best_episode','?')} ({rob.get('best_reward',0):.1f})",
            f"{u10.get('mean',0):.2f} ± {u10.get('std',0):.2f}",
            f"{u10.get('cv_pct',0):.1f}%",
            f"{u10.get('stability_idx',0):.4f}",
            f"{v.get('reward_mean',0):.2f} ± {v.get('reward_std',0):.2f}",
        ])
    table_simple(doc,
        ["Agente", "Tiempo GPU", "Ep. conv.", "Mejor ep/reward",
         "μ plateau ± σ", "CV", "StabIdx", "Val reward (det.)"],
        rows,
        "Tabla 4.1 — Robustez estocástica final (obs_dim=19, CO2_DUAL_FOCUS v8.1)")
    h2(doc, "4.2 CO₂ evitado y operación — 50 episodios por agente")
    rows2 = []
    for ag in AGENTS:
        ep = load_episodios(ag)
        if ep is not None:
            co2n = ep["co2_neta_kg"].sum() if "co2_neta_kg" in ep else 0
            co2d = ep["co2_directa_kg"].sum() if "co2_directa_kg" in ep else 0
            co2i = ep["co2_indirecta_kg"].sum() if "co2_indirecta_kg" in ep else 0
            ev_m = ep["ev_motos_kwh"].mean() if "ev_motos_kwh" in ep else 0
            ev_t = ep["ev_mototaxis_kwh"].mean() if "ev_mototaxis_kwh" in ep else 0
            gi   = ep["grid_import_kwh"].mean() if "grid_import_kwh" in ep else 0
            bess = ep["bess_discharge_kwh"].mean() if "bess_discharge_kwh" in ep else 0
            red  = ep["reduccion_pct"].mean() if "reduccion_pct" in ep else 0
            rows2.append([ag,
                          f"{co2n/1e6:.3f} M", f"{co2d/1e3:,.0f}",
                          f"{co2i/1e6:.3f} M",
                          f"{(ev_m+ev_t):,.0f}", f"{ev_t:,.0f}",
                          f"{gi:,.0f}", f"{bess:,.0f}", f"{red:.2f}%"])
    table_simple(doc,
        ["Agente", "CO₂ neta 50ep (kg)", "CO₂ directa/ep (kg)",
         "CO₂ indir. 50ep (kg)", "EV total/ep (kWh)", "Mototaxis/ep (kWh)",
         "Grid/ep (kWh/año)", "BESS/ep (kWh)", "Red. CO₂"],
        rows2,
        "Tabla 4.2 — Resultados operativos 50 episodios por agente")
    h2(doc, "4.3 Gráficas de convergencia")
    fig(doc, GRAFICAS / "co2_convergencia_reward.png",
        "Figura 4.1 — Convergencia del reward por episodio: A2C, PPO, SAC")
    fig(doc, GRAFICAS / "sac_convergencia_estable_inferior.png",
        "Figura 4.2 — SAC: convergencia a plateau inferior vs A2C/PPO")
    doc.add_page_break()


def cap_estadistica(doc: Document) -> None:
    h1(doc, "5. ANÁLISIS ESTADÍSTICO INFERENCIAL (18 VARIABLES)")
    body(doc,
         "Se analiza la significancia estadística de las diferencias entre los 3 agentes "
         "en 18 variables dependientes que cubren todos los componentes del reward multiobjetivo "
         "(CO₂, EV, BESS, grid, costos, estabilidad, solar F6). "
         "Nivel de significancia: α = 0.05. Bootstrap: B = 10,000 réplicas.")
    h2(doc, "5.1 Estadística descriptiva — Principales variables")
    # Cargar datos de los 3 agentes
    data = {}
    for ag in AGENTS:
        ep = load_episodios(ag)
        if ep is not None:
            ep["ev_total_kwh"] = ep["ev_motos_kwh"] + ep["ev_mototaxis_kwh"]
            data[ag] = ep
    if data:
        vars_desc = [
            ("co2_neta_kg", "CO₂ total evitado (kg/ep)", 1e3, "k"),
            ("co2_directa_kg", "CO₂ directa/ep (kg)", 1, ""),
            ("co2_indirecta_kg", "CO₂ indirecta/ep (kg)", 1e3, "k"),
            ("ev_total_kwh", "EV total/ep (kWh)", 1, ""),
            ("ev_mototaxis_kwh", "Mototaxis/ep (kWh)", 1, ""),
            ("bess_discharge_kwh", "BESS descarga/ep (kWh)", 1, ""),
            ("grid_import_kwh", "Grid import/ep (kWh/año)", 1, ""),
            ("reduccion_pct", "Reducción CO₂ (%)", 1, ""),
            ("debt_violations", "Violaciones deuda/ep", 1, ""),
        ]
        rows_desc = []
        for col, label, scale, unit in vars_desc:
            row = [label]
            for ag in AGENTS:
                if ag in data and col in data[ag].columns:
                    s = data[ag][col]
                    row.append(f"{s.mean()/scale:,.1f}{unit} ± {s.std()/scale:,.1f}{unit}")
                else:
                    row.append("N/D")
            rows_desc.append(row)
        table_simple(doc,
            ["Variable", "A2C (media ± SD)", "PPO (media ± SD)", "SAC (media ± SD)"],
            rows_desc,
            "Tabla 5.1 — Estadística descriptiva principal (n=50 ep/agente)")
    h2(doc, "5.2 Normalidad — Shapiro-Wilk")
    body(doc,
         "Todas las distribuciones rechazan normalidad (Shapiro-Wilk p < 0.05) → "
         "se aplican pruebas no paramétricas en todos los análisis.")
    h2(doc, "5.3 Prueba global — Kruskal-Wallis")
    table_simple(doc,
        ["Variable", "H", "p-valor", "Conclusión"],
        [
            ["CO₂ total evitado", "91.62", "1.27×10⁻²⁰", "✓ Diferencias globales muy significativas"],
            ["CO₂ directa", "42.40", "6.20×10⁻¹⁰", "✓ Significativo"],
            ["CO₂ indirecta", "96.34", "1.09×10⁻²¹", "✓ Muy significativo"],
            ["EV total", "52.31", "4.18×10⁻¹²", "✓ Significativo"],
            ["Mototaxis", "55.08", "1.12×10⁻¹²", "✓ Significativo"],
            ["BESS descarga", "62.77", "2.29×10⁻¹⁴", "✓ Significativo"],
            ["Grid import", "18.74", "8.59×10⁻⁵", "✓ Significativo"],
            ["Reducción CO₂ %", "55.28", "9.71×10⁻¹³", "✓ Significativo"],
        ],
        "Tabla 5.3 — Kruskal-Wallis: diferencias globales entre A2C, PPO, SAC")
    h2(doc, "5.4 Mann-Whitney U (independiente, one-tailed)")
    table_simple(doc,
        ["Variable", "A2C > SAC (p)", "PPO > SAC (p)", "A2C > PPO (p)", "Conclusión A2C vs PPO"],
        [
            ["CO₂ total evitado", "3.36×10⁻¹⁷ ✓", "4.43×10⁻¹⁶ ✓", "0.982 NS", "Equivalentes"],
            ["CO₂ directa (ICE→EV)", "4.39×10⁻⁹ ✓", "—", "0.097 NS", "Equivalentes"],
            ["CO₂ indirecta", "8.64×10⁻¹⁵ ✓", "—", "0.999 NS", "Equivalentes"],
            ["EV total carga", "9.39×10⁻¹⁰ ✓", "—", "0.071 NS", "Equivalentes"],
            ["Mototaxis (kWh)", "3.73×10⁻¹¹ ✓", "—", "0.053 NS", "Equiv. → Wilcoxon"],
            ["BESS descarga", "1.27×10⁻¹² ✓", "—", "0.029 ✓", "A2C > PPO"],
            ["Solar→EV (F6a)", "5.88×10⁻¹¹ ✓", "—", "0.019 ✓", "A2C > PPO"],
            ["Grid import", "3.94×10⁻³ ✓", "—", "0.366 NS", "Equivalentes"],
        ],
        "Tabla 5.4 — Mann-Whitney U (one-tailed α=0.05)")
    h2(doc, "5.5 Wilcoxon signed-rank (pareado ep₁...ep₅₀) — criterio de desempate")
    table_simple(doc,
        ["Variable", "A2C > PPO (W)", "A2C > PPO (p)", "Significativo", "Cohen d"],
        [
            ["Carga mototaxis", "994", "1.99×10⁻⁴", "✓ SÍ", "0.318 (small)"],
            ["BESS descarga", "variable", "0.029", "✓ SÍ", "−0.299 (small)"],
            ["Solar→EV", "variable", "0.019", "✓ SÍ", "0.251 (small)"],
            ["CO₂ total", "447", "0.968", "NS", "−0.142 (negligible)"],
        ],
        "Tabla 5.5 — Wilcoxon signed-rank: A2C supera a PPO en 3 criterios clave")
    h2(doc, "5.6 Tamaños del efecto (A2C vs SAC)")
    table_simple(doc,
        ["Variable", "Cohen d", "Magnitud", "Cliff δ", "Magnitud", "IC 95% bootstrap"],
        [
            ["CO₂ total evitado", "2.826", "very large", "0.970", "large", "[31,550; 41,581] kg"],
            ["CO₂ indirecta", "3.246", "very large", "0.934", "large", "[33,750; 42,854] kg"],
            ["EV total", "0.782", "large", "0.814", "large", "confirmado"],
            ["Mototaxis", "0.823", "large", "0.829", "large", "confirmado"],
        ],
        "Tabla 5.6 — Cohen d y Cliff δ: A2C domina en 97% de pares vs SAC")
    h2(doc, "5.7 Figuras estadísticas")
    fig(doc, GRAFICAS / "figura_pruebas_estadisticas_oe3.png",
        "Figura 5.1 — Pruebas estadísticas OE3: boxplots, Mann-Whitney, Cohen d, Bootstrap IC 95%")
    fig(doc, GRAFICAS / "co2_comparativa_multicriterio.png",
        "Figura 5.2 — Comparativa multicriterio CO₂ A2C vs PPO vs SAC (50 episodios)")
    doc.add_page_break()


def cap_costos_estabilidad(doc: Document) -> None:
    h1(doc, "6. COSTOS TARIFARIOS Y ESTABILIDAD DE RED")
    body(doc,
         "Análisis de los componentes W_COST (0.02) y W_GRID_STABLE (0.02) del reward "
         "multiobjetivo, previamente no reportados.")
    costos = load_costos()
    if costos is not None:
        h2(doc, "6.1 Costos energéticos OSINERGMIN (S./año)")
        rows = []
        for ag in AGENTS:
            df = costos[costos["agente"] == ag]
            if not df.empty:
                rows.append([
                    ag,
                    f"{df['costo_total_soles'].mean():,.0f}",
                    f"{df['costo_hp_soles'].mean():,.0f}",
                    f"{df['costo_hfp_soles'].mean():,.0f}",
                    f"{df['r_cost_mean'].mean():.4f}",
                ])
        if rows:
            table_simple(doc,
                ["Agente", "Costo total (S./año)", "Costo HP 18-23h", "Costo HFP", "r_cost medio"],
                rows,
                "Tabla 6.1 — Costos tarifarios OSINERGMIN por agente (HP=0.46 / HFP=0.29 S./kWh)")
        h2(doc, "6.2 Estabilidad de red (W_GRID_STABLE)")
        rows2 = []
        for ag in AGENTS:
            df = costos[costos["agente"] == ag]
            if not df.empty:
                rows2.append([
                    ag,
                    f"{df['r_grid_stable_mean'].mean():.4f}",
                    f"{df['grid_ramp_mean_kwh'].mean():.1f}",
                    f"{df['grid_ramp_std_kwh'].mean():.1f}",
                    f"{df['grid_cv'].mean():.4f}",
                    f"{df['grid_peak_kwh'].mean():.1f}",
                ])
        if rows2:
            table_simple(doc,
                ["Agente", "r_grid_stable", "Rampa media (kWh/h)", "Rampa std", "CV grid", "Grid peak (kWh)"],
                rows2,
                "Tabla 6.2 — Estabilidad de red: rampas y variabilidad grid_import")
        h2(doc, "6.3 Exportación solar a red Iquitos (F6d)")
        rows3 = []
        for ag in AGENTS:
            df = costos[costos["agente"] == ag]
            if not df.empty and "solar_export_kwh" in df.columns:
                exp = df["solar_export_kwh"].mean()
                rows3.append([ag, f"{exp:,.0f}", f"{exp*0.4521:,.0f}", f"{exp/5819332*100:.1f}%"])
        if rows3:
            table_simple(doc,
                ["Agente", "Export solar (kWh/año)", "CO₂ desplazado (kg/año)", "% gen. solar"],
                rows3,
                "Tabla 6.3 — Solar excedente exportado a red aislada Iquitos (F6d)")
    h2(doc, "6.4 Figuras costos y estabilidad")
    fig(doc, GRAFICAS / "costos_tarifarios_oe3.png",
        "Figura 6.1 — Costos tarifarios OSINERGMIN HP/HFP por agente RL")
    fig(doc, GRAFICAS / "estabilidad_red_oe3.png",
        "Figura 6.2 — Estabilidad de red: rampas grid_import y r_grid_stable por agente")
    doc.add_page_break()


def cap_control_operativo(doc: Document) -> None:
    h1(doc, "7. CONTROL OPERATIVO BESS/EV POR HORA")
    body(doc,
         "El análisis del patrón operativo horario revela diferencias cualitativas decisivas "
         "entre los agentes, particularmente en la gestión de la hora punta (18-23h).")
    h2(doc, "7.1 Grid import por hora del día (peak-shaving)")
    fig(doc, GRAFICAS / "control_operativo_bess_ev_oe3.png",
        "Figura 7.1 — Patrón operativo BESS/EV: grid_import, BESS SOC y EV carga por hora")
    h2(doc, "7.2 Comparativa HP: A2C vs PPO vs SAC")
    table_simple(doc,
        ["Hora", "Contexto", "A2C grid (kWh/h)", "PPO grid (kWh/h)", "SAC grid (kWh/h)", "Mejor"],
        [
            ["h06-h17", "Solar + carga BESS (HFP)", "~620-800", "~580-750", "~610-780", "PPO"],
            ["h18", "Inicio HP — BESS descarga", "~287", "~1,909", "~420", "A2C ✓"],
            ["h19-h21", "HP pico — peak-shaving", "~400-693", "~1,960-2,011", "~440-456", "A2C ✓"],
            ["h22-h23", "Fin HP", "~350-500", "~1,800-1,900", "~380-440", "A2C ✓"],
            ["h00-h05", "Noche — BESS recarga", "~620-2,114", "~435-531", "~580-650", "PPO"],
        ],
        "Tabla 7.1 — Grid import por período: A2C hace peak-shaving 3-7× más efectivo")
    body(doc,
         "A2C entra a HP con BESS SOC=0.88-0.94 (pre-cargado en solar), absorbiendo el pico. "
         "PPO concentra carga EV en HP creando pico de importación 3-7× mayor. "
         "SAC evita parcialmente HP pero a costa de debt_violations en primeros episodios.")
    doc.add_page_break()


def cap_seleccion(doc: Document, canon: dict) -> None:
    h1(doc, "8. SELECCIÓN DEL AGENTE MULTIOBJETIVO")
    meta = canon.get("metadata", {})
    sel  = meta.get("selected_agent", "A2C")
    h2(doc, f"8.1 Agente seleccionado: {sel}")
    body(doc,
         f"El agente **{sel}** es seleccionado por el criterio multiobjetivo operacional "
         f"sobre n=50 episodios, respaldado por evidencia estadística de 18 variables "
         f"con pruebas no paramétricas (α=0.05).")
    h2(doc, "8.2 Justificación estadística completa")
    table_simple(doc,
        ["Criterio", "Evidencia", "p-valor", "Efecto"],
        [
            ["Kruskal-Wallis global", "Diferencias globales significativas", "1.27×10⁻²⁰", "H=91.62"],
            ["A2C > SAC CO₂ total", "Mann-Whitney U=2462", "3.36×10⁻¹⁷", "Cliff δ=0.970 very large"],
            ["PPO > SAC CO₂ total", "Mann-Whitney U=2417", "4.43×10⁻¹⁶", "Cliff δ=0.934 very large"],
            ["A2C ≡ PPO CO₂ total", "Estadísticamente equivalentes", "p=0.982 NS", "Cohen d=−0.142 negligible"],
            ["A2C > PPO mototaxis", "Wilcoxon pareado W=994", "1.99×10⁻⁴ ✓", "Cohen d=0.318 small — DESEMPATE"],
            ["A2C > PPO BESS", "Mann-Whitney", "0.029 ✓", "Cohen d=−0.299 small"],
            ["A2C > PPO solar→EV", "Mann-Whitney", "0.019 ✓", "Cohen d=0.251 small"],
        ],
        "Tabla 8.1 — Evidencia estadística para selección A2C")
    h2(doc, "8.3 Ranking multiobjetivo — 9 criterios")
    agents_data = canon.get("agents", {})
    rows_rank = []
    for ag in AGENTS:
        ag_data = agents_data.get(ag, {})
        rows_rank.append([
            ag,
            f"{ag_data.get('co2_total_avoided_sum_50_kg', 0):,.0f}",
            f"{ag_data.get('f2_min_kg_per_year', 0):,.0f}",
            f"{ag_data.get('ev_total_equiv_count_50', 0):,.0f}",
            f"{ag_data.get('co2_reduction_vs_f0_pct', 0):.2f}%",
            str(ag_data.get("multiobj_score", "?")),
            "★ SELECCIONADO" if ag_data.get("selected") else "",
        ])
    table_simple(doc,
        ["Agente", "CO₂ evitado 50ep (kg)", "F2 mínimo (kg/año)", "EV equiv. 50ep",
         "Red. vs F0", "Score", ""],
        rows_rank,
        "Tabla 8.2 — Ranking multiobjetivo OE3 (50 episodios/agente)")
    h2(doc, "8.4 Figura comparativa final")
    fig(doc, GRAFICAS / "tabla_criterios_seleccion_oe3.png",
        "Figura 8.1 — Tabla canónica de criterios de selección OE3")
    doc.add_page_break()


def cap_conclusiones(doc: Document) -> None:
    h1(doc, "9. CONCLUSIONES")
    h2(doc, "9.1 Conclusión principal")
    body(doc,
         "El agente A2C (Advantage Actor-Critic) es el mejor para el control multiobjetivo "
         "de carga EV con solar PV + BESS en la red aislada de Iquitos, con evidencia "
         "estadística muy fuerte (Kruskal-Wallis H=91.62, p=1.27×10⁻²⁰).")
    h2(doc, "9.2 Hallazgos por objetivo")
    table_simple(doc,
        ["Hallazgo", "Evidencia", "Implicancia"],
        [
            ["A2C reduce 38.53% CO₂ vs F0 en 50 eps",
             "μ=2,460,341 kg/ep evitados (n=50, CV<0.5%)",
             "Viable para defensa de hipótesis H₁"],
            ["SAC descartado con evidencia extrema",
             "Cliff δ=0.970 (A2C>SAC), p=3.36×10⁻¹⁷",
             "SAC converge a plateau inferior (~1,464 vs ~1,676 reward)"],
            ["A2C=PPO en CO₂ total (empate estadístico)",
             "p=0.982 (NS), Cohen d=−0.142 negligible",
             "electricity_pricing (nuevo obs_dim=19) reduce ventaja A2C en CO₂ indirecto"],
            ["A2C gana en mototaxis vs PPO",
             "Wilcoxon p=1.99×10⁻⁴, Cohen d=0.318 small",
             "Criterio de desempate: satisfacción flota vulnerable"],
            ["A2C peak-shaving 3-7× superior a PPO",
             "HP grid: A2C 287-693 vs PPO 1,909-2,011 kWh/h",
             "BESS pre-cargado en solar, descarga en HP — control operativo superior"],
            ["Costo A2C: 2,426,823 S./año (no sig. vs PPO: 2,379,304)",
             "p=0.628 NS",
             "PPO menor costo, no significativo — no cambia selección"],
        ],
        "Tabla 9.1 — Conclusiones por hallazgo")
    h2(doc, "9.3 Limitaciones")
    body(doc,
         "• obs_dim=19 incluye electricity_pricing como señal observable — cambio vs run obs_dim=18 "
         "que podría afectar reproducibilidad con versiones anteriores.\n"
         "• SAC requiere ~205 min GPU vs ~22-24 min A2C/PPO — inviable para reentrenamiento frecuente.\n"
         "• n=50 episodios determinado por saturación estadística (CV<0.5%); "
         "mayor n podría detectar diferencias menores A2C vs PPO.")
    h2(doc, "9.4 Trabajo futuro")
    body(doc,
         "• Validación con datos meteorológicos 2025-2026 (actualmente usa TMY PVGIS 2024).\n"
         "• Prueba con obs_dim=19 en escenario Lima (SIN grid, carros eléctricos).\n"
         "• Comparativa con MAPPO/MASAC para control multi-agente distribuido.\n"
         "• Integración con hardware real (cargadores IoT, SCADA solar, BMS BESS).")
    doc.add_page_break()


def cap_anexos(doc: Document) -> None:
    h1(doc, "ANEXOS")
    h2(doc, "A. Configuración completa del entorno")
    table_simple(doc,
        ["Parámetro", "Valor"],
        [
            ["Python", "3.11.9"],
            ["stable-baselines3", "2.x"],
            ["CityLearn", "2.5.0"],
            ["PyTorch", "2.5.1+cu121"],
            ["GPU", "NVIDIA GeForce RTX 4060 Laptop (8.6 GB VRAM)"],
            ["CUDA", "12.1"],
            ["obs_dim", "19 (base=12 CityLearn + 5 EV + 2 tarifa)"],
            ["action_dim", "3 [bess(-1,1), motos_frac(0,1), mototaxis_frac(0,1)]"],
            ["VecNormalize", "norm_obs=True, norm_reward=True, clip_obs=10, clip_reward=10"],
            ["Semilla", "42 (random_seed schema + RNG bootstrap)"],
        ],
        "Tabla A.1 — Configuración del entorno de simulación")
    h2(doc, "B. Archivos generados")
    table_simple(doc,
        ["Archivo", "Ruta", "Contenido"],
        [
            ["agents_comparison_canonical.json", "reports/oe3/", "Ranking multiobjetivo canónico"],
            ["reporte_estadistico_oe3.md", "outputs/estadistica_oe3/", "Análisis estadístico 18 variables"],
            ["costos_estabilidad_consolidado.csv", "outputs/estadistica_oe3/", "Costos y estabilidad consolidados"],
            ["a2c_final.zip", "checkpoints/A2C_CityLearn/", "Modelo A2C entrenado"],
            ["ppo_final.zip", "checkpoints/PPO_CityLearn/", "Modelo PPO entrenado"],
            ["sac_final.zip", "checkpoints/SAC_CityLearn/", "Modelo SAC entrenado"],
            ["trace_a2c/ppo/sac.csv", "outputs/{ag}_training/", "Traza completa per-step"],
            ["timeseries_*.csv", "outputs/{ag}_training/", "Series temporales anuales"],
        ],
        "Tabla B.1 — Archivos generados por el pipeline")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("GENERANDO INFORME DE TESIS OE3 — pvbesscar")
    print(f"Fecha: {TODAY} | obs_dim=19 | CO2_DUAL_FOCUS v8.1")
    print("=" * 70)

    canon = load_canonical()
    sel   = canon.get("metadata", {}).get("selected_agent", "A2C")
    print(f"  Agente canonical: {sel}")

    doc = Document()
    # Márgenes
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3.0)
        section.right_margin  = Cm(2.5)

    cap_portada(doc, canon)
    cap_introduccion(doc)
    cap_metodologia(doc)
    cap_oe2(doc)
    cap_resultados_entrenamiento(doc, canon)
    cap_estadistica(doc)
    cap_costos_estabilidad(doc)
    cap_control_operativo(doc)
    cap_seleccion(doc, canon)
    cap_conclusiones(doc)
    cap_anexos(doc)

    out = OUT_DIR / "INFORME_OE3_SELECCION_AGENTE_RL_v12.docx"
    doc.save(str(out))
    size_mb = out.stat().st_size / 1e6
    print(f"\n  [OK] Informe generado: {out.relative_to(ROOT)}")
    print(f"  Tamaño: {size_mb:.1f} MB")
    print(f"  Capítulos: 9 + Anexos")
    print(f"  Agente seleccionado: {sel}")
    print("=" * 70)


if __name__ == "__main__":
    main()
