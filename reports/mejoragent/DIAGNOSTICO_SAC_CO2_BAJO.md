# 🔴 DIAGNÓSTICO: SAC tiene la PEOR reducción de CO2

**Fecha:** 2026-02-15  
**Resultado:** SAC = 37.09M kg CO2 vs PPO = 43.10M kg vs A2C = 42.65M kg  

---

## 📊 EVIDENCIA DEL PROBLEMA

### Métricas por Episodio SAC (TODAS con EV=0 y BESS=0):

| Episodio | Reward   | CO2 Grid  | EV Charging | BESS Discharge | Solar       |
|----------|----------|-----------|-------------|----------------|-------------|
| EP 1     | -3.61    | 2,940k kg | **0 kWh**   | **0 kWh**      | 8.29M kWh   |
| EP 2     | -3.06    | 2,586k kg | **0 kWh**   | **0 kWh**      | 7.40M kWh   |
| EP 3     | -3.67    | 2,940k kg | **0 kWh**   | **0 kWh**      | 8.29M kWh   |
| EP 4     | -3.73    | 2,940k kg | **0 kWh**   | **0 kWh**      | 8.29M kWh   |
| EP 5     | -3.85    | 2,940k kg | **0 kWh**   | **0 kWh**      | 8.29M kWh   |
| ...      | ...      | ...       | **0 kWh**   | **0 kWh**      | ...         |
| EP 10    | -2.19    | 2,939k kg | **0 kWh**   | **0 kWh**      | 8.29M kWh   |

### Comparación con PPO/A2C:

| Agente | EV Total     | BESS Total   | CO2 Evitado |
|--------|--------------|--------------|-------------|
| **SAC** | **0 kWh**   | **0 kWh**    | 37.09M kg   |
| PPO    | 2,983,478 kWh| 6,778,357 kWh| 43.10M kg   |
| A2C    | 5,555,775 kWh| 6,778,357 kWh| 42.65M kg   |

---

## 🔍 CAUSAS RAÍZ IDENTIFICADAS

### PROBLEMA 1: Info Dict con Claves Incorrectas (CRÍTICO)

**Descripción:** El diccionario `info` del ambiente SAC usaba claves diferentes a las que el callback esperaba.

**SAC devolvía:**
```python
info = {
    'chargers_demand_kw': charger_power_modulated,  # INCORRECTO
    'bess_action': bess_action,  # INCORRECTO (es 0-1, no kW)
    ...
}
```

**Callback buscaba:**
```python
ev_charging = info.get('ev_charging_kwh', info.get('ev_demand_kw', 0.0))  # -> 0.0
bess_power = info.get('bess_power_kw', 0.0)  # -> 0.0
```

**Resultado:** EV=0 kWh y BESS=0 kWh siempre.

**✅ CORRECCIÓN APLICADA:** Se agregaron las claves faltantes al info dict.

---

### PROBLEMA 2: Alpha Collapse (Colapso de Entropía)

**Evidencia del log:**
```
Alpha inicial: 0.9287
Alpha final:   0.0017  <- ¡Colapsó a casi 0!
[!] Alpha bajo (<0.01): 96 veces
```

**Consecuencia:** El agente dejó de explorar muy temprano:
- 51.1% de acciones saturadas en límite inferior
- Solo 4.7% en límite superior
- Política degenerada que "no hace nada"

**Causa:** `target_entropy=-19.5` es demasiado bajo para 39 acciones. SAC interpreta esto como "quiero poca variabilidad" y reduce alpha agresivamente.

---

### PROBLEMA 3: Saturación de Acciones

**Log:**
```
[ACCIONES]
- Mean:           +0.015      <- Casi todas en 0
- Std:            0.646
- Min/Max:        [-1.000, 1.000]
- Saturacion:     51.1% en limites inferiores, 4.7% en superiores
```

**Interpretación:** 
- El agente aprendió que "no actuar" (acciones mínimas) no es penalizado
- Como EV=0 no se reportaba, no había señal de reward por cargar vehículos
- El alpha bajo eliminó cualquier incentivo para explorar alternativas

---

### PROBLEMA 4: Poco Tiempo de Entrenamiento

- Solo **10 episodios** completados
- SAC es un algoritmo off-policy que necesita **más experiencias** en el buffer
- PPO/A2C son on-policy y convergen más rápido pero SAC necesita más timesteps

---

## ✅ SOLUCIONES PROPUESTAS

### 1. ✅ APLICADO: Corregir Info Dict

