#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISIS DE BASELINES - Comparación: Sin Control vs Con Control PPO
====================================================================

Baselines calculados:
  1. BASELINE 0: Sin Solar, sin BESS, sin RL (solo grid térmico)
  2. BASELINE 1: Con Solar, sin BESS, sin RL (carga manual/fija)
  3. BASELINE 2 (PPO): Con Solar, con BESS, con RL (control inteligente)

Año: 2024-2025 (Iquitos, Perú)
Sistema: 270 motos + 39 mototaxis cargadas diariamente
"""
import json
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONSTANTES Y FACTORES
# ============================================================================

REPORTS_DIR = Path('reports/mejoragent')

# Factor de emisión grid Iquitos
CO2_GRID_FACTOR = 0.4521  # kg CO2/kWh

# Factores EV
EV_MOTOS_CONSUMO = 0.15  # kWh/km
EV_MOTOTAXIS_CONSUMO = 0.20  # kWh/km
EV_MOTOS_KM_DIARIOS = 60  # km/día
EV_MOTOTAXIS_KM_DIARIOS = 80  # km/día

# Consumo energético EVs
MOTOS_CONSUMO_DIARIO = EV_MOTOS_KM_DIARIOS * EV_MOTOS_CONSUMO  # kWh/día
MOTOTAXIS_CONSUMO_DIARIO = EV_MOTOTAXIS_KM_DIARIOS * EV_MOTOTAXIS_CONSUMO  # kWh/día

# Flotas
MOTOS_DIARIAS = 270
MOTOTAXIS_DIARIOS = 39

# Consumo total diario
TOTAL_CONSUMO_DIARIO_KWH = (MOTOS_DIARIAS * MOTOS_CONSUMO_DIARIO + 
                             MOTOTAXIS_DIARIOS * MOTOTAXIS_CONSUMO_DIARIO)

# Consumo anual
TOTAL_CONSUMO_ANUAL_KWH = TOTAL_CONSUMO_DIARIO_KWH * 365

# ============================================================================
# DATOS PPO (desde entrenamienito)
# ============================================================================

ppo_result_file = Path('outputs/ppo_training/result_ppo.json')
with open(ppo_result_file) as f:
    ppo_data = json.load(f)

ppo_summary = ppo_data.get('summary_metrics', {})
ppo_co2_directo = ppo_summary.get('total_co2_avoided_direct_kg', 0)
ppo_co2_indirecto = ppo_summary.get('total_co2_avoided_indirect_kg', 0)
ppo_solar_kwh = sum(ppo_data.get('training_evolution', {}).get('episode_solar_kwh', []))
ppo_grid_kwh = sum(ppo_data.get('training_evolution', {}).get('episode_grid_import', []))

# ============================================================================
# BASELINES CALCULADOS
# ============================================================================

report = []

report.append('=' * 110)
report.append('ANÁLISIS COMPLETO DE BASELINES: Sin Control vs Con Control PPO')
report.append('=' * 110)
report.append(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
report.append('')

# ============================================================================
# SECCIÓN 1: DATOS DE ENTRADA
# ============================================================================

report.append('=' * 110)
report.append('1. DATOS DE ENTRADA Y CONFIGURACIÓN')
report.append('=' * 110)
report.append('')

report.append('1.1 FLOTA Y CONSUMO DIARIO')
report.append('-' * 110)
report.append('')
report.append(f'Motos:')
report.append(f'  • Cantidad diaria: {MOTOS_DIARIAS}')
report.append(f'  • km/día: {EV_MOTOS_KM_DIARIOS}')
report.append(f'  • Consumo específico: {EV_MOTOS_CONSUMO} kWh/km')
report.append(f'  • Consumo diario: {MOTOS_CONSUMO_DIARIO:.2f} kWh')
report.append(f'  • Consumo anual: {MOTOS_CONSUMO_DIARIO * 365:>14,.2f} kWh')
report.append('')

report.append(f'Mototaxis:')
report.append(f'  • Cantidad diaria: {MOTOTAXIS_DIARIOS}')
report.append(f'  • km/día: {EV_MOTOTAXIS_KM_DIARIOS}')
report.append(f'  • Consumo específico: {EV_MOTOTAXIS_CONSUMO} kWh/km')
report.append(f'  • Consumo diario: {MOTOTAXIS_CONSUMO_DIARIO:.2f} kWh')
report.append(f'  • Consumo anual: {MOTOTAXIS_CONSUMO_DIARIO * 365:>14,.2f} kWh')
report.append('')

report.append(f'TOTAL FLOTA:')
report.append(f'  • Consumo diario: {TOTAL_CONSUMO_DIARIO_KWH:>14,.2f} kWh/día')
report.append(f'  • Consumo anual: {TOTAL_CONSUMO_ANUAL_KWH:>14,.2f} kWh/año')
report.append('')
report.append('')

report.append('1.2 FACTORES DE EMISIÓN')
report.append('-' * 110)
report.append('')
report.append(f'Grid Iquitos (térmico):')
report.append(f'  • Factor CO2: {CO2_GRID_FACTOR} kg CO2/kWh')
report.append(f'  • Fuente: Operadora RED (2024-2025)')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 2: BASELINE 0 - SIN SOLAR, SIN BESS, SIN RL
# ============================================================================

report.append('=' * 110)
report.append('2. BASELINE 0: Sin Solar, Sin BESS, Sin RL (Grid 100%)')
report.append('=' * 110)
report.append('')

report.append('DESCRIPCIÓN:')
report.append('  Escenario: Carga totalmente desde grid térmico (estado actual)')
report.append('  Supuesto: No hay control inteligente, no hay solar, no hay BESS')
report.append('')

# Baseline 0: Todo desde grid
baseline0_consumo_kwh = TOTAL_CONSUMO_ANUAL_KWH
baseline0_co2_kg = baseline0_consumo_kwh * CO2_GRID_FACTOR
baseline0_co2_tco2 = baseline0_co2_kg / 1000

report.append(f'RESULTADOS BASELINE 0:')
report.append(f'  • Consumo de energía: {baseline0_consumo_kwh:>14,.2f} kWh/año')
report.append(f'  • Fuente: 100% Grid térmico')
report.append(f'  • CO2 Emitido: {baseline0_co2_kg:>14,.0f} kg')
report.append(f'  • CO2 Emitido: {baseline0_co2_tco2:>14,.0f} tCO2/año')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 3: BASELINE 1 - CON SOLAR, SIN BESS, SIN RL
# ============================================================================

report.append('=' * 110)
report.append('3. BASELINE 1: Con Solar, Sin BESS, Sin RL (Carga Manual)')
report.append('=' * 110)
report.append('')

report.append('DESCRIPCIÓN:')
report.append('  Escenario: Solar disponible pero sin control inteligente')
report.append('  Supuesto: Solo carga cuando hay solar (simple/manual), sin BESS')
report.append('')

# Baseline 1: Asumimos 40% del consumo desde solar (sin optimización)
solar_ratio_simple = 0.40
baseline1_solar_kwh = baseline0_consumo_kwh * solar_ratio_simple
baseline1_grid_kwh = baseline0_consumo_kwh * (1 - solar_ratio_simple)
baseline1_co2_kg = baseline1_grid_kwh * CO2_GRID_FACTOR
baseline1_co2_tco2 = baseline1_co2_kg / 1000

report.append(f'RESULTADOS BASELINE 1:')
report.append(f'  • Consumo total: {baseline0_consumo_kwh:>14,.2f} kWh/año')
report.append(f'  • Desde solar: {baseline1_solar_kwh:>14,.2f} kWh ({solar_ratio_simple*100:.0f}%, sin optimización)')
report.append(f'  • Desde grid: {baseline1_grid_kwh:>14,.2f} kWh ({(1-solar_ratio_simple)*100:.0f}%)')
report.append(f'  • CO2 Emitido: {baseline1_co2_kg:>14,.0f} kg')
report.append(f'  • CO2 Emitido: {baseline1_co2_tco2:>14,.0f} tCO2/año')
report.append('')

# Mejora B1 vs B0
mejora_b1_vs_b0_kg = baseline0_co2_kg - baseline1_co2_kg
mejora_b1_vs_b0_pct = (mejora_b1_vs_b0_kg / baseline0_co2_kg) * 100

report.append(f'MEJORA vs BASELINE 0:')
report.append(f'  • CO2 Reducido: {mejora_b1_vs_b0_kg:>14,.0f} kg')
report.append(f'  • % Reducción: {mejora_b1_vs_b0_pct:>14.2f}%')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 4: BASELINE 2 - CON SOLAR, CON BESS, CON RL (PPO)
# ============================================================================

report.append('=' * 110)
report.append('4. BASELINE 2: Con Solar, Con BESS, Con RL (Control Inteligente PPO)')
report.append('=' * 110)
report.append('')

report.append('DESCRIPCIÓN:')
report.append('  Escenario: Control inteligente con PPO')
report.append('  Supuesto: Maximiza solar, usa BESS para peak-shaving, RL optimiza carga')
report.append('')

# Baseline 2: PPO con datos reales
# Desde 10 episodios (10 días simulados)
# El ratio de solar/grid nos dice qué proporción se cubre desde cada fuente

# Calcular ratio solar/grid del PPO (datos de 10 episodios)
total_energy_10dias = ppo_solar_kwh + ppo_grid_kwh
ppo_solar_ratio = ppo_solar_kwh / total_energy_10dias if total_energy_10dias > 0 else 0
ppo_grid_ratio = ppo_grid_kwh / total_energy_10dias if total_energy_10dias > 0 else 0

# Aplicar estos ratios al consumo total anual
ppo_solar_annual = baseline0_consumo_kwh * ppo_solar_ratio
ppo_grid_annual = baseline0_consumo_kwh * ppo_grid_ratio
ppo_co2_annual_from_grid = ppo_grid_annual * CO2_GRID_FACTOR

# Proyectar CO2 evitado anually (10 dias → 365 días)
ppo_co2_anual_kg = (ppo_co2_directo + ppo_co2_indirecto) * 36.5
ppo_co2_anual_tco2 = ppo_co2_anual_kg / 1000

report.append(f'RESULTADOS BASELINE 2 (PPO):')
report.append(f'  • Consumo total: {baseline0_consumo_kwh:>14,.2f} kWh/año')
report.append(f'  • Desde solar: {ppo_solar_annual:>14,.2f} kWh ({(ppo_solar_annual/baseline0_consumo_kwh)*100:>6.2f}%, optimizado)')
report.append(f'  • Desde grid: {ppo_grid_annual:>14,.2f} kWh ({(ppo_grid_annual/baseline0_consumo_kwh)*100:>6.2f}%)')
report.append(f'  • CO2 Emitido (grid): {ppo_co2_annual_from_grid:>14,.0f} kg')
report.append(f'  • CO2 Evitado (total): {ppo_co2_anual_kg:>14,.0f} kg')
report.append(f'  • CO2 Neto: {ppo_co2_annual_from_grid - ppo_co2_anual_kg:>14,.0f} kg (reducción neta)')
report.append('')

report.append(f'Desglose de emisiones evitadas:')
report.append(f'  • Directo (EV): {ppo_co2_directo * 36.5:>14,.0f} kg')
report.append(f'  • Indirecto (Solar/BESS): {ppo_co2_indirecto * 36.5:>14,.0f} kg')
report.append(f'  • TOTAL: {ppo_co2_anual_kg:>14,.0f} kg')
report.append('')

# Mejora B2 vs B0
mejora_b2_vs_b0_kg = baseline0_co2_kg - ppo_co2_annual_from_grid
mejora_b2_vs_b0_pct = (mejora_b2_vs_b0_kg / baseline0_co2_kg) * 100

report.append(f'MEJORA vs BASELINE 0 (Sin Solar):')
report.append(f'  • CO2 Reducido: {mejora_b2_vs_b0_kg:>14,.0f} kg')
report.append(f'  • % Reducción: {mejora_b2_vs_b0_pct:>14.2f}%')
report.append('')

# Mejora B2 vs B1
mejora_b2_vs_b1_kg = baseline1_co2_kg - ppo_co2_annual_from_grid
mejora_b2_vs_b1_pct = (mejora_b2_vs_b1_kg / baseline1_co2_kg) * 100 if baseline1_co2_kg > 0 else 0

report.append(f'MEJORA vs BASELINE 1 (Carga Manual):')
report.append(f'  • CO2 Reducido: {mejora_b2_vs_b1_kg:>14,.0f} kg')
report.append(f'  • % Reducción: {mejora_b2_vs_b1_pct:>14.2f}%')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 5: COMPARATIVA RESUMIDA
# ============================================================================

report.append('=' * 110)
report.append('5. COMPARATIVA RESUMIDA: BASELINES 0, 1 Y 2')
report.append('=' * 110)
report.append('')

report.append('Escenario                              Solar  BESS   RL   | CO2 Anual (kg)    CO2 (tCO2)   % vs B0')
report.append('─' * 110)
report.append(f'B0: Sin Solar, Sin BESS, Sin RL        NO    NO    NO   | {baseline0_co2_kg:>17,.0f} {baseline0_co2_tco2:>10,} 100.00%')
report.append(f'B1: Con Solar, Sin BESS, Sin RL        SÍ    NO    NO   | {baseline1_co2_kg:>17,.0f} {baseline1_co2_tco2:>10,} {(baseline1_co2_kg/baseline0_co2_kg)*100:>6.2f}%')
report.append(f'B2: Con Solar, Con BESS, Con RL (PPO) SÍ    SÍ    SÍ   | {ppo_co2_annual_from_grid:>17,.0f} {ppo_co2_annual_from_grid/1000:>10,.0f} {(ppo_co2_annual_from_grid/baseline0_co2_kg)*100:>6.2f}%')
report.append('═' * 110)
report.append('')

# Ganancias
report.append(f'GANANCIAS POR CADA MEJORA:')
report.append(f'  • B1 - B0 (Solo Solar): {mejora_b1_vs_b0_kg:>14,.0f} kg ({mejora_b1_vs_b0_pct:>6.2f}%)')
report.append(f'  • B2 - B1 (PPO + BESS): {mejora_b2_vs_b1_kg:>14,.0f} kg ({mejora_b2_vs_b1_pct:>6.2f}%)')
report.append(f'  • B2 - B0 (Total): {mejora_b2_vs_b0_kg:>14,.0f} kg ({mejora_b2_vs_b0_pct:>6.2f}%)')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 6: ANÁLISIS POR COMPONENTE
# ============================================================================

report.append('=' * 110)
report.append('6. ANÁLISIS POR COMPONENTE: CONTRIBUCIÓN DE CADA FACTOR')
report.append('=' * 110)
report.append('')

report.append('6.1 CONTRIBUCIÓN SOLAR')
report.append('-' * 110)
report.append('')
report.append(f'B1 (Carga manual):')
report.append(f'  • Solar utilizado: {baseline1_solar_kwh:>14,.2f} kWh ({solar_ratio_simple*100:.1f}%)')
report.append(f'  • CO2 evitado: {baseline1_solar_kwh * CO2_GRID_FACTOR:>14,.0f} kg')
report.append('')

report.append(f'B2 (Carga inteligente PPO):')
report.append(f'  • Solar utilizado: {ppo_solar_annual:>14,.2f} kWh ({(ppo_solar_annual/baseline0_consumo_kwh)*100:.1f}%)')
report.append(f'  • CO2 evitado (solar): {ppo_solar_annual * CO2_GRID_FACTOR:>14,.0f} kg')
report.append(f'  • Mejora sobre B1: {(ppo_solar_annual - baseline1_solar_kwh) * CO2_GRID_FACTOR:>14,.0f} kg')
report.append('')
report.append('')

report.append('6.2 CONTRIBUCIÓN BESS + CONTROL INTELIGENTE')
report.append('-' * 110)
report.append('')
report.append(f'PPO (B2 vs B1 sin BESS):')
report.append(f'  • Mejora por optimización: {mejora_b2_vs_b1_kg:>14,.0f} kg')
report.append(f'  • % adicional: {mejora_b2_vs_b1_pct:>22.2f}%')
report.append(f'  • Causas:')
report.append(f'    - Peak-shaving con BESS')
report.append(f'    - Timing óptimo de carga (RL)')
report.append(f'    - Balanceo EV vs red')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 7: EQUIVALENCIAS Y CONTEXTO
# ============================================================================

report.append('=' * 110)
report.append('7. EQUIVALENCIAS: IMPACTO EN TÉRMINOS REALES')
report.append('=' * 110)
report.append('')

# Árboles
arboles_b0 = baseline0_co2_kg / 21
arboles_b1 = baseline1_co2_kg / 21
arboles_b2 = ppo_co2_annual_from_grid / 21

report.append(f'Árboles plantados (equivalencia CO2):')
report.append(f'  • B0: {arboles_b0:>8,.0f} árboles')
report.append(f'  • B1: {arboles_b1:>8,.0f} árboles')
report.append(f'  • B2: {arboles_b2:>8,.0f} árboles')
report.append('')

# Autos removidos
autos_b0 = baseline0_co2_kg / (4600)  # 4.6 ton CO2/auto/año
autos_b1 = baseline1_co2_kg / (4600)
autos_b2 = ppo_co2_annual_from_grid / (4600)

report.append(f'Autos sacados de circulación (equivalencia):')
report.append(f'  • B0: {autos_b0:>8,.0f} autos')
report.append(f'  • B1: {autos_b1:>8,.0f} autos')
report.append(f'  • B2: {autos_b2:>8,.0f} autos')
report.append('')

# Hogares
hogares_b0 = baseline0_co2_kg / (4500)  # 4.5 ton CO2/household/year
hogares_b1 = baseline1_co2_kg / (4500)
hogares_b2 = ppo_co2_annual_from_grid / (4500)

report.append(f'Hogares con electricidad limpia (equivalencia):')
report.append(f'  • B0: {hogares_b0:>8,.0f} hogares')
report.append(f'  • B1: {hogares_b1:>8,.0f} hogares')
report.append(f'  • B2: {hogares_b2:>8,.0f} hogares')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 8: CONCLUSIONES
# ============================================================================

report.append('=' * 110)
report.append('8. CONCLUSIONES Y RECOMENDACIONES')
report.append('=' * 110)
report.append('')

report.append('8.1 ANÁLISIS PROGRESIVO')
report.append('')
report.append(f'✅ BASELINE 0 → BASELINE 1 (Solo Solar):')
report.append(f'   Reducción: {mejora_b1_vs_b0_kg/1e6:.2f}M kg CO2 ({mejora_b1_vs_b0_pct:.2f}%)')
report.append(f'   Conclusión: Solar aporta mejora significativa, pero sin control es subóptimo.')
report.append('')

report.append(f'✅ BASELINE 1 → BASELINE 2 (Agregando BESS + RL):')
report.append(f'   Reducción adicional: {mejora_b2_vs_b1_kg/1e6:.2f}M kg CO2 ({mejora_b2_vs_b1_pct:.2f}%)')
report.append(f'   Conclusión: Control inteligente PPO optimiza carga y timing.')
report.append('')

report.append(f'✅ BASELINE 0 → BASELINE 2 (Mejora Total):')
report.append(f'   Reducción: {mejora_b2_vs_b0_kg/1e6:.2f}M kg CO2 ({mejora_b2_vs_b0_pct:.2f}%)')
report.append(f'   Conclusión: Combinación de solar + BESS + RL es óptima.')
report.append('')

report.append('8.2 RECOMENDACIONES')
report.append('')
report.append('1. IMPLEMENTAR BASELINE 2 (PPO) como estándar operacional')
report.append('2. MONITOREAR desempeño vs baselines en tiempo real')
report.append('3. ESCALAR a 100% de flota en 12-24 meses')
report.append('4. EXPANDIR solar PV de 4,050 kWp → 8,000+ kWp')
report.append('')

# Guardar reporte
output_file = REPORTS_DIR / '4_6_4_BASELINES_ANALISIS_COMPLETO.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n'.join(report))
print(f'\n✅ Reporte guardado: {output_file}')

# ============================================================================
# GUARDAR DATOS EN JSON
# ============================================================================

baselines_data = {
    'timestamp': datetime.now().isoformat(),
    'baseline_0': {
        'descripcion': 'Sin Solar, Sin BESS, Sin RL (Grid 100%)',
        'consumo_kwh_anual': float(baseline0_consumo_kwh),
        'co2_kg': float(baseline0_co2_kg),
        'co2_tco2': float(baseline0_co2_tco2),
        'nota': 'Estado actual de Iquitos'
    },
    'baseline_1': {
        'descripcion': 'Con Solar, Sin BESS, Sin RL (Carga manual)',
        'solar_kwh_anual': float(baseline1_solar_kwh),
        'grid_kwh_anual': float(baseline1_grid_kwh),
        'solar_ratio': float(solar_ratio_simple),
        'co2_kg': float(baseline1_co2_kg),
        'co2_tco2': float(baseline1_co2_tco2),
        'mejora_vs_b0_kg': float(mejora_b1_vs_b0_kg),
        'mejora_vs_b0_pct': float(mejora_b1_vs_b0_pct),
    },
    'baseline_2_ppo': {
        'descripcion': 'Con Solar, Con BESS, Con RL (Control inteligente)',
        'solar_kwh_anual': float(ppo_solar_annual),
        'grid_kwh_anual': float(ppo_grid_annual),
        'solar_ratio': float(ppo_solar_ratio),
        'co2_from_grid_kg': float(ppo_co2_annual_from_grid),
        'co2_evitado_kg': float(ppo_co2_anual_kg),
        'co2_evitado_directo_kg': float(ppo_co2_directo * 36.5),
        'co2_evitado_indirecto_kg': float(ppo_co2_indirecto * 36.5),
        'mejora_vs_b0_kg': float(mejora_b2_vs_b0_kg),
        'mejora_vs_b0_pct': float(mejora_b2_vs_b0_pct),
        'mejora_vs_b1_kg': float(mejora_b2_vs_b1_kg),
        'mejora_vs_b1_pct': float(mejora_b2_vs_b1_pct),
    },
    'resumen': {
        'b0_co2_kg': float(baseline0_co2_kg),
        'b1_co2_kg': float(baseline1_co2_kg),
        'b2_co2_kg': float(ppo_co2_annual_from_grid),
        'total_reduction_b0_to_b2_kg': float(mejora_b2_vs_b0_kg),
        'total_reduction_b0_to_b2_pct': float(mejora_b2_vs_b0_pct),
        'solar_impact_kg': float(mejora_b1_vs_b0_kg),
        'ppo_bess_impact_kg': float(mejora_b2_vs_b1_kg),
    }
}

json_file = REPORTS_DIR / '4_6_4_BASELINES_DATA.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(baselines_data, f, indent=2, ensure_ascii=False)

print(f'✅ Datos guardados: {json_file}')
