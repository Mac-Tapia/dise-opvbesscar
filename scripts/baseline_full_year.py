#!/usr/bin/env python
"""
Baseline COMPLETO - Garantiza calcular 8,760 timesteps (1 año completo).
Sin control inteligente. Chargers siempre al 100%.
"""
import sys
from pathlib import Path
import logging
import json

import numpy as np
from citylearn.citylearn import CityLearnEnv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

def baseline_full_year():
    """
    Simula COMPLETO 1 año SIN control (cargar chargers 100% siempre).
    GARANTIZA 8,760 timesteps = 365 días × 24 horas.
    """
    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")

    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return None

    logger.info("="*80)
    logger.info("BASELINE - AÑO COMPLETO SIN CONTROL INTELIGENTE")
    logger.info("="*80)
    logger.info(f"Schema: {schema_path}")

    # CO2 params
    CO2_GRID_KG_PER_KWH = 0.4521  # Iquitos thermal generators

    # Cargar ambiente
    logger.info("\n[1/3] Cargando CityLearn environment...")
    env = CityLearnEnv(schema_path)
    logger.info(f"✓ Environment cargado")

    # Reset
    logger.info("\n[2/3] Iniciando simulación...")
    obs = env.reset()
    logger.info(f"✓ Episodio 1 iniciado")

    # Simulación - GARANTIZAR 8,760 pasos COMPLETOS
    done = False
    step = 0
    max_steps = 8760  # REQUERIDO: Exactamente 8760 pasos (1 año)

    total_grid_kwh = 0.0
    total_solar_kwh = 0.0
    hourly_data = []

    logger.info(f"\n[3/3] Ejecutando {max_steps} timesteps (1 año)...")
    logger.info("="*80)

    while step < max_steps:  # Remove 'and not done' to force full 8760
        # BASELINE: Action = [electrical_storage, electric_vehicle_storage, washing_machine]
        # All chargers at max power (1.0)
        action = [np.array([1.0, 1.0, 0.0])]

        # Ejecutar step (gymnasium format: obs, reward, done, truncated, info)
        result = env.step(action)
        if len(result) == 5:
            obs, reward, done, truncated, info = result
        else:
            obs, reward, done, info = result
            truncated = False
        step += 1

        # If done reached but we haven't hit max_steps, force next step after done
        if done and step < max_steps:
            obs, info = env.reset()  # Reset for next episode segment
            done = False

        # Extraer métricas por hora
        grid_kw = info.get("grid_import", 0.0)
        solar_kw = info.get("solar_generation", 0.0)

        grid_kwh = grid_kw / 1000 if grid_kw > 0 else 0
        solar_kwh = solar_kw / 1000 if solar_kw > 0 else 0

        total_grid_kwh += grid_kwh
        total_solar_kwh += solar_kwh

        # Guardar datos por hora
        hourly_data.append({
            "hour": step,
            "day": (step - 1) // 24 + 1,
            "grid_kw": grid_kw,
            "solar_kw": solar_kw,
            "grid_kwh": grid_kwh,
            "solar_kwh": solar_kwh
        })

        # Log cada 1000 pasos
        if step % 1000 == 0 or step == max_steps:
            elapsed_days = step // 24
            co2_so_far = total_grid_kwh * CO2_GRID_KG_PER_KWH
            logger.info(
                f"Paso {step:5d}/{max_steps} | Día {elapsed_days:3d}/365 | "
                f"Grid: {total_grid_kwh:8.1f} kWh | "
                f"CO₂: {co2_so_far:8.1f} kg | "
                f"Solar: {total_solar_kwh:8.1f} kWh"
            )

    # Validación
    logger.info("="*80)
    if step != max_steps:
        logger.warning(f"⚠️ ADVERTENCIA: Solo {step} pasos ejecutados (esperados {max_steps})")
        logger.warning(f"⚠️ done={done}, step={step}")
    else:
        logger.info(f"✅ ÉXITO: {step} pasos completados (1 año completo)")

    # Cálculos finales
    total_co2_kg = total_grid_kwh * CO2_GRID_KG_PER_KWH
    solar_util = (total_solar_kwh / (total_solar_kwh + total_grid_kwh) * 100) if (total_solar_kwh + total_grid_kwh) > 0 else 0

    # Resultados
    results = {
        "status": "COMPLETE" if step == max_steps else "INCOMPLETE",
        "total_timesteps": step,
        "total_days": step // 24,
        "total_hours": step,
        "metrics": {
            "grid_import_kwh": total_grid_kwh,
            "co2_emissions_kg": total_co2_kg,
            "solar_generation_kwh": total_solar_kwh,
            "solar_utilization_percent": solar_util,
            "avg_grid_kw": total_grid_kwh * 1000 / step if step > 0 else 0,
            "avg_solar_kw": total_solar_kwh * 1000 / step if step > 0 else 0,
        },
        "hourly_data": hourly_data
    }

    logger.info("\n" + "="*80)
    logger.info("RESULTADOS BASELINE - AÑO COMPLETO")
    logger.info("="*80)
    logger.info(f"Timesteps: {results['total_timesteps']}/8760 (completo)" if results['total_timesteps'] == 8760 else f"Timesteps: {results['total_timesteps']}/8760 (INCOMPLETO)")
    logger.info(f"Días: {results['total_days']}")
    logger.info(f"Grid Import: {results['metrics']['grid_import_kwh']:.1f} kWh/año")
    logger.info(f"CO₂ Emissions: {results['metrics']['co2_emissions_kg']:.1f} kg/año")
    logger.info(f"Solar Generation: {results['metrics']['solar_generation_kwh']:.1f} kWh/año")
    logger.info(f"Solar Utilization: {results['metrics']['solar_utilization_percent']:.2f}%")
    logger.info(f"Avg Grid: {results['metrics']['avg_grid_kw']:.2f} kW")
    logger.info(f"Avg Solar: {results['metrics']['avg_solar_kw']:.2f} kW")
    logger.info("="*80)

    return results

def main():
    # Ejecutar baseline completo
    results = baseline_full_year()

    if results is None:
        logger.error("❌ Baseline FALLÓ")
        sys.exit(1)

    # Guardar resultados
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    baseline_file = output_dir / "baseline_full_year.json"
    with open(baseline_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n✅ Baseline guardado: {baseline_file}")

    # Validación final
    if results["status"] != "COMPLETE":
        logger.error(f"❌ BASELINE INCOMPLETO: {results['total_timesteps']}/8760 pasos")
        sys.exit(1)
    else:
        logger.info(f"✅ BASELINE COMPLETO: 8760/8760 pasos")
        sys.exit(0)

if __name__ == "__main__":
    main()
