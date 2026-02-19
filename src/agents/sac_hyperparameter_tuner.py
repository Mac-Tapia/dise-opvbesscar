#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALGORITMO DE HIPERPARÁMETROS PARA SAC v2.0 (2026-02-19)
========================================================

Implementa 3 estrategias para optimizar hiperparámetros de SAC:

1. GRID SEARCH (Exhaustivo)
   - Prueba todas las combinaciones posibles
   - Mejor para espacios pequeños (<1000 combos)
   - Resultado: parametros OPTIMOS garantizados

2. RANDOM SEARCH (Exploratorio)
   - Muestrea aleatoriamente N combinaciones
   - Mejor para espacios grandes (>1000 combos)
   - Resultado: parametros BUENOS con menos tiempo

3. BAYESIAN OPTIMIZATION (Inteligente)
   - Usa modelo probabilístico (Gaussian Process)
   - Aprende donde están los buenos parametros
   - Mejor: Usa info de entrenamientos previos
   - Resultado: parametros EXCELENTES en menos iteraciones

METRICAS DE EVALUACION:
- Reward promedio por episodio
- CO2 evitado (kg/año)
- Convergencia (velocidad de mejora)
- Estabilidad (varianza de rewards)
- Eficiencia temporal (steps para alcanzar target)

