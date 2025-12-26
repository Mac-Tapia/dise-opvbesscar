#!/usr/bin/env python3
"""
Genera reportes y visualizaciones completas de OE2:
- Dimensionamiento Solar (PV)
- Dimensionamiento de Cargadores EV
- Dimensionamiento BESS
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configurar estilo
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    base = Path(__file__).parent.parent
    interim = base / "data" / "interim" / "oe2"
    reports = base / "reports" / "oe2"
    reports.mkdir(parents=True, exist_ok=True)
    
    # =========================================
    # 1. CARGAR TODOS LOS RESULTADOS
    # =========================================
    solar = load_json(interim / "solar" / "solar_results.json")
    chargers = load_json(interim / "chargers" / "chargers_results.json")
    bess = load_json(interim / "bess" / "bess_results.json")
    scale_factor = solar.get("scale_factor")
    if scale_factor is None:
        target_annual = solar.get("target_annual_kwh", 0.0)
        annual_kwh = solar.get("annual_kwh", 0.0)
        scale_factor = target_annual / annual_kwh if annual_kwh else 1.0
    
    # Cargar series temporales
    pv_ts = pd.read_csv(interim / "solar" / "pv_generation_timeseries.csv")
    pv_24h = pd.read_csv(interim / "solar" / "pv_profile_24h.csv")
    ev_24h = pd.read_csv(interim / "chargers" / "perfil_horario_carga.csv")
    bess_24h = pd.read_csv(interim / "bess" / "bess_daily_balance_24h.csv")
    scenarios = pd.read_csv(interim / "chargers" / "selection_pe_fc_completo.csv")
    
    # Normalizar columnas esperadas si el CSV no las incluye
    if "surplus_kwh" not in bess_24h.columns or "deficit_kwh" not in bess_24h.columns:
        if "net_balance_kwh" in bess_24h.columns:
            net_balance = bess_24h["net_balance_kwh"]
        else:
            net_balance = bess_24h["pv_kwh"] - bess_24h["load_kwh"]
        bess_24h["surplus_kwh"] = net_balance.clip(lower=0)
        bess_24h["deficit_kwh"] = (-net_balance).clip(lower=0)

    if "mall_kwh" not in bess_24h.columns or "ev_kwh" not in bess_24h.columns:
        total_demand = float(bess.get("total_demand_kwh_day", 0.0)) or 1.0
        mall_share = float(bess.get("mall_demand_kwh_day", 0.0)) / total_demand
        ev_share = float(bess.get("ev_demand_kwh_day", 0.0)) / total_demand
        bess_24h["mall_kwh"] = bess_24h["load_kwh"] * mall_share
        bess_24h["ev_kwh"] = bess_24h["load_kwh"] * ev_share

    # =========================================
    # 2. GENERAR FIGURAS
    # =========================================
    
    # --- Fig 1: Perfil PV anual ---
    fig1, axes1 = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1a: Serie temporal completa
    ax = axes1[0, 0]
    pv_ts['timestamp'] = pd.to_datetime(pv_ts['timestamp'])
    ax.plot(pv_ts['timestamp'], pv_ts['pv_kwh'], linewidth=0.3, alpha=0.7, color='orange')
    ax.set_title('Generación FV Anual (2025)', fontweight='bold')
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Energía (kWh)')
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    
    # 1b: Perfil promedio 24h
    ax = axes1[0, 1]
    ax.fill_between(pv_24h['hour'], pv_24h['pv_kwh'], alpha=0.4, color='orange')
    ax.plot(pv_24h['hour'], pv_24h['pv_kwh'], 'o-', color='darkorange', markersize=4)
    ax.set_title('Perfil Promedio Diario FV', fontweight='bold')
    ax.set_xlabel('Hora del día')
    ax.set_ylabel('Energía promedio (kWh)')
    ax.set_xticks(range(0, 24, 2))
    ax.axvspan(6, 18, alpha=0.1, color='yellow', label='Horas de sol')
    ax.legend()
    
    # 1c: Distribución mensual
    ax = axes1[1, 0]
    pv_ts['month'] = pd.to_datetime(pv_ts['timestamp']).dt.month
    monthly = pv_ts.groupby('month')['pv_kwh'].sum() / 1000  # MWh
    bars = ax.bar(monthly.index, monthly.values, color='orange', edgecolor='darkorange')
    ax.set_title('Generación Mensual FV', fontweight='bold')
    ax.set_xlabel('Mes')
    ax.set_ylabel('Energía (MWh)')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'])
    for bar, val in zip(bars, monthly.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    
    # 1d: Resumen numérico
    ax = axes1[1, 1]
    ax.axis('off')
    summary_text = f"""
    ╔══════════════════════════════════════════╗
    ║     DIMENSIONAMIENTO SOLAR (FV)          ║
    ╠══════════════════════════════════════════╣
    ║  Capacidad DC:     {solar['target_dc_kw']:,.2f} kWp           ║
    ║  Capacidad AC:     {solar['target_ac_kw']:,.2f} kW            ║
    ║  Generación anual: {solar['annual_kwh']/1e6:,.2f} GWh          ║
    ║  Factor de escala: {scale_factor:.4f}               ║
    ╠══════════════════════════════════════════╣
    ║  Ubicación: Iquitos, Perú                ║
    ║  Lat: -3.7437°  Lon: -73.2516°           ║
    ║  Zona horaria: America/Lima              ║
    ╚══════════════════════════════════════════╝
    """
    ax.text(0.5, 0.5, summary_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='center', horizontalalignment='center',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightyellow'))
    
    plt.tight_layout()
    fig1.savefig(reports / 'oe2_solar_analysis.png', dpi=150, bbox_inches='tight')
    print(f"OK Guardado: {reports / 'oe2_solar_analysis.png'}")
    
    # --- Fig 2: Análisis de Cargadores EV ---
    fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10))
    
    # 2a: Perfil horario de carga
    ax = axes2[0, 0]
    ax.fill_between(ev_24h['hour'], ev_24h['energy_kwh'], alpha=0.4, color='green')
    ax.plot(ev_24h['hour'], ev_24h['energy_kwh'], 'o-', color='darkgreen', markersize=4)
    ax.set_title('Perfil Horario de Carga EV', fontweight='bold')
    ax.set_xlabel('Hora del día')
    ax.set_ylabel('Energía (kWh)')
    ax.set_xticks(range(0, 24, 2))
    # Marcar horas pico
    peak_hours = [7, 8, 17, 18]
    for ph in peak_hours:
        ax.axvline(x=ph, color='red', linestyle='--', alpha=0.3)
    ax.legend(['Demanda EV', 'Horas pico'])
    
    # 2b: Escenarios PE vs FC
    ax = axes2[0, 1]
    scatter = ax.scatter(scenarios['pe'], scenarios['fc'], 
                         c=scenarios['chargers_required'], 
                         cmap='RdYlGn_r', s=50, alpha=0.7)
    ax.set_title('Escenarios: Penetración vs Factor de Carga', fontweight='bold')
    ax.set_xlabel('PE (Penetración Eléctrica)')
    ax.set_ylabel('FC (Factor de Carga)')
    plt.colorbar(scatter, ax=ax, label='Cargadores requeridos')
    
    # 2c: Distribución de cargadores por escenario
    ax = axes2[1, 0]
    ax.hist(scenarios['chargers_required'], bins=20, color='green', 
            edgecolor='darkgreen', alpha=0.7)
    ax.axvline(chargers['esc_rec']['chargers_required'], color='red', 
               linestyle='--', linewidth=2, label=f"Recomendado: {chargers['esc_rec']['chargers_required']:.0f}")
    ax.set_title('Distribución de Cargadores por Escenario', fontweight='bold')
    ax.set_xlabel('Número de cargadores')
    ax.set_ylabel('Frecuencia')
    ax.legend()
    
    # 2d: Resumen numérico
    ax = axes2[1, 1]
    ax.axis('off')
    rec = chargers['esc_rec']
    summary_text = f"""
    ╔══════════════════════════════════════════╗
    ║     DIMENSIONAMIENTO CARGADORES EV       ║
    ╠══════════════════════════════════════════╣
    ║  Flota: 900 motos + 130 mototaxis        ║
    ╠══════════════════════════════════════════╣
    ║  ESCENARIO RECOMENDADO (PE={rec['pe']}, FC={rec['fc']})   ║
    ║  ─────────────────────────────────────   ║
    ║  Cargadores:       {rec['chargers_required']:.0f}                    ║
    ║  Sockets totales:  {rec['sockets_total']:.0f}                   ║
    ║  Energía diaria:   {rec['energy_day_kwh']:,.0f} kWh           ║
    ║  Sesiones pico/h:  {rec['peak_sessions_per_hour']:,.0f}                 ║
    ║  Potencia/cargador:{rec['charger_power_kw']:.1f} kW               ║
    ║  Sockets/cargador: {rec['sockets_per_charger']:.0f}                     ║
    ╚══════════════════════════════════════════╝
    """
    ax.text(0.5, 0.5, summary_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='center', horizontalalignment='center',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightgreen'))
    
    plt.tight_layout()
    fig2.savefig(reports / 'oe2_chargers_analysis.png', dpi=150, bbox_inches='tight')
    print(f"OK Guardado: {reports / 'oe2_chargers_analysis.png'}")
    
    # --- Fig 3: Análisis BESS ---
    fig3, axes3 = plt.subplots(2, 2, figsize=(14, 10))
    
    # 3a: Balance energético 24h
    ax = axes3[0, 0]
    hours = bess_24h['hour']
    ax.bar(hours - 0.2, bess_24h['pv_kwh'], width=0.4, label='Generación FV', color='orange', alpha=0.7)
    ax.bar(hours + 0.2, bess_24h['load_kwh'], width=0.4, label='Carga total', color='blue', alpha=0.7)
    ax.set_title('Balance Energético Diario: FV vs Carga', fontweight='bold')
    ax.set_xlabel('Hora del día')
    ax.set_ylabel('Energía (kWh)')
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    
    # 3b: Excedente y déficit
    ax = axes3[0, 1]
    ax.fill_between(hours, bess_24h['surplus_kwh'], alpha=0.6, color='green', label='Excedente (→BESS)')
    ax.fill_between(hours, -bess_24h['deficit_kwh'], alpha=0.6, color='red', label='Déficit (←BESS/Red)')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_title('Excedente y Déficit Horario', fontweight='bold')
    ax.set_xlabel('Hora del día')
    ax.set_ylabel('Energía (kWh)')
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    
    # 3c: Composición de carga
    ax = axes3[1, 0]
    labels = ['Mall', 'Carga EV']
    mall_total = bess_24h['mall_kwh'].sum()
    ev_total = bess_24h['ev_kwh'].sum()
    sizes = [mall_total, ev_total]
    colors = ['#ff9999', '#66b3ff']
    explode = (0, 0.05)
    ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
           shadow=True, startangle=90)
    ax.set_title('Composición de la Carga Diaria', fontweight='bold')
    
    # 3d: Resumen BESS
    ax = axes3[1, 1]
    ax.axis('off')
    surplus = bess_24h['surplus_kwh'].sum()
    deficit = bess_24h['deficit_kwh'].sum()
    summary_text = f"""
    ╔══════════════════════════════════════════╗
    ║     DIMENSIONAMIENTO BESS                ║
    ╠══════════════════════════════════════════╣
    ║  Capacidad nominal:  {bess['capacity_kwh']:,.0f} kWh          ║
    ║  Potencia nominal:   {bess['nominal_power_kw']:,.0f} kW           ║
    ║  DoD (Prof. descarga): {bess['dod']*100:.0f}%                  ║
    ║  C-Rate:             {bess['c_rate']:.2f}                    ║
    ║  Eficiencia ida/vuelta: {bess['efficiency_roundtrip']*100:.0f}%              ║
    ╠══════════════════════════════════════════╣
    ║  BALANCE DIARIO                          ║
    ║  ─────────────────────────────────────   ║
    ║  Excedente FV:       {surplus:,.0f} kWh            ║
    ║  Déficit nocturno:   {deficit:,.0f} kWh          ║
    ║  Capacidad útil:     {bess['capacity_kwh']*bess['dod']:,.0f} kWh          ║
    ╚══════════════════════════════════════════╝
    """
    ax.text(0.5, 0.5, summary_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='center', horizontalalignment='center',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightblue'))
    
    plt.tight_layout()
    fig3.savefig(reports / 'oe2_bess_analysis.png', dpi=150, bbox_inches='tight')
    print(f"OK Guardado: {reports / 'oe2_bess_analysis.png'}")
    
    # --- Fig 4: Dashboard Integrado OE2 ---
    fig4, axes4 = plt.subplots(2, 3, figsize=(16, 10))
    
    # 4a: Comparativa 24h - FV, Mall, EV
    ax = axes4[0, 0]
    ax.stackplot(hours, bess_24h['mall_kwh'], bess_24h['ev_kwh'], 
                 labels=['Mall', 'Carga EV'], colors=['#ff9999', '#66b3ff'], alpha=0.7)
    ax.plot(hours, bess_24h['pv_kwh'], 'o-', color='orange', linewidth=2, label='Generación FV')
    ax.set_title('Demanda vs Generación (24h)', fontweight='bold')
    ax.set_xlabel('Hora')
    ax.set_ylabel('kWh')
    ax.legend(loc='upper left')
    ax.set_xticks(range(0, 24, 3))
    
    # 4b: Flujo de energía BESS
    ax = axes4[0, 1]
    # Simular estado de carga del BESS
    soc = [50]  # Empezar al 50%
    capacity = bess['capacity_kwh']
    for i in range(24):
        delta = (bess_24h['surplus_kwh'].iloc[i] - bess_24h['deficit_kwh'].iloc[i]) / capacity * 100
        new_soc = np.clip(soc[-1] + delta * bess['efficiency_roundtrip'], 
                          (1-bess['dod'])*100, 100)
        soc.append(new_soc)
    ax.plot(range(25), soc, 'b-', linewidth=2, marker='o', markersize=3)
    ax.axhline(y=(1-bess['dod'])*100, color='red', linestyle='--', label=f"Mín ({(1-bess['dod'])*100:.0f}%)")
    ax.axhline(y=100, color='green', linestyle='--', label='Máx (100%)')
    ax.fill_between(range(25), (1-bess['dod'])*100, soc, alpha=0.3, color='blue')
    ax.set_title('Estado de Carga BESS (simulado)', fontweight='bold')
    ax.set_xlabel('Hora')
    ax.set_ylabel('SoC (%)')
    ax.set_ylim(0, 110)
    ax.legend()
    
    # 4c: KPIs del sistema
    ax = axes4[0, 2]
    ax.axis('off')
    total_gen = solar['annual_kwh']
    total_ev = rec['energy_day_kwh'] * 365
    total_mall = bess_24h['mall_kwh'].sum() * 365
    autoconsumo = min(total_gen, total_ev + total_mall) / total_gen * 100
    
    kpi_text = f"""
    ══════════════════════════════
       KPIs SISTEMA OE2
    ══════════════════════════════
    
    GENERACION ANUAL
       FV: {total_gen/1e6:.2f} GWh
    
    CONSUMO ANUAL
       EV: {total_ev/1e6:.2f} GWh
       Mall: {total_mall/1e6:.2f} GWh
       Total: {(total_ev+total_mall)/1e6:.2f} GWh
    
    ALMACENAMIENTO
       BESS: {bess['capacity_kwh']/1e3:.1f} MWh
    
    AUTOCONSUMO
       ~{autoconsumo:.0f}% de FV
    ══════════════════════════════
    """
    ax.text(0.5, 0.5, kpi_text, transform=ax.transAxes, fontsize=11,
            verticalalignment='center', horizontalalignment='center',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray'))
    
    # 4d: Comparativa escenarios cargadores
    ax = axes4[1, 0]
    esc_names = ['Mínimo', 'Recomendado', 'Máximo']
    charger_counts = [chargers['esc_min']['chargers_required'],
                      chargers['esc_rec']['chargers_required'],
                      chargers['esc_max']['chargers_required']]
    colors = ['lightgreen', 'green', 'darkgreen']
    bars = ax.bar(esc_names, charger_counts, color=colors, edgecolor='black')
    ax.set_title('Escenarios de Cargadores', fontweight='bold')
    ax.set_ylabel('Número de cargadores')
    for bar, val in zip(bars, charger_counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # 4e: Capacidades del sistema
    ax = axes4[1, 1]
    categories = ['FV (kWp)', 'BESS (kWh/10)', 'Cargadores']
    values = [solar['target_dc_kw'], bess['capacity_kwh']/10, rec['chargers_required']*10]
    bars = ax.barh(categories, values, color=['orange', 'blue', 'green'])
    ax.set_title('Capacidades del Sistema', fontweight='bold')
    ax.set_xlabel('Valor')
    
    # 4f: Configuración final
    ax = axes4[1, 2]
    ax.axis('off')
    config_text = f"""
    ╔════════════════════════════════════════╗
    ║    CONFIGURACIÓN FINAL OE2             ║
    ║    DISEÑO DE CARGA INTELIGENTE IQUITOS 2025    ║
    ╠════════════════════════════════════════╣
    ║                                        ║
    ║  SOLAR FV                              ║
    ║     {solar['target_dc_kw']:,.0f} kWp DC / {solar['target_ac_kw']:,.0f} kW AC    ║
    ║                                        ║
    ║  BESS                                  ║
    ║     {bess['capacity_kwh']:,.0f} kWh / {bess['nominal_power_kw']:,.0f} kW        ║
    ║                                        ║
    ║  CARGADORES                            ║
    ║     {rec['chargers_required']:.0f} unidades × {rec['sockets_per_charger']:.0f} sockets      ║
    ║     = {rec['sockets_total']:.0f} puntos de carga           ║
    ║                                        ║
    ║  FLOTA                                 ║
    ║     900 motos + 130 mototaxis          ║
    ║                                        ║
    ╚════════════════════════════════════════╝
    """
    ax.text(0.5, 0.5, config_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='center', horizontalalignment='center',
            fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))
    
    plt.tight_layout()
    fig4.savefig(reports / 'oe2_dashboard_integrado.png', dpi=150, bbox_inches='tight')
    print(f"OK Guardado: {reports / 'oe2_dashboard_integrado.png'}")
    
    # =========================================
    # 3. GENERAR REPORTE MARKDOWN
    # =========================================
    rec = chargers['esc_rec']
report_md = f"""# Reporte OE2 - Diseño de infraestructura de carga inteligente de motos y mototaxis eléctricas

