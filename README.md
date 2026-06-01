# pvbesscar — Optimización RL de Carga EV con Solar y BESS en Iquitos

Proyecto de tesis que optimiza la carga de vehículos eléctricos (270 motos + 39 mototaxis/día,
38 sockets) usando solar PV (4,162 kWp DC / 3,201 kW AC; 5.819 GWh/año) + BESS (2,000 kWh / 400 kW)
mediante agentes de Aprendizaje por Refuerzo (SAC, PPO, A2C) en la red aislada de Iquitos
(factor CO₂: 0.4521 kg CO₂/kWh — red térmica diesel, Electro Oriente S.A.).

## Estado Canónico

| Campo | Valor |
|---|---|
| **Actualizado** | 2026-05-31 |
| **Branch activo** | `smartcharger` |
| **Entrenamiento** | ✅ Completado — 50 episodios × 3 agentes (N=150) |
| **obs_dim** | **19** (base=12 CityLearn + 5 EV dims + 2 tarifa — incluye `electricity_pricing`) |
| **pv_kwp** | **4,162 kWp DC** (Jinko Tiger Neo JKM580N-72HL4-BDV + 8.7% bifacial) |
| **Reward** | CO2_DUAL_FOCUS v8.1 (7 componentes, Σ=1.00) |
| **Agente seleccionado OE3** | **A2C** — 6/9 criterios multiobjetivo, 48.36% reducción CO₂ vs F0 |
| **Fuente canónica** | `reports/oe3/agents_comparison_canonical.json` |
| **Informe tesis DOCX** | `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx` (2.9 MB, versionado en esta rama) |

---

## OE3 — Resultados del Entrenamiento (obs_dim=19, CO2_DUAL_FOCUS v8.1)

### Baseline de referencia

| Baseline | CO₂ (kg/año) | Descripción |
|---|---:|---|
| **F0** | **7,053,999** | Sin solar, sin BESS, sin RL — flota ICE completa |
| **F1** | ~5,300,000 | Sin RL (baseline no controlado, solo solar+BESS pasivos) |

### Ranking multiobjetivo — 50 episodios/agente

| Rank | Agente | F2 mín (kg/año) | F2 medio (kg/año) | CO₂ evitado 50ep | % red. vs F0 | Criterios | |
|---:|---|---:|---:|---:|---:|---:|---|
| **1** | **A2C** | **3,642,436** | **3,681,582 ± 26,971** | **123,017,056 kg** | **48.36%** | **6/9** | ★ SELECCIONADO |
| 2 | PPO | 3,658,366 | 3,691,968 ± 60,896 | 123,122,792 kg | 48.14% | 3/9 | |
| 3 | SAC | 3,695,754 | 3,713,975 ± 45,577 | 121,199,821 kg | 47.61% | 0/9 | |

### Convergencia del entrenamiento

| Agente | Tiempo GPU | Ep. conv. | Mejor ep | Reward plateau | CV plateau | Val. reward |
|---|---:|---:|---:|---:|---:|---:|
| **A2C** | **22.5 min** | ep 16 | ep 43 (1,681.6) | 1,676.7 ± 2.7 | 0.16% | 1,647.04 |
| PPO | 23.5 min | ep 22 | ep 50 (1,674.7) | 1,643.4 ± 2.9 | 0.14% | 1,619.44 |
| SAC | 181 min | ep 9 | ep 35 (1,469.2) | 1,455.0 ± 3.9 | 0.27% | 1,520.92 |

### Resultados operativos clave (media por episodio, n=50)

| Métrica | A2C | PPO | SAC |
|---|---:|---:|---:|
| CO₂ total evitado/ep (kg) | **2,460,341** | 2,462,456 | 2,423,996 |
| CO₂ directo evitado — 50ep (kg) | **10,873,530** | 10,608,490 | 10,561,551 |
| CO₂ indirecto evitado — 50ep (kg) | 112,143,526 | **112,514,302** | 110,638,270 |
| Grid import/ep (kWh/año) | **7,385,447** ← menor | 7,409,616 | 7,409,893 |
| EV motos — 50ep (kWh) | **11,259,985** | 10,608,490 | 11,003,146 |
| EV mototaxis — 50ep (kWh) | **1,995,080** | 1,879,821 | 1,831,137 |
| EV equiv. total — 50ep | **4,302,379** | 4,197,493 | 4,178,910 |
| BESS descarga — 50ep (kWh) | 31,615,038 | **32,718,773** | 30,040,467 |
| Debt violations — 50ep | **1,001** | 2,219 | 1,405 |
| Zero-violation episodes | 24 | 37 | **45** |

