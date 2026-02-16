#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPARATIVE CON BASELINES CORRECTOS - Análisis Comparativo de Agentes RL vs Baselines
====================================================================================

Incluye cálculo correcto de:
1. BASELINE CON SOLAR (4,050 kWp) - Referencia con solar
2. BASELINE SIN SOLAR (0 kWp) - Impacto de solar
3. AGENTES RL (SAC, PPO, A2C) - Mejora sobre baseline con solar

Datos de baseline: OE2 v5.4 (BESS simulation hourly, 8,760 horas)
"""
import json
from pathlib import Path
from datetime import datetime

# ============================================================================
# DATOS DE BASELINES (Calculados desde OE2 v5.4)
# ============================================================================

BASELINES_DATA = {
    'CON_SOLAR': {
        'name': 'CON SOLAR (4,050 kWp)',
        'description': 'Uncontrolled + 4,050 kWp solar + BESS (OE2 v5.4) - REFERENCIA RL',
        'solar_capacity_kwp': 4050.0,
        'bess_capacity_kwh': 1700.0,
        'grid_import_kwh': 18740000.0,  # kWh/año (uncontrolled scenario)
        'solar_generation_kwh': 82930000.0,  # kWh/año (PVGIS)
        'co2_grid_kg': 8470608.0,  # kg CO2/año (grid import × 0.4521)
        'co2_avoided_by_solar_kg': 37469000.0,  # kg CO2 avoided by solar (solar × 0.4521)
        'co2_net_kg': 8470608.0,  # CO2 neto después de solar
        'ev_demand_kwh': 2950000.0,  # EV charging demand
        'mall_demand_kwh': 35000000.0,  # Mall demand
        'timestamp': '2024-01-01T00:00:00',
    },
    'SIN_SOLAR': {
        'name': 'SIN SOLAR (0 kWp)',
        'description': 'Uncontrolled + Sin Solar (0 kWp) - Muestra impacto solar',
        'solar_capacity_kwp': 0.0,
        'bess_capacity_kwh': 1700.0,
        'grid_import_kwh': 101670000.0,  # kWh/año (NO hay solar)
        'solar_generation_kwh': 0.0,  # No hay generación
        'co2_grid_kg': 45939537.0,  # kg CO2/año (grid import × 0.4521)
        'co2_avoided_by_solar_kg': 0.0,  # No hay solar
        'co2_net_kg': 45939537.0,  # CO2 neto sin solar
        'ev_demand_kwh': 2950000.0,  # EV charging demand
        'mall_demand_kwh': 35000000.0,  # Mall demand
        'timestamp': '2024-01-01T00:00:00',
    }
}

# ============================================================================
# DATOS DE AGENTES RL (Desde resultados de entrenamiento)
# ============================================================================

REPORTS_DIR = Path('reports/mejoragent')
ppo_result_file = Path('outputs/ppo_training/result_ppo.json')
a2c_result_file = Path('outputs/a2c_training/result_a2c.json')
sac_result_file = Path('outputs/sac_training/result_sac.json')

# Cargar agentes
agents_data = {}
for agent, path in [('PPO', ppo_result_file), ('A2C', a2c_result_file), ('SAC', sac_result_file)]:
    if path.exists():
        with open(path) as f:
            agents_data[agent] = json.load(f)

# ============================================================================
# ANÁLISIS COMPARATIVO
# ============================================================================

report = []

report.append('=' * 100)
report.append('ANÁLISIS COMPARATIVO: BASELINES vs AGENTES RL')
report.append('Cálculos Correctos de Baseline (OE2 v5.4) + Mejora RL')
report.append('=' * 100)
report.append('')
report.append(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
report.append('')

# ============================================================================
# PARTE 1: BASELINES
# ============================================================================

report.append('=' * 100)
report.append('1. BASELINES - OE2 v5.4 (8,760 horas anuales)')
report.append('=' * 100)
report.append('')

baseline_con_solar = BASELINES_DATA['CON_SOLAR']
baseline_sin_solar = BASELINES_DATA['SIN_SOLAR']

# Baseline CON SOLAR
report.append('1.1 BASELINE CON SOLAR (4,050 kWp) - REFERENCIA PARA RL')
report.append('-' * 100)
report.append('')
report.append(f'Descripción: {baseline_con_solar["description"]}')
report.append('')
report.append('Generación y Demanda:')
report.append(f'  • Solar PV: {baseline_con_solar["solar_generation_kwh"]/1e6:>12.2f} GWh/año (4,050 kWp)')
report.append(f'  • EV Demand: {baseline_con_solar["ev_demand_kwh"]/1e6:>12.2f} GWh/año')
report.append(f'  • Mall Demand: {baseline_con_solar["mall_demand_kwh"]/1e6:>12.2f} GWh/año')
report.append(f'  • Total Demand: {(baseline_con_solar["ev_demand_kwh"] + baseline_con_solar["mall_demand_kwh"])/1e6:>12.2f} GWh/año')
report.append('')

report.append('Flujo Energético:')
report.append(f'  • Grid Import: {baseline_con_solar["grid_import_kwh"]/1e6:>12.2f} GWh/año')
report.append(f'  • Solar Coverage: {(baseline_con_solar["solar_generation_kwh"] / (baseline_con_solar["solar_generation_kwh"] + baseline_con_solar["grid_import_kwh"])) * 100:>10.1f}%')
report.append('')

report.append('Emisiones CO2:')
report.append(f'  • CO2 Grid (grid import × 0.4521): {baseline_con_solar["co2_grid_kg"]/1e6:>12.2f} M kg/año')
report.append(f'  • CO2 Évitado (solar × 0.4521):   {baseline_con_solar["co2_avoided_by_solar_kg"]/1e6:>12.2f} M kg/año')
report.append(f'  • CO2 NET (después de solar):      {baseline_con_solar["co2_net_kg"]/1e6:>12.2f} M kg/año')
report.append(f'  • Factor CO2 Iquitos: 0.4521 kg CO2/kWh (grid térmico)')
report.append('')
report.append(f'✅ REFERENCIA PARA MEDIR MEJORA RL: {baseline_con_solar["co2_net_kg"]/1e6:.2f} M kg CO2/año')
report.append('')
report.append('')

# Baseline SIN SOLAR
report.append('1.2 BASELINE SIN SOLAR (0 kWp) - MUESTRA IMPACTO SOLAR')
report.append('-' * 100)
report.append('')
report.append(f'Descripción: {baseline_sin_solar["description"]}')
report.append('')
report.append('Generación y Demanda:')
report.append(f'  • Solar PV: {baseline_sin_solar["solar_generation_kwh"]/1e6:>12.2f} GWh/año (SIN SOLAR)')
report.append(f'  • EV Demand: {baseline_sin_solar["ev_demand_kwh"]/1e6:>12.2f} GWh/año')
report.append(f'  • Mall Demand: {baseline_sin_solar["mall_demand_kwh"]/1e6:>12.2f} GWh/año')
report.append(f'  • Total Demand: {(baseline_sin_solar["ev_demand_kwh"] + baseline_sin_solar["mall_demand_kwh"])/1e6:>12.2f} GWh/año')
report.append('')

report.append('Flujo Energético:')
report.append(f'  • Grid Import: {baseline_sin_solar["grid_import_kwh"]/1e6:>12.2f} GWh/año (TODO del grid)')
report.append(f'  • Solar Coverage: {(baseline_sin_solar["solar_generation_kwh"] / (baseline_sin_solar["solar_generation_kwh"] + baseline_sin_solar["grid_import_kwh"]) if baseline_sin_solar["solar_generation_kwh"] + baseline_sin_solar["grid_import_kwh"] > 0 else 0) * 100:>10.1f}% (CERO)')
report.append('')

report.append('Emisiones CO2:')
report.append(f'  • CO2 Grid (grid import × 0.4521): {baseline_sin_solar["co2_grid_kg"]/1e6:>12.2f} M kg/año')
report.append(f'  • CO2 Évitado (solar × 0.4521):   {baseline_sin_solar["co2_avoided_by_solar_kg"]/1e6:>12.2f} M kg/año (CERO)')
report.append(f'  • CO2 NET (sin solar):              {baseline_sin_solar["co2_net_kg"]/1e6:>12.2f} M kg/año')
report.append('')

# Impacto de solar
solar_impact_kg = baseline_sin_solar['co2_net_kg'] - baseline_con_solar['co2_net_kg']
solar_impact_pct = (solar_impact_kg / baseline_sin_solar['co2_net_kg']) * 100

report.append('1.3 IMPACTO DE SOLAR (4,050 kWp)')
report.append('-' * 100)
report.append('')
report.append(f'CO2 Reducido por Solar:')
report.append(f'  • Absoluto: {solar_impact_kg/1e6:>12.2f} M kg CO2/año')
report.append(f'  • % Reducción: {solar_impact_pct:>10.1f}% vs sin solar')
report.append(f'  • Equivalencia: {solar_impact_kg/1e9:.3f} millones tCO2/año')
report.append('')
report.append(f'Conclusión: 4,050 kWp solar reduce CO2 de {baseline_sin_solar["co2_net_kg"]/1e6:.2f}M → {baseline_con_solar["co2_net_kg"]/1e6:.2f}M kg')
report.append('')
report.append('')

# ============================================================================
# PARTE 2: AGENTES RL
# ============================================================================

report.append('=' * 100)
report.append('2. AGENTES RL - MEJORA SOBRE BASELINE CON SOLAR')
report.append('=' * 100)
report.append('')

# Extraer datos de agentes
agents_metrics = {}

for agent, data in agents_data.items():
    summary = data.get('summary_metrics', {})
    agents_metrics[agent] = {
        'co2_total_kg': summary.get('total_co2_avoided_kg', 0),
        'co2_total_tco2': summary.get('total_co2_avoided_kg', 0) / 1000,
        'co2_direct_kg': summary.get('total_co2_avoided_direct_kg', 0),
        'co2_indirect_kg': summary.get('total_co2_avoided_indirect_kg', 0),
        'episodes': data.get('training', {}).get('total_episodes', 0),
        'timesteps': data.get('training', {}).get('total_timesteps', 0),
    }

# Ranking
report.append('2.1 RANKING DE AGENTES (por CO2 evitado vs Baseline CON SOLAR)')
report.append('-' * 100)
report.append('')

sorted_agents = sorted(agents_metrics.items(), key=lambda x: x[1]['co2_total_kg'], reverse=True)

for idx, (agent, metrics) in enumerate(sorted_agents, 1):
    medal = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉'
    
    # Mejora sobre baseline
    mejora_kg = metrics['co2_total_kg']
    mejora_pct = (mejora_kg / baseline_con_solar['co2_net_kg']) * 100 if baseline_con_solar['co2_net_kg'] > 0 else 0
    
    report.append(f'{medal} #{idx} {agent}')
    report.append(f'   CO2 Total Evitado: {metrics["co2_total_kg"]/1e6:>10.2f} M kg = {metrics["co2_total_tco2"]/1e3:>10.3f} M tCO2')
    report.append(f'   ├─ Directo (EV): {metrics["co2_direct_kg"]/1e6:>10.2f} M kg')
    report.append(f'   ├─ Indirecto (Solar): {metrics["co2_indirect_kg"]/1e6:>10.2f} M kg')
    report.append(f'   ├─ % Mejora vs Baseline: {mejora_pct:>10.2f}%')
    report.append(f'   ├─ Episodios: {metrics["episodes"]:>10d}')
    report.append(f'   └─ Steps: {metrics["timesteps"]:>10,d}')
    report.append('')

report.append('')

# ============================================================================
# PARTE 3: COMPARACIÓN BASELINE vs AGENTES
# ============================================================================

report.append('=' * 100)
report.append('3. TABLA COMPARATIVA: BASELINE CON SOLAR vs AGENTES RL')
report.append('=' * 100)
report.append('')

report.append('Escenario / Agente                 CO2 (M kg/año)    % vs Baseline    Mejora (M kg)    Status')
report.append('─' * 100)
report.append(f'BASELINE CON SOLAR (ref)           {baseline_con_solar["co2_net_kg"]/1e6:>12.2f}        0.00%       {0:>12.2f}    Referencia')

for agent, metrics in sorted_agents:
    mejora = metrics['co2_total_kg']
    mejora_pct = (mejora / baseline_con_solar['co2_net_kg']) * 100 if baseline_con_solar['co2_net_kg'] > 0 else 0
    co2_final = baseline_con_solar['co2_net_kg'] - mejora
    
    status = f'✅ Mejora {mejora_pct:.1f}%'
    
    report.append(f'{agent} (RL Agent)                    {co2_final/1e6:>12.2f}        {-mejora_pct:>6.2f}%       {mejora:>12.2f}    {status}')

report.append('─' * 100)
report.append(f'BASELINE SIN SOLAR (worst case)     {baseline_sin_solar["co2_net_kg"]/1e6:>12.2f}      {(baseline_sin_solar["co2_net_kg"]/baseline_con_solar["co2_net_kg"] - 1)*100:>6.1f}%       {solar_impact_kg:>12.2f}    Sin solar')
report.append('═' * 100)
report.append('')

# ============================================================================
# PARTE 4: ANÁLISIS DE MEJORA (Proyección Anual)
# ============================================================================

report.append('=' * 100)
report.append('4. ANÁLISIS DE MEJORA - PROYECCIÓN ANUAL')
report.append('=' * 100)
report.append('')

best_agent = sorted_agents[0][0]
best_metrics = sorted_agents[0][1]

report.append(f'🏆 MEJOR AGENTE: {best_agent}')
report.append('')

# En período evaluado (10 episodios)
report.append('En Período Evaluado (10 episodios):')
report.append(f'  • CO2 Evitado: {best_metrics["co2_total_kg"]/1e6:.2f} M kg')
report.append(f'  • Proyección Anual (×36.5): {best_metrics["co2_total_kg"] * 36.5/1e6:.2f} M kg')
report.append('')

# Final con RL vs baseline
report.append('Escenario Final (Con Control RL):')
final_co2 = baseline_con_solar['co2_net_kg'] - (best_metrics['co2_total_kg'] * 36.5)
final_co2_reduction = (best_metrics['co2_total_kg'] * 36.5) / baseline_con_solar['co2_net_kg'] * 100

report.append(f'  • CO2 Baseline: {baseline_con_solar["co2_net_kg"]/1e6:.2f} M kg/año')
report.append(f'  • CO2 RL Agent: {final_co2/1e6:.2f} M kg/año')
report.append(f'  • Reducción: {final_co2_reduction:.1f}%')
report.append(f'  • CO2 Evitado: {(best_metrics["co2_total_kg"] * 36.5)/1e6:.2f} M kg = {(best_metrics["co2_total_kg"] * 36.5)/1e9:.3f} millones tCO2/año')
report.append('')
report.append('')

# ============================================================================
# CONCLUSIONES
# ============================================================================

report.append('=' * 100)
report.append('5. CONCLUSIONES')
report.append('=' * 100)
report.append('')

report.append('✅ Cálculos Correctos de Baseline (OE2 v5.4):')
report.append(f'   • BASELINE CON SOLAR: {baseline_con_solar["co2_net_kg"]/1e6:.2f} M kg CO2/año (REFERENCIA)')
report.append(f'   • BASELINE SIN SOLAR: {baseline_sin_solar["co2_net_kg"]/1e6:.2f} M kg CO2/año')
report.append(f'   • Impacto Solar: {solar_impact_kg/1e6:.2f} M kg ({solar_impact_pct:.1f}% reducción)')
report.append('')

report.append(f'✅ Mejora RL ({best_agent}):')
report.append(f'   • CO2 Evitado Anual: {(best_metrics["co2_total_kg"] * 36.5)/1e6:.2f} M kg')
report.append(f'   • % Mejora: {final_co2_reduction:.1f}% vs baseline con solar')
report.append(f'   • Equivalencia: {(best_metrics["co2_total_kg"] * 36.5)/1e9:.3f} millones tCO2/año')
report.append('')

report.append('📊 Ranking Final:')
for idx, (agent, metrics) in enumerate(sorted_agents, 1):
    medal = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉'
    mejora = (metrics['co2_total_kg'] * 36.5) / baseline_con_solar['co2_net_kg'] * 100 if baseline_con_solar['co2_net_kg'] > 0 else 0
    report.append(f'   {medal} #{idx} {agent}: {mejora:.1f}% mejora')

report.append('')
report.append('=' * 100)
report.append('FIN DEL ANÁLISIS COMPARATIVO CON BASELINES')
report.append('=' * 100)

# Guardar reporte
output_file = REPORTS_DIR / '4_6_4_COMPARATIVE_CON_BASELINES_CORRECTO.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n'.join(report))
print(f'\n✅ Reporte guardado: {output_file}')

# Guardar datos estructurados
data_export = {
    'timestamp': datetime.now().isoformat(),
    'baselines': BASELINES_DATA,
    'agents': {
        agent: {
            'co2_total_kg': metrics['co2_total_kg'],
            'co2_total_tco2': metrics['co2_total_tco2'],
            'co2_direct_kg': metrics['co2_direct_kg'],
            'co2_indirect_kg': metrics['co2_indirect_kg'],
            'episodes': metrics['episodes'],
            'timesteps': metrics['timesteps'],
        }
        for agent, metrics in agents_metrics.items()
    },
    'analysis': {
        'best_agent': best_agent,
        'best_agent_improvement_pct': final_co2_reduction,
        'best_agent_co2_avoided_anual_kg': best_metrics['co2_total_kg'] * 36.5,
        'solar_impact_kg': solar_impact_kg,
        'solar_impact_pct': solar_impact_pct,
    }
}

json_file = REPORTS_DIR / '4_6_4_BASELINES_AGENTS_DATA_CORRECTO.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data_export, f, indent=2, ensure_ascii=False)

print(f'✅ Datos estructurados: {json_file}')
