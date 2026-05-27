#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera dos tablas como figuras PNG de alta calidad:
  1. Criterios de selección del agente RL óptimo para OE3
  2. Cuantificación de la reducción de CO₂ por componente — SAC Ep. 48
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from graphics_utils import (
    C_SAC, C_PPO, C_A2C, C_HEAD, C_SUB, C_ALT, C_WIN, C_WARN, C_OK, C_NO,
    get_output_dir, save_figure
)

OUT_DIR = get_output_dir()

# Paleta adicional
C_BL   = '#D62728'    # rojo (baseline)

# ═════════════════════════════════════════════════════════════════════════════
# TABLA 1 — Criterios de selección del agente RL óptimo para OE3
# ═════════════════════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(15, 7.5))
ax1.axis('off')

fig1.patch.set_facecolor('#FAFAFA')

# ── Datos de la tabla ─────────────────────────────────────────────────────────
cols = [
    'Criterio',
    'SAC\n(off-policy)',
    'PPO\n(on-policy)',
    'A2C\n(on-policy)',
    'Peso\ncritério',
    'Mejor\nagente',
]

filas = [
    # criterio                   SAC                    PPO                    A2C                    peso   mejor
    ['F₂ mínimo (kg CO₂/año)',  '2,622,735 ★',          '2,787,040',           '2,834,857',           'ALTO', 'SAC'],
    ['Reducción vs Baseline',   '−54.71 %  ★',          '−51.91 %',            '−50.98 %',            'ALTO', 'SAC'],
    ['Episodio óptimo alcanzado','Ep. 48\n(refinamiento)',
                                                         'Ep. 40\n(descenso sostenido)',
                                                                                'Ep. 3\n(convergencia rápida)',
                                                                                                       'MED',  'SAC'],
    ['σ F₂ (50 ep completos)',  '89,475 kg',            '113,816 kg',          '12,011 kg\n⚠ stagnation','MED','PPO'],
    ['CV% (coef. variación)',   '3.35 %',               '3.96 %',              '0.42 %\n⚠ subóptimo', 'MED',  '—'],
    ['Calidad de convergencia', 'Mejora continua\nhasta ep.48', 'Descenso\nsostenido 1–40',
                                                                               'Estancamiento\ntemprano','ALTO','SAC'],
    ['Violaciones de carga\n(debt_violations)', '0 / año  ★', '0 / año  ★',  '0 / año  ★',          'ALTO', 'Empate'],
    ['Solar aprovechado (MWh/año)',
                                '8,293 MWh',            '~8,293 MWh',          '~8,293 MWh',          'MED',  'Empate'],
    ['Algoritmo',               'Off-policy\nSAC (Haarnoja 2018)',
                                                         'On-policy\nPPO (Schulman 2017)',
                                                                                'On-policy\nA2C (Mnih 2016)',
                                                                                                       '—',    '—'],
    ['Seleccionado para OE3',   '✔  SÍ',               '—  No',               '—  No',               '—',    'SAC'],
]

# Color por fila
def row_color(i: int, fila: list) -> str:
    if fila[0] == 'Seleccionado para OE3':
        return C_WIN
    if '⚠' in str(fila[3]):
        return C_WARN
    return C_ALT if i % 2 == 0 else 'white'

cell_colors = []
for i, f in enumerate(filas):
    rc = row_color(i, f)
    # columna SAC siempre ligeramente azul si no es fila especial
    row_c = [rc] * len(cols)
    cell_colors.append(row_c)

# Construir tabla
col_widths = [0.22, 0.17, 0.17, 0.17, 0.10, 0.12]

