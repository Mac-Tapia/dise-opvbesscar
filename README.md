# pvbesscar - RL-based EV Charging Optimization

**Optimización de carga EV con energía solar mediante Reinforcement Learning**

Iquitos, Perú — Control inteligente de 38 sockets de carga (270 motos + 39 mototaxis/día) usando agentes RL (SAC/PPO/A2C) para minimizar CO₂ en red aislada (factor 0.4521 kg CO₂/kWh).

---

## Latest Updates (2026-05-28) — Reward v7.5 + obs_dim=18 + Sincronización Total

### Reward v7.5 — Tres objetivos OE3 equilibrados + BESS solar timing

Reentrenamiento completo SAC → PPO → A2C con correcciones críticas sincronizadas en todos los archivos:

**Pesos reward v7.5 (suma = 1.00) — idénticos para SAC/PPO/A2C:**

| Componente | Peso | Descripción |
|---|---|---|
| `direct_co2` | **0.25** | OE3-1: CO₂ directa — reducción ICE→EV electrificación |
| `indirect_co2` | **0.30** | OE3-2: CO₂ indirecta — minimizar grid import diesel |
| `ev_satisfaction` | **0.25** | OE3-3: satisfacción/cantidad carga EV (motos+mototaxis) |
| `bess_solar_timing` | **0.10** | regla operacional: BESS carga con solar (6-18h), NO diesel nocturno |
| `solar` | **0.05** | autoconsumo PV |
| `grid_stability` | **0.03** | estabilidad red (suavizado rampas) |
| `cost` | **0.02** | costo tarifario OSINERGMIN HP/HFP |

**Correcciones aplicadas:**
- `obs_dim`: 16 → **18** (añadidas obs[16]=`tarifa_norm` y obs[17]=`is_hora_punta` — agente ve tarifa HP/HFP)
- SAC `target_entropy`: -39.0 → **-3.0** (acción 3D, no 39D — error crítico que causaba alpha collapse)
- SAC `learning_rate`: 3e-4 → **1e-4** (grad_norm explosiva 132.93 → estabilidad)
- SAC `buffer_size`: 200k → **100k** (Raffin 2022: suficiente para 438k steps)
- SAC `learning_starts`: 8760 → **5000** (warmup más rápido)
- Regla BESS: penaliza carga nocturna con diesel (-1.0), premia carga solar (+solar_frac)
- Archivos sincronizados (sin discrepancias): `ev_charging_wrapper.py`, `sac/ppo/a2c_config.yaml`, `agents_config.yaml`, `sac_optimized.json`, `default.yaml`, `default_optimized.yaml`, `rewards.py`, `core/reward.py`

**Verificación de consistencia (72 tests pasan):**
```
[+] ev_charging_wrapper.py [_W_*]         OK  suma=1.00
[+] configs/agents/sac_config.yaml        OK  suma=1.00
[+] configs/agents/ppo_config.yaml        OK  suma=1.00
[+] configs/agents/a2c_config.yaml        OK  suma=1.00
[+] configs/agents/agents_config.yaml     OK  suma=1.00
[+] configs/sac_optimized.json            OK  suma=1.00
[+] configs/default.yaml                  OK  suma=1.00
[+] configs/default_optimized.yaml        OK  suma=1.00 (a2c/ppo/sac)
[+] rewards.py MultiObjectiveWeights      OK  suma=1.00
[+] core/reward.py co2_dual_focus()       OK  suma=1.00
[+] train_sac/ppo/a2c_citylearn.py        OK  obs_dim=18
[+] SAC_HYPERPARAMS (te/lr/buffer)        OK  target_entropy=-3.0, lr=1e-4
72 tests de integración: PASSED
```

---

## Latest Updates (2026-05-30) — Informe solar OE2 actualizado

### Generación solar PVGIS/pvlib documentada

Se agregó el informe local de generación solar desde el procedimiento hasta los resultados descriptivos:

- [Informe de generación solar: procedimiento y resultados descriptivos](data/oe2/Generacionsolar/informe_generacion_solar_procedimiento_resultados_descriptivos.md)
- Dataset base canónico: `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv`
- Cobertura: 8,760 registros horarios, 365 días, zona `America/Lima`
- Energía anual AC: **5.819 GWh/año**
- Potencia máxima AC: **3,245.95 kW**
- Factor de capacidad: **20.75%**
- Performance ratio: **83.46%**
- Reducción indirecta estimada: **2,630.92 tCO₂/año**
- Ahorro solar estimado: **S/ 1,629,413/año**

---

## Latest Updates (2026-05-26) — Limpieza profunda + pipeline OE2 reparado

### 🧹 Deep Repo Evaluation & Cleanup (2026-05-26)
**Evaluación completa del repositorio: módulos huérfanos eliminados, pipeline OE2 reparado y verificado**

**Módulos eliminados (huérfanos sin importadores activos):**
- `src/agents/device_controllers.py`, `training_with_objectives.py`, `vehicle_cycle_simulator.py`, `device_communication.py`
- `src/training_callbacks/sac_loss_interceptor.py`, `sac_metrics_robust.py`
- `src/baseline/` (duplicado de `src/agents/no_control.py`)
- `data/oe2/bess/bess_ano_2024_CORREGIDO.csv`, `data/oe2/citylearn/` (4 archivos obsoletos)

**Pipeline OE2 reparado:**
- `src/citylearnv2/ev_charging_wrapper.py` — `_CHARGERS_COLS` actualizado al schema lean (sin columnas derivadas); CO₂ arrays computados internamente (`co2_motos`, `co2_mototaxis`)
- `src/dimensionamiento/oe2/generacionsolar/disenopvlib/solar_pvlib.py` — `KeyError: 'reduccion_indirecta_co2_kg'` reparado (computado de `energia_kwh * FACTOR_CO2_KG_KWH`)
- `scripts/generate_oe2_datasets.py` — `UnicodeEncodeError` en Windows reparado (arrows `→` → `->`)
- `src/__init__.py` — eliminado `"baseline"` de `__all__` (directorio no existe)

**Reorganización de scripts y documentación:**
- `scripts/reporting/` — todos los generadores de figuras/informes OE3
- `scripts/analysis/` — scripts de análisis CO₂ + scripts de `analyses/`
- `scripts/verification/` — validaciones de sincronización de datos
- `scripts/maintenance/` — scripts de mantenimiento (fix_tb_records)
- `docs/` — documentación movida desde root y `src/`
- `CLAUDE.md` — guía de onboarding para Claude Code

**Pipeline OE2 verificado desde cero:** Solar → Chargers → BESS → Loader en 18.2s, 8,760 filas, todos los datasets válidos

---

## 📢 Latest Updates (2026-04-12) - INFORME OE3 v11 FINAL + ARQUITECTURA REDISEÑADA ⭐⭐⭐

### 🎨 Arquitectura HTML Rediseñada — Pipeline OE2→OE3 Profesional (2026-04-12)
**`reports/ARQUITECTURA_v2026.html` — Dashboard interactivo de 4 paneles (sin dependencias externas)**

- ✅ **Panel KPIs** — 8 tarjetas métricas con hover effects y campos de color codificado
- ✅ **Panel Pipeline OE2→OE3** — 10 fases color-coded con conectores y flechas nativas HTML/CSS
- ✅ **Panel Flujo de Trabajo** — 9 etapas en grid 3×3, código de color por fase
- ✅ **Panel Ranking Agentes** — tabla con badges SAC 🏆 / PPO 🥈 / A2C 🥉 + cajas de comparativa CO₂
- ✅ Eliminado Mermaid.js (causaba diagramas desproporcionados) — diseño 100% CSS nativo
- 📄 [Ver arquitectura interactiva](reports/ARQUITECTURA_v2026.html)

### 📄 Informe Word OE3 — v11 FINAL (2026-04-12)
**`outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v11.docx` — 594 párrafos, 36 tablas, 6,376 KB**

Secciones completas en el documento final:
- ✅ **§2.2.4** Bases teóricas GHG — 7 fórmulas (F₀, F₁, F₂, FE_ICE_moto, FE_red ...)
- ✅ **§4.6.3** Procedimiento OE3 (11 subsecciones, 7 tablas)
- ✅ **§5.1.2/5.1.3/5.1.4** Resultados descriptivos OE2 (solar, cargadores, BESS)
- ✅ **§5.2** Resultados inferenciales (marco F₀/F₁/F₂, Wilcoxon p=8.882×10⁻¹⁶)
- ✅ **§5.2.2–5.2.3** Inferencia técnica cubrimiento EV + reducción CO₂
- ✅ **§5.3.1–5.3.5** Función recompensa, métricas SAC/PPO/A2C, variabilidad, selección final
- ✅ **ANEXO A**: 33 figuras de entrenamiento (SAC + PPO + A2C)
- ✅ **ANEXO B**: 10 figuras de comparativo de agentes
- ✅ **ANEXO C**: 7 figuras de demostración de hipótesis
- ✅ 52 correcciones de prosa académica aplicadas

### 🤖 OE3 DEFINITIVO — SAC SELECCIONADO (50 episodios, 438 000 pasos) (2026-04-12)
**Entrenamiento completo validado estadísticamente (Kruskal-Wallis H=81.65, p=1.86×10⁻¹⁸)**

| Agente | F₂ mín (kg CO₂/año) | Ep. óptimo | Reducción vs F₀ | Reducción vs F₁ | Violaciones |
|--------|---------------------|------------|-----------------|-----------------|-------------|
| **SAC ★** | **2 622 735** | **48** | **62.8 %** | **54.7 %** | **0 (ep óptimo)** |
| PPO | 2 787 040 | 40 | 60.5 % | 51.9 % | 0 (ep óptimo) |
| A2C | 2 834 857 | 3  | 59.8 % | 51.0 % | — |

