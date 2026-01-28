"""
Análisis de Demanda de Carga Sin Control: Motos vs Mototaxis
Reporte de carga horaria, picos, utilización y patrones energéticos
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configuración
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# Paths
BASE_DIR = Path("d:\\diseñopvbesscar")
DATA_DIR = BASE_DIR / "data" / "interim" / "oe2" / "chargers"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

print("=" * 90)
print("ANÁLISIS DE CARGA SIN CONTROL: MOTOS vs MOTOTAXIS")
print("=" * 90)

# ============================================================================
# 1. CARGAR CONFIGURACIÓN DE CHARGERS
# ============================================================================
print("\n[1/5] Cargando configuración de chargers...")

with open(DATA_DIR / "individual_chargers.json", "r") as f:
    chargers: list[dict[str, Any]] = json.load(f)

# Clasificar chargers
motos_chargers = [c for c in chargers if c["charger_type"] == "moto"]
mototaxis_chargers = [c for c in chargers if c["charger_type"] == "moto_taxi"]

print(f"✓ Motos: {len(motos_chargers)} cargadores × 4 sockets = {len(motos_chargers)*4} sockets")
print(f"✓ Mototaxis: {len(mototaxis_chargers)} cargadores × 4 sockets = {len(mototaxis_chargers)*4} sockets")

# ============================================================================
# 2. CARGAR PERFILES HORARIOS DE DEMANDA
# ============================================================================
print("\n[2/5] Cargando perfiles horarios de demanda...")

# Cargar perfil general (todos los tomas)
perfil_15min = pd.read_csv(DATA_DIR / "perfil_horario_carga.csv")
print(f"✓ Perfil de 15 minutos cargado: {len(perfil_15min)} filas × {len(perfil_15min.columns)} columnas")

# Para datos horarios usamos chargers_hourly_profiles.csv (112 motos + 16 mototaxis = 128)
# Pero verificamos estructura de perfil_15min primero
print(f"  Columnas: {list(perfil_15min.columns[:10])}...")

# Extraer demanda total por hora
perfil_15min['hour'] = perfil_15min['hour_of_day']
perfil_horaria = perfil_15min.groupby('hour_of_day').agg({
    'total_demand_kw': ['mean', 'std', 'min', 'max', 'sum']
}).reset_index()
perfil_horaria.columns = ['hour', 'demand_mean', 'demand_std', 'demand_min', 'demand_max', 'demand_sum']

print(f"✓ Demanda horaria agregada en {len(perfil_horaria)} horas")

# ============================================================================
# 3. CARGAR PERFILES INDIVIDUALES DE CHARGERS (horarios)
# ============================================================================
print("\n[3/5] Cargando perfiles individuales horarios...")

chargers_hourly = pd.read_csv(DATA_DIR / "chargers_hourly_profiles.csv")
print(f"✓ Perfiles horarios: {len(chargers_hourly)} horas × {len(chargers_hourly.columns)-1} chargers")

# Columnas de motos (112) y mototaxis (16)
moto_cols = [col for col in chargers_hourly.columns if 'MOTO_CH_' in col and 'TAXI' not in col]
taxi_cols = [col for col in chargers_hourly.columns if 'MOTO_TAXI_CH_' in col]

print(f"✓ Columnas encontradas:")
print(f"  - Motos: {len(moto_cols)} (esperadas: 112)")
print(f"  - Mototaxis: {len(taxi_cols)} (esperadas: 16)")

# ============================================================================
# 4. ANÁLISIS SEPARADO: MOTOS vs MOTOTAXIS
# ============================================================================
print("\n[4/5] Análisis de demanda horaria...")

# Demanda por hora y tipo
chargers_hourly['motos_total_kw'] = chargers_hourly[moto_cols].sum(axis=1)
chargers_hourly['taxis_total_kw'] = chargers_hourly[taxi_cols].sum(axis=1)
chargers_hourly['total_kw'] = chargers_hourly['motos_total_kw'] + chargers_hourly['taxis_total_kw']
chargers_hourly['hour'] = chargers_hourly['hour']

# Estadísticas anuales (asumiendo 365 días × 24 horas = 8760 horas teóricas)
# Pero chargers_hourly tiene solo 24 horas (perfil diario típico)
horas_por_año = 365
horas_perfil = len(chargers_hourly)

# Escalar energías anuales
energia_motos_anual_kwh: float = float(chargers_hourly['motos_total_kw'].sum()) * horas_por_año
energia_taxis_anual_kwh: float = float(chargers_hourly['taxis_total_kw'].sum()) * horas_por_año
energia_total_anual_kwh: float = float(chargers_hourly['total_kw'].sum()) * horas_por_año

# Potencia promedio
potencia_motos_prom: float = float(chargers_hourly['motos_total_kw'].mean())
potencia_taxis_prom: float = float(chargers_hourly['taxis_total_kw'].mean())
potencia_total_prom: float = float(chargers_hourly['total_kw'].mean())

# Picos
potencia_motos_pico: float = float(chargers_hourly['motos_total_kw'].max())
potencia_taxis_pico: float = float(chargers_hourly['taxis_total_kw'].max())
potencia_total_pico: float = float(chargers_hourly['total_kw'].max())

# Horas pico
hora_pico_motos: int = int(chargers_hourly.loc[chargers_hourly['motos_total_kw'].idxmax(), 'hour'])  # type: ignore
hora_pico_taxis: int = int(chargers_hourly.loc[chargers_hourly['taxis_total_kw'].idxmax(), 'hour'])  # type: ignore

# Demanda promedio por socket
sockets_motos: int = len(motos_chargers) * 4  # 112
sockets_taxis: int = len(mototaxis_chargers) * 4  # 16

demanda_per_socket_motos: float = float(chargers_hourly['motos_total_kw'].mean()) / sockets_motos
demanda_per_socket_taxis: float = float(chargers_hourly['taxis_total_kw'].mean()) / sockets_taxis

print(f"\n📊 ESTADÍSTICAS ANUALES (extrapoladas de perfil 24h):")
print(f"\n  MOTOS:")
print(f"    • Chargers: {len(motos_chargers)} (4 sockets c/u = {sockets_motos} sockets)")
print(f"    • Energía anual: {energia_motos_anual_kwh:,.0f} kWh")
print(f"    • Potencia promedio: {potencia_motos_prom:.2f} kW")
print(f"    • Potencia pico (hora {hora_pico_motos}): {potencia_motos_pico:.2f} kW")
print(f"    • Demanda por socket: {demanda_per_socket_motos:.4f} kW/socket")
print(f"    • Factor de utilización: {(demanda_per_socket_motos / 2.0)*100:.1f}%")

print(f"\n  MOTOTAXIS:")
print(f"    • Chargers: {len(mototaxis_chargers)} (4 sockets c/u = {sockets_taxis} sockets)")
print(f"    • Energía anual: {energia_taxis_anual_kwh:,.0f} kWh")
print(f"    • Potencia promedio: {potencia_taxis_prom:.2f} kW")
print(f"    • Potencia pico (hora {hora_pico_taxis}): {potencia_taxis_pico:.2f} kW")
print(f"    • Demanda por socket: {demanda_per_socket_taxis:.4f} kW/socket")
print(f"    • Factor de utilización: {(demanda_per_socket_taxis / 3.0)*100:.1f}%")

print(f"\n  TOTAL SISTEMA:")
print(f"    • Chargers: {len(chargers)} (128 sockets)")
print(f"    • Energía anual: {energia_total_anual_kwh:,.0f} kWh")
print(f"    • Potencia promedio: {potencia_total_prom:.2f} kW")
print(f"    • Potencia pico: {potencia_total_pico:.2f} kW")

# ============================================================================
# 5. GENERAR REPORTE MARKDOWN
# ============================================================================
print("\n[5/5] Generando reporte...")

reporte_md = f"""# Reporte de Carga Sin Control: Motos vs Mototaxis
**Fecha de generación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Análisis:** Demanda horaria sin control inteligente (baseline uncontrolled)

