#!/usr/bin/env python3
"""
Script para visualizar resultados OE3 desde Docker
Carga datos existentes y genera reportes sin reentrenamiento
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def main():
    # Rutas
    results_dir = Path('/app/outputs/oe3/simulations')
    summary_file = results_dir / 'simulation_summary.json'
    co2_file = results_dir / 'co2_comparison.md'
    
    print("\n" + "="*70)
    print("🐳 DOCKER - VISUALIZADOR DE RESULTADOS OE3")
    print("="*70)
    print(f"📁 Directorio: {results_dir}")
    print(f"⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # Verificar archivos
    if not summary_file.exists():
        print("❌ ERROR: No se encontró simulation_summary.json")
        print(f"   Ruta esperada: {summary_file}")
        return 1
    
    # Cargar datos
    try:
        with open(summary_file, 'r') as f:
            data = json.load(f)
        print("✅ Datos cargados correctamente")
    except Exception as e:
        print(f"❌ Error al cargar JSON: {e}")
        return 1
    
    # Mostrar información
    print("\n📊 INFORMACIÓN DE SIMULACIÓN:\n")
    
    # Escenarios
    scenarios = data.get('scenarios', [])
    print(f"  • Escenarios: {len(scenarios)}")
    
    # Agentes
    agents = data.get('agents', {})
    print(f"  • Agentes entrenados: {list(agents.keys())}")
    print(f"  • Total: {len(agents)} agentes\n")
    
    # Resultados CO2
    if agents:
        print("🌍 RESULTADOS CO2 (kg):\n")
        for agent_name, agent_data in agents.items():
            co2_kg = agent_data.get('co2_kg', 0)
            reduction = agent_data.get('reduction_pct', 0)
            print(f"  • {agent_name:15s}: {co2_kg:>12,.0f} kg CO2  ({reduction:+.2f}%)")
    
    # Mostrar CO2 comparison
    if co2_file.exists():
        print("\n" + "="*70)
        print("📋 COMPARACIÓN CO2 (CO2_comparison.md):\n")
        with open(co2_file, 'r') as f:
            print(f.read())
    
    # Archivos generados
    print("\n" + "="*70)
    print("📁 ARCHIVOS GENERADOS:\n")
    
    for file_path in sorted(results_dir.glob('*')):
        if file_path.is_file():
            size_kb = file_path.stat().st_size / 1024
            print(f"  • {file_path.name:40s} ({size_kb:>8.1f} KB)")
    
    print("\n" + "="*70)
    print("✅ DOCKER COMPLETÓ CORRECTAMENTE - No se requiere re-entrenamiento")
    print("="*70 + "\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
