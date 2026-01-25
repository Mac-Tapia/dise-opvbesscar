# CityLearn v2 - Perfiles de Generación Solar + 101 Escenarios de Demanda

## Descripción General

**Proyecto**: BESS Iquitos - Estacionamientos Vehículos Eléctricos  
**Fecha**: 24 Enero 2026  
**Objetivo**: Entrenar agentes RL en CityLearn v2 con 101 escenarios diferentes

## Estructura de Datos

### 1. Perfil de Generación Solar (ÚNICO para todos los escenarios)

**Archivo**: `perfil_solar_15min_anual.csv`

**Características**:

- **Resolución**: 15 minutos
- **Período**: 1 año (365 días)
- **Total timesteps**: 35,037
- **Ubicación**: Iquitos, Perú (-3.75°, -73.25°)
- **Sistema**:
  - Potencia DC: 622.58 kWp
  - Potencia AC: 497.92 kW
  - Módulos: 30,845 × Kyocera KS20
  - Inversor: Eaton Xpert1670
- **Generación anual**: 763,787 kWh

**Columnas del CSV**:

```
timestamp           : ISO 8601 (UTC-5)
hour                : 0-23
minute              : 0, 15, 30, 45
day                 : 0-364
pv_power_kw         : Potencia instantánea [kW]
pv_energy_kwh       : Energía en intervalo [kWh]
```

### 2. Escenarios de Demanda (101 DIFERENTES)

**Ubicación**: `data/oe2/citylearn_v2_101_escenarios/`

**Características**:

- **Archivos**: 101 × `escenario_###_citylearn.csv`
- **Resolución**: 15 minutos
- **Timesteps**: 35,037 por archivo (igual que solar)
- **Demanda**: Varía según escenario

**Escenarios por Rango**:

| Rango | Escenarios | Demanda Anual | Descripción |
|-------|-----------|---------------|-------------|
| **BAJO** | 1-20 | 7,024 - 23,140 kWh | Bajo uso de cargadores |
| **BAJO-MEDIO** | 21-40 | 24,564 - 64,744 kWh | Uso moderado |
| **MEDIO** | 41-60 | 66,902 - 119,548 kWh | Uso promedio |
| **MEDIO-ALTO** | 61-80 | 113,680 - 164,497 kWh | Alto uso |
| **ALTO** | 81-101 | 148,144 - 195,123 kWh | Máximo uso |

**Columnas del CSV**:

```
timestamp           : ISO 8601 (UTC-5) [IGUAL A SOLAR]
hour                : 0-23
minute              : 0, 15, 30, 45
day                 : 0-364
pv_power_kw         : Potencia solar [kW] [IGUAL PARA TODOS]
pv_energy_kwh       : Energía solar [kWh] [IGUAL PARA TODOS]
demand_kw           : Demanda de cargadores [kW] [VARÍA]
demand_kwh          : Energía de demanda [kWh] [VARÍA]
```

## Diferencia Clave con Sesión Anterior

### ❌ Anterior (Incorrecto)

- 101 escenarios con DIFERENTES perfiles solares
- Mezcla de generación + demanda en cada escenario
- No representaba realidad (hay un ÚNICO BESS con generación centralizada)

### ✅ Actual (Correcto)

- **1 ÚNICO perfil solar** para todos los escenarios
- 101 escenarios varían SOLO en demanda
- Representa realidad: Generación centralizada (BESS) + Demanda distribuida (cargadores)

## Uso en CityLearn v2

### Estructura para CityLearn

```python
# Ejemplo de carga para entrenar un agente
import pandas as pd

# Cargar perfil solar (igual para todos)
solar = pd.read_csv("perfil_solar_15min_anual.csv")

# Cargar escenario 051 (MEDIO)
scenario_51 = pd.read_csv("escenario_051_citylearn.csv")

# Datos para CityLearn v2:
data = {
    'timestamp': scenario_51['timestamp'],
    'pv_generation_kw': scenario_51['pv_power_kw'],
    'load_kw': scenario_51['demand_kw'],
    'bess_capacity_kwh': 1_632,  # Parámetro BESS verificado
    'bess_power_kw': 593,        # Parámetro BESS verificado
}

# Entrenar agente
agent.train(data, episodes=50)
```

### Ventajas para Entrenamiento

1. **Robustez**: Agente ve 101 patrones de demanda diferentes
2. **Escalabilidad**: Mismo código para todos los escenarios
3. **Convergencia**: Más rápida con escenarios que varían en demanda
4. **Realismo**: Solar varía naturalmente, demanda por política de carga

## Estadísticas Resumen

### Generación Solar (IGUAL para todos)

```
Energía anual:      763,787 kWh
Potencia máxima:    418.95 kW
Potencia promedio:  87.20 kW
Factor de planta:   17.5%
Performance Ratio:  73.7%
```

### Demanda Promedio por Rango

```
BAJO        :    12,823 kWh/año
BAJO-MEDIO  :    42,943 kWh/año
MEDIO       :    92,321 kWh/año
MEDIO-ALTO  :   139,819 kWh/año
ALTO        :   173,225 kWh/año
```

### Ratio Solar:Demanda

```
Escenario más bajo  : 763,787 / 7,024    = 108.7x (solar >> demanda)
Escenario más alto  : 763,787 / 195,123  = 3.9x  (solar > demanda)
```

## Archivos Generados

```
data/oe2/
├── perfiles_solares/
│   ├── perfil_solar_15min_anual.csv        (1.9 MB)
│   └── perfil_solar_metadata.json
│
└── citylearn_v2_101_escenarios/
    ├── escenario_001_citylearn.csv
    ├── escenario_002_citylearn.csv
    ├── ...
    ├── escenario_101_citylearn.csv         (101 archivos × ~1.8 MB)
    ├── citylearn_v2_metadata.json
    └── README.md (este archivo)
```

## Próximos Pasos

1. ✅ Generar perfil solar único
2. ✅ Generar 101 escenarios con demanda variable
3. ⏭️ Entrenar agentes SAC, PPO, A2C en escenarios selectos
4. ⏭️ Validar convergencia y performance BESS
5. ⏭️ Análisis comparativo entre 101 escenarios

## Notas Técnicas

- **Resolución 15 minutos**: Adecuada para dinámicas de BESS
- **Timesteps 35,037**: De 365 días × 96 intervalos (año completo)
- **Datos PVGIS TMY**: Radiación real para Iquitos
- **Modelo PV Sandia**: Precisión para simulación realista
- **Alineación temporal**: Todos los CSVs sincronizados en timestamp

## Validación

✅ 101 escenarios generados  
✅ Timesteps alineados (35,037 registros)  
✅ Perfiles solar + demanda combinados  
✅ Metadatos guardados  
✅ Listos para CityLearn v2  

---

**Generado**: 24 Enero 2026  
**Estado**: LISTO PARA ENTRENAR