### 9 criterios multiobjetivo — ganador por criterio

| Criterio | Modo | Ganador |
|---|---|---|
| Mayor CO₂ total evitado (50ep) | max | PPO |
| Menor importación de red | min | **A2C** |
| Mayor CO₂ directo evitado | max | **A2C** |
| Mayor CO₂ indirecto evitado | max | PPO |
| Mayor carga motos equivalentes | max | **A2C** |
| Mayor carga mototaxis equivalentes | max | **A2C** |
| Mayor carga EV total equivalente | max | **A2C** |
| Mayor uso útil BESS | max | PPO |
| Menor deuda/violaciones de carga | min | **A2C** |

**A2C: 6 criterios | PPO: 3 criterios | SAC: 0 criterios → A2C seleccionado**

---

## Metodología de investigación del proyecto

- **Enfoque:** Cuantitativo, porque cobertura, demanda, potencia PV, capacidad BESS, cargadores, energía EV, grid import, costos y CO₂ evitado se miden numéricamente y se contrastan con estadística descriptiva e inferencial (Hernández Sampieri et al., 2014).
- **Tipo:** Aplicada, porque resuelve el problema de diseñar una infraestructura de carga inteligente EV+BESS+solar y su control RL para reducir CO₂ en Iquitos (Murillo Vargas, 2010; Arias, 2012).
- **Nivel:** Explicativo-causal, porque explica cómo la infraestructura y la estrategia de control producen cambios medibles en CO₂, carga EV, importación de red y uso del BESS (Hernández Sampieri et al., 2014; Tamayo y Tamayo, 2003).
- **Diseño único:** Cuasi-experimental por simulación para todo el proyecto. OE1, OE2 y OE3 son etapas del mismo diseño: ubicación estratégica, dimensionamiento técnico y comparación de tratamientos RL en simulación controlada (Campbell & Stanley, 1966; Hernández Sampieri et al., 2014; Law, 2015; Montgomery, 2017).
  - Variable independiente: infraestructura de carga inteligente EV+BESS+solar con estrategia de control RL
  - Manipulación operativa en simulación: tipo de algoritmo RL (3 tratamientos: SAC, PPO, A2C)
  - Variables dependientes medidas: CO₂ total evitado, carga EV motos/mototaxis, grid import, BESS
  - Variables controladas: solar 5.819 GWh, BESS 2,000 kWh/400 kW, factor CO₂ 0.4521 kg/kWh
- **Muestra:** n=50 episodios/agente (N=150) — saturación estadística verificada por CV plateau <0.5%
- **Pruebas inferenciales:**
  - Shapiro-Wilk → Kruskal-Wallis → Dunn Bonferroni
  - Mann-Whitney U (muestras independientes, one-tailed, p propio)
  - Wilcoxon signed-rank (muestras pareadas, p propio e independiente)
  - Cohen d + Cliff delta + Bootstrap IC 95% (B=10,000)

**Documento completo:** [reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md](reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md)

**Informe Word vigente:** [outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx](outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx)

---

## Análisis Estadístico Inferencial (18 variables, α=0.05)

### Normalidad — Shapiro-Wilk

Todas las distribuciones rechazan normalidad (p < 0.05) → pruebas no paramétricas en todos los análisis.

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| SAC | 0.7458 | 6.07×10⁻⁸ | No |
| PPO | 0.7946 | 6.58×10⁻⁷ | No |
| A2C | 0.9329 | 7.10×10⁻³ | No |

### Prueba global — Kruskal-Wallis

