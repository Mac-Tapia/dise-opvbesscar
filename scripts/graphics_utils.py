#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades compartidas para generación de gráficas de entrenamiento RL.
Centraliza: paleta de colores, carga de datos, funciones de suavizado, setup matplotlib.
"""
from __future__ import annotations

import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d
from typing import Tuple

# ── Paleta de colores (proyecto) ──────────────────────────────────────────────
C_SAC   = '#1F77B4'    # azul
C_PPO   = '#FF7F0E'    # naranja
C_A2C   = '#2CA02C'    # verde
C_BL    = '#D62728'    # rojo (baseline)
C_DIFF  = '#7B2D8B'    # morado (diferencias)
C_HEAD  = '#1A3A5C'    # azul oscuro encabezado
C_SUB   = '#2E6DA4'    # azul subencabezado
C_ALT   = '#EBF3FD'    # fila alternada
C_WIN   = '#D4EFDF'    # fila ganadora
C_WARN  = '#FDECEA'    # fila advertencia
C_OK    = '#1E8449'    # tick verde
C_NO    = '#922B21'    # cruz roja

# ── Rutas base ────────────────────────────────────────────────────────────────
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]

def get_output_dir() -> pathlib.Path:
    """Obtiene directorio de salida de gráficas."""
    out_dir = BASE_DIR / 'outputs/docx/graficas'
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def load_training_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga datos de entrenamiento SAC, PPO, A2C.

    Returns:
        Tupla (sac_df, ppo_df, a2c_df)
    """
    sac_csv = BASE_DIR / 'outputs/sac_training/sac_episodios_history.csv'
    ppo_csv = BASE_DIR / 'outputs/ppo_training/ppo_episodios_history.csv'
    a2c_csv = BASE_DIR / 'outputs/a2c_training/a2c_episodios_history.csv'

    sac = pd.read_csv(sac_csv)
    ppo = pd.read_csv(ppo_csv)
    a2c = pd.read_csv(a2c_csv)

    return sac, ppo, a2c

def load_convergence_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga datos de convergencia (alternativa para reward)."""
    sac_csv = BASE_DIR / 'outputs/sac_training/sac_convergencia_episodios.csv'
    ppo_csv = BASE_DIR / 'outputs/ppo_training/ppo_convergencia_episodios.csv'
    a2c_csv = BASE_DIR / 'outputs/a2c_training/a2c_convergencia_episodios.csv'

    sac = pd.read_csv(sac_csv)
    ppo = pd.read_csv(ppo_csv)
    a2c = pd.read_csv(a2c_csv)

    return sac, ppo, a2c

def smooth(arr: np.ndarray, w: int = 5) -> np.ndarray:
    """Aplica suavizado con media móvil uniforme."""
    return uniform_filter1d(arr.astype(float), size=w)

def save_figure(fig: plt.Figure, filename: str, dpi: int = 300) -> pathlib.Path:
    """Guarda figura en outputs/docx/graficas."""
    out_dir = get_output_dir()
    path = out_dir / filename
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    return path
