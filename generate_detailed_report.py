#!/usr/bin/env python3
"""
Generar reporte detallado de métricas de CityLearn v2 desde logs de entrenamiento.

Genera un reporte en el formato solicitado:
- Componentes de reward (multiobjetivo)
- CO2 (reducción directa e indirecta)
- Vehículos cargados
- Control y operación
- Ahorro de costos
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
import statistics as stats

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def load_episode_data(log_path: Path) -> list[dict[str, Any]]:
    """Cargar datos de episodios desde archivo JSON de logs."""
    if not log_path.exists():
        return []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def generate_detailed_metrics_report(
    episodes: list[dict[str, Any]],
    agent_name: str = "SAC",
    episode_num: int = 1
) -> None:
    """Generar reporte detallado de métricas para un episodio."""
    
    if len(episodes) < episode_num:
        logger.warning(f"No hay {episode_num} episodios en los datos")
        return
    
    ep_data = episodes[episode_num - 1]
    
    # Extraer datos de steps del episodio
    steps = ep_data.get('steps', [])
    
    if not steps:
        logger.warning(f"Episodio {episode_num} no tiene datos de steps")
        return
    
    # Calcular promedios de componentes de reward
    r_solar_vals = [s.get('r_solar', 0) for s in steps if 'r_solar' in s]
    r_cost_vals = [s.get('r_cost', 0) for s in steps if 'r_cost' in s]
    r_ev_vals = [s.get('r_ev', 0) for s in steps if 'r_ev' in s]
    r_grid_vals = [s.get('r_grid', 0) for s in steps if 'r_grid' in s]
    r_co2_vals = [s.get('r_co2', 0) for s in steps if 'r_co2' in s]
    
    r_solar = stats.mean(r_solar_vals) if r_solar_vals else 0.0
    r_cost = stats.mean(r_cost_vals) if r_cost_vals else 0.0
    r_ev = stats.mean(r_ev_vals) if r_ev_vals else 0.0
    r_grid = stats.mean(r_grid_vals) if r_grid_vals else 0.0
    r_co2 = stats.mean(r_co2_vals) if r_co2_vals else 0.0
    
    # Calcular totales
    co2_grid = sum(s.get('co2_grid_kg', 0) for s in steps)
    co2_indirect = sum(s.get('co2_avoided_indirect_kg', 0) for s in steps)
    co2_direct = sum(s.get('co2_avoided_direct_kg', 0) for s in steps)
    co2_total = co2_indirect + co2_direct
    
    solar_gen = sum(s.get('solar_generation_kwh', 0) for s in steps)
    ev_charge = sum(s.get('ev_charging_kwh', 0) for s in steps)
    grid_import = sum(s.get('grid_import_kwh', 0) for s in steps)
    
    # Vehículos
    motos_max = max((s.get('motos_charging_count', 0) for s in steps), default=0)
    moto_max = max((s.get('mototaxis_charging_count', 0) for s in steps), default=0)
    
    # BESS
    bess_discharge = sum(s.get('bess_discharge_kwh', 0) for s in steps)
    bess_charge = sum(s.get('bess_charge_kwh', 0) for s in steps)
    
    # Promedios de control
    sockets_active = stats.mean(
        [s.get('sockets_active_pct', 0) for s in steps]
    ) if steps else 0
    bess_intensity = stats.mean(
        [s.get('bess_control_intensity', 0) for s in steps]
    ) if steps else 0
    bess_soc = stats.mean(
        [s.get('bess_soc', 0) for s in steps]
    ) if steps else 0
    ev_soc = stats.mean(
        [s.get('ev_soc_avg', 0) for s in steps]
    ) if steps else 0
    
    # Imprimir reporte
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"MÉTRICAS DETALLADAS CITYLEARN v2 - EPISODIO {episode_num} [{agent_name}]")
    logger.info("=" * 80)
    logger.info("")
    
    # Componentes de reward
    logger.info("📊 COMPONENTES DE REWARD (multiobjetivo)")
    logger.info("-" * 80)
    logger.info("Componente    Valor    Peso   Descripción")
    logger.info("-" * 80)
    
    weights = {
        'r_solar': 0.20,
        'r_cost': 0.10,
        'r_ev': 0.30,
        'r_grid': 0.05,
        'r_co2': 0.35,
    }
    
    descriptions = {
        'r_solar': 'Autoconsumo solar',
        'r_cost': 'Minimizar tarifa',
        'r_ev': 'Satisfacción carga EV',
        'r_grid': 'Estabilidad de red',
        'r_co2': 'Reducción CO2',
    }
    
    total_reward = 0.0
    for component, value in [
        ('r_solar', r_solar),
        ('r_cost', r_cost),
        ('r_ev', r_ev),
        ('r_grid', r_grid),
        ('r_co2', r_co2),
    ]:
        weight = weights[component]
        contrib = value * weight
        total_reward += contrib
        logger.info(
            f"{component:12s} {value:8.4f} {weight:5.2f}   "
            f"{descriptions[component]}"
        )
    
    logger.info("-" * 80)
    logger.info(f"{'TOTAL':12s} {total_reward:8.4f}")
    logger.info("")
    
    # CO2
    logger.info("🌿 CO2 - REDUCCIÓN DIRECTA E INDIRECTA")
    logger.info("-" * 80)
    
    reduction_pct = (co2_total / (co2_total + co2_grid) * 100) if (co2_total + co2_grid) > 0 else 0
    net_co2 = -co2_total  # Negativo = reducción
    
    logger.info(f"CO2 Grid (emitido)          {co2_grid:>15,.0f} kg")
    logger.info(f"CO2 Evitado Indirecto       {co2_indirect:>15,.0f} kg")
    logger.info(f"CO2 Evitado Directo         {co2_direct:>15,.0f} kg")
    logger.info(f"CO2 Evitado TOTAL           {co2_total:>15,.0f} kg")
    logger.info(f"CO2 NETO                    {net_co2:>15,.0f} kg")
    logger.info(f"Reducción                   {reduction_pct:>15.1f} %")
    logger.info("")
    
    # Vehículos
    logger.info("🛵 VEHÍCULOS CARGADOS (datos reales)")
    logger.info("-" * 80)
    logger.info(f"Motos cargadas máximo       {motos_max:>15} vehicles")
    logger.info(f"Mototaxis cargadas máximo   {moto_max:>15} vehicles")
    logger.info("")
    
    # Control
    logger.info("⚡ CONTROL Y OPERACIÓN")
    logger.info("-" * 80)
    logger.info(f"Sockets Activos             {sockets_active:>15.1f} %")
    logger.info(f"BESS Control Intensity      {bess_intensity*100:>15.1f} %")
    logger.info(f"BESS SOC Promedio           {bess_soc*100:>15.1f} %")
    logger.info(f"EV SOC Promedio             {ev_soc*100:>15.1f} %")
    logger.info(f"Solar Generado              {solar_gen:>15,.0f} kWh")
    logger.info(f"EV Cargado                  {ev_charge:>15,.0f} kWh")
    logger.info(f"Grid Import                 {grid_import:>15,.0f} kWh")
    logger.info(f"BESS Descarga               {bess_discharge:>15,.0f} kWh")
    logger.info(f"BESS Carga                  {bess_charge:>15,.0f} kWh")
    logger.info("")
    
    # Costos (estimación)
    cost_total = grid_import * 0.15  # $0.15/kWh
    baseline_no_solar = (ev_charge + 9202.4 * 365) * 0.20  # Baseline sin solar
    savings = max(0, baseline_no_solar - cost_total)
    
    logger.info("💰 AHORRO DE COSTOS")
    logger.info("-" * 80)
    logger.info(f"Costo Total                 ${cost_total:>14,.0f} USD")
    logger.info(f"Ahorro vs Baseline          ${savings:>14,.0f} USD")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")


def main() -> int:
    """Generar reportes de métricas para agentes disponibles."""
    repo_root = Path(__file__).parent
    
    logger.info("=" * 80)
    logger.info("GENERADOR DE REPORTES - MÉTRICAS DETALLADAS CITYLEARN v2")
    logger.info("=" * 80)
    logger.info("")
    
    # Buscar archivos de logs de todos los agentes
    agents = ['sac', 'ppo', 'a2c']
    
    for agent in agents:
        # Buscar archivo de logs más reciente para este agente
        outputs_dir = repo_root / "outputs"
        
        if not outputs_dir.exists():
            logger.warning(f"No se encontró directorio {outputs_dir}")
            continue
        
        # Buscar archivos JSON de logs del agente
        log_files = list(outputs_dir.glob(f"{agent}_training_*.json"))
        
        if not log_files:
            logger.info(f"No hay logs de {agent.upper()} disponibles (aún no se ha entrenado)")
            continue
        
        # Usar el archivo más reciente
        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Cargando logs de {agent.upper()}: {latest_log.name}")
        
        try:
            episodes = load_episode_data(latest_log)
            
            if episodes:
                # Mostrar reporte del primer episodio
                generate_detailed_metrics_report(episodes, agent.upper(), 1)
            else:
                logger.warning(f"No hay datos de episodios en {latest_log.name}")
        
        except Exception as e:
            logger.error(f"Error procesando {latest_log.name}: {e}")
    
    logger.info("✅ Generación de reportes completada")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
