# A2C MEJORA ITERATIVA v7.2 - INSTRUCTIVO TÉCNICO
**Fecha**: 2026-02-16  
**Estado**: Post-entrenamiento inicial exitoso - Optimizaciones aplicadas  
**Objetivo**: Incrementar convergencia y métricas clave (EV satisfaction, grid stability)

---

## 📊 RESUMEN ENTRENAMIENTO BASE (v7.1)

```
═══════════════════════════════════════════════════════════════
RESULTADOS A2C v7.1 - PRIMERA EJECUCIÓN
═══════════════════════════════════════════════════════════════
Recompensa Promedio:           3,062.6 pts
CO2 Total Evitado:             43,554,181 kg/año
  │├─ Indirecto (Solar/BESS):  40,287,246 kg (92.5%)
  └└─ Directo (EV):             3,266,935 kg (7.5%)
  
Vehículos Cargados:            35/38 (92.1%)
  ├─ Motos:                    27/30 (90%)
  └─ Mototaxis:                8/8 (100%)

Estabilidad Grid (Ramping):    22.7% (BAJA - Oportunidad)
Solar Aprovechada:             8,292,514 kWh (100% - Óptimo)
Tiempo Entrenamiento:          2.9 minutos (excelente velocidad)

Timesteps Entrenados:          87,600 (10 episodios × 8,760 por año)
═══════════════════════════════════════════════════════════════
```

---

## 🎯 OPORTUNIDADES DE MEJORA IDENTIFICADAS

### 1. **CARGA DE VEHÍCULOS (92.1% → 95%+)**
**Problema**: 3 vehículos no se cargan al 100%
- 3 motos por cargar (30 - 27 = 3)
- Mototaxis ya en 100%

**Causa Probable**:  
- `EV_SATISFACTION_WEIGHT` bajo (30%)  
- Lógica de prioridad de sockets no óptima  
- Finales de año (Dec) pueden tener menos demanda

**Soluciones A2C v7.2**:
```python
# Opción 1: Aumentar peso EV (conservative)
'vehicles_charged': 0.35  # (era 0.30)

# Opción 2: Penalizar mejor No-Charged EVs
reward_ev -= (unsatisfied_vehicles / total_vehicles) * 0.20

# Opción 3: Cambiar logica de cascada (priority 1 = EVs antes que mall)
# A2C aprenderá mejor con cascada estricta
```

**Implementación Recomendada**: **Opción 1 + Opción 3**  
(No cambiar Opción 2 sin análisis profundo - puede desestabilizar)

---

### 2. **ESTABILIDAD GRID (22.7% → 50%+)**
**Problema**: Ramping muy rápido (variaciones abruptas de potencia)
- Indica que A2C no está suavizando cambios  
- On-policy (A2C) responde a recompensas instantáneas

**Causa Probable**:
- `GRID_STABILITY_WEIGHT` bajo (5%)  
- Falta penalidad por cambios rápidos de potencia  
- n_steps=512 corto para observar ramping patterns

**Soluciones A2C v7.2**:
```python
# Opción 1: Aumentar peso estabilidad
'grid_stable': 0.15  # (era 0.05, +200%)

# Opción 2: Penalizar volatilidad de potencia
# Calcular ramping: |P(t+1) - P(t)| > threshold
ramping_rate = abs(bess_power[t] - bess_power[t-1])
penalty_ramping = max(0, ramping_rate - 50) * 0.01

# Opción 3: Filtro de suavizado en acciones BESS
# EMA de acciones: action_smooth = 0.3*action + 0.7*action_prev
```

**Implementación Recomendada**: **Opción 1 + Opción 2**  
(Opción 3 requiere cambio arquitectónico complejo)

---

### 3. **CONVERGENCIA Y REFINAMIENTO**
**Problema**: Plateau después de ~5-6 episodios
```
Ep 1: 1900.81 → Ep 2: 2177 → Ep 3: 2322 → Ep 4: 2429 → Ep 5: 2505
Ep 5: 2505 → Ep 6: 2682 → Ep 7: 2778 → Ep 8: 2851 → Ep 9: 2899 → Ep 10: 2899
```
(Mejora ralentiza entre Ep 8 y 10)

