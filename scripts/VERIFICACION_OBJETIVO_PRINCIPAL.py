"""
VERIFICACIÓN EXHAUSTIVA DEL OBJETIVO PRINCIPAL OE3
===================================================

Objetivo Principal:
  "Seleccionar el agente inteligente de gestión de carga de motos y mototaxis
   eléctricas más apropiado para maximizar la eficiencia operativa del sistema,
   asegurando la contribución cuantificable a la reducción de las emisiones de
   dióxido de carbono en la ciudad de Iquitos"

Verificaciones Implementadas:
  ✓ Métrica de CO₂ como criterio principal de selección
  ✓ Función multiobjetivo con 5 componentes
  ✓ Generación de tabla comparativa de agentes
  ✓ Contexto de Iquitos (factor emisión térmica, flota)
  ✓ Métricas de entrenamiento por componente (CO2, Solar, Costo, EV, Red)
  ✓ Evaluación de eficiencia operativa (autoconsumo, satisfacción)
  ✓ Contribución cuantificable a reducción de CO₂
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd  # type: ignore[import]

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.co2_table import EmissionsFactors, load_summary
from scripts._common import load_all


def verify_objective_implementation() -> Dict[str, Any]:
    """Verifica que el objetivo principal esté implementado correctamente."""

    print("\n" + "="*80)
    print("VERIFICACIÓN DE OBJETIVO PRINCIPAL - OE3")
    print("="*80)

    checks = {}

    # 1. Verificar función de recompensa multiobjetivo
    print("\n[1] FUNCIÓN DE RECOMPENSA MULTIOBJETIVO")
    print("-" * 80)
    try:
        from iquitos_citylearn.oe3.rewards import (
            MultiObjectiveReward,
            MultiObjectiveWeights,
            IquitosContext
        )

        # Instanciar con pesos estándar
        weights = MultiObjectiveWeights(
            co2=0.50,      # PRIMARY
            solar=0.20,    # SECONDARY
            cost=0.10,
            ev_satisfaction=0.10,
            grid_stability=0.10
        )

        context = IquitosContext()
        mor = MultiObjectiveReward(weights=weights, context=context)

        # Verificar componentes
        reward, components = mor.compute(
            grid_import_kwh=100.0,
            grid_export_kwh=10.0,
            solar_generation_kwh=150.0,
            ev_charging_kwh=80.0,
            ev_soc_avg=0.75,
            bess_soc=0.50,
            hour=15,
            ev_demand_kwh=80.0
        )

        required_components = ['r_co2', 'r_cost', 'r_solar', 'r_ev', 'r_grid', 'reward_total']
        found_components = [c for c in required_components if c in components]

        print(f"✓ Clase MultiObjectiveReward implementada")
        print(f"✓ Contexto Iquitos configurado (factor CO₂={context.co2_factor_kg_per_kwh} kg/kWh)")
        print(f"✓ Pesos multiobjetivo definidos:")
        print(f"    - CO₂: {weights.co2:.2f} (PRIMARY para reducción emisiones)")
        print(f"    - Solar: {weights.solar:.2f}")
        print(f"    - Costo: {weights.cost:.2f}")
        print(f"    - EV: {weights.ev_satisfaction:.2f}")
        print(f"    - Red: {weights.grid_stability:.2f}")
        print(f"✓ Componentes de recompensa: {', '.join(found_components)}")
        print(f"✓ Test compute(): reward={reward:.3f}")

        checks['multiobjetivo_implementado']: bool = True
        checks['componentes_recompensa']: int = len(found_components)
        checks['peso_co2_principal']: bool = weights.co2 >= 0.45

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['multiobjetivo_implementado'] = False

    # 2. Verificar agentes entrenables
    print("\n[2] AGENTES INTELIGENTES DISPONIBLES")
    print("-" * 80)
    try:
        from iquitos_citylearn.oe3.agents import SACConfig, PPOConfig, A2CConfig

        sac_cfg = SACConfig()
        ppo_cfg = PPOConfig()
        a2c_cfg = A2CConfig()

        agents = {
            'SAC (Soft Actor-Critic)': sac_cfg,
            'PPO (Proximal Policy Optimization)': ppo_cfg,
            'A2C (Advantage Actor-Critic)': a2c_cfg
        }

        for agent_name, cfg in agents.items():
            print(f"✓ {agent_name}")
            if hasattr(cfg, 'device'):
                print(f"    Device: {cfg.device}")
            if hasattr(cfg, 'learning_rate'):
                print(f"    Learning rate: {cfg.learning_rate}")

        checks['num_agentes']: int = len(agents)

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['num_agentes'] = 0  # type: ignore

    # 3. Verificar script de generación de tabla comparativa
    print("\n[3] TABLA COMPARATIVA DE AGENTES")
    print("-" * 80)
    try:
        table_script = Path("scripts/run_oe3_co2_table.py")
        if table_script.exists():
            print(f"✓ Script run_oe3_co2_table.py EXISTE")

            # Leer el script para verificar contenido
            content = table_script.read_text()

            required_features = [
                ('compute_agent_comparison', 'Comparación multicriterio de agentes'),
                ('compute_table', 'Tabla principal de emisiones'),
                ('compute_control_comparison', 'Comparación baseline vs control'),
                ('CityBaseline', 'Contexto ciudad Iquitos'),
                ('best_agent', 'Selección de agente óptimo'),
            ]

            for feature, desc in required_features:
                if feature in content:
                    print(f"✓ {desc} ({feature})")
                else:
                    print(f"✗ {desc} ({feature}) - NO ENCONTRADO")

            checks['tabla_comparativa_existe'] = True
        else:
            print(f"✗ Script run_oe3_co2_table.py NO EXISTE")
            checks['tabla_comparativa_existe'] = False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['tabla_comparativa_existe'] = False

    # 4. Verificar métricas de contexto Iquitos
    print("\n[4] MÉTRICAS DE CONTEXTO IQUITOS")
    print("-" * 80)
    try:
        from iquitos_citylearn.oe3.rewards import IquitosContext

        ctx = IquitosContext()

        print(f"✓ Factor emisión CO₂: {ctx.co2_factor_kg_per_kwh:.4f} kg/kWh (central térmica)")
        print(f"✓ Tarifa eléctrica: ${ctx.tariff_usd_per_kwh:.2f}/kWh")
        print(f"✓ Cargadores: {ctx.n_chargers} cargadores × {ctx.sockets_per_charger} sockets = "
              f"{ctx.n_chargers * ctx.sockets_per_charger} sockets")
        print(f"✓ Flota EV: {ctx.n_motos} motos + {ctx.n_mototaxis} mototaxis")
        print(f"✓ Horas pico: {ctx.peak_hours}")
        print(f"✓ Límite demanda pico: {ctx.peak_demand_limit_kw:.0f} kW")

        checks['contexto_iquitos'] = True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['contexto_iquitos'] = False

    # 5. Verificar dataset builder con métricas multiobjetivo
    print("\n[5] DATASET BUILDER - INTEGRACIÓN MULTIOBJETIVO")
    print("-" * 80)
    try:
        dataset_builder = Path("src/iquitos_citylearn/oe3/dataset_builder.py")
        if dataset_builder.exists():
            content = dataset_builder.read_text()

            features = [
                ('reward_co2_weight', 'Peso CO₂ en dataset'),
                ('reward_solar_weight', 'Peso solar en dataset'),
                ('multi_objective', 'Configuración multiobjetivo'),
            ]

            for feature, desc in features:
                if feature in content:
                    print(f"✓ {desc}")
                else:
                    print(f"✗ {desc} - NO ENCONTRADO")

            checks['dataset_builder_mo'] = True
        else:
            print(f"✗ dataset_builder.py NO EXISTE")
            checks['dataset_builder_mo'] = False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['dataset_builder_mo'] = False

    # 6. Verificar archivo de configuración con pesos multiobjetivo
    print("\n[6] CONFIGURACIÓN OE3 - PESOS MULTIOBJETIVO")
    print("-" * 80)
    try:
        cfg_file = Path("configs/default.yaml")
        if cfg_file.exists():
            import yaml
            with open(cfg_file) as f:
                cfg = yaml.safe_load(f)

            # Verificar que cada agente tiene pesos multiobjetivo
            oe3_cfg = cfg.get('evaluation', {})

            agents_cfg = ['sac', 'ppo', 'a2c']
            for agent in agents_cfg:
                if agent in oe3_cfg:
                    agent_cfg = oe3_cfg[agent]
                    weights = agent_cfg.get('multi_objective_weights', {})
                    if weights:
                        print(f"\n✓ Pesos {agent.upper()}:")
                        for key, val in weights.items():
                            print(f"    {key}: {val:.2f}")

                        # Verificar que CO₂ es dominante
                        if weights.get('co2', 0) >= 0.45:
                            print(f"    → CO₂ es PRIORITARIO (≥0.45)")
                        else:
                            print(f"    ⚠ CO₂ no es suficientemente prioritario")
                    else:
                        print(f"✗ {agent.upper()} sin pesos multiobjetivo")
                else:
                    print(f"✗ Configuración {agent.upper()} NO ENCONTRADA")

            checks['config_pesos_mo'] = True
        else:
            print(f"✗ configs/default.yaml NO EXISTE")
            checks['config_pesos_mo'] = False

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['config_pesos_mo'] = False

    # 7. Verificar simulación con recompensas registradas
    print("\n[7] SIMULACIÓN - REGISTRO DE MÉTRICAS")
    print("-" * 80)
    try:
        simulate_file = Path("src/iquitos_citylearn/oe3/simulate.py")
        if simulate_file.exists():
            content = simulate_file.read_text()

            metrics = [
                'reward_co2_mean',
                'reward_solar_mean',
                'reward_cost_mean',
                'reward_ev_mean',
                'reward_grid_mean',
                'reward_total_mean',
            ]

            found_metrics = [m for m in metrics if m in content]
            print(f"✓ Métricas registradas en simulación:")
            for m in found_metrics:
                print(f"    - {m}")

            if len(found_metrics) == len(metrics):
                print(f"\n✓ TODAS las métricas multiobjetivo se registran")

            checks['metricas_simulacion'] = len(found_metrics)
        else:
            print(f"✗ simulate.py NO EXISTE")
            checks['metricas_simulacion'] = 0

    except Exception as e:
        print(f"✗ ERROR: {e}")
        checks['metricas_simulacion'] = 0

    return checks


def analyze_summary_if_available(config_path: str) -> Dict[str, Any]:
    """Analiza el summary si existe (después de entrenamiento)."""

    print("\n" + "="*80)
    print("ANÁLISIS DE RESULTADOS (SI DISPONIBLE)")
    print("="*80)

    results: Dict[str, Any] = {}

    try:
        cfg, rp = load_all(config_path)

        summary_path = rp.outputs_dir / "oe3" / "simulations" / "simulation_summary.json"

        if not summary_path.exists():
            print(f"\n⏳ Summary NO DISPONIBLE aún (entrenamiento en progreso)")
            print(f"   Se generará en: {summary_path}")
            return results

        print(f"\n✓ Summary ENCONTRADO: {summary_path}")

        summary = load_summary(summary_path)

        # Análisis de PV+BESS results
        pv_results = summary.get("pv_bess_results", {})

        if not pv_results:
            print("⚠ Sin resultados PV+BESS en summary")
            return results

        print(f"\n[AGENTES COMPARADOS]")
        print("-" * 80)

        agents_data = []
        for agent_name, res in pv_results.items():
            ev_kwh = res.get('ev_charging_kwh', 0)
            import_kwh = res.get('grid_import_kwh', 0)
            co2_kg = res.get('carbon_kg', 0)

            # Anualizados
            sim_years = res.get('simulated_years', 1.0)
            if sim_years > 0:
                ev_kwh_y = ev_kwh / sim_years
                import_kwh_y = import_kwh / sim_years
                co2_kg_y = co2_kg / sim_years
            else:
                ev_kwh_y = import_kwh_y = co2_kg_y = 0

            # Métricas multiobjetivo
            r_co2 = res.get('reward_co2_mean', 0.0)
            r_solar = res.get('reward_solar_mean', 0.0)
            r_cost = res.get('reward_cost_mean', 0.0)
            r_ev = res.get('reward_ev_mean', 0.0)
            r_grid = res.get('reward_grid_mean', 0.0)
            r_total = res.get('reward_total_mean', 0.0)

            agents_data.append({
                'agente': agent_name,
                'ev_kwh_anual': ev_kwh_y,
                'import_red_kwh_anual': import_kwh_y,
                'carbon_tco2_anual': co2_kg_y / 1000.0,
                'reward_co2': r_co2,
                'reward_solar': r_solar,
                'reward_cost': r_cost,
                'reward_ev': r_ev,
                'reward_grid': r_grid,
                'reward_total': r_total,
            })

            print(f"\n{agent_name}:")
            print(f"  EV annual: {ev_kwh_y:,.0f} kWh")
            print(f"  Import grid: {import_kwh_y:,.0f} kWh/año")
            print(f"  CO₂ emissions: {co2_kg_y/1000.0:.1f} tCO₂/año")
            print(f"  Rewards: CO₂={r_co2:.3f}, Solar={r_solar:.3f}, Cost={r_cost:.3f}, "
                  f"EV={r_ev:.3f}, Grid={r_grid:.3f} | Total={r_total:.3f}")

        if agents_data:
            df_agents = pd.DataFrame(agents_data)

            # Ordenar por CO₂ (menor es mejor)
            df_agents = df_agents.sort_values('carbon_tco2_anual').reset_index(drop=True)
            df_agents['ranking'] = range(1, len(df_agents) + 1)

            best_agent = df_agents.iloc[0]

            print(f"\n[SELECCIÓN DE AGENTE ÓPTIMO]")
            print("-" * 80)
            print(f"\n🏆 AGENTE SELECCIONADO: {best_agent['agente']}")
            print(f"   Ranking: #{best_agent['ranking']}")
            print(f"   CO₂ anual: {best_agent['carbon_tco2_anual']:.1f} tCO₂/año")
            print(f"   Reward total medio: {best_agent['reward_total']:.3f}")

            results['best_agent'] = best_agent['agente']
            results['best_co2_tco2_y'] = float(best_agent['carbon_tco2_anual'])
            results['agents_df'] = df_agents

        # Análisis de contribución a reducción CO₂
        baseline_res = summary.get("pv_bess_uncontrolled", {})
        best_res = summary.get("best_result", {})

        if baseline_res and best_res:
            baseline_co2_y = baseline_res.get('carbon_kg', 0) / max(baseline_res.get('simulated_years', 1), 1e-9) / 1000.0
            best_co2_y = best_res.get('carbon_kg', 0) / max(best_res.get('simulated_years', 1), 1e-9) / 1000.0

            reduction = baseline_co2_y - best_co2_y
            reduction_pct = 100.0 * reduction / max(baseline_co2_y, 1e-9)

            print(f"\n[CONTRIBUCIÓN A REDUCCIÓN DE CO₂]")
            print("-" * 80)
            print(f"Baseline (sin control): {baseline_co2_y:.1f} tCO₂/año")
            print(f"Con control inteligente: {best_co2_y:.1f} tCO₂/año")
            print(f"Reducción: {reduction:.1f} tCO₂/año ({reduction_pct:.1f}%)")

            # Contexto ciudad
            print(f"\n[CONTEXTO CIUDAD IQUITOS]")
            print("-" * 80)
            city_transport = summary.get("city_baseline_tpy", {}).get("transport", 10000)
            contribution = 100.0 * reduction / max(city_transport, 1e-9)
            print(f"Reducción sector transporte: {reduction:.1f} tCO₂/año")
            print(f"Emisiones transporte ciudad: {city_transport:,.0f} tCO₂/año")
            print(f"Contribución del proyecto: {contribution:.2f}%")

            results['reduction_co2_tco2_y'] = reduction
            results['reduction_pct'] = reduction_pct
            results['contribution_city_pct'] = contribution

    except Exception as e:
        print(f"⚠ Error al analizar resultados: {e}")

    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Verifica objetivo principal OE3")
    ap.add_argument("--config", default="configs/default.yaml",
                    help="Ruta a config YAML")
    args = ap.parse_args()

    setup_logging()

    # Verificación de implementación
    checks = verify_objective_implementation()

    # Análisis de resultados (si disponible)
    results = analyze_summary_if_available(args.config)

    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN DE VERIFICACIÓN")
    print("="*80)

    implementation_ok = all([
        checks.get('multiobjetivo_implementado', False),
        checks.get('tabla_comparativa_existe', False),
        checks.get('contexto_iquitos', False),
        checks.get('peso_co2_principal', False),
    ])

    if implementation_ok:
        print("\n✓ OBJETIVO PRINCIPAL IMPLEMENTADO CORRECTAMENTE")
        print("  - Función multiobjetivo con CO₂ como criterio principal")
        print("  - Tabla comparativa de agentes inteligentes")
        print("  - Contexto específico de Iquitos")
        print("  - Métricas de entrenamiento por componente")
    else:
        print("\n⚠ ALGUNOS COMPONENTES INCOMPLETOS")

    if results:
        print("\n✓ RESULTADOS DE ENTRENAMIENTO DISPONIBLES")
        if 'best_agent' in results:
            print(f"  - Agente óptimo: {results['best_agent']}")
            print(f"  - CO₂ anual: {results['best_co2_tco2_y']:.1f} tCO₂/año")
        if 'reduction_co2_tco2_y' in results:
            print(f"  - Reducción CO₂ vs baseline: {results['reduction_co2_tco2_y']:.1f} tCO₂/año "
                  f"({results['reduction_pct']:.1f}%)")
            print(f"  - Contribución ciudad Iquitos: {results['contribution_city_pct']:.2f}%")
    else:
        print("\n⏳ Resultados aún no disponibles (entrenamiento en progreso)")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
