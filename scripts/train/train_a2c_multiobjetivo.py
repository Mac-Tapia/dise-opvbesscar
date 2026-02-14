#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENTRENAR A2C CON MULTIOBJETIVO REAL
Entrenamiento INDIVIDUAL con datos OE2 reales (chargers, BESS, mall demand, solar)
NO se usa ninguna formula de aproximacion - SOLO DATOS REALES
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from gymnasium import Env, spaces
from stable_baselines3 import A2C
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList

from src.citylearnv2.dataset_builder.rewards import (
    IquitosContext,
    MultiObjectiveReward,
    create_iquitos_reward_weights,
)

# Importar escenarios de carga de vehículos (comentado - módulo no disponible)
from vehicle_charging_scenarios import (
    VehicleChargingSimulator,
    VehicleChargingScenario,
    SCENARIO_OFF_PEAK,
    SCENARIO_PEAK_AFTERNOON,
    SCENARIO_PEAK_EVENING,
    SCENARIO_EXTREME_PEAK,
)

# ===== CONSTANTES IQUITOS v5.3 (2026-02-14) CON COMUNICACIÓN SISTEMA =====
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh (grid térmico aislado)
BESS_CAPACITY_KWH: float = 940.0    # 940 kWh (exclusivo EV, 100% cobertura)
BESS_MAX_POWER_KW: float = 342.0    # 342 kW potencia máxima BESS
HOURS_PER_YEAR: int = 8760

# v5.3: Constantes para normalización de observaciones
SOLAR_MAX_KW: float = 4100.0        # 4,050 kWp nominal + margen
MALL_MAX_KW: float = 150.0          # Demanda máxima mall
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad máxima BESS (referencia normalización)
CHARGER_MAX_KW: float = 10.0        # Max por socket (7.4 kW nominal, 10 kW margen)
CHARGER_MEAN_KW: float = 4.6        # Potencia media efectiva por socket

# ===== A2C CONFIG (COMPLETO CON BEST PRACTICES) =====
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para generación de gráficos
import matplotlib.pyplot as plt


@dataclass
class A2CConfig:
    """
    Configuración A2C COMPLETA - On-policy, updates frecuentes (fortaleza de A2C).
    
    A2C (Advantage Actor-Critic) es más simple y rápido que PPO pero menos estable.
    Características:
    - On-policy: aprende de experiencias recientes
    - Updates síncronos (vs A3C asíncrono)
    - Menor sample efficiency pero muy rápido
    - Ideal para tareas con feedback denso
    
    HIPERPARÁMETROS PRINCIPALES (Best Practices):
    ================================================================================
    n_steps: 5-20 (clásico), 32-128 para tareas complejas
        - Horizonte por update antes de calcular returns
        - A2C funciona mejor con n_steps pequeños (updates frecuentes)
        
    learning_rate: 7e-4 (clásico RMSProp) o 1e-4 - 3e-4 (Adam)
        - Papers originales usaban RMSProp con 7e-4
        - Con Adam, usar rates más bajos
        
    gamma: 0.99 típico (discount factor)
        - Qué tan lejos mira el agente en el futuro
        
    gae_lambda: 0.9-0.97 (si implementado)
        - GAE reduce varianza de advantage estimates
        
    ent_coef: 0.0-0.02
        - Fomenta exploración penalizando policies determinísticas
        - Muy importante para evitar colapso prematuro
        
    vf_coef: 0.25-0.5
        - Peso del value loss en la función de pérdida total
        - Bajar si value loss domina demasiado
    
    max_grad_norm: 0.5-1.0
        - Gradient clipping para estabilidad
        
    SEÑALES DE PROBLEMA:
    - Alta varianza entre runs → subir num_envs, ajustar LR, normalización
    - Value loss muy alta persistente → crítico mal (LR/arquitectura/normalización)
    - Entropy colapsa a 0 → exploración muerta, aumentar ent_coef
    ================================================================================
    """
    
    # ========================================================================
    # LEARNING PARAMETERS - ÓPTIMOS PARA A2C
    # ========================================================================
    
    # Learning rate
    # - 7e-4: Clásico A2C con RMSProp (papers antiguos)
    # - 1e-4 a 3e-4: Recomendado con Adam
    learning_rate: float = 3e-4  # ✅ Óptimo con Adam
    
    # Horizonte por update (n_steps)
    # - 5-20: Clásico A2C (updates muy frecuentes = fortaleza)
    # - 32-128: Para tareas más complejas/largas
    n_steps: int = 16  # ✅ Balance entre frecuencia y estabilidad
    
    # Discount factor (gamma)
    # - 0.99: Típico para tareas de largo plazo
    # - 0.95-0.97: Para tareas más cortas
    gamma: float = 0.99
    
    # GAE lambda (Generalized Advantage Estimation)
    # - 0.9-0.97: Reduce varianza de advantage estimates
    # - 1.0: Sin GAE (solo temporal difference)
    gae_lambda: float = 0.95
    
    # Entropy coefficient
    # - 0.0: Sin bonus de exploración
    # - 0.01-0.02: Típico para fomentar exploración
    # - Muy importante para evitar colapso de policy
    ent_coef: float = 0.01  # ✅ Standard A2C exploration
    
    # Value function coefficient
    # - 0.25-0.5: Balance entre policy y value loss
    # - Bajar si value loss domina demasiado
    vf_coef: float = 0.5
    
    # Max gradient norm (clipping)
    # - 0.5: Conservador, más estable
    # - 1.0: Menos restrictivo
    max_grad_norm: float = 0.5
    
    # RMSProp epsilon (solo si use_rms_prop=True)
    rms_prop_eps: float = 1e-5
    
    # Usar RMSProp en lugar de Adam
    # - True: Clásico A2C (papers originales)
    # - False: Adam (generalmente mejor en práctica moderna)
    use_rms_prop: bool = False  # ✅ Adam es mejor en práctica moderna
    
    # Normalización de advantages
    normalize_advantage: bool = True  # ✅ Reduce varianza
    
    # ========================================================================
    # NETWORK ARCHITECTURE
    # ========================================================================
    policy_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'net_arch': dict(pi=[256, 256], vf=[256, 256])  # ✅ 256x256 adecuado
    })
    
    # ========================================================================
    # MONITORING THRESHOLDS (para alertas)
    # ========================================================================
    
    # Entropy mínima antes de warning (exploration collapse)
    min_entropy_warning: float = 0.1
    
    # Value loss máxima persistente (indica problemas)
    max_value_loss_warning: float = 100.0
    
    # Explained variance mínima esperada tras convergencia
    min_explained_variance: float = 0.0
    
    # ========================================================================
    # FACTORY METHODS
    # ========================================================================
    
    @classmethod
    def for_gpu(cls) -> 'A2CConfig':
        """
        Configuración ÓPTIMA para A2C en GPU.
        
        GPU permite n_steps más altos y redes más grandes.
        """
        return cls(
            learning_rate=3e-4,  # ✅ Adam rate óptimo
            n_steps=16,  # ✅ Balance updates/estabilidad
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.01,  # ✅ Exploración estándar
            vf_coef=0.5,
            max_grad_norm=0.5,
            use_rms_prop=False,  # Adam
            normalize_advantage=True,
            policy_kwargs={
                'net_arch': dict(pi=[256, 256], vf=[256, 256]),
            }
        )
    
    @classmethod
    def for_cpu(cls) -> 'A2CConfig':
        """
        Configuración para CPU (fallback).
        
        Más conservadora para evitar timeouts.
        """
        return cls(
            learning_rate=1e-4,  # ✅ Más bajo para estabilidad
            n_steps=8,  # ✅ Updates más frecuentes
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            use_rms_prop=False,
            normalize_advantage=True,
            policy_kwargs={
                'net_arch': dict(pi=[128, 128], vf=[128, 128]),  # Red más pequeña
            }
        )
    
    @classmethod
    def high_exploration(cls) -> 'A2CConfig':
        """
        Configuración con alta exploración.
        
        Útil al inicio del entrenamiento o en tareas complejas.
        """
        return cls(
            learning_rate=3e-4,
            n_steps=32,  # Horizonte más largo
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=0.02,  # ✅ Alta exploración
            vf_coef=0.25,  # Menos énfasis en value
            max_grad_norm=0.5,
            use_rms_prop=False,
            normalize_advantage=True,
        )
    
    @classmethod
    def stable_convergence(cls) -> 'A2CConfig':
        """
        Configuración conservadora para convergencia estable.
        
        Menor learning rate, más gradient clipping.
        """
        return cls(
            learning_rate=1e-4,  # ✅ Más bajo
            n_steps=16,
            gamma=0.99,
            gae_lambda=0.97,  # GAE más alto
            ent_coef=0.005,  # Menos exploración
            vf_coef=0.5,
            max_grad_norm=0.3,  # ✅ Más restrictivo
            use_rms_prop=False,
            normalize_advantage=True,
        )