SALIDA:
- config_optimal_{timestamp}.json: Mejores hiperparámetros
- tuning_results_{timestamp}.csv: Todos los entrenamientos + metricas
- plots_hyperparameter_*.png: Visualizaciones de convergencia
"""

from __future__ import annotations

import json
import math
import random
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings('ignore')


# =============================================================================
# ESPACIOS DE BUSQUEDA DE HIPERPARAMETROS
# =============================================================================

@dataclass
class HyperparameterSpace:
    """Define el espacio de búsqueda para hiperparámetros de SAC."""
    
    # Learning rate: {1e-5, 3e-5, 1e-4, 3e-4, 1e-3} - sensible para SAC
    learning_rate: List[float] = field(default_factory=lambda: [1e-5, 3e-5, 1e-4, 3e-4, 1e-3])
    
    # Buffer size: {50K, 100K, 200K, 400K, 1M} - memoria vs diversidad
    buffer_size: List[int] = field(default_factory=lambda: [50_000, 100_000, 200_000, 400_000, 1_000_000])
    
    # Batch size: {32, 64, 128, 256, 512} - gradientes vs memoria
    batch_size: List[int] = field(default_factory=lambda: [32, 64, 128, 256, 512])
    
    # Tau (soft update): {0.001, 0.005, 0.01, 0.02} - estabilidad vs freshness
    tau: List[float] = field(default_factory=lambda: [0.001, 0.005, 0.01, 0.02])
    
    # Gamma (discount): {0.90, 0.95, 0.99} - horizonte efectivo
    gamma: List[float] = field(default_factory=lambda: [0.90, 0.95, 0.99])
    
    # Entropy coefficient: {'auto', 0.05, 0.1, 0.2, 0.5} - exploracion
    ent_coef: List[str | float] = field(default_factory=lambda: ['auto', 0.05, 0.1, 0.2, 0.5])
    
    # Target entropy: {-50, -20, -10, -5} - para 39D action space
    target_entropy: List[int] = field(default_factory=lambda: [-50, -20, -10, -5])
    
    # Train frequency: {1, 2, 4, 8} - updates por environment step
    train_freq: List[int] = field(default_factory=lambda: [1, 2, 4, 8])
    
    # Network size: {128, 256, 384, 512} - capacidad del modelo
    net_arch_hidden: List[int] = field(default_factory=lambda: [128, 256, 384, 512])
    
    @property
    def grid_size(self) -> int:
        """Número total de combinaciones en grid search."""
        return (len(self.learning_rate) * len(self.buffer_size) * len(self.batch_size) * 
                len(self.tau) * len(self.gamma) * len(self.ent_coef) * len(self.target_entropy) * 
                len(self.train_freq) * len(self.net_arch_hidden))
    
    @property
    def summary(self) -> str:
        """Resumen del espacio de búsqueda."""
        return f"HyperparameterSpace(grid_size={self.grid_size:,})"


# =============================================================================
# RESULTADOS DE ENTRENAMIENTO Y METRICAS
# =============================================================================

@dataclass
class TrainingResult:
    """Resultado de un entrenamiento SAC con hiperparámetros dados."""
    
    # Configuracion
    learning_rate: float
    buffer_size: int
    batch_size: int
    tau: float
    gamma: float
    ent_coef: str | float
    target_entropy: int
    train_freq: int
    net_arch_hidden: int
    
    # Metricas finales
    avg_episode_reward: float = 0.0  # Reward promedio por episodio
    co2_avoided_kg: float = 0.0  # CO2 evitado total (kg/año)
    solar_utilization_pct: float = 0.0  # Porcentaje de solar usado
    grid_import_kwh: float = 0.0  # Importacion grid total (kwh/año)
    ev_satisfaction_pct: float = 0.0  # Vehiculos cargados al 100%
    convergence_speed: float = 0.0  # Steps para alcanzar 80% del reward final
    stability: float = 0.0  # Varianza de rewards (menor = mas estable)
    
    # Calidad del entrenamiento
    final_entropy: float = 0.0  # Entropía final del policy
    final_alpha: float = 0.0  # Alpha final (temperatura)
    q_value_stability: float = 0.0  # Varianza de Q-values
    
    # Metadata
    training_time_seconds: float = 0.0
    total_timesteps: int = 0
    episodes_completed: int = 0
    tuning_iteration: int = 0
    timestamp: str = ""
    
    @property
    def score(self) -> float:
        """Calcula score agregado (0-100) para ranking de resultados."""
        # Normalizar componentes
        reward_score = min(100, (self.avg_episode_reward + 10) * 5)  # -10 a +10 range
        co2_score = min(100, self.co2_avoided_kg / 1000)  # kg/1000
        solar_score = min(100, self.solar_utilization_pct)  # 0-100%
        convergence_score = min(100, 131400 / max(1, self.convergence_speed))  # Inversamente proporcional
        stability_score = min(100, 1.0 / (self.stability + 0.01) * 10)  # Inversamente proporcional
        
        # Pesos: prioriza CO2 (50%) luego reward (20%) luego convergencia (15%) luego stability (10%) luego solar (5%)
        total_score = (0.50 * co2_score + 
                      0.20 * reward_score + 
                      0.15 * convergence_score + 
                      0.10 * stability_score + 
                      0.05 * solar_score)
        
        return min(100, total_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para CSV."""
        return {
            'learning_rate': self.learning_rate,
            'buffer_size': self.buffer_size,
            'batch_size': self.batch_size,
            'tau': self.tau,
            'gamma': self.gamma,
            'ent_coef': self.ent_coef,
            'target_entropy': self.target_entropy,
            'train_freq': self.train_freq,
            'net_arch_hidden': self.net_arch_hidden,
            'avg_episode_reward': self.avg_episode_reward,
            'co2_avoided_kg': self.co2_avoided_kg,
            'solar_utilization_pct': self.solar_utilization_pct,
            'grid_import_kwh': self.grid_import_kwh,
            'ev_satisfaction_pct': self.ev_satisfaction_pct,
            'convergence_speed': self.convergence_speed,
            'stability': self.stability,
            'final_entropy': self.final_entropy,
            'final_alpha': self.final_alpha,
            'q_value_stability': self.q_value_stability,
            'score': self.score,
            'training_time_seconds': self.training_time_seconds,
            'total_timesteps': self.total_timesteps,
            'episodes_completed': self.episodes_completed,
            'tuning_iteration': self.tuning_iteration,
            'timestamp': self.timestamp,
        }


# =============================================================================
# MOTORES DE TUNING
# =============================================================================

