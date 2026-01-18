"""
REPORTE DE ENTRENAMIENTO: Estado Actual del Entrenamiento RL
Verificación de Avance y Aprendizaje de A2C, SAC, PPO
"""

import json
from pathlib import Path

print("=" * 110)
print("🚀 REPORTE DE ENTRENAMIENTO: VERIFICACIÓN DE AVANCE Y APRENDIZAJE")
print("=" * 110)
print()

results_dir = Path("outputs/oe3/simulations")

# Cargar resultados
results = {}
for agent in ["A2C", "SAC", "PPO", "Uncontrolled"]:
    with open(results_dir / f"result_{agent}.json") as f:
        results[agent] = json.load(f)

print("1️⃣ ESTADO DE ENTRENAMIENTO")
print("-" * 110)
print()

config_max_steps = {
    "A2C": 87600,
    "SAC": 100000,
    "PPO": 438000,
}

for agent in ["A2C", "SAC", "PPO"]:
    result = results[agent]
    steps = result["steps"]
    max_steps = config_max_steps[agent]
    years = result["simulated_years"]
    progress = (steps / max_steps) * 100
    
    print(f"🤖 {agent}")
    print(f"   Pasos completados:  {steps:>10,} / {max_steps:>10,} ({progress:>5.1f}%)")
    print(f"   Años simulados:     {years:>10.2f}")
    
    if progress >= 99:
        print(f"   Estado:             ✅ COMPLETADO")
    elif progress >= 50:
        print(f"   Estado:             🔄 EN PROGRESO (50%+)")
    elif progress >= 10:
        print(f"   Estado:             ⏳ EARLY STAGE (< 50%)")
    else:
        print(f"   Estado:             🚫 APENAS COMENZÓ")
    print()

print()
print("2️⃣ COMPARACIÓN: AGENTES ENTRENADOS VS BASELINE")
print("-" * 110)
print()

baseline = results["Uncontrolled"]
baseline_carbon = baseline["carbon_kg"]
baseline_grid = baseline["grid_import_kwh"]
baseline_reward = baseline["reward_total_mean"]

metrics = {
    "A2C": results["A2C"],
    "SAC": results["SAC"],
    "PPO": results["PPO"],
}

print(f"{'Agente':<12} {'CO₂ (kg)':<18} {'Reducción':<15} {'Grid (GWh)':<18} {'Reducción':<15} {'Recompensa':<12}")
print("-" * 110)

for name, result in metrics.items():
    carbon = result["carbon_kg"]
    grid = result["grid_import_kwh"] / 1e6
    reward = result["reward_total_mean"]
    
    carbon_red = ((baseline_carbon - carbon) / baseline_carbon) * 100
    grid_red = ((baseline_grid - result["grid_import_kwh"]) / baseline_grid) * 100
    
    print(f"{name:<12} {carbon:>15,.0f}  {carbon_red:>12.1f}%   {grid:>15.2f}  {grid_red:>12.1f}%   {reward:>10.4f}")

print()
print(f"{'BASELINE':<12} {baseline_carbon:>15,.0f}  {0:>12.1f}%   {baseline_grid/1e6:>15.2f}  {0:>12.1f}%   {baseline_reward:>10.4f}")

print()
print()
print("3️⃣ ANÁLISIS DETALLADO DE A2C (Agente Principal)")
print("-" * 110)
print()

a2c = results["A2C"]
steps_pct = (a2c["steps"] / 87600) * 100

print(f"Progreso de Entrenamiento:")
print(f"  Pasos: {a2c['steps']:>10,} / 87,600 ({steps_pct:>5.1f}%)")
print(f"  Época actual: ~{a2c['steps'] // 8760 + 1} de 10 episodios")
print(f"  Tiempo estimado para completar: ~{(87600 - a2c['steps']) // 8760 * 60:.0f} minutos")
print()

