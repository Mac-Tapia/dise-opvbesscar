# 📊 Gráficas y Análisis Solar - outputs/analysis/

## 📁 Estructura de Directorios

Este directorio centraliza TODAS las gráficas y visualizaciones generadas por los módulos de simulación solar:

```
outputs/analysis/
├── solar/                  # Gráficas específicas de análisis PV - GENERADAS POR: solar_pvlib.py
│   ├── profiles/          # Perfiles de generación (24h, diarios, mensuales)
│   ├── irradiance/        # Análisis de irradiancia (GHI, DNI, DHI)
│   ├── comparison/        # Comparativas (módulos, inversores, escenarios)
│   └── technical/         # Reportes técnicos visuales
├── bess/                  # Gráficas de BESS (si se generan)
├── balance/               # Gráficas de balance energético (si se generan)
└── README_SOLAR_GRAPHICS.md  # Este archivo

```

## 🔧 Cómo Usar las Funciones de Gráficas en `solar_pvlib.py`

### 1. **Obtener la ruta para guardar una gráfica**

```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import get_graphics_path

# Obtener ruta para guardar en outputs/analysis/solar/
graphics_path = get_graphics_path("mi_grafica.png", subdir="solar")

# Obtener ruta en subdirectorio específico
profiles_path = get_graphics_path("profile_24h.png", subdir="solar/profiles")

# Obtener ruta en outputs/analysis/ (sin subdirectorio)
analysis_path = get_graphics_path("resumen.png", subdir=None)
```

### 2. **Guardar una figura de matplotlib automáticamente**

```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure
import matplotlib.pyplot as plt

# Crear figura
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(datos)
ax.set_title("Generación Solar Diaria")

# Guardar automáticamente en outputs/analysis/solar/
save_matplotlib_figure(
    fig=fig,
    filename="generacion_solar_diaria.png",
    subdir="solar",
    dpi=100,
    verbose=True
)

plt.close(fig)
```

### 3. **Verificar si matplotlib está disponible**

```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import is_matplotlib_available

if is_matplotlib_available():
    print("matplotlib instalado - se generarán gráficas")
else:
    print("matplotlib NO instalado - solo se generarán datos CSV")
```

## 📊 Ejemplo Completo: Generar Gráfica de Perfil Solar

```python
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
    get_graphics_path,
    save_matplotlib_figure,
    is_matplotlib_available,
    GRAPHICS_OUTPUT_DIR,
)

def generate_solar_profile_graphic(df_solar: pd.DataFrame) -> None:
    """Genera gráfica de perfil solar 24h."""
    
    if not is_matplotlib_available():
        print("⚠ matplotlib no disponible - saltando gráficas")
        return
    
    # Crear figura
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    
    # Gráfica 1: Potencia AC por hora
    ax1.plot(df_solar['hora'], df_solar['ac_power_kw'], marker='o', linewidth=2)
    ax1.set_xlabel('Hora del día')
    ax1.set_ylabel('Potencia AC (kW)')
    ax1.set_title('Perfil de Generación Solar 24h - Potencia AC')
    ax1.grid(True, alpha=0.3)
    
    # Gráfica 2: Irradiancia GHI
    ax2.plot(df_solar['hora'], df_solar['ghi_wm2'], color='orange', marker='s', linewidth=2)
    ax2.set_xlabel('Hora del día')
    ax2.set_ylabel('Irradiancia GHI (W/m²)')
    ax2.set_title('Irradiancia en Plano Horizontal')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Guardar gráfica en outputs/analysis/solar/profiles/
    save_matplotlib_figure(
        fig=fig,
        filename="perfil_solar_24h.png",
        subdir="solar/profiles",
        dpi=100,
        verbose=True
    )
    plt.close(fig)
    
    print(f"✓ Gráfica guardada en: {GRAPHICS_OUTPUT_DIR}/solar/profiles/perfil_solar_24h.png")

```

## 🎯 Ubicación Centralizada de Gráficas

**Todas las gráficas generadas por `solar_pvlib.py` se guardan en:**

```
outputs/analysis/
└── solar/
    ├── profiles/           # Perfiles de generación
    ├── irradiance/         # Análisis de irradiancia
    ├── comparison/         # Comparativas de módulos/inversores
    └── technical/          # Reportes técnicos
```

**No** se mezclan con:
- ✗ `data/oe2/` (datos brutos y procesados)
- ✗ `outputs/balance_energetico/` (gráficas de balance)
- ✗ `outputs/comparative_analysis/` (análisis de agentes RL)

## 📝 Constantes en `solar_pvlib.py`

```python
# Rutas centralizadas para gráficas
GRAPHICS_OUTPUT_DIR = Path("outputs/analysis")        # Directorio raíz
SOLAR_GRAPHICS_SUBDIR = GRAPHICS_OUTPUT_DIR / "solar" # Subdirectorio solar

# Funciones de apoyo
_ensure_graphics_directories()      # Crear directorios
get_graphics_path(filename, subdir) # Obtener ruta
save_matplotlib_figure(fig, ...)   # Guardar figura
is_matplotlib_available()           # Verificar disponibilidad
```

## ✅ Checklist para Integración

- [x] Directorio `outputs/analysis/solar/` creado
- [x] Funciones `get_graphics_path()` agregadas a `solar_pvlib.py`
- [x] Función `save_matplotlib_figure()` agregada a `solar_pvlib.py`
- [x] Función `is_matplotlib_available()` agregada a `solar_pvlib.py`
- [x] Importación condicional de matplotlib en `solar_pvlib.py`
- [x] Documentación de `generate_solar_dataset_citylearn_complete()` actualizada
- [x] Este README creado con ejemplos

## 🔄 Flujo de Datos

```
solar_pvlib.py (cálculos)
    ↓
get_graphics_path() → outputs/analysis/solar/XXX.png
    ↓
save_matplotlib_figure() → Guardar figura en disco
    ↓
outputs/analysis/solar/ (gráficas listas para análisis)
```

## 📌 Notas Importantes

1. **Backward Compatibility**: Los datos siguen guardándose en `data/oe2/` como antes
2. **Opcional**: Si matplotlib no está instalado, solo se generan datos CSV (sin gráficas)
3. **Subdirectorios**: Se crean automáticamente según se necesite
4. **Resolución**: Default 100 DPI (parametrizable en `save_matplotlib_figure()`)

---

**Actualizado:** 2026-02-20  
**Módulo:** `src/dimensionamiento/oe2/generacionsolar/disenopvlib/solar_pvlib.py`
