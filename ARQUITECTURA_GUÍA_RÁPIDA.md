# 📍 ARQUITECTURA DEL PROYECTO - GUÍA RÁPIDA
**Ubicación**: Raíz del proyecto  
**Propósito**: Referencia rápida de estructura, archivos activos, y qué-está-dónde  
**Audiencia**: Developers, maintainers, newcomers

---

## 🚀 5-SEGUNDO SUMMARY

**pvbesscar** = EV Charging Optimization with Solar + Battery in Iquitos 🇵🇪

- **Input**: OE2 specs (solar, BESS, chargers, demand)
- **Process**: Build CityLearn dataset → Train RL agents (SAC/PPO/A2C)
- **Output**: 24-29% CO₂ reduction vs 3,059 t/year baseline

---

## 📂 DONDE ENCONTRAR TODO

### 🟢 CÓDIGO PRODUCTIVO (Usar estos)

| Qué | Dónde | Qué Hace |
|-----|-------|----------|
| **Chargers** | `src/dimensionamiento/oe2/disenocargadoresev/chargers.py` | Define 38 sockets (19×2) |
| **Solar** | `src/dimensionamiento/oe2/generacionsolar/.../solar_pvlib.py` | 4,050 kWp → 8.29M kWh/year |
| **BESS** | `src/dimensionamiento/oe2/disenobess/bess.py` | 1,700 kWh simulación horaria |
| **Dataset** | `src/citylearnv2/dataset_builder/dataset_builder.py` | 8,760 timesteps CityLearn |
| **Baseline** | `src/baseline/baseline_calculator_v2.py` | CO₂: 3,059 t (CON_SOLAR) |
| **Agents** | `src/agents/{sac,ppo_sb3,a2c_sb3}.py` | SAC/PPO/A2C training |
| **Rewards** | `src/rewards/rewards.py` | Multi-objetivo (CO2, Solar, EV) |

### 🟡 SCRIPTS DE EJECUCIÓN (Sistema oficial)

| Script | Propósito | Ejecución |
|--------|-----------|-----------|
| `scripts/train/train_sac_multiobjetivo.py` | Entrenar SAC | `python scripts/train/train_sac_multiobjetivo.py` |
| `scripts/train/train_ppo_multiobjetivo.py` | Entrenar PPO | `python scripts/train/train_ppo_multiobjetivo.py` |
| `scripts/train/train_a2c_multiobjetivo.py` | Entrenar A2C | `python scripts/train/train_a2c_multiobjetivo.py` |
| `execute_baselines_and_compare.py` | Baselines | `python execute_baselines_and_compare.py` |

### 🔵 VALIDACIÓN (Tests)

| Test | Ubicación | Status | Ejecutar |
|------|-----------|--------|----------|
| Dataset + Baseline integration | `test_integration_dataset_baseline.py` | ✅ 7/7 PASSING | `python test_integration_dataset_baseline.py` |

### 🟣 DATOS (18.8 MB OE2)

**Ubicación**: `data/oe2/`

```
data/oe2/
├── chargers/chargers_ev_ano_2024_v3.csv      (15.5 MB)  ← 38 sockets
├── bess/bess_simulation_hourly.csv           (1.7 MB)   ← v5.4
├── demandamallkwh/demandamallhorakwh.csv     (0.2 MB)
├── Generacionsolar/pv_generation_hourly_citylearn_v2.csv (1.4 MB)
└── chargers/chargers_real_statistics.csv     (tiny)
```

### 🟠 RESULTADOS (Outputs)

**Ubicación**: `outputs/`

```
outputs/
├── baselines/              ← CON_SOLAR vs SIN_SOLAR comparación
├── agent_training/         ← Métricas de entrenamiento
└── reports/                ← Reportes generados
```

### 🔴 CONFIGURACIONES (Config)

**Ubicación**: `configs/agents/`

```
configs/agents/
├── sac_config.yaml         ← SAC hyperparamters
├── ppo_config.yaml         ← PPO hyperparamters
├── a2c_config.yaml         ← A2C hyperparamters
└── agents_config.yaml      ← Config maestra (opcional)
```

---

## 🚫 QUÉ NO USAR (Archivos Obsoletos/Huérfanos)

### ❌ Python Scripts en Raíz

