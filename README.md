# pvbesscar - RL-based EV Charging Optimization

Optimizacion de carga EV con energia solar y BESS para Iquitos, Peru. El proyecto integra OE2
(dimensionamiento solar, BESS, cargadores y demanda) con OE3 (control RL SAC/PPO/A2C) para reducir
emisiones en una red aislada con factor de emision `0.4521 kg CO2/kWh`.

## Estado Canonico

**Actualizado:** 2026-05-31
**Branch:** `smartcharger`
**Agente OE3 seleccionado:** **A2C**
**Documento principal:** [reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md](reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md)

Los reportes antiguos donde SAC o A2C aparecen como ganador quedan reemplazados por la comparativa
canonica de mayo de 2026. SAC fue reentrenado en v8.2 con `VecNormalize` el 2026-05-30/31.
Para consultas automatizadas de otros agentes, usar:

- [reports/oe3/agents_comparison_canonical.json](reports/oe3/agents_comparison_canonical.json)
- [reports/oe3/agents_comparison_canonical.csv](reports/oe3/agents_comparison_canonical.csv)
- [reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md](reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md)
- [reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md](reports/oe3/REPORTE_MEJOR_AGENTE_CO2_DIRECTO_INDIRECTO.md)
- [outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json](outputs/hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json)

## Resultado OE3

Criterio operativo principal: score multiobjetivo acumulado en 50 episodios. Se prioriza mayor CO2
directo+indirecto evitado, menor importacion de red, mayor carga de motos/mototaxis en eventos
equivalentes, mayor uso util de BESS y menor deuda/violaciones de carga.

| Rank | Agente | Criterios liderados | CO2 total evitado kg | Grid import kWh | EV equiv 50 ep | BESS descarga kWh | Deuda/violaciones |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | **A2C** | **9/9** | **122,980,987** | **368,798,317** | **4,307,304** | **33,504,412** | **811** |
| 2 | PPO | 0/9 | 122,688,120 | 370,717,132 | 4,203,700 | 31,831,147 | 2,333 |
| 3 | SAC v8.2 | 0/9 | 121,316,857 | 370,440,348 | 4,180,962 | 30,022,939 | 1,385 |

**Conclusion:** A2C gana por el score multiobjetivo acumulado. PPO conserva el menor `F2` puntual
(3,657,484 kg CO2/año), pero ese valor queda como lectura complementaria.

Conteo EV: A2C carga **3,871,470 motos equivalentes** y **435,835 mototaxis equivalentes** en los
50 episodios. Ningun agente tiene cero violaciones acumuladas; A2C tiene el menor total.

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
| Diagnostico SAC v8.2 | `reports/oe3/DIAGNOSTICO_SAC_PLAN_REENTRENAMIENTO.md` |
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
python scripts/analysis/actualizar_canonico_oe3.py

# Regenerar tablas OE3 desde la fuente canonica
python scripts/reporting/generar_tablas_oe3.py
```

## Politica de Artefactos

Los resultados de entrenamiento completos (`outputs/*_training/`, trazas, checkpoints y figuras pesadas)
son artefactos generados y no deben usarse como fuente documental primaria en GitHub. La fuente versionada
para informes y consultas es `reports/oe3/`. Los binarios antiguos de informes OE3 y figuras de hipotesis
que apuntaban a SAC/A2C fueron retirados o reemplazados para evitar resultados desactualizados.

Los CSV grandes que deben permanecer versionados usan Git LFS segun `.gitattributes`.