```python
info = {
    # NUEVAS CLAVES (compatibles con callback)
    'ev_charging_kwh': charger_power_modulated,
    'ev_charging_kw': charger_power_modulated,
    'ev_demand_kw': charger_power_modulated,
    'bess_power_kw': (bess_action - 0.5) * 2.0 * BESS_MAX_POWER_KW,
    'solar_generation_kwh': solar_h,
    'grid_import_kwh': grid_import,
    ...
}
```

### 2. PENDIENTE: Aumentar Target Entropy

```python
# ANTES (muy restrictivo)
target_entropy=-19.5  # Causa alpha collapse

# DESPUÉS (más exploración)
target_entropy=-5.0   # Mucho más exploración
# O incluso:
target_entropy='auto'  # Dejar que SB3 lo calcule automáticamente
```

### 3. PENDIENTE: Aumentar Exploración Inicial

```python
policy_kwargs={
    'log_std_init': -1.0,  # ANTES: -2.0 (exploración muy baja)
    # -1.0 -> std = 0.37 (más exploración)
    # -2.0 -> std = 0.14 (poca exploración)
}
```

### 4. PENDIENTE: Considerar Alpha Fijo

```python
# En lugar de auto-tune que puede colapsar:
ent_coef=0.2  # Valor fijo, exploración constante
# O usar alpha con floor:
# Modificar código para: alpha = max(0.1, auto_alpha)
```

### 5. PENDIENTE: Más Timesteps de Entrenamiento

```python
total_timesteps=262_800  # 30 episodios (3x actual)
# O mejor:
total_timesteps=876_000  # 100 episodios (10x actual)
```

### 6. OPCIONAL: Noise Injection

Agregar ruido Ornstein-Uhlenbeck a las acciones durante exploración:
```python
use_sde=True,  # Stateful exploration (mejor para espacios continuos)
sde_sample_freq=8,  # Resamplear cada 8 steps
```

---

## 🔧 ARCHIVO A MODIFICAR

**`scripts/train/train_sac_multiobjetivo.py`**

### Cambios Recomendados en `SACConfig.for_gpu()`:

```python
@classmethod
def for_gpu(cls) -> 'SACConfig':
    return cls(
        # ... otras config ...
        
        # CAMBIO 1: Target entropy más alto
        target_entropy=-5.0,  # ERA: -19.5
        
        # CAMBIO 2: Más exploración inicial
        policy_kwargs={
            'net_arch': dict(pi=[256, 256], qf=[256, 256]),
            'activation_fn': torch.nn.ReLU,
            'log_std_init': -1.0,  # ERA: -2.0
            # ...
        },
        
        # CAMBIO 3: Usar SDE para mejor exploración
        use_sde=True,
        sde_sample_freq=8,
    )
```

---

## 📈 RESULTADOS ESPERADOS DESPUÉS DE CORRECCIONES

| Métrica              | SAC Actual | SAC Esperado | PPO (referencia) |
|----------------------|------------|--------------|------------------|
| EV Charging Total    | 0 kWh      | ~3M kWh      | 2.98M kWh        |
| BESS Discharge       | 0 kWh      | ~6M kWh      | 6.78M kWh        |
| CO2 Evitado          | 37.09M kg  | ~42-44M kg   | 43.10M kg        |
| Alpha Final          | 0.0017     | >0.05        | N/A              |
| Reward Final         | -2.19      | >0           | Positivo         |

---

## 🚀 COMANDO PARA RE-ENTRENAR SAC

```powershell
# 1. Limpiar checkpoints SAC (mantener PPO/A2C)
Remove-Item -Recurse -Force checkpoints\SAC\*

# 2. Re-entrenar con más episodios
python scripts/train/train_sac_multiobjetivo.py --timesteps 262800

# 3. Monitorear alpha y EV charging durante entrenamiento
# Verificar que:
#   - Alpha > 0.05 durante todo el entrenamiento
#   - EV charging > 0 desde episodio 1
#   - BESS discharge > 0
```

---

## 📋 CHECKLIST DE VERIFICACIÓN

- [x] Info dict corregido con claves `ev_charging_kwh`, `bess_power_kw`
- [ ] `target_entropy` aumentado a -5.0 o mayor
- [ ] `log_std_init` aumentado a -1.0
- [ ] Re-entrenamiento ejecutado
- [ ] EV charging > 0 verificado en episodios
- [ ] BESS discharge > 0 verificado
- [ ] Alpha > 0.05 durante todo el entrenamiento
- [ ] CO2 evitado comparable a PPO/A2C

---

**Autor:** Análisis automático pvbesscar  
**Archivos modificados:** `scripts/train/train_sac_multiobjetivo.py`