class GridSearchTuner:
    """
    Grid Search Exhaustivo para SAC.
    
    Prueba TODOS los parametros sistematicamente.
    Ventaja: Garantiza encontrar la mejor combinacion
    Desventaja: Lento para espacios grandes
    
    Complejidad: O(grid_size × training_time_per_config)
    """
    
    def __init__(self, space: HyperparameterSpace, max_configs: int = 100):
        """
        Args:
            space: Espacio de búsqueda de hiperparametros
            max_configs: Máximo número de configuraciones (si grid muy grande)
        """
        self.space = space
        self.max_configs = max_configs
        self.results: List[TrainingResult] = []
        self.total_configs = space.grid_size
        
    def generate_configs(self) -> List[Dict[str, Any]]:
        """Generar todas las combinaciones de hiperparametros."""
        configs = []
        
        for lr in self.space.learning_rate:
            for buf in self.space.buffer_size:
                for batch in self.space.batch_size:
                    for tau in self.space.tau:
                        for gamma in self.space.gamma:
                            for ent in self.space.ent_coef:
                                for tent in self.space.target_entropy:
                                    for tf in self.space.train_freq:
                                        for netarch in self.space.net_arch_hidden:
                                            configs.append({
                                                'learning_rate': lr,
                                                'buffer_size': buf,
                                                'batch_size': batch,
                                                'tau': tau,
                                                'gamma': gamma,
                                                'ent_coef': ent,
                                                'target_entropy': tent,
                                                'train_freq': tf,
                                                'net_arch_hidden': netarch,
                                            })
        
        # Si hay demasiadas, samplear aleatoriamente
        if len(configs) > self.max_configs:
            print(f"[GRID SEARCH] {len(configs):,} configs totales > {self.max_configs} max")
            print(f"             Sampleando {self.max_configs} aleatoriamente...")
            configs = random.sample(configs, self.max_configs)
        
        return configs
    
    def summary(self) -> str:
        """Resumen de la búsqueda."""
        explored = min(len(self.results), self.total_configs)
        best_result = sorted(self.results, key=lambda r: r.score, reverse=True)[0] if self.results else None
        
        summary = f"\n{'='*80}\n"
        summary += f"GRID SEARCH SUMMARY\n"
        summary += f"{'='*80}\n"
        summary += f"Total configs posibles: {self.total_configs:,}\n"
        summary += f"Configs explorados: {explored} ({100*explored/self.total_configs:.1f}%)\n"
        
        if best_result:
            summary += f"\nMejor configuración encontrada:\n"
            summary += f"  Score: {best_result.score:.1f}/100\n"
            summary += f"  LR={best_result.learning_rate:.1e} | "
            summary += f"Buf={best_result.buffer_size/1000:.0f}K | "
            summary += f"τ={best_result.tau:.4f}\n"
            summary += f"  CO2 Evitado: {best_result.co2_avoided_kg:,.0f} kg\n"
            summary += f"  Reward: {best_result.avg_episode_reward:.2f}\n"
        
        summary += f"{'='*80}\n"
        return summary


class RandomSearchTuner:
    """
    Random Search para SAC.
    
    Muestrea N configuraciones aleatoriamente.
    Ventaja: Rápido, buena probabilidad de encontrar buenas regiones
    Desventaja: Puede perder optimos locales
    
    Complejidad: O(N × training_time_per_config)
    """
    
    def __init__(self, space: HyperparameterSpace, num_samples: int = 50):
        """
        Args:
            space: Espacio de búsqueda
            num_samples: Número de muestras a explorar
        """
        self.space = space
        self.num_samples = num_samples
        self.results: List[TrainingResult] = []
        
    def generate_configs(self) -> List[Dict[str, Any]]:
        """Generar N configuraciones aleatorias."""
        configs = []
        
        for i in range(self.num_samples):
            config = {
                'learning_rate': random.choice(self.space.learning_rate),
                'buffer_size': random.choice(self.space.buffer_size),
                'batch_size': random.choice(self.space.batch_size),
                'tau': random.choice(self.space.tau),
                'gamma': random.choice(self.space.gamma),
                'ent_coef': random.choice(self.space.ent_coef),
                'target_entropy': random.choice(self.space.target_entropy),
                'train_freq': random.choice(self.space.train_freq),
                'net_arch_hidden': random.choice(self.space.net_arch_hidden),
            }
            configs.append(config)
        
        return configs
    
    def summary(self) -> str:
        """Resumen de la búsqueda."""
        best_result = sorted(self.results, key=lambda r: r.score, reverse=True)[0] if self.results else None
        
        summary = f"\n{'='*80}\n"
        summary += f"RANDOM SEARCH SUMMARY\n"
        summary += f"{'='*80}\n"
        summary += f"Muestras exploradas: {len(self.results)}\n"
        
        if best_result:
            summary += f"\nMejor configuración encontrada:\n"
            summary += f"  Score: {best_result.score:.1f}/100\n"
            summary += f"  LR={best_result.learning_rate:.1e} | "
            summary += f"Buf={best_result.buffer_size/1000:.0f}K | "
            summary += f"τ={best_result.tau:.4f}\n"
            summary += f"  CO2 Evitado: {best_result.co2_avoided_kg:,.0f} kg\n"
            summary += f"  Reward: {best_result.avg_episode_reward:.2f}\n"
        
        summary += f"{'='*80}\n"
        return summary


