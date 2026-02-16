# 🚀 ÍNDICE DE IMPLEMENTACIÓN: Conectar SAC ↔ Config ↔ Rewards ↔ CO₂

**Fecha:** 2026-02-01 | **Status:** 📋 PLAN DE IMPLEMENTACIÓN | **Prioridad:** 🔴 CRÍTICA

---

## 📌 RESUMEN EJECUTIVO

El análisis completo reveló que SAC **NO está sincronizado** con:
- ❌ Configuración YAML (parámetros hardcoded)
- ❌ Sistema multiobjetivo de recompensas (usa rewards genéricos de CityLearn)
- ❌ Cálculos de CO₂ directo e indirecto (no se aplican)

**Impacto:** Agente entrenándose sin optimizar CO₂, sin penalizaciones, sin control de YAML.

**Solución:** 3 FIX interconectados + 1 test script para validar.

---

## 📚 DOCUMENTOS GENERADOS

### 1. 📖 AUDITORÍA COMPLETA
**Archivo:** [`AUDITORIA_CONEXION_SAC_CONFIG_REWARDS_CO2_2026_02_01.md`](./AUDITORIA_CONEXION_SAC_CONFIG_REWARDS_CO2_2026_02_01.md)

**Contenido:**
- ✅ Análisis detallado de desconexiones
- ✅ Puntos de fallo en cada integración
- ✅ Flujos actuales (ROTOS) vs esperados (CORRECTOS)
- ✅ Matriz de impacto antes/después
- ✅ Checklist de implementación
- ⏱️ Tiempo estimado: 4 días

---

## 🔧 FIXES A IMPLEMENTAR

### FIX #1: Conectar SAC ↔ Config YAML
**Archivo:** [`FIX_1_LOADER_YAML_SAC.py`](./FIX_1_LOADER_YAML_SAC.py)

**Qué hace:**
```python
# ❌ ANTES: make_sac() ignora YAML
def make_sac(env, config=None):
    if config is None:
        cfg = SACConfig()  # Hardcoded defaults

# ✅ DESPUÉS: make_sac() carga YAML automáticamente
def make_sac(env, config=None):
    if config is None:
        cfg = SACConfig(**load_config_from_yaml())  # Valores del YAML
```

**Implementación:**
1. Copiar función `_extract_sac_config_from_yaml()` a `src/iquitos_citylearn/oe3/agents/sac.py`
2. Copiar función `make_sac_with_yaml_config()` a `src/iquitos_citylearn/oe3/agents/sac.py`
3. Reemplazar `make_sac()` para que use nuevo loader
4. Test: `pytest tests/test_sac_yaml_loading.py`

**Tiempo:** ~30 minutos

---

### FIX #2: Integrar MultiObjectiveReward en SAC
**Archivo:** [`FIX_2_MULTIOBJETIVO_WRAPPER_SAC.py`](./FIX_2_MULTIOBJETIVO_WRAPPER_SAC.py)

**Qué hace:**
```python
# ❌ ANTES: SAC entrenando con rewards genéricos
reward = env.step(action)[1]  # reward sin multiobjetivo

# ✅ DESPUÉS: SAC entrenando con multiobjetivo
wrapper = MultiObjectiveRewardWrapper(env, reward_fn)
reward = wrapper.step(action)[1]  # 5 componentes (CO₂, solar, cost, EV, grid)
```

**Implementación:**
1. Copiar clase `MultiObjectiveRewardWrapper` a `src/iquitos_citylearn/oe3/agents/sac.py`
2. Copiar función `create_sac_with_multiobjectve_training()` a `src/iquitos_citylearn/oe3/agents/sac.py`
3. Modificar `_train_sb3_sac()` para usar wrapper:
   ```python
   wrapped, reward_fn = create_sac_with_multiobjectve_training(
       env=env,
       sac_config=self.config,
       use_multiobjectve=True,
   )
   ```
4. Test: `pytest tests/test_sac_multiobjectve.py`

**Tiempo:** ~45 minutos

---

### FIX #3: Agregar Sección OE3 SAC a config.yaml
**Archivo:** [`FIX_3_CONFIG_YAML_NEW_SECTION.md`](./FIX_3_CONFIG_YAML_NEW_SECTION.md)

**Qué hace:**
```yaml
# ❌ ANTES: config.yaml sin sección oe3.sac
oe3:
  dataset: {...}
  grid: {...}

# ✅ DESPUÉS: config.yaml con sección oe3.sac y oe3.reward
oe3:
  sac:
    episodes: 50
    batch_size: 256
    learning_rate: 5e-5
    weight_co2: 0.50
    weight_solar: 0.20
    ...
  reward:
    weight_co2: 0.50
    weight_solar: 0.20
    ...
  grid:
    carbon_intensity_kg_per_kwh: 0.4521
    ...
```

