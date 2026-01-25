# 📊 Datasets OE3 - Resumen de Generación (2026-01-24)

## Objetivo

Generar datasets anuales (8760 horas) para entrenamiento de agentes RL con
CityLearn v2.
Cada **toma** (no cargador) es un punto de control independiente para el agente
OE3.

---

<!-- markdownlint-disable MD013 -->
## Configuración de Infraestructura | Parámetro | Valor | |-----------|-------| | **Cargadores físicos** | 32 | | **Tomas por cargador** | 4 | | **Total tomas controlables** | **128** | | Playa Motos | 28 cargadores × 4 = 112 tomas @ 2 kW | | Playa Mototaxis | 4 cargadores × 4 = 16 tomas @ 3 kW | | **Potencia total instalada** | **272 kW** | | Horario operación | 9 AM - 10 PM (13 horas) | | Duración sesión | 30 minutos (Modo 3 IEC 61851) | ---

<!-- markdownlint-disable MD013 -->
## Tabla 13 OE2 - Escenarios de Dimensionamiento | Escenario | PE | FC | Cargadores (×4) | Tomas | Energía/Día (kWh) | |-----------|---:|---:|----------------:|------:|------------------:| | **CONSERVADOR** | 0.10 | 0.40 | 4 | 16 | 231.20 | | **MEDIANO** | 0.50 | 0.60 | 20 | 80 | 1,738.80 | | **RECOMENDADO*** | 0.65 | 0.75 | 32 | 128 | 2,823.00 | | **MÁXIMO** | 1.00 | 1.00 | 35 | 140 | 5,800.00 | > **Nota**: PE = Probabilidad de Evento de carga, FC = Factor de Carga (% de
batería a recargar)

---

## Vehículos Cargados por Escenario

<!-- markdownlint-disable MD013 -->
### Cálculo basado en horas pico (6pm-10pm = 40% de demanda diaria) |Escenario|Motos/Día|Mototaxis/Día|Total/Día|Total/Mes|Total/Año|Total/20 años|
|-----------|----------:|--------------:|----------:|----------:|----------:|--------------:| | CONSERVADOR | 225 | 32 | 257 | 7,710 | 93,805 | 1,876,100 | | MEDIANO | 1,125 | 162 | 1,287 | 38,610 | 469,755 | 9,395,100 | |**RECOMENDADO***|**1,462**|**210**|**1,672**|**50,160**|**610,280**|**12,205,600**| | MÁXIMO | 2,250 | 325 | 2,575 | 77,250 | 939,875 | 18,797,500 | ---

<!-- markdownlint-disable MD013 -->
## Energía Cargada por Escenario | Escenario | Energía/Día | Energía/Mes | Energía/Año | Energía/20 años | |-----------|------------:|------------:|------------:|----------------:| | CONSERVADOR | 231 kWh | 6,936 kWh | 84,388 kWh | 1,688 MWh | | MEDIANO | 1,739 kWh | 52,164 kWh | 634,662 kWh | 12,693 MWh | |**RECOMENDADO***|**2,823 kWh**|**84,690 kWh**|**1,030,395 kWh**|**20,608 MWh**| | MÁXIMO | 5,800 kWh | 174,000 kWh | 2,117,000 kWh | 42,340 MWh | ---

## Datasets Generados

### 1. Escenario RECOMENDADO (Para Entrenamiento OE3)

**Ubicación**: `data/processed/citylearn/iquitos_128_tomas/`

<!-- markdownlint-disable MD013 -->
```text
iquitos_128_tomas/
├── Playa_Motos/           # 112 archivos CSV
│   ├── MOTO_CH_001_T1.csv
│   ├── MOTO_CH_001_T2.csv
│   ├── ...
│   └── MOTO_CH_028_T4.csv
├── Playa_Mototaxis/       # 16 archivos CSV
│   ├── MOTOTAXI_CH_001_T1.csv
│   ├── ...
│   └── MOTOTAXI_CH_004_T4.csv
├── schema_128_tomas.json  # Schema CityLearn v2
└── dataset_summary.json   # Resumen generación
```bash
<!-- markdownlint-...
```

[Ver código completo en GitHub]text
iquitos_128_tomas_maximo/
├── Playa_Motos/           # 112 archivos CSV
├── Playa_Mototaxis/       # 16 archivos CSV
├── schema_128_tomas_maximo.json
└── dataset_summary_maximo.json
```bash
<!-- markdownlint-enable MD013 -->

**Estadísticas**:

- Energía diaria: **~2,298 kWh/día**
- Vehículos/día: **~9,269** (8,099 motos + 1,170 mototaxis)
- Uso: Dimensionamiento de infraestructura

---

## Formato de Archivos CSV

<!-- markdownlint-disable MD013 -->
Cada archivo CSV tiene el formato CityLearn v2: | Columna | Descripción | |---------|-------------| | Hour | Hora del día (0-23) | | Da...
```

[Ver código completo en GitHub]python
# Cargar schema RECOMENDADO para entrenamiento
schema_path = "data/processed/citylearn/iquitos_128_tomas/schema_128_tomas.json"

# El agente OE3 controlará 128 tomas individuales
# Cada toma puede modular potencia: 0 a potencia_nominal kW
```bash
<!-- markdownlint-enable MD013 -->

---

## Referencias

- [DATASETS_ANUALES_128_CHARGERS.md](docs/DATASETS_ANUALES_128_CHARGERS.md) -
  - Detalles de datasets
- [MODO_3_OPERACION_30MIN.md](docs/MODO_3_OPERACION_30MIN.md) - Operación Modo 3
- [Tabla 13 OE2](src/iquitos_citylearn/oe2/chargers.py) - Función
  - `generate_tabla13_scenarios()`

---

**Generado**: 2026-01-24
**Autor**: Sistema automatizado