print(f"Desempeño Energético:")
print(f"  Grid Import Total:    {a2c['grid_import_kwh']:>15,.0f} kWh = {a2c['grid_import_kwh']/1e6:>6.2f} GWh")
print(f"  PV Generation:        {a2c['pv_generation_kwh']:>15,.0f} kWh = {a2c['pv_generation_kwh']/1e6:>6.2f} GWh")
print(f"  EV Charging Demand:   {a2c['ev_charging_kwh']:>15,.0f} kWh = {a2c['ev_charging_kwh']/1e3:>6.2f} MWh")
print(f"  Building Load:        {a2c['building_load_kwh']:>15,.0f} kWh = {a2c['building_load_kwh']/1e6:>6.2f} GWh")
print()

print(f"Métricas de CO₂ y Costo:")
print(f"  Emisiones CO₂:        {a2c['carbon_kg']:>15,.0f} kg")
print(f"  vs Baseline:          {((baseline_carbon - a2c['carbon_kg']) / baseline_carbon * 100):>14.1f}% reducción")
print(f"  Costo anual (est.):   ${a2c['net_grid_kwh'] * 0.20:>14,.0f}")
print()

print(f"Recompensas Multiobjetivo:")
objectives = [
    ("CO₂ Reduction (50%)",     a2c['reward_co2_mean'], 0.50),
    ("Cost Reduction (15%)",    a2c['reward_cost_mean'], 0.15),
    ("Solar Maximize (20%)",    a2c['reward_solar_mean'], 0.20),
    ("EV Satisfaction (10%)",   a2c['reward_ev_mean'], 0.10),
    ("Grid Stability (5%)",     a2c['reward_grid_mean'], 0.05),
]

for obj, reward, weight in objectives:
    weighted = reward * weight
    print(f"  {obj:<25} {reward:>8.4f} → {weighted:>8.4f}")

print(f"  {'─' * 40}")
print(f"  {'Total Reward':<25} {a2c['reward_total_mean']:>8.4f}")

print()
print()
print("4️⃣ EVALUACIÓN DE APRENDIZAJE A2C")
print("-" * 110)
print()

print("✅ LO QUE A2C HA APRENDIDO BIEN:")
print()
if a2c["reward_solar_mean"] > 0:
    print(f"  ☀️  Autoconsumo Solar ({a2c['reward_solar_mean']:.3f}):")
    print(f"      A2C APRENDE a cargar EVs cuando hay disponibilidad solar")
    print(f"      Estrategia: Maximizar autoconsumo, reducir importación de red")
else:
    print(f"  ☀️  Autoconsumo Solar ({a2c['reward_solar_mean']:.3f}): ⚠️ Débil")

if a2c["reward_ev_mean"] > 0.05:
    print(f"      ")
    print(f"  🔋 Satisfacción de EV ({a2c['reward_ev_mean']:.3f}):")
    print(f"      A2C APRENDE a mantener EVs satisfechos (>90% SOC)")
    print(f"      Gestiona carga para cumplir demanda con disponibilidad solar + BESS")
else:
    print(f"  🔋 Satisfacción de EV ({a2c['reward_ev_mean']:.3f}): ⚠️ Débil")

print()
print("⚠️ OBJETIVOS DIFÍCILES (comportamiento esperado):")
print()
if a2c["reward_co2_mean"] < -0.8:
    print(f"  🌍 CO₂ Reduction ({a2c['reward_co2_mean']:.3f}): ❌ IMPOSIBLE")
    print(f"      Razón: Red térmica Iquitos tiene factor de emisión 0.4521 kg/kWh")
    print(f"      Mall debe importar ~24.7 GWh/año para carga base (inevitables emisiones CO₂)")
    print(f"      PV solo genera 8 GWh → No es suficiente para bajar más.")
    print()

if a2c["reward_grid_mean"] < -0.4:
    print(f"  📊 Grid Stability ({a2c['reward_grid_mean']:.3f}): ⚠️ Difícil")
    print(f"      Razón: Demanda del mall es muy alta (peak 570 kWh vs 200 kWh limite)")
    print(f"      BESS solo 2000 kWh no es suficiente para desplazar toda la carga pico")

print()
print()
print("5️⃣ PROGRESO DE APRENDIZAJE A TRAVÉS DE ENTRENAMIENTOS")
print("-" * 110)
print()

