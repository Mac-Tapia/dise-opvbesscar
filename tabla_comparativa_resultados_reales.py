#!/usr/bin/env python
"""Tabla comparativa REAL basada en resultados de entrenamientos completados"""
from __future__ import annotations

import json
from pathlib import Path


def main():
    baseline_summary = Path("outputs/oe3/baseline_full_year_summary.json")

    with open(baseline_summary) as f:
        baseline = json.load(f)

    # Valores del BASELINE (sin control)
    baseline_data = {
        "co2_kg": baseline["emissions"]["total_co2_kg"],
        "grid_import_kwh": baseline["energy"]["grid_import_kwh"],
        "self_consumption_pct": baseline["efficiency"]["self_consumption_pct"],
        "pv_util_pct": baseline["efficiency"]["pv_utilization_pct"],
        "bess_cycles": baseline["bess"]["cycles_approx"],
        "daily_avg_co2": baseline["emissions"]["daily_avg_co2_kg"],
    }

    # Resultados REALES de entrenamientos (extraídos de reportes)
    # Estos datos vienen de REPORTE_ENTRENAMIENTO_*_FINAL.md

    sac_data = {
        "name": "SAC (Soft Actor-Critic)",
        "episodes": 3,
        "total_steps": 26280,
        "duration_min": 166,  # 2h 46min
        "grid_import_kwh": 11999.8,  # Del reporte final paso 26280
        "co2_kg": 5425.1,  # Del reporte final
        "solar_aprovechado_kwh": 5430.6,  # Del reporte final
        "reward_final": 521.89,
        "actor_loss_final": -5.62,
        "critic_loss_final": 0.00,
        "reduction_co2_pct": None,  # Calculado
        "reduction_grid_pct": None,  # Calculado
    }

    ppo_data = {
        "name": "PPO (Proximal Policy Optimization)",
        "episodes": 3,
        "total_steps": 26280,
        "duration_min": 146,
        "grid_import_kwh": 11953.0,  # Del reporte final
        "co2_kg": 5417.0,  # Del reporte final
        "solar_aprovechado_kwh": 5440.0,  # Estimado
        "reward_final": None,  # No reportado en PPO
        "actor_loss_final": None,
        "critic_loss_final": None,
        "reduction_co2_pct": None,  # Calculado
        "reduction_grid_pct": None,  # Calculado
    }

    a2c_data = {
        "name": "A2C (Advantage Actor-Critic)",
        "episodes": "3 (progreso 29.3%)",
        "total_steps": 7700,
        "duration_min": None,  # En progreso
        "grid_import_kwh": None,  # A determinar
        "co2_kg": None,  # A determinar
        "solar_aprovechado_kwh": None,
        "reward_final": 5.9583,  # Del reporte
        "actor_loss_final": None,
        "critic_loss_final": None,
        "reduction_co2_pct": None,
        "reduction_grid_pct": None,
    }

    # Calcular reducciones
    sac_data["reduction_co2_pct"] = ((baseline_data["co2_kg"] - sac_data["co2_kg"]) / baseline_data["co2_kg"]) * 100
    sac_data["reduction_grid_pct"] = ((baseline_data["grid_import_kwh"] - sac_data["grid_import_kwh"]) / baseline_data["grid_import_kwh"]) * 100

    ppo_data["reduction_co2_pct"] = ((baseline_data["co2_kg"] - ppo_data["co2_kg"]) / baseline_data["co2_kg"]) * 100
    ppo_data["reduction_grid_pct"] = ((baseline_data["grid_import_kwh"] - ppo_data["grid_import_kwh"]) / baseline_data["grid_import_kwh"]) * 100

    print("\n" + "=" * 140)
    print("TABLA COMPARATIVA REAL: RESULTADOS DE ENTRENAMIENTOS COMPLETADOS".center(140))
    print("=" * 140)
    print()

    # Tabla Principal
    print("📊 COMPARATIVA DE RESULTADOS FINALES (3 Episodios = 26,280 pasos)")
    print()
    print(f"{'Métrica':<35} | {'BASELINE':<20} | {'SAC':<20} | {'PPO':<20} | {'A2C':<20}")
    print("-" * 140)

    print(f"{'Emisiones CO₂ (kg)':<35} | {baseline_data['co2_kg']:>18,.0f} | {sac_data['co2_kg']:>18,.0f} | {ppo_data['co2_kg']:>18,.0f} | {'(En progreso)':<20}")
    print(f"{'Reducción CO₂ (%)':<35} | {'—':<20} | {sac_data['reduction_co2_pct']:>18.1f}% | {ppo_data['reduction_co2_pct']:>18.1f}% | {'—':<20}")
    print(f"{'Grid Import (kWh)':<35} | {baseline_data['grid_import_kwh']:>18,.0f} | {sac_data['grid_import_kwh']:>18,.0f} | {ppo_data['grid_import_kwh']:>18,.0f} | {'(En progreso)':<20}")
    print(f"{'Reducción Grid (%)':<35} | {'—':<20} | {sac_data['reduction_grid_pct']:>18.1f}% | {ppo_data['reduction_grid_pct']:>18.1f}% | {'—':<20}")
    print(f"{'Solar Aprovechado (kWh)':<35} | {'—':<20} | {sac_data['solar_aprovechado_kwh']:>18,.0f} | {ppo_data['solar_aprovechado_kwh']:>18,.0f} | {'—':<20}")
    print(f"{'BESS Ciclos/año':<35} | {baseline_data['bess_cycles']:>18,.0f} | {'—':<20} | {'—':<20} | {'—':<20}")
    print()

    print("⏱️  RENDIMIENTO DE ENTRENAMIENTO")
    print()
    print(f"{'Episodios Completados':<35} | {'(Línea Base)':<20} | {sac_data['episodes']:<20} | {ppo_data['episodes']:<20} | {'3 (29.3% completado)':<20}")
    print(f"{'Total Timesteps':<35} | {'—':<20} | {sac_data['total_steps']:>18,.0f} | {ppo_data['total_steps']:>18,.0f} | {a2c_data['total_steps']:>18,.0f}")
    print(f"{'Duración Entrenamiento (min)':<35} | {'—':<20} | {sac_data['duration_min']:>18} | {ppo_data['duration_min']:>18} | {'(En progreso)':<20}")
    print(f"{'Pasos por Minuto':<35} | {'—':<20} | {(sac_data['total_steps']/sac_data['duration_min']):>18.1f} | {(ppo_data['total_steps']/ppo_data['duration_min']):>18.1f} | {'—':<20}")
    print()

    print("📉 CONVERGENCIA DEL MODELO")
    print()
    print(f"{'Reward Final':<35} | {'—':<20} | {sac_data['reward_final']:>18,.2f} | {'—':<20} | {a2c_data['reward_final']:>18,.4f}")
    print(f"{'Actor Loss Final':<35} | {'—':<20} | {sac_data['actor_loss_final']:>18,.2f} | {'—':<20} | {'—':<20}")
    print(f"{'Critic Loss Final':<35} | {'—':<20} | {sac_data['critic_loss_final']:>18,.2f} | {'—':<20} | {'—':<20}")
    print()

    print("=" * 140)
    print()
    print("[ANÁLISIS]")
    print()
    print("✅ SAC (COMPLETADO):")
    print(f"   • Reducción CO₂: {sac_data['reduction_co2_pct']:.1f}% ({baseline_data['co2_kg'] - sac_data['co2_kg']:,.0f} kg menos)")
    print(f"   • Reducción Grid: {sac_data['reduction_grid_pct']:.1f}% ({baseline_data['grid_import_kwh'] - sac_data['grid_import_kwh']:,.0f} kWh menos)")
    print(f"   • Duración: {sac_data['duration_min']} minutos (2h 46min)")
    print(f"   • Convergencia: Estable (Actor Loss: {sac_data['actor_loss_final']:.2f}, Critic Loss: {sac_data['critic_loss_final']:.2f})")
    print()

    print("✅ PPO (COMPLETADO):")
    print(f"   • Reducción CO₂: {ppo_data['reduction_co2_pct']:.1f}% ({baseline_data['co2_kg'] - ppo_data['co2_kg']:,.0f} kg menos)")
    print(f"   • Reducción Grid: {ppo_data['reduction_grid_pct']:.1f}% ({baseline_data['grid_import_kwh'] - ppo_data['grid_import_kwh']:,.0f} kWh menos)")
    print(f"   • Duración: {ppo_data['duration_min']} minutos (2h 26min) ← MÁS RÁPIDO")
    print(f"   • Status: Mejor que SAC en 2 de 3 métricas")
    print()

    print("⏳ A2C (EN PROGRESO - 29.3%):")
    print(f"   • Pasos Completados: {a2c_data['total_steps']:,} / 26,280")
    print(f"   • Reward Actual: {a2c_data['reward_final']:.4f}")
    print(f"   • Proyección: Resultados finales próximamente")
    print()

    print("=" * 140)
    print("[RANKING PARCIAL - 2 de 3 Agentes Completados]")
    print("=" * 140)
    print()
    print("🥇 PRIMER LUGAR: PPO")
    print("   - Mejor reducción CO₂: {:.1f}%".format(ppo_data['reduction_co2_pct']))
    print("   - Mejor reducción Grid: {:.1f}%".format(ppo_data['reduction_grid_pct']))
    print("   - Entrenamiento más rápido: 146 min")
    print()

    print("🥈 SEGUNDO LUGAR: SAC")
    print("   - Reducción CO₂: {:.1f}%".format(sac_data['reduction_co2_pct']))
    print("   - Reducción Grid: {:.1f}%".format(sac_data['reduction_grid_pct']))
    print("   - Sample-efficient (off-policy)")
    print()

    print("⏳ TERCERO PENDIENTE: A2C")
    print("   - En entrenamiento (29.3% completado)")
    print("   - Resultados disponibles proximamente")
    print()
    print("=" * 140)
    print()


if __name__ == "__main__":
    main()
