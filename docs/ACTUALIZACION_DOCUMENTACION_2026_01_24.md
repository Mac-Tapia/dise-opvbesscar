# ✅ Actualización de Documentación - 2026-01-24

## Resumen de Cambios

Esta actualización consolida la documentación relacionada con los datasets OE3
para entrenamiento de agentes RL con 128 tomas controlables.

---

## 📁 Documentos Creados

### 1. `docs/DATASETS_OE3_RESUMEN_2026_01_24.md`

**Contenido**:

- Descripción completa de datasets OE3 CityLearn v2
- Tabla 13 OE2 escenarios con vehículos cargados
- Especificaciones de archivos y formato
- Scripts de generación

---

## 📝 Documentos Actualizados

### 2. `docs/CONSTRUCCION_128_CHARGERS_FINAL.md`

**Cambios**:

  | Antes | Después |  
|-------|---------|
  | 128 chargers individuales | 32 cargadores × 4 tomas = 128 tomas |  
  | Energía: 3,252 kWh/día | RECOMENDADO: 905 kWh/día,... |  
  | Vehículos/día: 2,200+ | 2,575/día (RECOMENDADO), 9,269/día... |  
  | 131 observables | 264 observables |  
  | Sin acciones individuales | 129 acciones (128 tomas + 1 BESS) |  

### 3. `docs/MODO_3_OPERACION_30MIN.md`

**Cambios**:

- Corregido timeline operativo: horas pico 6pm-10pm (no 9am-1pm)
- Actualizada tabla de sesiones con valores realistas
- Cambiado "112 chargers" → "112 tomas (28 cargadores × 4 tomas)"
- Actualizado control RL a OE3: 129 acciones individuales
- Corregidos observables: formato `MOTO_CH_XXX_ev_charging_power`
- Actualizado reward esperado con escenario RECOMENDADO (905 kWh/día)

### 4. `docs/00_INDEX_MAESTRO_CONSOLIDADO.md`

**Cambios**:

- Añadida referencia a `DATASETS_OE3_RESUMEN_2026_01_24.md`
- Añadida referencia a `MODO_3_OPERACION_30MIN.md` actualizado
- Descripción de vehículos/día corregida

### 5. `INDICE_DOCUMENTACION.md`

**Cambios**:

- Añadida sección 8: DATASETS_OE3_RESUMEN_2026_01_24.md
- Añadida sección 9: MODO_3_OPERACION_30MIN.md

---

## 📊 Datos Clave Consolidados

### Arquitectura de Infraestructura

  | Playa | Cargadores | Tomas | Potencia/Toma | Potencia Total |  
|-------|------------|-------|---------------|----------------|
  | Motos | 28 | 112 | 2.0 kW | 224 kW |  
  | Mototaxis | 4 | 16 | 3.0 kW | 48 kW |  
  | **TOTAL** | **32** | **128** | - | **272 kW** |  

### Escenarios de Dimensionamiento (Tabla 13 OE2)

  | Escenario | PE | FC | Cargadores | Tomas | Energía/Día |  
|-----------|---:|---:|-----------:|------:|------------:|
  | CONSERVADOR | 0.10 | 0.40 | 4 | 16 | 231 kWh |  
  | MEDIANO | 0.50 | 0.60 | 20 | 80 | 1,739 kWh |  
  | **RECOMENDADO*** | **0.65** | **0.75** | **32** | **128** | **2,823 kWh** |  
  | MÁXIMO | 1.00 | 1.00 | 35 | 140 | 5,800 kWh |  

### Vehículos Cargados por Escenario

  | Escenario | Motos/Día | Mototaxis/Día | Total/Día | Total/Año | Total/20 años |  
|-----------|----------:|--------------:|----------:|----------:|--------------:|
  | CONSERVADOR | 225 | 32 | 257 | 93,805 | 1,876,100 |  
  | MEDIANO | 1,125 | 162 | 1,287 | 469,755 | 9,395,100 |  
  | **RECOMENDADO*** | **1,462** | **210** | **1,672** | **610,280** | **12,205,600** |  
  | MÁXIMO | 2,250 | 325 | 2,575 | 939,875 | 18,797,500 |  

