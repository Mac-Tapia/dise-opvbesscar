#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRAPPER DE NORMALIZACION DE REWARDS PARA SAC
Escala rewards a rango [-1, 1] para evitar Q-value explosion
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class RewardNormalizerWrapper(gym.Wrapper):
    """
    Normaliza rewards a un rango controlado para evitar overflow.
    
    Problema: Actor Loss = -146 indica Q-values explosivos
    Causa: Rewards sin normalizar están en rango grande
    Solución: Dividir por factor de escala basado en estadísticas observadas
    """
    
    def __init__(self, env: gym.Env, reward_scale: float = 0.01):
        """
        Args:
            env: Environment a wrappear
            reward_scale: Factor de escala (1.0 = sin cambio, 0.01 = dividir por 100)
        """
        super().__init__(env)
        self.reward_scale = reward_scale
        self.reward_sum = 0.0
        self.reward_count = 0
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.rewards_buffer = []
    
    def step(self, action):
        obs, reward, done, truncated, info = self.env.step(action)
        
        # Acumular para estadísticas
        self.reward_sum += reward
        self.reward_count += 1
        self.rewards_buffer.append(float(reward))
        
        # Guardar reward original en info
        info['reward_original'] = float(reward)
        
        # Aplicar normalización
        normalized_reward = reward * self.reward_scale
        
        # Cada 100 steps, actualizar estadísticas
        if self.reward_count % 100 == 0:
            if len(self.rewards_buffer) > 0:
                self.reward_mean = np.mean(self.rewards_buffer)
                self.reward_std = max(1.0, np.std(self.rewards_buffer))
                self.rewards_buffer = []
        
        info['reward_normalized'] = normalized_reward
        info['reward_scale'] = self.reward_scale
        info['reward_mean_obs'] = self.reward_mean
        info['reward_std_obs'] = self.reward_std
        
        return obs, normalized_reward, done, truncated, info
    
    def reset(self, **kwargs):
        self.reward_sum = 0.0
        self.reward_count = 0
        return self.env.reset(**kwargs)


class ClipRewardWrapper(gym.Wrapper):
    """
    Simplemente clipea rewards a un rango [-1, 1] para SAC.
    Más agresivo que normalizar - directamente limita valores.
    """
    
    def __init__(self, env: gym.Env, min_reward: float = -1.0, max_reward: float = 1.0):
        super().__init__(env)
        self.min_reward = min_reward
        self.max_reward = max_reward
    
    def step(self, action):
        obs, reward, done, truncated, info = self.env.step(action)
        
        info['reward_original'] = float(reward)
        
        # Clipear
        clipped_reward = np.clip(float(reward), self.min_reward, self.max_reward)
        info['reward_clipped'] = clipped_reward
        
        return obs, clipped_reward, done, truncated, info


def apply_reward_wrapper(env: gym.Env, wrapper_type: str = 'normalize', **kwargs) -> gym.Wrapper:
    """
    Aplica wrapper de normalización de rewards.
    
    Args:
        env: Environment
        wrapper_type: 'normalize' o 'clip'
        **kwargs: Argumentos para el wrapper
    
    Returns:
        Environment wrapped
    """
    if wrapper_type == 'normalize':
        reward_scale = kwargs.get('reward_scale', 0.01)
        return RewardNormalizerWrapper(env, reward_scale=reward_scale)
    elif wrapper_type == 'clip':
        min_reward = kwargs.get('min_reward', -1.0)
        max_reward = kwargs.get('max_reward', 1.0)
        return ClipRewardWrapper(env, min_reward=min_reward, max_reward=max_reward)
    else:
        raise ValueError(f"Unknown wrapper type: {wrapper_type}")
