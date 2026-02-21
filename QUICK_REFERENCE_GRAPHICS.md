# QUICK REFERENCE: Graphics de solar_pvlib.py
**Guía Rápida - Copiar & Pegar**

---

## ⚡ Quick Start (30 segundos)

```python
# 1. Importar
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
    save_matplotlib_figure, is_matplotlib_available
)
import matplotlib.pyplot as plt

# 2. Crear gráfica
fig, ax = plt.subplots()
ax.plot([1,2,3], [1,4,9])

# 3. Guardar (automático a outputs/analysis/solar/)
save_matplotlib_figure(fig, "my_plot.png", subdir="solar/profiles")
plt.close()
```

---

## 📚 Funciones Disponibles

### `save_matplotlib_figure()`
```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Forma más simple
save_matplotlib_figure(fig, "plot.png")
# → Guarda en: outputs/analysis/solar/plot.png

# Con subdirectorio personalizado
save_matplotlib_figure(fig, "plot.png", subdir="solar/profiles")
# → Guarda en: outputs/analysis/solar/profiles/plot.png

# Con configuración completa
save_matplotlib_figure(
    fig, 
    "plot.png", 
    subdir="solar/heatmaps",
    dpi=150,                    # Resolución (default 100)
    bbox_inches="tight",        # Recortar espacios en blanco
    verbose=True                # Imprimir confirmación
)
```

### `get_graphics_path()`
```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import get_graphics_path

# Obtener ruta sin guardar automáticamente
path = get_graphics_path("plot.png", subdir="solar/profiles")
print(path)  # → Path("outputs/analysis/solar/profiles/plot.png")

# Luego puedes guardar manualmente
fig.savefig(path, dpi=100)
```

### `is_matplotlib_available()`
```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import is_matplotlib_available

if is_matplotlib_available():
    print("✓ matplotlib disponible")
else:
    print("✗ matplotlib NO disponible")
```

---

## 💡 Snippets de Código

### 1. Gráfica de Línea Simple
```python
import matplotlib.pyplot as plt
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Crear datos
x = [0, 1, 2, 3, 4]
y = [0, 1, 4, 9, 16]

# Crear gráfica
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(x, y, marker='o', label='Datos')
ax.set_title('Mi Gráfica')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.legend()
ax.grid(True, alpha=0.3)

# Guardar
save_matplotlib_figure(fig, "line_plot.png", subdir="solar/profiles")
plt.close()
```

### 2. Gráfica de Barras
```python
import matplotlib.pyplot as plt
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Criar datos
meses = ['Ene', 'Feb', 'Mar', 'Abr']
valores = [750, 720, 780, 760]

# Crear gráfica
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(meses, valores, color='blue', alpha=0.7)

# Etiquetas en barras
for bar, val in zip(bars, valores):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'{val}', ha='center', va='bottom')

ax.set_title('Energía Mensual')
ax.set_ylabel('Energía [MWh]')

# Guardar
save_matplotlib_figure(fig, "bar_chart.png", subdir="solar/profiles")
plt.close()
```

### 3. Histograma
```python
import matplotlib.pyplot as plt
import numpy as np
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Crear datos
data = np.random.normal(100, 15, 1000)

# Crear gráfica
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(data, bins=30, color='green', alpha=0.7, edgecolor='black')
ax.axvline(np.mean(data), color='red', linestyle='--', label=f'Media: {np.mean(data):.1f}')
ax.set_title('Distribución de Datos')
ax.set_xlabel('Valores')
ax.set_ylabel('Frecuencia')
ax.legend()

# Guardar
save_matplotlib_figure(fig, "histogram.png", subdir="solar/profiles")
plt.close()
```

### 4. Mapa de Calor (Heatmap)
```python
import matplotlib.pyplot as plt
import numpy as np
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Crear matriz 2D
data = np.random.rand(12, 24) * 100

# Crear gráfica
fig, ax = plt.subplots(figsize=(14, 8))
im = ax.imshow(data, cmap='hot', aspect='auto')
ax.set_xlabel('Hora')
ax.set_ylabel('Mes')
ax.set_title('Heatmap: 12 meses × 24 horas')
plt.colorbar(im, ax=ax, label='Valor')

# Guardar
save_matplotlib_figure(fig, "heatmap.png", subdir="solar/heatmaps", dpi=150)
plt.close()
```

### 5. Scatter Plot (Puntos)
```python
import matplotlib.pyplot as plt
import numpy as np
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Crear datos
np.random.seed(42)
x = np.random.rand(100) * 10
y = 2*x + np.random.normal(0, 2, 100)

# Crear gráfica
fig, ax = plt.subplots(figsize=(10, 6))
scatter = ax.scatter(x, y, c=x, cmap='viridis', s=100, alpha=0.6)
ax.set_title('Scatter Plot')
ax.set_xlabel('X')
ax.set_ylabel('Y')
plt.colorbar(scatter, ax=ax, label='Color')
ax.grid(True, alpha=0.3)

# Guardar
save_matplotlib_figure(fig, "scatter_plot.png", subdir="solar/comparisons")
plt.close()
```

