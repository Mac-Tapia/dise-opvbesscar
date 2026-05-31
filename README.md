# pvbesscar - RL-based EV Charging Optimization

Optimizacion de carga EV con energia solar y BESS para Iquitos, Peru. El proyecto integra OE2
(dimensionamiento solar, BESS, cargadores y demanda) con OE3 (control RL SAC/PPO/A2C) para reducir
emisiones en una red aislada con factor de emision `0.4521 kg CO2/kWh`.

## Estado Canonico

**Actualizado:** 2026-05-30
**Branch:** `smartcharger`
**Agente OE3 seleccionado:** **PPO**
**Documento principal:** [reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md](reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md)

Los reportes antiguos donde SAC o A2C aparecen como ganador quedan reemplazados por la comparativa
canonica de mayo de 2026. Para consultas automatizadas de otros agentes, usar:

- [reports/oe3/agents_comparison_canonical.json](reports/oe3/agents_comparison_canonical.json)
- [reports/oe3/agents_comparison_canonical.csv](reports/oe3/agents_comparison_canonical.csv)
- [reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md](reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md)
- [reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md](reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md)
- [outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json](outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json)

## Resultado OE3

Criterio operativo principal: minimizar `F2` anual (`kg CO2/año`) con 50 episodios por agente.
La prueba de normalidad se usa solo para decidir el tipo de inferencia; no reemplaza el criterio
operativo de seleccion. Como Shapiro-Wilk rechaza normalidad, la comparacion usa pruebas no
parametricas.

| Rank | Agente | F2 minimo (kg CO2/año) | Episodio | F2 media (kg/año) | Sigma (kg/año) | Reduccion vs F0 | CV plateau |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | **PPO** | **3,657,483** | **49** | 3,695,605 | 63,818 | **48.15%** | **0.034%** |
| 2 | A2C | 3,659,010 | 45 | 3,699,834 | 38,248 | 48.13% | 0.422% |
| 3 | SAC | 3,720,640 | 33 | 3,747,127 | 42,424 | 47.25% | 0.065% |

**Conclusion:** PPO gana por el menor `F2` anual. A2C queda muy cerca, pero su `F2` minimo es
1,527 kg CO2/año mayor que PPO. SAC no gana porque su mejor episodio emite 63,157 kg CO2/año mas que
PPO bajo la corrida vigente.

## Estado OE2

La infraestructura OE2 vigente para CityLearn v2 queda validada con:

| Componente | Valor vigente |
|---|---:|
| Solar PV | 4,162 kWp DC PVWatts / 3,201 kW AC; 4,050 kWp nominal de diseno |
| Energia solar anual | 5.819 GWh/año |
| Cargadores | 19 cargadores x 2 sockets = 38 puntos |
| Flota diaria | 270 motos + 39 mototaxis |
| BESS | 2,000 kWh / 400 kW |
| Dataset horario | 8,760 filas |

Referencia OE2 vigente: [docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md](docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md)

## Rutas Canonicas

| Uso | Ruta |
|---|---|
| Informe OE3 actualizado | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` |
| Datos OE3 para otros agentes | `reports/oe3/agents_comparison_canonical.json` |
| Tabla OE3 para hojas/calculo | `reports/oe3/agents_comparison_canonical.csv` |
| Auditoria de fuentes OE3 | `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md` |
| Informe CO2 directo/indirecto OE3 | `reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md` |
| Hipotesis CO2 actualizada | `outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json` |
| Solar OE2 | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` |
| Cargadores OE2 | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` |
| BESS OE2 | `data/oe2/bess/bess_ano_2024.csv` |
| Dataset CityLearn | `data/iquitos_ev_mall/` |

## Comandos

```powershell
# Entorno
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Tests
python -m pytest tests -q

# Regenerar datasets OE2 -> CityLearn
python scripts/generate_oe2_datasets.py --loader-only

# Consultar ranking OE3 canonico
python scripts/analysis/_ranking_oe3.py
python scripts/analysis/_seleccion_agente_oe3.py

# Regenerar tablas OE3 desde la fuente canonica
python scripts/reporting/generar_tablas_oe3.py
```

## Politica de Artefactos

Los resultados de entrenamiento completos (`outputs/*_training/`, trazas, checkpoints y figuras pesadas)
son artefactos generados y no deben usarse como fuente documental primaria en GitHub. La fuente versionada
para informes y consultas es `reports/oe3/`. Los binarios antiguos de informes OE3 y figuras de hipotesis
que apuntaban a SAC/A2C fueron retirados o reemplazados para evitar resultados desactualizados.

Los CSV grandes que deben permanecer versionados usan Git LFS segun `.gitattributes`.
