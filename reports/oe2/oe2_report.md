# Reporte OE2 - Dimensionamiento de Infraestructura

## Ubicación: Mall de Iquitos, Perú
- **Latitud:** -3.75°
- **Longitud:** -73.25°
- **Altitud:** 104 m
- **Año objetivo:** 2025
- **Timezone:** America/Lima

---

## 1. Dimensionamiento Solar (FV)

| Parámetro | Valor |
|-----------|-------|
| **Módulo** | SunPower SPR-315E (315 W) |
| **Inversor** | Sungrow SG2500U (550V) |
| **Área total disponible** | 20,637 m² |
| **Factor de diseño** | 65% |
| **Área útil** | 13,414 m² |
| **Número de módulos** | 8,224 unidades |
| **Capacidad DC instalada** | **2,591.15 kWp** |
| **Capacidad AC máxima** | **2,500 kW** |
| **Generación anual** | **3,299 MWh** |
| **Generación diaria promedio** | 9,040 kWh/día |
| **Irradiación específica** | 1,273 kWh/kWp/año |
| **Performance Ratio** | **76.5%** |

**Archivos generados:**
- `data/interim/oe2/solar/solar_results.json` - Resultados completos
- `data/interim/oe2/solar/pv_generation_timeseries.csv` - Serie temporal horaria (8,760 h)
- `data/interim/oe2/solar/pv_candidates_modules.csv` - Módulos candidatos
- `data/interim/oe2/solar/pv_candidates_inverters.csv` - Inversores candidatos

---

## 2. Dimensionamiento de Cargadores EV

### Flota objetivo
- **Motos eléctricas:** 900 unidades
- **Mototaxis eléctricas:** 130 unidades
- **Total flota:** 1,030 vehículos

### Escenario recomendado (PE=100%, FC=100%)

| Parámetro | Valor |
|-----------|-------|
| **Cargadores requeridos** | **33 unidades** |
| **Sockets totales** | **129 tomas** |
| **Sockets por cargador** | 4 |
| **Tipo de carga** | Modo 3 (IEC 61851) |
| **Potencia motos** | 2.0 kW |
| **Potencia mototaxis** | 3.0 kW |
| **Potencia objetivo** | 310-340 kW |
| **Energía diaria EV** | **567 kWh** |
| **Vehículos efectivos/día** | **927** (810 motos + 117 mototaxis) |
| **Potencia pico perfil** | **283 kW** |
| **Sesiones pico/hora (capacidad)** | 258 |
| **Sesiones/día (capacidad)** | 3,354 |
| **Duración sesión** | 30 min |
| **Horario mall** | 9:00 - 22:00 |
| **Horas pico** | 18:00 - 22:00 |
| **Utilización** | 85% |

**Archivos generados:**
- `data/interim/oe2/chargers/chargers_results.json` - Resultados completos
- `data/interim/oe2/chargers/perfil_horario_carga.csv` - Perfil de carga 24h

---

## 3. Dimensionamiento BESS

| Parámetro | Valor |
|-----------|-------|
| **Capacidad nominal** | **740 kWh** |
| **Potencia nominal** | **370 kW** |
| **C-Rate** | 0.50 |
| **Profundidad de descarga (DoD)** | **90%** |
| **SOC mínimo** | 10% |
| **SOC máximo** | 100% |
| **Eficiencia roundtrip** | **95%** |
| **Autonomía** | **4 horas** |
| **Autosuficiencia** | **25.3%** |
| **Ciclos por día** | 0.79 |

**Balance energético diario:**
- Demanda Mall: 33,885 kWh/día
- Demanda EV: 567 kWh/día
- **Demanda Total:** **34,452 kWh/día**
- Generación PV: 9,016 kWh/día
- Déficit: 25,436 kWh/día
- Importación de red: 25,436 kWh/día
- Exportación a red: 222 kWh/día

**Archivos generados:**
- `data/interim/oe2/bess/bess_results.json` - Resultados completos
- `data/interim/oe2/bess/bess_simulation_hourly.csv` - Simulación horaria

---

## 4. Resumen del Sistema

| Componente | Capacidad | Especificación |
|------------|-----------|----------------|
| **Solar FV** | **2,591 kWp** | 8,224 módulos SunPower SPR-315E |
| **Inversor** | **2,500 kW AC** | Sungrow SG2500U (550V) |
| **BESS** | **740 kWh / 370 kW** | DoD 90%, eficiencia 95%, autonomía 4h |
| **Cargadores** | **33 unidades (129 sockets)** | Modo 3, 2-3 kW por socket |

### Energía anual estimada
- **Generación FV:** 3,299 MWh/año
- **Demanda EV:** 207 MWh/año (567 kWh/día × 365)
- **Demanda Mall:** 12,368 MWh/año (33,885 kWh/día × 365)
- **Autosuficiencia:** 25.3%

---

## 5. Visualizaciones

Ver `reports/oe2/REPORTE_SISTEMA_COMPLETO.md` para el reporte detallado con todas las tablas y especificaciones.

---

*Actualizado: 2025-12-29 - Valores OE2 definitivos alineados con commit 3fcae56*