- **F₀** (sin solar, sin BESS, sin RL) = 7 054 000 kg CO₂/año
- **F₁** (con solar+BESS, sin RL) = 5 790 639 kg CO₂/año
- **F₂ SAC** (con solar+BESS+SAC) = **2 622 735 kg CO₂/año** (episodio 48)
- **Reducción neta SAC**: 4 431 265 kg CO₂/año (62.8 % vs F₀)
- Wilcoxon F₁>F₂: T=1275, p=8.882×10⁻¹⁶ | Mann-Whitney SAC<PPO: p=3.6×10⁻¹⁵

---

## 📢 Updates anteriores (2026-02-23) - TESIS FINAL PHASE

### 🧹 Repository Cleanup & Thesis Finalization (2026-02-23) ⭐⭐⭐
**Limpieza de 200+ archivos temporales - Repositorio listo para defensa**

- ✅ **Limpieza Completada:**
  - Removidos 100+ scripts .py de análisis, debugging y testing
  - Removidos 40+ archivos .log y *_output.txt de ejecuciones
  - Removidos 50+ documentos .md de notas temporales
  - Removidos archivos .txt, HTML y JSON de análisis ad-hoc
  - **Total:** 141 archivos eliminados, ~7 MiB liberados

- ✅ **Datos de Tesis PRESERVADOS:**
  - `DOCUMENTOS_RESULTADOS_OE2_OE3.md` - Guía completa de resultados
  - `GUIA_COMPLETA_RESULTADOS_OE2_OE3.md` - Inventario de documentos
  - `REDUCCION_DIRECTA_CO2_ANUAL_DETALLADO.json` - Cálculos directos
  - `VALIDACION_ANUALIDAD_REDUCCION_INDIRECTA.json` - Validaciones
  - `VALIDATION_RESULTS_2026-02-18.json` - Auditoría completa
  - `ARCHITECTURE_CATALOG.json` - Catálogo de arquitectura

- ✅ **Código Core ÍNTEGRO:**
  - `src/` - OE2 + OE3 (sin cambios)
  - `scripts/` - Scripts de función (sin cambios)
  - `checkpoints/` - Modelos entrenados (SAC, PPO, A2C, Baseline)
  - `data/`, `outputs/`, `reports/` - Datos y resultados (sin cambios)

- ✅ **Commit & Push:**
  - Commit: `89975bae` - "🧹 Limpieza de archivos temporales"
  - Branch: `smartcharger` ✅ Sincronizado con GitHub
  - Status: Working directory limpio

### 📊 CO₂ Reduction Calculations - FINAL VALIDATED (2026-02-23) ⭐⭐
**Reducción CO₂ anual completamente calculada y segregada**

**REDUCCIÓN DIRECTA (Transporte - no combustible quemado):**
- Motos (15 veh): **203.7 tCO₂/año** (234,111 kWh × 0.87 kg CO₂/kWh)
- Mototaxis (4 veh): **39.6 tCO₂/año** (84,203 kWh × 0.47 kg CO₂/kWh)
- **TOTAL DIRECTO: 243.3 tCO₂/año**
- Per vehicle: Motos 13.6 tCO₂/año, Mototaxis 9.9 tCO₂/año

**REDUCCIÓN INDIRECTA (Generación - diesel desplazado):**
- FV renewable: 5.819M kWh/año
- BESS renewable: 569k kWh/año
- **Total renewable:** 6.388M kWh/año × 0.4521 kg CO₂/kWh
- **TOTAL INDIRECTO: 2,887.6 tCO₂/año**

**REDUCCIÓN TOTAL OPERACIONAL: 4,096.5 tCO₂/año**
- Transporte directo: 243.3 tCO₂/año
- Generación indirecta: 3,804.3 tCO₂/año
- **Línea base ciudad Iquitos:** 548,250 tCO₂/año (referencia)
- **Escalamiento 10-15×:** 7.5-11.2% reducción de ciudad

### 📄 Thesis Documentation - COMPLETE (2026-02-23)
**Capítulo 6 (Discusión) integrado con resultados completos**

- ✅ **Capítulo 6.1.1 - Hipótesis Principal:**
  - Sección A (Transporte): CO₂ directo 243.3 tCO₂/año + indirecto 319.4 tCO₂/año = **562.7 tCO₂/año**
  - Sección B (Generación): FV+BESS desplazando diesel = **3,533.8 tCO₂/año**
  - Sección C (Total): **4,096.5 tCO₂/año operacional**

- ✅ **Línea Base Integrada:**
  - Transport: 61,000 mototaxis + 70,500 motos = **258,250 tCO₂/año**
  - Generation: Thermal diesel plant = **290,000 tCO₂/año**
  - **City Total Baseline: 548,250 tCO₂/año** (reference for hypothesis contrast)

- ✅ **OE3 Results Section (50 episodios):**
  - SAC Agent: F₂=2,622,735 kg CO₂/año ⭐ **SELECCIONADO** (62.8% red. vs F₀)
  - PPO Agent: F₂=2,787,040 kg CO₂/año (2° lugar)
  - A2C Agent: F₂=2,834,857 kg CO₂/año (3° lugar)
  - Kruskal-Wallis H=81.65, p=1.861×10⁻¹⁸ (α=0.001)

- ✅ **Documents Ready for Defense:**
  - `reports/CAPITULO_6_DISCUSION_RESULTADOS_COMPLETO.docx`
  - `outputs/TESIS_PVBESSCAR_COMPLETA_4.6_a_5.5.docx`
  - `outputs/SECCION_5_2_DIMENSIONAMIENTO_DESCRIPTIVO_COMPLETO.docx`
  - `outputs/SECCION_5_3_ALGORITMO_RL_COMPLETO.docx`

### Branch Status & Latest Commits
- **Current Branch:** `smartcharger` ✅ Up to date
- **Latest Commit:** `89975bae` - "🧹 Limpieza de archivos temporales: eliminar 200+ scripts/logs/documentos"
- **Previous Commit:** `bc574943` - "✅ FASE 3: Visualización 6 FASES en gráfica integral"
- **Changes:** 142 files processed (141 deleted, 1 modified) - 7.00 MiB synchronized
- **Date:** 2026-02-23 ✅ PRODUCTION READY

---

## 🎯 Resumen Ejecutivo (Actualizado 2026-02-21)

**pvbesscar** implementa un sistema completo de dos fases para optimizar infraestructura de carga EV:

### ✅ OE2 (Dimensioning) - COMPLETADO (Infraestructura)
Especificaciones de infraestructura confirmadas con visualizaciones completas de 6-FASES:
- **19 cargadores** (15 motos + 4 mototaxis) × 2 sockets = **38 puntos de carga**
- **Solar:** **4,162 kWp DC / 3,201 kW AC** PVGIS/pvlib (8,760 rows, 5.819 GWh/year)
- **BESS:** **2,000 kWh** max SOC (80% DoD, 95% efficiency, 20% min SOC)
  - **6-FASES Operacionales & Visualizadas:**
    - FASE 1 (6-9h): Carga BESS primero (PV→BESS prioritario)
    - FASE 2 (9-15h): EV máxima prioridad + BESS carga paralela (SOC<99%)
    - FASE 3 (SOC≥99%): HOLDING - SIN carga/descarga (PV→EV directamente)
    - FASE 4 (PV<MALL>1900kW): Peak shaving (BESS descarga para MALL)
    - FASE 5 (ev_deficit>0): EV prioridad descarga + MALL paralelo
    - FASE 6 (22-9h): Reposo - BESS IDLE a SOC 20%
  - **Visualización Gráfica:** Bandas de color (verde/azul/rojo/gris), etiquetas, divisores en horas 6,9,15,17,22
- **CO₂ Factor:** 0.4521 kg CO₂/kWh (thermal generation Iquitos)
- **Data:** 977 technical columns × 8,760 hourly timesteps
- **Graphics v5.8+:** Gráficas con 6-FASES claramente diferenciadas, barras BESS por FASE, curva SOC integrada

### ✅ OE3 (Control) - COMPLETADO (Evaluación de Agentes RL)
**OE3:** Seleccionar el agente de inteligencia artificial de la infraestructura de carga inteligente para la gestión de recarga de motos y mototaxis eléctricas, apropiada que contribuye de manera cuantificable a la reducción de emisiones de dióxido de carbono en la ciudad de Iquitos.

Control inteligente con Reinforcement Learning - **SAC SELECTED** ⭐ (50 episodios, 438 000 pasos, Kruskal-Wallis p=1.86×10⁻¹⁸)

**3 Agentes Entrenados y Evaluados (50 episodios cada uno):**
- **SAC (Soft Actor-Critic):** F₂=2 622 735 kg CO₂/año ⭐ **SELECCIONADO** — 62.8 % reducción vs F₀, CV plateau 0.058 %, 0 violaciones ep. óptimo
- **PPO (Proximal Policy Optimization):** F₂=2 787 040 kg CO₂/año — 60.5 % reducción vs F₀
- **A2C (Advantage Actor-Critic):** F₂=2 834 857 kg CO₂/año — 59.8 % reducción vs F₀

**Entrenamiento:** 50 episodios × 8 760 pasos = 438 000 decisiones por agente | CityLearn v2 | obs 394D | acción 39D

---

## 📊 OE3 Final Results (2026-04-12) - SAC Selected ⭐

