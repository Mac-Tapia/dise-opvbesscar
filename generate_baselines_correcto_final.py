#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPARATIVE CON BASELINES CORRECTOS - Análisis Realista Normalizado
===================================================================

Incluye:
1. BASELINE CON SOLAR (4,050 kWp) - Referencia sin control RL
2. BASELINE SIN SOLAR (0 kWp) - Impacto solar
3. AGENTES RL (SAC, PPO, A2C) - Mejora con coverage scenarios realistas

Normalización: 10 episodios de entrenamiento → proyección operativa (30/50/100% coverage)
"""
import json
from pathlib import Path
from datetime import datetime

# ============================================================================
# DATOS DE BASELINES (OE2 v5.4)
# ============================================================================

BASELINE_DATA = {
    'CON_SOLAR': {
        'name': 'BASELINE CON SOLAR (4,050 kWp)',
        'description': 'Dispatch sin control + 4,050 kWp solar + BESS (OE2 v5.4)',
        'solar_kwp': 4050.0,
        'grid_import_kwh': 18740000.0,  # Annual grid import
        'solar_generation_kwh': 82930000.0,  # Annual solar generation
        'co2_grid_kg': 8470608.0,  # grid import × 0.4521
        'co2_avoided_solar_kg': 37469000.0,  # solar × 0.4521
        'notes': 'Referencia para medir mejora RL',
    },
    'SIN_SOLAR': {
        'name': 'BASELINE SIN SOLAR (0 kWp)',
        'description': 'Dispatch sin control + Sin solar (worst case)',
        'solar_kwp': 0.0,
        'grid_import_kwh': 101670000.0,  # Annual grid import (100% from grid)
        'solar_generation_kwh': 0.0,
        'co2_grid_kg': 45939537.0,  # grid import × 0.4521
        'co2_avoided_solar_kg': 0.0,
        'notes': 'Muestra impacto total de 4,050 kWp solar',
    }
}

# CO2 emissions factor
CO2_FACTOR = 0.4521  # kg CO2/kWh (Iquitos thermal grid)

# ============================================================================
# CARGAR DATOS DE AGENTES ENTRENADOS
# ============================================================================

REPORTS_DIR = Path('reports/mejoragent')
outputs_dir = Path('outputs')

agents_data = {}
for agent in ['PPO', 'A2C', 'SAC']:
    result_file = outputs_dir / f'{agent.lower()}_training' / f'result_{agent.lower()}.json'
    
    if result_file.exists():
        try:
            with open(result_file) as f:
                agents_data[agent] = json.load(f)
        except:
            agents_data[agent] = {}

# ============================================================================
# FUNCIÓN AUXILIAR: EXTRAER MÉTRICAS
# ============================================================================

def get_agent_metrics(agent_name, agent_data):
    """Extrae métricas de CO2 del JSON del agente."""
    try:
        summary = agent_data.get('summary_metrics', {})
        
        # Intentar extraer valores principales
        total_avoided = summary.get('total_co2_avoided_kg', 0)
        direct_avoided = summary.get('total_co2_avoided_direct_kg', 0)
        indirect_avoided = summary.get('total_co2_avoided_indirect_kg', 0)
        
        episodes = agent_data.get('training', {}).get('total_episodes', 0)
        timesteps = agent_data.get('training', {}).get('total_timesteps', 0)
        
        return {
            'total_kg': total_avoided,
            'direct_kg': direct_avoided,
            'indirect_kg': indirect_avoided,
            'episodes': episodes,
            'timesteps': timesteps,
            'valid': total_avoided > 0 or episodes > 0
        }
    except:
        return {
            'total_kg': 0,
            'direct_kg': 0,
            'indirect_kg': 0,
            'episodes': 0,
            'timesteps': 0,
            'valid': False
        }

# Extraer datos de todos los agentes
agents_metrics = {}
for agent, data in agents_data.items():
    agents_metrics[agent] = get_agent_metrics(agent, data)

# ============================================================================
# GENERAR REPORTE
# ============================================================================

report = []

report.append('╔' + '═' * 98 + '╗')
report.append('║ ANÁLISIS COMPARATIVO: BASELINES CON SOLAR + AGENTES RL (NORMALIZADO)' + ' ' * 28 + '║')
report.append('║ Cálculos Correctos de Baseline (OE2 v5.4) + Mejora RL Realista                 ║')
report.append('╚' + '═' * 98 + '╝')
report.append('')
report.append(f'📅 Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
report.append('')

# ============================================================================
# SECCIÓN 1: BASELINES
# ============================================================================

report.append('╔' + '═' * 98 + '╗')
report.append('║ 1. BASELINES - OE2 v5.4 (DISPATCH SIN CONTROL, 8,760 HORAS ANUALES)' + ' ' * 29 + '║')
report.append('╚' + '═' * 98 + '╝')
report.append('')

baseline_con = BASELINE_DATA['CON_SOLAR']
baseline_sin = BASELINE_DATA['SIN_SOLAR']

# Baseline CON SOLAR
report.append('┌─ 1.1 BASELINE CON SOLAR (4,050 kWp) - REFERENCIA PARA RL')
report.append('│')
report.append(f'├─ Generación Solar: {baseline_con["solar_generation_kwh"]/1e6:>10.2f} GWh/año')
report.append(f'├─ Grid Import: {baseline_con["grid_import_kwh"]/1e6:>10.2f} GWh/año (sin control)')
report.append(f'├─ CO2 Grid: {baseline_con["co2_grid_kg"]/1e6:>10.2f} M kg/año')
report.append(f'├─ CO2 Evitado Solar: {baseline_con["co2_avoided_solar_kg"]/1e6:>10.2f} M kg/año')
report.append(f'└─ 🎯 CO2 NET (REFERENCIA): {baseline_con["co2_grid_kg"]/1e6:>10.2f} M kg/año')
report.append('')

# Baseline SIN SOLAR
report.append('┌─ 1.2 BASELINE SIN SOLAR (0 kWp) - IMPACTO SOLAR')
report.append('│')
report.append(f'├─ Generación Solar: {baseline_sin["solar_generation_kwh"]/1e6:>10.2f} GWh/año')
report.append(f'├─ Grid Import: {baseline_sin["grid_import_kwh"]/1e6:>10.2f} GWh/año (100% grid)')
report.append(f'├─ CO2 Grid: {baseline_sin["co2_grid_kg"]/1e6:>10.2f} M kg/año')
report.append(f'├─ CO2 Evitado Solar: {baseline_sin["co2_avoided_solar_kg"]/1e6:>10.2f} M kg/año')
report.append(f'└─ CO2 NET: {baseline_sin["co2_grid_kg"]/1e6:>10.2f} M kg/año')
report.append('')

# Impacto de solar
solar_impact = baseline_sin['co2_grid_kg'] - baseline_con['co2_grid_kg']
solar_pct = (solar_impact / baseline_sin['co2_grid_kg']) * 100

report.append('┌─ 1.3 IMPACTO DE SOLAR (4,050 kWp)')
report.append('│')
report.append(f'├─ CO2 Reducido: {solar_impact/1e6:>10.2f} M kg/año')
report.append(f'├─ % Reducción: {solar_pct:>10.1f}% (reducción vs sin solar)')
report.append(f'└─ Conclusión: Solar reduce de {baseline_sin["co2_grid_kg"]/1e6:.2f}M → {baseline_con["co2_grid_kg"]/1e6:.2f}M kg')
report.append('')
report.append('')

# ============================================================================
# SECCIÓN 2: AGENTES RL
# ============================================================================

report.append('╔' + '═' * 98 + '╗')
report.append('║ 2. AGENTES RL - MEJORA SOBRE BASELINE CON SOLAR' + ' ' * 49 + '║')
report.append('╚' + '═' * 98 + '╝')
report.append('')

report.append('📊 DATOS DE ENTRENAMIENTO:')
report.append('')

sorted_agents = sorted(agents_metrics.items(), 
                       key=lambda x: x[1]['total_kg'], 
                       reverse=True)

for idx, (agent, metrics) in enumerate(sorted_agents, 1):
    medal = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉'
    
    report.append(f'{medal} {agent}')
    report.append(f'   ├─ Episodios: {metrics["episodes"]:>6d}')
    report.append(f'   ├─ Steps: {metrics["timesteps"]:>10,d}')
    report.append(f'   ├─ CO2 Evitado (período evaluado): {metrics["total_kg"]/1e6:>10.2f} M kg')
    report.append(f'   └─ CO2 Status: {"✅ Datos válidos" if metrics["valid"] else "⚠️  Sin datos"}')
    report.append('')

report.append('')

# ============================================================================
# SECCIÓN 3: TABLA COMPARATIVA NORMALIZADA
# ============================================================================

report.append('╔' + '═' * 98 + '╗')
report.append('║ 3. TABLA COMPARATIVA - ESCENARIOS DE COBERTURA REALISTA' + ' ' * 40 + '║')
report.append('╚' + '═' * 98 + '╝')
report.append('')

report.append('ℹ️  NOTA TÉCNICA IMPORTANTE:')
report.append('   Los agentes fueron entrenados en 10 episodios (10 días virtuales).')
report.append('   Para proyectar impacto anual, consideramos 3 escenarios de cobertura operativa:')
report.append('   • 30% (Conservative): Implementación en 30% de la flota')
report.append('   • 50% (Moderate): Implementación en 50% de la flota')
report.append('   • 100% (Optimistic): Implementación en 100% de la flota')
report.append('')
report.append('   Proyección anual = CO2_evitado(10 días) × 36.5 × coverage_factor')
report.append('')

# Coverage scenarios
coverage_scenarios = [
    ('30%', 0.30),
    ('50%', 0.50),
    ('100%', 1.00),
]

best_agent = sorted_agents[0][0]
best_metrics = sorted_agents[0][1]

for coverage_label, coverage_factor in coverage_scenarios:
    report.append('─' * 100)
    report.append(f'📍 ESCENARIO {coverage_label} COBERTURA OPERATIVA')
    report.append('─' * 100)
    report.append('')
    
    # Header
    report.append(f'{"Agente/Baseline":<30} {"CO2 Anual (M kg)":<20} {"Mejora vs CON_SOLAR":<20} {"Status"}')
    report.append('─' * 100)
    
    # Baseline
    report.append(f'{"BASELINE CON SOLAR (ref)":<30} {baseline_con["co2_grid_kg"]/1e6:>12.2f}       {"0.00%":>18} {"🎯 Referencia"}')
    
    # Agentes
    for agent, metrics in sorted_agents:
        if metrics['total_kg'] > 0:
            # Proyección: CO2 evitado en 10 días × 36.5 × coverage
            co2_anual_projected = metrics['total_kg'] * 36.5 * coverage_factor
            
            # CO2 final después de RL
            co2_final = baseline_con['co2_grid_kg'] - co2_anual_projected
            
            # % mejora
            mejora_pct = (co2_anual_projected / baseline_con['co2_grid_kg']) * 100 if baseline_con['co2_grid_kg'] > 0 else 0
            
            # Status
            status = f'✅ {mejora_pct:.1f}% mejora'
            
            report.append(f'{agent:<30} {co2_final/1e6:>12.2f}       {mejora_pct:>16.1f}%  {status}')
        else:
            report.append(f'{agent:<30} {"(sin datos)":>20} {"N/A":>18} ⚠️  Sin datos')
    
    report.append('─' * 100)
    report.append('')

report.append('')

# ============================================================================
# SECCIÓN 4: ANÁLISIS DETALLADO
# ============================================================================

report.append('╔' + '═' * 98 + '╗')
report.append('║ 4. ANÁLISIS DETALLADO - MEJORES AGENTES' + ' ' * 55 + '║')
report.append('╚' + '═' * 98 + '╝')
report.append('')

report.append(f'🏆 {best_agent} - MEJOR AGENTE')
report.append('')

if best_metrics['total_kg'] > 0:
    report.append('Resumen de Mejora (Normalizado):')
    report.append('')
    
    # 30% coverage
    co2_30 = best_metrics['total_kg'] * 36.5 * 0.30
    reduction_30 = (co2_30 / baseline_con['co2_grid_kg']) * 100
    
    report.append(f'├─ Cobertura 30%: {co2_30/1e6:.2f} M kg CO2/año evitado ({reduction_30:.1f}% mejora)')
    
    # 50% coverage
    co2_50 = best_metrics['total_kg'] * 36.5 * 0.50
    reduction_50 = (co2_50 / baseline_con['co2_grid_kg']) * 100
    
    report.append(f'├─ Cobertura 50%: {co2_50/1e6:.2f} M kg CO2/año evitado ({reduction_50:.1f}% mejora)')
    
    # 100% coverage
    co2_100 = best_metrics['total_kg'] * 36.5 * 1.00
    reduction_100 = (co2_100 / baseline_con['co2_grid_kg']) * 100
    
    report.append(f'└─ Cobertura 100%: {co2_100/1e6:.2f} M kg CO2/año evitado ({reduction_100:.1f}% mejora)')
    
    report.append('')
    report.append(f'Ranking de otros agentes:')
    for idx, (agent, metrics) in enumerate(sorted_agents[1:], 2):
        if metrics['total_kg'] > 0:
            co2_50_other = metrics['total_kg'] * 36.5 * 0.50
            reduction_50_other = (co2_50_other / baseline_con['co2_grid_kg']) * 100
            delta = reduction_50 - reduction_50_other
            report.append(f'   {"🥈" if idx == 2 else "🥉"} #{idx} {agent}: {reduction_50_other:.1f}% mejora (Δ {delta:+.1f}% vs winner)')
        else:
            report.append(f'   {"🥈" if idx == 2 else "🥉"} #{idx} {agent}: ⚠️  Sin datos')
else:
    report.append('⚠️  No hay datos válidos para {best_agent}')

report.append('')
report.append('')

# ============================================================================
# SECCIÓN 5: CONCLUSIONES Y RECOMENDACIONES
# ============================================================================

report.append('╔' + '═' * 98 + '╗')
report.append('║ 5. CONCLUSIONES Y RECOMENDACIONES' + ' ' * 62 + '║')
report.append('╚' + '═' * 98 + '╝')
report.append('')

report.append('✅ BASELINES CORRECTOS (OE2 v5.4):')
report.append(f'   • BASELINE CON SOLAR: {baseline_con["co2_grid_kg"]/1e6:.2f} M kg CO2/año (REFERENCIA)')
report.append(f'   • BASELINE SIN SOLAR: {baseline_sin["co2_grid_kg"]/1e6:.2f} M kg CO2/año')
report.append(f'   • Impacto Solar (4,050 kWp): {solar_impact/1e6:.2f} M kg ({solar_pct:.1f}% reducción)')
report.append('')

report.append('✅ MEJORA RL (ESCENARIO 50% COBERTURA - REALISTA):')
if best_metrics['total_kg'] > 0:
    co2_50_best = best_metrics['total_kg'] * 36.5 * 0.50
    reduction_50_best = (co2_50_best / baseline_con['co2_grid_kg']) * 100
    
    report.append(f'   • Agente: {best_agent}')
    report.append(f'   • CO2 Evitado Anual: {co2_50_best/1e6:.2f} M kg')
    report.append(f'   • % Mejora: {reduction_50_best:.1f}% vs baseline con solar')
    report.append(f'   • Equivalencia: {co2_50_best/1e9:.4f} millones tCO2/año')
else:
    report.append(f'   ⚠️  Datos no disponibles')

report.append('')

report.append('📌 RANKING FINAL (% MEJORA A 50% COBERTURA):')
for idx, (agent, metrics) in enumerate(sorted_agents, 1):
    medal = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉'
    
    if metrics['total_kg'] > 0:
        co2_scenario = metrics['total_kg'] * 36.5 * 0.50
        reduction = (co2_scenario / baseline_con['co2_grid_kg']) * 100
        report.append(f'   {medal} #{idx} {agent}: {reduction:>6.1f}% mejora')
    else:
        report.append(f'   {medal} #{idx} {agent}: ⚠️  Sin datos')

report.append('')
report.append('⚠️  NOTA: Proyecciones basadas en cobertura operativa realista (30-100%)')
report.append('    No se recomiendan mejoras > 100% sin validación de cobertura real.')
report.append('')

report.append('═' * 100)
report.append('FIN DEL ANÁLISIS COMPARATIVO CON BASELINES CORRECTOS')
report.append('═' * 100)

# ============================================================================
# GUARDAR ARCHIVOS
# ============================================================================

output_file = REPORTS_DIR / '4_6_4_BASELINES_CORRECTO_FINAL.txt'
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print('\n'.join(report))
print(f'\n✅ Reporte guardado: {output_file}')

# Datos estructurados
data_export = {
    'timestamp': datetime.now().isoformat(),
    'baselines': {
        'CON_SOLAR': {
            'co2_net_kg': baseline_con['co2_grid_kg'],
            'solar_generation_kwh': baseline_con['solar_generation_kwh'],
            'grid_import_kwh': baseline_con['grid_import_kwh'],
            'solar_impact_kg': solar_impact,
            'solar_impact_pct': solar_pct,
        },
        'SIN_SOLAR': {
            'co2_net_kg': baseline_sin['co2_grid_kg'],
            'solar_generation_kwh': baseline_sin['solar_generation_kwh'],
            'grid_import_kwh': baseline_sin['grid_import_kwh'],
        }
    },
    'agents': {
        agent: {
            'total_co2_avoided_kg': metrics['total_kg'],
            'episodes': metrics['episodes'],
            'timesteps': metrics['timesteps'],
        }
        for agent, metrics in agents_metrics.items()
    },
    'coverage_scenarios': {
        coverage: {
            agent: {
                'co2_anual_projected_kg': metrics['total_kg'] * 36.5 * factor if metrics['total_kg'] > 0 else 0,
                'improvement_pct': ((metrics['total_kg'] * 36.5 * factor) / baseline_con['co2_grid_kg']) * 100 if metrics['total_kg'] > 0 and baseline_con['co2_grid_kg'] > 0 else 0,
            }
            for agent, metrics in agents_metrics.items()
        }
        for coverage, factor in [('30%', 0.30), ('50%', 0.50), ('100%', 1.00)]
    }
}

json_file = REPORTS_DIR / '4_6_4_BASELINES_AGENTS_DATA_FINAL.json'
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data_export, f, indent=2, ensure_ascii=False)

print(f'✅ Datos estructurados: {json_file}')