| Variable | H | p-valor | Conclusión |
|---|---:|---:|---|
| CO₂ total evitado | **91.62** | **1.27×10⁻²⁰** | Diferencias globales muy significativas |
| CO₂ directa | 42.40 | 6.20×10⁻¹⁰ | Significativo |
| CO₂ indirecta | 96.34 | 1.09×10⁻²¹ | Muy significativo |
| EV total | 52.31 | 4.18×10⁻¹² | Significativo |
| Mototaxis | 55.08 | 1.12×10⁻¹² | Significativo |
| BESS descarga | 62.77 | 2.29×10⁻¹⁴ | Significativo |
| Grid import | 18.74 | 8.59×10⁻⁵ | Significativo |
| F2 residual CO₂ | 54.20 | 1.70×10⁻¹² | Significativo |

### Mann-Whitney U (independiente, one-tailed)

| Comparación | U | p-valor | Decisión |
|---|---:|---:|---|
| A2C > SAC (CO₂ total) | 2,462 | **3.36×10⁻¹⁷** | ✓ Rechaza H₀ |
| PPO > SAC (CO₂ total) | 2,417 | **4.43×10⁻¹⁶** | ✓ Rechaza H₀ |
| A2C > PPO (CO₂ total) | 947 | 0.982 NS | No rechaza H₀ — equivalentes |
| A2C > PPO (mototaxis) | — | — | → Wilcoxon (desempate) |
| PPO < SAC (F2 residual) | 419 | **5.16×10⁻⁹** | ✓ PPO mejor F2 puntual |
| A2C < SAC (F2 residual) | 257 | **3.90×10⁻¹²** | ✓ A2C mejor F2 que SAC |

### Wilcoxon signed-rank (pareado ep₁…ep₅₀)

| Comparación | W | p-valor | Decisión | Cohen d |
|---|---:|---:|---|---:|
| A2C > PPO (mototaxis) | 994 | **1.99×10⁻⁴** | ✓ **DESEMPATE — define selección** | 0.318 small |
| A2C > PPO (BESS) | — | 0.029 | ✓ significativo | −0.299 small |
| A2C > PPO (solar→EV) | — | 0.019 | ✓ significativo | 0.251 small |
| A2C > PPO (CO₂ total) | 447 | 0.968 NS | No rechaza H₀ | −0.142 negligible |

### Tamaños del efecto — A2C vs SAC

| Variable | Cohen d | Magnitud | Cliff δ | Magnitud | IC 95% Bootstrap |
|---|---:|---|---:|---|---|
| CO₂ total evitado | 2.826 | very large | **0.970** | large | [31,550; 41,581] kg |
| CO₂ indirecta | 3.246 | very large | 0.934 | large | [33,750; 42,854] kg |
| EV total | 0.782 | large | 0.814 | large | confirmado |
| Mototaxis | 0.823 | large | 0.829 | large | confirmado |

**A2C domina a SAC en el 97% de los pares episódicos (Cliff δ=0.970).**

Reporte estadístico completo: [outputs/estadistica_oe3/reporte_estadistico_oe3.md](outputs/estadistica_oe3/reporte_estadistico_oe3.md)

---

## Control operativo BESS/EV — por qué A2C gana

| Hora | Contexto | A2C grid (kWh/h) | PPO grid (kWh/h) | SAC grid (kWh/h) |
|---|---|---:|---:|---:|
| h06–h17 | Solar + carga BESS (HFP) | ~620–800 | ~580–750 | ~610–780 |
| h18 | Inicio HP — BESS descarga | **~287** | ~1,909 | ~420 |
| h19–h21 | HP pico — peak-shaving | **~400–693** | ~1,960–2,011 | ~440–456 |
| h22–h23 | Fin HP | **~350–500** | ~1,800–1,900 | ~380–440 |
| h00–h05 | Noche — BESS recarga | ~620–2,114 | ~435–531 | ~580–650 |

A2C entra al HP con BESS SOC=0.88–0.94 (pre-cargado en solar), absorbiendo el pico.
PPO concentra la carga EV en HP, creando pico de importación **3–7× mayor**.
SAC evita parcialmente HP pero a costa de debt_violations en primeros episodios.

Reporte operativo: [reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md](reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md)

