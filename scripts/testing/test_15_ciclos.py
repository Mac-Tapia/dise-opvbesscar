#!/usr/bin/env python3.11
"""
Test automático: 15 ciclos de prueba con datos aleatorios
"""

import requests
import random
import time

print()
print('╔═══════════════════════════════════════════════════════════╗')
print('║   🚀 PRUEBA AUTOMÁTICA PVBESSCAR - 15 CICLOS             ║')
print('╚═══════════════════════════════════════════════════════════╝')
print()

acciones = ['CHARGE', 'DISCHARGE', 'IDLE']
exitosos = 0
recompensa_total = 0
episodios_finales = 0

for i in range(1, 16):
    accion = random.choice(acciones)
    try:
        response = requests.post(f'http://localhost:8000/api/control/{accion}', timeout=2)
        if response.status_code == 200:
            data = response.json()
            episodes = data['episodes']
            reward = round(float(data['reward']), 2)
            episodios_finales = episodes
            recompensa_total = reward
            print(f'[Ciclo {i:2d}/15] ✅ {accion:10} → Episodios: {episodes:5d} | Recompensa: €{reward:8.2f}')
            exitosos += 1
        else:
            print(f'[Ciclo {i:2d}/15] ⚠️  {accion:10} → Status {response.status_code}')
    except Exception as e:
        print(f'[Ciclo {i:2d}/15] ❌ {accion:10} → Error: {str(e)[:30]}')
    
    time.sleep(0.5)

print()
print('═══════════════════════════════════════════════════════════')
print(f'✅ RESULTADO FINAL:')
print(f'   Ciclos Exitosos: {exitosos}/15')
print(f'   Episodios Totales: {episodios_finales}')
print(f'   Recompensa Acumulada: €{recompensa_total:.2f}')
print('═══════════════════════════════════════════════════════════')
print()
print('📊 ESTADO ACTUAL DEL SISTEMA:')
print()

try:
    # Métricas
    r = requests.get('http://localhost:8000/api/metrics', timeout=2)
    m = r.json()
    print(f'⚡ Energía:')
    print(f'   Consumo: {m["consumo_kw"]} kW')
    print(f'   Solar: {m["solar_kw"]} kW')
    print(f'   Batería: {m["bateria_soc"]}%')
    print()
    
    # Agente
    r = requests.get('http://localhost:8000/api/agent', timeout=2)
    a = r.json()
    print(f'🤖 Agente RL:')
    print(f'   Estado: {a["status"]}')
    print(f'   Acción: {a["action"]}')
    print(f'   Episodios: {a["episodes"]}')
    print(f'   Recompensa Total: €{a["total_reward"]}')
    print(f'   Convergencia: {a["convergence_percent"]}%')
    print()
    
    # Objetivos
    r = requests.get('http://localhost:8000/api/objectives', timeout=2)
    o = r.json()
    print(f'🎯 Objetivos:')
    print(f'   Reducción Costo: {o["objectives"]["reduccion_costo"]["current"]}% / 75%')
    print(f'   Reducción CO2: {o["objectives"]["reduccion_co2"]["current"]}% / 50%')
    print(f'   Disponibilidad: {o["objectives"]["disponibilidad"]["current"]}% / 99%')
    print(f'   Convergencia IA: {o["objectives"]["convergencia_ia"]["current"]}% / 100%')
except Exception as e:
    print(f'⚠️  Error obteniendo datos: {e}')

print()
print('═══════════════════════════════════════════════════════════')
print('🌐 ACCESO:')
print('   Dashboard: http://localhost:5000')
print('   API Docs: http://localhost:8000/docs')
print('═══════════════════════════════════════════════════════════')
print()
