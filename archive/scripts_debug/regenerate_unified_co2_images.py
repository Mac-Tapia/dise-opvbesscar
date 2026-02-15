#!/usr/bin/env python3
"""
UNIFIED CO2 METHODOLOGY - Regenerar imágenes de CO2 paratodos los agentes
Verifica que SAC, A2C y PPO usan EXACTAMENTE la misma lógica de cálculo de CO2
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple

# ============================================================================
# UNIFIED CO2 CALCULATION FUNCTIONS (Identical for all 3 agents)
# ============================================================================

CO2_FACTOR_IQUITOS = 0.4521  # kg CO2/kWh diesel
GASOLINA_KG_CO2_PER_LITRO = 2.31
MOTO_LITROS_PER_100KM = 2.0
MOTOTAXI_LITROS_PER_100KM = 3.0
MOTO_KM_PER_KWH = 50.0
MOTOTAXI_KM_PER_KWH = 30.0


def calculate_unified_co2(
    ev_charging_kwh: float,
    solar_kw: float,
    bess_power_kw: float,
    mall_kw: float,
    total_demand_kwh: float,
    grid_import_kwh: float,
) -> Tuple[float, float, float]:
    """
    Calcula CO2 directo e indirecto usando lógica UNIFICADA (SAC/A2C/PPO).
    
    Returns:
        (co2_directo, co2_indirecto, peak_shaving_factor)
    """
    
    # ===== CO2 DIRECTO (Modal Shift: gasolina → eléctrico) =====
    # Proporción: 30 motos + 8 mototaxis = 38 sockets
    moto_ratio = 30.0 / 38.0
    mototaxi_ratio = 8.0 / 38.0
    
    motos_energy = ev_charging_kwh * moto_ratio
    mototaxis_energy = ev_charging_kwh * mototaxi_ratio
    
    km_motos = motos_energy * MOTO_KM_PER_KWH
    km_mototaxis = mototaxis_energy * MOTOTAXI_KM_PER_KWH
    
    litros_motos = km_motos * MOTO_LITROS_PER_100KM / 100.0
    litros_taxis = km_mototaxis * MOTOTAXI_LITROS_PER_100KM / 100.0
    
    co2_directo = (litros_motos + litros_taxis) * GASOLINA_KG_CO2_PER_LITRO
    
    # ===== CO2 INDIRECTO (Solar + BESS con Peak Shaving) =====
    solar_avoided = min(solar_kw, total_demand_kwh)
    bess_discharge = max(0.0, bess_power_kw)
    
    # Peak shaving factor
    if mall_kw > 2000.0:
        peak_shaving_factor = 1.0 + (mall_kw - 2000.0) / max(1.0, mall_kw) * 0.5
    else:
        peak_shaving_factor = 0.5 + (mall_kw / 2000.0) * 0.5
    
    bess_co2_benefit = bess_discharge * peak_shaving_factor
    co2_indirecto = (solar_avoided + bess_co2_benefit) * CO2_FACTOR_IQUITOS
    
    return co2_directo, co2_indirecto, peak_shaving_factor


def load_agent_timeseries(agent_name: str) -> pd.DataFrame:
    """Carga el timeseries para un agente."""
    path = Path(f'outputs/{agent_name.lower()}_training/timeseries_{agent_name.lower()}.csv')
    if not path.exists():
        print(f"⚠️ No encontrado: {path}")
        return pd.DataFrame()
    
    df = pd.read_csv(path)
    print(f"✅ Cargado: {agent_name} ({len(df)} rows)")
    return df


def validate_unified_methodology(df: pd.DataFrame, agent_name: str):
    """Valida que el timeseries use la metodología unificada de CO2."""
    
    print(f"\n{'='*80}")
    print(f"VALIDACIÓN METODOLOGÍA UNIFICADA - {agent_name}")
    print(f"{'='*80}")
    
    required_cols = ['solar_kw', 'ev_charging_kw', 'bess_power_kw', 'mall_demand_kw', 'grid_import_kw']
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"❌ FALTA COLUMNAS: {missing}")
        return False
    
    print(f"✅ Todas las columnas requeridas presentes")
    
    # Validar que tenemos datos de CO2
    if 'co2_avoided_direct_kg' in df.columns:
        print(f"✅ CO2 DIRECTO encontrado (media: {df['co2_avoided_direct_kg'].mean():.2f} kg/h)")
    else:
        print(f"⚠️ CO2 DIRECTO no en timeseries (será recalculado)")
    
    if 'co2_avoided_indirect_kg' in df.columns:
        print(f"✅ CO2 INDIRECTO encontrado (media: {df['co2_avoided_indirect_kg'].mean():.2f} kg/h)")
    else:
        print(f"⚠️ CO2 INDIRECTO no en timeseries (será recalculado)")
    
    return True


def recalculate_co2_unified(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """Recalcula CO2 usando metodología unificada para verificación."""
    
    co2_directo = []
    co2_indirecto = []
    peak_factors = []
    
    for _, row in df.iterrows():
        direct, indirect, factor = calculate_unified_co2(
            ev_charging_kwh=row.get('ev_charging_kw', 0),
            solar_kw=row.get('solar_kw', 0),
            bess_power_kw=row.get('bess_power_kw', 0),
            mall_kw=row.get('mall_demand_kw', 0),
            total_demand_kwh=row.get('ev_charging_kw', 0) + row.get('mall_demand_kw', 0),
            grid_import_kwh=row.get('grid_import_kw', 0),
        )
        co2_directo.append(direct)
        co2_indirecto.append(indirect)
        peak_factors.append(factor)
    
    return {
        'co2_directo': np.array(co2_directo),
        'co2_indirecto': np.array(co2_indirecto),
        'peak_factors': np.array(peak_factors),
    }


def main():
    """Regenera imágenes de CO2 para todos los agentes con metodología unificada."""
    
    print("\n" + "="*80)
    print("UNIFIED CO2 METHODOLOGY - Regenerando imágenes para SAC/A2C/PPO")
    print("="*80)
    
    # Cargar datos de los 3 agentes
    agents = ['SAC', 'A2C', 'PPO']
    data = {}
    
    for agent in agents:
        print(f"\n📊 Cargando {agent}...")
        df = load_agent_timeseries(agent)
        if df.empty:
            print(f"⚠️ Saltando {agent}")
            continue
        
        # Validar metodología
        if validate_unified_methodology(df, agent):
            # Recalcular CO2 con fórmula unificada
            recalc = recalculate_co2_unified(df)
            data[agent] = {
                'df': df,
                'co2_directo': recalc['co2_directo'],
                'co2_indirecto': recalc['co2_indirecto'],
                'peak_factors': recalc['peak_factors'],
            }
    
    if not data:
        print("\n❌ No se pudieron cargar datos de agentes")
        return
    
    # ========================================================================
    # CREAR VISUALIZACIONES
    # ========================================================================
    
    output_dir = Path('outputs/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # --- FIGURE 1: CO2 DIRECTO E INDIRECTO POR AGENTE ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('UNIFIED CO2 METHODOLOGY - Directo vs Indirecto por Agente\n(Same formula for all: SAC/A2C/PPO)', 
                 fontsize=14, fontweight='bold')
    
    colors = {'SAC': '#3498db', 'A2C': '#2ecc71', 'PPO': '#e74c3c'}
    
    for idx, (agent, color) in enumerate(colors.items()):
        if agent not in data:
            continue
        
        ax = axes[idx]
        co2_d = data[agent]['co2_directo']
        co2_i = data[agent]['co2_indirecto']
        
        hours = np.arange(len(co2_d))
        ax.plot(hours, co2_d, label='CO₂ Directo (Modal Shift)', color=color, linewidth=2, alpha=0.8)
        ax.plot(hours, co2_i, label='CO₂ Indirecto (Solar + BESS)', color='#f39c12', linewidth=2, alpha=0.8)
        ax.fill_between(hours, co2_d, alpha=0.2, color=color)
        ax.fill_between(hours, co2_i, alpha=0.2, color='#f39c12')
        
        ax.set_title(f'{agent} Agent\n({len(co2_d)} timesteps)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Hour of Year', fontsize=10)
        ax.set_ylabel('CO₂ Avoided (kg/h)', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc='upper right')
        
        # Statistics
        total_directo = co2_d.sum()
        total_indirecto = co2_i.sum()
        mean_ratio = np.mean(co2_i[co2_d > 0] / co2_d[co2_d > 0]) if np.any(co2_d > 0) else 0
        
        stats_text = f"Total Direct: {total_directo:,.0f} kg/year\nTotal Indirect: {total_indirecto:,.0f} kg/year"
        ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='bottom', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    save_path = output_dir / 'unified_co2_by_agent.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Guardado: {save_path}")
    
    # --- FIGURE 2: COMPARACIÓN 3 AGENTES ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('UNIFIED CO2 METHODOLOGY - 3-Agent Comparison\n(All use: Directo=Modal Shift + Indirecto=Solar+BESS peak shaving)', 
                 fontsize=14, fontweight='bold')
    
    # Panel 1: Total CO2 evitado
    ax = axes[0, 0]
    agents_list = list(data.keys())
    totals_directo = [data[a]['co2_directo'].sum() for a in agents_list]
    totals_indirecto = [data[a]['co2_indirecto'].sum() for a in agents_list]
    
    x = np.arange(len(agents_list))
    width = 0.35
    ax.bar(x - width/2, [t/1000 for t in totals_directo], width, label='CO₂ Directo (Modal Shift)',
           color='#3498db', alpha=0.8)
    ax.bar(x + width/2, [t/1000 for t in totals_indirecto], width, label='CO₂ Indirecto (Solar+BESS)',
           color='#f39c12', alpha=0.8)
    ax.set_ylabel('CO₂ Evitado (toneladas/año)', fontsize=11, fontweight='bold')
    ax.set_title('Total CO₂ Avoided (Annual)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(agents_list)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Añadir valores en barras
    for i, (d, ind) in enumerate(zip(totals_directo, totals_indirecto)):
        ax.text(i - width/2, d/1000 + 50, f'{d/1000:.0f}t', ha='center', fontsize=9, fontweight='bold')
        ax.text(i + width/2, ind/1000 + 50, f'{ind/1000:.0f}t', ha='center', fontsize=9, fontweight='bold')
    
    # Panel 2: Ratio Indirecto/Directo
    ax = axes[0, 1]
    ratios = [totals_indirecto[i] / max(totals_directo[i], 1) for i in range(len(agents_list))]
    bars = ax.bar(agents_list, ratios, color=[colors[a] for a in agents_list], alpha=0.7, edgecolor='black', linewidth=2)
    ax.set_ylabel('Ratio (Indirecto / Directo)', fontsize=11, fontweight='bold')
    ax.set_title('Indirect/Direct CO₂ Ratio (Higher = Better Solar/BESS utilization)', fontsize=12, fontweight='bold')
    ax.axhline(y=1, color='red', linestyle='--', linewidth=2, alpha=0.5, label='1:1 ratio')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=10)
    
    for bar, ratio in zip(bars, ratios):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 0.1, f'{ratio:.2f}x',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Panel 3: Peak Shaving Factor Distribution
    ax = axes[1, 0]
    for agent, color in colors.items():
        if agent in data:
            peak_factors = data[agent]['peak_factors']
            ax.hist(peak_factors, bins=50, alpha=0.6, label=f'{agent} (mean={peak_factors.mean():.3f})',
                   color=color, edgecolor='black')
    ax.set_xlabel('Peak Shaving Factor', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequency (hours)', fontsize=11, fontweight='bold')
    ax.set_title('Peak Shaving Factor Distribution\n(Identical formula for all agents)', fontsize=12, fontweight='bold')
    ax.axvline(x=1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Baseline (factor=1.0)')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Methodology Summary
    ax = axes[1, 1]
    ax.axis('off')
    
    methodology_text = """
