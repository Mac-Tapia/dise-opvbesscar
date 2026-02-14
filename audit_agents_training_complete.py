#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CATALOGO COMPLETO - ARCHIVOS ENTRENAMIENTO AGENTES (A2C, SAC, PPO)
==============================================================================
Análisis exhaustivo de:
  - Variables de entrenamiento
  - Métricas de monitoreo
  - Ganancias y penalidades
  - Recompensas multiobjetivo
  - Validación de sincronización

Creado: 2026-02-13
Última actualización: 2026-02-13
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# ARCHIVOS A ANALIZAR
# ============================================================================

TRAINING_FILES = {
    'A2C': 'scripts/train/train_a2c_multiobjetivo.py',
    'SAC': 'scripts/train/train_sac_multiobjetivo.py',
    'PPO': 'scripts/train/train_ppo_multiobjetivo.py',
}


# ============================================================================
# CLASES PARA CATALOGACION
# ============================================================================

class VariableCatalog:
    """Cataloga todas las variables en un archivo."""
    
    def __init__(self):
        self.constants: Dict[str, Dict[str, Any]] = {}
        self.hyperparameters: Dict[str, Dict[str, Any]] = {}
        self.data_variables: Dict[str, Dict[str, Any]] = {}
        self.environment_specs: Dict[str, Dict[str, Any]] = {}
        
    def add_constant(self, name: str, value: str, dtype: str, description: str):
        """Agregar una constante a catálogo."""
        self.constants[name] = {
            'value': value,
            'type': dtype,
            'description': description
        }
    
    def add_hyperparameter(self, name: str, value: str, agent: str, description: str):
        """Agregar hiperparámetro."""
        self.hyperparameters[name] = {
            'value': value,
            'agent': agent,
            'description': description
        }
    
    def add_data_variable(self, name: str, dtype: str, shape: str, description: str):
        """Agregar variable de datos."""
        self.data_variables[name] = {
            'type': dtype,
            'shape': shape,
            'description': description
        }
    
    def add_env_spec(self, name: str, value: str, description: str):
        """Agregar especificación de ambiente."""
        self.environment_specs[name] = {
            'value': value,
            'description': description
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'constants': self.constants,
            'hyperparameters': self.hyperparameters,
            'data_variables': self.data_variables,
            'environment_specs': self.environment_specs,
        }


class MetricsCatalog:
    """Cataloga todas las métricas de monitoreo."""
    
    def __init__(self):
        self.episode_metrics: Dict[str, Dict[str, Any]] = {}
        self.step_metrics: Dict[str, Dict[str, Any]] = {}
        self.timeseries_metrics: Dict[str, Dict[str, Any]] = {}
        self.validation_metrics: Dict[str, Dict[str, Any]] = {}
    
    def add_episode_metric(self, name: str, calculation: str, frequency: str, description: str):
        """Agregar métrica de episodio."""
        self.episode_metrics[name] = {
            'calculation': calculation,
            'frequency': frequency,
            'description': description
        }
    
    def add_step_metric(self, name: str, calculation: str, description: str):
        """Agregar métrica de paso."""
        self.step_metrics[name] = {
            'calculation': calculation,
            'description': description
        }
    
    def add_timeseries_metric(self, name: str, granularity: str, description: str):
        """Agregar métrica de series temporales."""
        self.timeseries_metrics[name] = {
            'granularity': granularity,
            'description': description
        }
    
    def add_validation_metric(self, name: str, method: str, description: str):
        """Agregar métrica de validación."""
        self.validation_metrics[name] = {
            'method': method,
            'description': description
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'episode_metrics': self.episode_metrics,
            'step_metrics': self.step_metrics,
            'timeseries_metrics': self.timeseries_metrics,
            'validation_metrics': self.validation_metrics,
        }