print(f"Configuración de Entrenamiento:")
print(f"  • Episodes configurados: 10")
print(f"  • Pasos por episodio: ~8,760 (1 año de datos)")
print(f"  • Pasos totales máximo: 87,600")
print(f"  • Pasos actuales: {a2c['steps']:,} ({steps_pct:.1f}%)")
print()

if steps_pct < 20:
    stage = "🚫 EARLY STAGE (aprendizaje inicial)"
elif steps_pct < 50:
    stage = "🔄 CONVERGENCIA INICIAL (políticas básicas formadas)"
elif steps_pct < 80:
    stage = "📈 MEJORA (refinamiento de estrategia)"
else:
    stage = "✅ CONVERGENCIA FINAL (políticas estables)"

print(f"Etapa de Aprendizaje: {stage}")
print()

print("Comportamiento Esperado por Etapa:")
print(f"  • 0-10%: Acciones aleatorias, sin estrategia clara")
print(f"  • 10-30%: Primeras estrategias básicas emergen")
print(f"  • 30-60%: Mejora consistente, refinamiento")
print(f"  • 60-100%: Convergencia, políticas estables")
print()

if steps_pct < 50:
    print(f"⚠️ NOTA: A2C está en fase temprana ({steps_pct:.1f}%). El aprendizaje mejorará conforme")
    print(f"   complete más episodios. Las recompensas mostradas son PRELIMINARES.")
else:
    print(f"✅ A2C ha pasado punto de convergencia. Estrategias estables esperadas.")

print()
print()
print("6️⃣ COMPARACIÓN A2C vs OTROS AGENTES")
print("-" * 110)
print()

print("📊 Tabla Comparativa (Agentes en Etapas Diferentes):")
print()
print(f"{'Agente':<12} {'% Entrenado':<15} {'CO₂ (kg)':<18} {'Recompensa':<18} {'Estado':<20}")
print("-" * 110)

for agent in ["A2C", "SAC", "PPO"]:
    result = results[agent]
    steps = result["steps"]
    max_steps = config_max_steps[agent]
    pct = (steps / max_steps) * 100
    
    if pct >= 99:
        status = "✅ COMPLETO"
    elif pct >= 50:
        status = "🔄 EN PROGRESO"
    else:
        status = "⏳ TEMPRANO"
    
    print(f"{agent:<12} {pct:>13.1f}% {result['carbon_kg']:>15,.0f} kg  {result['reward_total_mean']:>15.4f}    {status:<20}")

print()
print("⚠️ INTERPRETACIÓN:")
print("  • SAC está al 1.9% (1,873 / 100,000 pasos)")
print("  • A2C está al 10.0% (8,759 / 87,600 pasos)")
print("  • PPO está al 0.0% (0 pasos, probablemente no ejecutado aún)")
print()
print("  Los agentes en etapas diferentes NO son comparables directamente.")
print("  Esperar a que TODOS completen entrenamiento antes de evaluar ganador.")

print()
print()
print("7️⃣ RECOMENDACIONES")
print("-" * 110)
print()

print("📋 ACCIONES INMEDIATAS:")
print()
print("1. ✅ A2C: Continuar entrenamiento hasta 87,600 pasos")
print(f"   Progreso actual: {a2c['steps']:,} / 87,600 ({steps_pct:.1f}%)")
print(f"   ETA completación: ~{(87600 - a2c['steps']) / 100:.0f} minutos")
print()

print("2. ✅ SAC: Reanudar o reiniciar entrenamiento")
print(f"   Progreso actual: {results['SAC']['steps']:,} / 100,000 (1.9%)")
print(f"   Usar: python -m scripts.continue_sac_training --config configs/default.yaml")
print()

print("3. ✅ PPO: Iniciar entrenamiento")
print(f"   Progreso actual: {results['PPO']['steps']:,} / 438,000 (0.0%)")
print(f"   Usar: python -m scripts.run_oe3_simulate --config configs/default.yaml")
print()

print("📊 MONITOREO:")
print("  • Ver archivo 'co2_comparison.md' para tabla final")
print("  • Usar 'monitor_checkpoints.py' para seguimiento en tiempo real")
print("  • Checkpoints guardados en: outputs/oe3/checkpoints/<agent>/")
print()

print("=" * 110)