### Energía Cargada por Escenario

  | Escenario | Energía/Día | Energía/Año | Energía/20 años |  
|-----------|------------:|------------:|----------------:|
  | CONSERVADOR | 231 kWh | 84,388 kWh | 1,688 MWh |  
  | MEDIANO | 1,739 kWh | 634,662 kWh | 12,693 MWh |  
  | **RECOMENDADO*** | **2,823 kWh** | **1,030,395 kWh** | **20,608 MWh** |  
  | MÁXIMO | 5,800 kWh | 2,117,000 kWh | 42,340 MWh |  

---

## 📂 Ubicación de Datasets Generados

```text
data/processed/citylearn/
├── iquitos_128_tomas/              # ESCENARIO RECOMENDADO
│   ├── Playa_Motos/               # 112 CSVs
│   ├── Playa_Mototaxis/           # 16 CSVs
│   └── schema_128_tomas.json      # Schema CityLearn v2
│
└── iquitos_128_tomas_maximo/       # ESCENARIO MÁXIMO
    ├── Playa_Motos/               # 112 CSVs
    ├── Playa_Mototaxis/           # 16 CSVs
    └── schema_128_tomas_maximo.json

data/oe2/
└── tabla_escenarios_vehiculos.csv  # Tabla 13 con vehículos (actualizado)
```bash

---

## 🛠️ Scripts Asociados

  | Script | Propósito |  
|--------|-----------|
  | `src/iquitos_citylearn/oe2/chargers.py` | **Módulo principal** - Genera... |  
  | `generar_dataset_oe3_128_tomas.py` | Dataset RECOMENDADO |  
  | `generar_dataset_oe3_128_tomas_MAXIMO.py` | Dataset MÁXIMO |  
  | `generar_tabla_escenarios_vehiculos.py` | Tabla 13 con vehículos |  

---

## 📊 TABLA 13 OE2 - RESUMEN CONSOLIDADO FINAL

### Escenarios de Dimensionamiento

  | Escenario | PE | FC | Cargadores | Tomas | Energía/Día | Vehíc/Día | Vehíc/20años |  
|-----------|---:|---:|----------:|------:|------------:|----------:|-------------:|
  | CONSERVADOR | 0.10 | 0.40 | 4 | 16 | 231 kWh | 257 | **1,876,100** |  
  | MEDIANO | 0.50 | 0.60 | 20 | 80 | 1,739 kWh | 1,287 | **9,395,100** |  
  ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  | MÁXIMO | 1.00 | 1.00 | 35 | 140 | 5,800 kWh | 2,575 | **18,797,500** |  

### Energía Cargada

  | Escenario | Energía/Año | Energía/20 años |  
|-----------|------------:|----------------:|
  | CONSERVADOR | 84,388 kWh | **1,688 MWh** |  
  | MEDIANO | 634,662 kWh | **12,693 MWh** |  
  | **RECOMENDADO*** | **1,030,395 kWh** | **20,608 MWh** |  
  | MÁXIMO | 2,117,000 kWh | **42,340 MWh** |  

---

## ✅ Estado Final

- [x] Tabla 13 OE2 con 4 escenarios completos
- [x] Cálculos de vehículos: día, mes, año, 20 años
- [x] Cálculos de energía: día, mes, año, 20 años
- [x] `chargers.py` actualizado con salida completa
- [x] CSV `tabla_escenarios_vehiculos.csv` actualizado
- [x] 6 documentos Markdown actualizados:
  - DATASETS_OE3_RESUMEN_2026_01_24.md
  - DATASETS_ANUALES_128_CHARGERS.md
  - MODO_3_OPERACION_30MIN.md
  - CONSTRUCCION_128_CHARGERS_FINAL.md
  - 00_INDEX_MAESTRO_CONSOLIDADO.md
  - ACTUALIZACION_DOCUMENTACION_2026_01_24.md

---

**Fecha**: 2026-01-24
**Autor**: Sistema Automatizado
**Autor**: Sistema Automatizado
