# Diagnostico SAC v8.2 y plan de mejora OE3

**Fecha local:** 2026-05-31
**Alcance:** SAC sobre Iquitos PV-BESS-EV, comparado con PPO y A2C entrenados con el mismo entorno.
**Estado:** Reentrenamiento limpio SAC v8.2 completado y verificado.

## 1. Verificacion de datos reales y objetivo multiobjetivo

SAC, PPO y A2C usan la misma fabrica de entorno:

- `scripts/train/train_sac_citylearn.py` -> `create_iquitos_env_for_sb3()`
- `scripts/train/train_ppo_citylearn.py` -> `create_iquitos_env_for_sb3()`
- `scripts/train/train_a2c_citylearn.py` -> `create_iquitos_env_for_sb3()`

Esa fabrica construye `IquitosEVChargingWrapper(CityLearnEnv)`, con observacion 18D y accion 3D:

- `action[0]`: despacho BESS.
- `action[1]`: fraccion de carga de motos.
- `action[2]`: fraccion de carga de mototaxis.

Los datos reales vigentes vienen de:

- `data/iquitos_ev_mall/`
- `data/interim/citylearn_v2/`

Archivos verificados:

- `data/iquitos_ev_mall/solar_generation.csv`
- `data/iquitos_ev_mall/chargers_timeseries.csv`
- `data/iquitos_ev_mall/mall_demand.csv`
- `data/iquitos_ev_mall/bess_timeseries.csv`
- `data/iquitos_ev_mall/co2_emissions.csv`
- `data/iquitos_ev_mall/tariffs_osinergmin.csv`
- `data/interim/citylearn_v2/energy_simulation.csv`
- `data/interim/citylearn_v2/weather.csv`
- `data/interim/citylearn_v2/carbon_intensity.csv`
- `data/interim/citylearn_v2/ev_charger_motos.csv`
- `data/interim/citylearn_v2/ev_charger_mototaxis.csv`
- `data/interim/citylearn_v2/tariffs_osinergmin.csv`
- `data/interim/citylearn_v2/schema_iquitos.json`

La recompensa real activa es `CO2_DUAL_FOCUS v8.1`:

| Componente | Peso |
|---|---:|
| CO2 directa evitada | 0.20 |
| CO2 indirecta por importacion de red | 0.30 |
| Cumplimiento de carga EV | 0.35 |
| BESS cargando con solar, no diesel nocturno | 0.07 |
| Autoconsumo solar | 0.04 |
| Estabilidad de red | 0.02 |
| Costo OSINERGMIN | 0.02 |
| **Total** | **1.00** |

## 2. Evidencia usada

El diagnostico se basa en checkpoints, resultados y traces guardados:

| Tipo | Archivo/directorio | Uso |
|---|---|---|
| SAC v8.2 vigente | `outputs/sac_training/result_sac.json` | Hiperparametros, validacion, duracion y ruta `VecNormalize`. |
| Trace SAC v8.2 | `outputs/sac_training/trace_sac.csv` | CO2, solar, EV, grid y reward por hora. |
| Episodios SAC v8.2 | `outputs/sac_training/sac_episodios_history.csv` | F2, grid, BESS, CO2 directa/indirecta por episodio. |
| Checkpoint SAC v8.2 | `checkpoints/SAC_CityLearn/sac_final.zip` | Modelo final vigente. |
| Normalizacion SAC v8.2 | `checkpoints/SAC_CityLearn/vecnormalize.pkl` | Confirma normalizacion de entorno. |
| SAC anterior | `outputs/training_chain/20260530_221713_sac_v82/archive_previous/outputs__sac_training/` | Evidencia historica de resultados/traces anteriores. |
| Checkpoints SAC anteriores | Eliminados | Se eliminaron solo checkpoints archivados de SAC por instruccion del usuario. |
| PPO vigente | `outputs/ppo_training/result_ppo.json` y `checkpoints/PPO_CityLearn/ppo_final.zip` | Comparacion; no se tocaron checkpoints PPO. |
| A2C vigente | `outputs/a2c_training/result_a2c.json` y `checkpoints/A2C_CityLearn/a2c_final.zip` | Comparacion; no se tocaron checkpoints A2C. |
| Auditoria OE3 | `reports/oe3/AUDITORIA_FUENTES_CHECKPOINTS_OE3.md` | Confirma fuentes vigentes/no archive. |
| Canonico OE3 | `reports/oe3/agents_comparison_canonical.json` | Fuente para consultas de otros agentes. |

## 3. Por que SAC anterior tuvo malos resultados

SAC anterior si usaba datos reales actuales, pero su regimen era mas debil que PPO/A2C:

1. **No usaba `VecNormalize`.**
   El entorno mezcla escalas de energia, CO2, SOC, demanda EV y costos. Sin normalizacion, los critics
   Q de SAC reciben observaciones y rewards con magnitudes muy distintas.

2. **Horizonte temporal excesivo.**
   `gamma=0.99` en episodios anuales de 8,760 pasos dificulta estimar retornos estables. PPO usa
   `gamma=0.88` y A2C `gamma=0.90`.

3. **Exploracion conservadora.**
   `ent_coef="auto"` y `target_entropy=-3.0` tendian a reducir exploracion antes de explorar bien la
   combinacion BESS + motos + mototaxis.

4. **Replay buffer con transiciones tempranas suboptimas.**
   SAC es off-policy. Si los primeros episodios cargan mal BESS/EV, el buffer sigue entrenando con esas
   decisiones.