---

## 📊 Resumen Ejecutivo

### Infraestructura
- **Motos:** {len(motos_chargers)} cargadores × 4 sockets = **{sockets_motos} sockets** @ 2 kW/socket
- **Mototaxis:** {len(mototaxis_chargers)} cargadores × 4 sockets = **{sockets_taxis} sockets** @ 3 kW/socket
- **Sistema total:** {len(chargers)} cargadores, 128 sockets, 272 kW de capacidad instalada

### Demanda Anual (Proyectada desde perfil 24h)

#### Motos
| Métrica | Valor |
|---------|-------|
| Energía anual | {energia_motos_anual_kwh:,.0f} kWh |
| Potencia promedio | {potencia_motos_prom:.2f} kW |
| Potencia pico | {potencia_motos_pico:.2f} kW (hora {hora_pico_motos:02d}) |
| Demanda por socket | {demanda_per_socket_motos:.4f} kW/socket |
| Factor de utilización | {(demanda_per_socket_motos / 2.0)*100:.1f}% (nominal 2 kW) |
| % del total sistema | {(energia_motos_anual_kwh/energia_total_anual_kwh)*100:.1f}% |

#### Mototaxis
| Métrica | Valor |
|---------|-------|
| Energía anual | {energia_taxis_anual_kwh:,.0f} kWh |
| Potencia promedio | {potencia_taxis_prom:.2f} kW |
| Potencia pico | {potencia_taxis_pico:.2f} kW (hora {hora_pico_taxis:02d}) |
| Demanda por socket | {demanda_per_socket_taxis:.4f} kW/socket |
| Factor de utilización | {(demanda_per_socket_taxis / 3.0)*100:.1f}% (nominal 3 kW) |
| % del total sistema | {(energia_taxis_anual_kwh/energia_total_anual_kwh)*100:.1f}% |

