#!/usr/bin/env python3.11
"""
🎮 PVBESSCAR Simulador Interactivo
Simulación de cómo funciona el sistema de gestión de energía
"""

import requests
import json
from datetime import datetime, timedelta
import time
import random

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

BASE_URL = "http://localhost:8000"

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")

def print_section(text):
    print(f"{Colors.BLUE}{Colors.BOLD}▶ {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")

# ============================================================================
# 1. VERIFICAR QUE EL SISTEMA ESTÁ VIVO
# ============================================================================

def health_check():
    """Verifica que el API está respondiendo"""
    print_header("1️⃣  HEALTH CHECK - Verificar Sistema")
    
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        data = resp.json()
        
        print_success(f"Sistema: {data['status'].upper()}")
        print_info(f"Servicio: {data['service']}")
        print_info(f"Hora: {data['timestamp']}")
        return True
    except Exception as e:
        print_error(f"No se pudo conectar: {str(e)}")
        return False

# ============================================================================
# 2. ESTADO DEL SISTEMA
# ============================================================================

def system_status():
    """Obtiene el estado de todos los componentes"""
    print_header("2️⃣  ESTADO DEL SISTEMA")
    
    try:
        resp = requests.get(f"{BASE_URL}/api/status", timeout=5)
        data = resp.json()
        
        print_section("Sistema")
        print(f"  Estado: {data['status']}")
        
        print_section("Componentes")
        for component, status in data['components'].items():
            icon = "✅" if status == "connected" or status == "loaded" or status == "active" else "❌"
            print(f"  {icon} {component.replace('_', ' ').title()}: {status}")
        
        return True
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

# ============================================================================
# 3. LEER MÉTRICAS ACTUALES
# ============================================================================

def read_metrics():
    """Lee las métricas actuales del sistema"""
    print_header("3️⃣  MÉTRICAS ACTUALES")
    
    try:
        resp = requests.get(f"{BASE_URL}/api/metrics", timeout=5)
        data = resp.json()
        
        # Visualizar como barra de progreso
        build_load = data['building_load_kw']
        pv_gen = data['pv_generation_kw']
        battery = data['battery_soc']
        grid = data['grid_import_kw']
        cost = data['total_cost']
        
        print_section("Consumo del Edificio")
        print(f"  Valor: {Colors.RED}{build_load}{Colors.END} kW")
        _draw_bar(build_load, max_val=100, label="Consumo")
        
        print_section("Generación Solar")
        print(f"  Valor: {Colors.YELLOW}{pv_gen}{Colors.END} kW")
        _draw_bar(pv_gen, max_val=100, label="Solar")
        
        print_section("Estado Batería")
        print(f"  Valor: {Colors.GREEN}{battery}{Colors.END}%")
        _draw_bar(battery, max_val=100, label="Batería")
        
        print_section("Importación Red")
        print(f"  Valor: {Colors.CYAN}{grid}{Colors.END} kW")
        _draw_bar(grid, max_val=100, label="Red")
        
        print_section("Costo Acumulado")
        print(f"  ${Colors.BOLD}{cost}{Colors.END} €")
        
        return data
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def _draw_bar(value, max_val=100, label=""):
    """Dibuja una barra de progreso"""
    percentage = (value / max_val) * 100
    filled = int(percentage / 5)
    bar = "█" * filled + "░" * (20 - filled)
    print(f"  [{bar}] {percentage:.1f}%")

# ============================================================================
# 4. SIMULACIÓN: DECIDE ACCIÓN
# ============================================================================

def decide_action(metrics):
    """Usa IA para decidir qué acción ejecutar"""
    print_header("4️⃣  DECISIÓN IA - ¿Qué Acción Ejecutar?")
    
    build_load = metrics['building_load_kw']
    pv_gen = metrics['pv_generation_kw']
    battery = metrics['battery_soc']
    grid = metrics['grid_import_kw']
    
    print_section("Análisis del Controlador IA")
    
    # Lógica de decisión
    action = "idle"
    reason = ""
    value = 0
    
    if pv_gen > 50 and battery < 80:
        # Mucho solar, batería no llena → Cargar
        action = "charge"
        value = min(pv_gen - build_load, 20)  # Carga limitada
        reason = "✅ Solar disponible + Batería no llena → CARGAR"
    
    elif pv_gen < 10 and battery > 40:
        # Poco solar, batería disponible → Descargar
        action = "discharge"
        value = min(build_load - pv_gen, 30)  # Descarga limitada
        reason = "✅ Poco solar + Batería disponible → DESCARGAR"
    
    elif build_load > 60 and battery > 60:
        # Alto consumo, batería disponible → Descargar
        action = "discharge"
        value = 15
        reason = "✅ Alto consumo + Batería disponible → DESCARGAR"
    
    else:
        action = "idle"
        reason = "✅ Situación equilibrada → ESPERAR"
    
    print_info(f"Consumo edificio: {build_load} kW")
    print_info(f"Generación solar: {pv_gen} kW")
    print_info(f"Batería: {battery}%")
    print_info(f"Importación red: {grid} kW")
    
    print()
    print_success(reason)
    
    if action != "idle":
        print_info(f"Potencia a {action}: {value:.1f} kW")
    
    return action, value