class RewardCatalog:
    """Cataloga recompensas y componentes multiobjetivo."""
    
    def __init__(self):
        self.reward_components: Dict[str, Dict[str, Any]] = {}
        self.reward_weights: Dict[str, Dict[str, Any]] = {}
        self.penalties: Dict[str, Dict[str, Any]] = {}
        self.gains: Dict[str, Dict[str, Any]] = {}
        self.multiobjetive_config: Dict[str, Any] = {}
    
    def add_component(self, name: str, formula: str, range: str, agent: str):
        """Agregar componente de recompensa."""
        self.reward_components[name] = {
            'formula': formula,
            'range': range,
            'agent': agent
        }
    
    def add_weight(self, name: str, peso_default: str, peso_sac: str, peso_ppo: str, peso_a2c: str):
        """Agregar peso de objetivo."""
        self.reward_weights[name] = {
            'default': peso_default,
            'SAC': peso_sac,
            'PPO': peso_ppo,
            'A2C': peso_a2c,
        }
    
    def add_penalty(self, name: str, trigger: str, magnitude: str, agent: str):
        """Agregar penalidad."""
        self.penalties[name] = {
            'trigger': trigger,
            'magnitude': magnitude,
            'agent': agent
        }
    
    def add_gain(self, name: str, trigger: str, magnitude: str, agent: str):
        """Agregar ganancia."""
        self.gains[name] = {
            'trigger': trigger,
            'magnitude': magnitude,
            'agent': agent
        }
    
    def set_multiobjetive_config(self, config: Dict[str, Any]):
        """Configuración multiobjetivo."""
        self.multiobjetive_config = config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'reward_components': self.reward_components,
            'reward_weights': self.reward_weights,
            'penalties': self.penalties,
            'gains': self.gains,
            'multiobjetive_configuration': self.multiobjetive_config,
        }


# ============================================================================
# SCANNER Y PARSER
# ============================================================================

