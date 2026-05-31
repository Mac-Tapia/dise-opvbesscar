# pvbesscar — Optimización RL de Carga EV con Solar y BESS en Iquitos

Proyecto de tesis que optimiza la carga de vehículos eléctricos (270 motos + 39 mototaxis/día,
38 sockets) usando solar PV (4,162 kWp DC / 3,201 kW AC; 5.819 GWh/año) + BESS (2,000 kWh / 400 kW)
mediante agentes de Aprendizaje por Refuerzo (SAC, PPO, A2C) en la red aislada de Iquitos
(factor CO₂: 0.4521 kg CO₂/kWh — red térmica diesel).

## Estado Canónico

| Campo | Valor |
|---|---|
| **Actualizado** | 2026-05-31 |
| **Branch activo** | `smartcharger` |
| **Entrenamiento activo** | A2C ep 17/50 — pipeline desde cero con obs_dim=19 |
| **obs_dim** | **19** (base=12 CityLearn + 5 EV dims + 2 tarifa) — incluye `electricity_pricing` |
| **pv_kwp** | **4,162 kWp DC** (único valor canónico — eliminado 4,050 legacy) |
| **Agente OE3 histórico** | A2C — score multiobjetivo 50 eps (obs_dim=18, referencia anterior) |
| **Fuente canónica** | `reports/oe3/agents_comparison_canonical.json` (se regenerará post-entrenamiento) |

## Resultado OE3 — Entrenamiento activo (obs_dim=19, pricing activo)

> **Entrenamiento en curso (2026-05-31):** Pipeline completo desde cero con la nueva
> arquitectura (obs_dim=19, `electricity_pricing` como observación, `pricing.csv` vinculado
> al schema CityLearn v2, `oe2_metadata.py` — valores auto-leídos de JSONs reales).

**Progreso actual:**
- A2C ep 17/50 → F2=3,674,242 kg CO₂/año (38.7% vs F0) | convergiendo
- PPO: pendiente (inicia al terminar A2C ~2:55 PM)
- SAC: pendiente (~3:00 PM)

**Referencia histórica (obs_dim=18 — antes del 2026-05-31 tarde):**

| Rank | Agente | CO₂ evitado 50ep (kg) | EV equiv. | Criterios |
|---:|---|---:|---:|---:|
| 1 | **A2C** | **122,980,987** | **4,307,304** | **9/9** |
| 2 | PPO | 122,688,120 | 4,203,700 | 0/9 |
| 3 | SAC | 121,316,857 | 4,180,962 | 0/9 |

F2 histórico: PPO ep49=3,657,484 | A2C ep45=3,659,010 | SAC ep17=3,693,084 kg CO₂/año

## Metodología de investigación (OE3)

- **Tipo:** Aplicada, cuantitativa
- **Nivel:** Explicativo-causal
- **Diseño:** Cuasi-experimental por simulación (Hernández Sampieri et al., 2014; Campbell & Stanley, 1966)
  - Variable independiente manipulada: tipo de algoritmo RL (3 tratamientos: SAC, PPO, A2C)
  - Variables dependientes medidas: CO₂ total evitado, carga EV motos/mototaxis, grid import, BESS
  - Variables controladas: solar 5.819 GWh, BESS 2000 kWh/400 kW, factor CO₂ 0.4521 kg/kWh
- **Muestra:** n=50 episodios/agente (N=150) — saturación estadística verificada por CV plateau <0.5%
- **Pruebas inferenciales:**
  - Shapiro-Wilk → Kruskal-Wallis → Dunn Bonferroni
  - Mann-Whitney U (muestras independientes, p-valor propio)
  - Wilcoxon signed-rank (muestras pareadas, p-valor propio e independiente)
  - Cohen d + Cliff delta + Bootstrap IC 95% (B=10,000)

**Documento completo:** [reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md](reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md)

## Pruebas estadísticas — resumen inferencial

| Comparación | Mann-Whitney U p | Wilcoxon p | Cliff δ | Decisión |
|---|---:|---:|---:|---|
| A2C > SAC (CO₂ total) | **8.78×10⁻¹²** | **6.77×10⁻¹³** | 0.781 large | **Rechaza H₀** |
| PPO > SAC (CO₂ total) | **1.11×10⁻¹⁰** | **1.41×10⁻⁹** | 0.737 large | **Rechaza H₀** |
| A2C > PPO (CO₂ total) | 0.240 | 0.109 | 0.082 negligible | No rechaza H₀ — equivalentes |
| A2C > PPO (mototaxis) | **0.016** | **1.99×10⁻⁴** | 0.250 small | **Rechaza H₀** ← define selección |
| Todo RL > F1 baseline | **<10⁻¹⁵** | — | >40 gigante | **Rechaza H₀** |