#### Sistema Total
| Métrica | Valor |
|---------|-------|
| Energía anual | {energia_total_anual_kwh:,.0f} kWh |
| Potencia promedio | {potencia_total_prom:.2f} kW |
| Potencia pico | {potencia_total_pico:.2f} kW |
| Factor de utilización promedio | {(potencia_total_prom/272)*100:.1f}% de 272 kW |

---

## 📈 Análisis Horario

### Demanda Máxima por Hora
"""

# Tabla horaria
for idx, row in chargers_hourly.iterrows():
    hora_val: int = int(row['hour'])  # type: ignore
    motos_val: float = float(row['motos_total_kw'])
    taxis_val: float = float(row['taxis_total_kw'])
    total_val: float = float(row['total_kw'])
    reporte_md += f"\n**Hora {hora_val:02d}:00**\n"
    reporte_md += f"- Motos: {motos_val:.2f} kW ({(motos_val/2.0/sockets_motos)*100:.1f}% utilización)\n"
    reporte_md += f"- Taxis: {taxis_val:.2f} kW ({(taxis_val/3.0/sockets_taxis)*100:.1f}% utilización)\n"
    reporte_md += f"- Total: {total_val:.2f} kW ({(total_val/272)*100:.1f}% de 272 kW)\n"

reporte_md += f"""

---

## 🔍 Hallazgos Clave

### Caracterización de Demanda

1. **Diferenciación Motos vs Mototaxis:**
   - Las **motos** representan **{(energia_motos_anual_kwh/energia_total_anual_kwh)*100:.1f}%** de la energía total
   - Los **mototaxis** representan **{(energia_taxis_anual_kwh/energia_total_anual_kwh)*100:.1f}%** de la energía total
   - Aunque motos tenemos 7× más sockets ({sockets_motos} vs {sockets_taxis}), la demanda es solo {energia_motos_anual_kwh/energia_taxis_anual_kwh:.1f}× mayor
   - **Conclusión:** Los mototaxis tienen factor de utilización {(demanda_per_socket_taxis/demanda_per_socket_motos):.1f}× superior

