# ⚠️ VALIDACION: dataset_builder.py vs DATASETS REALES

**Fecha**: 2026-02-11  
**Estado**: ⚠️ **INCONSISTENCIA ENCONTRADA - REQUIERE CORRECCION**

---

## 📋 RESUMEN EJECUTIVO

El archivo `dataset_builder.py` está buscando archivos con **nombres DIFERENTES** a los que realmente existen en las carpetas. Esto causará **FALLO en la construcción de datasets para OE3**.

### Impacto:
- ❌ CityLearn v2 NO podrá cargar los datos
- ❌ Los agentes RL NO podrán entrenar
- ❌ La simulación OE3 FALLARÁ

---

## 🔴 ARCHIVOS ESPERADOS vs ARCHIVOS REALES

### 1. CHARGERS (Demanda EV)

| Ubicación | dataset_builder.py BUSCA | REALMENTE EXISTE | Estado |
|-----------|---------------------------|------------------|--------|
| `data/oe2/chargers/` | `chargers_real_hourly_2024.csv` | `chargers_ev_ano_2024_v3.csv` | ❌ NO COINCIDE |
| `data/oe2/chargers/` | `chargers_real_statistics.csv` | `chargers_real_statistics.csv` | ✓ OK |

**Columnas esperadas**: 8,760 × 38 (38 sockets horarios v5.2)  
**Columnas reales**: 8,760 × 643 (detalladas, incluyendo metadata)

### 2. BESS (Simulación)

| Ubicación | dataset_builder.py BUSCA | REALMENTE EXISTE | Estado |
|-----------|---------------------------|------------------|--------|
| `data/oe2/bess/` | `bess_hourly_dataset_2024.csv` | `bess_simulation_hourly.csv` | ❌ NO COINCIDE |

**Esperado**: Columnas específicas de CityLearn  
**Real**: Simulación BESS completa con 18 columnas

### 3. PV (Generación Solar)

| Ubicación | dataset_builder.py BUSCA | REALMENTE EXISTE | Estado |
|-----------|---------------------------|------------------|--------|
| `data/oe2/Generacionsolar/` | `pv_generation_hourly_citylearn_v2.csv` | `pv_generation_timeseries.csv` | ⚠️ PARCIAL |
| `data/oe2/Generacionsolar/` | ~same~ | `pv_generation_hourly_citylearn_v2.csv` | ✓ OK |

**Nota**: Sí existe `pv_generation_hourly_citylearn_v2.csv` (generado por bess.py)

### 4. MALL (Demanda)

| Ubicación | dataset_builder.py BUSCA | REALMENTE EXISTE | Estado |
|-----------|---------------------------|------------------|--------|
| `data/oe2/demandamallkwh/` | `demandamallhorakwh.csv` | `demandamallhorakwh.csv` | ✓ OK |

---

## 🔧 SOLUCIONES

### Opción A: Renombrar archivos reales (⚠️ NO RECOMENDADO)
Cambiar nombres de archivos generados - causaría fallos en otros scripts.

### Opción B: Actualizar dataset_builder.py (✅ RECOMENDADO)
Modificar rutas en `dataset_builder.py` para apuntar a nombres reales:

```python
# ANTES (línea 255):
chargers_real_fixed_path = oe2_base_path / "chargers" / "chargers_real_hourly_2024.csv"

# DESPUÉS:
chargers_real_fixed_path = oe2_base_path / "chargers" / "chargers_ev_ano_2024_v3.csv"
```

### Opción C: Crear links/copias (⚠️ SUBOPTIMO)
Crear archivos con nombres esperados como copias o links simbólicos.

---

## 📊 IMPACTO POR COMPONENTE

### ✓ COMPONENTES OK
- ✓ `demandamallhorakwh.csv` - Nombre correcto, archivo presente
- ✓ `chargers_real_statistics.csv` - Existe
- ✓ Algunos archivos PV alternos existen
- ✓ Estructura general válida

### ❌ COMPONENTES CON PROBLEMAS
- ❌ `chargers_ev_ano_2024_v3.csv` - NO llamado `chargers_real_hourly_2024.csv`
- ❌ `bess_simulation_hourly.csv` - NO llamado `bess_hourly_dataset_2024.csv`
- ⚠️ Columnas de BESS pueden no coincidir exactamente con expectativas CityLearn

---

## 🚀 ACCION RECOMENDADA

**Actualizar `dataset_builder.py` para usar nombres reales de archivos** (Opción B):

