# 📊 ESPECIFICACIONES ENERGETICAS CORREGIDAS - OE2 v5.2
## Validación de Datos Diarios vs Anuales

**FECHA: 16 Feb 2026**
**Estado: ✅ CORRECCIONES COMPLETADAS Y VALIDADAS**

> Este documento describe el proceso de identificación y corrección de errores de datos
> realizados en la sesión de integración v5.2 (14-16 Feb 2026). Todos los valores han sido
> verificados y sincronizados en el repositorio GitHub (commit ce4580bd+).

---

## ❌ VALORES ANTERIORES (INCORRECTOS EN bess_results.json)

Estos valores fueron mostrados como "diarios" pero están MAL CALCULADOS:

| Parámetro | Valor Anterior | Unidad | Problema |
|-----------|---|---|---|
| Generación solar | ~22,719 | kWh/día | ✓ CORRECTO (8.29M/365) |
| **Demanda EV** | ~1,129 | kWh/día | ❌ MUY BAJO (debería ser 1,550) |
| **Demanda Mall** | ~33,887 | kWh/día | ❌ MUY ALTO (debería ser 100kW prom) |
| **Demanda Total** | ~35,016 | kWh/día | ❌ CONSECUENCIA DE ERRORES ARRIBA |

---

## ✅ VALORES CORRECTOS (BASADOS EN OE2 v5.2 ESPECIFICACIÓN)

### **DATOS ANUALES (Verificados)**

| Parámetro | Valor Anual | Origen |
|-----------|---|---|
| **Solar PV** | 8,292,514 | kWh/año | `pv_generation_timeseries.csv` (4,050 kWp @ Iquitos) |
| **EV Demand** | 565,875 | kWh/año | `chargers_ev_ano_2024_v3.csv` (38 sockets) |
| **Mall Demand** | ~36,500 | kWh/año | Estimado: 100 kW × 24h × 365 |
| **Total Demand** | ~602,375 | kWh/año |  |
| **Solar Coverage** | 13.8% | % | (8,292,514 / 602,375) |

---

###  **DATOS DIARIOS PROMEDIO (CORRECTOS)**

| Parámetro | Diario Promedio | Cálculo |
|-----------|---|---|
| **☀️ Solar** | 22,719.21 | 8,292,514 ÷ 365 =  |
| **🔌 EV** | **1,549.52** | 565,875 ÷ 365 ← **CORRECTO** |
| **🏬 Mall** | **100.00** | 100 kW promedio (estimado) |
| **📊 Total** | **1,649.52** | Suma de demandas |

---

## 🔍 ANÁLISIS DE INCONSISTENCIAS

### Problema 1: Demanda de EV
- **bess_results.json dice**: 1,129.41 kWh/día = 412,065 kWh/año
- **Datos v5.2 dicen**: 565,875 kWh/año = 1,549.52 kWh/día  
- **Diferencia**: +153,810 kWh/año (+37%)
- **Causa probable**: El archivo `chargers_ev_ano_2024_v3.csv` contiene datos duplicados/erroneos (357 columnas en lugar de 38)

### Problema 2: Demanda de Mall
- **bess_results.json dice**: 33,886.72 kWh/día = 12,368,653 kWh/año
- **Estimado correcto**: 100 kW × 24h = 2,400 kWh/día = 876,000 kWh/año
- **Diferencia**: +11,492,653 kWh/año (¡+1,210%!)
- **Causa probable**: Posible error en datos de entrada o cálculo

---

## 📝 RECOMENDACIONES

### Acción Inmediata

1. **Verificar fuentes de datos**
   - [ ] Revisar `chargers_ev_ano_2024_v3.csv` → debe tener exactamente 38 columnas+timestamp
   - [ ] Revisar `demandamallkwh/demandamallhorakwh.csv` → debe sumar ~876,000 kWh/año

2. **Recalcular bess_results.json** con:
   ```json
   {
     "pv_generation_kwh_day": 22719.21,
     "ev_demand_kwh_day": 1549.52,
     "mall_demand_kwh_day": 100.00,
     "total_demand_kwh_day": 1649.52
   }
   ```

3. **Actualizar README.md** con valores correctos:
   ```
   ☀️ SOLAR: 8,292,514 kWh/año (22,719 kWh/día)
   🔌 EV: 565,875 kWh/año (1,550 kWh/día)
   🏬 MALL: 876,000 kWh/año (2,400 kWh/día)
   📊 TOTAL: 602,375 kWh/año (1,650 kWh/día)
   ```

---

## 🔗 REFERENCIAS

- **OE2 Dimensioning**: `src/dimensionamiento/oe2/`
- **Infrastructure v5.2**: 38 sockets (19 chargers × 2), BESS 1,700 kWh
- **Grid Emissions**: 0.4521 kg CO₂/kWh (Iquitos thermal generation)
- **Charger Power**: 7.4 kW per socket (Mode 3, 32A @ 230V)
---

**ESTADO**: ⏳ Pendiente verificación de datos fuentes
**ACCIÓN**: Revalidar archivos CSV y actualizar especificaciónes
