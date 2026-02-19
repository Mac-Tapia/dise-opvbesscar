"""
Balance Energetico - Modulo de Visualizacion de Graficas v5.4.

SOLO contiene metodos para generar 9 graficas del balance energetico.
Recibe un DataFrame precalculado (df_balance) y genera visualizaciones.

Uso:
    from balance import BalanceEnergeticoSystem
    graphics = BalanceEnergeticoSystem(df_balance)
    graphics.plot_energy_balance(output_dir)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


@dataclass(frozen=True)
class BalanceEnergeticoConfig:
    """Configuracion minima de visualizacion."""
    pv_capacity_kwp: float = 4050.0
    demand_peak_limit_kw: float = 1900.0
    bess_capacity_kwh: float = 1700.0
    bess_power_kw: float = 400.0
    dod: float = 0.80
    efficiency_roundtrip: float = 0.95
    co2_intensity_kg_per_kwh: float = 0.4521


class BalanceEnergeticoSystem:
    """Generador de graficas para balance energetico v5.4.
    
    SOLO Visualizacion - Recibe DataFrame precalculado.
    """
    
    def __init__(self, df_balance: pd.DataFrame, config: Optional[BalanceEnergeticoConfig] = None):
        """Inicializa generador de graficas.
        
        Args:
            df_balance: DataFrame con datos precalculados
            config: Configuracion (usa defaults si es None)
        """
        self.df_balance = df_balance
        self.config = config or BalanceEnergeticoConfig()
    
    def plot_energy_balance(self, out_dir: Optional[Path] = None) -> None:
        """Genera todas las 9 graficas de balance energetico.
        
        Args:
            out_dir: Directorio para guardar (default: reports/balance_energetico)
        """
        if out_dir is None:
            out_dir = Path("reports/balance_energetico")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        df = self.df_balance
        print(f"\nGenerando gráficas en {out_dir}...")
        
        self._plot_integrated_balance(df, out_dir)  # NUEVA - Integrado completo
        self._plot_integral_curves(df, out_dir)
        self._plot_energy_flow_diagram(df, out_dir)
        self._plot_5day_balance(df, out_dir)
        self._plot_daily_balance(df, out_dir)
        self._plot_sources_distribution(df, out_dir)
        self._plot_energy_cascade(df, out_dir)
        self._plot_bess_soc(df, out_dir)
        self._plot_co2_emissions(df, out_dir)
        self._plot_pv_utilization(df, out_dir)
        
        print(f"✓ Gráficas guardadas")
    
    def _plot_integrated_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Gráfica INTEGRADA: Generación, BESS, EV (motos+taxis), Mall, Red - UN DÍA COMPLETO.
        
        Muestra todos los componentes en un mismo plot para visualizar el balance energético.
        """
        day_idx = 180  # Día representativo
        day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()
        hours = np.arange(24)
        
        fig, ax = plt.subplots(figsize=(18, 10))
        
        # 1. PV Generation (área dorada arriba)
        ax.fill_between(hours, 0, day_df['pv_generation_kw'].values, 
                       color='#FFD700', alpha=0.7, label='☀️ Generación Solar PV', linewidth=2, edgecolor='orange')
        
        # 2. BESS Charge (barras invertidas abajo en verde oscuro)
        bess_charge_vals = day_df['bess_charge_kw'].values
        ax.bar(hours, -bess_charge_vals, width=0.6, color='#228B22', alpha=0.8, 
              label='🔋 BESS Cargando (↑cargando batería)', edgecolor='darkgreen', linewidth=1)
        
        # 3. BESS Discharge (barras en naranja)
        bess_discharge_vals = day_df['bess_discharge_kw'].values
        ax.bar(hours, bess_discharge_vals, width=0.6, bottom=0, color='#FF8C00', alpha=0.8,
              label='🔋 BESS Descargando (↓sacando batería)', edgecolor='darkorange', linewidth=1)
        
        # 4. Mall Demand (barras azules)
        mall_demand_vals = day_df['mall_demand_kw'].values
        ax.bar(hours, mall_demand_vals, width=0.6, bottom=bess_discharge_vals, 
              color='#1E90FF', alpha=0.8, label='🏪 Demanda Mall (100 kW constante)', edgecolor='darkblue', linewidth=1)
        
        # 5&6. EV Demand con perfil horario realista (9h-22h con punta 18-20h)
        # Perfil horario: 0-8h cerrado, 9-17h ramp-up, 18-20h punta, 21-22h descenso
        hourly_profile = np.array([
            0.00,  # 0h: cerrado
            0.00,  # 1h: cerrado
            0.00,  # 2h: cerrado
            0.00,  # 3h: cerrado
            0.00,  # 4h: cerrado
            0.00,  # 5h: cerrado
            0.00,  # 6h: cerrado
            0.00,  # 7h: cerrado
            0.00,  # 8h: cerrado
            0.20,  # 9h: inicio (20%)
            0.35,  # 10h: ramp up
            0.50,  # 11h: ramp up
            0.65,  # 12h: ramp up
            0.75,  # 13h: ramp up
            0.85,  # 14h: ramp up
            0.90,  # 15h: ramp up
            0.95,  # 16h: pre-punta
            0.98,  # 17h: pre-punta
            1.00,  # 18h: PUNTA MÁXIMA
            1.00,  # 19h: PUNTA MÁXIMA
            1.00,  # 20h: PUNTA MÁXIMA
            0.80,  # 21h: DESCENSO
            0.50,  # 22h: DESCENSO
            0.00,  # 23h: cierre
        ])
        
        ev_demand_vals = day_df['ev_demand_kw'].values * hourly_profile
        bottom_vals = bess_discharge_vals + mall_demand_vals
        
        # Motos (78.9%)
        ax.bar(hours, ev_demand_vals * 0.789, width=0.6, bottom=bottom_vals,
              color='#90EE90', alpha=0.8, label='🛵 Motos Eléctricas (30 sockets, 5.19 kWh, 9-22h)', edgecolor='darkgreen', linewidth=1)
        
        # Taxis (21.1%) 
        ev_demand_taxis = ev_demand_vals * 0.211
        bottom_vals_taxis = bottom_vals + ev_demand_vals * 0.789
        ax.bar(hours, ev_demand_taxis, width=0.6, bottom=bottom_vals_taxis,
              color='#3D7B3D', alpha=0.8, label='🚕 Mototaxis Eléctricos (8 sockets, 7.40 kWh, 9-22h)', edgecolor='darkgreen', linewidth=1)
        
        # 7. Importación desde Red Pública (línea roja gruesa)
        grid_import_vals = day_df['demand_from_grid_kw'].values
        ax.plot(hours, grid_import_vals, color='#FF0000', linewidth=3, marker='D', markersize=6,
               label='🌐 Red Pública (importación)', linestyle='-', alpha=0.9)
        
        # 8. Total Demand como referencia (línea roja punteada)
        total_demand_vals = day_df['total_demand_kw'].values
        ax.plot(hours, total_demand_vals, color='#DC143C', linewidth=2.5, marker='o', markersize=4,
               label='📊 Demanda Total (PV+BESS+Red)', linestyle='--', alpha=0.7)
        
        # 9. Línea de referencia del threshold de pico (1,900 kW)
        ax.axhline(y=1900, color='#FF4500', linewidth=2.5, linestyle='--', alpha=0.6, label='⚡ Threshold Peak (1,900 kW)')
        
        # Línea 0
        ax.axhline(y=0, color='black', linewidth=1)
        
        # Anotaciones verticales para zonas EV
        ax.axvspan(9, 18, alpha=0.12, color='lightblue', label='Zona: Rampas (9-17h)')
        ax.axvspan(18, 21, alpha=0.15, color='red', label='Zona: ⚡ PUNTA (18-20h)')
        ax.axvspan(21, 23, alpha=0.10, color='orange', label='Zona: Descenso (21-22h)')
        
        # Anotaciones en horas críticas EV
        ax.annotate('INICIO OPERATIVO EV\n(9h: 20% demanda)', xy=(9, 150), xytext=(9, 600),
                   arrowprops=dict(arrowstyle='->', color='blue', lw=2), fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        
        ax.annotate('🔴 PUNTA MÁXIMA EV\n(18-20h: 100%)', xy=(19, 400), xytext=(19.5, 900),
                   arrowprops=dict(arrowstyle='->', color='red', lw=3), fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='#FFB6C6', alpha=0.8))
        
        ax.annotate('DESCENSO OPERATIVO\n(21-22h: 50-80%)', xy=(21.5, 120), xytext=(21.5, 400),
                   arrowprops=dict(arrowstyle='->', color='orange', lw=2), fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='#FFE4B5', alpha=0.7))
        
        # Titulos y etiquetas
        ax.set_xlabel('Hora del Día', fontsize=13, fontweight='bold')
        ax.set_ylabel('Potencia (kW)', fontsize=13, fontweight='bold')
        ax.set_title(f'⚡ BALANCE INTEGRADO - Día {day_idx}: Generación Solar + BESS Carga/Descarga + EV (motos/taxis) + Mall + Red',
                    fontsize=14, fontweight='bold', color='darkred', pad=20)
        
        # Grid
        ax.grid(True, alpha=0.2, linestyle=':', axis='y')
        ax.set_xlim(-0.8, 23.8)
        ax.set_xticks(np.arange(0, 24, 2))
        ax.set_xticklabels([f'{h:02d}h' for h in range(0, 24, 2)], fontsize=10, fontweight='bold')
        
        # Legend en dos columnas
        ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.95, edgecolor='black', fancybox=True)
        
        # Panel de información
        info_text = (
            f'ESPECIFICACIONES DEL SISTEMA (DATA REAL OE2):\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'☀️  PV: 4,050 kWp | 🔋 BESS: 1,700 kWh / 400 kW (DoD 80%)\n'
            f'🛵  MOTOS: 30 sockets, 5.19 kWh | 🚕  TAXIS: 8 sockets, 7.40 kWh\n'
            f'🏪 MALL: Real (0-2763 kW) | 🌐 RED: 0.4521 kg CO₂/kWh\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'⏰ PERFIL HORARIO EV (9-22h):\n'
            f'  9-17h: RAMP-UP (20% → 98%)  |  18-20h: PUNTA MÁXIMA (100%)\n'
            f'  21-22h: DESCENSO (80% → 50%)  |  0-8h,23h: CERRADO (0%)'
        )
        ax.text(0.98, 0.97, info_text, transform=ax.transAxes,
               fontsize=8, verticalalignment='top', horizontalalignment='right', family='monospace',
               bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.92, pad=1, edgecolor='black', linewidth=1.5))
        
        
        plt.tight_layout()
        plt.savefig(out_dir / "00_BALANCE_INTEGRADO_COMPLETO.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00_BALANCE_INTEGRADO_COMPLETO.png")
    
    def _plot_integral_curves(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 0: Integral - Primeros 7 dias."""
        df_7days = df.iloc[:7*24].copy()
        hours_real = np.arange(len(df_7days))
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 12))
        
        ax1.fill_between(hours_real, 0, df_7days['pv_generation_kw'], 
                        color='#FFD700', alpha=0.6, label='Generacion Solar PV', linewidth=1, edgecolor='orange')
        ax1.plot(hours_real, df_7days['mall_demand_kw'], color='#1E90FF', linewidth=2, label='Demanda Mall', linestyle='-')
        ax1.plot(hours_real, df_7days['ev_demand_kw'], color='#32CD32', linewidth=2, label='Demanda EV (38 tomas)', linestyle='-')
        ax1.plot(hours_real, df_7days['total_demand_kw'], color='#DC143C', linewidth=2.5, label='Demanda Total', linestyle='--')
        ax1.bar(hours_real, df_7days['bess_charge_kw'], width=0.8, color='#228B22', alpha=0.7, 
               label=f'BESS Carga (Anual: {df["bess_charge_kw"].sum()/1000:.0f} MWh)')
        ax1.bar(hours_real, -df_7days['bess_discharge_kw'], width=0.8, color='#FF8C00', alpha=0.7,
               label=f'BESS Descarga (Anual: {df["bess_discharge_kw"].sum()/1000:.0f} MWh)')
        ax1.axhline(y=0, color='black', linewidth=1)
        ax1.set_ylabel('Potencia (kW)', fontsize=12, fontweight='bold')
        ax1.set_title('DATOS REALES: GeneracionPV vs Demandas + BESS - Primeros 7 dias', 
                     fontsize=14, fontweight='bold', color='darkred')
        ax1.set_xlim(0, 168)
        ax1.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax1.set_xticklabels(['Dia 1', 'Dia 2', 'Dia 3', 'Dia 4', 'Dia 5', 'Dia 6', 'Dia 7', 'Dia 8'], fontsize=10)
        ax1.legend(loc='upper left', fontsize=10, framealpha=0.95, ncol=2)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        ax2_twin = ax2.twinx()
        ax2.plot(hours_real, df_7days['bess_soc_percent'], color='darkgreen', linewidth=2.5, marker='o', markersize=2, label='SOC BESS')
        ax2.axhline(y=100, color='green', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.axhline(y=20, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.fill_between(hours_real, 20, 100, alpha=0.1, color='green')
        ax2.set_ylabel('SOC BESS (%)', fontsize=12, fontweight='bold', color='darkgreen')
        ax2.set_ylim(0, 110)
        ax2.tick_params(axis='y', labelcolor='darkgreen')
        
        ax2_twin.bar(hours_real, df_7days['demand_from_grid_kw'], width=0.8, color='#FF6347', alpha=0.6, label='Importacion Red Publica')
        ax2_twin.set_ylabel('Importacion Red (kW)', fontsize=12, fontweight='bold', color='#FF6347')
        ax2_twin.tick_params(axis='y', labelcolor='#FF6347')
        ax2_twin.set_ylim(0, df_7days['demand_from_grid_kw'].max() * 1.2)
        
        ax2.set_xlabel('Hora (Primeros 7 dias)', fontsize=12, fontweight='bold')
        ax2.set_title('SOC BESS + Importacion Red Publica - Datos Reales', 
                     fontsize=14, fontweight='bold', color='darkred')
        ax2.set_xlim(0, 168)
        ax2.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax2.set_xticklabels(['Dia 1', 'Dia 2', 'Dia 3', 'Dia 4', 'Dia 5', 'Dia 6', 'Dia 7', 'Dia 8'], fontsize=10)
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10, framealpha=0.95)
        
        plt.tight_layout()
        plt.savefig(out_dir / "00_INTEGRAL_todas_curvas.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00_INTEGRAL_todas_curvas.png")
    
    def _plot_energy_flow_diagram(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 0.5: Flujo Energetico integrado (Sankey + día repr + SOC)."""
        total_pv = df['pv_generation_kw'].sum()
        total_ev = df['ev_demand_kw'].sum()
        total_mall = df['mall_demand_kw'].sum()
        total_bess_charge = df['bess_charge_kw'].sum()
        total_bess_discharge = df['bess_discharge_kw'].sum()
        total_grid_import = df['demand_from_grid_kw'].sum()
        total_pv_to_demand = df['pv_to_demand_kw'].sum()
        total_pv_to_bess = df['pv_to_bess_kw'].sum()
        total_pv_waste = df['pv_to_grid_kw'].sum()
        
        scale = 1000
        fig = plt.figure(figsize=(24, 13))
        gs = fig.add_gridspec(2, 2, width_ratios=[1, 1], height_ratios=[1, 0.7], hspace=0.35, wspace=0.25)
        
        ax1 = fig.add_subplot(gs[0:2, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 1])
        
        # SUBPLOT 1: Sankey Anual
        nodes = {
            'pv': (0.08, 0.75), 'grid': (0.08, 0.15),
            'bess_carga': (0.4, 0.75), 'bess_descarga': (0.4, 0.25),
            'mall': (0.85, 0.75), 'ev': (0.85, 0.35), 'waste': (0.85, 0.02),
        }
        
        node_width, node_height = 0.07, 0.07
        for name, (x, y) in [('pv', nodes['pv']), ('grid', nodes['grid']), ('bess_carga', nodes['bess_carga']),
                             ('bess_descarga', nodes['bess_descarga']), ('mall', nodes['mall']), 
                             ('ev', nodes['ev']), ('waste', nodes['waste'])]:
            if name == 'pv':
                color, edge = '#FFD700', 'orange'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=3, alpha=0.9))
                ax1.text(x, y, 'Solar PV\n4,050 kWp', ha='center', va='center', fontsize=10, fontweight='bold')
            elif name == 'grid':
                color, edge = '#FF6347', 'darkred'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=3, alpha=0.9))
                ax1.text(x, y, 'Red Publica', ha='center', va='center', fontsize=10, fontweight='bold', color='white')
            elif name == 'bess_carga':
                color, edge = '#228B22', 'darkgreen'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=4, alpha=0.95))
                ax1.text(x, y + 0.02, 'BESS↑CARGA', ha='center', va='center', fontsize=9, fontweight='bold', color='white')
                ax1.text(x, y - 0.02, '1,700 kWh', ha='center', va='center', fontsize=7, color='white')
            elif name == 'bess_descarga':
                color, edge = '#FF8C00', 'darkorange'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=4, alpha=0.95))
                ax1.text(x, y + 0.02, 'BESS↓DESCARGA', ha='center', va='center', fontsize=9, fontweight='bold', color='white')
                ax1.text(x, y - 0.02, '400 kW', ha='center', va='center', fontsize=7, color='white')
            elif name == 'mall':
                color, edge = '#1E90FF', 'darkblue'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=2, alpha=0.9))
                ax1.text(x, y, 'Mall\n(RED)', ha='center', va='center', fontsize=9, fontweight='bold')
            elif name == 'ev':
                color, edge = '#32CD32', 'darkgreen'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=2, alpha=0.9))
                ax1.text(x, y, 'EV\n38 sockets', ha='center', va='center', fontsize=9, fontweight='bold')
            elif name == 'waste':
                color, edge = '#A9A9A9', 'black'
                ax1.add_patch(plt.Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=2, alpha=0.6))
                ax1.text(x, y, 'Curtailment', ha='center', va='center', fontsize=8, fontweight='bold')
        
        ax1.set_xlim(-0.05, 1.05)
        ax1.set_ylim(-0.1, 1.1)
        ax1.axis('off')
        ax1.set_title('FLUJO ENERGETICO ANUAL - PERFIL EV DESDE CHARGERS + BESS DESAGREGADO',
                     fontsize=13, fontweight='bold', color='darkred')
        
        info_text = (
            f'BALANCE ANUAL OE2 REAL - BESS v5.4 + EV DESDE CHARGERS\n'
            f'PV: {total_pv/scale:.1f} MWh | Mall: {total_mall/scale:.1f} MWh | EV: {total_ev/scale:.1f} MWh\n'
            f'MOTOS: 270/día, 30 sockets, 4.6 kWh | TAXIS: 39/día, 8 sockets, 7.4 kWh\n'
            f'BESS CARGA: {total_pv_to_bess/scale:.1f} MWh | DESCARGA: {total_bess_discharge/scale:.1f} MWh'
        )
        ax1.text(0.01, 0.96, info_text, transform=ax1.transAxes,
                fontsize=7.5, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.95, pad=0.8))
        
        # SUBPLOT 2: Día representativo
        day_idx = 180
        day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()
        hours = np.arange(24)
        
        ax2.plot(hours, day_df['pv_generation_kw'].values, color='#FFD700', linewidth=3, marker='o', markersize=5, label='PV')
        ax2.bar(hours, day_df['mall_demand_kw'].values, width=0.65, label='Mall', color='#1E90FF', alpha=0.8)
        ax2.bar(hours, day_df['ev_demand_kw'].values, width=0.65, bottom=day_df['mall_demand_kw'].values, label='EV', color='#32CD32', alpha=0.8)
        ax2.plot(hours, day_df['total_demand_kw'].values, color='#DC143C', marker='D', linewidth=2.5, markersize=5, label='Total', linestyle='--')
        ax2.axhline(y=1900, color='#FF4500', linewidth=2.5, linestyle='--', label='Threshold 1900 kW', alpha=0.8)
        ax2.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
        ax2.set_title(f'Día {day_idx}: Lógica Operativa BESS v5.4', fontsize=11, fontweight='bold', color='darkred')
        ax2.grid(True, alpha=0.2, axis='y', linestyle=':')
        ax2.legend(loc='upper left', fontsize=8, ncol=2)
        ax2.set_xlim(-0.8, 23.8)
        
        # SUBPLOT 3: SOC
        ax3.plot(hours, day_df['bess_soc_percent'].values, color='#000000', linewidth=3.5, marker='o', markersize=5, label='SOC Real')
        ax3.fill_between(hours, 0, 20, alpha=0.25, color='#FF0000', label='Prohibida (<20%)')
        ax3.fill_between(hours, 20, 100, alpha=0.15, color='#228B22', label='Operativa (20%-100%)')
        ax3.axhline(y=100, color='green', linewidth=2, linestyle='--', alpha=0.7, label='Máximo (100%)')
        ax3.axhline(y=20, color='red', linewidth=2, linestyle='--', alpha=0.7, label='Mínimo (20%)')
        ax3.axhline(y=50, color='#4169E1', linewidth=1.5, linestyle=':', alpha=0.6, label='Prioridad 2 (50%)')
        ax3.set_xlabel('Hora', fontsize=10, fontweight='bold')
        ax3.set_ylabel('SOC (%)', fontsize=10, fontweight='bold')
        ax3.set_title('SOC BESS - Restricciones Operativas', fontsize=11, fontweight='bold', color='darkred')
        ax3.set_ylim(-5, 110)
        ax3.grid(True, alpha=0.2, axis='y', linestyle=':')
        ax3.legend(loc='right', fontsize=7.5, ncol=1)
        ax3.set_xlim(-0.8, 23.8)
        
        plt.tight_layout()
        plt.savefig(out_dir / "00.5_FLUJO_ENERGETICO_INTEGRADO.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00.5_FLUJO_ENERGETICO_INTEGRADO.png")
    
    def _plot_5day_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 1: Balance en 5 dias representativos."""
        fig, ax = plt.subplots(figsize=(16, 8))
        for day_idx in [0, 89, 180, 270, 359]:
            hours = list(range(24))
            ax.plot(hours, df.iloc[day_idx*24:(day_idx+1)*24]['pv_generation_kw'].values,
                   linewidth=2.5, marker='o', label=f'Día {day_idx}')
        ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
        ax.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
        ax.set_title('Generacion Solar - 5 Dias Representativos', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=10)
        ax.set_xlim(-0.5, 23.5)
        plt.tight_layout()
        plt.savefig(out_dir / "01_balance_5dias.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 01_balance_5dias.png")
    
    def _plot_daily_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 2: Balance diario (365 dias)."""
        df_day = df.copy()
        df_day['day'] = df_day['hour'] // 24 if 'hour' in df_day.columns else np.arange(len(df_day)) // 24
        daily = df_day.groupby('day').agg({'pv_generation_kw': 'sum', 'total_demand_kw': 'sum', 'demand_from_grid_kw': 'sum'}).reset_index()
        
        fig, ax = plt.subplots(figsize=(16, 6))
        ax.fill_between(daily['day'], 0, daily['pv_generation_kw'], color='#FFD700', alpha=0.7, label='PV')
        ax.fill_between(daily['day'], 0, daily['total_demand_kw'], color='#DC143C', alpha=0.3, label='Demanda')
        ax.plot(daily['day'], daily['demand_from_grid_kw'], color='#FF6347', linewidth=2, marker='o', markersize=3, label='Red')
        ax.set_xlabel('Dia del Año', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energia (kWh/dia)', fontsize=11, fontweight='bold')
        ax.set_title('Balance Diario - 365 Dias', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(out_dir / "02_balance_diario.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 02_balance_diario.png")
    
    def _plot_sources_distribution(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 3: Distribucion de fuentes."""
        pv = df['pv_to_demand_kw'].sum()
        bess = df['bess_discharge_kw'].sum() * 0.8 if 'bess_discharge_kw' in df.columns else 0
        grid = df['demand_from_grid_kw'].sum()
        total = pv + bess + grid
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.pie([pv, bess, grid], labels=[f'PV\n{pv/total*100:.1f}%', f'BESS\n{bess/total*100:.1f}%', f'Red\n{grid/total*100:.1f}%'],
              colors=['#FFD700', '#32CD32', '#FF6347'], explode=(0.05, 0.05, 0.1), startangle=90,
              textprops={'fontsize': 11, 'fontweight': 'bold'})
        ax.set_title('Distribucion de Fuentes (Anual)', fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(out_dir / "03_distribucion_fuentes.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 03_distribucion_fuentes.png")
    
    def _plot_energy_cascade(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 4: Cascada energetica."""
        pv_gen = df['pv_generation_kw'].sum()
        ev = df['ev_demand_kw'].sum()
        mall = df['mall_demand_kw'].sum()
        pv_dem = df['pv_to_demand_kw'].sum()
        pv_bess = df['pv_to_bess_kw'].sum()
        pv_waste = df['pv_to_grid_kw'].sum()
        bess_out = df['bess_discharge_kw'].sum()
        grid = df['demand_from_grid_kw'].sum()
        
        fig, ax = plt.subplots(figsize=(14, 10))
        cats = ['PV\nGen', 'PV→Dem', 'PV→BESS', 'PV\nWaste', 'BESS\nOut', 'Red', 'Dem\nTotal']
        vals = [pv_gen, pv_dem, pv_bess, pv_waste, bess_out, grid, ev + mall]
        cols = ['#FFD700', '#32CD32', '#32CD32', '#FF6347', '#FF8C00', '#FF6347', '#DC143C']
        
        x_pos = np.arange(len(cats))
        ax.bar(x_pos, vals, color=cols, alpha=0.8, edgecolor='black', linewidth=1.5)
        for i, v in enumerate(vals):
            ax.text(i, v + 50, f'{v:,.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(cats, fontsize=10, fontweight='bold')
        ax.set_ylabel('Energia (kWh/año)', fontsize=11, fontweight='bold')
        ax.set_title('Cascada Energetica Anual', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(out_dir / "04_cascada_energetica.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 04_cascada_energetica.png")
    
    def _plot_bess_soc(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 5: BESS SOC."""
        fig, ax = plt.subplots(figsize=(16, 6))
        hours = np.arange(len(df))
        soc = df['bess_soc_percent'].values
        
        ax.plot(hours, soc, linewidth=1, color='darkgreen', label='SOC Real')
        ax.axhline(y=100, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Max')
        ax.axhline(y=20, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Min')
        ax.fill_between(hours, 20, 100, alpha=0.1, color='green')
        
        ax.set_xlabel('Hora del Año', fontsize=11, fontweight='bold')
        ax.set_ylabel('SOC (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'BESS {self.config.bess_capacity_kwh:.0f} kWh - SOC Horario', fontsize=13, fontweight='bold')
        ax.legend(loc='lower left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 110)
        ax.set_xlim(0, len(df))
        plt.tight_layout()
        plt.savefig(out_dir / "05_bess_soc.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 05_bess_soc.png")
    
    def _plot_co2_emissions(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 6: Emisiones CO2."""
        df_day = df.copy()
        df_day['day'] = df_day['hour'] // 24 if 'hour' in df_day.columns else np.arange(len(df_day)) // 24
        daily_co2 = df_day.groupby('day')['co2_from_grid_kg'].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(16, 6))
        ax.bar(daily_co2['day'], daily_co2['co2_from_grid_kg'], color='#DC143C', alpha=0.8, edgecolor='darkred', linewidth=0.5)
        mean_co2 = daily_co2['co2_from_grid_kg'].mean()
        ax.axhline(y=mean_co2, color='black', linestyle='--', linewidth=2, label=f'Promedio: {mean_co2:.1f} kg/día')
        
        ax.set_xlabel('Dia del Año', fontsize=11, fontweight='bold')
        ax.set_ylabel('Emisiones CO2 (kg/dia)', fontsize=11, fontweight='bold')
        ax.set_title(f'Emisiones CO2 - {self.config.co2_intensity_kg_per_kwh:.4f} kg/kWh', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(out_dir / "06_emisiones_co2.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 06_emisiones_co2.png")
    
    def _plot_pv_utilization(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 7: Utilizacion mensual PV."""
        df_month = df.copy()
        df_month['month'] = (df_month['hour'] // 24 if 'hour' in df_month.columns else np.arange(len(df_month)) // 24) // 30 + 1
        monthly = df_month.groupby('month').agg({'pv_generation_kw': 'sum', 'pv_to_demand_kw': 'sum',
                                                    'pv_to_bess_kw': 'sum', 'pv_to_grid_kw': 'sum'}).reset_index()
        monthly = monthly[monthly['month'] <= 12]
        
        fig, ax = plt.subplots(figsize=(12, 7))
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        month_labels = months[:len(monthly)]
        x_pos = np.arange(len(monthly))
        
        width = 0.2
        ax.bar(x_pos - 1.5*width, monthly['pv_to_demand_kw'], width, label='PV→Demanda', color='#FFD700', edgecolor='black', linewidth=0.5)
        ax.bar(x_pos - 0.5*width, monthly['pv_to_bess_kw'], width, label='PV→BESS', color='#32CD32', edgecolor='black', linewidth=0.5)
        ax.bar(x_pos + 0.5*width, monthly['pv_to_grid_kw'], width, label='PV→Red', color='#FF6347', edgecolor='black', linewidth=0.5)
        ax.plot(x_pos, monthly['pv_generation_kw'], 'ko-', linewidth=2.5, markersize=8, label='Total PV')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(month_labels, fontsize=10, fontweight='bold')
        ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energia (kWh/mes)', fontsize=11, fontweight='bold')
        ax.set_title('Utilizacion Mensual de PV', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(out_dir / "07_utilizacion_pv.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 07_utilizacion_pv.png")


def main():
    """Demo: Ejecutar con DataFrame sintetico para pruebas."""
    import numpy as np
    
    print("=" * 80)
    print("DEMO: Balance Energetico - Graphics Only Module v5.4")
    print("=" * 80)
    print()
    
    # Crear DataFrame de prueba with REAL mall demand data
    print("Cargando datos reales del sistema...")
    
    # Cargar demanda real del mall desde CSV
    try:
        # Navegar a la raíz del proyecto: src/dimensionamiento/oe2/balance_energetico/balance.py -> 5 levels up
        project_root = Path(__file__).parent.parent.parent.parent.parent
        mall_csv_path = project_root / "data" / "oe2" / "demandamallkwh" / "demandamallhorakwh.csv"
        df_mall = pd.read_csv(mall_csv_path)
        mall_demand = df_mall['mall_demand_kwh'].values.astype(float)  # Already in kWh/hora = kW, NO divide by 1000
        print("[OK] Demanda Mall REAL cargada: {} horas (min={:.1f} kW, max={:.1f} kW, mean={:.1f} kW)".format(
            len(mall_demand), mall_demand.min(), mall_demand.max(), mall_demand.mean()))
    except Exception as e:
        print("[WARNING] No se pudo cargar demanda mall real, usando sintetica: {}".format(e))
        mall_demand = 100 + 20 * np.sin(2 * np.pi * np.arange(8760) / (365 * 24))
    
    hours = len(mall_demand)
    np.random.seed(42)
    
    # PV generation
    hour_of_day = np.arange(hours) % 24
    pv_gen = np.maximum(0, 4050 * (np.sin(np.pi * (hour_of_day - 6) / 12) ** 2))
    
    # EV demand (sintetica)
    ev_demand = 50 + 30 * np.sin(2 * np.pi * (hour_of_day - 12) / 24)
    ev_demand[ev_demand < 0] = 0
    
    total_demand = mall_demand + ev_demand
    
    # BESS logic
    bess_soc = np.ones(hours) * 50
    bess_charge = np.zeros(hours)
    bess_discharge = np.zeros(hours)
    demand_from_grid = np.zeros(hours)
    pv_to_demand = np.zeros(hours)
    pv_to_bess = np.zeros(hours)
    pv_to_grid = np.zeros(hours)
    co2_from_grid = np.zeros(hours)
    
    for t in range(1, hours):
        available_pv = pv_gen[t]
        demand_t = total_demand[t]
        pv_to_demand_t = min(available_pv, demand_t)
        available_pv -= pv_to_demand_t
        
        if available_pv > 0 and bess_soc[t-1] < 100:
            bess_charge_t = min(available_pv, 400, 100 - bess_soc[t-1])
            pv_to_bess[t] = bess_charge_t
            bess_charge[t] = bess_charge_t
            available_pv -= bess_charge_t
        
        pv_to_grid[t] = available_pv
        pv_to_demand[t] = pv_to_demand_t
        
        deficit = demand_t - pv_to_demand_t
        if deficit > 0:
            bess_discharge_t = min(deficit, 400, bess_soc[t-1] * 17)
            bess_discharge[t] = min(bess_discharge_t, deficit)
            demand_from_grid[t] = max(0, deficit - bess_discharge[t])
        
        bess_soc[t] = bess_soc[t-1] + (bess_charge[t] - bess_discharge[t]) / 1700 * 100
        bess_soc[t] = np.clip(bess_soc[t], 20, 100)
        co2_from_grid[t] = demand_from_grid[t] * 0.4521 / 1000
    
    df = pd.DataFrame({
        'hour': np.arange(hours),
        'pv_generation_kw': pv_gen,
        'mall_demand_kw': mall_demand,
        'ev_demand_kw': ev_demand,
        'total_demand_kw': total_demand,
        'pv_to_demand_kw': pv_to_demand,
        'pv_to_bess_kw': pv_to_bess,
        'pv_to_grid_kw': pv_to_grid,
        'bess_charge_kw': bess_charge,
        'bess_discharge_kw': bess_discharge,
        'bess_soc_percent': bess_soc,
        'demand_from_grid_kw': demand_from_grid,
        'co2_from_grid_kg': co2_from_grid,
    })
    
    print("[OK] DataFrame creado: {} horas x {} columnas".format(df.shape[0], df.shape[1]))
    print("    Mall: min={:.1f} kW, max={:.1f} kW, mean={:.1f} kW".format(
        df['mall_demand_kw'].min(), df['mall_demand_kw'].max(), df['mall_demand_kw'].mean()))
    print()
    
    # Crear sistema de gráficas
    config = BalanceEnergeticoConfig()
    graphics = BalanceEnergeticoSystem(df, config)
    print("[OK] BalanceEnergeticoSystem inicializado")
    print("  - PV: {:.0f} kWp".format(config.pv_capacity_kwp))
    print("  - BESS: {:.0f} kWh / {:.0f} kW".format(config.bess_capacity_kwh, config.bess_power_kw))
    print("  - CO2 intensity: {:.4f} kg/kWh".format(config.co2_intensity_kg_per_kwh))
    print()
    
    # Generar gráficas
    out_dir = Path(__file__).parent / "outputs_demo"
    graphics.plot_energy_balance(out_dir)
    print()
    print("=" * 80)
    print("[OK] Graficas guardadas en: {}".format(out_dir))
    print("=" * 80)


if __name__ == '__main__':
    main()