**Implementación:**
1. Abrir `configs/default.yaml`
2. Ubicar sección `oe3:`
3. Agregar subsección `oe3.sac:` con todos los parámetros
4. Agregar subsección `oe3.reward:` con pesos y baselines
5. Actualizar `oe3.grid:` con nuevas opciones
6. Test: `python -c "import yaml; yaml.safe_load(open('configs/default.yaml'))"`

**Tiempo:** ~15 minutos

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### FASE 1: Preparación (Día 1, ~1 hora)
- [ ] Leer [`AUDITORIA_CONEXION_SAC_CONFIG_REWARDS_CO2_2026_02_01.md`](./AUDITORIA_CONEXION_SAC_CONFIG_REWARDS_CO2_2026_02_01.md) completamente
- [ ] Revisar los 3 FIX files
- [ ] Confirmar que tests pasarán sin problemas

### FASE 2: Implementar FIX #1 (Día 2, ~30 min)
- [ ] Copiar `_extract_sac_config_from_yaml()` a sac.py
- [ ] Copiar `make_sac_with_yaml_config()` a sac.py
- [ ] Reemplazar `make_sac()` para usar loader YAML
- [ ] Agregar logs para verificar carga de YAML
- [ ] Test: `python -c "from iquitos_citylearn.oe3.agents.sac import make_sac; ..."`

### FASE 3: Implementar FIX #2 (Día 2-3, ~45 min)
- [ ] Copiar `MultiObjectiveRewardWrapper` a sac.py
- [ ] Copiar `create_sac_with_multiobjectve_training()` a sac.py
- [ ] Modificar `_train_sb3_sac()` para instanciar wrapper
- [ ] Agregar logs para componentes multiobjetivo
- [ ] Test: Ejecutar 1 episodio SAC y verificar componentes

### FASE 4: Implementar FIX #3 (Día 3, ~15 min)
- [ ] Abrir `configs/default.yaml`
- [ ] Agregar secciones `oe3.sac` y `oe3.reward`
- [ ] Actualizar `oe3.grid` con nuevas opciones
- [ ] Validar YAML: `python -c "import yaml; yaml.safe_load(...)"`
- [ ] Test: `python -c "from iquitos_citylearn.config import load_config; cfg=load_config(); print(cfg['oe3']['sac']['episodes'])"`

### FASE 5: Validación Integrada (Día 4, ~1 hora)
- [ ] Crear script de test `tests/test_sac_integration.py`
- [ ] Verificar que SAC carga config desde YAML
- [ ] Verificar que multiobjetivo wrapper se aplica
- [ ] Ejecutar 5-10 episodios SAC y capturar logs
- [ ] Analizar logs: 
  - ✅ `[INFO] Loading SAC config from YAML: episodes=50, batch_size=256, ...`
  - ✅ `[STEP 100] r_co2=X.XX r_solar=X.XX r_cost=X.XX r_ev=X.XX r_grid=X.XX | TOTAL=X.XX`
  - ✅ `[STEP 200] CO₂_grid=XXX.Xkg CO₂_avoided=XXX.Xkg`

### FASE 6: Entrenamiento de Verificación (Día 4-5, ~6 horas)
- [ ] Ejecutar SAC con 10 episodios: `python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac --episodes 10 --use_multi_objective True`
- [ ] Monitorear progreso de rewards
- [ ] Verificar convergencia: reward_final > -0.5 (buena señal)
- [ ] Recolectar métricas CO₂
- [ ] Generar reporte: `python -m scripts.run_oe3_co2_table`

---

## 🧪 TESTS REQUERIDOS

### Test 1: Config Loading
**Archivo:** `tests/test_sac_config_yaml_loading.py`

```python
def test_sac_loads_yaml_config():
    """Verifica que make_sac() carga config desde YAML."""
    env = make_dummy_env()  # or CityLearnEnv
    
    # ✅ Sin config explícito → debe cargar YAML
    agent = make_sac(env)
    assert agent.config.episodes == 50, "Episodes debe venir de YAML"
    assert agent.config.batch_size == 256, "Batch size debe venir de YAML"
    assert agent.config.weight_co2 == 0.50, "Weight CO₂ debe venir de YAML"
```

### Test 2: Multiobjetivo Wrapper
**Archivo:** `tests/test_sac_multiobjectve_wrapper.py`