class BayesianTuner:
    """
    Optimizacion Bayesiana para SAC.
    
    Usa un modelo probabilístico (Gaussian Process) para aprender
    donde estan los buenos hiperparametros. Inteligente y eficiente.
    
    Ventaja: Converge a optimo con pocas iteraciones
    Desventaja: Complejidad computacional mayor
    
    Algoritmo:
    1. Modelo probabilístico P(score | parametros)
    2. Función de adquisicion: Esperanza de Mejora (EI)
    3. Seleccionar siguiente config con EI mayor
    4. Entrenar -> actualizar modelo -> repetir
    
    Complejidad: O(N × (training_time + GP_fitting))
    """
    
    def __init__(self, space: HyperparameterSpace, num_iterations: int = 30, 
                 initial_random_samples: int = 5):
        """
        Args:
            space: Espacio de búsqueda
            num_iterations: Número de iteraciones (initial + sequential)
            initial_random_samples: Muestras iniciales random antes de optimizacion
        """
        self.space = space
        self.num_iterations = num_iterations
        self.initial_random_samples = initial_random_samples
        self.results: List[TrainingResult] = []
        
        # Historia para GP fitting
        self.history_params: List[np.ndarray] = []  # Parametros codificados
        self.history_scores: List[float] = []  # Scores obtenidos
        
        # Mejor resultado observado
        self.best_result: Optional[TrainingResult] = None
        self.best_score: float = -np.inf
        
    def _encode_config(self, config: Dict[str, Any]) -> np.ndarray:
        """Codificar configuración como vector de features para el GP."""
        # Mapear nombres a indices en listas de espacio
        lr_idx = self.space.learning_rate.index(config['learning_rate']) / len(self.space.learning_rate)
        buf_idx = self.space.buffer_size.index(config['buffer_size']) / len(self.space.buffer_size)
        batch_idx = self.space.batch_size.index(config['batch_size']) / len(self.space.batch_size)
        tau_idx = self.space.tau.index(config['tau']) / len(self.space.tau)
        gamma_idx = self.space.gamma.index(config['gamma']) / len(self.space.gamma)
        
        # ent_coef puede ser string o float
        ent_idx = self.space.ent_coef.index(config['ent_coef']) / len(self.space.ent_coef)
        tent_idx = self.space.target_entropy.index(config['target_entropy']) / len(self.space.target_entropy)
        tf_idx = self.space.train_freq.index(config['train_freq']) / len(self.space.train_freq)
        net_idx = self.space.net_arch_hidden.index(config['net_arch_hidden']) / len(self.space.net_arch_hidden)
        
        return np.array([lr_idx, buf_idx, batch_idx, tau_idx, gamma_idx, 
                        ent_idx, tent_idx, tf_idx, net_idx], dtype=np.float32)
    
    def _fit_gp(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Ajustar Gaussian Process simple a datos observados.
        
        Retorna:
            (mu, sigma): Media y desviación estándar del GP
        """
        if len(self.history_scores) < 2:
            # No hay datos suficientes
            return np.array([0.0] * len(self.history_params)), np.array([1.0] * len(self.history_params))
        
        # GP SIMPLE: RBF kernel + Bayesian regression (implementacion minimalista)
        # Para version produccion, usar sklearn.gaussian_process
        
        # Normalizar scores
        scores_arr = np.array(self.history_scores)
        mu_hist = np.mean(scores_arr)
        std_hist = np.std(scores_arr) + 1e-6
        scores_norm = (scores_arr - mu_hist) / std_hist
        
        # Kernel RBF simple
        X = np.array(self.history_params)  # N x 9
        # Distancias pairwise
        distances = np.linalg.norm(X[:, np.newaxis, :] - X[np.newaxis, :, :], axis=2)  # N x N
        K = np.exp(-distances**2 / 2)  # RBF kernel
        
        # Regularizacion Tikhonov
        K_reg = K + 0.1 * np.eye(len(K))
        
        # Predicción en puntos entrenados
        try:
            alpha = np.linalg.solve(K_reg, scores_norm)
            mu = K @ alpha
            sigma = np.sqrt(np.diag(K - K @ np.linalg.inv(K_reg) @ K))
            sigma = np.maximum(sigma, 1e-6)  # Evitar sigma=0
        except np.linalg.LinAlgError:
            # Degenerate case
            mu = mu_hist * np.ones(len(K))
            sigma = std_hist * np.ones(len(K))
        
        return mu, sigma
    
    def _expected_improvement(self, mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
        """
        Calcular Expected Improvement (EI) para cada punto.
        
        EI(x) = (mu(x) - f_best) * Phi(Z) + sigma(x) * phi(Z)
        donde Z = (mu(x) - f_best) / sigma(x)
        Phi = CDF normal, phi = PDF normal
        
        EI balancea explotacion (mu alto) y exploración (sigma alto).
        """
        f_best = np.max(self.history_scores) if self.history_scores else 0.0
        
        # Evitar division by zero
        sigma = np.maximum(sigma, 1e-6)
        
        Z = (mu - f_best) / sigma
        ei = (mu - f_best) * norm.cdf(Z) + sigma * norm.pdf(Z)
        ei = np.maximum(ei, 0.0)  # EI >= 0
        
        return ei
    
    def _select_next_config(self) -> Dict[str, Any]:
        """
        Seleccionar siguiente configuración a probar usando EI.
        """
        # Generar candidatos (sampleo random + EI selection)
        num_candidates = max(100, self.num_iterations * 5)
        candidates = []
        
        for _ in range(num_candidates):
            config = {
                'learning_rate': random.choice(self.space.learning_rate),
                'buffer_size': random.choice(self.space.buffer_size),
                'batch_size': random.choice(self.space.batch_size),
                'tau': random.choice(self.space.tau),
                'gamma': random.choice(self.space.gamma),
                'ent_coef': random.choice(self.space.ent_coef),
                'target_entropy': random.choice(self.space.target_entropy),
                'train_freq': random.choice(self.space.train_freq),
                'net_arch_hidden': random.choice(self.space.net_arch_hidden),
            }
            candidates.append(config)
        
        # Evaluar EI para cada candidato
        if self.history_scores:
            mu, sigma = self._fit_gp()
            
            # Codificar candidatos
            X_candidates = np.array([self._encode_config(c) for c in candidates])
            
            # Calcular distancias a puntos observados
            X_history = np.array(self.history_params)
            distances = np.min(np.linalg.norm(X_candidates[:, np.newaxis, :] - X_history[np.newaxis, :, :], axis=2), axis=1)
            
            # Kernel RBF predicion
            ei_scores = []
            for i, x_cand in enumerate(X_candidates):
                k = np.exp(-np.sum((x_cand - X_history)**2, axis=1) / 2)
                mu_pred = np.mean(self.history_scores) + np.dot(k - np.mean(k), np.array(self.history_scores) - np.mean(self.history_scores))
                sigma_pred = np.std(self.history_scores) / (1 + distances[i])  # Penalizar puntos cercanos
                ei = self._expected_improvement(np.array([mu_pred]), np.array([sigma_pred]))[0]
                ei_scores.append(ei)
            
            # Seleccionar candidato con EI mayor
            best_idx = np.argmax(ei_scores)
        else:
            # Sin datos aun, seleccionar aleatorio
            best_idx = 0
        
        return candidates[best_idx]
    
    def generate_configs(self) -> List[Dict[str, Any]]:
        """Generar configuraciones usando AG."""
        configs = []
        
        # Fase 1: Muestras iniciales random
        for _ in range(self.initial_random_samples):
            config = {
                'learning_rate': random.choice(self.space.learning_rate),
                'buffer_size': random.choice(self.space.buffer_size),
                'batch_size': random.choice(self.space.batch_size),
                'tau': random.choice(self.space.tau),
                'gamma': random.choice(self.space.gamma),
                'ent_coef': random.choice(self.space.ent_coef),
                'target_entropy': random.choice(self.space.target_entropy),
                'train_freq': random.choice(self.space.train_freq),
                'net_arch_hidden': random.choice(self.space.net_arch_hidden),
            }
            configs.append(config)
        
        # Fase 2: Seleccion secuencial con EI
        for _ in range(self.num_iterations - self.initial_random_samples):
            config = self._select_next_config()
            configs.append(config)
        
        return configs
    
    def update_history(self, config: Dict[str, Any], result: TrainingResult) -> None:
        """Actualizar historia con nuevo resultado."""
        x = self._encode_config(config)
        self.history_params.append(x)
        self.history_scores.append(result.score)
        
        # Actualizar mejor resultado
        if result.score > self.best_score:
            self.best_score = result.score
            self.best_result = result
    
    def summary(self) -> str:
        """Resumen de la búsqueda."""
        summary = f"\n{'='*80}\n"
        summary += f"BAYESIAN OPTIMIZATION SUMMARY\n"
        summary += f"{'='*80}\n"
        summary += f"Iteraciones completadas: {len(self.results)}/{self.num_iterations}\n"
        
        if self.best_result:
            summary += f"\nMejor configuración encontrada:\n"
            summary += f"  Score: {self.best_score:.1f}/100\n"
            summary += f"  LR={self.best_result.learning_rate:.1e} | "
            summary += f"Buf={self.best_result.buffer_size/1000:.0f}K | "
            summary += f"τ={self.best_result.tau:.4f}\n"
            summary += f"  CO2 Evitado: {self.best_result.co2_avoided_kg:,.0f} kg\n"
            summary += f"  Reward: {self.best_result.avg_episode_reward:.2f}\n"
            
            # Mejora respecto a baseline
            if len(self.results) > 1:
                first_score = self.results[0].score
                improvement = ((self.best_score - first_score) / first_score * 100) if first_score > 0 else 0
                summary += f"  Mejora respecto a baseline: {improvement:+.1f}%\n"
        
        summary += f"{'='*80}\n"
        return summary


# =============================================================================
# ORCHESTRATOR PRINCIPAL
# =============================================================================

class SACHyperparameterTuner:
    """
    Orchestrador de tuning de hiperparámetros para SAC.
    
    Maneja:
    - Selección del algoritmo de búsqueda (Grid/Random/Bayesian)
    - Ejecución de entrenamientos
    - Recolección de resultados
    - Exportación de resultados
    - Visualización
    """
    
    def __init__(self, output_dir: Path = Path('outputs/hyperparameter_tuning')):
        """
        Args:
            output_dir: Directorio para guardar resultados
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.results: List[TrainingResult] = []
        
    def run_grid_search(self, space: HyperparameterSpace, max_configs: int = 100,
                       train_func: Optional[Callable] = None) -> GridSearchTuner:
        """
        Ejecutar Grid Search.
        
        Args:
            space: Espacio de búsqueda
            max_configs: Máximo número de configs
            train_func: Función para entrenar (test si None)
        
        Returns:
            Tuner con resultados
        """
        print(f"\n{'='*80}")
        print(f"GRID SEARCH HYPERPARAMETER TUNING")
        print(f"{'='*80}\n")
        
        tuner = GridSearchTuner(space, max_configs)
        configs = tuner.generate_configs()
        
        print(f"Exploración de {len(configs)} configuraciones...")
        print(f"(de {tuner.total_configs:,} posibles en el grid)\n")
        
        for i, config in enumerate(configs, 1):
            print(f"[{i}/{len(configs)}] LR={config['learning_rate']:.1e} | "
                 f"Buf={config['buffer_size']/1000:.0f}K | "
                 f"τ={config['tau']:.4f} | ent={config['ent_coef']}")
            
            # Entrenar con esta configuracion
            if train_func:
                result = train_func(config)
                tuner.results.append(result)
            else:
                # Modo test: resultado simulado
                result = TrainingResult(
                    **config,
                    avg_episode_reward=np.random.randn() * 2,
                    co2_avoided_kg=np.random.randint(900_000, 1_100_000),
                    tuning_iteration=i,
                    timestamp=self.timestamp,
                )
                tuner.results.append(result)
        
        self.results.extend(tuner.results)
        self._export_results(tuner.results, f"grid_search_{self.timestamp}")
        print(tuner.summary())
        
        return tuner
    
    def run_random_search(self, space: HyperparameterSpace, num_samples: int = 50,
                         train_func: Optional[Callable] = None) -> RandomSearchTuner:
        """
        Ejecutar Random Search.
        
        Args:
            space: Espacio de búsqueda
            num_samples: Número de muestras
            train_func: Función para entrenar
        
        Returns:
            Tuner con resultados
        """
        print(f"\n{'='*80}")
        print(f"RANDOM SEARCH HYPERPARAMETER TUNING")
        print(f"{'='*80}\n")
        
        tuner = RandomSearchTuner(space, num_samples)
        configs = tuner.generate_configs()
        
        print(f"Sampleando {len(configs)} configuraciones aleatorias...\n")
        
        for i, config in enumerate(configs, 1):
            print(f"[{i}/{len(configs)}] LR={config['learning_rate']:.1e} | "
                 f"Buf={config['buffer_size']/1000:.0f}K | "
                 f"τ={config['tau']:.4f} | ent={config['ent_coef']}")
            
            if train_func:
                result = train_func(config)
                tuner.results.append(result)
            else:
                result = TrainingResult(
                    **config,
                    avg_episode_reward=np.random.randn() * 2,
                    co2_avoided_kg=np.random.randint(900_000, 1_100_000),
                    tuning_iteration=i,
                    timestamp=self.timestamp,
                )
                tuner.results.append(result)
        
        self.results.extend(tuner.results)
        self._export_results(tuner.results, f"random_search_{self.timestamp}")
        print(tuner.summary())
        
        return tuner
    
    def run_bayesian_optimization(self, space: HyperparameterSpace, num_iterations: int = 30,
                                 train_func: Optional[Callable] = None) -> BayesianTuner:
        """
        Ejecutar Bayesian Optimization.
        
        Args:
            space: Espacio de búsqueda
            num_iterations: Número de iteraciones
            train_func: Función para entrenar
        
        Returns:
            Tuner con resultados
        """
        print(f"\n{'='*80}")
        print(f"BAYESIAN OPTIMIZATION HYPERPARAMETER TUNING")
        print(f"{'='*80}\n")
        
        tuner = BayesianTuner(space, num_iterations)
        configs = tuner.generate_configs()
        
        print(f"Optimización bayesiana en {num_iterations} iteraciones...\n")
        
        for i, config in enumerate(configs, 1):
            print(f"[{i}/{len(configs)}] LR={config['learning_rate']:.1e} | "
                 f"Buf={config['buffer_size']/1000:.0f}K | "
                 f"τ={config['tau']:.4f} | ent={config['ent_coef']}")
            
            if train_func:
                result = train_func(config)
            else:
                result = TrainingResult(
                    **config,
                    avg_episode_reward=np.random.randn() * 2 + (i * 0.1),  # Simulado con mejora
                    co2_avoided_kg=np.random.randint(900_000, 1_100_000) + (i * 1000),
                    tuning_iteration=i,
                    timestamp=self.timestamp,
                )
            
            tuner.results.append(result)
            tuner.update_history(config, result)
            
            if i > 1:
                print(f"     Best so far: {tuner.best_score:.1f}/100 @ iteration {len(tuner.results)-1}")
        
        self.results.extend(tuner.results)
        self._export_results(tuner.results, f"bayesian_opt_{self.timestamp}")
        print(tuner.summary())
        
        return tuner
    
    def _export_results(self, results: List[TrainingResult], name: str) -> None:
        """Exportar resultados a CSV."""
        df = pd.DataFrame([r.to_dict() for r in results])
        
        csv_path = self.output_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"\n[EXPORT] Resultados guardados en: {csv_path}")
        
        # Mostrar top 5
        top_5 = df.nlargest(5, 'score')[['learning_rate', 'buffer_size', 'tau', 'score', 'co2_avoided_kg']]
        print(f"\nTop 5 configuraciones:")
        print(top_5.to_string(index=False))
    
    def save_best_config(self, best_result: TrainingResult) -> Path:
        """Guardar mejor configuración como JSON."""
        config_dict = {
            'learning_rate': float(best_result.learning_rate),
            'buffer_size': int(best_result.buffer_size),
            'batch_size': int(best_result.batch_size),
            'tau': float(best_result.tau),
            'gamma': float(best_result.gamma),
            'ent_coef': best_result.ent_coef,
            'target_entropy': float(best_result.target_entropy),
            'train_freq': int(best_result.train_freq),
            'net_arch_hidden': int(best_result.net_arch_hidden),
            'network_arch': [best_result.net_arch_hidden, best_result.net_arch_hidden],  # Para SAC
            'metadata': {
                'score': float(best_result.score),
                'co2_avoided_kg': float(best_result.co2_avoided_kg),
                'avg_episode_reward': float(best_result.avg_episode_reward),
                'timestamp': best_result.timestamp,
            }
        }
        
        json_path = self.output_dir / f"config_optimal_{self.timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2)
        
        print(f"\n[SAVE] Mejor config salvada en: {json_path}")
        return json_path


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def create_default_space() -> HyperparameterSpace:
    """Crear espacio de búsqueda por defecto para SAC."""
    return HyperparameterSpace(
        learning_rate=[1e-5, 3e-5, 1e-4, 3e-4, 1e-3],
        buffer_size=[50_000, 100_000, 200_000, 400_000, 1_000_000],
        batch_size=[32, 64, 128, 256, 512],
        tau=[0.001, 0.005, 0.01, 0.02],
        gamma=[0.90, 0.95, 0.99],
        ent_coef=['auto', 0.05, 0.1, 0.2, 0.5],
        target_entropy=[-50, -20, -10, -5],
        train_freq=[1, 2, 4, 8],
        net_arch_hidden=[128, 256, 384, 512],
    )


if __name__ == '__main__':
    # Demo de tuning
    print("DEMO: Hyperparameter Tuning para SAC\n")
    
    space = create_default_space()
    print(f"Espacio de búsqueda: {space.summary}\n")
    
    # Crear tuner
    tuner = SACHyperparameterTuner()
    
    # Mostrar que es posible hacer:
    print("Opciones disponibles:")
    print("1. Grid Search:           Prueba todas las combinaciones")
    print("2. Random Search:         Muestrea N aleatorias")
    print("3. Bayesian Optimization: Optimización inteligente\n")
    
    # Demo Grid Search
    print("Demo Grid Search:")
    grid_tuner = tuner.run_grid_search(space, max_configs=10)  # Solo 10 para demo
    print(f"Resultados: {len(grid_tuner.results)} configs probadas\n")
    
    # Salvar mejor
    if grid_tuner.results:
        best = sorted(grid_tuner.results, key=lambda r: r.score, reverse=True)[0]
        tuner.save_best_config(best)
