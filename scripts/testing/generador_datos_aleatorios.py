#!/usr/bin/env python3.11
"""
Generador de Datos Aleatorios para PVBESSCAR
Crea datos realistas para probar el dashboard
"""

import requests
import random
import time
from datetime import datetime, timedelta
import json

API_URL = "http://localhost:8000"

def generar_datos_aleatorios():
    """Genera datos aleatorios realistas"""
    return {
        'consumo_kw': round(30 + random.uniform(-10, 40), 2),
        'solar_kw': round(max(0, 45 + random.uniform(-30, 30)), 2),
        'bateria_soc': round(max(0, min(100, 60 + random.uniform(-5, 5))), 1),
        'grid_import': round(max(0, random.uniform(-5, 30)), 2),
        'costo_kwh': round(random.uniform(0.12, 0.28), 3),
        'action': random.choice(['CHARGE', 'DISCHARGE', 'IDLE']),
    }

def enviar_control_agente(accion):
    """Envía comando de control al agente"""
    try:
        # Enviar en MAYÚSCULAS como espera el servidor
        response = requests.post(
            f"{API_URL}/api/control/{accion.upper()}",
            timeout=3
        )
        if response.status_code == 200:
            print(f"✅ Agente: {accion} ejecutado")
            return response.json()
        else:
            print(f"❌ Error enviando {accion}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)[:50]}")
    return None

def mostrar_datos_actuales():
    """Obtiene y muestra datos actuales del sistema"""
    try:
        # Métricas
        resp = requests.get(f"{API_URL}/api/metrics", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n📊 MÉTRICAS ACTUALES:")
            print(f"   ⚡ Consumo: {data['consumo_kw']} kW")
            print(f"   ☀️  Solar: {data['solar_kw']} kW")
            print(f"   🔋 Batería: {data['bateria_soc']}%")
            print(f"   💰 Costo: €{data['costo_kwh']}/kWh")
        
        # Agente
        resp = requests.get(f"{API_URL}/api/agent", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n🤖 AGENTE RL:")
            print(f"   Acción: {data['action']}")
            print(f"   Episodios: {data['episodes']}")
            print(f"   Recompensa: €{data['total_reward']}")
            print(f"   Convergencia: {data['convergence_percent']}%")
        
        # Objetivos
        resp = requests.get(f"{API_URL}/api/objectives", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n🎯 OBJETIVOS:")
            print(f"   Costo: {data['objectives']['reduccion_costo']['current']}% / 75%")
            print(f"   CO2: {data['objectives']['reduccion_co2']['current']}% / 50%")
            print(f"   Disponibilidad: {data['objectives']['disponibilidad']['current']}% / 99%")
            print(f"   IA: {data['objectives']['convergencia_ia']['current']}% / 100%")
    
    except Exception as e:
        print(f"❌ Error obteniendo datos: {str(e)[:50]}")

def prueba_interactiva():
    """Prueba interactiva del sistema"""
    print("\n" + "="*60)
    print("🧪 PRUEBA INTERACTIVA DEL SISTEMA PVBESSCAR")
    print("="*60)
    
    print("\n📋 Menú de Pruebas:")
    print("  1. Enviar comando CHARGE (cargar batería)")
    print("  2. Enviar comando DISCHARGE (descargar batería)")
    print("  3. Enviar comando IDLE (reposo)")
    print("  4. Ver datos actuales")
    print("  5. Ejecutar prueba automática (5 ciclos)")
    print("  6. Streaming continuo (30 segundos)")
    print("  7. Salir")
    
    while True:
        try:
            opcion = input("\n👉 Selecciona opción (1-7): ").strip()
            
            if opcion == "1":
                print("\n⬆️  Enviando CHARGE...")
                enviar_control_agente("CHARGE")
                time.sleep(1)
                mostrar_datos_actuales()
            
            elif opcion == "2":
                print("\n⬇️  Enviando DISCHARGE...")
                enviar_control_agente("DISCHARGE")
                time.sleep(1)
                mostrar_datos_actuales()
            
            elif opcion == "3":
                print("\n➡️  Enviando IDLE...")
                enviar_control_agente("IDLE")
                time.sleep(1)
                mostrar_datos_actuales()
            
            elif opcion == "4":
                mostrar_datos_actuales()
            
            elif opcion == "5":
                print("\n🔄 Ejecutando prueba automática (5 ciclos)...")
                acciones = ['CHARGE', 'DISCHARGE', 'IDLE', 'CHARGE', 'IDLE']
                for i, accion in enumerate(acciones, 1):
                    print(f"\n[Ciclo {i}/5] Enviando {accion}...")
                    enviar_control_agente(accion)
                    mostrar_datos_actuales()
                    time.sleep(2)
                print("\n✅ Prueba automática completada")
            
            elif opcion == "6":
                print("\n🌊 Streaming continuo de datos (30 segundos)...")
                inicio = time.time()
                contador = 0
                while time.time() - inicio < 30:
                    try:
                        resp = requests.get(f"{API_URL}/api/metrics", timeout=2)
                        if resp.status_code == 200:
                            data = resp.json()
                            contador += 1
                            print(f"[{contador}] ⚡{data['consumo_kw']}kW | ☀️ {data['solar_kw']}kW | 🔋{data['bateria_soc']}% | 💰€{data['costo_kwh']}")
                    except:
                        pass
                    time.sleep(2)
                print(f"\n✅ Streaming completado ({contador} actualizaciones)")
            
            elif opcion == "7":
                print("\n👋 ¡Hasta luego!")
                break
            
            else:
                print("❌ Opción no válida. Intenta de nuevo.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Programa interrumpido")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def prueba_automatica():
    """Ejecuta pruebas automáticas del sistema"""
    print("\n" + "="*60)
    print("🤖 PRUEBA AUTOMÁTICA DEL SISTEMA")
    print("="*60)
    
    print("\n1️⃣  Verificando conectividad...")
    try:
        resp = requests.get(f"{API_URL}/health", timeout=3)
        if resp.status_code == 200:
            print("   ✅ Servidor FastAPI responde")
        else:
            print("   ❌ Servidor no responde correctamente")
            return
    except Exception as e:
        print(f"   ❌ No se pudo conectar: {e}")
        return
    
    print("\n2️⃣  Ejecutando 10 ciclos de comandos aleatorios...")
    acciones = ['CHARGE', 'DISCHARGE', 'IDLE']
    
    for i in range(1, 11):
        accion = random.choice(acciones)
        print(f"\n[Ciclo {i}/10] Enviando {accion}...")
        enviar_control_agente(accion)
        
        # Mostrar estado actual
        try:
            resp = requests.get(f"{API_URL}/api/metrics", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                print(f"   📊 Consumo: {data['consumo_kw']}kW | Solar: {data['solar_kw']}kW | Batería: {data['bateria_soc']}%")
        except:
            pass
        
        time.sleep(1.5)
    
    print("\n✅ Prueba automática completada")
    print("\n📌 Abre http://localhost:5000 para ver el dashboard actualizado")

if __name__ == "__main__":
    import sys
    
    print("""
╔════════════════════════════════════════════════════════════╗
║     🧪 GENERADOR DE DATOS ALEATORIOS - PVBESSCAR         ║
║        Para probar y validar el sistema completo          ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        prueba_automatica()
    else:
        prueba_interactiva()