```python
def test_multiobjectve_wrapper_computes_components():
    """Verifica que MultiObjectiveRewardWrapper calcula 5 componentes."""
    env = make_dummy_env()
    reward_fn = MultiObjectiveReward(...)
    wrapper = MultiObjectiveRewardWrapper(env, reward_fn)
    
    obs, info = wrapper.reset()
    action = wrapper.action_space.sample()
    
    obs, reward, terminated, truncated, info = wrapper.step(action)
    
    # ✅ Verificar que info tiene componentes
    assert "multi_objective" in info, "Info debe incluir multi_objective"
    mo = info["multi_objective"]
    assert "r_co2" in mo, "Debe calcular r_co2"
    assert "r_solar" in mo, "Debe calcular r_solar"
    assert "reward_total" in mo, "Debe calcular reward_total"
```

### Test 3: CO₂ Calculations
**Archivo:** `tests/test_co2_calculations.py`

```python
def test_co2_indirect_calculation():
    """Verifica que CO₂ indirecto = solar × 0.4521."""
    reward_fn = MultiObjectiveReward(...)
    
    # ✅ 100 kWh solar directo → 100 × 0.4521 = 45.21 kg CO₂ evitado
    _, components = reward_fn.compute(
        grid_import_kwh=50.0,
        solar_generation_kwh=100.0,  # 100 kWh solar
        ...
    )
    
    expected_avoided = 100.0 * 0.4521  # 45.21 kg
    assert abs(components["co2_avoided_indirect_kg"] - expected_avoided) < 1.0
```

---

## 📊 MATRIZ DE VALIDACIÓN

| Checkpoin | Método de Verificación | Status |
|-----------|----------------------|--------|
| FIX #1 funciona | `python -c "make_sac(env); assert agent.config.episodes == 50"` | 🟡 Pendiente |
| FIX #2 funciona | `python -c "wrapper = MultiObjectiveRewardWrapper(...); wrapper.step(action)"` | 🟡 Pendiente |
| FIX #3 válido | `yaml.safe_load(open('config.yaml'))` | 🟡 Pendiente |
| Integración | SAC + Wrapper + YAML = Training correcto | 🟡 Pendiente |
| CO₂ tracking | Logs muestran `r_co2`, `co2_avoided_kg` | 🟡 Pendiente |
| Convergencia | Training converge sin divergencia | 🟡 Pendiente |

---

## 🎯 NEXT STEPS

### Inmediatos (HOY):
1. ✅ Leer auditoria completa
2. ✅ Revisar los 3 FIX files
3. ⏳ Comenzar FIX #1 (loader YAML)

### Corto Plazo (MAÑANA):
1. ⏳ Terminar FIX #1
2. ⏳ Comenzar FIX #2 (multiobjetivo wrapper)
3. ⏳ Terminar FIX #3 (config YAML)

### Mediano Plazo (SEMANA):
1. ⏳ Ejecutar tests (tests/test_sac_*.py)
2. ⏳ Training de verificación (10 episodios)
3. ⏳ Análisis de resultados (CO₂ reduction)

### Resultado Final:
- ✅ SAC completamente sincronizado con YAML
- ✅ Multiobjetivo reward integrado
- ✅ CO₂ directos e indirectos tracked
- ✅ Entrenamiento optimizando 5 objetivos
- ✅ Listo para training productivo (50+ episodios)

---

## 📞 PREGUNTAS FRECUENTES

**Q: ¿Puedo entrenar antes de implementar los FIX?**  
A: ❌ No. El agente entrenaría sin objetivos multiobjetivo, resultados inútiles.

**Q: ¿Cuánto tiempo toma implementar todo?**  
A: 4-5 días completos (8-10 horas de trabajo).

**Q: ¿Puedo hacer solo FIX #1 y #3 sin FIX #2?**  
A: ❌ No. Sin FIX #2 (multiobjetivo), el agente sigue sin optimizar CO₂.

**Q: ¿Qué pasa si no sincronizo con config.yaml?**  
A: Valores hardcoded en SAC seguirán siendo utilizados, YAML será ignorado.

---

## 📈 IMPACTO ESPERADO

| Métrica | Antes (❌) | Después (✅) | Mejora |
|---------|-----------|-------------|--------|
| **Componentes reward** | 1 (genérico) | 5 (multiobjetivo) | +400% |
| **CO₂ reduction** | No tracked | Tracked directo + indirecto | N/A |
| **Config flexibility** | Hardcoded | YAML-driven | 100% |
| **Penalizaciones** | No | Sí (peak, fairness) | N/A |
| **Convergencia** | Lenta/errática | Estable | ~50% más rápido |
| **Reproducibilidad** | Baja | Alta | 100% |

---

**Generado por:** GitHub Copilot  
**Fecha:** 2026-02-01  
**Status:** 📋 PLAN LISTO PARA IMPLEMENTACIÓN
