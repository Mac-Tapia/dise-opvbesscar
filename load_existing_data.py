import json
from pathlib import Path

# Cargar datos existentes
results_path = Path('/app/outputs/oe3/simulations')
summary_file = results_path / 'simulation_summary.json'

if summary_file.exists():
    with open(summary_file) as f:
        data = json.load(f)
    print('✅ Datos cargados correctamente desde Docker')
    agents = list(data.get('agents', {}).keys())
    print(f'   - Agentes encontrados: {agents}')
    scenarios = len(data.get('scenarios', []))
    print(f'   - Escenarios: {scenarios}')
    
    # Mostrar resultados CO2
    print('\n📊 Resultados CO2:')
    for agent, result in data.get('agents', {}).items():
        co2 = result.get('co2_kg', 0)
        print(f'   {agent}: {co2:,.0f} kg CO2')
else:
    print('❌ No se encontraron datos guardados')
    print(f'   Buscando en: {summary_file}')