## Ubicación: Iquitos, Perú
- **Latitud:** -3.7437°
- **Longitud:** -73.2516°
- **Año objetivo:** 2025

---

## 1. Dimensionamiento Solar (FV)

| Parámetro | Valor |
|-----------|-------|
| Capacidad DC | {solar['target_dc_kw']:,.2f} kWp |
| Capacidad AC | {solar['target_ac_kw']:,.2f} kW |
| Generación anual | {solar['annual_kwh']/1e6:,.2f} GWh |
| Factor de escala | {scale_factor:.4f} |

**Archivos generados:**
- `data/interim/oe2/solar/pv_generation_timeseries.csv` - Serie temporal horaria
- `data/interim/oe2/solar/pv_profile_24h.csv` - Perfil promedio 24h

---

## 2. Dimensionamiento de Cargadores EV

### Flota objetivo
- **Motos eléctricas:** 900 unidades
- **Mototaxis eléctricas:** 130 unidades

### Escenario recomendado (PE={rec['pe']}, FC={rec['fc']})

| Parámetro | Valor |
|-----------|-------|
| Cargadores requeridos | {rec['chargers_required']:.0f} |
| Sockets totales | {rec['sockets_total']:.0f} |
| Energía diaria | {rec['energy_day_kwh']:,.0f} kWh |
| Sesiones pico/hora | {rec['peak_sessions_per_hour']:,.0f} |
| Potencia/cargador | {rec['charger_power_kw']:.1f} kW |
| Duración sesión | {rec['session_minutes']:.0f} min |