---

## Función de recompensa — CO2_DUAL_FOCUS v8.1

```python
# src/citylearnv2/ev_charging_wrapper.py — ÚNICA FUENTE de pesos para SAC/PPO/A2C
_W_DIRECT_CO2   = 0.20  # CO₂ directa: ICE→EV (transporte)
_W_INDIRECT_CO2 = 0.30  # CO₂ indirecta: grid_import × 0.4521 kg/kWh
_W_EV_COMPLETE  = 0.35  # EV satisfaction: motos + mototaxis sin deuda
_W_BESS_SOLAR   = 0.07  # BESS carga desde solar, no diesel nocturno
_W_SOLAR        = 0.04  # Autoconsumo PV directo
_W_GRID_STABLE  = 0.02  # Suavizado rampas grid_import
_W_COST         = 0.02  # Costo tarifario OSINERGMIN HP(0.46)/HFP(0.29 S./kWh)
# Suma = 1.00 — los 3 agentes usan exactamente los mismos pesos
```

---

## OE2 — Dimensionamiento validado

| Componente | Valor |
|---|---:|
| Solar PV DC (PVWatts pdc0) | **4,162 kWp DC** / 3,201 kW AC |
| Energía solar anual | 5,819,332 kWh/año (yield=1,398 kWh/kWp, PR=83.5%) |
| BESS | 2,000 kWh / 400 kW (DoD 80%, SOC mín 20%) |
| Cargadores | 19 × 2 sockets = 38 puntos (socket_000–socket_037) |
| Flota diaria | 270 motos + 39 mototaxis |
| Factor CO₂ Iquitos | 0.4521 kg CO₂/kWh (red térmica diesel, MINEM 2024) |
| Tarifa HP (18-23h) | 0.46 S./kWh — OSINERGMIN Res. 047-2024-OS/CD |
| Tarifa HFP | 0.29 S./kWh |
| Dataset horario | 8,760 filas/año (2024) |
| Tests OE2 | 106 passed — `python -m pytest tests -v -ra` |

Referencia OE2: [docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md](docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md)

---

## Comandos

```powershell
# Entorno (Python 3.11 estrictamente)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Tests OE2 + integración
python -m pytest tests -q

# ── OE3 — cadena completa (un comando) ──────────────────────────────────────
python scripts/reporting/run_all_oe3.py
# Genera/actualiza automáticamente:
#   reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md
#   reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md
#   outputs/estadistica_oe3/reporte_estadistico_oe3.md
#   outputs/estadistica_oe3/tabla_completa_estadistica_oe3.csv
#   outputs/docx/graficas/*.png  (12 figuras)

# ── Informe de tesis OE3 (Word .docx) ──────────────────────────────────────
python scripts/reporting/generar_informe_tesis_oe3.py
# → outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx (2.9 MB)

# ── OE3 — scripts individuales ──────────────────────────────────────────────
python scripts/analysis/demostracion_estadistica_oe3.py   # pruebas inferenciales (18 variables)
python scripts/analysis/control_operativo_bess_ev_oe3.py  # BESS/EV/pico por hora
python scripts/analysis/analizar_co2_trace_oe3.py         # CO2 directo+indirecto trace
python scripts/reporting/comparativa_agentes_co2_trace.py # figuras convergencia (6 PNGs)
python scripts/reporting/generar_tablas_oe3.py            # tablas PNG canónicas

# ── OE2 — regenerar datasets ────────────────────────────────────────────────
python scripts/generate_oe2_datasets.py --loader-only

# ── Entrenamiento RL (50 episodios cada uno) ────────────────────────────────
python scripts/train/train_a2c_citylearn.py  # ~22.5 min GPU (CUDA RTX 4060)
python scripts/train/train_ppo_citylearn.py  # ~23.5 min GPU
python scripts/train/train_sac_citylearn.py  # ~181 min GPU

# ── Verificación datos ──────────────────────────────────────────────────────
python scripts/verification/verify_citylearn_data.py
```

### API Docker operativa y simulación visible

