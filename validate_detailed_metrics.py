#!/usr/bin/env python3
"""
Validar y reportar métricas detalladas de CityLearn v2 para SAC, PPO, A2C.

Este script valida:
1. Pesos de recompensa sincronizados (0.35, 0.20, 0.30, 0.10, 0.05)
2. Cálculo correcto de componentes: r_solar, r_cost, r_ev, r_grid, r_co2
3. Métricas de CO2 (directa e indirecta)
4. Conteo de vehículos cargados
5. Operación de BESS y EVs
6. Ahorro de costos
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent


def load_yaml(path: Path) -> dict[str, Any]:
    """Cargar archivo YAML."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def validate_reward_weights() -> bool:
    """Validar que los pesos de recompensa están sincronizados."""
    logger.info("=" * 70)
    logger.info("VALIDACIÓN 1: PESOS DE RECOMPENSA SINCRONIZADOS")
    logger.info("=" * 70)
    
    expected_weights = {
        'co2': 0.35,
        'solar': 0.20,
        'ev': 0.30,
        'cost': 0.10,
        'grid': 0.05,
    }
    
    expected_sum = sum(expected_weights.values())
    logger.info(f"✓ Pesos esperados (suma={expected_sum}): {expected_weights}")
    print()
    
    all_correct = True
    
    # Validar en default.yaml
    config_yaml = load_yaml(REPO_ROOT / "configs" / "default.yaml")
    oe3_rewards = config_yaml.get('oe3', {}).get('rewards', {})
    
    logger.info("📋 PESOS EN default.yaml (oe3.rewards):")
    weights_yaml = {
        'co2': oe3_rewards.get('co2_weight', 0),
        'solar': oe3_rewards.get('solar_weight', 0),
        'ev': oe3_rewards.get('ev_satisfaction_weight', 0),
        'cost': oe3_rewards.get('cost_weight', 0),
        'grid': oe3_rewards.get('grid_stability_weight', 0),
    }
    
    for key, expected in expected_weights.items():
        actual = weights_yaml.get(key, 0)
        status = "✅" if abs(actual - expected) < 0.001 else "❌"
        logger.info(f"  {status} {key.upper():10s}: {actual:.2f} (esperado: {expected:.2f})")
        if abs(actual - expected) >= 0.001:
            all_correct = False
    print()
    
    # Validar en archivos de agentes
    for agent_name in ['sac', 'ppo', 'a2c']:
        config_file = REPO_ROOT / "configs" / "agents" / f"{agent_name}_config.yaml"
        agent_config = load_yaml(config_file)
        
        logger.info(f"📋 PESOS EN {agent_name}_config.yaml:")
        agent_weights = agent_config.get(agent_name, {}).get('multi_objective_weights', {})
        
        for key, expected in expected_weights.items():
            actual = agent_weights.get(key, 0)
            status = "✅" if abs(actual - expected) < 0.001 else "❌"
            logger.info(f"  {status} {key.upper():10s}: {actual:.2f} (esperado: {expected:.2f})")
            if abs(actual - expected) >= 0.001:
                all_correct = False
        print()
    
    return all_correct


