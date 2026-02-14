#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper para ejecutar train_a2c_multiobjetivo.py con PYTHONPATH configurado
"""
import sys
from pathlib import Path

# Agregar raíz del proyecto al PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Importar y ejecutar el script de entrenamiento
from scripts.train.train_a2c_multiobjetivo import *