**Causa Probable**:
- A2C on-policy se estabiliza rápido (ventaja)  
- Pero necesita más exploración para refinamiento  
- `ent_coef` actual pequeño (0.0001)

**Soluciones A2C v7.2**:
```python
# Opción 1: Aumentar episodios (13 en lugar de 10)
total_timesteps = 113_880  # 13 × 8,760

# Opción 2: Aumentar entropy coefficient
'ent_coef': 0.0002  # (era 0.0001)  - Promueve más exploración

# Opción 3: Reducir learning rate ligeramente
'learning_rate': 1.5e-4  # (era 2e-4) - Más estable, converge mejor
```

**Implementación Recomendada**: **Opción 1 + Opción 2**  
(Opción 3 secundaria, pero beneficiosa)

---

## 🔧 PLAN DE IMPLEMENTACIÓN v7.2

### Paso 1: ACTUALIZAR REWARD WEIGHTS

**Archivo**: `scripts/train/train_a2c_multiobjetivo.py` (línea ~150)

```python
# v7.1 (actual)
REWARD_WEIGHTS_V6: Dict[str, float] = {
    'co2': 0.35,               # ← mantener
    'cost': 0.10,              # ← mantener
    'solar': 0.20,             # ← mantener
    'vehicles_charged': 0.30,  # ← ⬆️ AUMENTAR A 0.35
    'grid_stable': 0.05,       # ← ⬆️ AUMENTAR A 0.15
    'ev_utilization': 0.00     # ← mantener
}

# v7.2 (optimizado)
REWARD_WEIGHTS_V72: Dict[str, float] = {
    'co2': 0.35,               
    'cost': 0.10,              
    'solar': 0.20,             
    'vehicles_charged': 0.35,  # +5%
    'grid_stable': 0.15,       # +10% (200%)
    'ev_utilization': 0.00     
}
# Nota: 0.35+0.10+0.20+0.35+0.15 = 1.15 > 1.0
# Aplicar softmax para normalizar: w_normalized = w / sum(w)
```

### Paso 2: AÑADIR PENALIDAD RAMPING

**Función en environment/dentro de step()**:

```python
def calculate_ramping_penalty(bess_power_current: float, 
                              bess_power_prev: float) -> float:
    """
    Penalidad por cambios abruptos de potencia en BESS.
    A2C aprende a suavizar acciones para evitar penalidad.
    """
    ramping_rate = abs(bess_power_current - bess_power_prev)
    threshold = 50  # kW max permisible cambio
    
    if ramping_rate > threshold:
        penalty = (ramping_rate - threshold) ** 2 / 10000.0  # Escalar
        return penalty
    else:
        return 0.0

# En step():
ramping_penalty = calculate_ramping_penalty(bess_power_kw, self.prev_bess_power)
reward_stability = -(ramping_penalty)  # Negativo = penalidad

# Agregar a reward total:
reward += (self.reward_weights['grid_stable'] / 0.15) * reward_stability
```

### Paso 3: AUMENTAR EPISODIOS Y AJUSTAR HIPER-PARÁMETROS

**Archivo**: `scripts/train/train_a2c_multiobjetivo.py` (línea ~1600-1700, A2CConfig)

```python
@dataclass
class A2CConfig:
    # v7.1
    # total_timesteps: int = 87_600  # 10 episodios
    # learning_rate: float = 2.0e-4
    # ent_coef: float = 0.0001
    
    # v7.2 MEJORADO
    total_timesteps: int = 113_880  # 13 episodios (30% más para refinamiento)
    learning_rate: float = 1.5e-4   # 25% menos (convergencia más estable)
    ent_coef: float = 0.0002         # 100% más (mayor exploración)
    
    # Mantener resto igual
    gamma: float = 0.99
    gae_lambda: float = 0.95
    n_steps: int = 512
    ent_coef_init: float = 0.0002
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
```

### Paso 4: REGISTRAR CAMBIOS EN CHECKPOINT