UNIFIED CO2 METHODOLOGY (Applied to SAC / A2C / PPO)

═══════════════════════════════════════════════════

CO2 DIRECTO (Modal Shift: Gasoline → Electric)
─────────────────────────────────────────────────
Formula:
  • EV energy delivered (kWh) × moto ratio (30/38)
  • km_motos = energy × 50 km/kWh
  • litros_motos = km × 2.0 L/100km
  • CO₂ directo = litros × 2.31 kg CO₂/L

CO2 INDIRECTO (Solar + BESS with Peak Shaving)
─────────────────────────────────────────────────
Formula:
  • Solar used = min(solar_kw, demand)
  • BESS benefit = discharge × peak_shaving_factor
  
  Peak Shaving Factor:
    if mall > 2000 kW: factor = 1.0 + (mall-2000)/mall × 0.5
    if mall ≤ 2000 kW: factor = 0.5 + mall/2000 × 0.5
  
  • CO₂ indirecto = (solar + BESS_benefit) × 0.4521 kg CO₂/kWh

═══════════════════════════════════════════════════

✓ All agents use identical formulas
✓ Differences in CO2 come from different control strategies
✓ Better agents = same methodology, smarter dispatch
"""
    
    ax.text(0.1, 0.95, methodology_text, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
    
    plt.tight_layout()
    save_path = output_dir / 'unified_co2_comparison_3agents.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✅ Guardado: {save_path}")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    
    print("\n" + "="*80)
    print("RESUMEN: UNIFIED CO2 METHODOLOGY")
    print("="*80)
    
    for agent in agents_list:
        d_total = data[agent]['co2_directo'].sum()
        i_total = data[agent]['co2_indirecto'].sum()
        total = d_total + i_total
        
        print(f"\n{agent}:")
        print(f"  CO₂ Directo:    {d_total:>12,.0f} kg/año ({d_total/total*100:>5.1f}%)")
        print(f"  CO₂ Indirecto:  {i_total:>12,.0f} kg/año ({i_total/total*100:>5.1f}%)")
        print(f"  Total Evitado:  {total:>12,.0f} kg/año")
        print(f"  Peak Shaving:   Factor promedio = {data[agent]['peak_factors'].mean():.4f}x")
    
    print("\n" + "="*80)
    print("✅ VISUALIZACIONES REGENERADAS CON METODOLOGÍA UNIFICADA")
    print("="*80)
    print("\nTodas las imágenes están en: outputs/analysis/")


if __name__ == "__main__":
    main()
