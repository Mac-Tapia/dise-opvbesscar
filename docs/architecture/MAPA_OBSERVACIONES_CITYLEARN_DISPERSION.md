# 🗺️ Mapa de Dispersión de Observaciones - CityLearn v2

**Objetivo:** Identificar todas las ubicaciones donde se construyen/usan observaciones de CityLearn para unificarlas.

---

## 📍 UBICACIONES ACTUALES DE OBSERVACIONES

### 1️⃣ **train_ppo_multiobjetivo.py** (PRINCIPAL)
- **Ruta:** `scripts/train/train_ppo_multiobjetivo.py`
- **OBS_DIM:** 156
- **Construcción:** `_make_observation(hour_idx: int)` (línea 587)
- **Componentes:**
  ```
  [0-14]   = Solar + tiempo (15 features)
  [15-52]  = Chargers: ocupancia × 38 sockets (38 features)
  [53-90]  = Chargers: potencia × 38 sockets (38 features)
  [91-128] = Grid/misc features (38 features)
  [129-131] = BESS (3 features)
  [132-155] = Tiempo + agregados (24 features)
  Total: 156
  ```
- **Estado:** ✅ ACTUALMENTE USADO
- **Líneas:** 433, 503, 587, 601, 848, 1158, 3159, 3354

---

### 2️⃣ **train_sac_multiobjetivo.py** (DUPLICADO)
- **Ruta:** `scripts/train/train_sac_multiobjetivo.py`
- **OBS_DIM:** Similar a PPO (156)
- **Construcción:** `_make_observation()` method similar
- **Estado:** ⚠️ CÓDIGO DUPLICADO (copia de PPO)
- **Líneas:** Similar al PPO

---

### 3️⃣ **train_sac_all_columns_expanded.py** (ALTERNATIVO)
- **Ruta:** `scripts/train/train_sac_all_columns_expanded.py`
- **OBS_DIM:** 66-dim (39-base + 27-observables)
- **Construcción:** `_make_observation(step: int)` (línea 435)
- **Componentes:**
  ```
  [0-38]   = Base system + dummy random (39 features)
  [39-66]  = Observable variables reales (27 features)
  Total: 66
  ```
- **Estado:** ⚠️ VERSIÓN EXPERIMENTAL/ALTERNATIVA
- **Líneas:** 435, 490

---

### 4️⃣ **train_sac_sistema_comunicacion_v6.py** (AVANZADO)
- **Ruta:** `scripts/train/train_sac_sistema_comunicacion_v6.py`
- **OBS_DIM:** 246-dim (v6.0 con cascada)
- **Construcción:** `_make_observation(hour_idx: int)` (línea 587)
- **Componentes:**
  ```
  [0-155]   = v5.3 básica (156 features)
  [156-193] = SOC por socket (38 features)
  [194-231] = Tiempo carga por socket (38 features)
  [232-233] = BESS dispatch signals (2 features)
  [234-235] = Solar bypass signals (2 features)
  [236-237] = Grid import signals (2 features)
  [238-245] = Agregados críticos (8 features)
  Total: 246
  ```
- **Estado:** ⚠️ EXTENSIÓN ESPECIALIZADA (comunicación v6)
- **Líneas:** 587, 650

---

### 5️⃣ **train_ppo_robust.py** (SIMPLE)
- **Ruta:** `scripts/train/train_ppo_robust.py`
- **OBS_DIM:** 50-dim
- **Construcción:** `_make_observation(hour_idx: int)` (línea 114)
- **Componentes:**
  ```
  [0-7]    = Energía del sistema (8 features)
  [8-49]   = Resto (42 features)
  Total: 50
  ```
- **Estado:** ⚠️ VERSIÓN SIMPLIFICADA/LEGACY
- **Líneas:** 114, 170

---

### 6️⃣ **src/utils/agent_utils.py** (UTILIDADES)
- **Ruta:** `src/utils/agent_utils.py`
- **Funciones:**
  - `clip_observations()` (línea 160) - Clipea valores extremos
  - `normalize_observations()` (línea 168) - Normaliza a media=0, std=1
  - `denormalize_observations()` (línea 183) - Revierte normalización
  - `validate_env_spaces()` (línea 32) - Valida obs_space del env
  - `ListToArrayWrapper` (línea 77) - Convierte lista → array numpy
- **Estado:** ✅ UTILIDADES REUTILIZABLES
- **Uso:** Por todos los agentes y scripts

---

### 7️⃣ **src/dataset_builder_citylearn/** (PARCIAL)
- **Ruta:** `src/dataset_builder_citylearn/`
- **Archivos:**
  - `rewards.py` (línea 720) - Maneja observation/action_space de wrapper
  - `main_build_citylearn.py` - Construye env de CityLearn
  - `data_loader.py` - Carga datos OE2
- **Estado:** ⚠️ MANEJO PARCIAL (toma obs del env, no las construye)
- **Constructor:** No construye observaciones, las recibe del env de CityLearn

---

### 8️⃣ **docs/FLUJO_DATOS_OE2_OE3.md** (ESPECIFICACIÓN)
- **Ruta:** `docs/FLUJO_DATOS_OE2_OE3.md`
- **Contenido:** Especificación detallada de estructura 156-dim
- **Estado:** ✅ ESPECIFICACIÓN OFICIAL
- **Líneas:** 71-118 (especificación detallada)

