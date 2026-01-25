#!/usr/bin/env python3.11
"""Script de prueba del dashboard"""
import subprocess
import time
import requests
import threading

def check_service(port, name):
    try:
        response = requests.get(f'http://localhost:{port}', timeout=2)
        print(f"✅ {name} (puerto {port}): OK - Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ {name} (puerto {port}): ERROR - {str(e)[:50]}")
        return False

def start_service(cmd, name):
    """Inicia un servicio en background"""
    print(f"🚀 Iniciando {name}...")
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"   PID: {proc.pid}")
        return proc
    except Exception as e:
        print(f"❌ Error iniciando {name}: {e}")
        return None

print("""
╔════════════════════════════════════════════════╗
║  🧪 PVBESSCAR Dashboard - Test Suite           ║
╚════════════════════════════════════════════════╝
""")

print("\n📋 Iniciando servicios...")
print("=" * 50)

# Matar procesos previos
subprocess.run("taskkill /f /im python.exe", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
time.sleep(2)

# Iniciar FastAPI
fastapi_proc = start_service('py -3.11 fastapi_websocket_server.py', 'FastAPI Server')
time.sleep(5)  # Esperar a que inicie

# Iniciar Dashboard
dashboard_proc = start_service('py -3.11 dashboard_pro.py', 'Dashboard Pro')
time.sleep(3)

print("\n🔍 Verificando servicios...")
print("=" * 50)

# Verificar servicios
time.sleep(2)
fastapi_ok = check_service(8000, 'FastAPI')
time.sleep(1)
dashboard_ok = check_service(5000, 'Dashboard')

print("\n" + "=" * 50)
print("\n📊 Resultados:")
print(f"  FastAPI (8000):  {'✅ OK' if fastapi_ok else '❌ FAILED'}")
print(f"  Dashboard (5000): {'✅ OK' if dashboard_ok else '❌ FAILED'}")

print("\n🌐 URLs de Acceso:")
print(f"  Dashboard:    http://localhost:5000")
print(f"  API Docs:     http://localhost:8000/docs")
print(f"  WebSocket:    ws://localhost:8000/ws")

print("\n" + "=" * 50)
print("\n✨ Sistema listo para usar!")
print("\nPresiona Ctrl+C para detener\n")

# Mantener procesos activos
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n⏹️  Deteniendo servicios...")
    if fastapi_proc:
        fastapi_proc.terminate()
    if dashboard_proc:
        dashboard_proc.terminate()
    print("✅ Servicios detenidos")