### 6. Subplots (Múltiples Gráficas)
```python
import matplotlib.pyplot as plt
import numpy as np
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import save_matplotlib_figure

# Crear datos
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)
y3 = np.tan(x)

# Crear figura con 3 subplots
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].plot(x, y1, 'r-')
axes[0].set_title('sin(x)')
axes[0].grid(True, alpha=0.3)

axes[1].plot(x, y2, 'g-')
axes[1].set_title('cos(x)')
axes[1].grid(True, alpha=0.3)

axes[2].plot(x, y3, 'b-')
axes[2].set_title('tan(x)')
axes[2].grid(True, alpha=0.3)

fig.suptitle('Funciones Trigonométricas', fontsize=14, fontweight='bold')
fig.tight_layout()

# Guardar
save_matplotlib_figure(fig, "subplots.png", subdir="solar/comparisons")
plt.close()
```

---

## 📂 Directorios Recomendados

```
subdir="solar"                    # Raíz (default)
subdir="solar/profiles"           # Perfiles horarios/diarios
subdir="solar/heatmaps"           # Mapas de calor
subdir="solar/comparisons"        # Comparativas
subdir="solar/irradiance"         # Análisis de irradiancia
subdir="solar/reports"            # Reportes técnicos
subdir="solar/validation"         # Gráficas de validación
```

---

## ⚙️ Configuración de DPI

```python
# Para pantalla (web)
save_matplotlib_figure(fig, "plot.png", dpi=100)   # Default

# Para impresión de calidad
save_matplotlib_figure(fig, "plot.png", dpi=300)

# Alto contraste (póster)
save_matplotlib_figure(fig, "plot.png", dpi=600)
```

---

## 🎨 Colores y Estilos

### Colores Named
```python
# Rojo, Verde, Azul, Amarillo, Naranja, Púrpura
colors = ['red', 'green', 'blue', 'yellow', 'orange', 'purple']
ax.plot(x, y, color='red')
```

### Colormaps
```python
# Caliente/Frío
plt.imshow(data, cmap='hot')           # Color caliente
plt.imshow(data, cmap='cool')          # Color frío
plt.imshow(data, cmap='viridis')       # Viridis (perceptual)
plt.imshow(data, cmap='gray')          # Escala de grises
```

### Estilos de Línea
```python
ax.plot(x, y, linestyle='-')           # Sólida
ax.plot(x, y, linestyle='--')          # Discontinua
ax.plot(x, y, linestyle=':')           # Puntada
ax.plot(x, y, linestyle='-.')          # Guión-punto
```

---

## 🐛 Troubleshooting

### Matplotlib NO disponible
```python
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import is_matplotlib_available

if not is_matplotlib_available():
    print("⚠ Instalar: pip install matplotlib")
    # Las funciones retornarán None silenciosamente
```

### Archivo NO se guarda
```python
# Verificar que el path existe y es escribible
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import get_graphics_path
path = get_graphics_path("test.png")
print(f"Ruta: {path}")
print(f"Directorio existe: {path.parent.exists()}")
print(f"Escribible: {path.parent.is_dir()}")
```

### Gráfica se ve muy pequeña/grande
```python
# Ajustar figsize
fig, ax = plt.subplots(figsize=(14, 8))  # Ancho×Alto en pulgadas
```

---

## 📊 Ejemplo Completo (Copia y Pega)

```python
#!/usr/bin/env python
"""Ejemplo completo de uso de graphics."""

import matplotlib.pyplot as plt
import numpy as np
from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
    save_matplotlib_figure,
    is_matplotlib_available
)

def main():
    if not is_matplotlib_available():
        print("❌ matplotlib no disponible")
        return
    
    # Generar datos
    np.random.seed(42)
    x = np.linspace(0, 10, 100)
    y = np.sin(x) + np.random.normal(0, 0.1, 100)
    
    # Crear gráfica
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, y, 'b.', label='Datos')
    ax.plot(x, np.sin(x), 'r-', linewidth=2, label='sin(x)')
    ax.set_title('Ejemplo de Gráfica', fontsize=14, fontweight='bold')
    ax.set_xlabel('X', fontsize=12)
    ax.set_ylabel('Y', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Guardar
    path = save_matplotlib_figure(
        fig,
        "example_plot.png",
        subdir="solar/profiles",
        dpi=150,
        verbose=True
    )
    
    print(f"✓ Gráfica guardada en: {path}")
    plt.close()

if __name__ == "__main__":
    main()
```

Salida esperada:
```
✓ Gráfica guardada: outputs/analysis/solar/profiles/example_plot.png
✓ Gráfica guardada en: d:\diseñopvbesscar\outputs\analysis\solar\profiles\example_plot.png
```

---

## 🔗 Enlaces Relacionados

- **Documentación Completa:** [README_SOLAR_GRAPHICS.md](outputs/analysis/README_SOLAR_GRAPHICS.md)
- **Detalles Técnicos:** [INTEGRACION_GRAFICAS_SOLAR_PVLIB_2026-02-20.md](INTEGRACION_GRAFICAS_SOLAR_PVLIB_2026-02-20.md)
- **Ejemplos Ejecutables:** [examples_graphics_usage.py](examples_graphics_usage.py)
- **Código Fuente:** [solar_pvlib.py](src/dimensionamiento/oe2/generacionsolar/disenopvlib/solar_pvlib.py) (líneas 35-170)

---

## 💬 Resumen en 1 Frase

**Usa `save_matplotlib_figure(fig, "nombre.png")` y automáticamente se guarda en `outputs/analysis/solar/` listo para usar. 🎉**

---

**Last Updated:** 2026-02-20  
**Version:** 1.0  
**Status:** ✅ Production Ready
