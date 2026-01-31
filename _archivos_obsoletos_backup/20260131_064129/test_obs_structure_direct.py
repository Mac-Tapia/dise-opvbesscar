"""
Verificar la estructura de observaciones de CityLearn y calcular ev_demand_kw.

Propósito:
- Debuggear por qué co2_direct_kg=0.0 y motos/mototaxis=0
- Confirmar que ev_demand_kw se está calculando correctamente
"""
from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    from citylearn.citylearn import CityLearnEnv

    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")

    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return

    logger.info(f"Cargando CityLearn environment desde {schema_path}")
    env = CityLearnEnv(str(schema_path))

    logger.info(f"Buildings: {len(env.buildings)}")

    if len(env.buildings) == 0:
        logger.error("❌ No buildings found!")
        return

    b = env.buildings[0]
    logger.info(f"\n{'='*80}")
    logger.info(f"Building: {b.name}")
    logger.info(f"{'='*80}")

    # Inspeccion de atributos del building
    logger.info("\nInspeccionando atributos disponibles...")

    # net_electricity_consumption
    if hasattr(b, 'net_electricity_consumption'):
        net_elec = b.net_electricity_consumption
        logger.info(f"  net_electricity_consumption type: {type(net_elec)}")
        if hasattr(net_elec, '__len__'):
            logger.info(f"  net_electricity_consumption length: {len(net_elec)}")
            if len(net_elec) > 0:
                logger.info(f"  net_electricity_consumption[-1]: {net_elec[-1]}")
        else:
            logger.info(f"  net_electricity_consumption value: {net_elec}")

    # non_shiftable_load
    if hasattr(b, 'non_shiftable_load'):
        non_shift = b.non_shiftable_load
        logger.info(f"  non_shiftable_load type: {type(non_shift)}")
        if hasattr(non_shift, '__len__'):
            logger.info(f"  non_shiftable_load length: {len(non_shift)}")
            if len(non_shift) > 0:
                logger.info(f"  non_shiftable_load[-1]: {non_shift[-1]}")
        else:
            logger.info(f"  non_shiftable_load value: {non_shift}")

    # electric_vehicle_chargers
    if hasattr(b, 'electric_vehicle_chargers'):
        chargers = b.electric_vehicle_chargers
        logger.info(f"  electric_vehicle_chargers type: {type(chargers)}")
        if isinstance(chargers, list):
            logger.info(f"  electric_vehicle_chargers length: {len(chargers)}")
            if len(chargers) > 0:
                c = chargers[0]
                logger.info(f"  charger[0] type: {type(c)}")
                logger.info(f"  charger[0] attributes: {dir(c)[:10]}")

    logger.info(f"\n{'='*80}")

    # Reset environment
    obs = env.reset()
    logger.info(f"Observation reset shape: {len(obs)} buildings")
    logger.info(f"Observation[0] shape: {len(obs[0])} dims")

    # Ejecutar 500 pasos y loggear ev_demand_kw
    logger.info("\nEjecutando 500 pasos para verificar ev_demand_kw...")

    ev_demand_values = []

    for step in range(500):
        # Acción dummy (lista de listas: 1 building × 126 chargers)
        action = [[0.5] * 126]
        # Calcular ev_demand_kw usando la fórmula del código
        net_elec = b.net_electricity_consumption
        if isinstance(net_elec, (list, tuple)) and len(net_elec) > 0:
            total_building_demand_kw = float(net_elec[-1]) if net_elec[-1] is not None else 0.0
        else:
            total_building_demand_kw = 0.0

        non_shift = b.non_shiftable_load
        if isinstance(non_shift, (list, tuple)) and len(non_shift) > 0:
            mall_demand_kw = float(non_shift[-1]) if non_shift[-1] is not None else 0.0
        else:
            mall_demand_kw = 0.0

        ev_demand_kw = max(0.0, total_building_demand_kw - mall_demand_kw)

        ev_demand_values.append(ev_demand_kw)

        if step < 10 or step % 100 == 0:
            logger.info(f"Step {step:3d}: total={total_building_demand_kw:.1f} kW, mall={mall_demand_kw:.1f} kW, ev_demand={ev_demand_kw:.1f} kW")

    # Estadísticas
    logger.info(f"\n{'='*80}")
    logger.info("ESTADÍSTICAS DE ev_demand_kw (primeros 500 pasos)")
    logger.info(f"{'='*80}")
    logger.info(f"  Valores no-cero: {sum(1 for v in ev_demand_values if v > 0)}")
    logger.info(f"  Valores cero:    {sum(1 for v in ev_demand_values if v == 0)}")
    logger.info(f"  Mínimo:          {min(ev_demand_values):.2f} kW")
    logger.info(f"  Máximo:          {max(ev_demand_values):.2f} kW")
    logger.info(f"  Promedio:        {sum(ev_demand_values)/len(ev_demand_values):.2f} kW")

    if sum(ev_demand_values) == 0:
        logger.error("\n❌ PROBLEMA: ev_demand_kw siempre es 0!")
        logger.error("Esto explica por qué co2_direct_kg=0.0 y motos=0")
    else:
        logger.info("\n✅ ev_demand_kw tiene valores no-cero - el cálculo está funcionando")

if __name__ == "__main__":
    main()