**Archivos generados:**
- `data/interim/oe2/chargers/perfil_horario_carga.csv` - Perfil de carga 24h
- `data/interim/oe2/chargers/selection_pe_fc_completo.csv` - Todos los escenarios

---

## 3. Dimensionamiento BESS

| Parámetro | Valor |
|-----------|-------|
| Capacidad nominal | {bess['capacity_kwh']:,.0f} kWh |
| Potencia nominal | {bess['nominal_power_kw']:,.0f} kW |
| Profundidad de descarga (DoD) | {bess['dod']*100:.0f}% |
| C-Rate | {bess['c_rate']:.2f} |
| Eficiencia ida/vuelta | {bess['efficiency_roundtrip']*100:.0f}% |
| Criterio BESS | {bess.get('sizing_mode', 'max')} |
| Alcance BESS | {bess.get('bess_load_scope', 'total')} |
| PV disponible BESS | {bess.get('pv_available_kwh_day', 0):,.0f} kWh/dia |
| Demanda BESS | {bess.get('bess_load_kwh_day', 0):,.0f} kWh/dia |
| Excedente diario FV (BESS) | {bess['surplus_kwh_day']:,.0f} kWh |

**Archivos generados:**
- `data/interim/oe2/bess/bess_daily_balance_24h.csv` - Balance energético 24h