5. **Critic menos expresivo.**
   La arquitectura anterior `[256,256]` era menor para una recompensa multiobjetivo con CO2, EV,
   estabilidad, solar y costo.

6. **Resume de checkpoints no robusto.**
   El script ordenaba checkpoints lexicograficamente; en reanudaciones podia elegir un checkpoint no
   numericamente mas avanzado.

## 4. Ajustes aplicados en SAC v8.2

| Parametro | SAC anterior | SAC v8.2 |
|---|---:|---:|
| Normalizacion entorno | No | `VecNormalize(norm_obs=True, norm_reward=True)` |
| `learning_rate` | `5e-5` | `1e-4` |
| `buffer_size` | `100000` | `87600` |
| `learning_starts` | `8760` | `17520` |
| `batch_size` | `256` | `512` en CUDA |
| `gamma` | `0.99` | `0.95` |
| `tau` | `0.005` | `0.01` |
| `gradient_steps` | `1` | `2` |
| `ent_coef` | `auto` | `auto_0.2` |
| `target_entropy` | `-3.0` | `-2.0` |
| Actor | `[256,256]` | `pi=[256,256,128]` |
| Critic | `[256,256]` | `qf=[512,512,256]` |
| `max_grad_norm` | `5.0` | `1.0` |
| Resume checkpoint | Lexicografico | Numerico por steps |
| Modo limpio | No | `--fresh` |

Comando ejecutado:

```powershell
python scripts\train\train_sac_citylearn.py --fresh --timesteps 438000
```

## 5. Resultado SAC antes vs despues

| Version SAC | Steps | Mejor F2 kg CO2/año | Episodio | F2 media kg/año | Reward validacion | CO2 evitado validacion kg | Grid validacion kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| SAC anterior | 438,000 | 3,720,640 | 33 | 3,747,127 | 1,519.15 | 2,400,665 | 7,456,699 |
| SAC v8.2 | 438,000 | **3,693,084** | **17** | **3,711,823** | 1,517.13 | **2,438,610** | **7,345,854** |

Mejoras SAC v8.2:

- `F2` baja **27,556 kg CO2/año**.
- `F2` medio baja **35,304 kg CO2/año**.
- CO2 evitado de validacion sube **37,944 kg CO2/año**.
- Grid import de validacion baja **110,845 kWh/año**.
- El entrenamiento fue limpio: `fresh_start=true`, sin append del trace anterior.

La recompensa de validacion baja levemente de 1,519.15 a 1,517.13. Eso no invalida la mejora en
CO2/grid; muestra que el reward multiobjetivo todavia distribuye peso entre CO2, cumplimiento EV,
BESS, estabilidad y costo.

## 6. Comparacion final con PPO y A2C

| Rank | Agente | F2 minimo kg CO2/año | Episodio | CO2 evitado vs F0 | Reward validacion | Grid validacion kWh | CV plateau |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | **PPO** | **3,657,484** | **49** | **3,396,515** | 1,628.46 | 7,348,969 | **0.034%** |
| 2 | A2C | 3,659,010 | 45 | 3,394,989 | **1,633.29** | **7,337,811** | 0.422% |
| 3 | SAC v8.2 | 3,693,084 | 17 | 3,360,915 | 1,517.13 | 7,345,854 | 0.036% |

SAC v8.2 ya no esta tan lejos como el SAC anterior, pero sigue emitiendo:

- **35,600 kg CO2/año** mas que PPO.
- **34,074 kg CO2/año** mas que A2C.

La seleccion canonica sigue siendo **PPO** porque tiene el menor `F2`. A2C queda como mejor en grid
validation y CO2 total evitado desde trace, pero no supera a PPO en `F2`.

## 7. Plan de mejora siguiente para SAC

Si se necesita una tercera corrida SAC, el plan recomendado es:

1. Mantener `VecNormalize` obligatorio y guardar `vecnormalize.pkl` junto al modelo.
2. Probar `gamma` en `[0.90, 0.93, 0.95]` para acercar SAC al horizonte efectivo de PPO/A2C.
3. Probar `ent_coef` inicial en `auto_0.3` y `auto_0.5` para sostener exploracion.
4. Reducir memoria temprana del replay con `buffer_size=52,560` o usar curriculum de warmup.
5. Evaluar `learning_starts=26,280` para que el critic vea tres meses antes de actualizar.
6. Mantener critics anchos y actor moderado.
7. Reportar siempre tres criterios separados: menor `F2`, CO2 total evitado desde trace y grid
   validation.

## 8. Estado final de archivos

- `checkpoints/SAC_CityLearn/sac_final.zip`: vigente.
- `checkpoints/SAC_CityLearn/vecnormalize.pkl`: vigente.
- `outputs/sac_training/result_sac.json`: vigente.
- `outputs/sac_training/trace_sac.csv`: vigente.
- `outputs/sac_training/timeseries_sac.csv`: vigente.
- `outputs/training_chain/20260530_221713_sac_v82/archive_previous/checkpoints__SAC_CityLearn/`: eliminado.
- `checkpoints/PPO_CityLearn/`: intacto.
- `checkpoints/A2C_CityLearn/`: intacto.

**Conclusion:** SAC v8.2 fue corregido y mejoro de forma medible, pero no gana. El agente OE3
seleccionado para reportes y consultas externas sigue siendo **PPO**.
