# Reporte OE2 - Dimensionamiento de Infraestructura

## Ubicación: Iquitos, Perú
- **Latitud:** -3.7437°
- **Longitud:** -73.2516°
- **Año objetivo:** 2025

---

## 1. Dimensionamiento Solar (FV)

| Parámetro | Valor |
|-----------|-------|
| Capacidad DC | 4,162.00 kWp |
| Capacidad AC | 3,201.20 kW |
| Generación anual | 8.04 GWh |
| Factor de escala | 0.4939 |

**Archivos generados:**
- `data/interim/oe2/solar/pv_generation_timeseries.csv` - Serie temporal horaria
- `data/interim/oe2/solar/pv_profile_24h.csv` - Perfil promedio 24h

---

## 2. Dimensionamiento de Cargadores EV

### Flota objetivo
- **Motos eléctricas:** 900 unidades
- **Mototaxis eléctricas:** 130 unidades

### Escenario recomendado (PE=1.0, FC=1.0)

| Parámetro | Valor |
|-----------|-------|
| Cargadores requeridos | 30 |
| Sockets totales | 120 |
| Energía diaria | 912 kWh |
| Sesiones pico/hora | 258 |
| Potencia/cargador | 2.1 kW |
| Duración sesión | 25 min |

**Archivos generados:**
- `data/interim/oe2/chargers/perfil_horario_carga.csv` - Perfil de carga 24h
- `data/interim/oe2/chargers/selection_pe_fc_completo.csv` - Todos los escenarios

---

## 3. Dimensionamiento BESS

| Parámetro | Valor |
|-----------|-------|
| Capacidad nominal | 7,410 kWh |
| Potencia nominal | 3,705 kW |
| Profundidad de descarga (DoD) | 90% |
| C-Rate | 0.50 |
| Eficiencia ida/vuelta | 95% |
| Criterio BESS | surplus_only |
| Alcance BESS | total |
| PV disponible BESS | 21,978 kWh/dia |
| Demanda BESS | 34,799 kWh/dia |
| Excedente diario FV (BESS) | 6,328 kWh |

**Archivos generados:**
- `data/interim/oe2/bess/bess_daily_balance_24h.csv` - Balance energético 24h

---

## 4. Resumen del Sistema

| Componente | Capacidad |
|------------|-----------|
| **Solar FV** | 4,162 kWp |
| **BESS** | 7,410 kWh / 3,705 kW |
| **Cargadores** | 30 (120 sockets) |

### Energía anual estimada
- Generación FV: **8.04 GWh**
- Demanda EV: **0.33 GWh**

---

## 5. Visualizaciones

Las siguientes figuras fueron generadas en `reports/oe2/`:

1. `oe2_solar_analysis.png` - Análisis de generación solar
2. `oe2_chargers_analysis.png` - Análisis de cargadores EV
3. `oe2_bess_analysis.png` - Análisis de almacenamiento BESS
4. `oe2_dashboard_integrado.png` - Dashboard integrado del sistema

---

*Generado automáticamente - 2025-12-23 03:08:12*