**~90 archivos en raíz son DEPRECATED**:
```
❌ analyze_*.py                (análisis obsoletos)
❌ audit_*.py                  (auditorías históricas)
❌ BALANCE_ENERGETICO_*.py     (análisis viejos)
❌ BESS_*.py                   (scripts BESS experimentales)
❌ callback_*.py               (callbacks descontinuados)
❌ check_*.py                  (checks viejos)
❌ fix_*.py                    (fixers temporales)
❌ FLUJO_*.py | flujo_*.py     (flujos experimentales)
❌ generate_*.py               (generadores viejos)
❌ validate_*.py               (validadores viejos)
❌ verify_*.py                 (verificadores viejos)
❌ hyperparams_analysis.py
❌ TRAINING_MASTER.py          (reemplazado por train_*.py)
```

**¿Por qué no usar?**
- Reemplazados por código en `src/`
- No sincronizados con v5.4
- Documentación interna obsoleta
- No son parte del pipeline oficial

### ❌ Documentación en Raíz

**~210 archivos .md históricos** (REVISAR/ARCHIVAR):
```
❌ AUDITORIA_*.md              (auditorías antiguas)
❌ BALANCE_ENERGETICO_*.md     (análisis viejos)
❌ DIMENSIONAMIENTO_*.md       (dimensionamientos históricos)
❌ ESTADO_*.md                 (estados finales anteriores)
❌ RESUMEN_*.md                (resúmenes históricos)
❌ VALIDACION_*.md             (validaciones antiguas)
```

**Mantener solo**:
- `README.md` (índice)
- `AUDITORÍA_ARQUITECTURA_PROYECTO_2026-02-13.md` (este análisis)
- `FLOW_ARCHITECTURE.md` (flujo)
- `INTEGRACION_COMPLETADA_v54.md` (estado actual)
- `LIMPIEZA_COMPLETADA_2026-02-13.md` (auditoría de limpieza)
- `CONFLICTOS_ARCHIVOS_v54.md` (análisis conflictos)

---

## 🎯 FLUJO MÍNIMO (¿Cómo empezar?)

### 1️⃣ Verificar datos OE2

```bash
# Datos deben estar presentes y correctos
ls -lh data/oe2/chargers/chargers_ev_ano_2024_v3.csv
ls -lh data/oe2/bess/bess_simulation_hourly.csv
```

### 2️⃣ Validar dataset builder

```bash
# Debe pasar 7/7 tests
python test_integration_dataset_baseline.py
```

### 3️⃣ Elegir agente y entrenar

```bash
# Entrenar SAC (recomendado)
python scripts/train/train_sac_multiobjetivo.py

# O PPO
python scripts/train/train_ppo_multiobjetivo.py

# O A2C
python scripts/train/train_a2c_multiobjetivo.py
```

### 4️⃣ Comparar resultados

```bash
# Ejecutar baselines
python execute_baselines_and_compare.py

# Ver resultados
cat outputs/baselines/baseline_comparison.csv
```

---

## 📊 MATRIZ DE ARCHIVOS ACTIVOS

### ✅ Core (Necesario para producción)

```
MUST-HAVE (Sin estos, nada funciona):
├── src/citylearnv2/dataset_builder/dataset_builder.py
├── src/dimensionamiento/oe2/disenocargadoresev/chargers.py
├── src/dimensionamiento/oe2/generacionsolar/disenopvlib/solar_pvlib.py
├── src/dimensionamiento/oe2/disenobess/bess.py
├── src/baseline/baseline_calculator_v2.py
├── data/oe2/*.csv (5 files)
└── test_integration_dataset_baseline.py
```

### ⭐ Training (Para RL agents)

```
TRAINING (necesario para entrenar):
├── scripts/train/train_sac_multiobjetivo.py
├── scripts/train/train_ppo_multiobjetivo.py
├── scripts/train/train_a2c_multiobjetivo.py
├── src/agents/sac.py | ppo_sb3.py | a2c_sb3.py
└── src/rewards/rewards.py
```

### 📈 Evaluation (Para validar)

```
EVALUATION (necesario para comparar):
├── execute_baselines_and_compare.py
├── src/baseline/citylearn_baseline_integration.py
└── src/baseline/agent_baseline_integration.py
```

---

## 🔍 VALIDACIÓN RÁPIDA

### Check 1: Datos OE2 Presentes