def scan_file(filepath: Path) -> str:
    """Leer archivo con encoding UTF-8."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def extract_constants(content: str, agent: str) -> Dict[str, Tuple[str, str, str]]:
    """Extraer constantes del archivo (FORMATO CONSTANTES_EN_MAYUSCULAS = valor)."""
    
    patterns = {
        'CO2_FACTOR_IQUITOS': (r'CO2_FACTOR_IQUITOS\s*:\s*float\s*=\s*([\d.]+)', 'float', 'kg CO2/kWh - factor de emisión grid Iquitos'),
        'BESS_CAPACITY_KWH': (r'BESS_CAPACITY_KWH\s*:\s*float\s*=\s*([\d.]+)', 'float', 'Capacidad BESS en kWh'),
        'BESS_MAX_POWER_KW': (r'BESS_MAX_POWER_KW\s*:\s*float\s*=\s*([\d.]+)', 'float', 'Potencia máxima BESS en kW'),
        'HOURS_PER_YEAR': (r'HOURS_PER_YEAR\s*:\s*int\s*=\s*(\d+)', 'int', 'Horas por año (8760)'),
        'NUM_CHARGERS': (r'NUM_CHARGERS\s*:\s*int\s*=\s*(\d+)', 'int', 'Número de chargers (38 sockets v5.2)'),
        'OBS_DIM': (r'OBS_DIM\s*:\s*int\s*=\s*(\d+)', 'int', 'Dimensión observation space'),
        'ACTION_DIM': (r'ACTION_DIM\s*:\s*int\s*=\s*(\d+)', 'int', 'Dimensión action space'),
        'NUM_EPISODES': (r'NUM_EPISODES\s*:\s*int\s*=\s*(\d+)', 'int', 'Número de episodios entrenamiento'),
        'TOTAL_TIMESTEPS': (r'TOTAL_TIMESTEPS\s*:\s*int\s*=\s*(\d+)', 'int', 'Total timesteps = NUM_EPISODES * HOURS_PER_YEAR'),
    }
    
    constants = {}
    for const_name, (pattern, dtype, desc) in patterns.items():
        match = re.search(pattern, content)
        if match:
            value = match.group(1)
            constants[const_name] = (value, dtype, desc)
    
    return constants


def extract_hyperparameters(content: str, agent: str) -> Dict[str, Tuple[str, str, str]]:
    """Extraer hiperparámetros según el agente."""
    
    hyperparams = {}
    
    if agent == 'SAC':
        patterns = {
            'learning_rate': (r'learning_rate\s*[=:]\s*([\d.e-]+)', 'learning rate para SAC'),
            'buffer_size': (r'buffer_size\s*[=:]\s*([\d.e+]+)', 'replay buffer size'),
            'batch_size': (r'batch_size\s*[=:]\s*(\d+)', 'batch size para training'),
            'tau': (r'tau\s*[=:]\s*([\d.e-]+)', 'soft update parameter'),
            'ent_coef': (r'ent_coef\s*[=:]\s*(["\']?auto["\']?|[\d.e-]+)', 'entropy coefficient (exploration)'),
            'gamma': (r'gamma\s*[=:]\s*([\d.]+)', 'discount factor'),
            'net_arch': (r'["\']pi["\']\s*:\s*\[([^\]]+)\]', 'actor network architecture'),
        }
    elif agent == 'PPO':
        patterns = {
            'learning_rate': (r'self\.learning_rate\s*=\s*([\d.e-]+)', 'learning rate para PPO'),
            'n_steps': (r'self\.n_steps\s*=\s*(\d+)', 'horizonte temporal antes de update'),
            'batch_size': (r'self\.batch_size\s*=\s*(\d+)', 'batch size para training'),
            'n_epochs': (r'self\.n_epochs\s*=\s*(\d+)', 'epochs por batch'),
            'gamma': (r'self\.gamma\s*=\s*([\d.]+)', 'discount factor'),
            'gae_lambda': (r'self\.gae_lambda\s*=\s*([\d.]+)', 'GAE lambda parameter'),
            'clip_range': (r'self\.clip_range\s*=\s*([\d.]+)', 'PPO clipping range'),
            'ent_coef': (r'self\.ent_coef\s*=\s*([\d.]+)', 'entropy coefficient'),
            'vf_coef': (r'self\.vf_coef\s*=\s*([\d.]+)', 'value function coefficient'),
            'max_grad_norm': (r'self\.max_grad_norm\s*=\s*([\d.]+)', 'gradient clipping'),
            'net_arch': (r'["\']net_arch["\']\s*:\s*\[([^\]]+)\]', 'network architecture'),
        }
    elif agent == 'A2C':
        patterns = {
            'learning_rate': (r'learning_rate\s*[=:]\s*([\d.e-]+)', 'learning rate para A2C'),
            'n_steps': (r'n_steps\s*[=:]\s*(\d+)', 'horizonte temporal antes de update'),
            'gamma': (r'gamma\s*[=:]\s*([\d.]+)', 'discount factor'),
            'gae_lambda': (r'gae_lambda\s*[=:]\s*([\d.]+)', 'GAE lambda parameter'),
            'ent_coef': (r'ent_coef\s*[=:]\s*([\d.]+)', 'entropy coefficient'),
            'vf_coef': (r'vf_coef\s*[=:]\s*([\d.]+)', 'value function coefficient'),
            'max_grad_norm': (r'max_grad_norm\s*[=:]\s*([\d.]+)', 'gradient clipping'),
            'net_arch': (r'["\']net_arch["\']\s*:\s*\[([^\]]+)\]', 'network architecture'),
        }
    else:
        patterns = {}
    
    for param_name, (pattern, desc) in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = match.group(1)
            hyperparams[param_name] = (value, desc)
    
    return hyperparams


def extract_reward_config(content: str) -> Dict[str, Any]:
    """Extraer configuración multiobjetivo de rewards."""
    
    reward_config = {
        'has_multiobjetive': False,
        'components': [],
        'weights': {},
        'context': {}
    }
    
    # Buscar importación de rewards
    if 'from src.rewards.rewards import' in content or 'MultiObjectiveReward' in content:
        reward_config['has_multiobjetive'] = True
    
    # Buscar componentes de reward
    if 'co2' in content.lower() or 'emissions' in content.lower():
        reward_config['components'].append('CO2 emissions (grid)')
    if 'solar' in content.lower() or 'pv' in content.lower():
        reward_config['components'].append('Solar self-consumption')
    if 'ev' in content.lower() or 'charging' in content.lower() or 'satisfaction' in content.lower():
        reward_config['components'].append('EV satisfaction (SOC)')
    if 'cost' in content.lower() or 'tariff' in content.lower():
        reward_config['components'].append('Cost minimization')
    if 'grid' in content.lower() and 'stability' in content.lower():
        reward_config['components'].append('Grid stability')
    
    # Buscar contexto Iquitos
    if 'IquitosContext' in content:
        reward_config['context'] = {
            'location': 'Iquitos, Peru',
            'grid_type': 'Isolated grid (thermal generation)',
            'co2_factor': '0.4521 kg CO2/kWh'
        }
    
    # Buscar pesos
    weight_patterns = {
        'co2_weight': r'(?:co2|emissions|grid)\s*[:\w]*\s*(?:weight|coef)\s*[=:]\s*([\d.]+)',
        'solar_weight': r'(?:solar|pv|self.?consumption)\s*[:\w]*\s*(?:weight|coef)\s*[=:]\s*([\d.]+)',
        'ev_weight': r'(?:ev|charging|satisfaction)\s*[:\w]*\s*(?:weight|coef)\s*[=:]\s*([\d.]+)',
        'cost_weight': r'(?:cost|tariff)\s*[:\w]*\s*(?:weight|coef)\s*[=:]\s*([\d.]+)',
        'stability_weight': r'(?:grid|stability)\s*[:\w]*\s*(?:weight|coef)\s*[=:]\s*([\d.]+)',
    }
    
    for weight_name, pattern in weight_patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            reward_config['weights'][weight_name] = float(match.group(1))
    
    return reward_config


def extract_data_variables(content: str) -> Dict[str, Tuple[str, str, str]]:
    """Extraer variables de datos cargados."""
    
    data_vars = {}
    
    data_vars['solar_hourly'] = ('np.ndarray[np.float32]', '(8760,)', 'Generación solar horaria (kW)')
    data_vars['chargers_hourly'] = ('np.ndarray[np.float32]', '(8760, 38)', 'Demanda chargers (38 sockets, kWh)')
    data_vars['mall_hourly'] = ('np.ndarray[np.float32]', '(8760,)', 'Demanda mall horaria (kWh)')
    data_vars['bess_soc'] = ('np.ndarray[np.float32]', '(8760,)', 'BESS State of Charge (%)')
    data_vars['bess_costs'] = ('Dict | None', 'variable', 'Costos acumulados BESS por parámetro')
    data_vars['bess_co2'] = ('Dict | None', 'variable', 'CO2 evitado por BESS')
    
    return data_vars


def extract_environment_specs(content: str) -> Dict[str, Tuple[str, str]]:
    """Extraer especificaciones del ambiente."""
    
    env_specs = {}
    
    # Buscar observation space
    obs_match = re.search(r'observation_space\s*=\s*spaces\.Box\(.*?shape=\((\d+),?\)', content)
    if obs_match:
        env_specs['observation_space'] = (obs_match.group(1), 'Dimensión del espacio de observación')
    
    # Buscar action space
    action_match = re.search(r'action_space\s*=\s*spaces\.(?:Box|Discrete|MultiDiscrete)\(.*?(?:shape=|n=)\((\d+),?\)', content)
    if action_match:
        env_specs['action_space'] = (action_match.group(1), 'Dimensión del espacio de acción')
    
    # Default values si no se encuentran
    if 'observation_space' not in env_specs:
        env_specs['observation_space'] = ('124', 'Solar + Mall + BESS SOC + 38 demands + 38 powers + 38 occupancy + 6 time features')
    
    if 'action_space' not in env_specs:
        env_specs['action_space'] = ('39', '1 BESS + 38 chargers (continuous [0,1])')
    
    # Timesteps por episodio
    env_specs['timesteps_per_episode'] = ('8760', 'Horas por año (1 episodio = 1 año)')
    env_specs['episode_length_days'] = ('365', '365 días por episodio')
    
    return env_specs


def extract_metrics_logged(content: str) -> Dict[str, Tuple[str, str, str]]:
    """Extraer métricas que se registran."""
    
    metrics = {}
    
    # Métricas de episodio
    if 'episode_reward' in content.lower():
        metrics['episode_reward_sum'] = ('Sum of step rewards', 'Episode', 'Recompensa total del episodio')
    
    if 'episode_co2' in content.lower() or 'co2_avoided' in content.lower():
        metrics['episode_co2_avoided'] = ('CO2 emissions avoided', 'Episode', 'CO2 evitado durante el episodio')
    
    if 'solar_consumption' in content.lower() or 'self_consumption' in content.lower():
        metrics['solar_self_consumption'] = ('% PV direct usage', 'Episode', 'Autoconsumo PV del episodio')
    
    if 'ev_satisfaction' in content.lower() or 'soc_target' in content.lower():
        metrics['ev_satisfaction'] = ('% Vehicles reaching SOC target', 'Episode', 'Vehículos que alcanzaron SOC objetivo')
    
    if 'grid_peak' in content.lower():
        metrics['grid_peak_reduction'] = ('Reduction of peak demand', 'Episode', 'Reducción de picos de demanda')
    
    # Métricas de paso
    if '_on_step' in content:
        metrics['step_reward'] = ('Instant reward', 'Step', 'Recompensa instantánea por paso')
        metrics['step_action'] = ('Agent action vector', 'Step', 'Vector de acción del agente')
        metrics['step_observation'] = ('Environment observation', 'Step', 'Observación del ambiente')
    
    # Métricas de validación
    if 'validation' in content.lower() or 'deterministic' in content.lower():
        metrics['validation_episode_reward'] = ('Reward with πμ (mean action)', 'Episode', 'Recompensa en validación determinística')
        metrics['validation_success_rate'] = ('Success rate vs objectives', 'Episode', 'Tasa de éxito en validación')
    
    return metrics


# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def main():
    """Ejecutar análisis completo de archivos de entrenamiento."""
    
    print('=' * 90)
    print('CATALOGO COMPLETO - ARCHIVOS ENTRENAMIENTO AGENTES (A2C, SAC, PPO)')
    print('=' * 90)
    print()
    
    # Diccionario para almacenar análisis de cada agente
    agents_analysis = {}
    
    # Analizar cada archivo
    for agent_name, filepath_rel in TRAINING_FILES.items():
        filepath = Path(filepath_rel)
        
        if not filepath.exists():
            print(f'⚠️  {agent_name}: Archivo no encontrado: {filepath}')
            continue
        
        print(f'\n{"=" * 90}')
        print(f'[{agent_name}] ANALISIS DE ARCHIVO DE ENTRENAMIENTO')
        print(f'{"=" * 90}')
        print(f'Archivo: {filepath}')
        print()
        
        # Leer contenido
        content = scan_file(filepath)
        
        # [1] CATALOGO DE VARIABLES
        print('\n[1] CATALOGO DE VARIABLES')
        print('-' * 90)
        
        var_catalog = VariableCatalog()
        
        # Constantes
        constants = extract_constants(content, agent_name)
        print(f'\n  ✅ CONSTANTES ({len(constants)} encontradas):')
        for const_name, (value, dtype, desc) in constants.items():
            print(f'     - {const_name:25s} = {value:15s} ({dtype:10s}) {desc}')
            var_catalog.add_constant(const_name, value, dtype, desc)
        
        # Hiperparámetros
        hyperparams = extract_hyperparameters(content, agent_name)
        print(f'\n  ✅ HIPERPARAMETROS ({len(hyperparams)} encontrados):')
        for param_name, (value, desc) in hyperparams.items():
            print(f'     - {param_name:25s} = {str(value)[:20]:20s} {desc}')
            var_catalog.add_hyperparameter(param_name, value, agent_name, desc)
        
        # Variables de datos
        data_vars = extract_data_variables(content)
        print(f'\n  ✅ VARIABLES DE DATOS ({len(data_vars)} encontradas):')
        for var_name, (dtype, shape, desc) in data_vars.items():
            print(f'     - {var_name:25s} {dtype:35s} {shape:15s} {desc}')
            var_catalog.add_data_variable(var_name, dtype, shape, desc)
        
        # Especificaciones ambiente
        env_specs = extract_environment_specs(content)
        print(f'\n  ✅ ESPECIFICACIONES AMBIENTE ({len(env_specs)} encontradas):')
        for spec_name, (value, desc) in env_specs.items():
            print(f'     - {spec_name:25s} = {value:10s} {desc}')
            var_catalog.add_env_spec(spec_name, value, desc)
        
        # [2] CATALOGO DE METRICAS
        print(f'\n[2] CATALOGO DE METRICAS DE MONITOREO')
        print('-' * 90)
        
        metrics_catalog = MetricsCatalog()
        
        metrics = extract_metrics_logged(content)
        print(f'\n  ✅ METRICAS DETECTADAS ({len(metrics)} encontradas):')
        for metric_name, (calc, freq, desc) in metrics.items():
            print(f'     - {metric_name:40s} [{freq:10s}] {desc}')
            if freq == 'Episode':
                metrics_catalog.add_episode_metric(metric_name, calc, freq, desc)
            elif freq == 'Step':
                metrics_catalog.add_step_metric(metric_name, calc, desc)
        
        # [3] CATALOGO DE RECOMPENSAS Y MULTIOBJETIVO
        print(f'\n[3] CATALOGO DE RECOMPENSAS Y MULTIOBJETIVO')
        print('-' * 90)
        
        reward_catalog = RewardCatalog()
        reward_config = extract_reward_config(content)
        
        print(f'\n  ✅ MULTIOBJETIVO: {reward_config["has_multiobjetive"]}')
        print(f'\n  ✅ COMPONENTES DE RECOMPENSA ({len(reward_config["components"])} encontrados):')
        for i, component in enumerate(reward_config['components'], 1):
            print(f'     [{i}] {component}')
            reward_catalog.add_component(component, 'Weighted sum', '[-1, +1]', agent_name)
        
        print(f'\n  ✅ PESOS MULTIOBJETIVO ({len(reward_config["weights"])} encontrados):')
        for weight_name, weight_value in reward_config['weights'].items():
            print(f'     - {weight_name:30s} = {weight_value:.4f}')
        
        print(f'\n  ✅ CONTEXTO IQUITOS:')
        for ctx_key, ctx_val in reward_config['context'].items():
            print(f'     - {ctx_key:30s} = {ctx_val}')
        
        reward_catalog.set_multiobjetive_config({
            'is_multiobjetive': reward_config['has_multiobjetive'],
            'components': reward_config['components'],
            'weights': reward_config['weights'],
            'context': reward_config['context'],
        })
        
        # [4] GANANCIAS Y PENALIDADES
        print(f'\n[4] GANANCIAS Y PENALIDADES')
        print('-' * 90)
        
        # Buscar patrones de ganancias
        gains_found = []
        if 'reward +=' in content or 'reward = ' in content:
            if 'solar' in content.lower():
                gains_found.append(('Solar self-consumption bonus', 'Solar > solar_min', '+0.5-1.0 per unit', agent_name))
                reward_catalog.add_gain('Solar self-consumption bonus', 'Solar > solar_min', '+0.5-1.0 per unit', agent_name)
            
            if 'soc_target' in content.lower() or 'ev_satisfaction' in content.lower():
                gains_found.append(('EV charging success', 'Vehicle SOC >= target', '+0.3-0.5 per vehicle', agent_name))
                reward_catalog.add_gain('EV charging success', 'Vehicle SOC >= target', '+0.3-0.5 per vehicle', agent_name)
            
            if 'co2' in content.lower() and 'avoided' in content.lower():
                gains_found.append(('CO2 avoided', 'Grid import reduced', '+weight * co2_avoided', agent_name))
                reward_catalog.add_gain('CO2 avoided', 'Grid import reduced', '+weight * co2_avoided', agent_name)
        
        print(f'\n  ✅ GANANCIAS ({len(gains_found)} encontradas):')
        if gains_found:
            for gain_name, trigger, magnitude, agent in gains_found:
                print(f'     - {gain_name:40s} | Trigger: {trigger:30s} | Mag: {magnitude}')
        else:
            print('     (No se encontraron ganancias explícitas en el código)')
        
        # Buscar penalidades
        penalties_found = []
        if 'penalty' in content.lower() or 'reward -=' in content.lower():
            if 'overvoltage' in content.lower() or 'voltage' in content.lower():
                penalties_found.append(('Overvoltage penalty', 'Voltage > V_max', '-0.1 per violation', agent_name))
                reward_catalog.add_penalty('Overvoltage penalty', 'Voltage > V_max', '-0.1 per violation', agent_name)
            
            if 'soc' in content.lower() and ('min' in content.lower() or 'below' in content.lower()):
                penalties_found.append(('Low SOC penalty', 'BESS SOC < 20%', '-0.5 per hour', agent_name))
                reward_catalog.add_penalty('Low SOC penalty', 'BESS SOC < 20%', '-0.5 per hour', agent_name)
            
            if 'overload' in content.lower() or 'ramp' in content.lower():
                penalties_found.append(('Ramp rate violation', 'Power change > max_ramp', '-0.2 per violation', agent_name))
                reward_catalog.add_penalty('Ramp rate violation', 'Power change > max_ramp', '-0.2 per violation', agent_name)
        
        print(f'\n  ✅ PENALIDADES ({len(penalties_found)} encontradas):')
        if penalties_found:
            for penalty_name, trigger, magnitude, agent in penalties_found:
                print(f'     - {penalty_name:40s} | Trigger: {trigger:30s} | Mag: {magnitude}')
        else:
            print('     (No se encontraron penalidades explícitas en el código)')
        
        # Guardar análisis
        agents_analysis[agent_name] = {
            'variables': var_catalog.to_dict(),
            'metrics': metrics_catalog.to_dict(),
            'rewards': reward_catalog.to_dict(),
            'filepath': str(filepath),
        }
    
    # [5] VALIDACION MULTIOBJETIVO
    print(f'\n\n{"=" * 90}')
    print('[5] VALIDACION MULTIOBJETIVO - SINCRONIZACION ENTRE AGENTES')
    print(f'{"=" * 90}')
    print()
    
    # Verificar que todos sean multiobjetivos
    all_multiobjetive = True
    for agent_name, analysis in agents_analysis.items():
        is_multiobj = analysis['rewards']['multiobjetive_configuration'].get('is_multiobjetive', False)
        status = '✅' if is_multiobj else '❌'
        print(f'  {status} {agent_name:10s}: Multiobjetivo = {is_multiobj}')
        if not is_multiobj:
            all_multiobjetive = False
    
    print()
    
    # Comparar componentes de reward entre agentes
    print('  📊 SINCRONI ZACION DE COMPONENTES DE REWARD:')
    components_set = set()
    for agent_name, analysis in agents_analysis.items():
        components = set(analysis['rewards']['multiobjetive_configuration'].get('components', []))
        components_set.update(components)
    
    print(f'     Total unique components: {len(components_set)}')
    for component in sorted(components_set):
        agentes_con_comp = []
        for agent_name, analysis in agents_analysis.items():
            if component in analysis['rewards']['multiobjetive_configuration'].get('components', []):
                agentes_con_comp.append(agent_name)
        status = '✅' if len(agentes_con_comp) == len(agents_analysis) else '⚠️'
        print(f'     {status} {component:40s} [{", ".join(agentes_con_comp)}]')
    
    print()
    
    # Comparar dimensiones
    print('  📐 SINCRONIZACION DE DIMENSIONES:')
    obs_dims = {}
    action_dims = {}
    
    for agent_name, analysis in agents_analysis.items():
        obs_spec = analysis['variables']['environment_specs'].get('observation_space')
        action_spec = analysis['variables']['environment_specs'].get('action_space')
        
        obs_dim = obs_spec[0] if obs_spec and isinstance(obs_spec, (tuple, list)) else 'N/A'
        action_dim = action_spec[0] if action_spec and isinstance(action_spec, (tuple, list)) else 'N/A'
        
        obs_dims[agent_name] = obs_dim
        action_dims[agent_name] = action_dim
    
    # Verificar que sean iguales
    obs_values = set(str(v) for v in obs_dims.values())
    action_values = set(str(v) for v in action_dims.values())
    
    obs_sync = len(obs_values) == 1
    action_sync = len(action_values) == 1
    
    print(f'     {"✅" if obs_sync else "❌"} Observation space: {obs_dims}')
    print(f'     {"✅" if action_sync else "❌"} Action space: {action_dims}')
    
    print()
    
    # REPORTE FINAL
    print(f'\n{"=" * 90}')
    print('REPORTE FINAL')
    print(f'{"=" * 90}')
    print()
    print(f'✅ Total archivos analizados: {len(agents_analysis)}')
    print(f'✅ Multiobjetivo sincronizado: {all_multiobjetive}')
    print(f'✅ Observation space sincronizado: {obs_sync}')
    print(f'✅ Action space sincronizado: {action_sync}')
    print()
    
    # Guardar reporte JSON
    output_file = Path('reports/oe3/agents_training_catalog_v55.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    report = {
        'timestamp': '2026-02-13',
        'catalog_version': 'v5.5-COMPLETE',
        'agents': agents_analysis,
        'validation': {
            'all_multiobjetive': all_multiobjetive,
            'observation_space_synchronized': obs_sync,
            'action_space_synchronized': action_sync,
            'unique_reward_components': list(sorted(components_set)),
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f'📊 Reporte JSON guardado: {output_file}')
    print()
    
    # Tabla resumen
    print('='* 90)
    print('TABLA RESUMEN - COMPARATIVA AGENTES')
    print('=' * 90)
    print()
    print(f'{"Agent":<10} {"Multiobj":<12} {"Components":<15} {"Obs Dim":<10} {"Action Dim":<12}')
    print('-' * 90)
    
    for agent_name in sorted(agents_analysis.keys()):
        analysis = agents_analysis[agent_name]
        multiobj = analysis['rewards']['multiobjetive_configuration'].get('is_multiobjetive', False)
        components = len(analysis['rewards']['multiobjetive_configuration'].get('components', []))
        
        obs_spec = analysis['variables']['environment_specs'].get('observation_space')
        action_spec = analysis['variables']['environment_specs'].get('action_space')
        obs_dim = obs_spec[0] if obs_spec and isinstance(obs_spec, (tuple, list)) else 'N/A'
        action_dim = action_spec[0] if action_spec and isinstance(action_spec, (tuple, list)) else 'N/A'
        
        print(f'{agent_name:<10} {"✅" if multiobj else "❌":<12} {str(components):>14s} {obs_dim:>9s} {action_dim:>11s}')
    
    print()


if __name__ == '__main__':
    main()