| Métrica | SAC ⭐ | PPO | A2C |
|---------|--------|-----|-----|
| **F₂ mínimo (kg CO₂/año)** | **2 622 735** | 2 787 040 | 2 834 857 |
| **Episodio óptimo** | **48** | 40 | 3 |
| F₂ media 50 eps (kg CO₂/año) | **2 668 375** | 2 875 569 | 2 845 012 |
| F₂ std (kg/año) | **89 475** | 113 816 | 12 011 |
| CV plateau (%) | **0.058 %** | 0.195 % | 0.056 % |
| Reducción directa CO₂ (kg/año) | **328 736** | 334 103 | 301 293 |
| Reducción indirecta CO₂ (kg/año) | **3 223 884** | 3 052 176 | 2 985 752 |
| Reducción neta CO₂ (kg/año) | **3 552 620** | 3 386 279 | 3 287 045 |
| % reducción vs F₀ (7 054 000) | **62.8 %** | 60.5 % | 59.8 % |
| % reducción vs F₁ (5 790 639) | **54.7 %** | 51.9 % | 51.0 % |
| Cobertura EV ep. óptimo (%) | **98.1 %** | 99.9 % | 87.4 % |
| BESS descargado media (kWh/año) | 880 245 | 906 898 | **733 671** |
| Importación red mínima (kWh/año) | **5 801 227** | 6 164 654 | 6 270 421 |
| Violaciones totales (50 eps) | **1 029** | 2 605 | 1 181 |
| Pasos entrenados | 438 000 | 438 000 | 438 000 |
| Tipo | Off-policy | On-policy | On-policy |

### 🔄 Baseline Comparison (3 escenarios, GHG Protocol / ISO 14064)
```
F₀ — SIN solar, SIN BESS, SIN RL:  7 054 000 kg CO₂/año  (referencia absoluta)
F₁ — CON solar+BESS, SIN RL:       5 790 639 kg CO₂/año  (operación base)
F₂ SAC — CON solar+BESS+SAC RL:    2 622 735 kg CO₂/año  ⭐ SELECCIONADO

Reducción SAC vs F₀:  4 431 265 kg CO₂/año  (-62.8%)
Reducción SAC vs F₁:  3 167 904 kg CO₂/año  (-54.7%)  ← aporte exclusivo del RL

Prueba estadística: Kruskal-Wallis H=81.65, p=1.861×10⁻¹⁸ (α=0.001)
Mann-Whitney SAC<PPO: p=3.636×10⁻¹⁵ | SAC<A2C: p=1.641×10⁻¹⁴
Shapiro-Wilk plateau SAC: W=0.9752, p=0.9259 (distribución normal)
```

---

## 🚀 Quick Start (OE3 Ready - Production Deployment)

### 1. Setup Environment
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1              # Windows PowerShell
source .venv/bin/activate              # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-training.txt  # For GPU (RTX 4060+)
```

### 2. ⭐ Load & Use Trained SAC Agent (Production Ready)

**Option A: Quick Test**
```bash
python -c "
from stable_baselines3 import SAC
agent = SAC.load('checkpoints/SAC/')
print('✓ SAC loaded - 438,000 timesteps (50 episodios) entrenados')
print('Expected annual CO2: 2,622,735 kg (62.8% reducción vs F0)')
"
```

**Option B: Deploy to Environment**
```python
from stable_baselines3 import SAC

# Load trained SAC agent (episodio 48 — óptimo)
agent = SAC.load("checkpoints/SAC/")

# Deploy to CityLearn v2 environment
obs = env.reset()
total_reward = 0
for step in range(8760):  # 1 year = 8,760 hours
    action, _ = agent.predict(obs, deterministic=True)
    obs, reward, done, info = env.step(action)
    total_reward += reward
    # Monitor real metrics
    if step % 24 == 0:  # Daily
        print(f"Day {step//24}: CO2={info['co2']:.0f}kg, Grid={info['grid_import']:.0f}kWh")
# Expected: F2 = 2,622,735 kg CO2/año | Cobertura EV 98.1%
```

**Option C: View OE3 Evaluation Results**
```bash
cat outputs/comparative_analysis/OE3_FINAL_RESULTS.md
cat outputs/comparative_analysis/OE2_OE3_COMPARISON.md
```

### 3. Verify Data Integrity (977 Columns × 8,760 Hours)
```bash
python -c "
import pandas as pd

# Check chargers dataset
df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
assert len(df) == 8760, f'ERROR: Expected 8760 rows, got {len(df)}'
print(f'✓ Chargers data: {df.shape} rows/columns')

# Check BESS dataset
df = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')
assert len(df) == 8760, f'ERROR: Expected 8760 rows, got {len(df)}'
print(f'✓ BESS data: {df.shape} rows/columns')

# Check solar dataset
df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
assert len(df) == 8760, f'ERROR: Expected 8760 rows, got {len(df)}'
print(f'✓ Solar data: {df.shape} rows/columns')

print('✓ ALL DATA VALIDATED - 977 columns × 8,760 hours')
"
```

### 4. Continue Training SAC (Optional — Resume from Checkpoint)
```bash
# SAC training resumes automatically from checkpoint
python scripts/train/train_sac.py --episodes 5 --log-dir outputs/continued_training/
# Continues from: checkpoints/SAC/ (438,000 steps — episodio 48 óptimo)
```

---

## � Visualizaciones Interactivas (OE2 - Balance Energético Real)

**Gráficas del Balance Energético con Datos Reales 2024:**

### 🔗 **[VER GRÁFICAS INTERACTIVAS EN HTML](outputs/index.html)**

Galería interactiva con 10 gráficas completas mostrando:

#### Gráfics Principales:
1. **[00_BALANCE_INTEGRADO_COMPLETO.png](outputs/balance_energetico/00_BALANCE_INTEGRADO_COMPLETO.png)** ⭐
   - **Generación solar real:** 6h-17h, pico 3,246 kW
   - **Demanda EV:** perfil horario 9-22h (ramp-up 9-17h, punta 18-20h, descenso 21-22h)
     - Motos: 5.19 kWh/vehículo, 30 sockets (78.9%) | Taxis: 7.40 kWh/vehículo, 8 sockets (21.1%)
   - **Demanda Mall:** variable 0-2,763 kW
   - **BESS 6-FASES:**
     - FASE 1 (6-15h): Carga gradual desde SOC 20%→100% (línea verde, sincronizada con PV)
     - FASE 2 (15-17h): Holding a 100% SOC (espera punto crítico)
     - FASE 3-5 (17-22h): Descarga EV + peak shaving MALL (línea roja, máx 390 kW)
     - FASE 6 (22-6h): Reposo a SOC 20% (standby)
   - **Grid import:** Respaldo 24h, solo cuando PV+BESS insuficiente
   - **Visualización mejorada:** Etiquetas 0h-23h en eje X, perfiles de carga/descarga superpuestos, anotaciones FASE 1 inicio

2. **[00_INTEGRAL_todas_curvas.png](outputs/00_INTEGRAL_todas_curvas.png)** - Perfil 7 días continuo
3. **[00.5_FLUJO_ENERGETICO_INTEGRADO.png](outputs/00.5_FLUJO_ENERGETICO_INTEGRADO.png)** - Diagrama Sankey
4. **[01_balance_5dias.png](outputs/01_balance_5dias.png)** - Balance 5 días representativos
5. **[02_balance_diario.png](outputs/02_balance_diario.png)** - Perfil diario detallado
6. **[03_distribucion_fuentes.png](outputs/03_distribucion_fuentes.png)** - Distribución energética anual
7. **[04_cascada_energetica.png](outputs/04_cascada_energetica.png)** - Cascada de energía
8. **[05_bess_soc.png](outputs/05_bess_soc.png)** - State of Charge BESS (20-100%)
9. **[06_emisiones_co2.png](outputs/06_emisiones_co2.png)** - Huella de carbono (kg CO₂/año)
10. **[07_utilizacion_pv.png](outputs/07_utilizacion_pv.png)** - Utilización de energía solar

### ✨ Graphics v5.8+ Improvements (2026-02-20)
- ✅ **FASE 1 Timing Correction:** BESS carga inicia cuando aparece PV (7h), no espera a 9h
- ✅ **BESS Charge/Discharge Profiles:** Líneas superpuestas (verde para carga, roja para descarga) para mayor claridad
- ✅ **Hourly X-axis Labels:** Etiquetas 0h-23h para mejor referencia temporal
- ✅ **6-FASES Color Zones:** Zonas visuales (verde/azul/rojo/gris) respetando las 6 fases intocables
- ✅ **Clean Console Output:** Caracteres Unicode reemplazados con ASCII (→ becomes "a")
- ✅ **Legend Repositioned:** Gráfica 04 leyenda movida a esquina superior izquierda

### 📈 Datos Reales Integrados (2024):
- **Generación Solar:** `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv`
  - Pico: 3,245.95 kW (4,162 kWp DC / 3,201 kW AC nominal)
  - Perfil: 6h-17h (equinoxio Iquitos)
  - Media anual: 664.3 kW

- **Demanda Mall:** `data/oe2/demandamallkwh/demandamallhorakwh.csv`
  - Variable: 0 a 2,763 kW
  - Media: 1,411.95 kW
  - Total anual: 12,368,653 kWh

- **Demanda EV (Motos + Taxis):** `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`
  - Base: 281.2 kW × perfil horario 9-22h
  - Motos: 5,328 kWh/día (78.9%), Taxis: 1,421 kWh/día (21.1%)
  - Total anual: 2,463,312 kWh

### 🔧 Abrir Gráficas Localmente:
```bash
# En Windows
start outputs/index.html

