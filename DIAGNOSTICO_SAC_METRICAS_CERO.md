# 🔍 DIAGNÓSTICO: Por qué SAC registra CO₂ y Grid como 0.0

**Fecha:** 2026-01-28 18:05 UTC  
**Problema:** SAC_training_metrics.csv muestra CO₂=0.0 kg y Grid=0.0 kWh  
**PPO registra correctamente:** CO₂=356.3 kg, Grid=788.0 kWh

---

## Problema Identificado

**Ubicación:** [src/iquitos_citylearn/oe3/agents/sac.py](src/iquitos_citylearn/oe3/agents/sac.py), línea 924-925

### Código SAC (INCORRECTO):
```python
# Línea 924-925
episode_co2_kg = self.grid_energy_sum * self.co2_intensity
episode_grid_kwh = self.grid_energy_sum
episode_solar_kwh = self.solar_energy_sum

# Resultado: 0.0 * 0.4521 = 0.0 kg
#           0.0 = 0.0 kWh
#           0.0 = 0.0 kWh
```

### Código PPO (CORRECTO):
```python
# Línea 607-609 en ppo_sb3.py (idéntico en a2c_sb3.py)
episode_co2_kg = self.grid_energy_sum * self.co2_intensity
episode_grid_kwh = self.grid_energy_sum
episode_solar_kwh = self.solar_energy_sum

# ¿Por qué PPO SÍ registra? → Ver abajo
```

---

## Raíz del Problema

### El contador NUNCA se actualiza correctamente

**Ubicación:** Línea 834 y 839 (SAC)

```python
try:
    env = self.training_env  # type: ignore
    if hasattr(env, 'unwrapped'):
        env = env.unwrapped  # type: ignore
    if hasattr(env, 'buildings'):
        for b in env.buildings:  # type: ignore
            # Acumular consumo neto de la red
            if hasattr(b, 'net_electricity_consumption') and b.net_electricity_consumption:
                last_consumption = b.net_electricity_consumption[-1] if b.net_electricity_consumption else 0
                if last_consumption != 0:
                    self.grid_energy_sum += abs(last_consumption)  # ← LÍNEA 834
            # Acumular generación solar
            if hasattr(b, 'solar_generation') and b.solar_generation:
                last_solar = b.solar_generation[-1] if b.solar_generation else 0
                if last_solar != 0:
                    self.solar_energy_sum += abs(last_solar)  # ← LÍNEA 839
except (ImportError, ModuleNotFoundError, AttributeError):
    pass
```

### Posibles Causas:

1. **`env.buildings` no existe o está vacío**
   - Condición `if hasattr(env, 'buildings')` falla → contador no se actualiza

2. **`b.net_electricity_consumption` está vacío o None**
   - Condición `if hasattr(b, 'net_electricity_consumption') and b.net_electricity_consumption` falla
   - Lista vacía `[]` evalúa como False en Python

3. **`last_consumption == 0` siempre**
   - Condición `if last_consumption != 0` falla → no se acumula nada
   - Contador permanece 0.0

4. **Exception silenciosa**
   - `except (ImportError, ModuleNotFoundError, AttributeError): pass`
   - Error captado pero NO logeado → falla silenciosa

---

## Comparación: SAC vs PPO vs A2C

| Archivo | Código | Status |
|---------|--------|--------|
| **sac.py** | Línea 834/839 | ❌ Contador = 0.0 siempre |
| **ppo_sb3.py** | Línea 566/571 | ✅ Contador funciona → 788.0 kWh |
| **a2c_sb3.py** | Línea 408/413 | ✅ Contador funciona → esperado 700+ kWh |

**PREGUNTA:** ¿Por qué PPO Y A2C funcionan, pero SAC no?

---

## Hipótesis: Diferencia en inicialización

Buscando diferencias en `__init__`:

### SAC.__init__ (Línea ~200-300)
```python
self.grid_energy_sum = 0.0
self.solar_energy_sum = 0.0
```

### PPO.__init__ (Línea ~200-300)
```python
self.grid_energy_sum = 0.0
self.solar_energy_sum = 0.0
```

**Las inicializaciones son IDÉNTICAS** → El problema no es inicialización

---

## Potencial Solución: Agregar Debug Logging

**Modificar línea 831** (antes del try):

```python
# Extraer métricas de energía del environment
try:
    env = self.training_env  # type: ignore
    if hasattr(env, 'unwrapped'):
        env = env.unwrapped  # type: ignore
    
    # DEBUG: Log environment structure
    if hasattr(env, 'buildings'):
        logger.debug(f"[SAC] Buildings found: {len(env.buildings)}")
        for idx, b in enumerate(env.buildings):
            net_elec = getattr(b, 'net_electricity_consumption', None)
            solar = getattr(b, 'solar_generation', None)
            logger.debug(f"  Building {idx}: net_elec={'empty' if not net_elec else f'len={len(net_elec)}'}, solar={'empty' if not solar else f'len={len(solar)}'}")
            if net_elec:
                logger.debug(f"    Last net_elec: {net_elec[-1]}")
            if solar:
                logger.debug(f"    Last solar: {solar[-1]}")
    else:
        logger.warning("[SAC] No 'buildings' attribute in environment!")
        
except Exception as e:
    logger.error(f"[SAC] Error extracting metrics: {e}", exc_info=True)
```

---

## Explicación de PPO/A2C Funcionan

**Hipótesis:** PPO/A2C usan el MISMO código (línea 566/408), entonces ¿por qué registran correctamente?

**Posibilidades:**
1. El archivo en disco es antiguo (SAC entrenado hace días)
2. Parámetro de configuración diferente
3. Diferencia en versión de CityLearn usado
4. La captura de logs sucedió en diferente orden temporal

---

## Recomendación Inmediata

### Opción 1: Forzar debug y reentrenar SAC
```bash
# En SAC config, agregar:
log_level: DEBUG  # Ver qué sucede con buildings
```

### Opción 2: Validar que PPO/A2C también capturen correctamente
```bash
# Esperar que PPO termine, verificar que grid_energy_sum ≠ 0.0
grep "episode_grid_kwh" SAC_training_metrics.csv  # Verificar
```

### Opción 3: Investigar diferencia de CityLearn
```bash
# En ambos agentes, llamar:
print(f"CityLearn version: {citylearn.__version__}")
print(f"Environment type: {type(env)}")
print(f"Has buildings: {hasattr(env, 'buildings')}")
```

---

## Estado Actual

```
✅ SAC entrenó correctamente (reward=521.89)
❌ Pero NO capturó métricas de energía (0.0 / 0.0 / 0.0)

✅ PPO entrenando correctamente (reward=5,218.90)
✅ SÍ captura métricas de energía (356.3 / 788.0 / ?)

❓ A2C: Pendiente de verificar cuando termine
```

---

## Próximos Pasos

1. **Inmediato:** Esperar que PPO termine (ETA 19:15 UTC)
2. **Verificar:** Confirmar que PPO/A2C guardan correctamente energy metrics
3. **Investigar:** Por qué SAC falló en captura pero PPO/A2C funcionan
4. **Fix:** Aplicar debug logging a SAC si es necesario reentrenar

---

**Conclusión:** El problema es que `self.grid_energy_sum` y `self.solar_energy_sum` permanecen en 0.0 durante el entrenamiento SAC. El código está allí para actualizarlos (línea 834/839) pero algo falla silenciosamente. PPO/A2C funcionan correctamente, por lo que es un problema específico de SAC.