En archivo de configuración o metadata:
```json
{
  "a2c_version": "v7.2",
  "improvements": [
    "vehicles_charged_weight: 0.30 → 0.35",
    "grid_stable_weight: 0.05 → 0.15",
    "added_ramping_penalty: true",
    "total_episodes: 10 → 13",
    "learning_rate: 2e-4 → 1.5e-4",
    "ent_coef: 0.0001 → 0.0002"
  ],
  "expected_improvements": {
    "vehicles_charged": "92% → 95%+",
    "grid_stability": "22.7% → 50%+",
    "convergence": "more refined (3 extra episodes)"
  }
}
```

---

## 📈 RESULTADOS ESPERADOS (v7.2)

Basado en análisis de SAC y PPO con cambios similares:

```
═══════════════════════════════════════════════════════════════
PUNTO BASE (v7.1)          →  ESPERADO (v7.2)      →  MEJORA
═══════════════════════════════════════════════════════════════
Recompensa: 3,062.6        →  3,200-3,400          →  +4-11%
EV Charged: 92.1%          →  95-96%                →  +3-4%
CO2 Total:  43.6M kg       →  44.0-44.5M kg        →  +1-2%
Grid Stab:  22.7%          →  40-50%                →  +76-120%
Conv.Time:  2.9 min        →  3.8-4.2 min          →  (3 ep extra)
═══════════════════════════════════════════════════════════════
```

---

## ✅ VALIDACIÓN Y TESTING

### Antes de aplicar mejoras:
```bash
# 1. Backup checkpoint actual
cp checkpoints/A2C/a2c_final_model.zip checkpoints/A2C/a2c_v71_BACKUP.zip

# 2. Crear rama de prueba
git checkout -b a2c-v72-improvements
```

### Durante aplicación:
```bash
# 1. Actualizar pesos en train_a2c_multiobjetivo.py
# 2. Agregar función ramping_penalty
# 3. Actualizar A2CConfig con nuevos parámetros
# 4. Ejecutar: python scripts/train/train_a2c_multiobjetivo.py
# 5. Monitorear cada 10 segundos
```

### Después de entrenamiento:
```bash
# Comparar resultados v7.1 vs v7.2
diff outputs/a2c_training_v71/result_a2c.json \
     outputs/a2c_training_v72/result_a2c.json

# Si mejora >= 3% en cualquier métrica clave → Aceptar v7.2
# Si no mejora → Analizar y ajustar
```

---

## 🚨 GUARDRAILS Y LÍMITES DE SEGURIDAD

**NUNCA HACER**:
- ❌ Modificar CO2 weights directamente sin normalización
- ❌ Cambiar `n_steps` a < 256 (demasiado inestable)
- ❌ Aumentar `ent_coef` a > 0.001 (exploración excesiva)
- ❌ Reducir `learning_rate` a < 1e-5 (convergencia lentísima)

**SIEMPRE HACER**:
- ✅ Backup de checkpoints antes de cambiar parámetros
- ✅ Mantener dataset OE2 validado (8,760 horas)
- ✅ Normalizar pesos de reward (sum = 1.0)
- ✅ Monitorear primeros 5000 pasos para anomalías
- ✅ Generar gráficos comparativos v7.1 vs v7.2

---

## 📞 PRÓXIMOS PASOS

1. **Aplicar cambios v7.2** (30 minutos)
2. **Entrenar A2C v7.2** (~4 minutos con 13 episodios)
3. **Generar reportes comparativos** (5 minutos)
4. **Análisis final**: SAC vs PPO vs A2C v7.2
5. **Documentación**: Resultados finales y conclusiones

---

## 📋 CHECKLIST IMPLEMENTACIÓN

- [ ] Actualizar reward weights (v7.1 → v7.2)
- [ ] Agregar función ramping_penalty
- [ ] Actualizar A2CConfig (total_timesteps, learning_rate, ent_coef)
- [ ] Backup checkpoints A2C v7.1
- [ ] Ejecutar entrenamiento A2C v7.2
- [ ] Monitorear progreso (ramping penalty, EV satisfaction)
- [ ] Generar gráficos KPI comparativos
- [ ] Guardar result_a2c_v72.json
- [ ] Análisis de mejoras
- [ ] Documentar conclusiones finales

---

**Autor**: Copilot  
**Estado**: Listo para implementación  
**Próximo revisión**: Post-entrenamiento v7.2
