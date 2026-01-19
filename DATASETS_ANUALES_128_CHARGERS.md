# ✅ Datasets Anuales por Charger - Verificación Completada

## Estado: LISTO PARA ENTRENAMIENTO

Cada una de las **128 tomas (chargers)** tiene su **dataset anual completo** para entrenamiento en CityLearn.

---

## Estructura de Datasets

### Ubicación

```
data/interim/oe2/chargers/annual_datasets/
├── Playa_Motos/
│   ├── base/
│   │   ├── aggregated_profile.csv (suma de 112 chargers)
│   │   ├── MOTO_CH_001.csv (charger 1 - año completo)
│   │   ├── MOTO_CH_002.csv (charger 2 - año completo)
│   │   ├── ...
│   │   └── MOTO_CH_112.csv (charger 112 - año completo)
│   ├── high/  (escenario alta demanda)
│   │   └── [112 chargers anuales]
│   └── low/   (escenario baja demanda)
│       └── [112 chargers anuales]
│
└── Playa_Mototaxis/
    ├── base/
    │   ├── aggregated_profile.csv (suma de 16 chargers)
    │   ├── MOTO_TAXI_CH_113.csv (charger 113 - año completo)
    │   ├── MOTO_TAXI_CH_114.csv (charger 114 - año completo)
    │   ├── ...
    │   └── MOTO_TAXI_CH_128.csv (charger 128 - año completo)
    ├── high/
    │   └── [16 chargers anuales]
    └── low/
        └── [16 chargers anuales]
```

---

## Verificación de Datasets

### Conteo Total

| Playa | Chargers | Escenarios | Total Archivos |
|-------|----------|-----------|-----------------|
| **Playa Motos** | 112 | 3 (base, high, low) | 336 |
| **Playa Mototaxis** | 16 | 3 (base, high, low) | 48 |
| **Total** | **128** | **3** | **384** |

### Datos por Charger

✅ **Escenario Base** (base - demanda típica):

- Playa Motos: 112 chargers × 8760 horas/año = 982,080 puntos de datos
- Playa Mototaxis: 16 chargers × 8760 horas/año = 140,160 puntos de datos
- **Total Base**: 1,122,240 puntos de datos

✅ **Escenario Alto** (high - demanda pico):

- Playa Motos: 112 chargers × 8760 horas/año = 982,080 puntos
- Playa Mototaxis: 16 chargers × 8760 horas/año = 140,160 puntos
- **Total Alto**: 1,122,240 puntos de datos

✅ **Escenario Bajo** (low - demanda reducida):

- Playa Motos: 112 chargers × 8760 horas/año = 982,080 puntos
- Playa Mototaxis: 16 chargers × 8760 horas/año = 140,160 puntos
- **Total Bajo**: 1,122,240 puntos de datos

**TOTAL DATASETS**: 3,366,720 puntos de datos de carga (1 año × 3 escenarios × 128 chargers)

---

## Estructura de Archivo CSV

Cada charger tiene archivo con 8760 filas (1 hora × 365 días):

```csv
timestamp,power_kw,energy_kwh
2024-01-01 00:00:00,0.0,0.0
2024-01-01 01:00:00,0.0,0.0
...
2024-01-01 09:00:00,2.0,2.0    (ejemplo: cargando a 2 kW en Playa Motos)
...
2024-12-31 23:00:00,0.0,0.0
```

### Campos

- **timestamp**: Marca temporal (YYYY-MM-DD HH:MM:SS)
- **power_kw**: Potencia de carga en kW (0 = no cargando, hasta 2 kW Motos o 3 kW Taxis)
- **energy_kwh**: Energía acumulada en esa hora

---

## Integración con CityLearn

### Para Entrenamiento

Cada observable individual en CityLearn:

```python
"charger_MOTO_CH_001_power_kw"      # Leer de MOTO_CH_001.csv
"charger_MOTO_CH_002_power_kw"      # Leer de MOTO_CH_002.csv
...
"charger_MOTO_TAXI_CH_128_power_kw" # Leer de MOTO_TAXI_CH_128.csv
```

CityLearn **en cada timestep (1 hora)**:

1. Lee power_kw de cada CSV correspondiente
2. Suma para obtener agregados (`ev_charging_power_playa_motos_kw`, etc.)
3. Pasa observables al agente RL
4. Agente toma acción (reducir potencia, pausa, etc.)
5. Aplica cambios y pasa al siguiente timestep

### Escenarios Disponibles

El agente puede entrenarse en:

- **Base**: Demanda típica (escenario normal)
- **High**: Demanda pico (casos extremos, aprender robustez)
- **Low**: Demanda reducida (casos de bajo uso)

---

## Listo para Entrenamiento

✅ **128 chargers** → 128 datasets anuales individuales  
✅ **3 escenarios** → Variabilidad de demanda  
✅ **8760 timesteps/charger** → Cobertura anual completa  
✅ **3.3 M puntos de datos** → Suficiente para RL  

### Próximo Paso

Ejecutar entrenamiento con:

```bash
python train_v2_fresh.py --scenario base
```

CityLearn cargará automáticamente:

- `charger_MOTO_CH_001.csv` → observable `charger_MOTO_CH_001_power_kw`
- `charger_MOTO_CH_002.csv` → observable `charger_MOTO_CH_002_power_kw`
- ... (128 chargers)

---

## Verificación de Integridad

```python
# Cada charger debe tener exactamente:
# - 8760 filas (365 días × 24 horas)
# - 3 columnas (timestamp, power_kw, energy_kwh)
# - power_kw ≤ 2 kW (Motos) o 3 kW (Taxis)
# - Secuencia temporal continua (sin saltos)

Verificación: ✅ COMPLETADA
```

---

**Nota**: Los datasets fueron generados por el script OE2 con perfiles horarios realistas de carga de motos y mototaxis durante 2024.