# ============================================================================
# 5. EJECUTAR ACCIÓN
# ============================================================================

def execute_action(action, value):
    """Envía la acción al API"""
    print_header("5️⃣  EJECUTAR ACCIÓN")
    
    if action == "idle":
        print_info("Acción IDLE: Sistema se mantiene en estado actual")
        return True
    
    try:
        print_section(f"Enviando comando: {action.upper()}")
        
        resp = requests.post(
            f"{BASE_URL}/api/control",
            json={"action": action, "value": value},
            timeout=5
        )
        
        result = resp.json()
        
        print_success(f"Acción {result['action'].upper()} ejecutada")
        print_info(f"Potencia: {result['value']} kW")
        print_info(f"Estado: {result['status']}")
        print_info(f"Hora: {result['timestamp']}")
        
        return True
    except Exception as e:
        print_error(f"Error al ejecutar: {str(e)}")
        return False

# ============================================================================
# 6. SIMULACIÓN COMPLETA
# ============================================================================

def simulate_day():
    """Simula un día completo de operación"""
    print_header("🌅 SIMULACIÓN: DÍA COMPLETO")
    
    print_info("Simulando 24 horas con decisiones cada 1 hora")
    print_info("Presiona Enter para cada paso...\n")
    
    scenarios = [
        # Mañana (5-11h): Poco solar
        {"hora": "05:00", "consumo": 35, "solar": 2, "bateria": 40, "desc": "Madrugada: bajo consumo"},
        {"hora": "06:00", "consumo": 38, "solar": 5, "bateria": 42, "desc": "Amanecer: solar leve"},
        {"hora": "07:00", "consumo": 42, "solar": 15, "bateria": 45, "desc": "Mañana temprano"},
        {"hora": "08:00", "consumo": 48, "solar": 35, "bateria": 55, "desc": "Día empieza"},
        {"hora": "09:00", "consumo": 52, "solar": 55, "bateria": 65, "desc": "Mañana: buen solar"},
        
        # Mediodía (11-14h): Máximo solar
        {"hora": "10:00", "consumo": 50, "solar": 75, "bateria": 75, "desc": "Mediodía: máximo solar"},
        {"hora": "11:00", "consumo": 48, "solar": 85, "bateria": 85, "desc": "Solar al máximo"},
        {"hora": "12:00", "consumo": 52, "solar": 90, "bateria": 95, "desc": "Pico solar"},
        {"hora": "13:00", "consumo": 55, "solar": 88, "bateria": 100, "desc": "Batería llena"},
        
        # Tarde (14-17h): Baja solar
        {"hora": "14:00", "consumo": 58, "solar": 70, "bateria": 100, "desc": "Tarde: solar baja"},
        {"hora": "15:00", "consumo": 60, "solar": 50, "bateria": 95, "desc": "Tarde: consumo sube"},
        {"hora": "16:00", "consumo": 65, "solar": 30, "bateria": 85, "desc": "Atardecer: solar cae"},
        
        # Peak (17-21h): Máximo consumo
        {"hora": "17:00", "consumo": 72, "solar": 15, "bateria": 70, "desc": "PEAK: máximo consumo"},
        {"hora": "18:00", "consumo": 75, "solar": 5, "bateria": 55, "desc": "Peak: descargar batería"},
        {"hora": "19:00", "consumo": 70, "solar": 2, "bateria": 40, "desc": "Noche: uso batería"},
        {"hora": "20:00", "consumo": 65, "solar": 0, "bateria": 25, "desc": "Noche: bajo consumo"},
        {"hora": "21:00", "consumo": 45, "solar": 0, "bateria": 20, "desc": "Noche: batería baja"},
        
        # Noche (21-5h): Mínimo
        {"hora": "22:00", "consumo": 38, "solar": 0, "bateria": 18, "desc": "Noche: mínimo"},
        {"hora": "23:00", "consumo": 35, "solar": 0, "bateria": 16, "desc": "Medianoche"},
        {"hora": "00:00", "consumo": 32, "solar": 0, "bateria": 15, "desc": "Madrugada"},
        {"hora": "04:00", "consumo": 30, "solar": 0, "bateria": 14, "desc": "Últimas horas noche"},
    ]
    
    total_cost = 0
    actions_count = {"charge": 0, "discharge": 0, "idle": 0}
    
    for i, scenario in enumerate(scenarios, 1):
        print_section(f"Hora {i}: {scenario['hora']} - {scenario['desc']}")
        
        print_info(f"📊 Consumo: {scenario['consumo']} kW")
        print_info(f"☀️  Solar: {scenario['solar']} kW")
        print_info(f"🔋 Batería: {scenario['bateria']}%")
        
        # Simular decisión
        if scenario['solar'] > 50 and scenario['bateria'] < 90:
            action = "charge"
            ahorro = 2
        elif scenario['consumo'] > 60 and scenario['bateria'] > 20:
            action = "discharge"
            ahorro = 3
        else:
            action = "idle"
            ahorro = 0
        
        actions_count[action] += 1
        total_cost += (scenario['consumo'] * 0.15) - ahorro  # Simular costo
        
        print_success(f"⚡ Acción: {action.upper()} → Ahorro: €{ahorro}")
        print()
        
        if i < len(scenarios):
            input(f"Presiona Enter para siguiente hora...")
            print()
    
    # Resumen
    print_header("📊 RESUMEN DEL DÍA")
    print_section("Acciones ejecutadas")
    print(f"  Carga (CHARGE): {actions_count['charge']} veces")
    print(f"  Descarga (DISCHARGE): {actions_count['discharge']} veces")
    print(f"  Espera (IDLE): {actions_count['idle']} veces")
    
    print_section("Resultados")
    print(f"  Costo total: €{total_cost:.2f}")
    print_success(f"  Ahorro estimado: €{total_cost * 0.25:.2f} (sin IA sería 25% más)")