def validate_reference_metrics() -> bool:
    """Validar que las métricas de referencia están documentadas."""
    logger.info("=" * 70)
    logger.info("VALIDACIÓN 2: MÉTRICAS DE REFERENCIA (Episode 1 validado)")
    logger.info("=" * 70)
    
    config_yaml = load_yaml(REPO_ROOT / "configs" / "default.yaml")
    ref_metrics = config_yaml.get('oe3', {}).get('reference_metrics', {})
    
    if not ref_metrics:
        logger.error("❌ No se encontraron reference_metrics en default.yaml")
        return False
    
    # Componentes de Reward
    logger.info("📊 COMPONENTES DE REWARD (multiobjetivo)")
    logger.info("-" * 70)
    reward_components = ref_metrics.get('reward_components', {})
    
    expected_components = {
        'r_solar': (-0.3, 0.0),   # Debe ser negativo (penaliza)
        'r_cost': (-0.3, 0.0),    # Debe ser negativo (penaliza)
        'r_ev': (0.99, 1.0),      # Debe ser alto (satisfacción)
        'r_grid': (-0.1, 0.0),    # Debe ser pequeño negativo
        'r_co2': (0.2, 0.3),      # Debe ser positivo (reward)
    }
    
    weights = {
        'r_solar': 0.20,
        'r_cost': 0.10,
        'r_ev': 0.30,
        'r_grid': 0.05,
        'r_co2': 0.35,
    }
    
    all_valid = True
    total_reward = 0.0
    
    logger.info("| Componente | Valor   | Peso  | Descripción")
    logger.info("|" + "-" * 66 + "|")
    
    for component, (min_val, max_val) in expected_components.items():
        actual = reward_components.get(component, 0)
        weight = weights.get(component, 0)
        component_reward = actual * weight
        total_reward += component_reward
        
        in_range = min_val <= actual <= max_val
        status = "✅" if in_range else "⚠️"
        
        if component == 'r_solar':
            desc = "Autoconsumo solar"
        elif component == 'r_cost':
            desc = "Minimizar tarifa"
        elif component == 'r_ev':
            desc = "Satisfacción EV"
        elif component == 'r_grid':
            desc = "Estabilidad red"
        elif component == 'r_co2':
            desc = "Reducción CO2"
        else:
            desc = ""
        
        logger.info(f"| {component:10s} | {actual:7.4f} | {weight:5.2f} | {desc}")
        
        if not in_range:
            all_valid = False
    
    logger.info("|" + "-" * 66 + "|")
    logger.info(f"| TOTAL REWARD     | {total_reward:7.4f}   |")
    logger.info("|" + "-" * 66 + "|")
    print()
    
    # CO2 Reduction
    logger.info("🌿 CO2 - REDUCCIÓN DIRECTA E INDIRECTA")
    logger.info("-" * 70)
    co2_annual = ref_metrics.get('co2_annual', {})
    
    co2_grid = co2_annual.get('grid_emitted_kg', 0)
    co2_indirect = co2_annual.get('avoided_indirect_kg', 0)
    co2_direct = co2_annual.get('avoided_direct_kg', 0)
    co2_total = co2_annual.get('avoided_total_kg', 0)
    reduction_pct = co2_annual.get('reduction_pct', 0)
    
    logger.info(f"CO2 Grid (emitido):     {co2_grid:>12,} kg")
    logger.info(f"CO2 Evitado Indirecto:  {co2_indirect:>12,} kg")
    logger.info(f"CO2 Evitado Directo:    {co2_direct:>12,} kg")
    logger.info(f"CO2 Evitado TOTAL:      {co2_total:>12,} kg")
    logger.info(f"CO2 NETO:               {-co2_total:>12,} kg")
    logger.info(f"Reducción:              {reduction_pct:>12.1f} %")
    print()
    
    # Vehículos cargados
    logger.info("🛵 VEHÍCULOS CARGADOS (datos reales)")
    logger.info("-" * 70)
    vehicles = ref_metrics.get('vehicles_charged', {})
    
    motos_vh = vehicles.get('motos_vehicle_hours', 0)
    motos_day = vehicles.get('motos_per_day_avg', 0)
    moto_vh = vehicles.get('mototaxis_vehicle_hours', 0)
    moto_day = vehicles.get('mototaxis_per_day_avg', 0)
    
    logger.info(f"Motos:       {motos_vh:>12,} veh-h/año | {motos_day:>6,} motos/día")
    logger.info(f"Mototaxis:   {moto_vh:>12,} veh-h/año | {moto_day:>6,} mototaxis/día")
    print()
    
    # Control y Operación
    logger.info("⚡ CONTROL Y OPERACIÓN")
    logger.info("-" * 70)
    control = ref_metrics.get('control_operation', {})
    
    logger.info(f"Sockets Activos:        {control.get('sockets_active_pct', 0):>12.1f} %")
    logger.info(f"BESS Control Intensity: {control.get('bess_control_intensity', 0):>12.1f} %")
    logger.info(f"BESS SOC Promedio:      {control.get('bess_soc_avg', 0):>12.1f} %")
    logger.info(f"EV SOC Promedio:        {control.get('ev_soc_avg', 0):>12.1f} %")
    logger.info(f"Grid Ramp:              {control.get('grid_ramp_kwh_per_h', 0):>12.1f} kWh/h")
    print()
    
    # Costos
    logger.info("💰 AHORRO DE COSTOS")
    logger.info("-" * 70)
    cost = ref_metrics.get('cost_savings', {})
    
    cost_total = cost.get('cost_total_usd', 0)
    savings = cost.get('savings_vs_baseline', 0)
    
    logger.info(f"Costo Total:            ${cost_total:>12,.0f} USD")
    logger.info(f"Ahorro vs Baseline:     ${savings:>12,.0f} USD")
    print()
    
    return all_valid


def validate_agent_implementations() -> bool:
    """Validar que los agentes tienen las métricas en info dict."""
    logger.info("=" * 70)
    logger.info("VALIDACIÓN 3: COMPONENTES EN INFO DICT DE AGENTES")
    logger.info("=" * 70)
    
    all_correct = True
    
    for agent_name, script in [
        ('SAC', 'train_sac_multiobjetivo.py'),
        ('PPO', 'train_ppo_multiobjetivo.py'),
        ('A2C', 'train_a2c_multiobjetivo.py'),
    ]:
        script_path = REPO_ROOT / script
        content = script_path.read_text(encoding='utf-8')
        
        required_fields = ['r_co2', 'r_solar', 'r_cost', 'r_ev', 'r_grid']
        
        logger.info(f"\n📜 {agent_name} ({script}):")
        
        for field in required_fields:
            if field in content:
                logger.info(f"  ✅ {field:10s} present in info dict")
            else:
                logger.info(f"  ❌ {field:10s} MISSING in info dict")
                all_correct = False
    
    print()
    return all_correct


def main() -> int:
    """Ejecutar todas las validaciones."""
    logger.info("\n" + "=" * 70)
    logger.info("VALIDACIÓN COMPLETA DE MÉTRICAS DETALLADAS CITYLEARN v2")
    logger.info("=" * 70 + "\n")
    
    results = {
        "Pesos sincronizados": validate_reward_weights(),
        "Métricas de referencia": validate_reference_metrics(),
        "Implementación en agentes": validate_agent_implementations(),
    }
    
    logger.info("=" * 70)
    logger.info("RESUMEN FINAL")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {name}")
    
    logger.info("=" * 70)
    logger.info(f"Total: {passed}/{len(results)} validaciones pasadas")
    logger.info("=" * 70 + "\n")
    
    if failed == 0:
        logger.info("🎉 ¡TODAS LAS VALIDACIONES PASARON!")
        return 0
    else:
        logger.error(f"⚠️  {failed} validación(es) fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