Reporte estadístico completo: [outputs/estadistica_oe3/reporte_estadistico_oe3.md](outputs/estadistica_oe3/reporte_estadistico_oe3.md)

## Control operativo BESS/EV — por qué A2C gana

| Hora | Contexto | A2C grid (kWh) | PPO grid (kWh) | SAC grid (kWh) |
|---|---|---:|---:|---:|
| h18–h21 | Hora punta (HP) | **287–693** | 1,909–2,011 | 420–456 |
| h00–h06 | Noche (BESS descarga) | 620–2,114 | 435–531 | — |

A2C entra al HP con BESS cargado (SOC 0.88–0.94), absorbiendo el pico.
PPO concentra la carga EV en HP, creando pico de importación alto.
SAC evita el pico desconectando cargadores — no es control óptimo.

Reporte operativo: [reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md](reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md)

## OE2 — Dimensionamiento validado

| Componente | Valor |
|---|---:|
| Solar PV DC (PVWatts pdc0) | **4,162 kWp DC** / 3,201 kW AC (Jinko Tiger Neo JKM580N-72HL4-BDV + 8.7% bifacial) |
| Energía solar anual | 5,819,332 kWh/año (yield=1,398 kWh/kWp, PR=83.5%) |
| BESS | 2,000 kWh / 400 kW (DoD 80%, SOC mín 20%) |
| Cargadores | 19 × 2 sockets = 38 puntos (socket_000–socket_037) |
| Flota diaria | 270 motos + 39 mototaxis |
| Factor CO₂ Iquitos | 0.4521 kg CO₂/kWh (red térmica diesel) |
| Dataset horario | 8,760 filas/año (2024) |

Referencia OE2: [docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md](docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md)

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
#   outputs/docx/graficas/*.png  (11 figuras)

# ── OE3 — scripts individuales ──────────────────────────────────────────────
python scripts/analysis/demostracion_estadistica_oe3.py   # pruebas inferenciales completas
python scripts/analysis/control_operativo_bess_ev_oe3.py  # BESS/EV/pico por hora
python scripts/analysis/analizar_co2_trace_oe3.py         # CO2 directo+indirecto trace
python scripts/reporting/comparativa_agentes_co2_trace.py # figuras convergencia
python scripts/reporting/generar_tablas_oe3.py            # tablas PNG canónicas

# ── OE2 — regenerar datasets ────────────────────────────────────────────────
python scripts/generate_oe2_datasets.py --loader-only

# ── Entrenamiento RL ────────────────────────────────────────────────────────
python scripts/train/train_ppo_citylearn.py
python scripts/train/train_a2c_citylearn.py
python scripts/train/train_sac_citylearn.py

# ── Verificación datos ──────────────────────────────────────────────────────
python scripts/verification/verify_citylearn_data.py
```

## Rutas Canónicas

| Propósito | Ruta |
|---|---|
| Comparativa canónica OE3 | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` |
| JSON canónico OE3 | `reports/oe3/agents_comparison_canonical.json` |
| CSV canónico OE3 | `reports/oe3/agents_comparison_canonical.csv` |
| CO₂ directo/indirecto trace | `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` |
| Control operativo BESS/EV | `reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md` |
| Metodología investigación | `reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md` |
| Reporte estadístico | `outputs/estadistica_oe3/reporte_estadistico_oe3.md` |
| Tabla estadística CSV | `outputs/estadistica_oe3/tabla_completa_estadistica_oe3.csv` |
| Figuras tesis | `outputs/docx/graficas/` |
| Solar OE2 | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` |
| Cargadores OE2 | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` |
| BESS OE2 | `data/oe2/bess/bess_ano_2024.csv` |
| Dataset CityLearn | `data/iquitos_ev_mall/` |

## Política de Artefactos

Los resultados de entrenamiento completos (`outputs/*_training/`, trazas, checkpoints) son
artefactos generados — no son fuente documental primaria en GitHub. La fuente versionada
para informes y consultas es `reports/oe3/`. Los CSV grandes usan Git LFS (`.gitattributes`).
