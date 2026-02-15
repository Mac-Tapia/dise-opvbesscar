#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 EJECUTAR - Punto de Entrada Unificado para pvbesscar
========================================================

Script simplificado para ejecutar el sistema de optimización de carga EV
con Solar PV + BESS mediante Reinforcement Learning.

Uso:
    python ejecutar.py --agent a2c              # Entrenar A2C (RECOMENDADO)
    python ejecutar.py --agent ppo              # Entrenar PPO
    python ejecutar.py --agent sac              # Entrenar SAC
    python ejecutar.py --validate               # Solo validar sistema
    python ejecutar.py --help                   # Mostrar ayuda

Agentes Disponibles:
    - A2C: Advantage Actor-Critic (PRODUCCIÓN - 64.3% reducción CO₂)
    - PPO: Proximal Policy Optimization (47.5% reducción CO₂)
    - SAC: Soft Actor-Critic (43.3% reducción CO₂)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ===== COLORES PARA TERMINAL =====
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header():
    """Mostrar cabecera del script"""
    print()
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}🚀 PVBESSCAR - Optimización de Carga EV con RL{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'=' * 80}{Colors.ENDC}")
    print()
    print(f"{Colors.OKCYAN}📍 Ubicación: Iquitos, Perú (red aislada){Colors.ENDC}")
    print(f"{Colors.OKCYAN}⚡ Infraestructura: 38 sockets (19 chargers × 2){Colors.ENDC}")
    print(f"{Colors.OKCYAN}☀️  Solar PV: 4,050 kWp{Colors.ENDC}")
    print(f"{Colors.OKCYAN}🔋 BESS: 940 kWh / 342 kW{Colors.ENDC}")
    print()


def check_python_version() -> bool:
    """Verificar versión de Python"""
    print(f"{Colors.BOLD}[1/4] Verificando versión de Python...{Colors.ENDC}")
    
    version = sys.version_info
    if version.major == 3 and version.minor == 11:
        print(f"{Colors.OKGREEN}  ✓ Python {version.major}.{version.minor}.{version.micro} (CORRECTO){Colors.ENDC}")
        return True
    elif version.major == 3 and version.minor == 12:
        print(f"{Colors.WARNING}  ⚠ Python {version.major}.{version.minor}.{version.micro} (ADVERTENCIA){Colors.ENDC}")
        print(f"{Colors.WARNING}    Recomendado: Python 3.11, pero continuando...{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ Python {version.major}.{version.minor}.{version.micro} (INCOMPATIBLE){Colors.ENDC}")
        print(f"{Colors.FAIL}    Se requiere Python 3.11 o 3.12{Colors.ENDC}")
        return False


def check_dependencies() -> bool:
    """Verificar dependencias instaladas"""
    print(f"\n{Colors.BOLD}[2/4] Verificando dependencias...{Colors.ENDC}")
    
    required_packages = [
        'numpy',
        'pandas',
        'torch',
        'gymnasium',
        'stable_baselines3',
        'yaml'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"{Colors.OKGREEN}  ✓ {package}{Colors.ENDC}")
        except ImportError:
            missing.append(package)
            print(f"{Colors.FAIL}  ✗ {package} (NO INSTALADO){Colors.ENDC}")
    
    if missing:
        print()
        print(f"{Colors.WARNING}📦 Instalar dependencias faltantes:{Colors.ENDC}")
        print(f"{Colors.WARNING}   pip install -r requirements.txt{Colors.ENDC}")
        return False
    
    return True


def check_datasets() -> bool:
    """Verificar datasets OE2"""
    print(f"\n{Colors.BOLD}[3/4] Verificando datasets OE2...{Colors.ENDC}")
    
    datasets = {
        'Solar': 'data/interim/oe2/solar/pv_generation_timeseries.csv',
        'Chargers': 'data/interim/oe2/chargers/chargers_hourly_dataset.csv',
        'BESS': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
        'Mall': 'data/interim/oe2/mall/mall_demand_hourly.csv'
    }
    
    all_exist = True
    for name, path in datasets.items():
        if Path(path).exists():
            print(f"{Colors.OKGREEN}  ✓ {name}: {path}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}  ⚠ {name}: {path} (NO ENCONTRADO){Colors.ENDC}")
            all_exist = False
    
    if not all_exist:
        print(f"\n{Colors.WARNING}⚠️  Algunos datasets no encontrados, pero continuando...{Colors.ENDC}")
    
    return True  # Continue even if some missing


def check_environment() -> bool:
    """Verificar entorno GPU/CPU"""
    print(f"\n{Colors.BOLD}[4/4] Verificando entorno de ejecución...{Colors.ENDC}")
    
    try:
        import torch
        if torch.cuda.is_available():
            device = torch.cuda.get_device_name(0)
            print(f"{Colors.OKGREEN}  ✓ GPU disponible: {device}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}  ⚠ Solo CPU disponible (entrenamiento será lento){Colors.ENDC}")
    except ImportError:
        print(f"{Colors.WARNING}  ⚠ PyTorch no instalado, no se puede verificar GPU{Colors.ENDC}")
    
    return True


def run_validation() -> int:
    """Ejecutar solo validación del sistema"""
    print()
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}🔍 MODO VALIDACIÓN{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'=' * 80}{Colors.ENDC}")
    print()
    
    # Verificaciones
    if not check_python_version():
        return 1
    
    if not check_dependencies():
        return 1
    
    check_datasets()
    check_environment()
    
    print()
    print(f"{Colors.OKGREEN}{Colors.BOLD}✓ Validación completada{Colors.ENDC}")
    print()
    print(f"{Colors.OKCYAN}Siguiente paso:{Colors.ENDC}")
    print(f"{Colors.OKCYAN}  python ejecutar.py --agent a2c{Colors.ENDC}")
    print()
    
    return 0