### Cambios necesarios:

**Línea 255** - Chargers:
```python
# ANTES:
chargers_real_fixed_path = oe2_base_path / "chargers" / "chargers_real_hourly_2024.csv"

# DESPUÉS:
chargers_real_fixed_path = oe2_base_path / "chargers" / "chargers_ev_ano_2024_v3.csv"
```

**Línea 275** - Chargers stats (OK, no cambio):
```python
chargers_stats_fixed_path = oe2_base_path / "chargers" / "chargers_real_statistics.csv"
# Este está OK ✓
```

**Línea 291** - BESS:
```python
# ANTES:
bess_hourly_fixed_path = oe2_base_path / "bess" / "bess_hourly_dataset_2024.csv"

# DESPUÉS:
bess_hourly_fixed_path = oe2_base_path / "bess" / "bess_simulation_hourly.csv"
```

**Línea 310** - Mall (OK, no cambio):
```python
mall_demand_fixed_path = oe2_base_path / "demandamallkwh" / "demandamallhorakwh.csv"
# Este está OK ✓
```

**Línea 329** - PV (OK, existe):
```python
solar_generation_fixed_path = oe2_base_path / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv"
# Este ya existe ✓
```

---

## ✅ VALIDACION POST-CORRECCION

Después de actualizar `dataset_builder.py`:

```
data/oe2/
├── chargers/
│   └── ✓ chargers_ev_ano_2024_v3.csv (8,760 × 643) → para cargar 38 sockets
├── bess/
│   └── ✓ bess_simulation_hourly.csv (8,760 × 18) → simulación BESS
├── Generacionsolar/
│   └── ✓ pv_generation_hourly_citylearn_v2.csv (8,760 × 11) → PV horario
├── demandamallkwh/
│   └── ✓ demandamallhorakwh.csv (8,760 × 1) → demanda mall
└── citylearn/
    ├── building_load.csv
    ├── bess_solar_generation.csv
    └── bess_schema_params.json
```

**Resultado esperado**:
- ✅ dataset_builder.py encontrará todos los archivos
- ✅ CityLearn v2 podrá cargar los datos
- ✅ Agentes RL podrán entrenar
- ✅ Simulación OE3 funcionará correctamente

---

## 📝 NOTAS TÉCNICAS

### Sobre la estructura de datos:

1. **Chargers** (8,760 × 643):
   - Incluye metadata de simulación
   - dataset_builder.py necesita extraer 38 columnas de sockets
   - Puede requerir transformación/filtrado

2. **BESS** (8,760 × 18):
   - Incluye estado completo de simulación (SOC, carga, descarga, etc.)
   - CityLearn puede usar directamente
   - Validar que columnas coincidan con esquema esperado

3. **PV** (8,760 × 11):
   - Ya en formato CityLearn v2
   - Validar que columna principal sea `pv_generation_kwh` o similar

4. **Mall** (8,760 × 1):
   - Simple demanda horaria
   - OK tal como está

---

## 🎯 PROXIMOS PASOS

**PRIORITY 1 (Inmediato)**:
1. ✅ Validar que archivos reales existen y tienen estructura correcta
2. ⚠️ Actualizar `dataset_builder.py` con nombres correctos
3. ✅ Verificar que dataset_builder.py pueda cargar todos los archivos

**PRIORITY 2 (Validación)**:
4. Ejecutar `dataset_builder.py` y verificar que construye datasets sin errores
5. Validar que CityLearn v2 puede cargar la estructura generada
6. Verificar que agentes RL pueden acceder a datos

**PRIORITY 3 (Training)**:
7. Iniciar entrenamiento de SAC/PPO/A2C con datos validados

---

## ARCHIVO A ACTUALIZAR

**Archivo**: `src/citylearnv2/dataset_builder/dataset_builder.py`

**Líneas clave para cambiar**:
- Línea 255: `chargers_real_hourly_2024.csv` → `chargers_ev_ano_2024_v3.csv`
- Línea 291: `bess_hourly_dataset_2024.csv` → `bess_simulation_hourly.csv`
- Línea 329: Verificar que `pv_generation_hourly_citylearn_v2.csv` existe (OK)

---

**Estado**: REQUIERE CORRECCION ANTES DE ENTRENAR AGENTES  
**Dificultad**: BAJA (cambios simples de nombres de rutas)  
**Impacto**: CRITICO (sin corrección, entrenamiento fallará)