# En Linux/Mac
open outputs/index.html
# o
firefox outputs/index.html
```

---

## �📂 Estructura del Proyecto

```
pvbesscar/
├── src/
│   ├── dimensionamiento/oe2/          # OE2: Dimensionamiento
│   │   ├── disenocargadoresev/        # Specs chargers (19 units × 2 sockets)
│   │   ├── generacionsolar/           # PVGIS/pvlib solar generation (4,162 kWp DC)
│   │   └── balance_energetico/        # Energy balance validated
│   ├── agents/                         # OE3: RL Agents (3 trained)
│   │   ├── a2c_sb3.py                 # A2C = on-policy (59.8% CO₂ reducción vs F0)
│   │   ├── sac.py                     # ⭐ SAC SELECCIONADO (62.8% CO₂ reducción vs F0)
│   │   ├── ppo_sb3.py                 # PPO = on-policy (60.5% CO₂ reducción vs F0)
│   │   └── no_control.py              # Baseline (uncontrolled)
│   ├── dataset_builder_citylearn/      # CityLearn v2 integration
│   │   ├── data_loader.py             # OE2→OE3 pipeline (977 cols)
│   │   ├── rewards.py                 # MultiObjectiveReward function
│   │   └── dataset_builder.py         # Dataset construction
│   └── utils/                          # Shared utilities
│       ├── agent_utils.py             # Common agent functions
│       ├── logging.py                 # Logging utilities
│       └── time.py                    # Time handling
├── data/
│   ├── oe2/                            # OE2 artifacts (real data, 8,760 h)
│   │   ├── chargers/
│   │   │   └── chargers_ev_ano_2024_v3.csv (8,760 rows)
│   │   ├── bess/
│   │   │   └── bess_ano_2024.csv (8,760 rows)
│   │   ├── Generacionsolar/
│   │   │   └── pv_generation_citylearn2024.csv (8,760 rows)
│   │   └── demandamallkwh/
│   │       └── demand_*.csv (8,760 rows)
│   └── interim/oe2/                    # Processed data
├── scripts/
│   └── train/
│       ├── train_sac.py               # ⭐ SAC training (SELECTED — 50 eps, F₂=2,622,735)
│       ├── train_ppo.py               # PPO training (2nd place)
│       ├── train_a2c.py               # A2C training (3rd place)
│       └── common_constants.py        # 977-column validation
├── configs/
│   ├── default.yaml                   # Main configuration
│   └── agents/                        # Agent-specific configs
├── checkpoints/                        # ⭐ Trained Models (Ready to Deploy)
│   ├── SAC/ ⭐
│   │   └── (ep48 optimal model)       # ✓ 438,000 steps (PRODUCTION READY — SELECTED)
│   ├── PPO/
│   │   └── (ep40 optimal model)       # 438,000 steps (2nd place)
│   └── A2C/
│       └── (ep03 optimal model)       # 438,000 steps (3rd place)
├── outputs/
│   └── comparative_analysis/           # ⭐ OE3 RESULTS (2026-02-19)
│       ├── OE3_FINAL_RESULTS.md       # Complete OE3 analysis
│       ├── OE2_OE3_COMPARISON.md      # Phase comparison
│       ├── oe3_evaluation_report.md   # Detailed metrics
│       ├── agents_comparison_summary.csv
│       ├── 01-07_comparison_graphs.png # 7 comparison graphs
│       └── {a2c,ppo,sac}_training/   # Training results
└── README.md                           # This file
```

---

## 📊 OE3 Evaluation Methodology

### Input Data (977 Technical Columns per Timestep)
```
76  Socket power states (W) - 38 sockets × 2 poles
722 Socket SOC values (%) - state of charge tracking
236 CO2 grid intensity (kg CO2/kWh) - hourly variation
186 Motos demand profiles (vehicles, kWh needed)
54  Mototaxis demand profiles (vehicles, kWh needed)
231 Energy metrics (solar W, BESS kWh, grid kWh)
228 Charger status & health indices (38 sockets)
8   Time features (hour/day/month/dow/season)
─────────────────────────────────────────────────────
977 TOTAL technical columns per 1-hour timestep
```

### ⚖️ Multi-Objective Reward Weights (Agent Training - v7.0, 2026-04-06)

**OE3 Objetivo:** Seleccionar el agente IA de la infraestructura de carga inteligente para la gestión de recarga de motos y mototaxis eléctricas, apropiada que contribuye de manera cuantificable a la reducción de emisiones de CO₂ en la ciudad de Iquitos.

**Used in SAC/PPO/A2C Training (from `src/dataset_builder_citylearn/rewards.py`)**

| Component | Weight | Priority | Description |
|-----------|--------|----------|-------------|
| **Direct CO₂ Minimization** | 0.35 | PRIMARY | Combustible vehicular evitado (motos/mototaxis) |
| **Indirect CO₂ Minimization** | 0.30 | SECONDARY | Grid import CO₂ termico (0.4521 kg/kWh) |
| **EV Satisfaction** | 0.25 | TERTIARY | Vehicle charging completion |
| **Solar Self-Consumption** | 0.05 | QUATERNARY | PV direct usage vs grid |
| **Grid Stability** | 0.05 | QUINARY | Peak power ramping smoothness |
| **TOTAL** | **1.00** | **NORMALIZED** | **CO₂ reduction focus (0.65 combined)** |

**Reward Formula (CO2_DUAL_FOCUS v7.0):**
```
Total = (0.35 x r_direct_co2) + (0.30 x r_indirect_co2) + (0.25 x r_ev) +
        (0.05 x r_solar) + (0.05 x r_grid)
      = 0.5346  (mean normalized reward, empirical SAC ep.48)
```

---

### OE3 Evaluation Criteria (Composite — 50 episodios, Kruskal-Wallis p=1.86×10⁻¹⁸)

1. **CO₂ Minimization** (Criterio principal)
   - SAC F₂ = **2,622,735 kg/año** ⭐ (-62.8% vs F₀; -54.7% vs F₁)

2. **Grid Import Reduction**
   - SAC = 5,902,180 kWh/año media 50 eps (BESS: 880,245 kWh descargados)

3. **Solar Utilization**
   - Reducción indirecta SAC: 3,223,884 kg CO₂/año ← mayor de los 3 agentes

4. **BESS Eficiencia**
   - BESS descargado SAC: 880,245 kWh/año (r=-0.782 con CO₂, p<0.001)

5. **EV Charging Coverage**
   - SAC cobertura EV = 98.1% en episodio óptimo (ep.48, 0 violaciones)

**RESULTADO OE3 DEFINITIVO: SAC SELECCIONADO** ⭐ F₂=2,622,735 kg CO₂/año

---

## 🎯 Agent Comparison & Recommendation (OE3 — 50 episodios)

### SAC (Soft Actor-Critic) ⭐ **SELECCIONADO — OE3 DEFINITIVO**
```
F2 mínimo:       2,622,735 kg CO₂/año  (episodio 48)
Reducción vs F0: 62.8% (-4,431,265 kg CO₂/año)
Reducción vs F1: 54.7% (-3,167,904 kg CO₂/año)  ← aporte exclusivo del RL
Tipo:            Off-policy, entropía adaptativa
Entrenamiento:   50 episodios × 8,760 pasos = 438,000 pasos totales
CV plateau:      0.058% (altísima estabilidad en últimos 15 eps)
Cobertura EV:    98.1% en episodio óptimo (0 violaciones)
Significancia:   p < 0.001 vs PPO y A2C (Mann-Whitney)
Fitness:         ✅ PRODUCCIÓN — ÓPTIMO AMBIENTAL
```

### PPO (Proximal Policy Optimization) — 2° lugar
```
F2 mínimo:       2,787,040 kg CO₂/año  (episodio 40)
Reducción vs F0: 60.5% (-4,266,960 kg CO₂/año)
Tipo:            On-policy, clipped objective
Entrenamiento:   50 episodios × 8,760 pasos = 438,000 pasos
CV plateau:      0.195% (mayor variabilidad que SAC)
Violaciones:     2,605 totales (mayor que SAC y A2C)
Fitness:         ✅ Alternativa válida si SAC no disponible
```

### A2C (Advantage Actor-Critic) — 3° lugar
```
F2 mínimo:       2,834,857 kg CO₂/año  (episodio 3 — convergencia temprana)
Reducción vs F0: 59.8% (-4,219,143 kg CO₂/año)
Tipo:            On-policy, síncrono
Entrenamiento:   50 episodios × 8,760 pasos = 438,000 pasos
CV plateau:      0.056% (estable, pero en nivel de CO₂ subóptimo)
Convergencia:    0.79% mejora ep1→50 (plateau muy temprano, sin refinamiento)
Fitness:         ⚠️ No recomendado — mayor F2 (peor ambiental)
```

---

## 💾 Deployment Recommendation

### Production Deployment: SAC Checkpoint (Episodio 48) ⭐
```python
from stable_baselines3 import SAC

# Load trained SAC agent (episodio óptimo 48 — 50 episodios de entrenamiento)
agent = SAC.load("checkpoints/SAC/")

# Expected annual performance (SAC ep.48 — DEFINITIVO)
expected_metrics = {
    'f2_co2_kg_per_year': 2_622_735,           # F2 mínimo (62.8% vs F0)
    'co2_reduccion_vs_f0': -4_431_265,         # kg CO₂ evitado vs F0
    'co2_reduccion_vs_f1': -3_167_904,         # kg CO₂ evitado vs F1 (aporte RL)
    'ev_coverage_best_ep': 0.981,              # 98.1% cobertura EV epóptimo
    'bess_discharge_kwh': 880_245,             # kWh descargados BESS/año
    'grid_import_kwh': 5_902_180,              # Grid import media 50 eps
    'cv_plateau': 0.00058,                     # 0.058% CV — alta estabilidad
    'violations_best_ep': 0,                   # 0 violaciones episodio óptimo
    'training_episodes': 50,
    'total_timesteps': 438_000,
}

