#!/usr/bin/env python3
"""
Genera visualización de los esquemas preparados para OE3
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def main():
    base = Path(__file__).parent.parent
    dataset_dir = base / "data" / "processed" / "citylearn" / "iquitos_ev_mall"
    reports = base / "reports" / "oe3"
    reports.mkdir(parents=True, exist_ok=True)
    
    # Cargar esquemas
    schema_pv = json.loads((dataset_dir / "schema_pv_bess.json").read_text(encoding='utf-8'))
    schema_grid = json.loads((dataset_dir / "schema_grid_only.json").read_text(encoding='utf-8'))
    
    # Extraer información clave
    building = list(schema_pv.get("buildings", {}).values())[0] if schema_pv.get("buildings") else {}
    
    # Capacidades
    pv_nominal = building.get("pv", {}).get("nominal_power", 0)
    bess_cap = building.get("electrical_storage", {}).get("capacity", 0)
    bess_pow = building.get("electrical_storage", {}).get("nominal_power", 0)
    charger_count = len(building.get("chargers", {}) or {})

    ev_motos = 900
    ev_mototaxis = 130
    ev_results_path = base / "data" / "interim" / "oe2" / "chargers" / "chargers_results.json"
    if ev_results_path.exists():
        ev_results = json.loads(ev_results_path.read_text(encoding="utf-8"))
        ev_motos = int(ev_results.get("n_motos", ev_motos))
        ev_mototaxis = int(ev_results.get("n_mototaxis", ev_mototaxis))
    
    # Crear figura comparativa
    fig, axes = plt.subplots(1, 2, figsize=(16, 10))
    
    # --- Esquema Grid Only ---
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Esquema: GRID ONLY\n(Baseline sin FV ni BESS)', fontsize=14, fontweight='bold', color='red')
    
    # Grid
    grid = mpatches.FancyBboxPatch((0.5, 7), 2, 2, boxstyle="round,pad=0.1", 
                                    facecolor='lightgray', edgecolor='black', linewidth=2)
    ax.add_patch(grid)
    ax.text(1.5, 8, 'RED\nELÉCTRICA', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Building/Mall
    building_box = mpatches.FancyBboxPatch((3.5, 4), 3, 3, boxstyle="round,pad=0.1",
                                            facecolor='#ffcccc', edgecolor='black', linewidth=2)
    ax.add_patch(building_box)
    ax.text(5, 5.5, f'MALL\n+\nCARGADORES EV\n({charger_count} unidades)', ha='center', va='center', fontsize=9, fontweight='bold')
    
    # EV Fleet
    ev = mpatches.FancyBboxPatch((3.5, 0.5), 3, 2, boxstyle="round,pad=0.1",
                                  facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(ev)
    ax.text(5, 1.5, f'FLOTA EV\n{ev_motos} motos + {ev_mototaxis} mototaxis', ha='center', va='center', fontsize=9)
    
    # Flechas
    ax.annotate('', xy=(3.5, 5.5), xytext=(2.5, 8),
                arrowprops=dict(arrowstyle='->', color='red', lw=3))
    ax.text(2.8, 7, '100%\nRed', fontsize=9, color='red', fontweight='bold')
    
    ax.annotate('', xy=(5, 2.5), xytext=(5, 4),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    
    # Etiqueta de emisiones
    ax.text(8, 8, 'CO₂ = ALTO\n(toda la energía\nviene de red)',
            fontsize=10, color='red', ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='mistyrose', edgecolor='red'))
    
    # --- Esquema PV + BESS ---
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Esquema: PV + BESS + CONTROL\n(Sistema optimizado OE2)', fontsize=14, fontweight='bold', color='green')
    
    # Grid
    grid = mpatches.FancyBboxPatch((0.5, 7), 2, 2, boxstyle="round,pad=0.1",
                                    facecolor='lightgray', edgecolor='black', linewidth=2)
    ax.add_patch(grid)
    ax.text(1.5, 8, 'RED\nELÉCTRICA', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Solar PV
    pv = mpatches.FancyBboxPatch((7, 7), 2.5, 2, boxstyle="round,pad=0.1",
                                  facecolor='orange', edgecolor='darkorange', linewidth=2)
    ax.add_patch(pv)
    ax.text(8.25, 8, f'SOLAR FV\n{pv_nominal:,.0f} kWp', ha='center', va='center', fontsize=10, fontweight='bold')
    
    # BESS
    bess = mpatches.FancyBboxPatch((7, 4), 2.5, 2, boxstyle="round,pad=0.1",
                                    facecolor='#66b3ff', edgecolor='blue', linewidth=2)
    ax.add_patch(bess)
    ax.text(8.25, 5, f'BESS\n{bess_cap:,.0f} kWh\n{bess_pow:,.0f} kW', 
            ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Building/Mall
    building_box = mpatches.FancyBboxPatch((3, 4), 3, 3, boxstyle="round,pad=0.1",
                                            facecolor='#ccffcc', edgecolor='black', linewidth=2)
    ax.add_patch(building_box)
    ax.text(4.5, 5.5, f'MALL\n+\nCARGADORES EV\n({charger_count} unidades)', ha='center', va='center', fontsize=9, fontweight='bold')
    
    # EV Fleet
    ev = mpatches.FancyBboxPatch((3, 0.5), 3, 2, boxstyle="round,pad=0.1",
                                  facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(ev)
    ax.text(4.5, 1.5, f'FLOTA EV\n{ev_motos} motos + {ev_mototaxis} mototaxis', ha='center', va='center', fontsize=9)
    
    # Control Agent
    agent = mpatches.Ellipse((4.5, 8.5), 2, 1.2, facecolor='yellow', edgecolor='black', linewidth=2)
    ax.add_patch(agent)
    ax.text(4.5, 8.5, 'AGENTE\nRL/RBC', ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Flechas
    # Grid -> Building (menor)
    ax.annotate('', xy=(3, 6), xytext=(2.5, 8),
                arrowprops=dict(arrowstyle='->', color='gray', lw=2, ls='--'))
    ax.text(2.3, 7.2, 'Backup', fontsize=8, color='gray')
    
    # PV -> Building
    ax.annotate('', xy=(6, 6), xytext=(7, 8),
                arrowprops=dict(arrowstyle='->', color='orange', lw=3))
    ax.text(6.8, 7.2, 'Solar', fontsize=9, color='darkorange', fontweight='bold')
    
    # PV -> BESS
    ax.annotate('', xy=(8.25, 6), xytext=(8.25, 7),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
    
    # BESS -> Building
    ax.annotate('', xy=(6, 5), xytext=(7, 5),
                arrowprops=dict(arrowstyle='->', color='blue', lw=2))
    
    # Building -> EV
    ax.annotate('', xy=(4.5, 2.5), xytext=(4.5, 4),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    
    # Agent connections
    ax.plot([4.5, 4.5], [7.9, 7], 'k--', lw=1)
    ax.plot([4.5, 8.25], [7.9, 6], 'k--', lw=1)
    
    # Etiqueta de emisiones
    ax.text(1.5, 3, 'CO₂ = BAJO\n(máximo uso\nde solar)',
            fontsize=10, color='green', ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='honeydew', edgecolor='green'))
    
    plt.tight_layout()
    fig.savefig(reports / 'oe3_schemas_comparison.png', dpi=150, bbox_inches='tight')
    print(f"OK Guardado: {reports / 'oe3_schemas_comparison.png'}")
    
    # =========================================
    # Figura 2: Configuración de agentes OE3
    # =========================================
    fig2, ax2 = plt.subplots(figsize=(14, 8))
    ax2.axis('off')
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.set_title('Configuración de Agentes para OE3\nSimulación CityLearn', fontsize=16, fontweight='bold')
    
    # Tabla de agentes
    agents_info = """
    ╔════════════════════════════════════════════════════════════════════════════════════╗
    ║                        AGENTES DE CONTROL OE3                                      ║
    ╠════════════════════════════════════════════════════════════════════════════════════╣
    ║                                                                                    ║
    ║  1. UNCONTROLLED (Baseline)                                                        ║
    ║     ─────────────────────────────────────────────────────────────                  ║
    ║     • Carga EV al máximo disponible inmediatamente                                 ║
    ║     • BESS permanece inactivo (acción = 0)                                         ║
    ║     • Propósito: Línea base para comparación de emisiones                          ║
    ║                                                                                    ║
    ║  2. BasicEVRBC (Rule-Based Control)                                                ║
    ║     ─────────────────────────────────────────────────────────────                  ║
    ║     • Prioriza carga durante horas de máxima generación solar                      ║
    ║     • Reglas heurísticas simples basadas en hora del día                           ║
    ║     • Propósito: Control simple sin aprendizaje                                    ║
    ║                                                                                    ║
    ║  3. SAC (Soft Actor-Critic)                                                        ║
    ║     ─────────────────────────────────────────────────────────────                  ║
    ║     • Agente RL con máxima entropía                                                ║
    ║     • Entrena 5 episodios, luego evalúa determinísticamente                        ║
    ║     • Reward: -emisiones CO₂ (minimiza impacto ambiental)                          ║
    ║     • Propósito: Control óptimo aprendido                                          ║
    ║                                                                                    ║
    ╠════════════════════════════════════════════════════════════════════════════════════╣
    ║                        MÉTRICAS DE EVALUACIÓN                                      ║
    ╠════════════════════════════════════════════════════════════════════════════════════╣
    ║                                                                                    ║
    ║  • Emisiones CO₂ anuales (kg CO₂/año)                                              ║
    ║  • Energía importada de red (kWh)                                                  ║
    ║  • Autoconsumo solar (%)                                                           ║
    ║  • Proyección a 20 años                                                            ║
    ║                                                                                    ║
    ╚════════════════════════════════════════════════════════════════════════════════════╝
    """
    ax2.text(5, 5, agents_info, ha='center', va='center', fontsize=10, fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange', linewidth=2))
    
    fig2.savefig(reports / 'oe3_agents_config.png', dpi=150, bbox_inches='tight')
    print(f"OK Guardado: {reports / 'oe3_agents_config.png'}")
    
    # =========================================
    # Resumen final
    # =========================================
    print("\n" + "="*70)
    print("         ESQUEMAS OE3 PREPARADOS CORRECTAMENTE")
    print("="*70)
    print(f"\nDataset CityLearn: {dataset_dir}")
    print("\nEsquemas generados:")
    print(f"   1. schema_grid_only.json  - Baseline (solo red)")
    print(f"   2. schema_pv_bess.json    - Sistema completo (FV + BESS + Control)")
    print("\nConfiguracion del sistema:")
    print(f"   • BESS Capacidad: {bess_cap:,.0f} kWh")
    print(f"   • BESS Potencia:  {bess_pow:,.0f} kW")
    print(f"   • Timestep:       {schema_pv.get('seconds_per_time_step', 3600)} segundos")
    print(f"   • Pasos totales:  {schema_pv.get('simulation_end_time_step', 8759) + 1}")
    print("\nAgentes a evaluar:")
    print(f"   • Uncontrolled (baseline)")
    print(f"   • BasicEVRBC (rule-based)")
    print(f"   • SAC (reinforcement learning)")
    print("\n" + "="*70)
    
    plt.show()

if __name__ == "__main__":
    main()
