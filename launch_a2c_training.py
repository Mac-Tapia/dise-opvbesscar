#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper para lanzar entrenamiento A2C ejecutando como módulo
"""
import sys
import os
import subprocess
from pathlib import Path

if __name__ == '__main__':
    # Configurar PYTHONPATH
    project_root = Path(__file__).parent.absolute()
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    # Ejecutar como módulo
    result = subprocess.run([
        sys.executable, 
        '-m', 'scripts.train.train_a2c_multiobjetivo'
    ], cwd=str(project_root), env=env)
    
    sys.exit(result.returncode)