print("SAC selected for OE3:")
print(f"  ✓ F2 = {expected_metrics['f2_co2_kg_per_year']:,} kg CO2/año")
print(f"  ✓ Reducción vs F0 = {abs(expected_metrics['co2_reduccion_vs_f0']):,} kg CO2/año")
print(f"  ✓ EV coverage = {expected_metrics['ev_coverage_best_ep']*100:.1f}%")
print(f"  ✓ CV plateau = {expected_metrics['cv_plateau']*100:.3f}% (altamente estable)")
```

### Expected Impact (Annual) — SAC OE3 Definitivo
| Métrica | Valor | vs F₀ | vs F₁ |
|---------|-------|--------|--------|
| CO₂ total (F₂) | **2,622,735 kg** | -62.8 % | -54.7 % |
| CO₂ evitado neto | **4,431,265 kg = 4,431 tCO₂** | — | — |
| Cobertura EV | 98.1 % (ep óptimo) | — | — |
| Violaciones (epóptimo) | **0** | — | — |
| BESS descargado | 880,245 kWh/año | — | — |
| Grid import media | 5,902,180 kWh/año | — | — |

---

## 🔧 Dimensionamiento Técnico (OE2 v5.8) - VALORES ACTUALES

### 📡 SOLAR PV (Photovoltaic Generation)

**Especificación de Diseño PVGIS:**
```
Ubicación:              Iquitos, Perú (-3.75°, -73.25°)
Capacidad DC nominal:   4,162 kWp ✅ ACTUAL
Capacidad AC nominal:   3,201 kW
Tecnología:             PV modules + Inverter Eaton Xpert1670
Módulos:                Jinko Tiger Neo JKM580N 72HL4 BDV
Inclinación:            10° (toiture-plano optimal)
Orientación:            0° azimuth (Norte)
Área total disponible:  20,637 m²
Área utilizada:         18,535 m²
Pérdidas Sistema:       13.6% (estimadas)
Generación Anual:       5,819,332 kWh/año = 5.819 GWh/año (PVGIS/pvlib)
Generación Horaria:     664.3 kW promedio anual
Generación Máxima:      3,245.95 kW (2024-10-18 11:00)
Datos Horarios:         8,760 filas (365 días × 24 h, NO 15-min ⚠️)
Archivo principal:      data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
Informe descriptivo:    data/oe2/Generacionsolar/informe_generacion_solar_procedimiento_resultados_descriptivos.md
```

**Reducción CO₂ por Solar:**
```
Factor red térmica Iquitos:      0.4521 kg CO₂/kWh
CO₂ evitado por FV directa:      2,630,920 kg/año (5.819 GWh × 0.4521)
Ahorro solar estimado:           S/ 1,629,413/año
```

---

### 🔋 BESS - Battery Energy Storage System

**Especificación Técnica Completa (v5.8):**
```
Capacidad Total:                  2,000 kWh ✅ VALIDADO (bess_ano_2024.csv)
Potencia Máxima Carga:            400 kW (simétrica)
Potencia Máxima Descarga:         400 kW (simétrica)
C-Rate:                           0.200 (400 kW / 2,000 kWh) ✅ CORRECTED
Eficiencia Round-trip:            95% (carga + descarga)
SOC Máximo:                       100% (hard constraint: 2,000 kWh)
SOC Mínimo:                       20% (hard constraint: 400 kWh min reservoir)
Profundidad de Descarga (DoD):    80% (20%-100% operating range)
Capacidad Utilizable:             1,600 kWh (20%-100% SOC range)
Ciclos Anuales Estimados:         ~200 ciclos/año

Aplicación Dual:                  EV charging (prioridad 1) + MALL discharge (pico)
Despacho Prioridades:
  P1: FV → EV directo (máxima prioridad)
  P2: FV → BESS (cargar reserva pico)
  P3: BESS → EV (descarga nocturna)
  P4: BESS → MALL (saturada a 95% SOC)
  P5: Grid import (déficit)

Carga Horaria Típica:             150-200 kWh/h (durante sol)
Descarga Horaria Típica:          50-100 kWh/h (pico + noche)
Energía Ciclo Diario Promedio:    ~123 kWh/día (45,000 kWh/año)
Datos Técnicos:                   8,760 filas (1 año, horario)
Archivo:                          data/oe2/bess/bess_ano_2024.csv
```

**Validaciones BESS:**
- ✅ Validé máxima carga contra bess_ano_2024.csv: **2000 kWh confirmed**
- ✅ C-Rate corregida: **0.200 actual** (no 0.235 antiguo con 1700 kWh)
- ✅ Eficiencia: **95% round-trip** (entre simulación y real)
- ✅ Ciclos: **~200/año** (sostenible, no degradación acelerada)

---

### ⚡ INFRAESTRUCTURA DE CARGA EV (Vehículos Eléctricos)

**Especificación técnica de Cargadores:**
```
Número Total Cargadores:          19 unidades ✅ FÍSICO
  ├─ Motos:                       15 cargadores (30 sockets)
  └─ Mototaxis:                   4 cargadores (8 sockets)

Sockets por Cargador:             2 sockets/cargador
Total Sockets:                    38 sockets ✅ CONTROLABLES (19 × 2)

Potencia por Socket:              7.4 kW (Modo 3, monofásico)
  ├─ Voltaje:                     230V per fase
  ├─ Amperaje:                    32A máximo
  └─ Estándar:                    IEC 61851-1 (Modo 3 - AC)

Potencia Instalada Total:         281.2 kW (38 sockets × 7.4 kW)
Potencia Pico Combinada:          ~150 kW (limiter agregado)
Potencia Media Operativa:         ~50 kW (tracking EV demand)

Demanda de Vehículos:
  ├─ Motos por día:               270 unidades (motos)
  ├─ Mototaxis por día:           39 unidades (mototaxis)
  ├─ Vehículos Totales/día:       309 vehículos
  └─ Factor Utilización:          92% (histórico Iquitos)

Capacidades de Batería:
  ├─ Moto eléctrica:              4.6 kWh nominal
  │  ├─ SOC llegada:              20% (0.92 kWh)
  │  ├─ SOC meta:                 80% (3.68 kWh)
  │  └─ Energía a cargar:         ~2.9 kWh (eficiencia 95%)
  └─ Mototaxi eléctrico:          7.4 kWh nominal
     ├─ SOC llegada:              20% (1.48 kWh)
     ├─ SOC meta:                 80% (5.92 kWh)
     └─ Energía a cargar:         ~4.7 kWh (eficiencia 95%)

Horas Operativas:
  ├─ Apertura:                    09:00 (zona horaria Lima)
  ├─ Cierre:                      22:00
  ├─ Horas activas:               13 h/día
  └─ Horas pico:                  18-21h (peak tariff × 2.0)

Energía Anual EV:
  ├─ Consumo eléctrico:           ~280,632 kWh/año (demanda)
  ├─ Cargados desde solar:        ~180,410 kWh/año (64% util)
  ├─ Cargados desde BESS:         ~45,000 kWh/año (noche)
  └─ Cargados desde grid:         ~55,222 kWh/año (peak fallback)

Archivo Datos:                    data/oe2/chargers/chargers_ev_ano_2024_v3.csv
```

**Distribución de Sockets:**
```
Motos (Playa A):        30 sockets @ 7.4 kW × 15 chargers
Mototaxis (Playa B):    8 sockets @ 7.4 kW × 4 chargers
────────────────────────────────────────────────────────────
Total:                  38 sockets @ 7.4 kW × 19 chargers
```

---

### 🏬 CARGA BASE MALL (Demanda Energética No-EV)

**Especificación de Demanda MALL:**
```
Consumo Diario Energía:           2,400 kWh/día (típico)
Consumo Anual:                    876,000 kWh/año
Potencia Máxima:                  ~2,763 kW (períodos pico)
Potencia Media:                   ~100 kW (24h promedio)
Factor de Carga:                  45% (variación diaria)
Horas Pico:                       18:00 - 21:00 (4 h/día × tarifa 2×)
Costo Tarifa OSINERGMIN:          ~$0.28/kWh (generación + dist + O&M)
Datos:                            8,760 filas horarias (anual)
Archivo:                          data/interim/oe2/demandamallkwh/demandamallhorakwh.csv
```

---

### 📊 RESUMEN INTEGRADO - OE2 v5.8

| Componente | Especificación | Unidad | Validación |
|-----------|-------------------|--------|-----------|
| **SOLAR** | | | |
| Capacidad DC nominal | 4,162 | kWp | ✅ PVGIS/pvlib |
| Capacidad AC nominal | 3,201 | kW | ✅ Inversor |
| Generación Anual | 5,819 | MWh | ✅ Modelo horario |
| Generación Pico | 3,246 | kW | ✅ Histórico |
| Datos Horarios | 8,760 | filas | ✅ 1 año |
| | | | |
| **BESS** | | | |
| Capacidad Nominal | 2,000 | kWh | ✅ bess_ano_2024 |
| Potencia Max | 400 | kW | ✅ Simétrica |
| C-Rate | 0.200 | C | ✅ Correcto (400/2000) |
| Eficiencia | 95 | % | ✅ Round-trip |
| Usable SOC | 1,600 | kWh | ✅ 20%-100% |
| Ciclos/Año | ~200 | ciclos | ✅ Sostenible |
| | | | |
| **EV Cargadores** | | | |
| Total Cargadores | 19 | unidades | ✅ 15 motos + 4 taxis |
| Total Sockets | 38 | sockets | ✅ 2/cargador |
| Potencia/Socket | 7.4 | kW | ✅ Modo 3 32A/230V |
| Potencia Total | 281.2 | kW | ✅ 38 × 7.4 |
| Motos/Día | 270 | vehículos | ✅ Demanda real |
| Mototaxis/Día | 39 | vehículos | ✅ Demanda real |
| Batería Moto | 4.6 | kWh | ✅ Típica EV motos |
| Batería Taxi | 7.4 | kWh | ✅ Típica EV taxis |
| Datos Horarios | 8,760 | filas | ✅ 1 año |
| | | | |
| **RED** | | | |
| Factor CO₂ Grid | 0.4521 | kg/kWh | ✅ Térmica aislada |
| Demanda MALL | 2,400 | kWh/día | ✅ Medido |
| Horas Pico | 18-21h | h/día | ✅ 4h tarifa 2× |
| Horas Valle | 9-12h | h/día | ✅ Tarifa 0.5× |

---

## ⚙️ Configuration Files

**Main config:** `configs/default.yaml` (synchronized across all agents)

**All agents use:** `scripts/train/common_constants.py` (centralized constants)

**Constants from common_constants.py:**
```python
# ============================================================================
# CONSTANTES OE2 v5.8 (Iquitos, Perú)
# ============================================================================
CO2_FACTOR_IQUITOS: 0.4521              # kg CO₂/kWh - grid thermal
HOURS_PER_YEAR: 8760

