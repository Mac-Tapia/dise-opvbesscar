"""
Test corrección: Usar índice [0] en lugar de [-1] para building attributes.
"""
from __future__ import annotations

import logging
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    from citylearn.citylearn import CityLearnEnv

    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")

    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return

    logger.info(f"Cargando environment desde {schema_path}")
    env = CityLearnEnv(str(schema_path))

    b = env.buildings[0]

    # Reset environment
    obs = env.reset()
    logger.info(f"Reset completo: {len(env.buildings)} buildings, obs shape={len(obs)}")
    logger.info(f"Observation[0] shape: {len(obs[0])} (building 0 observations)")
    logger.info(f"Action space: {env.action_space}")

    # Determinar shape de acción correcta
    if hasattr(env.action_space[0], 'shape'):
        action_shape = env.action_space[0].shape[0]
    else:
        action_shape = 1

    logger.info(f"Action shape por building: {action_shape}")

    # Ejecutar 500 pasos y verificar ev_demand_kw
    logger.info("\n🔍 TEST: Verificar ev_demand_kw con índice [0] vs [-1]\n")

    ev_demand_values_idx0 = []
    ev_demand_values_idx_neg1 = []

    for step in range(500):
        # Acción dummy (lista de listas: N buildings × M dims cada uno)
        action = [[0.5] * action_shape]
        net_elec = b.net_electricity_consumption
        non_shift = b.non_shiftable_load

        if isinstance(net_elec, (list, tuple, np.ndarray)) and len(net_elec) > 0:
            total_old = float(net_elec[-1]) if net_elec[-1] is not None else 0.0
        else:
            total_old = 0.0

        if isinstance(non_shift, (list, tuple, np.ndarray)) and len(non_shift) > 0:
            mall_old = float(non_shift[-1]) if non_shift[-1] is not None else 0.0
        else:
            mall_old = 0.0

        ev_demand_old = max(0.0, total_old - mall_old)
        ev_demand_values_idx_neg1.append(ev_demand_old)

        # NUEVO MÉTODO ([0]): Acceso más reciente - CORRECTO
        if isinstance(net_elec, (list, tuple, np.ndarray)) and len(net_elec) > 0:
            total_new = float(net_elec[0]) if net_elec[0] is not None else 0.0
        else:
            total_new = 0.0

        if isinstance(non_shift, (list, tuple, np.ndarray)) and len(non_shift) > 0:
            mall_new = float(non_shift[0]) if non_shift[0] is not None else 0.0
        else:
            mall_new = 0.0

        ev_demand_new = max(0.0, total_new - mall_new)
        ev_demand_values_idx0.append(ev_demand_new)

        if step < 5:
            logger.info(f"Step {step:3d}: OLD ([-1]): total={total_old:.1f}, mall={mall_old:.1f}, ev={ev_demand_old:.1f} | NEW ([0]): total={total_new:.1f}, mall={mall_new:.1f}, ev={ev_demand_new:.1f}")

    # Estadísticas
    logger.info(f"\n{'='*80}")
    logger.info("RESULTADOS: Comparación [-1] vs [0]")
    logger.info(f"{'='*80}")

    logger.info("\nMÉTODO ANTIGUO ([-1] - HISTÓRICO):")
    logger.info(f"  Valores no-cero: {sum(1 for v in ev_demand_values_idx_neg1 if v > 0)}")
    logger.info(f"  Valores cero:    {sum(1 for v in ev_demand_values_idx_neg1 if v == 0)}")
    logger.info(f"  Promedio:        {sum(ev_demand_values_idx_neg1)/len(ev_demand_values_idx_neg1):.2f} kW")

    logger.info("\nMÉTODO NUEVO ([0] - MÁS RECIENTE):")
    logger.info(f"  Valores no-cero: {sum(1 for v in ev_demand_values_idx0 if v > 0)}")
    logger.info(f"  Valores cero:    {sum(1 for v in ev_demand_values_idx0 if v == 0)}")
    logger.info(f"  Promedio:        {sum(ev_demand_values_idx0)/len(ev_demand_values_idx0):.2f} kW")

    if sum(ev_demand_values_idx0) > 0:
        logger.info("\n✅ CORRECCIÓN EXITOSA: Usar índice [0] resuelve el problema!")
        logger.info("   ev_demand_kw ahora tiene valores no-cero")
    else:
        logger.error("\n❌ CORRECCIÓN FALLIDA: Ambos métodos devuelven 0")
        logger.error("   Investigar estructura de datos más profundamente")

if __name__ == "__main__":
    main()