```bash
# DEBE dar 5 archivos
ls data/oe2/*/*.csv | wc -l
# Esperado: 5

# BESS debe ser 1,700 kWh v5.4
grep -r "1700" src/citylearnv2/dataset_builder/dataset_builder.py | head -1
# Esperado: bess_cap = 1700.0

# Chargers debe ser 38 sockets
grep "38" src/dimensionamiento/oe2/disenocargadoresev/chargers.py | head -1
# Esperado: algo mencionando 38 sockets
```

### Check 2: Tests Pasando

```bash
python test_integration_dataset_baseline.py 2>&1 | grep "TODOS"
# Esperado: ✅ TODOS LOS TESTS PASARON (7/7)
```

### Check 3: Scripts Training Presentes

```bash
# Deben existir los 3 scripts
ls scripts/train/train_*.py | wc -l
# Esperado: 3
```

---

## 🎓 FLUJO TÍPICO DE UN DEVELOPER

```
Day 1: Onboarding
  1. Lee README.md
  2. Lee FLOW_ARCHITECTURE.md (este archivo básicamente)
  3. Lee AUDITORÍA_ARQUITECTURA_PROYECTO_2026-02-13.md
  4. Ejecuta: python test_integration_dataset_baseline.py
  5. Verifica que 7/7 tests pasen ✅

Day 2: Entrenar un agente
  1. Elige: SAC (recomendado), PPO, o A2C
  2. Ejecuta: python scripts/train/train_*_multiobjetivo.py
  3. Monitorea progreso (tensorboard en outputs/)
  4. Espera ~5-7 horas (SAC en GPU RTX 4060)

Day 3: Evaluar resultados
  1. Ejecuta: python execute_baselines_and_compare.py
  2. Compara vs baseline (3,059 t CO₂)
  3. Mide mejora (esperado: 24-29% reducción)
  4. Genera report

Day 4+: Optimización
  1. Ajusta reward weights en src/rewards/rewards.py
  2. Ajusta hyperparameters en configs/agents/
  3. Reentrana
  4. Compara nuevamente
```

---

## 🆘 TROUBLESHOOTING

| Problema | Causa | Solución |
|----------|-------|----------|
| "ModuleNotFoundError: baseline_definitions" | Imports en `__init__.py` apuntan archivos viejos | Ver `src/baseline/__init__.py` - debe importar v54 y v2 |
| "8,760 rows ≠ expected" | Solar data no es horaria (ej 15-min) | Resample `df.resample('h').mean()` |
| Tests fallan | Datos OE2 no presentes | Verificar `data/oe2/` existe + 5 archivos |
| Agent no entrena | Env dimensions inválidas | Verificar obs=394, act=38 exactamente |
| Baselines no calculan | baseline_calculator_v2 no encontrado | Verificar imports en `execute_baselines_and_compare.py` |

---

## 📞 QUICK LINKS

- **Architecture** (NUEVO): [AUDITORÍA_ARQUITECTURA_PROYECTO_2026-02-13.md](AUDITORÍA_ARQUITECTURA_PROYECTO_2026-02-13.md)
- **Data Flow**: [FLOW_ARCHITECTURE.md](FLOW_ARCHITECTURE.md)
- **Integration Status**: [INTEGRACION_COMPLETADA_v54.md](INTEGRACION_COMPLETADA_v54.md)
- **Cleanup Report**: [LIMPIEZA_COMPLETADA_2026-02-13.md](LIMPIEZA_COMPLETADA_2026-02-13.md)
- **Conflicts Analysis**: [CONFLICTOS_ARCHIVOS_v54.md](CONFLICTOS_ARCHIVOS_v54.md)

---

## ✅ CHECKLIST - ¿ESTÁ LISTO EL SISTEMA?

- ✅ Datos OE2 (5 files 18.8 MB) presentes
- ✅ BESS v5.4 (1,700 kWh) configurado
- ✅ Chargers: 38 sockets verificados
- ✅ Dataset builder: 2,327 líneas activas
- ✅ Tests: 7/7 pasando
- ✅ Baselines: 3,059 t (CON_SOLAR) calculado
- ✅ Training scripts: SAC/PPO/A2C listos
- ✅ Rewards: Multi-objetivo configurado
- ✅ Imports: v54 + v2 sincronizados

**Resultado**: 🟢 **SISTEMA LISTO PARA PRODUCCIÓN**

---

**Última actualización**: 2026-02-13  
**Mantenedor**: Project Team  
**Versión**: v5.4 Final

