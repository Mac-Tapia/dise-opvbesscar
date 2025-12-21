#!/usr/bin/env python3
"""
VERIFICADOR DE REQUERIMIENTOS - Validación completa del entorno
Compara requirements.txt con paquetes instalados
"""

import subprocess
import sys
from pathlib import Path
from packaging import version

# Colores
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

class VerificadorRequerimientos:
    def __init__(self):
        self.proyecto_root = Path(__file__).parent.parent
        self.requirements_path = self.proyecto_root / "requirements.txt"
        self.resultados = []
        
    def leer_requirements(self):
        """Lee requirements.txt y retorna lista de (paquete, versión_minima)"""
        if not self.requirements_path.exists():
            print(f"{RED}❌ requirements.txt no encontrado{RESET}")
            return []
        
        requerimientos = []
        lineas = self.requirements_path.read_text().strip().split('\n')
        
        for linea in lineas:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            
            # Parsear formato: paquete>=version
            if '>=' in linea:
                paquete, ver_min = linea.split('>=')
                requerimientos.append((paquete.strip(), ver_min.strip(), '>='))
            elif '==' in linea:
                paquete, ver_exact = linea.split('==')
                requerimientos.append((paquete.strip(), ver_exact.strip(), '=='))
            else:
                requerimientos.append((linea.strip(), '0.0.0', '>='))
        
        return requerimientos
    
    def obtener_versiones_instaladas(self):
        """Obtiene versiones de paquetes instalados"""
        try:
            resultado = subprocess.run(
                [sys.executable, '-m', 'pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if resultado.returncode == 0:
                import json
                return {pkg['name'].lower(): pkg['version'] for pkg in json.loads(resultado.stdout)}
        except Exception as e:
            print(f"{YELLOW}⚠️  Error obteniendo versiones: {e}{RESET}")
        return {}
    
    def comparar_versiones(self, requerida, instalada, operador):
        """Compara versiones según operador"""
        try:
            v_req = version.parse(requerida)
            v_inst = version.parse(instalada)
            
            if operador == '>=':
                return v_inst >= v_req
            elif operador == '==':
                return v_inst == v_req
            return False
        except Exception:
            return False
    
    def verificar(self):
        """Realiza verificación completa"""
        print(f"\n{BOLD}{CYAN}{'='*70}")
        print("VERIFICADOR DE REQUERIMIENTOS - ENTORNO DEL PROYECTO")
        print(f"{'='*70}{RESET}\n")
        
        # Leer requerimientos
        requerimientos = self.leer_requirements()
        print(f"📦 Requerimientos especificados: {len(requerimientos)}\n")
        
        # Obtener instalados
        instalados = self.obtener_versiones_instaladas()
        print(f"📦 Paquetes instalados en entorno: {len(instalados)}\n")
        
        # Verificar cada requerimiento
        print(f"{BOLD}VERIFICACIÓN DETALLADA:{RESET}\n")
        
        cumplidos = 0
        incumplidos = []
        
        for paquete, ver_requerida, operador in requerimientos:
            paquete_lower = paquete.lower()
            
            if paquete_lower in instalados:
                ver_instalada = instalados[paquete_lower]
                cumple = self.comparar_versiones(ver_requerida, ver_instalada, operador)
                
                if cumple:
                    print(f"{GREEN}✅ {paquete:<20}{RESET} {ver_instalada:<15} (requerida: {operador}{ver_requerida})")
                    cumplidos += 1
                else:
                    print(f"{RED}❌ {paquete:<20}{RESET} {ver_instalada:<15} {RED}(requerida: {operador}{ver_requerida}){RESET}")
                    incumplidos.append((paquete, ver_instalada, ver_requerida))
            else:
                print(f"{RED}❌ {paquete:<20}{RESET} {RED}NO INSTALADO{RESET} (requerida: {operador}{ver_requerida})")
                incumplidos.append((paquete, "NO INSTALADO", ver_requerida))
        
        # Resumen
        print(f"\n{BOLD}{CYAN}{'='*70}")
        print("RESUMEN")
        print(f"{'='*70}{RESET}\n")
        
        total = len(requerimientos)
        print(f"{GREEN}✅ Cumplidos: {cumplidos}/{total}{RESET}")
        print(f"{RED}❌ Incumplidos: {len(incumplidos)}/{total}{RESET}\n")
        
        if incumplidos:
            print(f"{BOLD}{RED}PAQUETES QUE NECESITAN ACTUALIZACIÓN:{RESET}\n")
            for paquete, actual, requerida in incumplidos:
                print(f"  • {paquete}")
                if actual != "NO INSTALADO":
                    print(f"    Actual: {actual} → Requerida: {requerida}")
                else:
                    print(f"    Estado: No instalado")
            
            print(f"\n{YELLOW}Para instalar/actualizar, ejecuta:{RESET}")
            print(f"\n{BOLD}pip install -r requirements.txt{RESET}\n")
            return False
        else:
            print(f"{GREEN}{BOLD}✅ TODOS LOS REQUERIMIENTOS INSTALADOS Y ACTUALIZADOS{RESET}\n")
            print(f"El entorno está listo para ejecutar el proyecto.\n")
            return True
    
    def mostrar_entorno(self):
        """Muestra información del entorno"""
        print(f"\n{BOLD}INFORMACIÓN DEL ENTORNO:{RESET}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Proyecto: {self.proyecto_root}")
        print(f"Entorno: {'.venv' if ('.venv' in str(sys.executable)) else 'Sistema/Otro'}\n")


if __name__ == "__main__":
    verificador = VerificadorRequerimientos()
    verificador.mostrar_entorno()
    exito = verificador.verificar()
    sys.exit(0 if exito else 1)
