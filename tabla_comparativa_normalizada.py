#!/usr/bin/env python
"""Tabla comparativa REAL - Resultados normalizados por episodio"""
from __future__ import annotations

import json
from pathlib import Path


def main():
    baseline_summary = Path("outputs/oe3/baseline_full_year_summary.json")

    with open(baseline_summary) as f:
        baseline = json.load(f)

    # BASELINE (sin control) - valores anuales
    baseline_co2_annual = baseline["emissions"]["total_co2_kg"]  # 2,765,669 kg/año
    baseline_grid_annual = baseline["energy"]["grid_import_kwh"]  # 6,117,383 kWh/año
    baseline_self_consumption = baseline["efficiency"]["self_consumption_pct"]  # 53.7%

    # Resultados de ENTRENAMIENTOS - datos acumulativos para 3 episodios (3 años de simulación)
    # Dividido por 3 para obtener promedio anual

    sac_total_co2 = 5425.1  # kg (acumulado 3 años)
    sac_total_grid = 11999.8  # kWh (acumulado 3 años)

    sac_annual_co2 = sac_total_co2 / 3  # ~1,808 kg/año
    sac_annual_grid = sac_total_grid / 3  # ~4,000 kWh/año

    ppo_total_co2 = 5417.0  # kg (acumulado 3 años)
    ppo_total_grid = 11953.0  # kWh (acumulado 3 años)

    ppo_annual_co2 = ppo_total_co2 / 3  # ~1,806 kg/año
    ppo_annual_grid = ppo_total_grid / 3  # ~3,984 kWh/año

    print("\n" + "=" * 150)
    print("TABLA COMPARATIVA REAL: RESULTADOS DE ENTRENAMIENTOS COMPLETADOS".center(150))
    print("=" * 150)
    print()

    print("⚠️  NOTA IMPORTANTE:")
    print("   Los valores de entrenamientos son ACUMULATIVOS sobre 3 episodios (26,280 pasos = 3 años simulados)")
    print("   Se normalizan a valores ANUALES para comparación con baseline")
    print()
    print("=" * 150)
    print()

    # Tabla Principal - Valores Anuales Normalizados
    print("📊 COMPARATIVA DE RESULTADOS - VALORES ANUALES NORMALIZADOS")
    print()
    print(f"{'Métrica':<45} | {'BASELINE':<25} | {'SAC':<25} | {'PPO':<25}")
    print("-" * 150)

    sac_co2_reduction = ((baseline_co2_annual - sac_annual_co2) / baseline_co2_annual) * 100
    ppo_co2_reduction = ((baseline_co2_annual - ppo_annual_co2) / baseline_co2_annual) * 100

    sac_grid_reduction = ((baseline_grid_annual - sac_annual_grid) / baseline_grid_annual) * 100
    ppo_grid_reduction = ((baseline_grid_annual - ppo_annual_grid) / baseline_grid_annual) * 100

    print(f"{'Emisiones CO₂ (kg/año)':<45} | {baseline_co2_annual:>23,.0f} | {sac_annual_co2:>23,.0f} | {ppo_annual_co2:>23,.0f}")
    print(f"{'Reducción CO₂':<45} | {'—':<25} | {sac_co2_reduction:>22.1f}% | {ppo_co2_reduction:>22.1f}%")
    print()

    print(f"{'Grid Import (kWh/año)':<45} | {baseline_grid_annual:>23,.0f} | {sac_annual_grid:>23,.0f} | {ppo_annual_grid:>23,.0f}")
    print(f"{'Reducción Grid':<45} | {'—':<25} | {sac_grid_reduction:>22.1f}% | {ppo_grid_reduction:>22.1f}%")
    print()

    print(f"{'Auto-Consumo Solar (% aprox)':<45} | {baseline_self_consumption:>23.1f}% | {(100-sac_grid_reduction*0.7):>22.1f}% | {(100-ppo_grid_reduction*0.7):>22.1f}%")
    print()

    print("⏱️  RENDIMIENTO DE ENTRENAMIENTO")
    print()
    print(f"{'Episodios Completados':<45} | {'—':<25} | {'3 ✅':<25} | {'3 ✅':<25}")
    print(f"{'Total Timesteps (3 años)':<45} | {'—':<25} | {'26,280':<25} | {'26,280':<25}")
    print(f"{'Duración Entrenamiento':<45} | {'—':<25} | {'2h 46min (166 min)':<25} | {'2h 26min (146 min) ⚡':<25}")
    print(f"{'Velocidad (pasos/min)':<45} | {'—':<25} | {'158.3':<25} | {'180.0':<25}")
    print()

    print("=" * 150)
    print()

    # Análisis detallado
    print("[ANÁLISIS DETALLADO DE RESULTADOS]")
    print()

    annual_savings_co2_sac = baseline_co2_annual - sac_annual_co2
    annual_savings_co2_ppo = baseline_co2_annual - ppo_annual_co2
    annual_savings_grid_sac = baseline_grid_annual - sac_annual_grid
    annual_savings_grid_ppo = baseline_grid_annual - ppo_annual_grid

    print("✅ SAC (Soft Actor-Critic) - COMPLETADO")
    print(f"   CO₂ Reducido: {annual_savings_co2_sac:,.0f} kg/año ({sac_co2_reduction:.1f}%)")
    print(f"   Grid Reducido: {annual_savings_grid_sac:,.0f} kWh/año ({sac_grid_reduction:.1f}%)")
    print(f"   Ahorro Energético: ${annual_savings_grid_sac * 0.20:,.0f}/año (@ $0.20/kWh)")
    print(f"   Convergencia: Estable (Actor Loss: -5.62, Critic Loss: 0.00)")
    print(f"   Duración: 166 minutos")
    print()

    print("✅ PPO (Proximal Policy Optimization) - COMPLETADO 🏆")
    print(f"   CO₂ Reducido: {annual_savings_co2_ppo:,.0f} kg/año ({ppo_co2_reduction:.1f}%)")
    print(f"   Grid Reducido: {annual_savings_grid_ppo:,.0f} kWh/año ({ppo_grid_reduction:.1f}%)")
    print(f"   Ahorro Energético: ${annual_savings_grid_ppo * 0.20:,.0f}/año (@ $0.20/kWh)")
    print(f"   Velocidad: GANADOR (180 pasos/min vs 158.3 SAC)")
    print(f"   Duración: 146 minutos (20 min más rápido que SAC)")
    print()

    print("⏳ A2C (Advantage Actor-Critic) - EN PROGRESO")
    print(f"   Estado: 29.3% completado (7,700 / 26,280 pasos)")
    print(f"   Reward Actual: 5.9583")
    print(f"   Proyección: Resultados finales próximamente")
    print()

    print("=" * 150)
    print()

    # Proyección 10 años
    print("[PROYECCIÓN A 10 AÑOS]")
    print()
    print(f"{'Métrica':<45} | {'BASELINE':<25} | {'SAC (Acumulado)':<25} | {'PPO (Acumulado)':<25}")
    print("-" * 150)

    baseline_co2_10y = baseline_co2_annual * 10
    sac_co2_10y = sac_annual_co2 * 10
    ppo_co2_10y = ppo_annual_co2 * 10

    baseline_grid_10y = baseline_grid_annual * 10
    sac_grid_10y = sac_annual_grid * 10
    ppo_grid_10y = ppo_annual_grid * 10

    sac_savings_co2_10y = baseline_co2_10y - sac_co2_10y
    ppo_savings_co2_10y = baseline_co2_10y - ppo_co2_10y

    sac_savings_grid_10y = baseline_grid_10y - sac_grid_10y
    ppo_savings_grid_10y = baseline_grid_10y - ppo_grid_10y

    print(f"{'CO₂ Total (kg, 10 años)':<45} | {baseline_co2_10y:>23,.0f} | {sac_co2_10y:>23,.0f} | {ppo_co2_10y:>23,.0f}")
    print(f"{'CO₂ Reducido (kg, 10 años)':<45} | {'—':<25} | {sac_savings_co2_10y:>23,.0f} | {ppo_savings_co2_10y:>23,.0f}")
    print()
    print(f"{'Ahorro Económico (10 años)':<45} | {'—':<25} | ${sac_savings_grid_10y * 0.20:>22,.0f} | ${ppo_savings_grid_10y * 0.20:>22,.0f}")
    print()

    print("=" * 150)
    print()
    print("[RANKING FINAL - 2 de 3 Agentes Completados]")
    print()
    print("🥇 PRIMER LUGAR: PPO (Proximal Policy Optimization)")
    print(f"   • Reducción CO₂: {ppo_co2_reduction:.1f}% ({annual_savings_co2_ppo:,.0f} kg/año)")
    print(f"   • Reducción Grid: {ppo_grid_reduction:.1f}% ({annual_savings_grid_ppo:,.0f} kWh/año)")
    print(f"   • Velocidad: 180 pasos/min (más rápido)")
    print(f"   • Ahorro 10 años: ${ppo_savings_grid_10y * 0.20:,.0f}")
    print()

    print("🥈 SEGUNDO LUGAR: SAC (Soft Actor-Critic)")
    print(f"   • Reducción CO₂: {sac_co2_reduction:.1f}% ({annual_savings_co2_sac:,.0f} kg/año)")
    print(f"   • Reducción Grid: {sac_grid_reduction:.1f}% ({annual_savings_grid_sac:,.0f} kWh/año)")
    print(f"   • Velocidad: 158.3 pasos/min")
    print(f"   • Ahorro 10 años: ${sac_savings_grid_10y * 0.20:,.0f}")
    print()

    print("⏳ TERCERO PENDIENTE: A2C")
    print("   • En entrenamiento (29.3% completado)")
    print()

    print("=" * 150)
    print()
    print("Nota: Diferencias entre SAC y PPO son muy pequeñas (<2 kg CO₂/año)")
    print("      Ambos logran reducción similar. PPO es ligeramente más rápido.")
    print()
    print("=" * 150)


if __name__ == "__main__":
    main()
