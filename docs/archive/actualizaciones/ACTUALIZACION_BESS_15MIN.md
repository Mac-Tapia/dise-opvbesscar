# ACTUALIZACIÓN DE BESS.PY PARA PERFILES DE 15 MINUTOS

## ✅ CAMBIOS REALIZADOS

Se ha actualizado el código de `bess.py`para soportar perfiles de carga EV con
resolución de 15 minutos:

### 1. Función `load_ev_demand()` Actualizada

#### Cambios:

- Detecta automáticamente si el CSV tiene formato de 15 minutos (96 intervalos)
  - o horario (24 horas)
- Para 15 minutos: Expande 96 intervalos a 35,040 intervalos anuales (365 días
  - × 96)
- Mantiene retrocompatibilidad con formato horario

#### Formato CSV esperado (15 minutos):

<!-- markdownlint-disable MD013 -->
```csv
interval,time_of_day,hour,minute,energy_kwh,power_kw,is_peak
0,0.00,0,0,0.0,0.0,False
1,0.25,0,15,0.0,0.0,False
...
36,9.00,9,0,0.0,0.0,False  # Apertura: 0.00 kW
...
95,23.75,23,45,0.0,0.0,False
```bash
<!-- markdownlint-enable MD013 -->

### 2. Alineación de Series Temporales

#### Cambios: (2)

- Detecta si EV está en formato de 15 min (35,040 puntos) o horario (8,760)
- Convierte automáticamen...
```

[Ver código completo en GitHub]bash
python src/iquitos_citylearn/oe2/solar_pvlib.py
```bash
<!-- markdownlint-enable MD013 -->

Este script generará:

- `data/oe2/pv_profile_24h.csv` - Perfil diario representativo
- `data/oe2/pv_generation_timeseries.csv` - Serie temporal anual

#### Opción B: Crear perfil solar simplificado

Si no tienes datos reales, crear un archivo con este formato:

#### pv_profile_24h.csv:

<!-- markdownlint-disable MD013 -->
```csv
hour,pv_kwh
0,0.0
1,0.0
2,0.0
3,...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

Este perfil genera ~22,036 kWh/día (generación 5h-17h con pico al mediodía).

### 3. ⚠️ Demanda Mall - OPCIONAL

**Ubicación:** `data/oe2/demanda_mall_real.csv`

Si no existe, el código usa un perfil sintético de 33,885 kWh/día.

---

## 🚀 PASOS SIGUIENTES

### 1. Generar Perfil Solar

#### Opción rápida (perfil simplificado):

<!-- markdownlint-disable MD013 -->
```python
# Crear archivo pv_profile_24h.csv
python CREAR_PERFIL_SOLAR_SIMPLE.py
```bash
<!-- markdownlint-enable MD013 -->

#### Opción completa (con PVLib):

<!-- markdownlint-disable MD013 -->
```python
# Requiere configuración de ubicación (Iquitos)
python src/iquitos_citylearn/oe2/solar_pvlib.py
```bash
<!-- markdownlint-enable MD013 -->

### 2. Ejecutar Dimensionamiento BESS

<!-- markdownlint-disable...
```

[Ver código completo en GitHub]bash
BESS DIMENSIONAMIENTO:
  Capacidad nominal:  1,712 kWh
  Potencia nominal:     622 kW
  DoD:                   80%
  SOC operacional:    20-100%
  
OPERACIÓN:
  Carga:    5h-17h (desde solar)
  Descarga: 18h-22h (a demanda EV)
  Déficit cubierto: 1,301 kWh/día
  
MÉTRICAS:
  Autosuficiencia: >40% (solo EV)
  Ciclos/día: ~0.76
  SOC mínimo: ~20% (a las 22h)
```bash
<!-- markdownlint-enable MD013 -->

---

## 🔧 TROUBLESHOOTING

### Error: "FileNotFoundError: pv_profile_24h.csv"

**Solución:** Generar perfil solar (ver sección "Generar Perfil Solar")

### Error: "Formato de CSV no reconocido"

**Solución:** Verificar que el CSV tenga columnas correctas:

- 15 min: `interval`, `energy_kwh`
- Horario: `hour`, `energy_kwh`

### Warning: "Series cortas"

**Solución:** Verificar que todos los archivos tengan datos completos:

- EV: 35,040 intervalos (15 min) o 8,760 horas
- Solar: 8,760 horas
- Mall: 8,760 horas

---

## 📚 DOCUMENTACIÓN ADICIONAL

Ver archivos relacionados:

- `GUIA_SCHEMA_BESS.md` - Guía completa de schema
- `RESUMEN_GENERACION_PERFIL_BESS.py` - Resumen ejecutivo
- `data/oe2/graficas/` - Gráficas de análisis del perfil
- `data/oe2/bess_dimensionamiento_schema.json` - Schema con parámetros

---

**Última actualización:** 24 de enero de 2026
**Versión código:** bess.py con soporte para perfiles de 15 minutos
