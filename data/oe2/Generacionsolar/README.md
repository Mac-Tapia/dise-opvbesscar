# Generacion Solar PVGIS/pvlib 2024 - Iquitos

Esta carpeta contiene el dataset canónico de generación solar horaria usado por OE2, BESS, CityLearn v2 y los agentes RL del proyecto `pvbesscar`.

## Dataset Canónico

| Elemento | Valor |
|---|---:|
| Archivo principal | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` |
| Perfil ampliado | `data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv` |
| Registros | 8,760 horas |
| Cobertura | 365 días x 24 h |
| Zona horaria | America/Lima |
| Ubicación | Iquitos, Perú |
| Latitud | -3.75 |
| Longitud | -73.25 |

## Sistema Fotovoltaico

| Parámetro | Valor |
|---|---:|
| Capacidad DC nominal | 4,162 kWp |
| Capacidad AC nominal | 3,201 kW |
| Módulo | Jinko Tiger Neo JKM580N 72HL4 BDV |
| Inversor | Eaton Xpert1670 |
| Inclinación | 10 grados |
| Azimut | 0 grados, norte |
| Área disponible | 20,637 m2 |
| Área utilizada | 18,535 m2 |

## Resultados Descriptivos

| Indicador | Valor |
|---|---:|
| Energía anual AC | 5,819,332 kWh |
| Energía anual AC | 5.819 GWh |
| Potencia media anual | 664.31 kW |
| Potencia media en horas con producción | 1,366.36 kW |
| Potencia máxima AC | 3,245.95 kW |
| Hora de potencia máxima | 2024-10-18 11:00:00-05:00 |
| Horas con producción | 4,259 h |
| Factor de capacidad | 20.75% |
| Performance ratio | 83.46% |
| Yield específico | 1,398.21 kWh/kWp-año |
| CO2 indirecto evitado | 2,630,920 kg CO2/año |
| Ahorro solar estimado | S/ 1,629,413/año |

## Archivos Relevantes

| Archivo | Uso |
|---|---|
| `pv_generation_citylearn2024.csv` | Dataset canónico compacto para CityLearn |
| `pv_generation_hourly_citylearn_v2.csv` | Dataset ampliado con ahorro, CO2, tarifas y alias `pv_kwh`/`pv_kw` |
| `pv_daily_energy.csv` | Energía diaria |
| `pv_monthly_energy.csv` | Energía mensual |
| `pv_dias_representativos.csv` | Días de máxima generación, despejado, intermedio y nublado |
| `solar_results.json` | Resumen técnico en JSON |
| `CERTIFICACION_SOLAR_DATASET_2024.json` | Validación de integridad |
| `informe_generacion_solar_procedimiento_resultados_descriptivos.md` | Informe metodológico y descriptivo completo |
| `solar_technical_report.md` | Reporte técnico base generado por el pipeline |

## Uso en Código

```python
import pandas as pd

solar_df = pd.read_csv("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
assert len(solar_df) == 8760
energia_anual = solar_df["energia_kwh"].sum()
print(f"Energía anual solar: {energia_anual:,.0f} kWh")
```

## Nota

Los archivos históricos con nombres `solar_generation_profile_2024.csv` o rutas en `data/interim/oe2/solar/` no deben usarse como fuente primaria. La fuente de verdad actual es `pv_generation_citylearn2024.csv`.
