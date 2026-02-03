#!/usr/bin/env python
"""
COMPARACIÓN: SAC vs PPO vs A2C contra IQUITOS_BASELINE

Genera tabla de comparación de reducción CO₂ para los 3 agentes RL
usando IQUITOS_BASELINE como referencia (valores reales de Iquitos).

Estado: ✅ CREADO 2026-02-03
Uso: python scripts/compare_agents_vs_baseline.py
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from iquitos_citylearn.oe3.simulate import IQUITOS_BASELINE
except ImportError:
    print("❌ ERROR: Cannot import IQUITOS_BASELINE from simulate.py")
    print("   Make sure to run: python scripts/validate_iquitos_baseline.py first")
    sys.exit(1)


@dataclass
class AgentMetrics:
    """Métricas de un agente RL."""
    name: str
    co2_emitido_kg: float
    co2_reduccion_indirecta_kg: float
    co2_reduccion_directa_kg: float
    co2_neto_kg: float
    solar_utilization_pct: float
    grid_independence_ratio: float

    # Calculados vs baseline
    reduction_direct_pct_vs_baseline: Optional[float] = None
    reduction_indirect_pct_vs_baseline: Optional[float] = None
    reduction_total_pct_vs_baseline: Optional[float] = None

    def calculate_percentages(self) -> None:
        """Calcula porcentajes vs baseline."""
        # Convertir de kg a tCO₂ (dividir por 1000)
        direct_tco2 = self.co2_reduccion_directa_kg / 1000.0
        indirect_tco2 = self.co2_reduccion_indirecta_kg / 1000.0
        total_tco2 = direct_tco2 + indirect_tco2

        # Calcular porcentajes
        baseline_direct = IQUITOS_BASELINE.reduction_direct_max_tco2_year
        baseline_indirect = IQUITOS_BASELINE.reduction_indirect_max_tco2_year
        baseline_total = IQUITOS_BASELINE.reduction_total_max_tco2_year

        self.reduction_direct_pct_vs_baseline = (direct_tco2 / baseline_direct * 100) if baseline_direct > 0 else 0.0
        self.reduction_indirect_pct_vs_baseline = (indirect_tco2 / baseline_indirect * 100) if baseline_indirect > 0 else 0.0
        self.reduction_total_pct_vs_baseline = (total_tco2 / baseline_total * 100) if baseline_total > 0 else 0.0


def load_agent_result(agent_name: str) -> Optional[AgentMetrics]:
    """Carga resultado_json de un agente."""
    result_file = PROJECT_ROOT / "outputs" / "oe3_simulations" / f"result_{agent_name}.json"

    if not result_file.exists():
        print(f"⚠️  No encontrado: {result_file}")
        return None

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        env_metrics = data.get("environmental_metrics", {})

        metrics = AgentMetrics(
            name=agent_name.upper(),
            co2_emitido_kg=float(env_metrics.get("co2_emitido_grid_kg", 0.0)),
            co2_reduccion_indirecta_kg=float(env_metrics.get("co2_reduccion_indirecta_kg", 0.0)),
            co2_reduccion_directa_kg=float(env_metrics.get("co2_reduccion_directa_kg", 0.0)),
            co2_neto_kg=float(env_metrics.get("co2_neto_kg", 0.0)),
            solar_utilization_pct=float(env_metrics.get("solar_utilization_pct", 0.0)),
            grid_independence_ratio=float(env_metrics.get("grid_independence_ratio", 0.0)),
        )

        # Calcular porcentajes si no están en el JSON
        if "reduction_direct_pct_vs_baseline" not in env_metrics:
            metrics.calculate_percentages()
        else:
            metrics.reduction_direct_pct_vs_baseline = float(env_metrics.get("reduction_direct_pct_vs_baseline", 0.0))
            metrics.reduction_indirect_pct_vs_baseline = float(env_metrics.get("reduction_indirect_pct_vs_baseline", 0.0))
            metrics.reduction_total_pct_vs_baseline = float(env_metrics.get("reduction_total_pct_vs_baseline", 0.0))

        return metrics

    except Exception as e:
        print(f"❌ Error leyendo {result_file}: {e}")
        return None


def print_comparison_table(agents: Dict[str, AgentMetrics]) -> None:
    """Imprime tabla de comparación."""
    print("\n" + "="*120)
    print("COMPARACIÓN: CO₂ REDUCTION vs IQUITOS BASELINE (3,328 EVs)")
    print("="*120 + "\n")

    # Encabezados
    print(f"{'MÉTRICA':<30} | {'SAC':^20} | {'PPO':^20} | {'A2C':^20} | {'BASELINE':^15}")
    print("-" * 120)

    # CO₂ Emitido (Grid)
    baseline_emission_tco2 = 5710.257  # ~290,000 tCO₂/año / 50 kW
    sac_emis = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).co2_emitido_kg / 1000
    ppo_emis = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).co2_emitido_kg / 1000
    a2c_emis = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).co2_emitido_kg / 1000
    print(f"{'CO₂ Emitido (tCO₂/año)':<30} | {sac_emis:>19.0f} | {ppo_emis:>19.0f} | {a2c_emis:>19.0f} | {baseline_emission_tco2:>14.0f}")

    # Reducción Indirecta (Solar + BESS)
    print(f"\n{'REDUCCIÓN INDIRECTA (Solar + BESS):':<30}")
    sac_indir = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).co2_reduccion_indirecta_kg / 1000
    ppo_indir = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).co2_reduccion_indirecta_kg / 1000
    a2c_indir = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).co2_reduccion_indirecta_kg / 1000
    sac_indir_pct = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).reduction_indirect_pct_vs_baseline or 0.0
    ppo_indir_pct = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).reduction_indirect_pct_vs_baseline or 0.0
    a2c_indir_pct = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).reduction_indirect_pct_vs_baseline or 0.0
    baseline_indir = IQUITOS_BASELINE.reduction_indirect_max_tco2_year

    print(f"{'  CO₂ Reducido (tCO₂)':<30} | {sac_indir:>19.0f} | {ppo_indir:>19.0f} | {a2c_indir:>19.0f} | {baseline_indir:>14.0f}")
    print(f"{'  % vs Baseline':<30} | {sac_indir_pct:>18.1f}% | {ppo_indir_pct:>18.1f}% | {a2c_indir_pct:>18.1f}% | {'100%':>14}")

    # Reducción Directa (EV)
    print(f"\n{'REDUCCIÓN DIRECTA (EV vs Gasoline):':<30}")
    sac_direct = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).co2_reduccion_directa_kg / 1000
    ppo_direct = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).co2_reduccion_directa_kg / 1000
    a2c_direct = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).co2_reduccion_directa_kg / 1000
    sac_direct_pct = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).reduction_direct_pct_vs_baseline or 0.0
    ppo_direct_pct = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).reduction_direct_pct_vs_baseline or 0.0
    a2c_direct_pct = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).reduction_direct_pct_vs_baseline or 0.0
    baseline_direct = IQUITOS_BASELINE.reduction_direct_max_tco2_year

    print(f"{'  CO₂ Reducido (tCO₂)':<30} | {sac_direct:>19.0f} | {ppo_direct:>19.0f} | {a2c_direct:>19.0f} | {baseline_direct:>14.0f}")
    print(f"{'  % vs Baseline':<30} | {sac_direct_pct:>18.1f}% | {ppo_direct_pct:>18.1f}% | {a2c_direct_pct:>18.1f}% | {'100%':>14}")

    # TOTAL
    print(f"\n{'REDUCCIÓN TOTAL (Indirecta + Directa):':<30}")
    sac_total = sac_indir + sac_direct
    ppo_total = ppo_indir + ppo_direct
    a2c_total = a2c_indir + a2c_direct
    sac_total_pct = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).reduction_total_pct_vs_baseline or 0.0
    ppo_total_pct = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).reduction_total_pct_vs_baseline or 0.0
    a2c_total_pct = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).reduction_total_pct_vs_baseline or 0.0
    baseline_total = IQUITOS_BASELINE.reduction_total_max_tco2_year

    print(f"{'  CO₂ Reducido (tCO₂)':<30} | {sac_total:>19.0f} | {ppo_total:>19.0f} | {a2c_total:>19.0f} | {baseline_total:>14.0f}")
    print(f"{'  % vs Baseline':<30} | {sac_total_pct:>18.1f}% | {ppo_total_pct:>18.1f}% | {a2c_total_pct:>18.1f}% | {'100%':>14}")

    # CO₂ NETO
    print(f"\n{'CO₂ NETO (Emitido - Reducciones)':<30}")
    sac_neto = agents.get("sac", AgentMetrics("sac", 0, 0, 0, 0, 0, 0)).co2_neto_kg / 1000
    ppo_neto = agents.get("ppo", AgentMetrics("ppo", 0, 0, 0, 0, 0, 0)).co2_neto_kg / 1000
    a2c_neto = agents.get("a2c", AgentMetrics("a2c", 0, 0, 0, 0, 0, 0)).co2_neto_kg / 1000

    sac_status = "✨ CARBONO-NEGATIVO" if sac_neto < 0 else "⚠️  Carbono-positivo"
    ppo_status = "✨ CARBONO-NEGATIVO" if ppo_neto < 0 else "⚠️  Carbono-positivo"
    a2c_status = "✨ CARBONO-NEGATIVO" if a2c_neto < 0 else "⚠️  Carbono-positivo"

    print(f"{'  CO₂ Neto (tCO₂)':<30} | {sac_neto:>19.0f} | {ppo_neto:>19.0f} | {a2c_neto:>19.0f}")
    print(f"{'  Estado':<30} | {sac_status:>20} | {ppo_status:>20} | {a2c_status:>20}")

    # ENERGÍA
    print(f"\n{'ENERGÍA Y RED:':<30}")
    print(f"{'  Solar Utilization (%)':<30} | {agents.get('sac', AgentMetrics('sac', 0, 0, 0, 0, 0, 0)).solar_utilization_pct:>18.1f}% | {agents.get('ppo', AgentMetrics('ppo', 0, 0, 0, 0, 0, 0)).solar_utilization_pct:>18.1f}% | {agents.get('a2c', AgentMetrics('a2c', 0, 0, 0, 0, 0, 0)).solar_utilization_pct:>18.1f}% | {'0%':>14}")
    print(f"{'  Grid Independence Ratio':<30} | {agents.get('sac', AgentMetrics('sac', 0, 0, 0, 0, 0, 0)).grid_independence_ratio:>18.2f}x | {agents.get('ppo', AgentMetrics('ppo', 0, 0, 0, 0, 0, 0)).grid_independence_ratio:>18.2f}x | {agents.get('a2c', AgentMetrics('a2c', 0, 0, 0, 0, 0, 0)).grid_independence_ratio:>18.2f}x | {'0.28x':>14}")

    print("\n" + "="*120 + "\n")


def print_interpretation(agents: Dict[str, AgentMetrics]) -> None:
    """Imprime interpretación de resultados."""
    print("="*120)
    print("INTERPRETACIÓN DE RESULTADOS")
    print("="*120 + "\n")

    # Orden por reducción total
    agent_list = list(agents.values())
    agent_list.sort(
        key=lambda a: (a.reduction_total_pct_vs_baseline or 0.0),
        reverse=True
    )

    for i, agent in enumerate(agent_list, 1):
        pct = agent.reduction_total_pct_vs_baseline or 0.0
        status = "🥇 MEJOR" if i == 1 else "🥈 SEGUNDO" if i == 2 else "🥉 TERCERO"

        print(f"{status}: {agent.name}")
        print(f"  • Reducción Total: {pct:.1f}% vs baseline máximo (6,481 tCO₂/año)")

        direct_pct = agent.reduction_direct_pct_vs_baseline or 0.0
        indirect_pct = agent.reduction_indirect_pct_vs_baseline or 0.0

        print(f"  • Reducción Directa: {direct_pct:.1f}% (EVs vs gasolina)")
        print(f"  • Reducción Indirecta: {indirect_pct:.1f}% (Solar + BESS vs grid)")
        print(f"  • Solar Utilization: {agent.solar_utilization_pct:.1f}%")
        print(f"  • Grid Independence: {agent.grid_independence_ratio:.2f}x")

        neto = agent.co2_neto_kg / 1000
        if neto < 0:
            print(f"  ✨ CARBONO-NEGATIVO: Sistema produce {abs(neto):.0f} tCO₂ más reducción que emisión")
        else:
            print(f"  ⚠️  CARBONO-POSITIVO: Sistema emite {neto:.0f} tCO₂ neto (no controla completamente)")
        print()

    print("="*120 + "\n")


def main() -> int:
    """Función principal."""
    print("\n" + "="*120)
    print("COMPARACIÓN: Agentes RL vs IQUITOS_BASELINE")
    print("="*120 + "\n")

    # Load Iquitos baseline reference
    print(f"Baseline de Iquitos (3,328 EVs):")
    print(f"  • Reducción Directa Máxima: {IQUITOS_BASELINE.reduction_direct_max_tco2_year:.0f} tCO₂/año")
    print(f"  • Reducción Indirecta Máxima: {IQUITOS_BASELINE.reduction_indirect_max_tco2_year:.0f} tCO₂/año")
    print(f"  • Potencial Total: {IQUITOS_BASELINE.reduction_total_max_tco2_year:.0f} tCO₂/año")
    print(f"  • Factor Grid: {IQUITOS_BASELINE.co2_factor_grid_kg_per_kwh} kgCO₂/kWh")
    print(f"  • Factor EV: {IQUITOS_BASELINE.co2_conversion_ev_kg_per_kwh} kgCO₂/kWh\n")

    # Load agents
    agents = {}
    for agent_name in ["sac", "ppo", "a2c"]:
        metrics = load_agent_result(agent_name)
        if metrics:
            agents[agent_name] = metrics
            print(f"✅ Cargado: {agent_name.upper()}")
        else:
            print(f"⚠️  No disponible: {agent_name.upper()}")

    if not agents:
        print("\n❌ ERROR: No se encontraron resultados de agentes")
        print("   Ejecuta primero: python -m scripts.run_oe3_simulate --config configs/default.yaml")
        return 1

    print(f"\n✅ Cargados {len(agents)} agentes. Generando tabla...\n")

    # Print tables
    print_comparison_table(agents)
    print_interpretation(agents)

    print("💡 NOTAS:")
    print("  • % vs Baseline = (Reducción Actual / Máximo Teórico) × 100")
    print("  • >100% significa que supera el máximo teórico (ventaja de sinergia)")
    print("  • Carbono-Negativo = Reducción > Emisión (sistemas más limpios que producen)")
    print(f"\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