# ===== A2C METRICS CALLBACK - MÉTRICAS ESPECÍFICAS A2C =====
class A2CMetricsCallback(BaseCallback):
    """
    Callback para registrar métricas ESPECÍFICAS de A2C durante entrenamiento.
    
    MÉTRICAS QUE SE LOGUEAN (Best Practices A2C):
    ================================================================================
    1. Entropy: Mide diversidad de la policy (exploración)
       - Warning si < 0.1 (exploration collapse)
       
    2. Policy Loss: Pérdida del actor
       - Debería estabilizarse tras convergencia
       
    3. Value Loss: Pérdida del crítico
       - Warning si muy alta persistente (>100)
       
    4. Explained Variance: Qué tan bien predice el crítico
       - 0 = aleatorio, 1 = perfecto
       - Debería aumentar durante entrenamiento
       
    5. Grad Norm: Norma de gradientes
       - Monitoreamos para detectar explosión/desvanecimiento
       
    6. Episode Length: Duración de episodios
       - Útil para detectar terminación prematura
       
    SEÑALES DE PROBLEMA (A2C):
    - Alta varianza entre runs → subir num_envs, ajustar LR
    - Value loss muy alta persistente → arquitectura/normalización
    - Entropy colapsa → aumentar ent_coef
    ================================================================================
    """
    
    def __init__(
        self, 
        output_dir: Path | None = None, 
        config: A2CConfig | None = None,
        verbose: int = 0
    ):
        super().__init__(verbose)
        self.output_dir = output_dir or Path('outputs/a2c_training')
        self.config = config or A2CConfig()
        
        # ========================================================================
        # HISTORIALES PARA GRÁFICOS
        # ========================================================================
        
        # Steps tracking (X-axis para todos los gráficos)
        self.steps_history: list[int] = []
        
        # Métricas A2C principales
        self.entropy_history: list[float] = []
        self.policy_loss_history: list[float] = []
        self.value_loss_history: list[float] = []
        self.explained_variance_history: list[float] = []
        self.grad_norm_history: list[float] = []
        
        # Métricas de episodios
        self.episode_lengths: list[int] = []
        self.episode_rewards: list[float] = []
        
        # Learning rate tracking (puede cambiar con schedulers)
        self.lr_history: list[float] = []
        
        # ========================================================================
        # KPIs CityLearn (estándar para evaluación de control en microgrids)
        # ========================================================================
        
        # Steps para KPIs (puede diferir de steps_history si se loguean diferente)
        self.kpi_steps_history: list[int] = []
        
        # 1. Electricity Consumption (net) - kWh neto consumido del grid
        #    Positivo = importación, Negativo = exportación
        self.electricity_consumption_history: list[float] = []
        
        # 2. Electricity Cost - USD (o soles) total
        self.electricity_cost_history: list[float] = []
        
        # 3. Carbon Emissions - kg CO2 total
        self.carbon_emissions_history: list[float] = []
        
        # 4. Ramping - kW diferencia absoluta entre timesteps consecutivos
        #    Mide la variabilidad de carga (menor = más estable)
        self.ramping_history: list[float] = []
        
        # 5. Average Daily Peak - kW promedio de picos diarios
        self.avg_daily_peak_history: list[float] = []
        
        # 6. (1 - Load Factor) - Medida de eficiencia de uso
        #    Load Factor = Average / Peak; menor (1-LF) = mejor
        self.one_minus_load_factor_history: list[float] = []
        
        # Acumuladores para calcular KPIs por ventana de evaluación
        self._kpi_window_size = 24  # Calcular KPIs cada 24 horas (1 día)
        self._kpi_grid_imports: list[float] = []  # Para net consumption
        self._kpi_grid_exports: list[float] = []
        self._kpi_costs: list[float] = []
        self._kpi_emissions: list[float] = []
        self._kpi_loads: list[float] = []  # Para ramping y load factor
        self._prev_load: float = 0.0  # Para calcular ramping
        self._kpi_ramping_sum: float = 0.0
        self._kpi_ramping_count: int = 0
        
        # ========================================================================
        # CONTADORES DE ALERTAS
        # ========================================================================
        self.entropy_collapse_alerts: int = 0
        self.high_value_loss_alerts: int = 0
        self.grad_explosion_alerts: int = 0
        self.low_explained_var_alerts: int = 0
        
        # Umbrales de alerta
        self.min_entropy = self.config.min_entropy_warning  # 0.1
        self.max_value_loss = self.config.max_value_loss_warning  # 100.0
        self.max_grad_norm_alert = 10.0  # Alert si grad_norm > 10
        
        # Logging frecuency
        self.log_freq = 1000  # Log cada 1000 steps
        
    def _on_step(self) -> bool:
        """Registrar métricas en cada step."""
        
        # Solo loguear cada log_freq steps
        if self.num_timesteps % self.log_freq != 0:
            return True
            
        # Obtener logger del modelo
        if self.model is None:
            return True
            
        # ========================================================================
        # EXTRAER MÉTRICAS DEL MODELO A2C
        # ========================================================================
        
        # Extraemos métricas del logger interno de SB3
        # A2C registra: entropy_loss, policy_gradient_loss, value_loss, explained_variance
        
        logger = self.model.logger
        if logger is None:
            return True
        
        # Registrar step
        self.steps_history.append(self.num_timesteps)
        
        # Entropy (de logger.name_to_value o del último rollout)
        entropy = 0.0
        policy_loss = 0.0
        value_loss = 0.0
        explained_var = 0.0
        
        # Intentar obtener de logger.name_to_value (SB3 >= 2.0)
        if hasattr(logger, 'name_to_value'):
            name_to_value = logger.name_to_value
            entropy = name_to_value.get('train/entropy_loss', 0.0)
            policy_loss = name_to_value.get('train/policy_gradient_loss', 0.0)
            value_loss = name_to_value.get('train/value_loss', 0.0)
            explained_var = name_to_value.get('train/explained_variance', 0.0)
        
        # Alternativamente, obtener del locals (última iteración)
        if entropy == 0.0 and 'entropy_losses' in self.locals:
            entropy_losses = self.locals.get('entropy_losses', [])
            if entropy_losses:
                entropy = -float(np.mean(entropy_losses))  # Negativo porque SB3 lo almacena negado
        
        if policy_loss == 0.0 and 'pg_losses' in self.locals:
            pg_losses = self.locals.get('pg_losses', [])
            if pg_losses:
                policy_loss = float(np.mean(pg_losses))
        
        if value_loss == 0.0 and 'value_losses' in self.locals:
            value_losses = self.locals.get('value_losses', [])
            if value_losses:
                value_loss = float(np.mean(value_losses))
        
        # Explained variance del rollout buffer
        if hasattr(self.model, 'rollout_buffer') and self.model.rollout_buffer is not None:
            rb = self.model.rollout_buffer
            if hasattr(rb, 'returns') and hasattr(rb, 'values') and rb.returns is not None:
                try:
                    returns = rb.returns.flatten()
                    values = rb.values.flatten()
                    if len(returns) > 0 and len(values) > 0:
                        var_returns = np.var(returns)
                        if var_returns > 0:
                            explained_var = 1 - np.var(returns - values) / var_returns
                except Exception:
                    pass
        
        # Guardar en historiales
        self.entropy_history.append(abs(entropy))  # Valor absoluto
        self.policy_loss_history.append(policy_loss)
        self.value_loss_history.append(value_loss)
        self.explained_variance_history.append(explained_var)
        
        # ========================================================================
        # GRAD NORM (calcular si posible)
        # ========================================================================
        grad_norm = 0.0
        try:
            if hasattr(self.model, 'policy') and self.model.policy is not None:
                total_norm = 0.0
                for p in self.model.policy.parameters():
                    if p.grad is not None:
                        param_norm = p.grad.data.norm(2)
                        total_norm += param_norm.item() ** 2
                grad_norm = total_norm ** 0.5
        except Exception:
            pass
        
        self.grad_norm_history.append(grad_norm)
        
        # Learning rate actual
        lr = self.model.learning_rate
        if callable(lr):
            lr = lr(1)  # type: ignore
        self.lr_history.append(float(lr))
        
        # ========================================================================
        # KPIs CityLearn - Recolectar datos para evaluación
        # ========================================================================
        self._collect_kpi_data()
        
        # ========================================================================
        # VERIFICAR ALERTAS
        # ========================================================================
        self._check_alerts(entropy, value_loss, grad_norm, explained_var)
        
        return True
    
    def _check_alerts(
        self, 
        entropy: float, 
        value_loss: float, 
        grad_norm: float,
        explained_var: float
    ) -> None:
        """Verificar condiciones problemáticas y emitir alertas."""
        
        # 1. Entropy collapse (exploración muerta)
        if abs(entropy) < self.min_entropy and abs(entropy) > 0:
            self.entropy_collapse_alerts += 1
            if self.entropy_collapse_alerts <= 3:  # Solo primeras 3 alertas
                print(f'  ⚠️ A2C ALERT [{self.num_timesteps}]: Entropy muy baja '
                      f'({abs(entropy):.4f} < {self.min_entropy}) - Aumentar ent_coef')
        
        # 2. Value loss muy alta
        if value_loss > self.max_value_loss:
            self.high_value_loss_alerts += 1
            if self.high_value_loss_alerts <= 3:
                print(f'  ⚠️ A2C ALERT [{self.num_timesteps}]: Value loss muy alta '
                      f'({value_loss:.2f} > {self.max_value_loss}) - Revisar arquitectura/LR')
        
        # 3. Gradient explosion
        if grad_norm > self.max_grad_norm_alert:
            self.grad_explosion_alerts += 1
            if self.grad_explosion_alerts <= 3:
                print(f'  ⚠️ A2C ALERT [{self.num_timesteps}]: Grad norm muy alta '
                      f'({grad_norm:.2f} > {self.max_grad_norm_alert}) - Reducir LR o max_grad_norm')
        
        # 4. Explained variance muy baja después de muchos steps
        if self.num_timesteps > 20000 and explained_var < -0.5:
            self.low_explained_var_alerts += 1
            if self.low_explained_var_alerts <= 3:
                print(f'  ⚠️ A2C ALERT [{self.num_timesteps}]: Explained variance negativa '
                      f'({explained_var:.3f}) - Crítico no está aprendiendo')
    
    def _collect_kpi_data(self) -> None:
        """
        Recolectar datos para KPIs CityLearn de evaluación.
        
        KPIs estándar CityLearn calculados sobre carga neta agregada:
        1. Electricity consumption (net) - kWh
        2. Electricity cost - USD
        3. Carbon emissions - kg CO2
        4. Ramping - kW (variabilidad de carga)
        5. Average daily peak - kW
        6. (1 - Load Factor) - eficiencia de uso
        """
        # Obtener infos del environment
        infos = self.locals.get('infos', [{}])
        if not infos:
            return
        
        info = infos[0] if isinstance(infos, list) else infos
        
        # Extraer métricas del step actual
        grid_import = info.get('grid_import_kwh', 0.0)
        grid_export = info.get('grid_export_kwh', 0.0)
        cost = info.get('cost_usd', info.get('cost_soles', 0.0) * 0.27)  # Convertir soles a USD aprox
        co2 = info.get('co2_grid_kg', grid_import * 0.4521)  # Factor Iquitos
        
        # Carga neta total (para ramping y load factor)
        mall_demand = info.get('mall_demand_kwh', info.get('mall_demand_kw', 0.0))
        ev_demand = info.get('ev_charging_kwh', info.get('ev_demand_kw', 0.0))
        solar_gen = info.get('solar_generation_kwh', info.get('solar_kw', 0.0))
        net_load = mall_demand + ev_demand - solar_gen + grid_import - grid_export
        
        # Acumular datos
        self._kpi_grid_imports.append(grid_import)
        self._kpi_grid_exports.append(grid_export)
        self._kpi_costs.append(cost)
        self._kpi_emissions.append(co2)
        self._kpi_loads.append(max(0, net_load))  # Solo carga positiva
        
        # Calcular ramping (diferencia con step anterior)
        if self._prev_load > 0:
            ramping = abs(net_load - self._prev_load)
            self._kpi_ramping_sum += ramping
            self._kpi_ramping_count += 1
        self._prev_load = net_load
        
        # Calcular KPIs cada _kpi_window_size steps (24 horas = 1 día)
        if len(self._kpi_loads) >= self._kpi_window_size:
            self._calculate_and_store_kpis()
    
    def _calculate_and_store_kpis(self) -> None:
        """
        Calcular y almacenar KPIs para la ventana actual.
        
        Fórmulas estándar CityLearn:
        - Net consumption = sum(imports) - sum(exports)
        - Ramping = mean(|load[t] - load[t-1]|)
        - Load Factor = mean(load) / max(load)
        - (1 - Load Factor) = 1 - (mean/max)
        """
        if len(self._kpi_loads) == 0:
            return
        
        # Guardar step actual
        self.kpi_steps_history.append(self.num_timesteps)
        
        # 1. Net electricity consumption (kWh)
        net_consumption = sum(self._kpi_grid_imports) - sum(self._kpi_grid_exports)
        self.electricity_consumption_history.append(net_consumption)
        
        # 2. Electricity cost (USD)
        total_cost = sum(self._kpi_costs)
        self.electricity_cost_history.append(total_cost)
        
        # 3. Carbon emissions (kg CO2)
        total_co2 = sum(self._kpi_emissions)
        self.carbon_emissions_history.append(total_co2)
        
        # 4. Ramping (kW promedio)
        avg_ramping = self._kpi_ramping_sum / max(1, self._kpi_ramping_count)
        self.ramping_history.append(avg_ramping)
        
        # 5. Average daily peak (kW)
        # Para una ventana de 24h, el peak es simplemente el máximo
        daily_peak = max(self._kpi_loads) if self._kpi_loads else 0.0
        self.avg_daily_peak_history.append(daily_peak)
        
        # 6. (1 - Load Factor)
        # Load Factor = average / peak (0 a 1, donde 1 = carga constante)
        avg_load = np.mean(self._kpi_loads) if self._kpi_loads else 0.0
        peak_load = max(self._kpi_loads) if self._kpi_loads else 1.0
        load_factor = avg_load / max(peak_load, 0.001)  # Evitar división por cero
        one_minus_lf = 1.0 - load_factor
        self.one_minus_load_factor_history.append(one_minus_lf)
        
        # Reset acumuladores para siguiente ventana
        self._kpi_grid_imports.clear()
        self._kpi_grid_exports.clear()
        self._kpi_costs.clear()
        self._kpi_emissions.clear()
        self._kpi_loads.clear()
        self._kpi_ramping_sum = 0.0
        self._kpi_ramping_count = 0
    
    def _on_training_end(self) -> None:
        """Generar gráficos al finalizar entrenamiento."""
        print('\n  📊 Generando gráficos A2C...')
        self._generate_a2c_graphs()
        
        # ✅ NUEVO: Generar gráficos de KPIs CityLearn
        print('\n  📊 Generando gráficos KPIs CityLearn...')
        self._generate_kpi_graphs()
        
        # Resumen de alertas
        total_alerts = (self.entropy_collapse_alerts + self.high_value_loss_alerts + 
                       self.grad_explosion_alerts + self.low_explained_var_alerts)
        
        if total_alerts > 0:
            print(f'\n  📋 RESUMEN ALERTAS A2C:')
            if self.entropy_collapse_alerts > 0:
                print(f'     - Entropy collapse: {self.entropy_collapse_alerts}')
            if self.high_value_loss_alerts > 0:
                print(f'     - High value loss: {self.high_value_loss_alerts}')
            if self.grad_explosion_alerts > 0:
                print(f'     - Gradient explosion: {self.grad_explosion_alerts}')
            if self.low_explained_var_alerts > 0:
                print(f'     - Low explained variance: {self.low_explained_var_alerts}')
    
    def _generate_kpi_graphs(self) -> None:
        """
        Generar gráficos de KPIs CityLearn vs Training Steps.
        
        GRÁFICOS GENERADOS:
        1. Electricity Consumption (net) vs Steps
        2. Electricity Cost vs Steps
        3. Carbon Emissions vs Steps
        4. Ramping vs Steps
        5. Average Daily Peak vs Steps
        6. (1 - Load Factor) vs Steps
        7. Dashboard KPIs combinado 2×3
        """
        
        if len(self.kpi_steps_history) < 2:
            print('     ⚠️ Insuficientes datos para gráficos KPIs (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Función helper para suavizado
        def smooth(data: list[float], window: int = 5) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return pd.Series(data).rolling(window=window, min_periods=1).mean().values
        
        steps = np.array(self.kpi_steps_history)
        
        # ====================================================================
        # GRÁFICO 1: ELECTRICITY CONSUMPTION vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps, consumption, 'b-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(consumption)), 'b-', linewidth=2, label='Smoothed')
            
            # Línea de tendencia
            if len(steps) > 2:
                z = np.polyfit(steps, consumption, 1)
                p = np.poly1d(z)
                ax.plot(steps, p(steps), 'r--', alpha=0.7, label=f'Trend (slope={z[0]:.4f})')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Net Electricity Consumption (kWh/day)')
            ax.set_title('Electricity Consumption vs Training Steps\n(Lower = better grid independence)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Anotar mejora si existe
            if len(consumption) > 1:
                improvement = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_consumption.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_electricity_consumption.png')
        except Exception as e:
            print(f'     ❌ Error en consumption graph: {e}')
        
        # ====================================================================
        # GRÁFICO 2: ELECTRICITY COST vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps, cost, 'g-', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(cost)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Electricity Cost (USD/day)')
            ax.set_title('Electricity Cost vs Training Steps\n(Lower = better cost efficiency)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora
            if len(cost) > 1:
                improvement = (cost[0] - cost[-1]) / max(cost[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% vs inicio', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_electricity_cost.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_electricity_cost.png')
        except Exception as e:
            print(f'     ❌ Error en cost graph: {e}')
        
        # ====================================================================
        # GRÁFICO 3: CARBON EMISSIONS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps, emissions, 'brown', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(emissions)), 'brown', linewidth=2, label='Smoothed')
            
            # Baseline sin control (aproximado como primer valor)
            if len(emissions) > 0:
                baseline = emissions[0]
                ax.axhline(y=baseline, color='gray', linestyle='--', alpha=0.5, label=f'Baseline ({baseline:.1f} kg)')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Carbon Emissions (kg CO₂/day)')
            ax.set_title('Carbon Emissions vs Training Steps\n(Lower = better environmental impact)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reducción CO2
            if len(emissions) > 1:
                reduction = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"↓" if reduction > 0 else "↑"} {abs(reduction):.1f}% CO₂', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_carbon_emissions.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_carbon_emissions.png')
        except Exception as e:
            print(f'     ❌ Error en emissions graph: {e}')
        
        # ====================================================================
        # GRÁFICO 4: RAMPING vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ramping = np.array(self.ramping_history)
            ax.plot(steps, ramping, 'purple', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(ramping)), 'purple', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Average Ramping (kW)')
            ax.set_title('Load Ramping vs Training Steps\n(Lower = more stable grid operation)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar mejora en estabilidad
            if len(ramping) > 1:
                improvement = (ramping[0] - ramping[-1]) / max(ramping[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}% ramping', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_ramping.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_ramping.png')
        except Exception as e:
            print(f'     ❌ Error en ramping graph: {e}')
        
        # ====================================================================
        # GRÁFICO 5: AVERAGE DAILY PEAK vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps, peak, 'red', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(peak)), 'red', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('Daily Peak Demand (kW)')
            ax.set_title('Average Daily Peak vs Training Steps\n(Lower = better peak shaving)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotar reducción de pico
            if len(peak) > 1:
                reduction = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                color = 'green' if reduction > 0 else 'red'
                ax.annotate(f'{"↓" if reduction > 0 else "↑"} {abs(reduction):.1f}% peak', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_daily_peak.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_daily_peak.png')
        except Exception as e:
            print(f'     ❌ Error en peak graph: {e}')
        
        # ====================================================================
        # GRÁFICO 6: (1 - LOAD FACTOR) vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps, one_minus_lf, 'orange', alpha=0.3, linewidth=0.5, label='Raw (24h window)')
            ax.plot(steps, smooth(list(one_minus_lf)), 'orange', linewidth=2, label='Smoothed')
            
            # Zona ideal (< 0.3 = buen load factor > 0.7)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7, label='Target (LF > 0.7)')
            ax.fill_between(steps, 0, 0.3, alpha=0.1, color='green')
            
            ax.set_xlabel('Training Steps')
            ax.set_ylabel('(1 - Load Factor)')
            ax.set_title('(1 - Load Factor) vs Training Steps\n(Lower = better load distribution, 0 = constant load)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Anotar mejora
            if len(one_minus_lf) > 1:
                improvement = (one_minus_lf[0] - one_minus_lf[-1]) / max(one_minus_lf[0], 0.001) * 100
                color = 'green' if improvement > 0 else 'red'
                ax.annotate(f'{"↓" if improvement > 0 else "↑"} {abs(improvement):.1f}%', 
                           xy=(0.98, 0.02), xycoords='axes fraction',
                           fontsize=10, color=color, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'kpi_load_factor.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_load_factor.png')
        except Exception as e:
            print(f'     ❌ Error en load factor graph: {e}')
        
        # ====================================================================
        # GRÁFICO 7: DASHBOARD KPIs COMBINADO 2×3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Electricity Consumption (top-left)
            ax = axes[0, 0]
            consumption = np.array(self.electricity_consumption_history)
            ax.plot(steps, smooth(list(consumption)), 'b-', linewidth=2)
            ax.set_title('Net Consumption (kWh/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            
            # 2. Electricity Cost (top-center)
            ax = axes[0, 1]
            cost = np.array(self.electricity_cost_history)
            ax.plot(steps, smooth(list(cost)), 'g-', linewidth=2)
            ax.set_title('Cost (USD/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 3. Carbon Emissions (top-right)
            ax = axes[0, 2]
            emissions = np.array(self.carbon_emissions_history)
            ax.plot(steps, smooth(list(emissions)), 'brown', linewidth=2)
            ax.set_title('CO₂ Emissions (kg/day)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Ramping (bottom-left)
            ax = axes[1, 0]
            ramping = np.array(self.ramping_history)
            ax.plot(steps, smooth(list(ramping)), 'purple', linewidth=2)
            ax.set_title('Ramping (kW)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 5. Daily Peak (bottom-center)
            ax = axes[1, 1]
            peak = np.array(self.avg_daily_peak_history)
            ax.plot(steps, smooth(list(peak)), 'red', linewidth=2)
            ax.set_title('Daily Peak (kW)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. (1 - Load Factor) (bottom-right)
            ax = axes[1, 2]
            one_minus_lf = np.array(self.one_minus_load_factor_history)
            ax.plot(steps, smooth(list(one_minus_lf)), 'orange', linewidth=2)
            ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.7)
            ax.fill_between(steps, 0, 0.3, alpha=0.1, color='green')
            ax.set_title('(1 - Load Factor)')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
            
            # Calcular mejoras para título
            improvements = []
            if len(consumption) > 1:
                imp = (consumption[0] - consumption[-1]) / max(abs(consumption[0]), 0.001) * 100
                if imp > 0:
                    improvements.append(f'Cons: {imp:.1f}%↓')
            if len(emissions) > 1:
                imp = (emissions[0] - emissions[-1]) / max(emissions[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'CO₂: {imp:.1f}%↓')
            if len(peak) > 1:
                imp = (peak[0] - peak[-1]) / max(peak[0], 0.001) * 100
                if imp > 0:
                    improvements.append(f'Peak: {imp:.1f}%↓')
            
            title = 'CityLearn KPIs Dashboard - A2C Training'
            if improvements:
                title += f'\n✅ Improvements: {", ".join(improvements)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'kpi_dashboard.png', dpi=150)
            plt.close(fig)
            print('     ✅ kpi_dashboard.png')
            
        except Exception as e:
            print(f'     ❌ Error en KPI dashboard: {e}')
        
        print(f'     📁 Gráficos KPIs guardados en: {self.output_dir}')
    
    def _generate_a2c_graphs(self) -> None:
        """
        Generar gráficos diagnósticos específicos de A2C.
        
        GRÁFICOS GENERADOS:
        1. Entropy vs Steps (con zona de colapso)
        2. Policy Loss vs Steps
        3. Value Loss vs Steps (con threshold warning)
        4. Explained Variance vs Steps (target zone)
        5. Grad Norm vs Steps (con clipping threshold)
        6. Dashboard combinado 2×3
        """
        
        if len(self.steps_history) < 2:
            print('     ⚠️ Insuficientes datos para gráficos A2C (< 2 puntos)')
            return
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Función helper para suavizado
        def smooth(data: list[float], window: int = 10) -> np.ndarray:
            """Rolling mean para suavizar curvas."""
            if len(data) < window:
                return np.array(data)
            return pd.Series(data).rolling(window=window, min_periods=1).mean().values
        
        steps = np.array(self.steps_history)
        
        # ====================================================================
        # GRÁFICO 1: ENTROPY vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            entropy = np.array(self.entropy_history)
            ax.plot(steps, entropy, 'b-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(entropy)), 'b-', linewidth=2, label='Smoothed')
            
            # Zona de colapso (< 0.1)
            ax.axhline(y=self.min_entropy, color='r', linestyle='--', 
                      label=f'Collapse zone ({self.min_entropy})')
            ax.fill_between(steps, 0, self.min_entropy, alpha=0.1, color='red')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Entropy')
            ax.set_title('A2C Entropy vs Training Steps\n(Higher = more exploration)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotación si hay colapso
            if self.entropy_collapse_alerts > 0:
                ax.annotate(f'⚠️ {self.entropy_collapse_alerts} collapse alerts', 
                           xy=(0.02, 0.98), xycoords='axes fraction',
                           fontsize=10, color='red', verticalalignment='top')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_entropy.png', dpi=150)
            plt.close(fig)
            print('     ✅ a2c_entropy.png')
        except Exception as e:
            print(f'     ❌ Error en entropy graph: {e}')
        
        # ====================================================================
        # GRÁFICO 2: POLICY LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            policy_loss = np.array(self.policy_loss_history)
            ax.plot(steps, policy_loss, 'g-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(policy_loss)), 'g-', linewidth=2, label='Smoothed')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Policy Loss')
            ax.set_title('A2C Policy Loss vs Training Steps')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_policy_loss.png', dpi=150)
            plt.close(fig)
            print('     ✅ a2c_policy_loss.png')
        except Exception as e:
            print(f'     ❌ Error en policy loss graph: {e}')
        
        # ====================================================================
        # GRÁFICO 3: VALUE LOSS vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            value_loss = np.array(self.value_loss_history)
            ax.plot(steps, value_loss, 'r-', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(value_loss)), 'r-', linewidth=2, label='Smoothed')
            
            # Warning threshold
            ax.axhline(y=self.max_value_loss, color='orange', linestyle='--',
                      label=f'Warning threshold ({self.max_value_loss})')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Value Loss')
            ax.set_title('A2C Value Loss vs Training Steps\n(Lower is better after convergence)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # Anotación si hay alertas
            if self.high_value_loss_alerts > 0:
                ax.annotate(f'⚠️ {self.high_value_loss_alerts} high loss alerts', 
                           xy=(0.02, 0.98), xycoords='axes fraction',
                           fontsize=10, color='orange', verticalalignment='top')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_value_loss.png', dpi=150)
            plt.close(fig)
            print('     ✅ a2c_value_loss.png')
        except Exception as e:
            print(f'     ❌ Error en value loss graph: {e}')
        
        # ====================================================================
        # GRÁFICO 4: EXPLAINED VARIANCE vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            explained_var = np.array(self.explained_variance_history)
            ax.plot(steps, explained_var, 'purple', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(explained_var)), 'purple', linewidth=2, label='Smoothed')
            
            # Target zone (> 0.5 es bueno)
            ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.7, label='Good (>0.5)')
            ax.axhline(y=0.0, color='gray', linestyle='-', alpha=0.5, label='Random (0)')
            ax.fill_between(steps, 0.5, 1.0, alpha=0.1, color='green')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Explained Variance')
            ax.set_title('A2C Explained Variance vs Training Steps\n(1.0 = perfect value predictions)')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(-1, 1.1)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_explained_variance.png', dpi=150)
            plt.close(fig)
            print('     ✅ a2c_explained_variance.png')
        except Exception as e:
            print(f'     ❌ Error en explained variance graph: {e}')
        
        # ====================================================================
        # GRÁFICO 5: GRAD NORM vs STEPS
        # ====================================================================
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            grad_norm = np.array(self.grad_norm_history)
            ax.plot(steps, grad_norm, 'orange', alpha=0.3, linewidth=0.5, label='Raw')
            ax.plot(steps, smooth(list(grad_norm)), 'orange', linewidth=2, label='Smoothed')
            
            # Max grad norm configured
            ax.axhline(y=self.config.max_grad_norm, color='blue', linestyle='--',
                      label=f'Clipping threshold ({self.config.max_grad_norm})')
            
            # Alert threshold
            ax.axhline(y=self.max_grad_norm_alert, color='red', linestyle='--',
                      label=f'Alert threshold ({self.max_grad_norm_alert})')
            
            ax.set_xlabel('Steps')
            ax.set_ylabel('Gradient Norm')
            ax.set_title('A2C Gradient Norm vs Training Steps\n(Monitoring for explosion/vanishing)')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'a2c_grad_norm.png', dpi=150)
            plt.close(fig)
            print('     ✅ a2c_grad_norm.png')
        except Exception as e:
            print(f'     ❌ Error en grad norm graph: {e}')
        
        # ====================================================================
        # GRÁFICO 6: DASHBOARD COMBINADO 2×3
        # ====================================================================
        try:
            fig, axes = plt.subplots(2, 3, figsize=(16, 10))
            
            # 1. Entropy (top-left)
            ax = axes[0, 0]
            entropy = np.array(self.entropy_history)
            ax.plot(steps, smooth(list(entropy)), 'b-', linewidth=2)
            ax.axhline(y=self.min_entropy, color='r', linestyle='--', alpha=0.7)
            ax.fill_between(steps, 0, self.min_entropy, alpha=0.1, color='red')
            ax.set_title('Entropy')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 2. Policy Loss (top-center)
            ax = axes[0, 1]
            policy_loss = np.array(self.policy_loss_history)
            ax.plot(steps, smooth(list(policy_loss)), 'g-', linewidth=2)
            ax.set_title('Policy Loss')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            
            # 3. Value Loss (top-right)
            ax = axes[0, 2]
            value_loss = np.array(self.value_loss_history)
            ax.plot(steps, smooth(list(value_loss)), 'r-', linewidth=2)
            ax.axhline(y=self.max_value_loss, color='orange', linestyle='--', alpha=0.7)
            ax.set_title('Value Loss')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 4. Explained Variance (bottom-left)
            ax = axes[1, 0]
            explained_var = np.array(self.explained_variance_history)
            ax.plot(steps, smooth(list(explained_var)), 'purple', linewidth=2)
            ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.7)
            ax.axhline(y=0.0, color='gray', linestyle='-', alpha=0.5)
            ax.fill_between(steps, 0.5, 1.0, alpha=0.1, color='green')
            ax.set_title('Explained Variance')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(-1, 1.1)
            
            # 5. Grad Norm (bottom-center)
            ax = axes[1, 1]
            grad_norm = np.array(self.grad_norm_history)
            ax.plot(steps, smooth(list(grad_norm)), 'orange', linewidth=2)
            ax.axhline(y=self.config.max_grad_norm, color='blue', linestyle='--', alpha=0.7)
            ax.set_title('Gradient Norm')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(bottom=0)
            
            # 6. Learning Rate (bottom-right)
            ax = axes[1, 2]
            if self.lr_history:
                lr = np.array(self.lr_history)
                ax.plot(steps[:len(lr)], lr, 'brown', linewidth=2)
            ax.set_title('Learning Rate')
            ax.set_xlabel('Steps')
            ax.grid(True, alpha=0.3)
            ax.ticklabel_format(style='scientific', axis='y', scilimits=(0, 0))
            
            # Título general con info de alertas
            alert_text = []
            if self.entropy_collapse_alerts > 0:
                alert_text.append(f'Entropy: {self.entropy_collapse_alerts}')
            if self.high_value_loss_alerts > 0:
                alert_text.append(f'VLoss: {self.high_value_loss_alerts}')
            if self.grad_explosion_alerts > 0:
                alert_text.append(f'Grad: {self.grad_explosion_alerts}')
            
            title = 'A2C Training Dashboard'
            if alert_text:
                title += f'\n⚠️ Alerts: {", ".join(alert_text)}'
            
            fig.suptitle(title, fontsize=14, fontweight='bold')
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(self.output_dir / 'a2c_dashboard.png', dpi=150)
            plt.close(fig)
            print('     ✅ a2c_dashboard.png')
            
        except Exception as e:
            print(f'     ❌ Error en dashboard: {e}')
        
        print(f'     📁 Gráficos guardados en: {self.output_dir}')


# Configurar encoding UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
if hasattr(sys.stdout, 'reconfigure'):
    try:
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
    except (AttributeError, TypeError, RuntimeError):
        pass

warnings.filterwarnings('ignore', category=DeprecationWarning)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print('='*80)
print('ENTRENAR A2C - CON MULTIOBJETIVO REAL (CO2, SOLAR, COST, EV, GRID)')
print('='*80)
print(f'Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# A2C OPTIMIZADO PARA GPU (RTX 4060 8GB)
# A2C: Red 256x256 on-policy, n_steps=8 (updates frecuentes = fortaleza de A2C)
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    # Suprimir warning de SB3 sobre A2C en GPU (funciona, solo es menos eficiente)
    warnings.filterwarnings('ignore', message='.*A2C on the GPU.*')
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    print(f'🚀 GPU: {GPU_NAME}')
    print(f'   VRAM: {GPU_MEMORY:.1f} GB')
    print(f'   CUDA: {cuda_version}')
    print('   Entrenamiento A2C en GPU (red 256x256, n_steps=8)')
else:
    print('CPU mode - GPU no disponible')

print(f'   Device: {DEVICE.upper()}')
print()

CHECKPOINT_DIR = Path('checkpoints/A2C')
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path('outputs/a2c_training')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== DATASET CONSTRUCTION HELPERS - Build CityLearn v2 environment from OE2 data =====

def validate_solar_timeseries_hourly(solar_df: pd.DataFrame) -> None:
    """
    CRITICAL VALIDATION: Ensure solar timeseries is EXACTLY hourly (8,760 rows per year).
    
    NO 15-minute, 30-minute, or sub-hourly data allowed.
    """
    n_rows = len(solar_df)
    
    if n_rows != 8760:
        raise ValueError(
            f"[ERROR] CRITICAL: Solar timeseries MUST be exactly 8,760 rows (hourly, 1 year).\n"
            f"   Got {n_rows} rows instead.\n"
            f"   If using PVGIS 15-minute data, downsample: "
            f"df.set_index('time').resample('h').mean()"
        )
    
    if n_rows == 52560:
        raise ValueError(
            f"[ERROR] CRITICAL: Solar timeseries has {n_rows} rows = 8,760 × 6 (likely 15-minute data).\n"
            f"   This codebase ONLY supports hourly resolution (8,760 rows per year).\n"
            f"   Downsample using: df.set_index('time').resample('h').mean()"
        )


def load_real_charger_dataset(charger_data_path: Path) -> Optional[pd.DataFrame]:
    """
    Load real charger dataset from data/oe2/chargers/chargers_ev_ano_2024_v3.csv (38 sockets, 353 columnas)
    
    CRITICAL: This is the NEW REAL DATASET with:
    - 38 individual socket columns (30 motos + 8 mototaxis) [v5.2]
    - 8,760 hourly timesteps (full year 2024)
    - Individual socket control capability for RL agents
    """
    if not charger_data_path.exists():
        return None
    
    try:
        df = pd.read_csv(charger_data_path, index_col=0, parse_dates=True)
        
        if df.shape[0] != 8760:
            raise ValueError(f"Charger dataset MUST have 8,760 rows (hourly), got {df.shape[0]}")
        
        if df.shape[1] != 38:
            raise ValueError(f"Charger dataset MUST have 38 columns (sockets), got {df.shape[1]}")
        
        if len(df.index) > 1:
            dt = (df.index[1] - df.index[0]).total_seconds() / 3600
            if abs(dt - 1.0) > 0.01:
                raise ValueError(f"Charger dataset MUST be hourly frequency, got {dt:.2f} hours")
        
        min_val = df.min().min()
        max_val = df.max().max()
        print(f"[CHARGERS REAL] ✅ Loaded: {df.shape} (8760 hours × 38 sockets)")
        print(f"[CHARGERS REAL]   Value range: [{min_val:.2f}, {max_val:.2f}] kW")
        print(f"[CHARGERS REAL]   Annual energy: {df.sum().sum():,.0f} kWh")
        
        return df
        
    except Exception as e:
        print(f"[CHARGERS REAL] Error loading: {e}")
        raise


def build_oe2_dataset(interim_oe2_dir: Path) -> dict[str, Any]:
    """
    Build complete OE2 dataset from 5 required files.
    
    SINCRONIZACIÓN DATASET_BUILDER v5.5:
    ================================================================================
    Esta función carga TODOS los datasets considerados en dataset_builder.py
    asegurando que se usen TODAS LAS COLUMNAS OBSERVABLES definidas:
    
    CHARGERS (10 columnas observables):
      - Prefijo "ev_": is_hora_punta, tarifa_aplicada_soles, energia_total_kwh,
        costo_carga_soles, energia_motos_kwh, energia_mototaxis_kwh,
        co2_reduccion_motos_kg (factor neto 0.87), co2_reduccion_mototaxis_kg (0.47),
        reduccion_directa_co2_kg, demand_kwh
      - Archivo: chargers_ev_ano_2024_v3.csv (38 sockets reales = 19 chargers × 2 tomas)
      - 38 sockets (30 motos + 8 mototaxis)
    
    SOLAR (6 columnas observables):
      - Prefijo "solar_": is_hora_punta, tarifa_aplicada_soles, ahorro_soles,
        reduccion_indirecta_co2_kg (factor 0.4521), co2_mall_kg, co2_ev_kg
      - Archivo: pv_generation_timeseries.csv
      - Capacidad: 4,050 kWp
    
    BESS (5 columnas observables) v5.5 NEW:
      - Prefijo "bess_": soc_percent (20-100%), charge_kwh, discharge_kwh,
        to_mall_kwh, to_ev_kwh
      - Archivo: bess_hourly_dataset_2024.csv
      - Especificaciones: 1,700 kWh, 400 kW
    
    MALL (3 columnas observables) v5.5 NEW:
      - Prefijo "mall_": demand_kwh, demand_reduction_kwh, cost_soles
      - Archivo: demandamallhorakwh.csv
    
    CONTEXTO IQUITOS:
      - CO2 factor grid: 0.4521 kg CO2/kWh (red térmica aislada)
      - Tarifa HP: 0.45 S/. (18:00-22:59)
      - Tarifa HFP: 0.28 S/.
    
    BASELINE COMPARISON (opcional):
      - CON_SOLAR: Sistema con 4,050 kWp + BESS + agente
      - SIN_SOLAR: Sistema sin solar (solo grid)
    
    METADATA DE ESCENARIOS (data/oe2/chargers/) v5.5:
      - selection_pe_fc_completo.csv: 54 escenarios (pe, fc, chargers_required, etc.)
      - tabla_escenarios_detallados.csv: CONSERVADOR, MEDIANO, RECOMENDADO*, MÁXIMO
      - tabla_estadisticas_escenarios.csv: Estadísticas agregadas
      - escenarios_tabla13.csv: 101 escenarios PE/FC
      → Cargar con: data_loader.load_scenarios_metadata()
      → ESCENARIO RECOMENDADO v5.5: PE=1.00, FC=1.00, 19 cargadores, 38 tomas, 1129 kWh/día
    
    El agente A2C recibe TODAS ESTAS COLUMNAS (27 observables)
    para entrenar con multiobjetivo (CO2, solar, costo, EV, grid).
    ================================================================================
    """
    print("\n" + "="*80)
    print("[DATASET BUILD] Cargando 5 archivos OE2 REALES OBLIGATORIOS")
    print("="*80)
    
    result: dict[str, Any] = {}
    
    # 1. SOLAR (pv_generation_timeseries.csv)
    solar_path = interim_oe2_dir / 'solar' / 'pv_generation_timeseries.csv'
    if not solar_path.exists():
        raise ValueError(f"❌ Solar REQUERIDO no encontrado: {solar_path}")
    solar_df = pd.read_csv(solar_path)
    validate_solar_timeseries_hourly(solar_df)
    solar_hourly = np.asarray(solar_df.iloc[:, 0], dtype=np.float32)
    result['solar'] = solar_hourly
    print(f"[SOLAR] ✅ Cargado: {len(solar_hourly)} horas, {solar_hourly.sum():.0f} kWh/año")
    
    # 2. CHARGERS (chargers_ev_ano_2024_v3.csv - 38 sockets ESPECIFICACIÓN OE2)
    chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    chargers_df = load_real_charger_dataset(chargers_path)
    if chargers_df is None or chargers_df.empty:
        raise ValueError(f"❌ Chargers REQUERIDO no cargado: {chargers_path}")
    chargers_hourly = np.asarray(chargers_df, dtype=np.float32)
    result['chargers'] = chargers_hourly
    
    # 3. MALL (demandamallhorakwh.csv)
    mall_path = interim_oe2_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
    if not mall_path.exists():
        raise ValueError(f"❌ Mall demand REQUERIDO no encontrado: {mall_path}")
    mall_df = pd.read_csv(mall_path)
    if len(mall_df) != 8760:
        raise ValueError(f"❌ Mall demand debe tener 8,760 filas, tiene {len(mall_df)}")
    mall_hourly = np.asarray(mall_df.iloc[:, 0], dtype=np.float32)
    result['mall'] = mall_hourly
    print(f"[MALL] ✅ Cargado: {len(mall_hourly)} horas, {mall_hourly.sum():.0f} kWh/año")
    
    # 4. BESS (bess_hourly_dataset_2024.csv)
    bess_path = interim_oe2_dir / 'bess' / 'bess_hourly_dataset_2024.csv'
    if not bess_path.exists():
        raise ValueError(f"❌ BESS REQUERIDO no encontrado: {bess_path}")
    bess_df = pd.read_csv(bess_path)
    if len(bess_df) != 8760:
        raise ValueError(f"❌ BESS debe tener 8,760 filas, tiene {len(bess_df)}")
    bess_soc = np.asarray(bess_df.iloc[:, 1] if len(bess_df.columns) > 1 else bess_df.iloc[:, 0], dtype=np.float32)
    result['bess'] = bess_soc
    print(f"[BESS] ✅ Cargado: {len(bess_soc)} horas, SOC promedio {bess_soc.mean():.1f}%")
    
    # 5. CONTEXT (Iquitos parameters)
    context = IquitosContext()
    result['context'] = context  # type: ignore[assignment]
    print(f"[CONTEXT] ✅ Cargado: CO2={context.co2_factor_kg_per_kwh} kg/kWh, Chargers={context.n_chargers}")
    
    print("="*80)
    print("[DATASET BUILD] ✅ Todos los 5 archivos OE2 cargados exitosamente")
    print("="*80)
    
    return result


# ===== DETAILED LOGGING CALLBACK (IGUAL QUE PPO) =====
class DetailedLoggingCallback(BaseCallback):
    """Callback para registrar métricas detalladas en cada step - misma estructura que PPO."""

    def __init__(self, env_ref: Any = None, output_dir: Path | None = None, verbose: int = 0, total_timesteps: int = 87600):
        super().__init__(verbose)
        self.env_ref = env_ref
        self.output_dir = output_dir
        self.total_timesteps = total_timesteps
        self.start_time = time.time()
        self.last_log_time = time.time()
        self.log_interval = 5000  # Log cada 5000 steps
        
        # ===== CARGAR DATASET REAL DE BESS (bess_ano_2024.csv) =====
        bess_real_path = Path('data/oe2/bess/bess_ano_2024.csv')
        if bess_real_path.exists():
            self.bess_real_df = pd.read_csv(bess_real_path)
            print(f'  [BESS REAL] Cargado: {len(self.bess_real_df)} horas')
        else:
            self.bess_real_df = None
            print(f'  [BESS REAL] No encontrado: {bess_real_path}')
        
        # Trace y timeseries records
        self.trace_records: list[dict[str, Any]] = []
        self.timeseries_records: list[dict[str, Any]] = []
        
        # Episode tracking (IGUAL QUE PPO)
        self.episode_count = 0
        self.step_in_episode = 0
        self.current_episode_reward = 0.0
        
        # Métricas por episodio (IGUAL QUE PPO + NUEVAS METRICAS)
        self.episode_rewards: list[float] = []
        self.episode_co2_grid: list[float] = []
        self.episode_co2_avoided_indirect: list[float] = []
        self.episode_co2_avoided_direct: list[float] = []
        self.episode_solar_kwh: list[float] = []
        self.episode_ev_charging: list[float] = []
        self.episode_grid_import: list[float] = []
        
        # ✅ NUEVAS: Estabilidad, Costos, Motos/Mototaxis
        self.episode_grid_stability: list[float] = []  # Promedio estabilidad por episodio
        self.episode_cost_usd: list[float] = []        # Costo total por episodio
        self.episode_motos_charged: list[int] = []     # Motos cargadas (>50% setpoint)
        self.episode_mototaxis_charged: list[int] = [] # Mototaxis cargadas (>50% setpoint)
        self.episode_bess_discharge_kwh: list[float] = []  # Descarga BESS por episodio
        self.episode_bess_charge_kwh: list[float] = []     # Carga BESS por episodio
        
        # ✅ NUEVAS: Progreso de control por socket y BESS
        self.episode_avg_socket_setpoint: list[float] = []  # Setpoint promedio 38 sockets
        self.episode_socket_utilization: list[float] = []   # % sockets activos (>0.1)
        self.episode_bess_action_avg: list[float] = []      # Acción BESS promedio [0-1]
        
        # ✅ NUEVAS: Reward components por episodio
        self.episode_r_solar: list[float] = []
        self.episode_r_cost: list[float] = []
        self.episode_r_ev: list[float] = []
        self.episode_r_grid: list[float] = []
        self.episode_r_co2: list[float] = []
        
        # Acumuladores episodio actual
        self._current_co2_grid = 0.0
        self._current_co2_avoided_indirect = 0.0
        self._current_co2_avoided_direct = 0.0
        self._current_solar_kwh = 0.0
        self._current_ev_charging = 0.0
        self._current_grid_import = 0.0
        
        # ✅ NUEVOS acumuladores
        self._current_stability_sum = 0.0
        self._current_stability_count = 0
        self._current_cost_usd = 0.0
        self._current_motos_charged_max = 0
        self._current_mototaxis_charged_max = 0
        self._current_bess_discharge = 0.0
        self._current_bess_charge = 0.0
        self._current_socket_setpoint_sum = 0.0
        self._current_socket_active_count = 0
        self._current_bess_action_sum = 0.0
        
        # ✅ NUEVOS acumuladores reward components
        self._current_r_solar_sum = 0.0
        self._current_r_cost_sum = 0.0
        self._current_r_ev_sum = 0.0
        self._current_r_grid_sum = 0.0
        self._current_r_co2_sum = 0.0
        
        # ✅ TRACKING DE VEHÍCULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
        self.episode_motos_10_max: float = 0
        self.episode_motos_20_max: float = 0
        self.episode_motos_30_max: float = 0
        self.episode_motos_50_max: float = 0
        self.episode_motos_70_max: float = 0
        self.episode_motos_80_max: float = 0
        self.episode_motos_100_max: float = 0
        
        self.episode_taxis_10_max: float = 0
        self.episode_taxis_20_max: float = 0
        self.episode_taxis_30_max: float = 0
        self.episode_taxis_50_max: float = 0
        self.episode_taxis_70_max: float = 0
        self.episode_taxis_80_max: float = 0
        self.episode_taxis_100_max: float = 0

    def _on_init(self) -> None:
        """Initialize callback after model is set. Called by BaseCallback."""
        pass

    def _on_step(self) -> bool:
        """Llamado en cada step del entrenamiento."""
        infos = self.locals.get('infos', [{}])
        rewards = self.locals.get('rewards', [0.0])
        dones = self.locals.get('dones', [False])
        
        # PROGRESO: Mostrar cada 5000 steps
        if self.num_timesteps % self.log_interval == 0 and self.num_timesteps > 0:
            elapsed = time.time() - self.start_time
            speed = self.num_timesteps / max(elapsed, 0.001)
            pct = 100.0 * self.num_timesteps / self.total_timesteps
            # ✅ CORREGIDO: Mostrar R_avg desde episodio 1 (antes requería 5+)
            mean_reward = np.mean(self.episode_rewards[-5:]) if len(self.episode_rewards) >= 1 else 0.0
            eta_seconds = (self.total_timesteps - self.num_timesteps) / max(speed, 1.0)
            print(f'  Step {self.num_timesteps:>7,}/{self.total_timesteps:,} ({pct:>5.1f}%) | '
                  f'Ep={self.episode_count} | R_avg={mean_reward:>6.2f} | '
                  f'{speed:,.0f} sps | ETA={eta_seconds/60:.1f}min', flush=True)

        for i, info in enumerate(infos):
            reward = float(rewards[i]) if i < len(rewards) else 0.0
            done = bool(dones[i]) if i < len(dones) else False

            self.current_episode_reward += reward
            self.step_in_episode += 1
            
            # Acumular métricas del step
            self._current_co2_grid += info.get('co2_grid_kg', 0.0)
            self._current_co2_avoided_indirect += info.get('co2_avoided_indirect_kg', 0.0)
            self._current_co2_avoided_direct += info.get('co2_avoided_direct_kg', 0.0)
            self._current_solar_kwh += info.get('solar_generation_kwh', 0.0)
            self._current_ev_charging += info.get('ev_charging_kwh', 0.0)
            self._current_grid_import += info.get('grid_import_kwh', 0.0)
            
            # ✅ NUEVAS métricas: Estabilidad, Costos, Motos/Mototaxis, BESS
            # Estabilidad: calcular ratio de variación de grid import
            grid_import = info.get('grid_import_kwh', 0.0)
            grid_export = info.get('grid_export_kwh', 0.0)
            peak_demand_limit = 450.0  # kW límite típico
            stability = 1.0 - min(1.0, abs(grid_import - grid_export) / peak_demand_limit)
            self._current_stability_sum += stability
            self._current_stability_count += 1
            
            # Costo: tarifa × (import - export)
            tariff_usd = 0.15  # USD/kWh tarifa Iquitos
            cost_step = (grid_import - grid_export * 0.5) * tariff_usd
            self._current_cost_usd += max(0.0, cost_step)
            
            # Motos y mototaxis (máximo por episodio)
            motos = info.get('motos_charging', 0)
            mototaxis = info.get('mototaxis_charging', 0)
            self._current_motos_charged_max = max(self._current_motos_charged_max, motos)
            self._current_mototaxis_charged_max = max(self._current_mototaxis_charged_max, mototaxis)
            
            # BESS (descarga/carga) - DATOS REALES del dataset OE2
            # Usa flujos reales de bess_ano_2024.csv en lugar de calcular
            hour_of_year = info.get('hour_of_year', self.step_in_episode % 8760)
            
            if self.bess_real_df is not None and hour_of_year < len(self.bess_real_df):
                # USAR DATOS REALES DEL DATASET
                bess_row = self.bess_real_df.iloc[hour_of_year]
                bess_charge_real = float(bess_row.get('bess_charge_kwh', 0.0))
                bess_discharge_real = float(bess_row.get('bess_discharge_kwh', 0.0))
                self._current_bess_charge += bess_charge_real
                self._current_bess_discharge += bess_discharge_real
                # También trackear destino de descarga
                self._current_bess_to_mall = getattr(self, '_current_bess_to_mall', 0.0) + float(bess_row.get('bess_to_mall_kwh', 0.0))
                self._current_bess_to_ev = getattr(self, '_current_bess_to_ev', 0.0) + float(bess_row.get('bess_to_ev_kwh', 0.0))
            else:
                # FALLBACK: usar info del environment si no hay dataset
                bess_power = info.get('bess_power_kw', 0.0)
                if bess_power > 0:
                    self._current_bess_discharge += bess_power
                else:
                    self._current_bess_charge += abs(bess_power)
            
            # Progreso de control de sockets (desde acciones)
            actions = self.locals.get('actions', None)
            if actions is not None and len(actions) > 0:
                action = actions[0] if len(actions[0].shape) > 0 else actions
                if len(action) >= 39:  # v5.2: 1 BESS + 38 sockets
                    bess_action = float(action[0])
                    socket_setpoints = action[1:39]  # v5.2: 38 sockets
                    self._current_bess_action_sum += bess_action
                    self._current_socket_setpoint_sum += float(np.mean(socket_setpoints))
                    self._current_socket_active_count += int(np.sum(socket_setpoints > 0.1))
            
            # ✅ NUEVAS: Acumular reward components desde info
            self._current_r_solar_sum += info.get('r_solar', 0.0)
            self._current_r_cost_sum += info.get('r_cost', 0.0)
            self._current_r_ev_sum += info.get('r_ev', 0.0)
            self._current_r_grid_sum += info.get('r_grid', 0.0)
            self._current_r_co2_sum += info.get('r_co2', 0.0)
            
            # ✅ ACTUALIZAR MÁXIMOS DE VEHÍCULOS POR SOC (desde environment)
            self.episode_motos_10_max = max(self.episode_motos_10_max, info.get('motos_10_percent', 0))
            self.episode_motos_20_max = max(self.episode_motos_20_max, info.get('motos_20_percent', 0))
            self.episode_motos_30_max = max(self.episode_motos_30_max, info.get('motos_30_percent', 0))
            self.episode_motos_50_max = max(self.episode_motos_50_max, info.get('motos_50_percent', 0))
            self.episode_motos_70_max = max(self.episode_motos_70_max, info.get('motos_70_percent', 0))
            self.episode_motos_80_max = max(self.episode_motos_80_max, info.get('motos_80_percent', 0))
            self.episode_motos_100_max = max(self.episode_motos_100_max, info.get('motos_100_percent', 0))
            
            self.episode_taxis_10_max = max(self.episode_taxis_10_max, info.get('taxis_10_percent', 0))
            self.episode_taxis_20_max = max(self.episode_taxis_20_max, info.get('taxis_20_percent', 0))
            self.episode_taxis_30_max = max(self.episode_taxis_30_max, info.get('taxis_30_percent', 0))
            self.episode_taxis_50_max = max(self.episode_taxis_50_max, info.get('taxis_50_percent', 0))
            self.episode_taxis_70_max = max(self.episode_taxis_70_max, info.get('taxis_70_percent', 0))
            self.episode_taxis_80_max = max(self.episode_taxis_80_max, info.get('taxis_80_percent', 0))
            self.episode_taxis_100_max = max(self.episode_taxis_100_max, info.get('taxis_100_percent', 0))

            # Registrar trace (cada step)
            trace_record = {
                'timestep': self.num_timesteps,
                'episode': self.episode_count,
                'step_in_episode': self.step_in_episode,
                'reward': reward,
                'cumulative_reward': self.current_episode_reward,
                'co2_grid_kg': info.get('co2_grid_kg', 0.0),
                'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0.0),
                'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0.0),
                'solar_generation_kwh': info.get('solar_generation_kwh', 0.0),
                'ev_charging_kwh': info.get('ev_charging_kwh', 0.0),
                'grid_import_kwh': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                'ev_soc_avg': info.get('ev_soc_avg', 0.0),
            }
            self.trace_records.append(trace_record)

            # Registrar timeseries (cada hora simulada)
            timeseries_record = {
                'timestep': self.num_timesteps,
                'hour': info.get('hour', self.step_in_episode % 8760),
                'solar_kw': info.get('solar_generation_kwh', 0.0),
                'mall_demand_kw': info.get('mall_demand_kw', 0.0),
                'ev_charging_kw': info.get('ev_charging_kwh', 0.0),
                'grid_import_kw': info.get('grid_import_kwh', 0.0),
                'bess_power_kw': info.get('bess_power_kw', 0.0),
                'bess_soc': info.get('bess_soc', 0.0),
                'motos_charging': info.get('motos_charging', 0),
                'mototaxis_charging': info.get('mototaxis_charging', 0),
            }
            self.timeseries_records.append(timeseries_record)

            if done:
                # Guardar métricas del episodio (IGUAL QUE PPO)
                self.episode_rewards.append(self.current_episode_reward)
                self.episode_co2_grid.append(self._current_co2_grid)
                self.episode_co2_avoided_indirect.append(self._current_co2_avoided_indirect)
                self.episode_co2_avoided_direct.append(self._current_co2_avoided_direct)
                self.episode_solar_kwh.append(self._current_solar_kwh)
                self.episode_ev_charging.append(self._current_ev_charging)
                self.episode_grid_import.append(self._current_grid_import)
                
                # ✅ NUEVAS métricas por episodio
                avg_stability = self._current_stability_sum / max(1, self._current_stability_count)
                self.episode_grid_stability.append(avg_stability)
                self.episode_cost_usd.append(self._current_cost_usd)
                self.episode_motos_charged.append(self._current_motos_charged_max)
                self.episode_mototaxis_charged.append(self._current_mototaxis_charged_max)
                self.episode_bess_discharge_kwh.append(self._current_bess_discharge)
                self.episode_bess_charge_kwh.append(self._current_bess_charge)
                
                # Promedios de control por episodio
                steps_in_ep = max(1, self.step_in_episode)
                self.episode_avg_socket_setpoint.append(self._current_socket_setpoint_sum / steps_in_ep)
                self.episode_socket_utilization.append(self._current_socket_active_count / (38.0 * steps_in_ep))
                self.episode_bess_action_avg.append(self._current_bess_action_sum / steps_in_ep)
                
                # ✅ NUEVAS: Promedios de reward components por episodio
                self.episode_r_solar.append(self._current_r_solar_sum / steps_in_ep)
                self.episode_r_cost.append(self._current_r_cost_sum / steps_in_ep)
                self.episode_r_ev.append(self._current_r_ev_sum / steps_in_ep)
                self.episode_r_grid.append(self._current_r_grid_sum / steps_in_ep)
                self.episode_r_co2.append(self._current_r_co2_sum / steps_in_ep)
                
                self.episode_count += 1
                
                # Reset acumuladores
                self.current_episode_reward = 0.0
                self.step_in_episode = 0
                self._current_co2_grid = 0.0
                self._current_co2_avoided_indirect = 0.0
                self._current_co2_avoided_direct = 0.0
                self._current_solar_kwh = 0.0
                self._current_ev_charging = 0.0
                self._current_grid_import = 0.0
                
                # ✅ Reset nuevos acumuladores
                self._current_stability_sum = 0.0
                self._current_stability_count = 0
                self._current_cost_usd = 0.0
                self._current_motos_charged_max = 0
                self._current_mototaxis_charged_max = 0
                self._current_bess_discharge = 0.0
                self._current_bess_charge = 0.0
                self._current_socket_setpoint_sum = 0.0
                self._current_socket_active_count = 0
                self._current_bess_action_sum = 0.0
                
                # ✅ Reset acumuladores reward components
                self._current_r_solar_sum = 0.0
                self._current_r_cost_sum = 0.0
                self._current_r_ev_sum = 0.0
                self._current_r_grid_sum = 0.0
                self._current_r_co2_sum = 0.0
                
                # ✅ RESET TRACKING DE VEHÍCULOS POR SOC
                self.episode_motos_10_max = 0.0
                self.episode_motos_20_max = 0.0
                self.episode_motos_30_max = 0.0
                self.episode_motos_50_max = 0.0
                self.episode_motos_70_max = 0.0
                self.episode_motos_80_max = 0.0
                self.episode_motos_100_max = 0.0
                
                self.episode_taxis_10_max = 0.0
                self.episode_taxis_20_max = 0.0
                self.episode_taxis_30_max = 0.0
                self.episode_taxis_50_max = 0.0
                self.episode_taxis_70_max = 0.0
                self.episode_taxis_80_max = 0.0
                self.episode_taxis_100_max = 0.0

        return True

    def _on_training_end(self) -> None:
        """Guardar archivos al finalizar entrenamiento."""
        pass  # Los archivos se guardan en main()


try:
    print('[1] CARGAR CONFIGURACION Y CONTEXTO MULTIOBJETIVO')
    print('-' * 80)

    with open('configs/default.yaml', 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    print(f'  OK Config loaded: {len(cfg)} keys')

    weights = create_iquitos_reward_weights("co2_focus")
    context = IquitosContext()
    reward_calculator = MultiObjectiveReward(weights=weights, context=context)

    print('  REWARD WEIGHTS (ACTUALIZADOS 2026-02-08 - LOG SAC):')
    print('    CO2 grid (0.35): Minimizar importacion grid')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90%')
    print('    Cost (0.10): Minimizar costo')
    print('    Grid stability (0.05): Suavizar picos')
    if weights is not None:
        print('  [Valores cargados: CO2={:.2f}, Solar={:.2f}, EV={:.2f}, Cost={:.2f}, Grid={:.2f}]'.format(
            weights.co2, weights.solar, weights.ev_satisfaction,
            weights.cost, weights.grid_stability))
    print()

    print('  OK Contexto Iquitos:')
    print(f'    - Grid CO2: {context.co2_factor_kg_per_kwh} kg CO2/kWh')
    print(f'    - EV CO2 factor: {context.co2_conversion_factor} kg CO2/kWh')
    print(f'    - Chargers: {context.n_chargers}')
    print(f'    - Sockets: {context.total_sockets}')
    print(f'    - Daily capacity: {context.motos_daily_capacity} motos + {context.mototaxis_daily_capacity} mototaxis')
    print()

    print('[2] CARGAR DATASET CITYLEARN V2 (COMPILADO)')
    print('-' * 80)

    # Dataset ya compilado en data/processed/citylearn/iquitos_ev_mall
    processed_path = Path('data/processed/citylearn/iquitos_ev_mall')
    if not processed_path.exists():
        print(f'ERROR: Dataset no encontrado en {processed_path}')
        print('   Crea el dataset primero con: python build.py')
        sys.exit(1)

    print(f'  Dataset precompilado: {processed_path}')
    dataset_dir = processed_path
    print(f'  OK Dataset: {dataset_dir}')
    print()

    # ========================================================================
    # PASO 3: CARGAR DATOS REALES OE2 (IGUAL QUE PPO)
    # ========================================================================
    print('[3] CARGAR DATOS DEL DATASET CITYLEARN V2 CONSTRUIDO ({} horas = 1 año)'.format(HOURS_PER_YEAR))
    print('-' * 80)

    # ====================================================================
    # SOLAR - RUTA REAL OE2 v5.5
    # ====================================================================
    solar_path: Path = Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
    if not solar_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Solar CSV REAL no encontrado: {solar_path}")
    
    df_solar = pd.read_csv(solar_path)
    # Prioridad: pv_generation_kwh (energía horaria) > ac_power_kw (potencia)
    if 'pv_generation_kwh' in df_solar.columns:
        col = 'pv_generation_kwh'
    elif 'ac_power_kw' in df_solar.columns:
        col = 'ac_power_kw'
    else:
        raise KeyError(f"Solar CSV debe tener 'pv_generation_kwh' o 'ac_power_kw'. Columnas: {list(df_solar.columns)}")
    
    solar_hourly = np.asarray(df_solar[col].values, dtype=np.float32)
    if len(solar_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Solar: {len(solar_hourly)} horas != {HOURS_PER_YEAR}")
    print('  [SOLAR] REAL (CityLearn v2): columna=%s | %.0f kWh/año (8760h)' % (col, float(np.sum(solar_hourly))))

    # ====================================================================
    # CHARGERS (38 sockets) - ESPECIFICACION OE2 v5.2
    # ====================================================================
    # ✅ OBLIGATORIO: chargers_ev_ano_2024_v3.csv con demanda REAL
    # Contiene 38 columnas de demanda horaria real (19 chargers × 2 sockets)
    charger_real_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    
    if not charger_real_path.exists():
        raise FileNotFoundError(
            f"OBLIGATORIO: chargers_ev_ano_2024_v3.csv NO ENCONTRADO\n"
            f"  Ruta esperada: {charger_real_path}\n"
            f"  ERROR: No hay datos REALES de chargers. Especificación OE2 v5.2 requiere 38 sockets."
        )
    
    print(f'  [CHARGERS] ✅ Cargando datos REALES desde: {charger_real_path.name} (38 sockets)')
    df_chargers = pd.read_csv(charger_real_path)
    
    # Excluir columna timestamp y columnas no numéricas (vehicle_type), tomar solo columnas de potencia (charger_power_kw)
    # Las columnas válidas son: socket_XXX_charger_power_kw (38 columnas para 38 sockets)
    data_cols = [c for c in df_chargers.columns if 'charger_power_kw' in c.lower()]
    
    if not data_cols:
        # Fallback: intentar con cualquier columna que no sea datetime o vehicle_type
        data_cols = [c for c in df_chargers.columns if all(x not in c.lower() for x in ['timestamp', 'time', 'vehicle_type', 'datetime'])]
    
    chargers_hourly = df_chargers[data_cols].values[:HOURS_PER_YEAR].astype(np.float32)
    
    n_sockets = chargers_hourly.shape[1]
    total_demand = float(np.sum(chargers_hourly))
    
    # Validar que tenemos 38 sockets (v5.2): 19 cargadores × 2 = 38 sockets
    # Si hay más columnas, tomar solo las primeras 38 (compatible con v5.2)
    if n_sockets > 38:
        print(f"  ⚠ AJUSTE v5.2: Reduciendo {n_sockets} → 38 sockets (19 chargers × 2)")
        chargers_hourly = chargers_hourly[:, :38]
        n_sockets = 38
        total_demand = float(np.sum(chargers_hourly))
    elif n_sockets != 38:
        print(f"  ⚠ ADVERTENCIA: Se encontraron {n_sockets} sockets en lugar de 38 (v5.2)")
    
    if len(chargers_hourly) != HOURS_PER_YEAR:
        raise ValueError(f"Chargers: {len(chargers_hourly)} horas != {HOURS_PER_YEAR}")
    
    print("  [CHARGERS] DATASET REAL: %d sockets | Demanda: %.0f kWh/año | Promedio: %.2f kW/socket" % 
          (n_sockets, total_demand, total_demand / n_sockets / HOURS_PER_YEAR))

    # ====================================================================
    # MALL DEMAND - DEL DATASET CITYLEARN V2 (prioridad) o interim
    # ====================================================================
    mall_path = dataset_dir / 'demandamallkwh' / 'demandamallhorakwh.csv'
    if not mall_path.exists():
        mall_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')
    if not mall_path.exists():
        raise FileNotFoundError(f"OBLIGATORIO: Mall demand no encontrado en dataset")
    
    # Intentar cargar con diferentes separadores
    try:
        df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
    except Exception:
        df_mall = pd.read_csv(mall_path, encoding='utf-8')
    col = df_mall.columns[-1]
    mall_data = np.asarray(df_mall[col].values[:HOURS_PER_YEAR], dtype=np.float32)
    if len(mall_data) < HOURS_PER_YEAR:
        mall_hourly = np.pad(mall_data, ((0, HOURS_PER_YEAR - len(mall_data)),), mode='wrap')
    else:
        mall_hourly = mall_data
    print("  [MALL] DATASET: %.0f kWh/año (promedio %.1f kW/h)" % (float(np.sum(mall_hourly)), float(np.mean(mall_hourly))))

    # ====================================================================
    # BESS SIMULATION COMPLETO - DATOS REALES CON CO2, COSTOS, TARIFAS
    # ====================================================================
    # Prioridad 1: bess_ano_2024.csv (COMPLETO con métricas)
    bess_sim_path = Path('data/oe2/bess/bess_ano_2024.csv')
    bess_dataset_path = dataset_dir / 'electrical_storage_simulation.csv'
    bess_interim_paths = [
        dataset_dir / 'bess' / 'bess_hourly_dataset_2024.csv',
        Path('data/interim/oe2/bess/bess_hourly_dataset_2024.csv'),
    ]
    
    # Inicializar arrays de BESS con métricas completas
    bess_data: dict[str, np.ndarray] = {}
    
    if bess_sim_path.exists():
        print(f"  [BESS] Cargando DATOS REALES COMPLETOS desde: {bess_sim_path.name}")
        df_bess = pd.read_csv(bess_sim_path, encoding='utf-8')
        
        # Cargar TODAS las métricas disponibles
        bess_cols = {
            'bess_soc_percent': 'soc',           # SOC %
            'bess_charge_kwh': 'charge',         # Carga kWh
            'bess_discharge_kwh': 'discharge',   # Descarga kWh
            'bess_to_ev_kwh': 'to_ev',           # BESS → EV
            'bess_to_mall_kwh': 'to_mall',       # BESS → Mall
            'pv_to_bess_kwh': 'pv_charge',       # PV → BESS
            'grid_to_bess_kwh': 'grid_charge',   # Grid → BESS
            'co2_avoided_indirect_kg': 'co2_avoided',  # CO2 evitado
            'cost_grid_import_soles': 'cost',    # Costo grid S/.
            'tariff_osinergmin_soles_kwh': 'tariff',  # Tarifa S/./kWh
            'peak_reduction_savings_soles': 'peak_savings',  # Ahorro punta
            'grid_import_total_kwh': 'grid_import',  # Import grid total
            'pv_to_ev_kwh': 'pv_to_ev',          # PV → EV directo
            'pv_to_mall_kwh': 'pv_to_mall',      # PV → Mall
            'pv_curtailed_kwh': 'pv_curtailed',  # PV descartado
        }
        
        for col_name, key in bess_cols.items():
            if col_name in df_bess.columns:
                bess_data[key] = np.asarray(df_bess[col_name].values[:HOURS_PER_YEAR], dtype=np.float32)
        
        # SOC normalizado [0,1]
        if 'soc' in bess_data:
            bess_soc = bess_data['soc'] / 100.0
        else:
            bess_soc = np.full(HOURS_PER_YEAR, 0.5, dtype=np.float32)
        
        print(f"  [BESS] MÉTRICAS CARGADAS: {len(bess_data)} columnas")
        print(f"         SOC: {float(np.mean(bess_soc))*100:.1f}% promedio")
        if 'co2_avoided' in bess_data:
            print(f"         CO2 evitado: {float(np.sum(bess_data['co2_avoided'])):,.0f} kg/año")
        if 'cost' in bess_data:
            print(f"         Costo grid: S/. {float(np.sum(bess_data['cost'])):,.0f}/año")
        if 'charge' in bess_data and 'discharge' in bess_data:
            print(f"         Carga: {float(np.sum(bess_data['charge'])):,.0f} kWh | Descarga: {float(np.sum(bess_data['discharge'])):,.0f} kWh")
    else:
        # Fallback a archivos anteriores
        bess_path: Path | None = None
        if bess_dataset_path.exists():
            bess_path = bess_dataset_path
        else:
            for p in bess_interim_paths:
                if p.exists():
                    bess_path = p
                    break
        
        if bess_path is None:
            raise FileNotFoundError("OBLIGATORIO: BESS data no encontrado")
        
        df_bess = pd.read_csv(str(bess_path), encoding='utf-8')
        if 'soc_stored_kwh' in df_bess.columns:
            bess_soc_kwh = np.asarray(df_bess['soc_stored_kwh'].values[:HOURS_PER_YEAR], dtype=np.float32)
            bess_soc = bess_soc_kwh / BESS_CAPACITY_KWH
        else:
            soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
            if not soc_cols:
                raise KeyError(f"BESS CSV debe tener columna 'soc'. Columnas: {list(df_bess.columns)}")
            bess_soc_raw = np.asarray(df_bess[soc_cols[0]].values[:HOURS_PER_YEAR], dtype=np.float32)
            bess_soc = (bess_soc_raw / 100.0 if float(np.max(bess_soc_raw)) > 1.0 else bess_soc_raw)
        print(f"  [BESS] FALLBACK: SOC media {float(np.mean(bess_soc))*100:.1f}%")
    
    # ====================================================================
    # EV CHARGERS COMPLETO - DATOS REALES CON SOC, TIPO VEHÍCULO, ESTADO
    # ====================================================================
    ev_chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    ev_data: dict[str, np.ndarray] = {}
    
    if ev_chargers_path.exists():
        print(f"  [EV] Cargando DATOS REALES COMPLETOS desde: {ev_chargers_path.name}")
        df_ev = pd.read_csv(ev_chargers_path, encoding='utf-8')
        
        # Cargar métricas por socket (primeros 38 sockets para v5.2)
        n_sockets_ev = min(38, len([c for c in df_ev.columns if 'socket_' in c and '_soc_current' in c]))
        
        # Arrays agregados por hora
        ev_soc_current = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
        ev_soc_target = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
        ev_active_count = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
        ev_charging_power = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
        ev_vehicle_count = np.zeros((HOURS_PER_YEAR,), dtype=np.float32)
        
        for i in range(n_sockets_ev):
            prefix = f'socket_{i:03d}_'
            if f'{prefix}soc_current' in df_ev.columns:
                ev_soc_current += df_ev[f'{prefix}soc_current'].values[:HOURS_PER_YEAR].astype(np.float32)
            if f'{prefix}soc_target' in df_ev.columns:
                ev_soc_target += df_ev[f'{prefix}soc_target'].values[:HOURS_PER_YEAR].astype(np.float32)
            if f'{prefix}active' in df_ev.columns:
                ev_active_count += df_ev[f'{prefix}active'].values[:HOURS_PER_YEAR].astype(np.float32)
            if f'{prefix}charging_power_kw' in df_ev.columns:
                ev_charging_power += df_ev[f'{prefix}charging_power_kw'].values[:HOURS_PER_YEAR].astype(np.float32)
            if f'{prefix}vehicle_count' in df_ev.columns:
                ev_vehicle_count += df_ev[f'{prefix}vehicle_count'].values[:HOURS_PER_YEAR].astype(np.float32)
        
        # Normalizar SOC por sockets activos
        active_mask = ev_active_count > 0
        ev_soc_current[active_mask] /= ev_active_count[active_mask]
        ev_soc_target[active_mask] /= ev_active_count[active_mask]
        
        ev_data['soc_current'] = ev_soc_current
        ev_data['soc_target'] = ev_soc_target
        ev_data['active_count'] = ev_active_count
        ev_data['charging_power'] = ev_charging_power
        ev_data['vehicle_count'] = ev_vehicle_count
        
        print(f"  [EV] MÉTRICAS CARGADAS: {len(ev_data)} arrays agregados")
        print(f"       SOC promedio: {float(np.mean(ev_soc_current[active_mask]))*100:.1f}%")
        print(f"       Vehículos activos: {float(np.sum(ev_active_count)):,.0f}/año")
        print(f"       Potencia carga: {float(np.sum(ev_charging_power)):,.0f} kWh/año")
    else:
        print(f"  [EV] ADVERTENCIA: {ev_chargers_path} no encontrado, usando solo demanda horaria")

    # ====================================================================
    # CHARGER STATISTICS (5to dataset OE2) - potencia máx/media por socket
    # ====================================================================
    charger_stats_path = Path('data/interim/oe2/chargers/chargers_real_statistics.csv')
    charger_max_power: np.ndarray | None = None
    charger_mean_power: np.ndarray | None = None
    
    if charger_stats_path.exists():
        df_stats = pd.read_csv(charger_stats_path)
        if len(df_stats) >= 38:
            charger_max_power = np.array(df_stats['max_power_kw'].values[:38], dtype=np.float32)
            charger_mean_power = np.array(df_stats['mean_power_kw'].values[:38], dtype=np.float32)
            min_pwr = float(np.min(charger_max_power))
            max_pwr = float(np.max(charger_max_power))
            mean_pwr = float(np.mean(charger_mean_power))
            print(f'  [CHARGER STATS] (5to OE2): max_power={min_pwr:.2f}-{max_pwr:.2f} kW, mean={mean_pwr:.2f} kW')
        else:
            print(f'  [CHARGER STATS] WARN: {len(df_stats)} filas < 38, usando valores por defecto')
    else:
        print('  [CHARGER STATS] WARN: archivo no encontrado, usando valores por defecto')

    print()

    # ========================================================================
    # PASO 4: CREAR ENVIRONMENT (IGUAL ESTRUCTURA QUE PPO)
    # ========================================================================
    print('[4] CREAR ENVIRONMENT CON DATOS OE2 REALES')
    print('-' * 80)

    class CityLearnEnvironment(Env):  # type: ignore[type-arg]
        """Environment compatible con Gymnasium para CityLearn v2.
        
        COMUNICACIÓN COMPLETA DEL SISTEMA v5.3
        ================================================================================
        El agente puede ver y coordinar TODOS los componentes del sistema:
        - BESS: estado, energía disponible, señales de carga/descarga
        - Solar: generación, excedente, ratio de uso para EVs
        - 38 Sockets: demanda, potencia, ocupación individual
        - Motos: cantidad cargando, en cola, SOC, tiempo restante
        - Mototaxis: igual que motos pero para sus 8 sockets
        - Coordinación: señales para optimizar flujo de energía
        
        Observation Space (156-dim v5.3):
        
        ENERGÍA DEL SISTEMA [0-7] (8 features):
        - [0]: Solar generation normalizada [0,1]
        - [1]: Mall demand normalizada [0,1]
        - [2]: BESS SOC [0,1]
        - [3]: BESS energía disponible normalizada
        - [4]: Solar excedente normalizado
        - [5]: Grid import necesario normalizado
        - [6]: Balance energético (-1 déficit, +1 excedente)
        - [7]: Capacidad EV libre normalizada
        
        ESTADO DE CARGADORES POR SOCKET [8-45] (38 sockets):
        - Demanda actual de cada socket normalizada [0,1]
        
        POTENCIA ACTUAL POR SOCKET [46-83] (38 sockets):
        - Potencia entregada a cada socket normalizada [0,1]
        
        OCUPACIÓN POR SOCKET [84-121] (38 sockets):
        - 1.0 si hay vehículo conectado, 0.0 si libre
        
        ESTADO DE VEHÍCULOS [122-137] (16 features):
        - [122]: Motos cargando actualmente (count/30)
        - [123]: Mototaxis cargando actualmente (count/8)  
        - [124]: Motos en cola esperando (count/100)
        - [125]: Mototaxis en cola esperando (count/20)
        - [126]: SOC promedio motos cargando [0,1]
        - [127]: SOC promedio mototaxis cargando [0,1]
        - [128]: Tiempo restante carga motos (horas norm)
        - [129]: Tiempo restante carga mototaxis (horas norm)
        - [130]: Sockets motos disponibles (count/30)
        - [131]: Sockets mototaxis disponibles (count/8)
        - [132]: Motos cargadas 100% hoy (count/270)
        - [133]: Mototaxis cargados 100% hoy (count/39)
        - [134]: Eficiencia carga actual [0,1]
        - [135]: Ratio solar usado para carga [0,1]
        - [136]: CO2 evitado acumulado (norm)
        - [137]: CO2 evitado potencial si carga más (norm)
        
        TIME FEATURES [138-143] (6 features):
        - [138]: Hora del día normalizada [0,1]
        - [139]: Día de semana normalizado [0,1]
        - [140]: Mes normalizado [0,1]
        - [141]: Indicador hora pico [0,1]
        - [142]: Factor CO2 Iquitos
        - [143]: Tarifa eléctrica (USD/kWh)
        
        COMUNICACIÓN INTER-SISTEMA [144-155] (12 features):
        - [144]: BESS puede suministrar a EVs [0,1]
        - [145]: Solar suficiente para demanda EV [0,1]
        - [146]: Grid necesario para completar carga [0,1]
        - [147]: Prioridad carga motos vs mototaxis [0,1]
        - [148]: Urgencia de carga (vehículos pendientes/capacidad)
        - [149]: Oportunidad solar (excedente/demanda EV)
        - [150]: BESS debería cargar (solar alto, demanda baja)
        - [151]: BESS debería descargar (solar bajo, demanda alta)
        - [152]: Potencial reducción CO2 con más carga
        - [153]: Saturación del sistema [0,1]
        - [154]: Eficiencia sistema completo [0,1]
        - [155]: Meta diaria de vehículos (progreso [0,1])

        Action Space (39-dim v5.2):
        - [0]: BESS control [0,1] (0=carga máx, 0.5=idle, 1=descarga máx)
        - [1:39]: 38 socket setpoints [0,1] (potencia asignada a cada socket)
        """
        
        HOURS_PER_YEAR: int = 8760
        NUM_CHARGERS: int = 38      # v5.2: 19 cargadores × 2 tomas = 38 sockets
        OBS_DIM: int = 156          # v5.3: 8 + 38*3 + 16 + 6 + 12 = 156 (comunicación completa)
        ACTION_DIM: int = 39        # v5.2: 1 BESS + 38 sockets

        def __init__(
            self,
            reward_calc: Any,
            ctx: Any,
            solar_kw: np.ndarray,
            chargers_kw: np.ndarray,
            mall_kw: np.ndarray,
            bess_soc_arr: np.ndarray,
            charger_max_power_kw: np.ndarray | None = None,
            charger_mean_power_kw: np.ndarray | None = None,
            bess_metrics: dict[str, np.ndarray] | None = None,
            ev_metrics: dict[str, np.ndarray] | None = None,
            max_steps: int = 8760
        ) -> None:
            """Inicializa environment con datos OE2 reales COMPLETOS (BESS + EV metrics)."""
            super().__init__()
            
            self.reward_calculator = reward_calc
            self.context = ctx
            self.max_steps = max_steps
            
            # DATOS REALES (8760 horas = 1 año)
            self.solar_hourly = np.asarray(solar_kw, dtype=np.float32)
            self.chargers_hourly = np.asarray(chargers_kw, dtype=np.float32)
            self.mall_hourly = np.asarray(mall_kw, dtype=np.float32)
            self.bess_soc_hourly = np.asarray(bess_soc_arr, dtype=np.float32)
            
            # ESTADISTICAS REALES DE CARGADORES (5to dataset OE2)
            if charger_max_power_kw is not None:
                self.charger_max_power = np.asarray(charger_max_power_kw, dtype=np.float32)
            else:
                # Fallback v5.2: 7.4 kW por socket (Modo 3 monofásico 32A @ 230V)
                self.charger_max_power = np.full(self.NUM_CHARGERS, 7.4, dtype=np.float32)
            if charger_mean_power_kw is not None:
                self.charger_mean_power = np.asarray(charger_mean_power_kw, dtype=np.float32)
            else:
                # Fallback v5.2: potencia efectiva = 7.4 × 0.62 = 4.6 kW
                self.charger_mean_power = np.full(self.NUM_CHARGERS, 4.6, dtype=np.float32)
            
            # MÉTRICAS REALES BESS (CO2, costos, tarifas, flujos energéticos)
            self.bess_metrics = bess_metrics if bess_metrics is not None else {}
            
            # MÉTRICAS REALES EV (SOC, conteos, potencias por hora)
            self.ev_metrics = ev_metrics if ev_metrics is not None else {}
            
            # Validación
            if len(self.solar_hourly) != self.HOURS_PER_YEAR:
                raise ValueError(f"Solar: {len(self.solar_hourly)} != {self.HOURS_PER_YEAR}")
            
            self.n_chargers = self.chargers_hourly.shape[1]
            
            # Para tracking de totales (backwards compatibility)
            self.chargers_total_kwh = float(np.sum(self.chargers_hourly))
            self.solar_hourly_kwh = self.solar_hourly  # Alias
            self.mall_hourly_kw = self.mall_hourly  # Alias

            # Espacios (Gymnasium API)
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(self.OBS_DIM,), dtype=np.float32
            )
            self.action_space = spaces.Box(
                low=0.0, high=1.0, shape=(self.ACTION_DIM,), dtype=np.float32
            )

            # STATE TRACKING
            self.step_count = 0
            self.episode_num = 0
            self.episode_reward = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import = 0.0
            self.episode_ev_satisfied = 0.0
            
            # Tracking acumulativo (backwards compatibility)
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            
            # [v5.3] ESTADO DE VEHÍCULOS (para comunicación del sistema)
            self.motos_charging_now: int = 0
            self.mototaxis_charging_now: int = 0
            self.motos_waiting: int = 0
            self.mototaxis_waiting: int = 0
            self.motos_soc_avg: float = 0.0
            self.mototaxis_soc_avg: float = 0.0
            self.motos_time_remaining: float = 0.0
            self.mototaxis_time_remaining: float = 0.0
            self.motos_charged_today: int = 0
            self.mototaxis_charged_today: int = 0
            self.daily_co2_avoided: float = 0.0
            
            # [v5.3] COMUNICACIÓN INTER-SISTEMA
            self.bess_available_kwh: float = 0.0
            self.solar_surplus_kwh: float = 0.0
            self.current_grid_import: float = 0.0
            self.system_efficiency: float = 0.0
            
            # ✅ TRACKING DE VEHÍCULOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
            self.episode_motos_10_max: float = 0
            self.episode_motos_20_max: float = 0
            self.episode_motos_30_max: float = 0
            self.episode_motos_50_max: float = 0
            self.episode_motos_70_max: float = 0
            self.episode_motos_80_max: float = 0
            self.episode_motos_100_max: float = 0
            
            self.episode_taxis_10_max: float = 0
            self.episode_taxis_20_max: float = 0
            self.episode_taxis_30_max: float = 0
            self.episode_taxis_50_max: float = 0
            self.episode_taxis_70_max: float = 0
            self.episode_taxis_80_max: float = 0
            self.episode_taxis_100_max: float = 0
            
            # Simulador de escenarios de carga (SINCRONIZADO CON PPO - habilitado)
            self.vehicle_simulator = VehicleChargingSimulator()
            # Seleccionar escenario basado en hora
            self.scenarios_by_hour = self._create_hour_scenarios()
        
        # Método para mapear horas a escenarios (SINCRONIZADO CON PPO - habilitado)
        def _create_hour_scenarios(self) -> Dict[int, VehicleChargingScenario]:
            """Mapea cada hora del año a un escenario de carga realista de Iquitos."""
            scenarios = {}
            for h in range(self.HOURS_PER_YEAR):
                hour_of_day = h % 24
                
                # Off-peak: 2-6 AM
                if 2 <= hour_of_day < 6:
                    scenarios[h] = SCENARIO_OFF_PEAK
                # Morning: 6-14 (bajo a moderado)
                elif 6 <= hour_of_day < 14:
                    scenarios[h] = SCENARIO_PEAK_AFTERNOON
                # Afternoon: 14-18 (carga rápida, moderada)
                elif 14 <= hour_of_day < 18:
                    scenarios[h] = SCENARIO_PEAK_AFTERNOON
                # Evening: 18-23 (pico máximo)
                elif 18 <= hour_of_day <= 22:
                    scenarios[h] = SCENARIO_EXTREME_PEAK if (19 <= hour_of_day <= 20) else SCENARIO_PEAK_EVENING
                # Noche: 23-2 (bajo)
                else:
                    scenarios[h] = SCENARIO_OFF_PEAK
            
            return scenarios
            
        def _make_observation(self, hour_idx: int) -> np.ndarray:
            """
            Crea observación v5.3 (156-dim) con COMUNICACIÓN COMPLETA del sistema.

            NORMALIZACIÓN CRÍTICA:
            Todas las features están en rango ~[0,1] para estabilidad del training.
            
            COMUNICACIÓN DEL SISTEMA:
            - El agente ve el estado completo de BESS, Solar, EVs, Cargadores
            - Puede coordinar carga de motos/mototaxis con disponibilidad solar
            - Sabe cuántos vehículos están cargando y cuántos faltan
            - Recibe señales de urgencia y oportunidad
            """
            obs = np.zeros(self.OBS_DIM, dtype=np.float32)
            h = hour_idx % self.HOURS_PER_YEAR
            hour_24 = h % 24
            day_of_year = (h // 24) % 365

            # ================================================================
            # [0-7] ENERGÍA DEL SISTEMA (8 features)
            # ================================================================
            solar_kw = float(self.solar_hourly[h])
            mall_kw = float(self.mall_hourly[h])
            bess_soc = float(self.bess_soc_hourly[h])
            
            # Calcular balance energético
            ev_demand_estimate = float(np.sum(self.chargers_hourly[h]))
            total_demand = mall_kw + ev_demand_estimate
            solar_surplus = max(0.0, solar_kw - total_demand)
            grid_import_needed = max(0.0, total_demand - solar_kw)
            
            # BESS energía disponible (SOC × capacidad máx × eficiencia)
            bess_energy_available = bess_soc * BESS_MAX_KWH_CONST * 0.90  # 90% eficiencia
            
            obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)                    # Solar norm
            obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)                      # Mall demand
            obs[2] = np.clip(bess_soc, 0.0, 1.0)                                   # BESS SOC
            obs[3] = np.clip(bess_energy_available / BESS_MAX_KWH_CONST, 0.0, 1.0) # BESS disponible
            obs[4] = np.clip(solar_surplus / SOLAR_MAX_KW, 0.0, 1.0)               # Solar excedente
            obs[5] = np.clip(grid_import_needed / 500.0, 0.0, 1.0)                 # Grid import
            obs[6] = np.clip((solar_kw - total_demand) / SOLAR_MAX_KW + 0.5, 0.0, 1.0)  # Balance
            obs[7] = np.clip(1.0 - ev_demand_estimate / (self.NUM_CHARGERS * CHARGER_MAX_KW), 0.0, 1.0)  # Capacidad libre

            # ================================================================
            # [8-45] DEMANDA POR SOCKET (38 features)
            # ================================================================
            if self.chargers_hourly.shape[1] >= self.NUM_CHARGERS:
                raw_demands = self.chargers_hourly[h, :self.NUM_CHARGERS]
            else:
                raw_demands = np.zeros(self.NUM_CHARGERS, dtype=np.float32)
                raw_demands[:self.chargers_hourly.shape[1]] = self.chargers_hourly[h]
            
            obs[8:46] = np.clip(raw_demands / CHARGER_MAX_KW, 0.0, 1.0)

            # ================================================================
            # [46-83] POTENCIA ACTUAL POR SOCKET (38 features)
            # ================================================================
            efficiency_factor = 0.7 if 6 <= hour_24 <= 22 else 0.5
            obs[46:84] = obs[8:46] * efficiency_factor

            # ================================================================
            # [84-121] OCUPACIÓN POR SOCKET (38 features)
            # ================================================================
            occupancy = (raw_demands > 0.1).astype(np.float32)
            obs[84:122] = occupancy

            # ================================================================
            # [122-137] ESTADO DE VEHÍCULOS (16 features) - CRÍTICO PARA APRENDIZAJE
            # ================================================================
            motos_sockets = occupancy[:30]  # Primeros 30 sockets = motos
            taxis_sockets = occupancy[30:]  # Últimos 8 sockets = mototaxis
            
            self.motos_charging_now = int(np.sum(motos_sockets))
            self.mototaxis_charging_now = int(np.sum(taxis_sockets))
            
            # Estimar vehículos en cola según hora pico
            if 6 <= hour_24 <= 22:
                self.motos_waiting = max(0, int(270 / 24 - self.motos_charging_now))
                self.mototaxis_waiting = max(0, int(39 / 24 - self.mototaxis_charging_now))
            else:
                self.motos_waiting = 0
                self.mototaxis_waiting = 0
            
            # SOC promedio (basado en potencia entregada)
            motos_power = obs[46:76]
            taxis_power = obs[76:84]
            self.motos_soc_avg = float(np.mean(motos_power)) if self.motos_charging_now > 0 else 0.0
            self.mototaxis_soc_avg = float(np.mean(taxis_power)) if self.mototaxis_charging_now > 0 else 0.0
            
            # Tiempo restante de carga (horas estimadas)
            self.motos_time_remaining = (1.0 - self.motos_soc_avg) * 0.76
            self.mototaxis_time_remaining = (1.0 - self.mototaxis_soc_avg) * 1.2
            
            # Sockets disponibles
            motos_available = 30 - self.motos_charging_now
            taxis_available = 8 - self.mototaxis_charging_now
            
            # Progreso diario (resetea cada 24 horas)
            hour_in_day = h % 24
            if hour_in_day == 0:
                self.motos_charged_today = 0
                self.mototaxis_charged_today = 0
                self.daily_co2_avoided = 0.0
            
            # Estimar vehículos completados
            vehicles_per_hour = max(1, self.motos_charging_now // 2)
            taxis_per_hour = max(0, self.mototaxis_charging_now // 3)
            self.motos_charged_today += vehicles_per_hour
            self.mototaxis_charged_today += taxis_per_hour
            
            # Eficiencia y ratios
            total_ev_power = float(np.sum(raw_demands))
            solar_for_ev_ratio = min(1.0, solar_kw / max(1.0, total_ev_power)) if total_ev_power > 0 else 0.0
            charge_efficiency = float(np.sum(obs[46:84])) / max(1.0, float(np.sum(obs[8:46])))
            
            # CO2 potencial
            co2_potential = (motos_available + taxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS
            
            obs[122] = self.motos_charging_now / 30.0                                # Motos cargando
            obs[123] = self.mototaxis_charging_now / 8.0                             # Mototaxis cargando
            obs[124] = np.clip(self.motos_waiting / 100.0, 0.0, 1.0)                 # Motos en cola
            obs[125] = np.clip(self.mototaxis_waiting / 20.0, 0.0, 1.0)              # Mototaxis en cola
            obs[126] = self.motos_soc_avg                                            # SOC promedio motos
            obs[127] = self.mototaxis_soc_avg                                        # SOC promedio mototaxis
            obs[128] = np.clip(self.motos_time_remaining / 2.0, 0.0, 1.0)            # Tiempo restante motos
            obs[129] = np.clip(self.mototaxis_time_remaining / 2.0, 0.0, 1.0)        # Tiempo restante taxis
            obs[130] = motos_available / 30.0                                        # Sockets motos libres
            obs[131] = taxis_available / 8.0                                         # Sockets taxis libres
            obs[132] = np.clip(self.motos_charged_today / 270.0, 0.0, 1.0)           # Motos cargadas hoy
            obs[133] = np.clip(self.mototaxis_charged_today / 39.0, 0.0, 1.0)        # Taxis cargados hoy
            obs[134] = np.clip(charge_efficiency, 0.0, 1.0)                          # Eficiencia carga
            obs[135] = solar_for_ev_ratio                                            # Ratio solar→EV
            obs[136] = np.clip(self.daily_co2_avoided / 500.0, 0.0, 1.0)             # CO2 evitado hoy
            obs[137] = np.clip(co2_potential / 100.0, 0.0, 1.0)                      # CO2 potencial

            # ================================================================
            # [138-143] TIME FEATURES (6 features)
            # ================================================================
            obs[138] = float(hour_24) / 24.0                                         # Hora
            obs[139] = float(day_of_year % 7) / 7.0                                  # Día semana
            obs[140] = float((day_of_year // 30) % 12) / 12.0                        # Mes
            obs[141] = 1.0 if 6 <= hour_24 <= 22 else 0.0                            # Hora pico
            obs[142] = float(self.context.co2_factor_kg_per_kwh)                     # Factor CO2
            obs[143] = 0.15                                                          # Tarifa

            # ================================================================
            # [144-155] COMUNICACIÓN INTER-SISTEMA (12 features)
            # ================================================================
            bess_can_supply = 1.0 if bess_energy_available > total_ev_power else bess_energy_available / max(1.0, total_ev_power)
            solar_sufficient = 1.0 if solar_kw >= total_ev_power else solar_kw / max(1.0, total_ev_power)
            grid_needed_ratio = grid_import_needed / max(1.0, total_ev_power) if total_ev_power > 0 else 0.0
            priority_motos = self.motos_waiting / max(1, self.motos_waiting + self.mototaxis_waiting) if (self.motos_waiting + self.mototaxis_waiting) > 0 else 0.5
            total_waiting = self.motos_waiting + self.mototaxis_waiting
            total_capacity = motos_available + taxis_available
            urgency = total_waiting / max(1, total_capacity) if total_capacity > 0 else 0.0
            solar_opportunity = solar_surplus / max(1.0, total_ev_power) if total_ev_power > 0 else 1.0
            should_charge_bess = 1.0 if (solar_surplus > 100 and bess_soc < 0.8) else 0.0
            should_discharge_bess = 1.0 if (solar_kw < total_demand * 0.5 and bess_soc > 0.3) else 0.0
            co2_reduction_potential = (motos_available + taxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS / 100.0
            saturation = (self.motos_charging_now + self.mototaxis_charging_now) / self.NUM_CHARGERS
            total_input = solar_kw + bess_energy_available / 10.0
            total_output = total_ev_power
            system_eff = min(1.0, total_output / max(1.0, total_input))
            daily_target = 309  # 270 motos + 39 mototaxis
            daily_progress = (self.motos_charged_today + self.mototaxis_charged_today) / daily_target
            
            obs[144] = np.clip(bess_can_supply, 0.0, 1.0)
            obs[145] = np.clip(solar_sufficient, 0.0, 1.0)
            obs[146] = np.clip(grid_needed_ratio, 0.0, 1.0)
            obs[147] = priority_motos
            obs[148] = np.clip(urgency, 0.0, 1.0)
            obs[149] = np.clip(solar_opportunity, 0.0, 1.0)
            obs[150] = should_charge_bess
            obs[151] = should_discharge_bess
            obs[152] = np.clip(co2_reduction_potential, 0.0, 1.0)
            obs[153] = saturation
            obs[154] = system_eff
            obs[155] = np.clip(daily_progress, 0.0, 1.0)

            return obs

        def render(self) -> None:
            """Render no implementado para este environment."""
            return

        def reset(
            self,
            *,
            seed: int | None = None,
            options: dict[str, Any] | None = None
        ) -> tuple[np.ndarray, dict[str, Any]]:
            del seed, options
            self.step_count = 0
            self.episode_num += 1
            self.episode_reward = 0.0
            self.episode_co2_avoided = 0.0
            self.episode_solar_kwh = 0.0
            self.episode_grid_import = 0.0
            self.episode_ev_satisfied = 0.0
            
            self.co2_avoided_total = 0.0
            self.solar_kwh_total = 0.0
            self.cost_total = 0.0
            self.grid_import_total = 0.0
            
            # [v5.3] RESET ESTADO DE VEHÍCULOS
            self.motos_charging_now = 0
            self.mototaxis_charging_now = 0
            self.motos_waiting = 0
            self.mototaxis_waiting = 0
            self.motos_soc_avg = 0.0
            self.mototaxis_soc_avg = 0.0
            self.motos_time_remaining = 0.0
            self.mototaxis_time_remaining = 0.0
            self.motos_charged_today = 0
            self.mototaxis_charged_today = 0
            self.daily_co2_avoided = 0.0
            
            # [v5.3] RESET COMUNICACIÓN INTER-SISTEMA
            self.bess_available_kwh = 0.0
            self.solar_surplus_kwh = 0.0
            self.current_grid_import = 0.0
            self.system_efficiency = 0.0
            
            # ✅ RESET SOC TRACKERS
            self.episode_motos_10_max = 0.0
            self.episode_motos_20_max = 0.0
            self.episode_motos_30_max = 0.0
            self.episode_motos_50_max = 0.0
            self.episode_motos_70_max = 0.0
            self.episode_motos_80_max = 0.0
            self.episode_motos_100_max = 0.0
            
            self.episode_taxis_10_max = 0.0
            self.episode_taxis_20_max = 0.0
            self.episode_taxis_30_max = 0.0
            self.episode_taxis_50_max = 0.0
            self.episode_taxis_70_max = 0.0
            self.episode_taxis_80_max = 0.0
            self.episode_taxis_100_max = 0.0

            obs = self._make_observation(0)
            return obs, {}

        def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
            """Ejecuta un paso de simulación (1 hora) - MISMA ESTRUCTURA QUE PPO."""
            self.step_count += 1
            h = (self.step_count - 1) % self.HOURS_PER_YEAR

            # DATOS REALES (OE2 timeseries)
            solar_kw = float(self.solar_hourly[h])
            mall_kw = float(self.mall_hourly[h])
            charger_demand = self.chargers_hourly[h].astype(np.float32)
            bess_soc = np.clip(float(self.bess_soc_hourly[h]), 0.0, 1.0)

            # PROCESAR ACCION (39-dim: 1 BESS + 38 sockets)
            bess_action = np.clip(action[0], 0.0, 1.0)
            charger_setpoints = np.clip(action[1:self.ACTION_DIM], 0.0, 1.0)

            # CALCULAR ENERGIA (usando max_power real del 5to dataset OE2)
            charger_power_effective = charger_setpoints * self.charger_max_power[:self.n_chargers]
            ev_charging_kwh = float(np.sum(np.minimum(charger_power_effective, charger_demand)))
            total_demand_kwh = mall_kw + ev_charging_kwh
            
            # BESS power (positivo = descarga, negativo = carga)
            bess_power_kw = (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW
            
            # Separar motos y mototaxis (30 motos + 8 mototaxis = 38 sockets)
            motos_demand = float(np.sum(charger_demand[:30] * charger_setpoints[:30]))
            mototaxis_demand = float(np.sum(charger_demand[30:] * charger_setpoints[30:]))
            motos_charging = int(np.sum(charger_setpoints[:30] > 0.5))
            mototaxis_charging = int(np.sum(charger_setpoints[30:] > 0.5))

            # GRID BALANCE
            net_demand = total_demand_kwh - bess_power_kw
            grid_import_kwh = max(0.0, net_demand - solar_kw)
            grid_export_kwh = max(0.0, solar_kw - net_demand)

            # ===== CO2 CALCULATIONS (MISMO FLUJO QUE SAC) =====
            # Factor CO2 gasolina para motos/mototaxis: ~2.31 kg CO2/litro
            GASOLINA_KG_CO2_PER_LITRO_A2C = 2.31
            MOTO_LITROS_PER_100KM_A2C = 2.0
            MOTOTAXI_LITROS_PER_100KM_A2C = 3.0
            MOTO_KM_PER_KWH_A2C = 50.0
            MOTOTAXI_KM_PER_KWH_A2C = 30.0
            
            # Usar proporción real de sockets motos/mototaxis (30 motos + 8 mototaxis = 38)
            moto_ratio_a2c = 30.0 / 38.0
            mototaxi_ratio_a2c = 8.0 / 38.0
            
            # CO2 DIRECTO: Emisiones evitadas por usar EV en lugar de gasolina (MISMO QUE SAC)
            motos_energy_a2c = ev_charging_kwh * moto_ratio_a2c
            mototaxis_energy_a2c = ev_charging_kwh * mototaxi_ratio_a2c
            
            km_motos_a2c = motos_energy_a2c * MOTO_KM_PER_KWH_A2C
            km_mototaxis_a2c = mototaxis_energy_a2c * MOTOTAXI_KM_PER_KWH_A2C
            
            litros_evitados_motos_a2c = km_motos_a2c * MOTO_LITROS_PER_100KM_A2C / 100.0
            litros_evitados_mototaxis_a2c = km_mototaxis_a2c * MOTOTAXI_LITROS_PER_100KM_A2C / 100.0
            
            co2_avoided_direct_kg = (litros_evitados_motos_a2c + litros_evitados_mototaxis_a2c) * GASOLINA_KG_CO2_PER_LITRO_A2C
            
            # CO2 INDIRECTO: SOLAR + BESS CON PEAK SHAVING (MISMO QUE SAC)
            solar_avoided = min(solar_kw, total_demand_kwh)
            bess_discharge = max(0.0, bess_power_kw)  # Solo contar descarga (positivo)
            
            # Factor peak shaving (IDENTICO A SAC)
            if mall_kw > 2000.0:
                peak_shaving_factor = 1.0 + (mall_kw - 2000.0) / max(1.0, mall_kw) * 0.5
            else:
                peak_shaving_factor = 0.5 + (mall_kw / 2000.0) * 0.5
            
            bess_co2_benefit = bess_discharge * peak_shaving_factor
            co2_avoided_indirect_kg = (solar_avoided + bess_co2_benefit) * CO2_FACTOR_IQUITOS
            co2_avoided_total_kg = co2_avoided_direct_kg + co2_avoided_indirect_kg
            
            # CO2 grid para tracking
            co2_grid_kg = grid_import_kwh * CO2_FACTOR_IQUITOS

            # EV SATISFACTION - MÉTODO REALISTA (similar a SAC)
            # Basado en cuánta carga se está entregando vs la demanda
            if float(np.sum(charger_demand)) > 0.1:
                charge_ratio = ev_charging_kwh / max(1.0, float(np.sum(charger_demand)))
                ev_soc_avg = np.clip(0.80 + 0.20 * charge_ratio, 0.0, 1.0)
            else:
                ev_soc_avg = 0.95
            
            # ✅ SIMULAR CARGA DE VEHÍCULOS POR SOC (SINCRONIZADO CON PPO - habilitado)
            scenario = self.scenarios_by_hour[h]
            
            # v5.6 CORREGIDO: USAR POTENCIA TOTAL DISPONIBLE DEL SISTEMA (IGUAL QUE PPO)
            # No solo la potencia controlada por el agente, sino:
            # Solar + BESS + Red (potencia total para cargar vehículos)
            actual_controlled_power_kw = float(np.sum(charger_power_effective[:self.n_chargers]))
            solar_available_kw = max(0.0, solar_kw - mall_kw)
            bess_available_kw = max(0.0, bess_power_kw) if bess_power_kw > 0 else 0.0
            grid_available_kw = 500.0
            
            # Potencia TOTAL disponible para carga de vehículos
            total_available_power_kw = actual_controlled_power_kw + solar_available_kw + bess_available_kw + grid_available_kw
            available_power_kw = max(50.0, total_available_power_kw)
            
            charging_result = self.vehicle_simulator.simulate_hourly_charge(scenario, available_power_kw)
            
            # Extraer conteos por SOC (valores REALES del simulador)
            motos_10 = charging_result.get('motos_10_percent_charged', 0)
            motos_20 = charging_result.get('motos_20_percent_charged', 0)
            motos_30 = charging_result.get('motos_30_percent_charged', 0)
            motos_50 = charging_result.get('motos_50_percent_charged', 0)
            motos_70 = charging_result.get('motos_70_percent_charged', 0)
            motos_80 = charging_result.get('motos_80_percent_charged', 0)
            motos_100 = charging_result.get('motos_100_percent_charged', 0)
            
            # Extraer conteos de mototaxis (valores REALES del simulador)
            taxis_10 = charging_result.get('mototaxis_10_percent_charged', 0)
            taxis_20 = charging_result.get('mototaxis_20_percent_charged', 0)
            taxis_30 = charging_result.get('mototaxis_30_percent_charged', 0)
            taxis_50 = charging_result.get('mototaxis_50_percent_charged', 0)
            taxis_70 = charging_result.get('mototaxis_70_percent_charged', 0)
            taxis_80 = charging_result.get('mototaxis_80_percent_charged', 0)
            taxis_100 = charging_result.get('mototaxis_100_percent_charged', 0)
            
            # Actualizar máximos del episodio
            self.episode_motos_10_max = max(self.episode_motos_10_max, motos_10)
            self.episode_motos_20_max = max(self.episode_motos_20_max, motos_20)
            self.episode_motos_30_max = max(self.episode_motos_30_max, motos_30)
            self.episode_motos_50_max = max(self.episode_motos_50_max, motos_50)
            self.episode_motos_70_max = max(self.episode_motos_70_max, motos_70)
            self.episode_motos_80_max = max(self.episode_motos_80_max, motos_80)
            self.episode_motos_100_max = max(self.episode_motos_100_max, motos_100)
            
            self.episode_taxis_10_max = max(self.episode_taxis_10_max, taxis_10)
            self.episode_taxis_20_max = max(self.episode_taxis_20_max, taxis_20)
            self.episode_taxis_30_max = max(self.episode_taxis_30_max, taxis_30)
            self.episode_taxis_50_max = max(self.episode_taxis_50_max, taxis_50)
            self.episode_taxis_70_max = max(self.episode_taxis_70_max, taxis_70)
            self.episode_taxis_80_max = max(self.episode_taxis_80_max, taxis_80)
            self.episode_taxis_100_max = max(self.episode_taxis_100_max, taxis_100)

            # CALCULAR RECOMPENSA MULTIOBJETIVO v5.3 (PRIORIZA CARGAR VEHÍCULOS)
            try:
                reward_val, components = self.reward_calculator.compute(
                    grid_import_kwh=grid_import_kwh,
                    grid_export_kwh=grid_export_kwh,
                    solar_generation_kwh=solar_kw,
                    ev_charging_kwh=ev_charging_kwh,
                    ev_soc_avg=ev_soc_avg,
                    bess_soc=bess_soc,
                    hour=h % 24,
                    ev_demand_kwh=self.context.ev_demand_constant_kw
                )
                
                # ================================================================
                # [v5.3] REWARD QUE PRIORIZA CARGAR MÁS VEHÍCULOS
                # ================================================================
                # Total cargando vs capacidad máxima (38 sockets)
                total_vehicles = motos_charging + mototaxis_charging
                vehicles_ratio = total_vehicles / 38.0  # MAX 38
                
                # Componentes de reward v5.3:
                r_vehicles_charging = vehicles_ratio * 0.25        # 25% - Más vehículos cargando
                r_vehicles_100 = (motos_100 + taxis_100) / 309.0 * 0.20  # 20% - Completar al 100%
                r_co2_avoided = np.clip(co2_avoided_total_kg / 50.0, 0.0, 0.10)  # 10% - CO2 evitado
                
                # Penalizar grid import alto (incentiva solar)
                r_grid_penalty = -np.clip(grid_import_kwh / 500.0, 0.0, 0.10)  # -10% max
                
                # Bonus por usar solar para EVs
                ev_demand_total = float(np.sum(charger_demand))
                if ev_demand_total > 0.1:
                    solar_for_ev = min(solar_kw, ev_demand_total) / ev_demand_total
                else:
                    solar_for_ev = 0.0
                r_solar_to_ev = solar_for_ev * 0.10  # 10% - Solar → EV
                
                # Bonus BESS (descargar durante pico, cargar con excedente)
                hour_24 = h % 24
                bess_direction = bess_action - 0.5  # -0.5 → +0.5
                is_peak = 6 <= hour_24 <= 22
                if is_peak and solar_kw < ev_demand_total and bess_direction > 0:
                    r_bess = 0.08  # Bonus: descargar BESS cuando hay déficit solar
                elif not is_peak and solar_kw > ev_demand_total * 1.2 and bess_direction < 0:
                    r_bess = 0.08  # Bonus: cargar BESS con excedente solar
                else:
                    r_bess = 0.0
                
                # Socket efficiency: penalizar sockets activos sin carga
                active_sockets = float(np.sum(charger_setpoints > 0.1))
                sockets_with_demand = float(np.sum(charger_demand > 0.1))
                if active_sockets > 0:
                    socket_efficiency = min(sockets_with_demand, active_sockets) / active_sockets
                else:
                    socket_efficiency = 1.0
                r_socket_eff = socket_efficiency * 0.05  # 5% - Eficiencia socket
                
                # Time penalty: urgencia de completar vehículos antes de fin de día
                hour_norm = hour_24 / 24.0
                daily_target = 309  # 270 motos + 39 mototaxis
                daily_completed = self.motos_charged_today + self.mototaxis_charged_today
                if hour_norm > 0.5:  # Segunda mitad del día
                    progress = daily_completed / daily_target
                    r_time_urgency = 0.02 if progress > hour_norm else -0.02
                else:
                    r_time_urgency = 0.0
                
                # COMBINAR REWARD COMPONENTS
                reward_custom = (
                    r_vehicles_charging +  # 25% - Prioridad #1: Más vehículos cargando
                    r_vehicles_100 +       # 20% - Prioridad #2: Completar cargas
                    r_co2_avoided +        # 10% - CO2 evitado
                    r_grid_penalty +       # -10% max - Penalidad grid
                    r_solar_to_ev +        # 10% - Usar solar para EVs
                    r_bess +               # 8% - Coordinación BESS
                    r_socket_eff +         # 5% - Eficiencia sockets
                    r_time_urgency         # ±2% - Urgencia temporal
                )
                
                # Mezclar con reward original (30% original, 70% custom v5.3)
                reward_val = reward_val * 0.30 + reward_custom * 0.70
                reward_val = float(np.clip(reward_val, -1.0, 1.0))
                
                # Guardar componentes adicionales para logging
                components['r_vehicles_charging'] = float(r_vehicles_charging)
                components['r_vehicles_100'] = float(r_vehicles_100)
                components['r_bess_control'] = float(r_bess)
                components['r_socket_eff'] = float(r_socket_eff)
                components['r_solar_to_ev'] = float(r_solar_to_ev)
                
            except (AttributeError, KeyError, TypeError):
                reward_val = -grid_import_kwh * 0.01 + solar_kw * 0.001
                components = {}

            # TRACKING
            self.episode_reward += float(reward_val)
            self.episode_co2_avoided += co2_avoided_total_kg
            self.episode_solar_kwh += solar_kw
            self.episode_grid_import += grid_import_kwh
            
            self.co2_avoided_total += co2_avoided_total_kg
            self.solar_kwh_total += solar_kw
            self.cost_total += components.get('cost_usd', 0)
            self.grid_import_total += grid_import_kwh

            # OBSERVACIÓN
            obs = self._make_observation(self.step_count)

            done = self.step_count >= self.max_steps
            truncated = False

            # INFO DICT (27 métricas - IGUAL QUE PPO + reward components)
            info: dict[str, Any] = {
                'co2_grid_kg': co2_grid_kg,
                'co2_avoided_indirect_kg': co2_avoided_indirect_kg,
                'co2_avoided_direct_kg': co2_avoided_direct_kg,
                'co2_avoided_total_kg': co2_avoided_total_kg,
                'solar_generation_kwh': solar_kw,
                'ev_charging_kwh': ev_charging_kwh,
                'mall_demand_kw': mall_kw,
                'grid_import_kwh': grid_import_kwh,
                'grid_export_kwh': grid_export_kwh,
                'bess_power_kw': float(bess_power_kw),
                'bess_soc': bess_soc,
                'ev_soc_avg': float(ev_soc_avg),
                'motos_charging': motos_charging,
                'mototaxis_charging': mototaxis_charging,
                'motos_demand_kwh': motos_demand,
                'mototaxis_demand_kwh': mototaxis_demand,
                'hour': h % 24,
                'day': h // 24,
                'step': self.step_count,
                'episode_reward': self.episode_reward,
                'episode_co2_avoided_kg': self.co2_avoided_total,
                'episode_solar_kwh': self.solar_kwh_total,
                # REWARD COMPONENTS (5 métricas adicionales)
                'r_solar': components.get('r_solar', 0.0),
                'r_cost': components.get('r_cost', 0.0),
                'r_ev': components.get('r_ev', 0.0),
                'r_grid': components.get('r_grid', 0.0),
                'r_co2': components.get('r_co2', 0.0),
                # ✅ VEHÍCULOS CARGADOS POR SOC (10%, 20%, 30%, 50%, 70%, 80%, 100%)
                'motos_10_percent': self.episode_motos_10_max,
                'motos_20_percent': self.episode_motos_20_max,
                'motos_30_percent': self.episode_motos_30_max,
                'motos_50_percent': self.episode_motos_50_max,
                'motos_70_percent': self.episode_motos_70_max,
                'motos_80_percent': self.episode_motos_80_max,
                'motos_100_percent': self.episode_motos_100_max,
                'taxis_10_percent': self.episode_taxis_10_max,
                'taxis_20_percent': self.episode_taxis_20_max,
                'taxis_30_percent': self.episode_taxis_30_max,
                'taxis_50_percent': self.episode_taxis_50_max,
                'taxis_70_percent': self.episode_taxis_70_max,
                'taxis_80_percent': self.episode_taxis_80_max,
                'taxis_100_percent': self.episode_taxis_100_max,
            }

            return obs, float(reward_val), done, truncated, info

    # Crear environment con datos cargados - COMPLETO CON MÉTRICAS BESS/EV REALES
    env = CityLearnEnvironment(
        reward_calc=reward_calculator,
        ctx=context,
        solar_kw=solar_hourly,
        chargers_kw=chargers_hourly,
        mall_kw=mall_hourly,
        bess_soc_arr=bess_soc,
        charger_max_power_kw=charger_max_power,
        charger_mean_power_kw=charger_mean_power,
        bess_metrics=bess_data,  # ← NUEVO: métricas BESS completas
        ev_metrics=ev_data,      # ← NUEVO: métricas EV completas
        max_steps=HOURS_PER_YEAR
    )
    print('  OK Environment creado (v5.3 con comunicación completa del sistema)')
    print(f'    - Observation: {env.observation_space.shape} (156-dim: energía + sockets + vehículos + coord)')
    print(f'    - Action: {env.action_space.shape}')
    if bess_data:
        print(f'    - BESS métricas: {list(bess_data.keys())}')
    if ev_data:
        print(f'    - EV métricas: {list(ev_data.keys())}')
    print()

    # ========================================================================
    # PASO 5: CREAR A2C AGENT (USANDO A2CConfig)
    # ========================================================================
    print('[5] CREAR A2C AGENT')
    print('-' * 80)

    a2c_config = A2CConfig.for_gpu() if DEVICE == 'cuda' else A2CConfig.for_cpu()

    a2c_agent = A2C(
        'MlpPolicy',
        env,
        learning_rate=a2c_config.learning_rate,
        n_steps=a2c_config.n_steps,
        gamma=a2c_config.gamma,
        gae_lambda=a2c_config.gae_lambda,
        ent_coef=a2c_config.ent_coef,
        vf_coef=a2c_config.vf_coef,
        max_grad_norm=a2c_config.max_grad_norm,
        rms_prop_eps=a2c_config.rms_prop_eps,
        use_rms_prop=a2c_config.use_rms_prop,
        normalize_advantage=a2c_config.normalize_advantage,
        policy_kwargs=a2c_config.policy_kwargs,
        verbose=0,
        device=DEVICE,
        tensorboard_log=None,
    )

    print(f'  OK A2C agent creado (DEVICE: {DEVICE.upper()})')
    print(f'    - Learning rate: {a2c_config.learning_rate}')
    print(f'    - N steps: {a2c_config.n_steps}')
    print(f'    - Gamma: {a2c_config.gamma}')
    print(f'    - GAE lambda: {a2c_config.gae_lambda}')
    print(f'    - Entropy coef: {a2c_config.ent_coef}')
    print(f'    - Value coef: {a2c_config.vf_coef}')
    print(f'    - Max grad norm: {a2c_config.max_grad_norm}')
    print(f'    - Use RMSProp: {a2c_config.use_rms_prop}')
    print(f'    - Normalize advantage: {a2c_config.normalize_advantage}')
    print()

    # ========================================================================
    # PASO 6: ENTRENAR A2C
    # ========================================================================
    print('[6] ENTRENAR A2C')
    print('-' * 80)

    # ENTRENAMIENTO: 10 episodios completos = 10 × 8,760 timesteps = 87,600 pasos
    # Velocidad GPU RTX 4060 (on-policy A2C): ~650-700 timesteps/segundo
    EPISODES = 10
    TOTAL_TIMESTEPS = EPISODES * 8760  # 87,600 timesteps
    SPEED_ESTIMATED = 650 if DEVICE == 'cuda' else 65  # Real RTX 4060 speed on A2C
    DURATION_MINUTES = TOTAL_TIMESTEPS / SPEED_ESTIMATED / 60

    if DEVICE == 'cuda':
        DURATION_TEXT = f'~{int(DURATION_MINUTES*60)} segundos (GPU RTX 4060)'
    else:
        DURATION_TEXT = f'~{DURATION_MINUTES:.1f} horas (CPU)'

    print()
    print('='*80)
    print('  📊 CONFIGURACION ENTRENAMIENTO A2C (100% DATOS REALES OE2)')
    print(f'     Episodios: {EPISODES} × 8,760 timesteps = {TOTAL_TIMESTEPS:,} pasos')
    print(f'     Device: {DEVICE.upper()}')
    print(f'     Velocidad: ~{SPEED_ESTIMATED:,} timesteps/segundo')
    print(f'     Duración: {DURATION_TEXT}')
    print('     Datos: REALES OE2 (chargers_ev_ano_2024_v3.csv 38 sockets, 940 kWh BESS, 4.05 MWp solar)')
    print('     Network: 256x256 (on-policy A2C), n_steps=8 (updates frecuentes)')
    print('     Output: result_a2c.json, timeseries_a2c.csv, trace_a2c.csv')
    print()
    print('  REWARD WEIGHTS (CO2_FOCUS):')
    print('    CO2 grid (0.35): Minimizar importacion')
    print('    Solar (0.20): Autoconsumo PV')
    print('    EV satisfaction (0.30): SOC 90%')
    print('    Cost (0.10): Minimizar costo')
    print('    Grid stability (0.05): Suavizar picos')
    print('='*80)
    print('  ENTRENAMIENTO EN PROGRESO:')
    print('  ' + '-' * 76)

    start_time = time.time()

    # Callbacks: Checkpoint + DetailedLogging + A2CMetrics
    checkpoint_callback = CheckpointCallback(
        save_freq=2000,
        save_path=str(CHECKPOINT_DIR),
        name_prefix='a2c_model',
        verbose=0
    )
    
    detailed_callback = DetailedLoggingCallback(
        env_ref=env,
        output_dir=OUTPUT_DIR,
        verbose=1,
        total_timesteps=TOTAL_TIMESTEPS
    )
    
    # ✅ NUEVO: A2CMetricsCallback para métricas específicas A2C
    a2c_metrics_callback = A2CMetricsCallback(
        output_dir=OUTPUT_DIR,
        config=a2c_config,
        verbose=1
    )
    
    callback_list = CallbackList([checkpoint_callback, detailed_callback, a2c_metrics_callback])

    a2c_agent.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=callback_list,
        progress_bar=False
    )

    elapsed = time.time() - start_time
    a2c_agent.save(CHECKPOINT_DIR / 'a2c_final_model.zip')

    print()
    print('  ✓ RESULTADO ENTRENAMIENTO:')
    print(f'    Tiempo: {elapsed/60:.1f} minutos ({elapsed:.0f} segundos)')
    print(f'    Timesteps ejecutados: {TOTAL_TIMESTEPS:,}')
    print(f'    Velocidad real: {TOTAL_TIMESTEPS/elapsed:.0f} timesteps/segundo')
    print(f'    Episodios completados: {detailed_callback.episode_count}')

    # ========== GUARDAR 3 ARCHIVOS DE SALIDA ==========
    print()
    print('[6] GUARDAR ARCHIVOS DE SALIDA')
    print('-' * 80)

    # 1. trace_a2c.csv - Registro detallado de cada step
    if detailed_callback.trace_records:
        trace_df = pd.DataFrame(detailed_callback.trace_records)
        trace_path = OUTPUT_DIR / 'trace_a2c.csv'
        trace_df.to_csv(trace_path, index=False)
        print(f'  ✓ trace_a2c.csv: {len(trace_df)} registros → {trace_path}')
    else:
        print('  ⚠ trace_a2c.csv: Sin registros (callback vacío)')

    # 2. timeseries_a2c.csv - Series temporales horarias
    if detailed_callback.timeseries_records:
        ts_df = pd.DataFrame(detailed_callback.timeseries_records)
        ts_path = OUTPUT_DIR / 'timeseries_a2c.csv'
        ts_df.to_csv(ts_path, index=False)
        print(f'  ✓ timeseries_a2c.csv: {len(ts_df)} registros → {ts_path}')
    else:
        print('  ⚠ timeseries_a2c.csv: Sin registros (callback vacío)')

    print()
    print('[7] VALIDACION - 10 EPISODIOS')
    print('-' * 80)

    val_obs, _ = env.reset()
    val_metrics: dict[str, list[float]] = {
        'rewards': [],
        'co2_avoided': [],
        'solar_kwh': [],
        'cost_usd': [],
        'grid_import': [],
    }

    for ep in range(10):
        val_obs, _ = env.reset()
        validation_done = False
        step_count = 0
        episode_co2 = 0.0
        episode_solar = 0.0
        episode_grid = 0.0

        print(f'  Episodio {ep+1}/10: ', end='', flush=True)

        while not validation_done:
            action_result = a2c_agent.predict(val_obs, deterministic=True)
            action_arr = action_result[0] if action_result is not None else np.zeros(129)
            val_obs, reward, terminated, val_truncated, step_info = env.step(action_arr)
            validation_done = terminated or val_truncated
            step_count += 1

            episode_co2 += step_info.get('co2_avoided_total_kg', 0)
            episode_solar += step_info.get('solar_generation_kwh', 0)
            episode_grid += step_info.get('grid_import_kwh', 0)

        val_metrics['rewards'].append(env.episode_reward)
        val_metrics['co2_avoided'].append(episode_co2)
        val_metrics['solar_kwh'].append(episode_solar)
        val_metrics['cost_usd'].append(env.cost_total)
        val_metrics['grid_import'].append(episode_grid)

        print(
            f'Reward={env.episode_reward:>8.2f} | CO2_avoided={episode_co2:>10.1f}kg'
            f' | Solar={episode_solar:>10.1f}kWh | Steps={step_count}'
        )

    print()

    # 3. result_a2c.json - Resumen completo del entrenamiento (IGUAL ESTRUCTURA QUE PPO)
    result_summary: dict[str, Any] = {
        'timestamp': datetime.now().isoformat(),
        'agent': 'A2C',
        'project': 'pvbesscar',
        'location': 'Iquitos, Peru',
        'co2_factor_kg_per_kwh': CO2_FACTOR_IQUITOS,
        'training': {
            'total_timesteps': int(TOTAL_TIMESTEPS),
            'episodes': int(EPISODES),
            'duration_seconds': float(elapsed),
            'speed_steps_per_second': float(TOTAL_TIMESTEPS / elapsed),
            'device': str(DEVICE),
            'episodes_completed': detailed_callback.episode_count,
            'hyperparameters': {
                'learning_rate': a2c_config.learning_rate,
                'n_steps': a2c_config.n_steps,
                'gamma': a2c_config.gamma,
                'gae_lambda': a2c_config.gae_lambda,
                'ent_coef': a2c_config.ent_coef,
                'vf_coef': a2c_config.vf_coef,
                'max_grad_norm': a2c_config.max_grad_norm,
            }
        },
        'datasets_oe2': {
            'chargers_path': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
            'chargers_sockets': 38,
            'chargers_total_kwh': float(env.chargers_total_kwh),
            'bess_path': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv',
            'bess_capacity_kwh': BESS_CAPACITY_KWH,
            'solar_path': 'data/interim/oe2/solar/pv_generation_citylearn_v2.csv',
            'solar_total_kwh': float(np.sum(np.asarray(env.solar_hourly_kwh))),
            'mall_path': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
            'mall_total_kwh': float(np.sum(np.asarray(env.mall_hourly_kw))),
        },
        'validation': {
            'num_episodes': 10,
            'mean_reward': float(np.mean(val_metrics['rewards'])),
            'std_reward': float(np.std(val_metrics['rewards'])),
            'mean_co2_avoided_kg': float(np.mean(val_metrics['co2_avoided'])),
            'mean_solar_kwh': float(np.mean(val_metrics['solar_kwh'])),
            'mean_cost_usd': float(np.mean(val_metrics['cost_usd'])),
            'mean_grid_import_kwh': float(np.mean(val_metrics['grid_import'])),
        },
        'training_evolution': {
            'episode_rewards': detailed_callback.episode_rewards,
            'episode_co2_grid': detailed_callback.episode_co2_grid,
            'episode_co2_avoided_indirect': detailed_callback.episode_co2_avoided_indirect,
            'episode_co2_avoided_direct': detailed_callback.episode_co2_avoided_direct,
            'episode_solar_kwh': detailed_callback.episode_solar_kwh,
            'episode_ev_charging': detailed_callback.episode_ev_charging,
            'episode_grid_import': detailed_callback.episode_grid_import,
            # ✅ NUEVAS métricas de evolución
            'episode_grid_stability': detailed_callback.episode_grid_stability,
            'episode_cost_usd': detailed_callback.episode_cost_usd,
            'episode_motos_charged': detailed_callback.episode_motos_charged,
            'episode_mototaxis_charged': detailed_callback.episode_mototaxis_charged,
            'episode_bess_discharge_kwh': detailed_callback.episode_bess_discharge_kwh,
            'episode_bess_charge_kwh': detailed_callback.episode_bess_charge_kwh,
            'episode_avg_socket_setpoint': detailed_callback.episode_avg_socket_setpoint,
            'episode_socket_utilization': detailed_callback.episode_socket_utilization,
            'episode_bess_action_avg': detailed_callback.episode_bess_action_avg,
        },
        # ✅ NUEVAS secciones de métricas detalladas
        'summary_metrics': {
            'total_co2_avoided_indirect_kg': float(sum(detailed_callback.episode_co2_avoided_indirect)),
            'total_co2_avoided_direct_kg': float(sum(detailed_callback.episode_co2_avoided_direct)),
            'total_co2_avoided_kg': float(sum(detailed_callback.episode_co2_avoided_indirect) + sum(detailed_callback.episode_co2_avoided_direct)),
            'total_cost_usd': float(sum(detailed_callback.episode_cost_usd)),
            'avg_grid_stability': float(np.mean(detailed_callback.episode_grid_stability)) if detailed_callback.episode_grid_stability else 0.0,
            'max_motos_charged': int(max(detailed_callback.episode_motos_charged)) if detailed_callback.episode_motos_charged else 0,
            'max_mototaxis_charged': int(max(detailed_callback.episode_mototaxis_charged)) if detailed_callback.episode_mototaxis_charged else 0,
            'total_bess_discharge_kwh': float(sum(detailed_callback.episode_bess_discharge_kwh)),
            'total_bess_charge_kwh': float(sum(detailed_callback.episode_bess_charge_kwh)),
        },
        'control_progress': {
            'avg_socket_setpoint_evolution': detailed_callback.episode_avg_socket_setpoint,
            'socket_utilization_evolution': detailed_callback.episode_socket_utilization,
            'bess_action_evolution': detailed_callback.episode_bess_action_avg,
            'description': 'Evolución del aprendizaje de control por episodio',
        },
        'reward_components_avg': {
            'r_solar': float(np.mean(detailed_callback.episode_r_solar)) if detailed_callback.episode_r_solar else 0.0,
            'r_cost': float(np.mean(detailed_callback.episode_r_cost)) if detailed_callback.episode_r_cost else 0.0,
            'r_ev': float(np.mean(detailed_callback.episode_r_ev)) if detailed_callback.episode_r_ev else 0.0,
            'r_grid': float(np.mean(detailed_callback.episode_r_grid)) if detailed_callback.episode_r_grid else 0.0,
            'r_co2': float(np.mean(detailed_callback.episode_r_co2)) if detailed_callback.episode_r_co2 else 0.0,
            'episode_r_solar': [float(x) for x in detailed_callback.episode_r_solar] if detailed_callback.episode_r_solar else [],
            'episode_r_cost': [float(x) for x in detailed_callback.episode_r_cost] if detailed_callback.episode_r_cost else [],
            'episode_r_ev': [float(x) for x in detailed_callback.episode_r_ev] if detailed_callback.episode_r_ev else [],
            'episode_r_grid': [float(x) for x in detailed_callback.episode_r_grid] if detailed_callback.episode_r_grid else [],
            'episode_r_co2': [float(x) for x in detailed_callback.episode_r_co2] if detailed_callback.episode_r_co2 else [],
            'description': 'Componentes de reward promedio por episodio',
        },
        'vehicle_charging': {
            'motos_total': 112,
            'mototaxis_total': 16,
            'motos_charged_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_motos_charged] if detailed_callback.episode_motos_charged else [],
            'mototaxis_charged_per_episode': [float(x) if isinstance(x, (np.floating, float)) else int(x) for x in detailed_callback.episode_mototaxis_charged] if detailed_callback.episode_mototaxis_charged else [],
            'description': 'Conteo real de vehículos cargados (setpoint > 50%)',
        },
        'model_path': str(CHECKPOINT_DIR / 'a2c_final_model.zip'),
    }

    # Custom JSON encoder para numpy types
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):  # type: ignore[no-untyped-def]
            if isinstance(obj, (np.floating, np.integer)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    result_path = OUTPUT_DIR / 'result_a2c.json'
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_summary, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
    print(f'  ✓ result_a2c.json: Resumen completo → {result_path}')

    # Extraer métricas para impresión (acceso directo)
    mean_reward = float(np.mean(val_metrics['rewards']))
    mean_co2 = float(np.mean(val_metrics['co2_avoided']))
    mean_solar = float(np.mean(val_metrics['solar_kwh']))
    mean_cost = float(np.mean(val_metrics['cost_usd']))
    mean_grid = float(np.mean(val_metrics['grid_import']))

    print()
    print('='*80)
    print('RESULTADOS FINALES - VALIDACION 10 EPISODIOS:')
    print('='*80)
    print()
    print('  ➤ MÉTRICAS DE RECOMPENSA:')
    print(f'    Reward promedio               {mean_reward:>12.4f} puntos')
    print()
    print('  ➤ REDUCCIÓN CO2 (kg):')
    total_indirect = float(sum(detailed_callback.episode_co2_avoided_indirect))
    total_direct = float(sum(detailed_callback.episode_co2_avoided_direct))
    print(f'    Reducción INDIRECTA (solar)   {total_indirect:>12.1f} kg')
    print(f'    Reducción DIRECTA (EVs)       {total_direct:>12.1f} kg')
    print(f'    Reducción TOTAL               {total_indirect + total_direct:>12.1f} kg')
    print(f'    CO2 evitado promedio/ep       {mean_co2:>12.1f} kg')
    print()
    print('  ➤ VEHÍCULOS CARGADOS (máximo por episodio):')
    max_motos = max(detailed_callback.episode_motos_charged) if detailed_callback.episode_motos_charged else 0
    max_mototaxis = max(detailed_callback.episode_mototaxis_charged) if detailed_callback.episode_mototaxis_charged else 0
    print(f'    Motos (de 112)                {max_motos:>12d} unidades')
    print(f'    Mototaxis (de 16)             {max_mototaxis:>12d} unidades')
    print(f'    Total vehículos               {max_motos + max_mototaxis:>12d} / 38')
    print()
    print('  ➤ ESTABILIDAD DE RED:')
    avg_stability = np.mean(detailed_callback.episode_grid_stability) if detailed_callback.episode_grid_stability else 0.0
    print(f'    Estabilidad promedio          {avg_stability*100:>12.1f} %')
    print(f'    Grid import promedio/ep       {mean_grid:>12.1f} kWh')
    print()
    print('  ➤ AHORRO ECONÓMICO:')
    total_cost = sum(detailed_callback.episode_cost_usd) if detailed_callback.episode_cost_usd else 0.0
    print(f'    Costo total (10 episodios)    ${total_cost:>11.2f} USD')
    print(f'    Costo promedio por episodio   ${mean_cost:>11.2f} USD')
    print()
    print('  ➤ CONTROL BESS:')
    total_discharge = sum(detailed_callback.episode_bess_discharge_kwh) if detailed_callback.episode_bess_discharge_kwh else 0.0
    total_charge = sum(detailed_callback.episode_bess_charge_kwh) if detailed_callback.episode_bess_charge_kwh else 0.0
    avg_bess_action = np.mean(detailed_callback.episode_bess_action_avg) if detailed_callback.episode_bess_action_avg else 0.5
    print(f'    Descarga total BESS           {total_discharge:>12.1f} kWh')
    print(f'    Carga total BESS              {total_charge:>12.1f} kWh')
    print(f'    Acción BESS promedio          {avg_bess_action:>12.3f} (0=carga, 1=descarga)')
    print()
    print('  ➤ PROGRESO DE CONTROL SOCKETS:')
    avg_setpoint = np.mean(detailed_callback.episode_avg_socket_setpoint) if detailed_callback.episode_avg_socket_setpoint else 0.0
    avg_utilization = np.mean(detailed_callback.episode_socket_utilization) if detailed_callback.episode_socket_utilization else 0.0
    print(f'    Setpoint promedio sockets     {avg_setpoint:>12.3f} [0-1]')
    print(f'    Utilización sockets           {avg_utilization*100:>12.1f} %')
    print()
    print('  ➤ SOLAR:')
    print(f'    Solar aprovechada por ep      {mean_solar:>12.1f} kWh')
    print()
    print('  ARCHIVOS GENERADOS:')
    print(f'    ✓ {OUTPUT_DIR}/result_a2c.json')
    print(f'    ✓ {OUTPUT_DIR}/timeseries_a2c.csv')
    print(f'    ✓ {OUTPUT_DIR}/trace_a2c.csv')
    print(f'    ✓ {CHECKPOINT_DIR}/a2c_final_model.zip')
    print()
    print('  ESTADO: Entrenamiento A2C exitoso con datos reales OE2.')
    print()

    print('='*80)
    print('ENTRENAMIENTO A2C COMPLETADO')
    print('='*80)

except (FileNotFoundError, KeyError, ValueError, RuntimeError, OSError, IOError) as e:
    print(f'\n[ERROR] {e}')
    traceback.print_exc()
    sys.exit(1)
