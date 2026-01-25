# CONSTRUCCION COMPLETADA: 128 TOMAS EN 2 PLAYAS SEGUN OE2

## Estado: ✅ LISTO PARA ENTRENAMIENTO

> **ACTUALIZADO 2026-01-24**: Arquitectura corregida a 32 cargadores × 4 tomas
= 128 tomas totales

---

## PLAYAS DE ESTACIONAMIENTO - ARQUITECTURA FINAL

### PLAYA MOTOS (87.5% del sistema)

- **Cargadores físicos**: 28 unidades
- **Tomas (sockets)**: 112 tomas de carga (4 tomas por cargador)
- **Potencia por toma**: 2.0 kW (Modo 3 IEC 61851)
- **Potencia total**: 224 kW (28 × 4 × 2 kW)
- **Energía diaria (RECOMENDADO)**: 791 kWh
- **Energía diaria (MÁXIMO)**: 2,009 kWh
- **Flota diaria**: 2,250 motos/día (RECOMENDADO)
- **IDs**: MOTO_CH_001 → MOTO_CH_112
- **Horas pico**: 18-22h (6pm-10pm)
- **Observable control**: `ev_charging_power_playa_motos_kw` (0-224 kW)

### PLAYA MOTOTAXIS (12.5% del sistema)

- **Cargadores físicos**: 4 unidades
- **Tomas (sockets)**: 16 tomas de carga (4 tomas por cargador)
- **Potencia por toma**: 3.0 kW (Modo 3 IEC 61851)
- **Potencia total**: 48 kW (4 × 4 × 3 kW)
- **Energía diaria (RECOMENDADO)**: 114 kWh
- **Energía diaria (MÁXIMO)**: 289 kWh
- **Flota diaria**: 325 mototaxis/día (RECOMENDADO)
- **IDs**: MOTO_TAXI_CH_113 → MOTO_TAXI_CH_128
- **Horas pico**: 18-22h (6pm-10pm)
- **Observable control**: `ev_charging_power_playa_mototaxis_kw` (0-48 kW)

<!-- markdownlint-disable MD013 -->
### TOTAL SISTEMA | Concepto | Cargadores | Tomas | Potencia | Energía REC | Energía MÁX | |----------|------------|-------|----------|-------------|-------------| | Motos | 28 | 112 | 224 kW | 2,193 kWh/día | 4,500 kWh/día | | Mototaxis | 4 | 16 | 48 kW | 630 kWh/día | 1,300 kWh/día | |**TOTAL**|**32**|**128**|**272 kW**|**2,823 kWh/día**|**5,800 kWh/día**| ---

<!-- markdownlint-disable MD013 -->
## TABLA 13 OE2 - ESCENARIOS DE DIMENSIONAMIENTO |Escenario|PE|FC|Cargadores|Tomas|Energía/Día|Vehíc/Día|Vehíc/20años|
|-----------|---:|---:|----------:|------:|------------:|----------:|-------------:| | CONSERVADOR | 0.10 | 0.40 | 4 | 16 | 231 kWh | 257 | 1,876,100 | | MEDIANO | 0.50 | 0.60 | 20 | 80 | 1,739 kWh | 1,287 | 9,395,100 | |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| | MÁXIMO | 1.00 | 1.00 | 35 | 140 | 5,800 kWh | 2,575 | 18,797,500 | ### VEHÍCULOS ATENDIDOS POR ESCENARIO |Escenario|Motos/Día|Mototaxis/Día|Total/Día|Total/Mes|Total/Año|Total/20años|
|-----------|----------:|--------------:|----------:|----------:|----------:|-------------:| | CONSERVADOR | 225 | 32 | 257 | 7,710 | 93,805 | 1,876,100 | | MEDIANO | 1,125 | 162 | 1,287 | 38,610 | 469,755 | 9,395,100 | |**RECOMENDADO***|**1,462**|**210**|**1,672**|**50,160**|**610,280**|**12,205,600**| | MÁXIMO | 2,250 | 325 | 2,575 | 77,250 | 939,875 | 18,797,500 | ### ENERGÍA CARGADA POR ESCENARIO | Escenario | Energía/Día | Energía/Mes | Energía/Año | Energía/20años | |-----------|------------:|------------:|------------:|---------------:| | CONSERVADOR | 231 kWh | 6,936 kWh | 84,388 kWh | 1,688 MWh | | MEDIANO | 1,739 kWh | 52,164 kWh | 634,662 kWh | 12,693 MWh | |**RECOMENDADO***|**2,823 kWh**|**84,690 kWh**|**1,030,395 kWh**|**20,608 MWh**| | MÁXIMO | 5,800 kWh | 174,000 kWh | 2,117,000 kWh | 42,340 MWh | ---

## DATOS CONSTRUIDOS SEGUN OE2

### Archivos Generados - Datasets OE3