# ============================================================================
# 7. MENÚ INTERACTIVO
# ============================================================================

def menu():
    """Menú principal"""
    while True:
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
        print("  🎮 PVBESSCAR - SIMULADOR INTERACTIVO")
        print(f"{'='*60}{Colors.END}")
        
        print(f"\n{Colors.BOLD}Opciones:{Colors.END}")
        print("1. ✅ Health Check")
        print("2. 📊 Ver Estado Sistema")
        print("3. 📈 Leer Métricas")
        print("4. 🤖 Decidir Acción IA")
        print("5. ⚡ Ejecutar Acción")
        print("6. 🔄 Ciclo Completo (1-5)")
        print("7. 🌅 Simular Día Completo")
        print("8. 📖 Ver Guía")
        print("9. ❌ Salir")
        
        opcion = input(f"\n{Colors.BOLD}Selecciona opción (1-9): {Colors.END}").strip()
        
        if opcion == "1":
            health_check()
        
        elif opcion == "2":
            system_status()
        
        elif opcion == "3":
            metrics = read_metrics()
        
        elif opcion == "4":
            if 'metrics' in locals() and metrics:
                action, value = decide_action(metrics)
                input("\nPresiona Enter para continuar...")
            else:
                print_warning("Primero debes leer métricas (opción 3)")
        
        elif opcion == "5":
            if 'action' in locals():
                execute_action(action, value)
                input("\nPresiona Enter para continuar...")
            else:
                print_warning("Primero debes decidir acción (opción 4)")
        
        elif opcion == "6":
            health_check()
            input("Presiona Enter...")
            system_status()
            input("Presiona Enter...")
            metrics = read_metrics()
            input("Presiona Enter...")
            action, value = decide_action(metrics)
            input("Presiona Enter...")
            execute_action(action, value)
            input("Presiona Enter para continuar...")
        
        elif opcion == "7":
            simulate_day()
        
        elif opcion == "8":
            print_header("📖 GUÍA RÁPIDA")
            print("""
El sistema PVBESSCAR funciona así:

1. SENSORES: Leen consumo, solar, batería, precio
2. IA (ML): Predice futuro con modelos entrenados
3. CONTROLADOR: Optimiza decisión (cargar/descargar/esperar)
4. EJECUTA: Envía comando a hardware
5. RESULTADO: Menor costo, menos CO2

ACCIONES DISPONIBLES:
- CHARGE:   Carga batería (almacena energía solar)
- DISCHARGE: Descarga batería (evita pagar a red)
- IDLE:     Espera (sistema equilibrado)

VALORES A PROPORCIONAR:
- action: "charge" | "discharge" | "idle"
- value: 0-100 (potencia en kW, opcional)

ENDPOINTS API:
- GET /health               → Verificar sistema
- GET /api/status          → Estado componentes  
- GET /api/metrics         → Métricas en tiempo real
- POST /api/control        → Ejecutar acción

DOCUMENTACIÓN COMPLETA:
http://localhost:8000/docs  (Swagger UI interactivo)
            """)
            input("Presiona Enter para volver...")
        
        elif opcion == "9":
            print_success("¡Hasta luego!")
            break
        
        else:
            print_error("Opción no válida")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════╗
║           🌞 PVBESSCAR - SIMULADOR INTERACTIVO 🔋        ║
║                                                           ║
║  Sistema de Gestión Inteligente de Energía en Edificios  ║
║                 con Inteligencia Artificial               ║
╚═══════════════════════════════════════════════════════════╝
{Colors.END}
    """)
    
    if health_check():
        print_success("Sistema listo para simular")
        input("\nPresiona Enter para comenzar...")
        menu()
    else:
        print_error("No se puede conectar al API")
        print_info("Asegúrate de que FastAPI está corriendo:")
        print("  py -3.11 fastapi_server.py")