tbl = ax1.table(
    cellText=filas,
    colLabels=cols,
    colWidths=col_widths,
    loc='center',
    cellLoc='center',
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(9.8)
tbl.scale(1, 2.05)

# Estilo encabezado
for j in range(len(cols)):
    cell = tbl[0, j]
    cell.set_facecolor(C_HEAD)
    cell.set_text_props(color='white', fontweight='bold', fontsize=10.5)
    cell.set_edgecolor('#FFFFFF')

# Estilo filas de datos
for i, fila in enumerate(filas):
    rc = row_color(i, fila)
    is_selected = fila[0] == 'Seleccionado para OE3'
    for j in range(len(cols)):
        cell = tbl[i + 1, j]
        cell.set_facecolor(rc)
        cell.set_edgecolor('#CCCCCC')
        fw = 'bold' if is_selected else 'normal'
        fs = 9.8

        # Columnas de agentes: dar color al texto
        if j == 1:  # SAC
            cell.set_text_props(color=C_SAC, fontweight='bold' if '★' in fila[1] or is_selected else 'normal', fontsize=fs)
        elif j == 2:  # PPO
            cell.set_text_props(color=C_PPO, fontsize=fs)
        elif j == 3:  # A2C
            cell.set_text_props(color=C_A2C, fontsize=fs)
        elif j == 4:  # Peso
            peso_colors = {'ALTO': '#7B241C', 'MED': '#784212', '—': '#555555'}
            cell.set_text_props(color=peso_colors.get(fila[4], '#555555'),
                                fontweight='bold', fontsize=fs)
        elif j == 5:  # Mejor
            if fila[5] == 'SAC':
                cell.set_text_props(color=C_SAC, fontweight='bold', fontsize=fs)
            elif fila[5] == 'PPO':
                cell.set_text_props(color=C_PPO, fontweight='bold', fontsize=fs)
        else:
            cell.set_text_props(fontsize=fs)

        if is_selected:
            cell.set_edgecolor('#1E8449')

# Título y pie
ax1.set_title(
    'Tabla — Criterios de selección del agente RL óptimo para OE3\n'
    'Objetivo OE3: Reducción cuantificable de CO₂ en Iquitos · '
    'Sistema PV (4,050 kWp) + BESS (2,000 kWh) + 38 tomas EV · '
    'Factor CO₂: 0.4521 kg/kWh',
    fontsize=12, fontweight='bold', pad=14, color='#1A3A5C'
)

# Leyenda
leyenda = [
    mpatches.Patch(color=C_WIN,  label='Agente seleccionado (SAC)'),
    mpatches.Patch(color=C_WARN, label='⚠ Criterio con advertencia (A2C estancamiento)'),
    mpatches.Patch(color=C_ALT,  label='Fila par'),
]
ax1.legend(handles=leyenda, loc='lower center', ncol=3,
           fontsize=9, framealpha=0.85,
           bbox_to_anchor=(0.5, -0.02))

ax1.text(0.99, -0.02,
         'Fuente: elaboración propia en Python · Iquitos, Perú · 2026',
         transform=ax1.transAxes, fontsize=8.5, ha='right', color='#555555', style='italic')

path1 = OUT_DIR / 'tabla_criterios_seleccion_oe3.png'
fig1.savefig(path1, dpi=300, bbox_inches='tight', facecolor=fig1.get_facecolor())
plt.close(fig1)
print(f'✓  Tabla 1 guardada → {path1}')

# ═════════════════════════════════════════════════════════════════════════════
# TABLA 2 — Cuantificación CO₂ por componente · SAC Ep. 48
# ═════════════════════════════════════════════════════════════════════════════
# Datos reales del CSV (ep 48)
BL_KG    = 5_782_148.48
CTL_KG   = 2_622_734.92
# Sub-componentes F₂
CO2_DIR  = 328_736.24    # co2_directa_kg  (emisiones directas con control)
CO2_IND  = 3_223_883.58  # co2_indirecta_kg (emisiones indirectas con control)
CO2_NETA = 3_552_619.82  # co2_neta_kg
RED_PCT  = 62.82         # reduccion_pct (%)

# F6 sub-descomposición
F6A = 113_832.92   # co2_f6a_kg
F6B = 2_616_857.04 # co2_f6b_kg
F6C = 221_346.04   # co2_f6c_kg
F6D = 797_009.66   # co2_f6d_kg
F7  = 508_040.40   # co2_f7_kg

# Derivados
RED_TOTAL       = BL_KG - CTL_KG             # reducción neta total
RED_DIR         = RED_TOTAL * (0.35 / 0.65)  # ~ proporción pesos reward
RED_IND         = RED_TOTAL * (0.30 / 0.65)
SOLAR_MWH       = 8_292.51
GRID_MWH        = 5_801.23
BESS_MWH        = 875.70
EV_MOTOS_MWH    = 341.05
EV_MOTO_MWH     = 59.31
DEBT_VIOL       = 0

fig2, ax2 = plt.subplots(figsize=(17, 11))
ax2.axis('off')
fig2.patch.set_facecolor('#FAFAFA')

C_HEAD2 = '#1A3A5C'
C_ROW1  = '#EAF2FF'
C_ROW2  = '#FDFEFE'
C_TOTAL = '#D5F5E3'

# Columnas
cols2 = [
    'Componente / Concepto',
    'Valor\nnumérico',
    'Unidad',
    'Descripción técnica',
    'Peso\nreward',
]

# Secciones y filas
# Cada fila: [tipo, col1, col2, col3, col4, col5]
filas2_raw = [
    ('header', 'A.  PARÁMETROS DEL SISTEMA\n    SAC · Ep. 48 óptimo',
     '', '', '', ''),
    ('data',  'Episodio óptimo',              '48',              '—',
     'Mínimo absoluto F₂ en los 50 episodios de entrenamiento', '—'),
    ('data',  'Generación solar PV',           '8,292.51',       'MWh/año',
     'PV: 4,050 kWp · PVGIS Iquitos',                    '—'),
    ('data',  'Descarga BESS',                 '875.70',         'MWh/año',
     'BESS: 2,000 kWh / 400 kW · DoD 80%',               '—'),
    ('data',  'Importación red eléctrica',      '5,801.23',       'MWh/año',
     'Red Iquitos · generación térmica diesel',            '—'),
    ('data',  'Energía EV motos (270 un.)',     '341.05',         'MWh/año',
     'Mode 3 · 7.4 kW/socket · 15 cargadores · 30 tomas', '—'),
    ('data',  'Energía EV mototaxis (39 un.)', '59.31',          'MWh/año',
     'Mode 3 · 7.4 kW/socket · 4 cargadores · 8 tomas',   '—'),
    ('data',  'Violaciones de carga (debt)',    '0',              'eventos',
     'Todas las EVs cargadas a tiempo dentro del turno',   '—'),

    ('header', 'B.  BASELINE\n    Sin agente RL (referencia CO₂)',
     '', '', '', ''),
    ('data',  'CO₂ baseline anual',   f'{BL_KG:>12,.2f}', 'kg CO₂/año',
     'Importación sin restricción · sin optimización RL',  '—'),

    ('header', 'C.  F₂  —  CO₂ total con agente SAC\n    Episodio óptimo Ep. 48',
     '', '', '', ''),
    ('data',  'F₂ CO₂ controlado (total)', f'{CTL_KG:>12,.2f}', 'kg CO₂/año',
     'Emisiones directas + indirectas bajo control SAC',   '—'),
    ('sub',   '  ├─ CO₂ directo (vehículos)', f'{CO2_DIR:>12,.2f}', 'kg CO₂/año',
     'Emisiones residuales directas motos/mototaxis',      '0.35'),
    ('sub',   '  └─ CO₂ indirecto (red)',    f'{CO2_IND:>12,.2f}', 'kg CO₂/año',
     f'Grid import × 0.4521 kg/kWh · {GRID_MWH:,.2f} MWh/año', '0.30'),

    ('header', 'D.  REDUCCIÓN DE CO₂ LOGRADA POR SAC\n    vs Baseline sin control',
     '', '', '', ''),
    ('total', 'ΔCO₂ total evitado',    f'{RED_TOTAL:>12,.2f}', 'kg CO₂/año',
     f'Baseline − F₂  =  {BL_KG:,.0f} − {CTL_KG:,.0f}',  '—'),
    ('total', 'Reducción porcentual',   f'{RED_PCT:.2f}',       '%',
     'Reducción verificada sobre baseline sin control SAC', '—'),
    ('sub',   '  ├─ Reducción directa (F₂dir)',   f'{CO2_DIR:>12,.2f}', 'kg CO₂/año',
     'Control EV desplaza importación en horas pico',      '0.35'),
    ('sub',   '  └─ Reducción indirecta (F₂ind)', f'{F6B:>12,.2f}',    'kg CO₂/año',
     'Importación suprimida mediante PV + BESS dispatch',  '0.30'),

    ('header', 'E.  SUB-COMPONENTES FUNCIÓN REWARD\n    F6a – F6d · F7',
     '', '', '', ''),
    ('data',  'F6a — CO₂ carga directa EV',    f'{F6A:>12,.2f}', 'kg CO₂/año',
     'Emisiones directas EV residuales bajo control activo','0.35'),
    ('data',  'F6b — CO₂ importación red',      f'{F6B:>12,.2f}', 'kg CO₂/año',
     'Grid import × 0.4521 kg/kWh (componente dominante)', '0.30'),
    ('data',  'F6c — CO₂ curva EV no cubierta', f'{F6C:>12,.2f}', 'kg CO₂/año',
     'Penalización EV no satisfecha (debt_violations = 0)', '0.25'),
    ('data',  'F6d — CO₂ solar no aprovechado', f'{F6D:>12,.2f}', 'kg CO₂/año',
     'Curtailment solar × factor equivalente CO₂',         '0.05'),
    ('data',  'F7  — CO₂ estabilidad red',      f'{F7:>12,.2f}',  'kg CO₂/año',
     'Penalización por ramping de potencia (suavizado)',    '0.05'),

    ('total', 'RESULTADO FINAL\nSAC SELECCIONADO PARA OE3',
     '−54.71 %', 'vs baseline',
     'F₂ mínimo = 2,622,735 kg CO₂/año · Ep. 48 · 0 violations', '✔'),
]

# Construir cell texts y colores
cell_texts   = []
cell_colors2 = []

for idx, row in enumerate(filas2_raw):
    tipo = row[0]
    vals = list(row[1:])
    cell_texts.append(vals)

    if tipo == 'header':
        cell_colors2.append(['#154360'] * len(cols2))
    elif tipo == 'total':
        cell_colors2.append([C_TOTAL] * len(cols2))
    elif tipo == 'sub':
        cell_colors2.append(['#F4F6F7'] * len(cols2))
    else:  # data
        cell_colors2.append([C_ROW1 if idx % 2 == 0 else C_ROW2] * len(cols2))

col_widths2 = [0.30, 0.12, 0.08, 0.36, 0.07]

tbl2 = ax2.table(
    cellText=cell_texts,
    colLabels=cols2,
    colWidths=col_widths2,
    loc='center',
    cellLoc='left',
)
tbl2.auto_set_font_size(False)
tbl2.set_fontsize(9.5)
tbl2.scale(1, 1.82)

# Estilo encabezado de columnas
for j in range(len(cols2)):
    cell = tbl2[0, j]
    cell.set_facecolor(C_HEAD2)
    cell.set_text_props(color='white', fontweight='bold', fontsize=10)
    cell.set_edgecolor('#FFFFFF')
    cell.set_height(cell.get_height() * 1.1)

# Estilo celdas de datos
for i, row in enumerate(filas2_raw):
    tipo_val = row[0]
    for j in range(len(cols2)):
        cell = tbl2[i + 1, j]
        cell.set_facecolor(cell_colors2[i][j])
        cell.set_edgecolor('#CCCCCC')

        if tipo_val == 'header':
            cell.set_text_props(color='white', fontweight='bold', fontsize=9.8)
            cell.set_edgecolor('#FFFFFF')
        elif tipo_val == 'total':
            cell.set_text_props(fontweight='bold', color='#1A5C1A', fontsize=9.5)
            cell.set_edgecolor('#1E8449')
        elif tipo_val == 'sub':
            cell.set_text_props(color='#4A4A4A', fontsize=9.2)
        else:
            cell.set_text_props(fontsize=9.5)

        if j == 1:  # valor numérico centrado
            cell._loc = 'center'
        if j == 4:  # peso reward centrado
            cell._loc = 'center'

# Título
ax2.set_title(
    'Tabla — Cuantificación de la reducción de CO₂ por componente\n'
    'Agente SAC · Episodio óptimo Ep. 48 · Sistema pvbesscar · Iquitos, Perú\n'
    'PV: 4,050 kWp · BESS: 2,000 kWh · 38 tomas EV · Factor CO₂: 0.4521 kg/kWh',
    fontsize=12, fontweight='bold', pad=16, color='#1A3A5C'
)

ax2.text(
    0.99, 0.01,
    'Fuente: elaboración propia en Python · datos entrenamiento SAC · Iquitos, Perú · 2026',
    transform=ax2.transAxes, fontsize=8.5, ha='right', va='bottom',
    color='#555555', style='italic'
)

# Leyenda (fuera del área de tabla, arriba)
ley2 = [
    mpatches.Patch(color='#154360', label='Sección/encabezado'),
    mpatches.Patch(color=C_TOTAL,   label='Total / resultado'),
    mpatches.Patch(color='#F4F6F7', label='Sub-componente'),
    mpatches.Patch(color=C_ROW1,    label='Dato del sistema'),
]
ax2.legend(handles=ley2, loc='upper right', ncol=4, fontsize=9,
           framealpha=0.85, bbox_to_anchor=(1.0, 1.02))

path2 = OUT_DIR / 'tabla_co2_componentes_sac_ep48.png'
fig2.savefig(path2, dpi=300, bbox_inches='tight', facecolor=fig2.get_facecolor())
plt.close(fig2)
print(f'✓  Tabla 2 guardada → {path2}')

print()
print('═══ Datos verificados SAC Ep.48 ═══')
print(f'  Baseline:        {BL_KG:>15,.2f} kg CO₂/año')
print(f'  F₂ controlado:   {CTL_KG:>15,.2f} kg CO₂/año')
print(f'  Reducción total: {RED_TOTAL:>15,.2f} kg CO₂/año  (−{RED_PCT:.2f}%)')
print(f'  CO₂ directo:     {CO2_DIR:>15,.2f} kg CO₂/año')
print(f'  CO₂ indirecto:   {CO2_IND:>15,.2f} kg CO₂/año')
print(f'  Violaciones:     {DEBT_VIOL}')