```powershell
# Levantar API A2C + MongoDB en la rama actual
docker compose -f docker-compose.dev.yml --env-file .env.local up -d --build

# Generar evidencia visible con trace horario multiobjetivo
python scripts/reporting/generar_reporte_api_docker.py
# → outputs/api_docker_test/latest/index.html
# → outputs/api_docker_test/latest/figuras/resumen_operativo.png
# → outputs/api_docker_test/latest/figuras/control_tiempo_real.png
# → outputs/api_docker_test/latest/trace_simulacion.csv

# Dashboard WebSocket para ver la ejecución en tiempo real
start http://localhost:8000/dashboard/realtime
```

La simulación API expone los pesos multiobjetivo y los valores anuales de CO₂ directa,
CO₂ indirecta, servicio EV/deuda, control BESS, autoconsumo solar, estabilidad de red,
costo OSINERGMIN, tomas activas, despacho PV→EV/BESS→EV/Grid→EV y trace horario para
graficar control BESS, uso de solar, balance energético y reducción de CO₂.

---

## Figuras generadas

| Figura | Ruta | Descripción |
|---|---|---|
| `figura_pruebas_estadisticas_oe3.png` | `outputs/docx/graficas/` | Boxplots, Mann-Whitney, Cohen d, Bootstrap IC 95% |
| `co2_convergencia_reward.png` | `outputs/docx/graficas/` | Reward por episodio A2C/PPO/SAC (rolling mean 10ep) |
| `co2_indirecto_residual.png` | `outputs/docx/graficas/` | F2 CO₂ indirecto residual por episodio |
| `co2_evitado_total_trace.png` | `outputs/docx/graficas/` | CO₂ total evitado por episodio |
| `grid_import_episodios.png` | `outputs/docx/graficas/` | Importación de red por episodio (kWh) |
| `co2_comparativa_multicriterio.png` | `outputs/docx/graficas/` | Panel 4 criterios multiobjetivo |
| `sac_convergencia_estable_inferior.png` | `outputs/docx/graficas/` | Diagnóstico SAC vs A2C/PPO |
| `control_operativo_bess_ev_oe3.png` | `outputs/docx/graficas/` | Patrón BESS/EV/pico por hora del día |
| `costos_tarifarios_oe3.png` | `outputs/docx/graficas/` | Costos OSINERGMIN HP/HFP por agente |
| `estabilidad_red_oe3.png` | `outputs/docx/graficas/` | Rampas y variabilidad grid_import |
| `tabla_criterios_seleccion_oe3.png` | `outputs/docx/graficas/` | Tabla canónica criterios OE3 |
| `tabla_co2_componentes_ppo_ep49.png` | `outputs/docx/graficas/` | Desglose CO₂ PPO episodio 49 (mejor F2 puntual) |

---

## Rutas Canónicas

| Propósito | Ruta |
|---|---|
| Comparativa canónica OE3 | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` |
| JSON canónico OE3 | `reports/oe3/agents_comparison_canonical.json` |
| CSV canónico OE3 | `reports/oe3/agents_comparison_canonical.csv` |
| CO₂ directo/indirecto trace | `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` |
| Control operativo BESS/EV | `reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md` |
| Costos + estabilidad OE3 | `reports/oe3/COSTOS_ESTABILIDAD_OE3.md` |
| Metodología investigación | `reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md` |
| Reporte estadístico | `outputs/estadistica_oe3/reporte_estadistico_oe3.md` |
| Tabla estadística CSV | `outputs/estadistica_oe3/tabla_completa_estadistica_oe3.csv` |
| Informe tesis DOCX | `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx` |
| Figuras tesis | `outputs/docx/graficas/` |
| Solar OE2 | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` |
| Cargadores OE2 | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` |
| BESS OE2 | `data/oe2/bess/bess_ano_2024.csv` |
| Dataset CityLearn | `data/iquitos_ev_mall/` |

## Política de Artefactos

Los resultados de entrenamiento completos (`outputs/*_training/`, trazas, checkpoints) son
artefactos generados — no son fuente documental primaria en GitHub. La fuente versionada
para informes y consultas es `reports/oe3/`. Los CSV grandes usan Git LFS (`.gitattributes`).