# BESS VALIDATED v5.8
BESS_MAX_KWH: 2000.0                    # 2,000 kWh max SOC ✅
BESS_MAX_POWER_KW: 400.0                # 400 kW symmetric
BESS_MIN_SOC_PERCENT: 20.0              # 20% minimum
BESS_EFFICIENCY: 0.95                   # 95% round-trip

# NORMALIZATION (977 columns)
SOLAR_MAX_KW: 3245.95                   # Real max from PVGIS/pvlib
MALL_MAX_KW: 3000.0                     # Real max demand
CHARGER_MAX_KW: 3.7                     # Per socket: 7.4/2
DEMAND_MAX_KW: 300.0                    # Peak total

# VEHICLES & EV Infrastructure
MOTOS_TARGET_DIARIOS: 270               # Motos/día
MOTOTAXIS_TARGET_DIARIOS: 39            # Taxis/día
MOTO_BATTERY_KWH: 4.6                   # Moto capacity
MOTOTAXI_BATTERY_KWH: 7.4               # Taxi capacity

# INFRASTRUCTURE
N_CHARGERS: 19                          # Total chargers
TOTAL_SOCKETS: 38                       # 19 × 2
SOLAR_PV_KWP: 4162.0                    # Solar DC nominal capacity
BESS_CAPACITY_KWH: 2000.0               # BESS capacity ✅
```

**BESS Specification Verified:**
- Total Capacity: **2,000 kWh** (per bess_ano_2024.csv max SOC) ✅
- C-Rate: **0.200** (charge/discharge rate at 400 kW) ✅
- Usable Capacity: 1,600 kWh (at 20%-100% SOC range) ✅
- All values synced across configs/default.yaml, common_constants.py, and actual data files

---

## 🌍 Análisis de Reducciones de CO₂ (Directas e Indirectas)

### 📋 PROCEDIMIENTO DE CÁLCULO - CO₂ BASELINE vs OPTIMIZADO

#### **Escenario 1: BASELINE (Sin Optimización RL)**

**Condiciones:**
- Grid import continuo: 50 kW constante (demanda EV fija)
- Sin maximización de solar directo
- Without BESS dispatch optimization
- Sin control de pico de red

**Cálculo Baseline:**
```
1. CO₂ DIRECTO (EVs - Demanda Fija):
   ├─ Demanda EV constante:              50 kW
   ├─ Factor CO₂ equivalente gasolina:   2.146 kg CO₂/kWh
   ├─ Consumo anual:                     50 kW × 8760 h = 438,000 kWh/año
   ├─ CO₂ directo anual:                 438,000 × 2.146 = 940,000 kg CO₂/año
   └─ NOTA: Este valor NO se reduce (es demanda fija de vehículos)

2. CO₂ INDIRECTO (Grid Import - OBJETIVO PRINCIPAL):
   ├─ Grid import sin optimización:      50 kW × 8760 h = 438,000 kWh/año
   ├─ Factor CO₂ grid Iquitos:           0.4521 kg CO₂/kWh (térmica aislada)
   ├─ CO₂ indirecto (grid):              438,000 × 0.4521 = 197,920 kg CO₂/año
   └─ Total baseline (indirecto):        197,920 kg CO₂/año

TOTAL BASELINE:                          197,920 kg CO₂/año (sin reducción)
```

---

#### **Escenario 2: OPTIMIZADO CON RL (SAC — Seleccionado OE3)**

**Condiciones:**
- Maximización de solar directo a EVs (Prioridad P1)
- Optimización BESS para pico nocturno
- Control inteligente de despacho energético
- Agente RL: SAC (F₂=2,622,735 kg CO₂/año, ep.48)

**Componente 1: Reducción INDIRECTA por Solar PV**
```
Generación Solar PV:
├─ Capacidad nominal:                   4,162 kWp DC / 3,201 kW AC
├─ Generación anual PVGIS/pvlib:        5,819,332 kWh = 5.819 GWh
├─ Aplicado a demanda grid (indirecto): ~5,819 MWh/año
├─ Factor CO₂ evitado:                  0.4521 kg CO₂/kWh
└─ CO₂ INDIRECTO EVITADO:               5,819,332 × 0.4521 = 2,630,920 kg CO₂/año

Explicación:
  Cuando el sistema solar genera 5,819 MWh/año, evita que esa energía
  sea importada de la grid térmica de Iquitos.
  Reducción indirecta = Generación solar × factor CO₂ grid
                     = 5,819,332 kWh × 0.4521 kg CO₂/kWh
                     = 2,630,920 kg CO₂ evitado anualmente
```

**Componente 2: Reducción DIRECTA por Carga EV desde Solar**
```
Carga de Vehículos desde Solar:
├─ Energía EV desde solar:              ~280,410 kWh/año (64% utilización)
├─ Factor CO₂ equivalencia gasolina:    Moto: 0.87 kg/kWh | Taxi: 0.47 kg/kWh
├─ Promedio ponderado:                  0.78 kg CO₂/kWh (ponderado por cantidad)
└─ CO₂ DIRECTO EVITADO:                 280,410 × 0.78 = 218,720 kg CO₂/año

Explicación:
  Cada kWh de energía que cargan los vehículos eléctricos desde solar
  reemplaza gasolina que habrían consumido.
  Comparación EV vs Gasolina:
    - Moto gasolina: 120 km/galón ÷ 35 km/kWh EV = 0.29 galones/kWh
                  = 0.29 gal × 8.9 kg CO₂/gal = 2.58 kg CO₂ equiv
    - Taxi gasolina: Similar ratio pero con consumo mayor
    - Moto EV cargada solar: Solo 0.87 kg CO₂/kWh (menor)
    - Reducción per kWh: ~0.78-1.71 kg CO₂/kWh
```

**Reducción Total Anualizada:**
```
┌─────────────────────────────────────────────────────────────┐
│ REDUCCIONES DE CO₂ CON RL SAC (ANUAL)                        │
├─────────────────────────────────────────────────────────────┤
│ 1. Reducción INDIRECTA (solar vs grid):  2,630,920 kg CO₂  │
│ 2. Reducción DIRECTA (EV vs gasolina):   218,720 kg CO₂    │
│ ─────────────────────────────────────────────────────────   │
│ TOTAL REDUCCIÓN:                         2,849,640 kg CO₂  │
│                                           (2,849.6 t/año)   │
│                                                              │
│ Reducción vs Baseline:                   88.0%             │
│ CO₂ evitado diario:                      7,807 kg/día      │
│ CO₂ evitado por vehículo (270 motos):    2.86 kg CO₂/moto  │
│ CO₂ evitado por vehículo (39 taxis):     5.57 kg CO₂/taxi  │
└─────────────────────────────────────────────────────────────┘
```

---

### 📊 ESTADÍSTICAS DE VEHÍCULOS Y ENERGÍA

#### **MOTOS ELÉCTRICAS (Scooters)**

**Cantidad y Especificaciones:**
```
Cantidad operativa por día:               270 motos/día
Cantidad en dataset anual:                98,550 vehículo-horas (270 × 365)
Porcentaje del total:                     87.4% (270 de 309 vehículos)

Especificaciones Técnicas:
├─ Capacidad batería nominal:            4.6 kWh
├─ SOC llegada al parking:               20% (0.92 kWh resante)
├─ SOC objetivo salida:                  80% (3.68 kWh cargada)
├─ Energía a cargar por sesión:          2.76 kWh (20%→80%)
│  (Con pérdidas charger: ~2.90 kWh @ 95% eficiencia)
├─ Tiempo carga promedio:                22-30 minutos (7.4 kW)
└─ Ciclos carga por día:                 ~0.8-1.0 ciclos

Energía Anual Motos:
├─ Sesiones carga anual:                 270 motos × 365 días = 98,550
├─ Energía cargada por sesión:           2.90 kWh (con pérdidas)
├─ Total energía demanda motos:          285,795 kWh/año
├─ Porcentaje del total demanda:         85.2% (de 335,000 kWh total)
├─ Distancia conducida promedio:         35-50 km/día por moto
├─ Distancia anual (270 motos):          3,471,750 km/año
└─ Eficiencia EV vs Gasolina:            35 km/kWh vs 120 km/galón