<!-- markdownlint-disable MD013 -->
```text
data/processed/citylearn/
├── iquitos_128_tomas/              # ESCENARIO RECOMENDADO (905 kWh/día)
│   ├── schema_128_chargers.json    # Schema CityLearn con 264 observables
│   ├── MOTO_CH_001.csv             # 112 archivos motos
│   ├── ...
│   ├── MOTO_CH_112.csv
│   ├── MOTO_TAXI_CH_113.csv        # 16 archivos mototaxis
│   ├── ...
│   └── MOTO_TAXI_CH_128.csv
│
└── iquitos_128_tomas_maximo/...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Perfiles de Carga

- ✓ 128 perfiles horarios por toma (24 horas × 365 días = 8760 registros)
- ✓ Sesiones de 30 minutos (Modo 3 IEC 61851)
- ✓ Horario operativo: 9am - 10pm (13 horas)
- ✓ 2 escenarios: RECOMENDADO y MÁXIMO
- ✓ Schema CityLearn v2 compatible

---

## INTEGRACION EN CITYLEARN

### Schema Enriquecido OE3

<!-- markdownlint-disable MD013 -->
```text
File: data/processed/citylearn/iquitos_128_tomas/schema_128_chargers.json

Observables (264 total):
  • ev_charging_power_total_kw (agregado)
  • ev_charging_power_playa_motos_kw (agregado)
  • ev_charging_power_playa_mototaxis_kw (agregado)
  • MOTO_CH_001_ev_charging_power ... MOTO_CH_112_ev_charging_power (112)
  • MOTO_TAXI_CH_113_ev_charging_power ... MOTO_TAXI_CH_128_ev_charging_power (16)
 ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Metadata de 128 Tomas

<!-- markdownlint-disable MD013 -->
```text
Arquitectura física:

  • Playa_Motos:
    - 28 cargadores físicos
    - 112 tomas (4 tomas × 28 cargadores)
    - 224 kW potencia (2 kW × 112 tomas)
    - IDs: [MOTO_CH_001, ..., MOTO_CH_112]

  • Playa_Mototaxis:
    - 4 cargadores físicos
    - 16 tomas (4 tomas × 4 cargadores)
    - 48 kW potencia (3 kW × 16 tomas)
    - IDs: [MOTO_TAXI_CH_113, ..., MOTO_TAXI_CH_128]
```bash
<!-- markdownlint-...
```

[Ver código completo en GitHub]bash
python train_v2_fresh.py
```text
<!-- markdownlint-enable MD013 -->

### Fases de Entrenamiento

1. **Fase 1**: Cargar configuracion y validar 128 chargers
2. **Fase 2**: Construir esquemas y dataset
3. **Fase 3**: Calcular baseline (sin control RL)
4. **Fase 4**: Entrenamiento en serie
   - A2C: 2 episodios (exploración)
   - PPO: 2 episodios (robustez)
   - SAC: 2 episodios (continuidad)

### Metricas Esperadas

- Reduccion pic...
```

[Ver código completo en GitHub]text
commit 2026-01-24
Author: Automated System
Date: 2026-01-24

Feat: Actualización arquitectura 32 cargadores × 4 tomas = 128 tomas OE2

- Playa Motos: 28 cargadores, 112 tomas (224 kW)
- Playa Mototaxis: 4 cargadores, 16 tomas (48 kW)
- Dataset RECOMENDADO: 905 kWh/día, 2,575 vehículos/día
- Dataset MÁXIMO: 2,298 kWh/día, 9,269 vehículos/día
- Schema CityLearn con 264 observables, 129 acciones
- Control individual por toma para agente OE3
- Sesiones de 30 minutos (Modo 3 IEC 61851)
```bash
<!-- markdownlint-enable MD013 -->

---

## RESUMEN FINAL

<!-- markdownlint-disable MD013 -->
✅ **Dos playas de estacionamiento correctamente construidas según OE2** | Playa | Cargadores | Tomas | Potencia | Energía REC | Energía MÁX | |-------|------------|-------|----------|-------------|-------------| | Motos | 28 | 112 | 224 kW | 791 kWh/día | 2,009 kWh/día | | Mototaxis | 4 | 16 | 48 kW | 114 kWh/día | 289 kWh/día | |**TOTAL**|**32**|**128**|**272 kW**|**905 kWh/día**|**2,298 kWh/día**| ✅ **Completamente integradas en CityLearn v2**

- 264 observables totales
- 129 acciones (128 tomas + 1 BESS)
- Control individual por toma implementado
- Dos escenarios: RECOMENDADO y MÁXIMO

✅ **Listo para entrenamiento TIER 2 V2 OE3**

- Arquitectura de control definida
- 8760 horas de datos por toma
- Sesiones de 30 minutos (Modo 3 IEC 61851)
- Vehículos/año: 939,875 (RECOMENDADO)
