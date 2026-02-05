# 🚀 BESS DATASET 2024 - QUICK START

## Estado Actual
✅ **Dataset BESS horario 2024 generado y listo para usar**

## Ubicación del Archivo
```
data/oe2/bess/bess_hourly_dataset_2024.csv
```

## Características
- **Período**: 2024-01-01 00:00 a 2024-12-30 23:00 (UTC-5)
- **Resolución**: Horaria (8,760 timesteps = 365 días × 24h)
- **Columnas**: 11 (flujos energéticos + BESS SOC)
- **Tamaño**: 1.1 MB
- **Índice**: DatetimeIndex (timezone-aware, America/Lima)

## Carga Rápida en Python

```python
import pandas as pd

# Cargar dataset
df = pd.read_csv('data/oe2/bess/bess_hourly_dataset_2024.csv',
                  index_col=0, parse_dates=True)

# Verificar estructura
print(df.shape)        # (8760, 11)
print(df.head())
print(df.index[0])     # 2024-01-01 00:00:00-05:00
```

## Columnas y su Significado

| Columna | Descripción | Rango |
|---------|-------------|-------|
| `pv_kwh` | Generación solar (kWh/h) | 0 - 2,887 |
| `ev_kwh` | Demanda carga EV (kWh/h) | 27 - 271 |
| `mall_kwh` | Demanda mall (kWh/h) | 0 - 2,763 |
| `pv_to_ev_kwh` | Solar → EV directo | 0 - 267 |
| `pv_to_bess_kwh` | Solar → BESS carga | 0 - 1,272 |
| `pv_to_mall_kwh` | Solar → Mall | 0 - 2,824 |
| `grid_to_ev_kwh` | Red → EV | 0 - 239 |
| `grid_to_mall_kwh` | Red → Mall | 0 - 2,706 |
| `bess_charge_kwh` | BESS cargando | 0 - 1,272 |
| `bess_discharge_kwh` | BESS descargando | 0 - 270 |
| `soc_percent` | Estado carga BESS | 50 - 100% |

## Energía Anual (Resumen)

```
Generación:
  • Solar PV:        8,292,514 kWh

Demanda:
  • EV:              1,024,818 kWh
  • Mall:            12,368,653 kWh
  • Total:           13,393,471 kWh

Autosuficiencia:
  • Solar cubre:     61.9%
  • Red requerida:   38.1%
```

## Análisis Rápido

```python
# Estadísticas
print(df.describe())

# Máximo/mínimo por hora
print(f"SOC mín: {df['soc_percent'].min()}%")
print(f"SOC máx: {df['soc_percent'].max()}%")
print(f"SOC prom: {df['soc_percent'].mean():.1f}%")

# Energía anual
pv_annual = df['pv_kwh'].sum()
grid_annual = df['grid_to_ev_kwh'].sum() + df['grid_to_mall_kwh'].sum()
print(f"\nPV anual: {pv_annual:,.0f} kWh")
print(f"Red anual: {grid_annual:,.0f} kWh")

# Autosuficiencia
autosuf = 100 * (1 - grid_annual / (df['ev_kwh'].sum() + df['mall_kwh'].sum()))
print(f"Autosuficiencia: {autosuf:.1f}%")
```

## Integración con OE3

```python
# 1. Cargar dataset
bess_dataset = pd.read_csv('data/oe2/bess/bess_hourly_dataset_2024.csv',
                           index_col=0, parse_dates=True)

# 2. Usar como baseline para comparación
baseline_co2_kg = (bess_dataset['grid_to_ev_kwh'].sum() + 
                   bess_dataset['grid_to_mall_kwh'].sum()) * 0.4521

# 3. Entrenar agentes y calcular mejora
# agent_co2 = ... (resultado del agente RL)
# improvement = (baseline_co2_kg - agent_co2) / baseline_co2_kg * 100
```

## Parámetros BESS (Usados en Simulación)

- **Capacidad**: 4,520 kWh
- **Potencia**: 1,644 kW (carga/descarga)
- **DoD**: 80% (SOC 20-100%)
- **Eficiencia**: 95% round-trip

## Métrica de Éxito para RL Agents

```
Baseline BESS (este dataset):
  • Autosuficiencia: 61.9%
  • CO2 grid: 3,175,514 kg/año

Objetivo RL agents:
  • Autosuficiencia: 75%+
  • CO2 reduction: 20-30%
```

## Limitaciones Conocidas

⚠️ **No incluye**:
- Control dinámico adaptativo (usa prioridad fija)
- Incertidumbre en demanda/PV
- Degradación de BESS
- Costos de operación
- Restricciones de red (voltage, frecuencia)

## Próximos Pasos

1. ✅ Dataset generado
2. → Integrar en CityLearn v2
3. → Entrenar agentes SAC/PPO/A2C
4. → Comparar vs baseline
5. → Publicar resultados

## Contacto & Documentación

Ver `BESS_DATASET_2024_SUMMARY.md` para documentación técnica completa.

---
**Generado**: 2026-02-04  
**Estado**: ✅ LISTO PARA PRODUCCIÓN  
**Verificado**: Todas validaciones pasadas (8,760 filas, índice único, sin NaN)
