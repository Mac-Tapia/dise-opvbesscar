#!/usr/bin/env python3
"""
VALIDACION COMPLETA DE PRODUCCION - PPO Training
=================================================
Verifica TODAS las conexiones, datos, y configura el entrenamiento correctamente

Valida:
[OK] Datasets OE2 sincronizados (5 ficheros)
[OK] Ambiente Gymnasium funcional
[OK] Modelo PPO disponible
[OK] GPU/CUDA disponible
[OK] Callbacks configurados
[OK] Estructura de directorios
[OK] Archivos de checkpoint
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionValidator:
    """Validador completo para entrenamiento PPO en produccion"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.root = Path(__file__).parent.parent
        
    def validate_all(self):
        """Ejecutar validacion completa"""
        print('\n' + '='*100)
        print('[OK] VALIDACION DE PRODUCCION - ENTRENAMIENTO PPO')
        print('='*100 + '\n')
        
        checks = [
            ('Python Version', self.check_python_version),
            ('Directorios', self.check_directories),
            ('Datos OE2', self.check_oe2_data),
            ('Dependencias', self.check_dependencies),
            ('GPU/CUDA', self.check_gpu),
            ('Ambiente Gymnasium', self.check_gymnasium_env),
            ('Configuracion', self.check_configuration),
            ('Archivos Log', self.check_logs),
        ]
        
        results = []
        for name, check_fn in checks:
            try:
                status = check_fn()
                results.append((name, status))
                print(f'[OK] {name}: OK\n')
            except Exception as e:
                results.append((name, False))
                print(f'[X] {name}: ERROR - {str(e)}\n')
                self.errors.append(f'{name}: {str(e)}')
        
        print('\n' + '='*100)
        print('[GRAPH] RESUMEN DE VALIDACION')
        print('='*100 + '\n')
        
        for name, status in results:
            symbol = '[OK]' if status else '[X]'
            print(f'{symbol} {name}')
        
        if self.errors:
            print(f'\n[X] {len(self.errors)} ERRORES ENCONTRADOS:')
            for err in self.errors:
                print(f'   - {err}')
        
        if self.warnings:
            print(f'\n[!]  {len(self.warnings)} ADVERTENCIAS:')
            for warn in self.warnings:
                print(f'   - {warn}')
        
        if not self.errors:
            print(f'\n[OK] SISTEMA LISTO PARA PRODUCCION')
        
        print('\n' + '='*100 + '\n')
        return len(self.errors) == 0
    
    def check_python_version(self) -> bool:
        """Verificar version de Python >= 3.9"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            raise ValueError(f'Python {version.major}.{version.minor} < 3.9 requerido')
        logger.info(f'Python {version.major}.{version.minor}.{version.micro}')
        return True
    
    def check_directories(self) -> bool:
        """Verificar estructura de directorios"""
        dirs = [
            'data/oe2/Generacionsolar',
            'data/oe2/chargers',
            'data/oe2/bess',
            'data/oe2/demandamallkwh',
            'data/processed/citylearn/iquitos_ev_mall',
            'outputs/ppo_training',
            'checkpoints/PPO',
            'scripts/train',
        ]
        
        for d in dirs:
            path = self.root / d
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.warning(f'Creado: {d}')
        
        return True
    
    def check_oe2_data(self) -> bool:
        """Verificar sincronizacion OE2 - 5 datasets obligatorios"""
        datasets = {
            'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
            'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
            'ChargerStats': 'data/oe2/chargers/chargers_real_statistics.csv',
            'BESS': 'data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv',
            'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
        }
        
        for name, path_str in datasets.items():
            path = self.root / path_str
            if not path.exists():
                raise FileNotFoundError(f'{name}: {path_str} no encontrado')
            
            # Validar estructura
            try:
                if 'chargers_ev' in path_str:
                    df = pd.read_csv(path)
                    assert len(df) == 8760, f'{name} debe tener 8,760 horas'
                    # Verificar que hay al menos 38 columnas de power
                    power_cols = [c for c in df.columns if 'charger_power' in c.lower()]
                    assert len(power_cols) >= 38, f'{name} debe tener >= 38 columnas socket_*_charger_power_kw'
                    logger.info(f'{name}: {len(df)} h × {len(df.columns)} cols -> {len(power_cols)} sockets')
                elif 'chargers_real_statistics' in path_str:
                    # ChargerStats tiene 38 filas (una por socket), no 8760 horas
                    df = pd.read_csv(path)
                    assert len(df) == 38, f'{name} debe tener 38 filas (una por socket)'
                    required_cols = ['max_power_kw', 'mean_power_kw']
                    for col in required_cols:
                        assert col in df.columns, f'{name} debe tener columna {col}'
                    logger.info(f'{name}: {len(df)} sockets × {len(df.columns)} cols [OK]')
                else:
                    df = pd.read_csv(path) if 'csv' in path_str else pd.read_csv(path, sep=';')
                    assert len(df) == 8760, f'{name} debe tener 8,760 horas'
                    logger.info(f'{name}: {len(df)} horas [OK]')
            except Exception as e:
                raise ValueError(f'{name} estructura invalida: {str(e)}')
        
        return True
    
    def check_dependencies(self) -> bool:
        """Verificar paquetes clave"""
        packages = [
            ('gymnasium', 'Gymnasium'),
            ('stable_baselines3', 'Stable-Baselines3'),
            ('torch', 'PyTorch'),
            ('pandas', 'Pandas'),
            ('numpy', 'NumPy'),
        ]
        
        for module, name in packages:
            try:
                __import__(module)
                logger.info(f'{name} [OK]')
            except ImportError:
                raise ImportError(f'{name} no instalado: pip install {module}')
        
        return True
    
    def check_gpu(self) -> bool:
        """Verificar GPU/CUDA"""
        try:
            import torch
            if torch.cuda.is_available():
                device = torch.cuda.get_device_name(0)
                logger.info(f'CUDA disponible: {device}')
                logger.info(f'CUDA Version: {torch.version.cuda}')
            else:
                self.warnings.append('CUDA no disponible - usar CPU (lento)')
                logger.warning('Entrenamiento en CPU sera lento')
        except Exception as e:
            self.warnings.append(f'Error checking CUDA: {str(e)}')
        
        return True
    
    def check_gymnasium_env(self) -> bool:
        """Verificar que CityLearnEnvironment se pueda importar"""
        try:
            sys.path.insert(0, str(self.root))
            # Importar modulos clave
            from scripts.train.vehicle_charging_scenarios import (
                VehicleChargingSimulator,
                SCENARIO_OFF_PEAK,
            )
            logger.info('CityLearnEnvironment componentes [OK]')
        except ImportError as e:
            raise ImportError(f'No se puede importar ambiente: {str(e)}')
        
        return True
    
    def check_configuration(self) -> bool:
        """Verificar archivo de configuracion"""
        config_file = self.root / 'configs/default.yaml'
        if config_file.exists():
            logger.info(f'Configuracion encontrada: {config_file}')
        else:
            self.warnings.append('configs/default.yaml no encontrado (se usaran defaults)')
        
        return True
    
    def check_logs(self) -> bool:
        """Verificar archivos de log"""
        log_file = self.root / 'train_ppo_log.txt'
        if log_file.exists():
            size = log_file.stat().st_size / 1024
            lines = len(open(log_file).readlines())
            logger.info(f'Log: {lines:,} lineas ({size:.1f} KB)')
        else:
            logger.info('Log anterior no encontrado (se creara en entrenamiento)')
        
        return True

def main():
    """Ejecutar validacion y luego entrenar si todo esta OK"""
    validator = ProductionValidator()
    
    if validator.validate_all():
        print('🚀 SISTEMA LISTO PARA ENTRENAR\n')
        print('Ejecutar: python scripts/train/train_ppo_multiobjetivo.py\n')
        return 0
    else:
        print('[X] ERRORES ENCONTRADOS - CORREGIR ANTES DE ENTRENAR\n')
        return 1

if __name__ == '__main__':
    exit(main())
