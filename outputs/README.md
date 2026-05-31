# outputs

Esta carpeta contiene artefactos generados por entrenamientos, hipotesis y documentos historicos.
No debe usarse como fuente primaria para seleccionar el agente OE3.

**Fuente canonica vigente:** `reports/oe3/`
**Agente seleccionado:** PPO
**Fecha:** 2026-05-30

## Archivos versionados vigentes

| Archivo | Uso |
|---|---|
| `hypothesis_test/RESULTADOS_HIPOTESIS_CO2_COMPLETO.json` | Resumen estadistico actualizado con PPO seleccionado |
| `hypothesis_test/tabla_estadisticos_descriptivos_oe3.csv` | Descriptivos SAC/PPO/A2C para F2 |
| `hypothesis_test/tabla_normalidad_shapiro_wilk_oe3.csv` | Pruebas de normalidad por agente |
| `hypothesis_test/tabla_pruebas_no_parametricas_oe3.csv` | Kruskal-Wallis, Mann-Whitney U y Wilcoxon |
| `docx/graficas/tabla_criterios_seleccion_oe3.png` | Tabla grafica de comparativa canonica PPO/A2C/SAC |
| `docx/graficas/tabla_co2_componentes_ppo_ep49.png` | Resumen grafico CO2 del PPO episodio 49 |
| `sac_training/timeseries_sac.csv`, `sac_training/trace_sac.csv` | Trazas SAC versionadas con Git LFS por reproducibilidad |

## Archivos retirados

Los informes Word y figuras que indicaban SAC/A2C como seleccionados fueron retirados del control de
versiones para evitar reportes desactualizados en GitHub. Para generar informes nuevos, consultar:

- `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md`
- `reports/oe3/agents_comparison_canonical.json`
- `reports/oe3/agents_comparison_canonical.csv`