2. **Eficiencia de Sockets:**
   - Demanda promedio por socket (motos): {demanda_per_socket_motos:.4f} kW = **{(demanda_per_socket_motos / 2.0)*100:.1f}%** utilización
   - Demanda promedio por socket (taxis): {demanda_per_socket_taxis:.4f} kW = **{(demanda_per_socket_taxis / 3.0)*100:.1f}%** utilización
   - Los mototaxis operan con ocupación **{(demanda_per_socket_taxis/demanda_per_socket_motos):.2f}×** más alta

3. **Picos de Demanda:**
   - Hora pico motos: **{int(hora_pico_motos)}:00** con {potencia_motos_pico:.2f} kW
   - Hora pico taxis: **{int(hora_pico_taxis)}:00** con {potencia_taxis_pico:.2f} kW
   - Hora pico sistema: **{chargers_hourly.loc[chargers_hourly['total_kw'].idxmax(), 'hour']:.0f}:00** con {potencia_total_pico:.2f} kW

4. **Implicaciones para Generación Solar:**
   - Potencia media del sistema: {potencia_total_prom:.2f} kW
   - Solar fotovoltaica instalada: 4,050 kWp (PVGIS Iquitos)
   - Factor de cobertura: {(272/4050)*100:.2f}% (carga vs PV)
   - Potencial de autoconsumo solar: **Muy alto** (PV >> Carga)

---

## ⚡ Consideraciones para Control Inteligente (RL)

### Oportunidades de Optimización

1. **Priorización Horaria:**
   - Cargar mototaxis en horas pico solar (10-15h) - mejor autoconsunción
   - Diferir carga de motos a horas valle - menor congestión

2. **Manejo Diferenciado por Tipo:**
   - Motos: Baja densidad de ocupación → mejor flexibilidad de carga
   - Taxis: Alta densidad → requieren respuesta más rápida

3. **Capacidad BESS (4,520 kWh / 2,712 kW):**
   - Puede almacenar energía solar de día
   - Servir demanda de noche (motos + taxis)
   - Duración máxima: {4520/potencia_total_prom:.1f} horas @ demanda promedio

4. **Reducción de CO₂:**
   - Factor grid Iquitos: 0.4521 kg CO₂/kWh (térmica)
   - Baseline anual: {energia_total_anual_kwh*0.4521/1000:.0f} t CO₂/año
   - Objetivo RL: Minimizar importación grid → reducir emisiones

---

## 📋 Datos Brutos Horarios

"""

# Tabla de datos
reporte_md += "\n| Hora | Motos (kW) | Taxis (kW) | Total (kW) | % Sistema |\n"
reporte_md += "|------|-----------|-----------|-----------|----------|\n"

for idx, row in chargers_hourly.iterrows():
    h_val: int = int(row['hour'])  # type: ignore
    m_val: float = float(row['motos_total_kw'])
    t_val: float = float(row['taxis_total_kw'])
    tot_val: float = float(row['total_kw'])
    pct_val: float = (tot_val / 272.0) * 100.0
    reporte_md += f"| {h_val:02d}:00 | {m_val:>9.2f} | {t_val:>9.2f} | {tot_val:>9.2f} | {pct_val:>8.1f}% |\n"

reporte_md += f"""

---

## 🎯 Métricas de Referencia (Baseline Sin Control)

```
MOTOS:
  Energía: {energia_motos_anual_kwh:,.0f} kWh/año
  Potencia prom: {potencia_motos_prom:.2f} kW
  Pico: {potencia_motos_pico:.2f} kW
  CO₂: {energia_motos_anual_kwh*0.4521/1000:.0f} t/año (sin optimización)

MOTOTAXIS:
  Energía: {energia_taxis_anual_kwh:,.0f} kWh/año
  Potencia prom: {potencia_taxis_prom:.2f} kW
  Pico: {potencia_taxis_pico:.2f} kW
  CO₂: {energia_taxis_anual_kwh*0.4521/1000:.0f} t/año (sin optimización)

TOTAL:
  Energía: {energia_total_anual_kwh:,.0f} kWh/año
  Potencia prom: {potencia_total_prom:.2f} kW
  Pico: {potencia_total_pico:.2f} kW
  CO₂: {energia_total_anual_kwh*0.4521/1000:.0f} t/año (sin optimización)
```