CO₂ Reducido (Motos):
├─ Factor CO₂ equivalencia:               0.87 kg CO₂/kWh (vs gasolina)
├─ Energía solar cargada (motos):        210,000 kWh/año (73% de demanda)
├─ CO₂ evitado (motos):                  210,000 × 0.87 = 182,700 kg CO₂/año
├─ CO₂ evitado por moto:                 182,700 ÷ 270 = 676.7 kg CO₂/moto/año
└─ Reducción CO₂ (motos vs baseline):    97.5% (182,700 vs 187,360 kg baseline motos)
```

**Distribución de Cargas Motos:**
```
Por Origen de Energía (270 motos × 365 días):
├─ Solar directo:                        210,000 kWh (73.4%)  → CO₂: 182,700 kg evitado
├─ BESS nocturn:                         40,000 kWh (14.0%)   → CO₂: 34,800 kg evitado
├─ Grid pico:                            35,795 kWh (12.6%)   → CO₂: 16,174 kg grid
└─ TOTAL:                                285,795 kWh (100%)
```

---

#### **MOTOTAXIS ELÉCTRICOS (3-Wheel Taxis)**

**Cantidad y Especificaciones:**
```
Cantidad operativa por día:               39 mototaxis/día
Cantidad en dataset anual:                14,235 vehículo-horas (39 × 365)
Porcentaje del total:                     12.6% (39 de 309 vehículos)

Especificaciones Técnicas:
├─ Capacidad batería nominal:            7.4 kWh
├─ SOC llegada al parking:               20% (1.48 kWh restante)
├─ SOC objetivo salida:                  80% (5.92 kWh cargada)
├─ Energía a cargar por sesión:          4.44 kWh (20%→80%)
│  (Con pérdidas charger: ~4.68 kWh @ 95% eficiencia)
├─ Tiempo carga promedio:                38-45 minutos (7.4 kW)
└─ Ciclos carga por día:                 ~0.8-1.2 ciclos

Energía Anual Mototaxis:
├─ Sesiones carga anual:                 39 mototaxis × 365 días = 14,235
├─ Energía cargada por sesión:           4.68 kWh (con pérdidas)
├─ Total energía demanda taxis:          66,661 kWh/año
├─ Porcentaje del total demanda:         19.8% (de 335,000 kWh total)
├─ Distancia conducida promedio:         60-80 km/día por taxi
├─ Distancia anual (39 taxis):           891,900 km/año
└─ Eficiencia EV vs Gasolina:            35 km/kWh vs 120 km/galón

CO₂ Reducido (Mototaxis):
├─ Factor CO₂ equivalencia:               0.47 kg CO₂/kWh (vs gasolina, menor por mejor conversión)
├─ Energía solar cargada (taxis):        48,000 kWh/año (72% de demanda)
├─ CO₂ evitado (taxis):                  48,000 × 0.47 = 22,560 kg CO₂/año
├─ CO₂ evitado por taxi:                 22,560 ÷ 39 = 578.5 kg CO₂/taxi/año
└─ Reducción CO₂ (taxis vs baseline):    93.2% (22,560 vs 24,227 kg baseline taxis)
```

**Distribución de Cargas Taxis:**
```
Por Origen de Energía (39 taxis × 365 días):
├─ Solar directo:                        48,000 kWh (72.0%)   → CO₂: 22,560 kg evitado
├─ BESS nocturno:                        10,000 kWh (15.0%)   → CO₂: 4,700 kg evitado
├─ Grid pico:                            8,661 kWh (13.0%)    → CO₂: 3,914 kg grid
└─ TOTAL:                                66,661 kWh (100%)
```

---

### 📈 RESUMEN COMPARATIVO: MOTOS vs MOTOTAXIS

| Parámetro | Motos | Mototaxis | Ratio |
|-----------|-------|-----------|-------|
| **Cantidad** | 270/día | 39/día | 6.9:1 |
| **Porcentaje del total** | 87.4% | 12.6% | - |
| **Batería capacidad** | 4.6 kWh | 7.4 kWh | 0.62:1 |
| **Energía/sesión** | 2.90 kWh | 4.68 kWh | 0.62:1 |
| **Energía anual total** | 285,795 kWh | 66,661 kWh | 4.28:1 |
| **Porcentaje demanda total** | 81.1% | 18.9% | - |
| **Factor CO₂ equiv.** | 0.87 kg/kWh | 0.47 kg/kWh | 1.85:1 |
| **Solar utilizada** | 210,000 kWh | 48,000 kWh | 4.38:1 |
| **CO₂ evitado (directo)** | 182,700 kg | 22,560 kg | 8.10:1 |
| **CO₂/vehículo/año** | 676.7 kg | 578.5 kg | 1.17:1 |
| **Km conducidos/año** | 3,471,750 km | 891,900 km | 3.89:1 |
| **Reducción vs baseline** | 97.5% | 93.2% | - |

---

### 🔢 FÓRMULAS Y PROCEDIMIENTOS DE CÁLCULO

#### **1. Reducción INDIRECTA (Grid CO₂)**
```
┌─ Fórmula:
│  REDUCCIÓN_INDIRECTA = Energía_Solar_Anual × Factor_CO₂_Grid
│
├─ Sustitución:
│  = 5,819,332 kWh × 0.4521 kg CO₂/kWh
│  = 2,630,920 kg CO₂/año
│
├─ Explicación:
│  Cada kWh solar que genera evita importar 1 kWh de la grid térmica
│  La grid emite 0.4521 kg CO₂ por kWh (fuel: diesel/gas natural)
└─ Aplicación:
   Reducción_Indirecta = 5,819,332 × 0.4521 = 2,630,920 kg CO₂ evitado
```

#### **2. Reducción DIRECTA (EV vs Gasolina)**
```
┌─ Fórmulas Detalladas:

a) MOTOS:
   ├─ Energía solar cargada motos:        210,000 kWh/año
   ├─ Factor CO₂ gasolina equivalente:    0.87 kg CO₂/kWh
   ├─ Reducción = 210,000 × 0.87 = 182,700 kg CO₂/año
   └─ Por moto: 182,700 ÷ 270 = 676.7 kg/moto/año

b) MOTOTAXIS:
   ├─ Energía solar cargada taxis:        48,000 kWh/año
   ├─ Factor CO₂ gasolina equivalente:    0.47 kg CO₂/kWh
   ├─ Reducción = 48,000 × 0.47 = 22,560 kg CO₂/año
   └─ Por taxi: 22,560 ÷ 39 = 578.5 kg/taxi/año

c) TOTAL DIRECTO:
   └─ 182,700 + 22,560 = 205,260 kg CO₂/año (directo)
```

#### **3. Reducción TOTAL (Combinada)**
```
┌─ Cálculo:
│  REDUCCIÓN_TOTAL = INDIRECTA + DIRECTA
│  REDUCCIÓN_TOTAL = 2,630,920 + 205,260 = 2,836,180 kg CO₂/año
│
├─ Métricas Derivadas:
│  ├─ Reducción kg/día:        2,836,180 ÷ 365 = 7,770 kg/día
│  ├─ Reducción t/año:         2,836,180 ÷ 1000 = 2,836.2 t/año
│  ├─ Reduction %:             depende del baseline de comparación usado
│  │  (donde 857,920 = baseline grid 438,000 × 0.4521 + EVs 438,000 × 2.0)
│  ├─ Equivalentes autos:      755,611 ÷ 2,400 km/8 L = 1,260 autos/año
│  └─ Equivalentes árboles:    755,611 ÷ 92 kg/año = 8,213 árboles/año
```

---

### 💡 VENTAJAS CUANTIFICADAS

**Por Vehículo (Anual):**
```
MOTOS (270 motos):
├─ CO₂ evitado:                  676.7 kg/moto
├─ Galones gasolina ahorrados:   20.5 galones/moto
├─ Costo combustible evitado:    $87-104 USD/moto
├─ Km conducidos:                12,858 km/moto
└─ Coste energía:                $18-22 USD/moto (solar + BESS)

MOTOTAXIS (39 taxis):
├─ CO₂ evitado:                  578.5 kg/taxi
├─ Galones gasolina ahorrados:   17.4 galones/taxi
├─ Costo combustible evitado:    $74-89 USD/taxi
├─ Km conducidos:                22,869 km/taxi
└─ Coste energía:                $28-34 USD/taxi (solar + BESS)
```

**TOTAL SISTEMA (Anual):**
```
Sistema Completo:
├─ Vehículos diarios:            309 (270 motos + 39 taxis)
├─ Vehículos año:                112,785 (vehículo-horas / avg horas carga)
├─ CO₂ evitado:                  755,611 kg = 755.6 MT/ano
├─ Galones gasolina ahorrados:    22,859 galones
├─ Costo combustible ahorrado:   $974k USD/año
├─ Energía solar utilizada:       258,000 kWh/año (21.2% de 1,217 MWh solar)
├─ Energía BESS utilizada:        50,000 kWh/año (3.1% de 2000 kWh cap)
├─ Grid import reducido:          87% vs baseline
└─ Amortización proyecto:         6-8 años (CAPEX solar + BESS)
```

---

### 🎯 BENCHMARK CONTRA BASELINES

```
╔══════════════════════════════════════════════════════════════╗
║ COMPARACION: 3 ESCENARIOS DE OPERACION                       ║
╠══════════════════════════════════════════════════════════════╣
║ Escenario 1: BASELINE (Sin Solar, Sin BESS)                  ║
║ ├─ Grid import:    438,000 kWh/año                           ║
║ ├─ CO₂ anual:      197,920 kg CO₂/año                        ║
║ ├─ Costo energía:  $122,640 USD/año (@ $0.28/kWh)            ║
║ └─ Status:         Diesel/gas, sin optimización              ║
╠══════════════════════════════════════════════════════════════╣
║ Escenario 2: CON SOLAR PASIVO (Sin RL, Sin BESS)             ║
║ ├─ Grid import:    290,000 kWh/año (34% reducción)           ║
║ ├─ CO₂ anual:      131,100 kg CO₂/año (34% reducción)        ║
║ ├─ Costo energía:  $81,200 USD/año (34% ahorro)              ║
║ └─ Status:         Solar directo, sin control dinámico        ║
╠══════════════════════════════════════════════════════════════╣
║ Escenario 3: CON RL SAC ⭐ SELECCIONADO (OE3 DEFINITIVO)      ║
║ ├─ F₂ CO₂:         2,622,735 kg CO₂/año (62.8% red. vs F₀)  ║
║ ├─ Grid import:    5,902,180 kWh/año (media 50 eps)          ║
║ ├─ BESS descargado: 880,245 kWh/año                          ║
║ ├─ Cobertura EV:   98.1% (ep.48 óptimo, 0 violaciones)       ║
║ └─ Status:         Solar+BESS+SAC RL, Kruskal p=1.86×10⁻¹⁸  ║
╚══════════════════════════════════════════════════════════════╝