---

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. Duplicación Masiva
- PPO, SAC multiobjetivo tienen `_make_observation()` casi idénticos
- Código copiado y pegado, no reutilizable

### 2. Múltiples Dimensionalidades
- 156-dim (estándar, PPO/SAC)
- 246-dim (v6 comunicación, especializado)
- 66-dim (expandido alternativo)
- 50-dim (legacy/simple)
- **NO HAY FORMA CLARA DE ELEGIR CUÁL USAR**

### 3. Falta de Abstracción
- Construcción de observaciones ENGARRADA en cada script
- No hay classe reutilizable
- Cambios requieren editar 5+ archivos

### 4. Inconsistencia en Espacios
- `observation_space` definida en cada script
- No hay validación centralizada
- Riesgo de desalineación entre `_make_observation()` y `observation_space`

### 5. Sin Versionamiento de Observaciones
- No hay forma de trackear cambios en estructura de obs
- No hay histórico de migraciones

---

## ✅ SOLUCIÓN PROPUESTA

### Crear: `src/dataset_builder_citylearn/observations.py`

**Estructura:**
```python
class ObservationBuilder:
    """Constructor canónico de observaciones para CityLearn v2."""
    
    VERSION = "6.0"
    
    # Versiones disponibles
    OBS_156_STANDARD = "156_standard"      # v5.3 - Estándar
    OBS_246_CASCADA = "246_cascada"        # v6.0 - Con cascada
    OBS_66_EXPANDED = "66_expanded"        # Experimental
    OBS_50_SIMPLE = "50_simple"            # Legacy
    
    def __init__(self, version: str = OBS_156_STANDARD):
        self.version = version
        self.obs_dim = self._get_obs_dim(version)
        self.observation_space = self._get_observation_space(version)
    
    def make_observation(self, hour_idx: int, data: dict) -> np.ndarray:
        """Construye observación según versión seleccionada."""
        if self.version == self.OBS_156_STANDARD:
            return self._make_obs_156(hour_idx, data)
        elif self.version == self.OBS_246_CASCADA:
            return self._make_obs_246(hour_idx, data)
        # ... más versiones
    
    def _make_obs_156(self, hour_idx: int, data: dict) -> np.ndarray:
        """Construcción 156-dim estándar."""
        obs = np.zeros(156, dtype=np.float32)
        # Lógica de construcción ...
        return obs
    
    def _make_obs_246(self, hour_idx: int, data: dict) -> np.ndarray:
        """Construcción 246-dim cascada."""
        obs = np.zeros(246, dtype=np.float32)
        # Lógica extendida ...
        return obs
```

### Refactor Scripts de Entrenamiento

**Antes:**
```python
class RealOE2Environment:
    OBS_DIM = 156
    
    def reset(self):
        obs = self._make_observation(0)  # Duplicado en cada script
        return obs, {}
```

**Después:**
```python
from src.dataset_builder_citylearn.observations import ObservationBuilder

class RealOE2Environment:
    def __init__(self):
        self.obs_builder = ObservationBuilder(version="156_standard")
        self.OBS_DIM = self.obs_builder.obs_dim
        self.observation_space = self.obs_builder.observation_space
    
    def reset(self):
        obs = self.obs_builder.make_observation(0, self.data)
        return obs, {}
```

---

## 📊 MATRIZ DE CAMBIOS

| Archivo | Acción | Razón |
|---------|--------|-------|
| `src/dataset_builder_citylearn/observations.py` | ✨ CREAR | Módulo canónico |
| `scripts/train/train_ppo_multiobjetivo.py` | 🔄 REFACTOR | Usar ObservationBuilder |
| `scripts/train/train_sac_multiobjetivo.py` | 🔄 REFACTOR | Usar ObservationBuilder |
| `scripts/train/train_sac_all_columns_expanded.py` | 🔄 REFACTOR | Registrar versión 66-dim |
| `scripts/train/train_sac_sistema_comunicacion_v6.py` | 🔄 REFACTOR | Registrar versión 246-dim |
| `scripts/train/train_ppo_robust.py` | ❌ DEPRECAR | Legacy, migrar a 156-dim |
| `src/utils/agent_utils.py` | ✅ MANTENER | Utilidades reutilizables |
| `docs/FLUJO_DATOS_OE2_OE3.md` | 🔗 ACTUALIZAR | Link a observations.py |

---

## 🎯 RESULTADO ESPERADO

✅ **Single Source of Truth (SSOT) para observaciones**
- Todas las versiones centralizadas en `observations.py`
- Fácil agregar nuevas versiones
- Scripts refactor, sin lógica duplicada

✅ **Eliminación de Duplicación**
- `-2,000+ LOC` de código duplicado
- Mantenimiento simplificado

✅ **Versionamiento Claro**
- 156-dim (estándar, default)
- 246-dim (v6 cascada)
- 66-dim (experimental)
- 50-dim (legacy, deprecado)

✅ **Compatibilidad**
- Todos los scripts existentes usan el nuevo módulo
- Cero breaking changes para agentes entrenados