def run_training(agent: str) -> int:
    """Ejecutar entrenamiento de agente específico"""
    print()
    print(f"{Colors.BOLD}{Colors.OKGREEN}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}🎯 ENTRENAMIENTO {agent.upper()}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}{'=' * 80}{Colors.ENDC}")
    print()
    
    # Verificaciones previas
    if not check_python_version():
        return 1
    
    if not check_dependencies():
        return 1
    
    check_datasets()
    check_environment()
    
    # Mapeo de agentes a scripts
    agent_scripts = {
        'a2c': 'scripts/train/train_a2c_multiobjetivo.py',
        'ppo': 'scripts/train/train_ppo_multiobjetivo.py',
        'sac': 'scripts/train/train_sac_multiobjetivo.py'
    }
    
    script_path = agent_scripts.get(agent.lower())
    if not script_path:
        print(f"{Colors.FAIL}✗ Agente '{agent}' no reconocido{Colors.ENDC}")
        print(f"{Colors.FAIL}  Opciones válidas: a2c, ppo, sac{Colors.ENDC}")
        return 1
    
    if not Path(script_path).exists():
        print(f"{Colors.FAIL}✗ Script no encontrado: {script_path}{Colors.ENDC}")
        return 1
    
    # Información del agente
    agent_info = {
        'a2c': ('⭐ RECOMENDADO', '64.3% reducción CO₂', '~2 horas'),
        'ppo': ('Alternativa', '47.5% reducción CO₂', '~2.5 horas'),
        'sac': ('Alternativa', '43.3% reducción CO₂', '~10 horas')
    }
    
    status, reduction, time = agent_info.get(agent.lower(), ('', '', ''))
    
    print(f"\n{Colors.BOLD}Agente seleccionado: {agent.upper()}{Colors.ENDC}")
    print(f"  Estado: {status}")
    print(f"  Reducción CO₂ esperada: {reduction}")
    print(f"  Tiempo estimado: {time}")
    print()
    
    print(f"{Colors.BOLD}Configuración de entrenamiento:{Colors.ENDC}")
    print(f"  • Episodios: 10 × 8,760 horas = 87,600 timesteps")
    print(f"  • Resolución temporal: 1 hora")
    print(f"  • Ambiente: CityLearn v2")
    print(f"  • Reward: Multi-objetivo (CO₂, Solar, EV, Cost, Grid)")
    print()
    
    print(f"{Colors.WARNING}⏳ Iniciando entrenamiento...{Colors.ENDC}")
    print(f"{Colors.WARNING}   Esto puede tardar varias horas. Presione Ctrl+C para cancelar.{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print()
    
    # Ejecutar script de entrenamiento
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=False
        )
        
        if result.returncode == 0:
            print()
            print(f"{Colors.BOLD}{Colors.OKGREEN}{'=' * 80}{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.OKGREEN}✓ ENTRENAMIENTO {agent.upper()} COMPLETADO{Colors.ENDC}")
            print(f"{Colors.BOLD}{Colors.OKGREEN}{'=' * 80}{Colors.ENDC}")
            print()
            print(f"{Colors.OKCYAN}Resultados guardados en:{Colors.ENDC}")
            print(f"{Colors.OKCYAN}  • checkpoints/{agent.upper()}/latest.zip{Colors.ENDC}")
            print(f"{Colors.OKCYAN}  • outputs/{agent}_training/{Colors.ENDC}")
            print()
        else:
            print()
            print(f"{Colors.FAIL}✗ Entrenamiento finalizado con errores (código: {result.returncode}){Colors.ENDC}")
            print()
        
        return result.returncode
        
    except KeyboardInterrupt:
        print()
        print(f"{Colors.WARNING}⚠️  Entrenamiento interrumpido por el usuario{Colors.ENDC}")
        return 130
    except Exception as e:
        print()
        print(f"{Colors.FAIL}✗ Error durante el entrenamiento: {e}{Colors.ENDC}")
        return 1


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='🚀 PVBESSCAR - Optimización de Carga EV con RL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python ejecutar.py --agent a2c       # Entrenar A2C (RECOMENDADO para producción)
  python ejecutar.py --agent ppo       # Entrenar PPO
  python ejecutar.py --agent sac       # Entrenar SAC
  python ejecutar.py --validate        # Solo validar sistema sin entrenar

Agentes disponibles:
  A2C: ⭐ RECOMENDADO - 64.3%% reducción CO₂, convergencia rápida (2h)
  PPO: Alternativa - 47.5%% reducción CO₂, convergencia lenta (2.5h)
  SAC: Alternativa - 43.3%% reducción CO₂, convergencia muy lenta (10h)

Para más información, ver README.md
        """
    )
    
    parser.add_argument(
        '--agent',
        type=str,
        choices=['a2c', 'ppo', 'sac'],
        help='Agente RL a entrenar (a2c, ppo, sac)'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Solo validar sistema sin entrenar'
    )
    
    args = parser.parse_args()
    
    # Mostrar cabecera
    print_header()
    
    # Ejecutar modo seleccionado
    if args.validate:
        return run_validation()
    elif args.agent:
        return run_training(args.agent)
    else:
        parser.print_help()
        print()
        print(f"{Colors.WARNING}⚠️  Debe especificar --agent o --validate{Colors.ENDC}")
        print()
        print(f"{Colors.OKCYAN}Ejemplos:{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  python ejecutar.py --agent a2c{Colors.ENDC}")
        print(f"{Colors.OKCYAN}  python ejecutar.py --validate{Colors.ENDC}")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