---

## 4. Resumen del Sistema

| Componente | Capacidad |
|------------|-----------|
| **Solar FV** | {solar['target_dc_kw']:,.0f} kWp |
| **BESS** | {bess['capacity_kwh']:,.0f} kWh / {bess['nominal_power_kw']:,.0f} kW |
| **Cargadores** | {rec['chargers_required']:.0f} ({rec['sockets_total']:.0f} sockets) |

### Energía anual estimada
- Generación FV: **{solar['annual_kwh']/1e6:,.2f} GWh**
- Demanda EV: **{rec['energy_day_kwh']*365/1e6:,.2f} GWh**

---

## 5. Visualizaciones

Las siguientes figuras fueron generadas en `reports/oe2/`:

1. `oe2_solar_analysis.png` - Análisis de generación solar
2. `oe2_chargers_analysis.png` - Análisis de cargadores EV
3. `oe2_bess_analysis.png` - Análisis de almacenamiento BESS
4. `oe2_dashboard_integrado.png` - Dashboard integrado del sistema

---

*Generado automáticamente - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    (reports / 'oe2_report.md').write_text(report_md, encoding='utf-8')
    print(f"OK Guardado: {reports / 'oe2_report.md'}")
    
    # =========================================
    # 4. MOSTRAR RESUMEN EN CONSOLA
    # =========================================
    print("\n" + "="*60)
    print("        RESUMEN OE2 - DIMENSIONAMIENTO COMPLETADO")
    print("="*60)
    print("\nSOLAR FV:")
    print(f"   Capacidad: {solar['target_dc_kw']:,.0f} kWp DC / {solar['target_ac_kw']:,.0f} kW AC")
    print(f"   Generación anual: {solar['annual_kwh']/1e6:,.2f} GWh")
    
    print("\nCARGADORES EV:")
    print(f"   Cargadores: {rec['chargers_required']:.0f} unidades")
    print(f"   Sockets: {rec['sockets_total']:.0f} puntos de carga")
    print(f"   Energía diaria: {rec['energy_day_kwh']:,.0f} kWh")
    
    print("\nBESS:")
    print(f"   Capacidad: {bess['capacity_kwh']:,.0f} kWh")
    print(f"   Potencia: {bess['nominal_power_kw']:,.0f} kW")
    print(f"   DoD: {bess['dod']*100:.0f}% | Eficiencia: {bess['efficiency_roundtrip']*100:.0f}%")
    
    print("\n" + "="*60)
    print("ARCHIVOS GENERADOS:")
    print("="*60)
    for f in reports.glob('*'):
        print(f"  - {f.relative_to(base)}")
    
    plt.show()

if __name__ == "__main__":
    main()