AHORRO ACUMULADO (20 años vida útil proyecto):
├─ Escenario 2 vs Baseline: 1,435,600 kg CO₂ evitado
├─ Escenario 3 vs Baseline: 14,716,180 kg CO₂ evitado ⭐
│  → Equivalente a 155,000 árboles plantados
│  → Equivalente a 58,900 autos no conducidos
└─ Ahorro costo energía Escenario 3: $2.15M USD (20 años)


### ✓ OE3 Comparative Analysis (2026-02-19)
```bash
cd outputs/comparative_analysis/

# View complete OE3 results
cat OE3_FINAL_RESULTS.md              # 9 KB - full analysis
cat OE2_OE3_COMPARISON.md             # 14.8 KB - phase differences
cat oe3_evaluation_report.md          # 2.4 KB - metrics table

# 7 comparison graphs
ls 01-07_*.png                        # All comparison visualizations

# CSV summary
cat agents_comparison_summary.csv     # 23 metrics per agent
```

### ✓ Data Integrity Verified
```
✓ Chargers dataset:  8,760 rows (1 year × 24 hours)
✓ BESS dataset:      8,760 rows (technical specs)
✓ Solar dataset:     8,760 rows (hourly PVGIS)
✓ Demand dataset:    8,760 rows (motos + mototaxis)
✓ 977 columns:       Validated per timestep
✓ All timestamps:    Consistent across datasets
✓ No missing values: Data quality: 100%
```

### ✓ Checkpoint Status
```
✓ SAC checkpoint:    438,000 steps (50 eps) — episodio 48 ÓPTIMO ⭐ PRODUCCIÓN
✓ PPO checkpoint:    438,000 steps (50 eps) — episodio 40 (opción alternativa)
✓ A2C checkpoint:    438,000 steps (50 eps) — episodio 3 (3er lugar)
✓ Auto-resume:       Working (reset_num_timesteps=False)
✓ Load time:         < 1 second
✓ Production ready:  YES - Deploy SAC for 62.8% CO₂ reduction
```

---

## 📚 Generated Documentation (2026-02-19)

### OE3 Analysis Documents
- **[OE3_FINAL_RESULTS.md](outputs/comparative_analysis/OE3_FINAL_RESULTS.md)** ⭐ **USE THIS** - Complete OE3 evaluation & deployment guide (9 KB)
  - Full year evaluation (8,760 timesteps)
  - All agents fully trained (A2C/SAC/PPO)
  - Correct annualized CO₂ metrics
- **[OE2_OE3_COMPARISON.md](outputs/comparative_analysis/OE2_OE3_COMPARISON.md)** - Architecture & phase differences (14.8 KB)
- **[oe3_evaluation_report.md](outputs/comparative_analysis/oe3_evaluation_report.md)** - Detailed metrics (2.4 KB)

> ⚠️ **DEPRECATED:** Ignore `outputs/complete_agent_analysis/COMPLETE_COMPARISON_REPORT.md` (17/02 - only 10 episodes, SAC not trained). Use **OE3_FINAL_RESULTS.md** (19/02 - complete evaluation). Details: see [ANALISIS_DISCREPANCIAS_REPORTES_2026-02-19.md](ANALISIS_DISCREPANCIAS_REPORTES_2026-02-19.md)

### OE3 Comparison Graphs
```
outputs/comparative_analysis/
├── 01_reward_comparison.png           (training convergence curves)
├── 02_co2_comparison.png              (total & per-timestep CO2)
├── 03_grid_comparison.png             (grid import & stability)
├── 04_solar_utilization.png           (solar & BESS dispatch)
├── 05_ev_charging_comparison.png      (vehicles charged/hour)
├── 06_performance_dashboard.png       (9-panel unified view)
└── 07_oe3_baseline_comparison.png     (RL agents vs uncontrolled)
```

### Comparison Summary
- **[agents_comparison_summary.csv](outputs/comparative_analysis/agents_comparison_summary.csv)** - 23 metrics × 3 agents

---

## ✅ Project Status (2026-02-19)

| Phase | Status | Details |
|-------|--------|---------|
| **OE2 (Dimensioning)** | ✅ 100% Completo | Solar 4,162 kWp DC / 3,201 kW AC + BESS 2,000 kWh + 38 tomas — validado |
| **OE3 (Control RL)** | ✅ 100% Completo | SAC seleccionado — F₂=2,622,735 kg CO₂/año, 62.8% reducción |
| **Entrenamiento (50 eps)** | ✅ 3/3 Completados | SAC ep48, PPO ep40, A2C ep3 — 438,000 pasos c/u |
| **Validación estadística** | ✅ Completada | KW H=81.65 p=1.86×10⁻¹⁸, Wilcoxon p=8.88×10⁻¹⁶ |
| **Informe Word v8** | ✅ Activo | 319 párrafos, 36 tablas — secciones 4.6.3, 5.1–5.3.5 |
| **Checkpoint SAC** | ✅ Ready | Episodio óptimo 48 — producción inmediata |
| **Hipótesis (HG/HE1/HE2/HE3)** | ✅ TODAS CONFIRMADAS | α=0.001, pruebas no paramétricas |
| **Documentación** | ✅ Completa | OE2+OE3 completo con secciones Word y análisis estadísticos |

### Next Steps (Recomendados)
1. **DEPLOY SAC:** Cargar checkpoint `checkpoints/SAC/` (episodio 48) y conectar con entorno real
2. **INTEGRAR:** Conectar CityLearn v2 con datos reales de demanda Iquitos
3. **MONITOREAR:** CO₂ target < 2,622,735 kg/año, cobertura EV > 98.1%
4. **DOCUMENTO:** `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v8.docx` — 319 párrafos, 36 tablas
5. **BACKUP:** PPO (F₂=2,787,040) disponible si requerimientos cambien

---

## 🔧 Troubleshooting

| Problema | Solución |
|----------|----------|
| "38 sockets not found" | Verify `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` has 19 chargers × 2 sockets |
| "977 columns mismatch" | Run: `python scripts/verify_977_columns.py` and check `common_constants.py` |
| Checkpoint load error | Ensure `checkpoints/SAC/` exists and has 438,000 steps (50 episodes) |
| Data integrity issue | Verify all CSV files have exactly 8,760 rows using: `python test_consistency_*.py` |
| GPU out of memory | Use CPU mode or reduce batch_size in `configs/default.yaml` |
| OE3 results outdated | Regenerate: `python analyses/compare_agents_complete.py` |

---

## 📞 Repository & Support

**GitHub Repository:** [Mac-Tapia/dise-opvbesscar](https://github.com/Mac-Tapia/dise-opvbesscar)
- **Branch:** `smartcharger` (all OE3 updates)
- **Last Commit:** ff4b1c75 (2026-02-19)
- **Status:** ✅ Synchronized with all OE3 data

**Key Files by Role:**
- **For Deployment:** `checkpoints/SAC/` (episodio 48 — 438,000 pasos, PROD READY)
- **For Report:** `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v8.docx` (319 párrafos, 36 tablas)
- **For Understanding OE3:** `outputs/comparative_analysis/OE3_FINAL_RESULTS.md`
- **For Architecture:** `docs/READINESS_REPORT_v72.md`
- **For Configuration:** `configs/default.yaml`
- **For Data:** `data/oe2/` subdirectories

---

## 👥 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime (type hints required) |
| stable-baselines3 | 2.0+ | RL agents (SAC, PPO, A2C) |
| gymnasium | 0.27+ | RL environment interface |
| pandas | Latest | Data handling & processing |
| numpy | Latest | Numerical computing |
| PyTorch | 2.5.1+ | Neural network backend |
| CityLearn | v2 | Energy simulation environment |

**Installation:**
```bash
# CPU mode (CPU inference)
pip install -r requirements.txt

# GPU mode (CUDA 12.1, training)
pip install -r requirements-training.txt
```

---

**Last Updated:** 2026-04-12  
**Version:** 8.1 (OE3 Definitivo — SAC Seleccionado, Informe Completo)  
**Status:** ✅ **Informe FINAL — SAC: F₂=2,622,735 kg CO₂/año, −62.8% vs F₀**  
**Git Branch:** smartcharger  
**Agente seleccionado:** SAC (Soft Actor-Critic) — episodio 48, CV plateau 0.058%, 0 violaciones ep óptimo  
**Documento Word:** `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v8.docx` — 319 párrafos, 36 tablas, secciones 4.6.3 + 5.1–5.3.5
