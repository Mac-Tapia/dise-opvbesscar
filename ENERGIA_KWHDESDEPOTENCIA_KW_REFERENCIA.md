# Cálculo de Energía (kWh) a partir de Potencia (kW) - Referencia Técnica

## Fórmula Principal (Verificada y Validada)

### **E [kWh] = P [kW] × Δt [h]**

Donde:
- **E** = Energía en **kilowatt-horas** (kWh)
- **P** = Potencia en **kilowatts** (kW)
- **Δt** = Intervalo de tiempo en **horas** (h)

---

## Verificación Dimensional

La fórmula es dimensionalmente correcta:

$$[kWh] = [kW] \times [h]$$

O en unidades fundamentales (SI):

$$[J] = [W] \times [s] = \frac{J}{s} \times s = [J] \text{ ✓}$$

---

## Ejemplos de Aplicación

### Ejemplo 1: Intervalo Horario (Caso Estándar PVGIS)

**Datos:**
- Potencia DC: 4,162,000 W = 4,162 kW
- Intervalo temporal: 1 hora
- Fórmula: E = 4,162 kW × 1 h = **4,162 kWh**

**Verificación:**
```
E [kWh] = 4,162,000 W × 1 h / 1000 = 4,162 kWh ✓
```

---

### Ejemplo 2: Intervalo de 15 Minutos (Alta Resolución)

**Datos:**
- Potencia: 1,040,500 W = 1,040.5 kW
- Intervalo temporal: 15 minutos = 0.25 horas
- Fórmula: E = 1,040.5 kW × 0.25 h = **260.1 kWh**

**Verificación:**
```
E [kWh] = 1,040,500 W × 0.25 h / 1000 = 260.125 kWh ✓
```

---

### Ejemplo 3: Cálculo Anual (Sistema Completo)

**Para instalación solar de 4,162 kW en Iquitos, Perú:**

- **Capacidad instalada:** 4,162 kW
- **Horas por año:** 8,760 h
- **Factor de capacidad:** ~30% (tropical con buen soleamiento)
- **Energía anual:** 4,162 kW × 8,760 h × 0.30 = **10,900,000 kWh/año**

(En realidad obtenemos ~8.3 GWh/año con datos reales de PVGIS)

---

## Conversión de Unidades

Si tienes potencia en **watts** y tiempo en **segundos**:

$$E[J] = P[W] \times t[s]$$

Para convertir a **kilowatt-horas:**

$$E[kWh] = \frac{P[W] \times t[s]}{3,600,000}$$

O más simplemente, si P está en **kW** y t en **horas**:

$$E[kWh] = P[kW] \times t[h]$$

---

## Aplicación en Código (solar_pvlib.py)

```python
# Datos de entrada (de ModelChain SAPM)
dc_power_w = 4162000  # watts
ac_power_w = 3200000  # watts (después del inversor)
dt_hours = 1.0        # intervalo horario

# FÓRMULA CORRECTA:
# Energía DC: E = P × Δt / 1000
dc_energy_kwh = dc_power_w * dt_hours / 1000
# → 4,162,000 × 1.0 / 1000 = 4,162 kWh

# Energía AC: E = P × Δt / 1000  
ac_energy_kwh = ac_power_w * dt_hours / 1000
# → 3,200,000 × 1.0 / 1000 = 3,200 kWh
```

**Ubicación en código:** `src/dimensionamiento/oe2/generacionsolar/solar_pvlib.py:874-889`

---

## Referencias Científicas y Técnicas

### Papers y Estándares

| Referencia | Descripción | URL/Nota |
|---|---|---|
| **IEC 61724-1:2017** | Photovoltaic system performance monitoring. Measurement, data and analysis | International Electrotechnical Commission |
| **NREL PVLib Python** | Open-source library para cálculos PV | https://pvlib-python.readthedocs.io |
| **PVGIS** | Photovoltaic Geographical Information System | https://pvgis.ec.europa.eu |
| **Sandia National Labs** | SAPM Module and Inverter Models | https://pvpmc.sandia.gov |

### Definiciones Fundamentales

**Watt (Potencia):**
- 1 W = 1 J/s (joule por segundo)
- Tasa de transferencia de energía

**Kilowatt-hora (Energía):**
- 1 kWh = 3.6 MJ (megajulios)
- 1 kWh = 1 kW × 1 h
- Cantidad total de energía consumida o generada

---

## Errores Comunes a Evitar

### ❌ ERROR 1: Ignorar el intervalo temporal
```python
# INCORRECTO:
energy_kwh = power_kw  # Asume E = P, falta el tiempo

# CORRECTO:
energy_kwh = power_kw * time_hours
```

### ❌ ERROR 2: No convertir unidades correctamente
```python
# INCORRECTO:
energy_kwh = power_w  # P en watts, resultado no es kWh

# CORRECTO:
energy_kwh = power_w * time_h / 1000  # Divide entre 1000 para W→kW
```

### ❌ ERROR 3: Mezclar unidades de tiempo
```python
# INCORRECTO:
energy_kwh = power_kw * time_minutes  # Unidades incompatibles

# CORRECTO:
energy_kwh = power_kw * (time_minutes / 60)  # Convierte minutos a horas
```

---

## Verificación de Datos Reales (2024 Iquitos)

**Dataset generado:** `pv_generation_timeseries.csv`

| Parámetro | Valor | Unidad |
|---|---|---|
| Energía anual (AC) | 8,292,514 | kWh |
| Potencia máxima | 2,886.7 | kW |
| Horas con producción | 4,259 | h/año |
| Factor de capacidad | 29.6% | % |
| Intervalo temporal | 1.0 | hora |

**Verificación de fórmula E = P × Δt:**
```
Hora con máxima potencia:
  - Potencia: 2,886.69 kW
  - Intervalo: 1.0 h
  - Energía: 2,886.69 kW × 1.0 h = 2,886.69 kWh ✓ CORRECTO
```

---

## Conclusiones

✅ La fórmula **E [kWh] = P [kW] × Δt [h]** es correcta y está validada

✅ Se ha aplicado correctamente en `solar_pvlib.py` (líneas 874-889)

✅ Los datos generados del sistema fotovoltaico de Iquitos son físicamente realistas

✅ El factor de capacidad (~30%) es típico para la ubicación ecuatorial con buen soleamiento

---

## Validación de Código (Ejecutar)

Para validar que las fórmulas están correctamente implementadas:

```bash
python validate_energy_formulas.py
```

**Salida esperada:**
```
✓ TEST 1 PASSED (Intervalo horario)
✓ TEST 2 PASSED (Intervalo 15 minutos)
✓ TEST 3 PASSED (Año completo - datos reales)
✓ TEST 4 PASSED (Análisis dimensional)
✓ TODAS LAS VALIDACIONES PASADAS
```

---

**Documento creado:** 2026-02-04  
**Estado:** VALIDADO ✓  
**Integración:** solar_pvlib.py (líneas 874-889)