**Estos valores servirán como baseline para comparar con SAC, PPO, A2C.**

---

## 📌 Conclusiones

1. **Motos y taxis tienen patrones muy diferentes:**
   - Motos: Factor de utilización **bajo** ({(demanda_per_socket_motos / 2.0)*100:.1f}%) → flexible
   - Taxis: Factor de utilización **alto** ({(demanda_per_socket_taxis / 3.0)*100:.1f}%) → demanda crítica

2. **Sistema está subdimensionado en taxis:**
   - Solo {sockets_taxis} sockets para vehículos de alta demanda
   - Mototaxis requieren priorización en despacho BESS-EV

3. **Gran potencial de solar:**
   - PV = 4,050 kWp >> Carga = 272 kW promedio
   - Autoconsumo solar es el principal objetivo (después de CO₂)

4. **Control RL debe diferenciar:**
   - Garantizar mototaxis (crítico) vs diferir motos (flexible)
   - Cargar ambos desde PV de día cuando sea posible
   - Usar BESS para noches

---

**Generado automáticamente - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
"""

# Guardar reporte
reporte_path = REPORTS_DIR / "ANALISIS_CARGA_SIN_CONTROL_BASELINE.md"
with open(reporte_path, "w", encoding="utf-8") as f:
    f.write(reporte_md)

print(f"\n✓ Reporte guardado: {reporte_path}")

# ============================================================================
# GRÁFICOS
# ============================================================================
print("\nGenerando gráficos...")

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Gráfico 1: Demanda horaria
ax = axes[0, 0]
ax.bar(chargers_hourly['hour'] - 0.2, chargers_hourly['motos_total_kw'],
       width=0.4, label='Motos', alpha=0.8, color='#3498db')
ax.bar(chargers_hourly['hour'] + 0.2, chargers_hourly['taxis_total_kw'],
       width=0.4, label='Mototaxis', alpha=0.8, color='#e74c3c')
ax.axhline(y=potencia_total_prom, color='green', linestyle='--', label='Promedio', linewidth=2)
ax.set_xlabel('Hora del día')
ax.set_ylabel('Potencia (kW)')
ax.set_title('Demanda Horaria Sin Control: Motos vs Mototaxis')
ax.legend()
ax.grid(True, alpha=0.3)

# Gráfico 2: % del sistema
ax = axes[0, 1]
sizes = [energia_motos_anual_kwh, energia_taxis_anual_kwh]
labels = [f'Motos\n{energia_motos_anual_kwh/1e6:.1f} MWh/año\n({energia_motos_anual_kwh/energia_total_anual_kwh*100:.1f}%)',
          f'Mototaxis\n{energia_taxis_anual_kwh/1e6:.1f} MWh/año\n({energia_taxis_anual_kwh/energia_total_anual_kwh*100:.1f}%)']
colors = ['#3498db', '#e74c3c']
ax.pie(sizes, labels=labels, autopct='', colors=colors, startangle=90)
ax.set_title('Distribución de Energía Anual')

# Gráfico 3: Utilización de sockets
ax = axes[1, 0]
utilization = [demanda_per_socket_motos/2.0*100, demanda_per_socket_taxis/3.0*100]
types = ['Motos\n(2 kW/socket)', 'Mototaxis\n(3 kW/socket)']
bars = ax.bar(types, utilization, color=['#3498db', '#e74c3c'], alpha=0.8, edgecolor='black')
ax.set_ylabel('Factor de Utilización (%)')
ax.set_title('Ocupación Promedio de Sockets')
ax.set_ylim([0, 100])
for bar, val in zip(bars, utilization):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

# Gráfico 4: Comparativa de potencias
ax = axes[1, 1]
x_pos = np.arange(3)
metricas = [potencia_motos_prom, potencia_taxis_prom, potencia_total_prom]
labels_power = ['Motos\n(Prom)', 'Taxis\n(Prom)', 'Total\n(Prom)']
bars = ax.bar(x_pos, metricas, color=['#3498db', '#e74c3c', '#2ecc71'], alpha=0.8, edgecolor='black')

# Agregar línea de picos
metricas_pico = [potencia_motos_pico, potencia_taxis_pico, potencia_total_pico]
ax.plot(x_pos, metricas_pico, 'ro--', linewidth=2, markersize=8, label='Pico')

ax.set_ylabel('Potencia (kW)')
ax.set_title('Potencia Promedio vs Pico')
ax.set_xticks(x_pos)
ax.set_xticklabels(labels_power)
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

for bar, val in zip(bars, metricas):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.0f}kW', ha='center', va='bottom', fontweight='bold', fontsize=9)

plt.tight_layout()
plt.savefig(REPORTS_DIR / "ANALISIS_CARGA_MOTOS_TAXIS_GRAFICOS.png", dpi=150, bbox_inches='tight')
print(f"✓ Gráficos guardados: ANALISIS_CARGA_MOTOS_TAXIS_GRAFICOS.png")

# ============================================================================
# EXPORTAR DATOS PROCESADOS
# ============================================================================
print("\nExportando datos procesados...")

# CSV con demanda horaria
export_df = chargers_hourly[['hour', 'motos_total_kw', 'taxis_total_kw', 'total_kw']].copy()
export_df.to_csv(REPORTS_DIR / "demanda_horaria_motos_taxis.csv", index=False)
print(f"✓ Datos horarios: demanda_horaria_motos_taxis.csv")

# JSON con resumen
resumen = {
    "fecha": datetime.now().isoformat(),
    "infraestructura": {
        "motos": {
            "chargers": len(motos_chargers),
            "sockets": sockets_motos,
            "potencia_nominal_kw": len(motos_chargers) * 2.0
        },
        "mototaxis": {
            "chargers": len(mototaxis_chargers),
            "sockets": sockets_taxis,
            "potencia_nominal_kw": len(mototaxis_chargers) * 3.0
        },
        "total": {
            "chargers": len(chargers),
            "sockets": 128,
            "potencia_nominal_kw": 272.0
        }
    },
    "energia_anual_kwh": {
        "motos": round(energia_motos_anual_kwh, 0),
        "mototaxis": round(energia_taxis_anual_kwh, 0),
        "total": round(energia_total_anual_kwh, 0),
        "pct_motos": round(energia_motos_anual_kwh/energia_total_anual_kwh*100, 1),
        "pct_taxis": round(energia_taxis_anual_kwh/energia_total_anual_kwh*100, 1)
    },
    "potencia_kw": {
        "motos_promedio": round(potencia_motos_prom, 2),
        "motos_pico": round(potencia_motos_pico, 2),
        "motos_hora_pico": int(hora_pico_motos),
        "taxis_promedio": round(potencia_taxis_prom, 2),
        "taxis_pico": round(potencia_taxis_pico, 2),
        "taxis_hora_pico": int(hora_pico_taxis),
        "total_promedio": round(potencia_total_prom, 2),
        "total_pico": round(potencia_total_pico, 2)
    },
    "utilizacion": {
        "motos_pct": round((demanda_per_socket_motos / 2.0)*100, 1),
        "taxis_pct": round((demanda_per_socket_taxis / 3.0)*100, 1),
        "sistema_pct": round((potencia_total_prom/272)*100, 1)
    },
    "co2_kg_anual_baseline": {
        "motos": round(energia_motos_anual_kwh * 0.4521, 0),
        "taxis": round(energia_taxis_anual_kwh * 0.4521, 0),
        "total": round(energia_total_anual_kwh * 0.4521, 0)
    }
}

with open(REPORTS_DIR / "resumen_carga_baseline.json", "w", encoding="utf-8") as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)

print(f"✓ Resumen JSON: resumen_carga_baseline.json")

print("\n" + "=" * 90)
print("✅ ANÁLISIS COMPLETADO")
print("=" * 90)
print(f"\nArchivos generados:")
print(f"  1. {reporte_path.name}")
print(f"  2. ANALISIS_CARGA_MOTOS_TAXIS_GRAFICOS.png")
print(f"  3. demanda_horaria_motos_taxis.csv")
print(f"  4. resumen_carga_baseline.json")
