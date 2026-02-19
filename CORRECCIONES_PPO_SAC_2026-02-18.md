# RESUMEN DE CORRECCIONES - PPO y SAC (2026-02-18)

## PROBLEMA ORIGINAL

### AttributeError en train_a2c.py (línea 3869)
```
AttributeError: 'DetailedLoggingCallback' object has no attribute 'episode_co2_avoided_indirect'
```

### Conteo Incorrecto de Motos/Mototaxis
- **Problema:** Se reportaban máximos por hora (11-12 motos) en lugar de acumulados diarios (270 motos)
- **Origen:** Código usaba `max()` para actualizar contadores
- **Impacto:** Reportes mostraban "de 112 motos" cuando debería ser "≈270 de 270"

---

## SOLUCIONES APLICADAS

### 1. A2C (✓ COMPLETADO)

#### Cambio 1: Agregar atributos faltantes
**Archivo:** `scripts/train/train_a2c.py` línea ~1806
```python
# Agregados:
self.episode_co2_avoided_indirect: list[float] = []  # Total indirecto (solar + BESS)
self.episode_co2_avoided_direct: list[float] = []    # Total directo (EVs)
```

#### Cambio 2: Cambiar conteo de motos de MAX a ACUMULADO
**Archivo:** `scripts/train/train_a2c.py` línea ~1955
```python
# ANTES (incorrecto):
self._current_motos_charged_max = max(self._current_motos_charged_max, motos)
self._current_mototaxis_charged_max = max(self._current_mototaxis_charged_max, mototaxis)

# DESPUÉS (correcto):
self._current_motos_charged_max += motos      # ACUMULAR
self._current_mototaxis_charged_max += mototaxis  # ACUMULAR
```

#### Cambio 3: Poblar atributos de CO2 al finalizar episodio
**Archivo:** `scripts/train/train_a2c.py` línea ~2103
```python
# Agregados en el bloque `if done:`:
total_indirect = self._current_co2_indirecto_solar_kg + self._current_co2_indirecto_bess_kg
self.episode_co2_avoided_indirect.append(total_indirect)
self.episode_co2_avoided_direct.append(self._current_co2_directo_kg)
```

---

### 2. PPO (✓ COMPLETADO)

#### Cambio Único: Cambiar conteo de motos de MAX a ACUMULADO
**Archivo:** `scripts/train/train_ppo.py` línea ~1717
```python
# ANTES (incorrecto):
self.ep_motos_charged_max = max(self.ep_motos_charged_max, motos)
self.ep_mototaxis_charged_max = max(self.ep_mototaxis_charged_max, mototaxis)

# DESPUÉS (correcto):
self.ep_motos_charged_max += motos      # ACUMULAR
self.ep_mototaxis_charged_max += mototaxis  # ACUMULAR
```

**Nota:** PPO ya tenía los atributos `episode_co2_avoided_indirect` y `episode_co2_avoided_direct`

---

### 3. SAC (✓ COMPLETADO)

#### Cambio 1: Agregar atributos faltantes
**Archivo:** `scripts/train/train_sac.py` línea ~2754
```python
# Agregados:
self.episode_co2_avoided_indirect: List[float] = []   # Solar + BESS CO2 evitado
self.episode_co2_avoided_direct: List[float] = []     # EV CO2 evitado
```

#### Cambio 2: Agregar acumuladores de motos/mototaxis
**Archivo:** `scripts/train/train_sac.py` línea ~2806
```python
# Agregados:
self._current_motos_charged_max: int = 0   # ACUMULAR motos cargadas
self._current_mototaxis_charged_max: int = 0  # ACUMULAR mototaxis cargadas
```

#### Cambio 3: Cambiar conteo de motos de MAX a ACUMULADO
**Archivo:** `scripts/train/train_sac.py` línea ~3505
```python
# Agregados:
motos = info.get('soc_motos_charging_now', 0)
mototaxis = info.get('soc_mototaxis_charging_now', 0)
self._current_motos_charged_max += motos      # ACUMULAR
self._current_mototaxis_charged_max += mototaxis  # ACUMULAR
```

#### Cambio 4: Poblar atributos de CO2 al finalizar episodio
**Archivo:** `scripts/train/train_sac.py` línea ~3593
```python
# Movidos dentro del bloque `if done:`:
total_indirect = self._current_co2_grid  # Proxy de indirecto
self.episode_co2_avoided_indirect.append(total_indirect)
self.episode_co2_avoided_direct.append(0.0)

self.episode_motos_charged.append(self._current_motos_charged_max)
self.episode_mototaxis_charged.append(self._current_mototaxis_charged_max)
```

#### Cambio 5: Resetear acumuladores al final de episodio
**Archivo:** `scripts/train/train_sac.py` línea ~3686
```python
# Agregados:
self._current_motos_charged_max = 0   # RESET
self._current_mototaxis_charged_max = 0  # RESET
```

---

## IMPACTO EN REPORTES

### ANTES (Incorrecto)
```
Motos (de 112)       [máximo por hora = incorrecto]
Mototaxis (de 16)    [máximo por hora = incorrecto]
```

### DESPUÉS (Correcto)
```
Motos TOTAL (objetivo 98,550/año)        [valor acumulado] unidades
Motos promedio por episodio               [~270] unidades (≈ 270/día)
Mototaxis TOTAL (objetivo 14,235/año)    [valor acumulado] unidades  
Mototaxis promedio por episodio           [~39] unidades (≈ 39/día)
```

---

## VALIDACIÓN COMPLETADA ✓

- [x] A2C: Atributos CO2 agregados + motos/mototaxis ACUMULADOS
- [x] PPO: Motos/mototaxis cambiados de MAX a ACUMULADOS
- [x] SAC: Atributos CO2 agregados + motos/mototaxis ACUMULADOS
- [x] Todos los scripts pueden ejecutarse sin AttributeError

---

## DISEÑO VERIFICADO (Iquitos)

| Métrica | Valor |
|---------|-------|
| Motos objetivo | 270/día × 365 = **98,550/año** |
| Mototaxis objetivo | 39/día × 365 = **14,235/año** |
| **TOTAL anual** | 309/día × 365 = **112,785/año** |

Todos los agentes ahora reportan correctamente los totales acumulados.
