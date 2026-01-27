# 🚨 REQUERIMIENTO: PYTHON 3.11 EXACTAMENTE

## ¿Cuál es el problema?

Este proyecto requiere **Python 3.11 EXACTAMENTE**.

Solo se soporta Python 3.11. No se soporta Python 3.12, 3.10 ni ninguna otra versión.

## ¿Por qué?

Hay compatibilidad de librerías que requieren exactamente Python 3.11:
- CityLearn v2 (compilado para 3.11)
- Stable-Baselines3 (binarios para 3.11)
- Otras dependencias específicas

## Solución RÁPIDA (5 minutos)

### 1. Desinstalar versiones conflictivas (Opcional pero recomendado)

Si quieres limpiar tu sistema de otras versiones de Python:
1. Abre "Agregar o quitar programas"
2. Busca otras versiones de Python (3.10, 3.12, etc)
3. Haz clic en "Desinstalar"

### 2. Descargar Python 3.11

Ve a: **https://www.python.org/downloads/**

Busca **Python 3.11** (por ejemplo, 3.11.8 o 3.11.9)

⚠️ **IMPORTANTE**: Selecciona 3.11, NO 3.12, NO 3.13

### 3. Instalar Python 3.11

1. Descarga el instalador de Python 3.11
2. Ejecuta el instalador
3. **MARCA**: "Add Python 3.11 to PATH"
4. Haz clic en "Install Now"

### 4. Verificar

Abre PowerShell y ejecuta:

```powershell
python --version
```

Debe mostrar:
```
Python 3.11.x
```

Si muestra Python 3.12 u otra versión, entonces esa versión está en PATH. Vuelve al instalador de Python 3.11 y marca "Add to PATH".

## Solución CON VENV (Sin cambiar sistema global)

Si no quieres desinstalar otras versiones de Python:

### Opción A: Con Python 3.11 ya instalado

```powershell
# Crear venv con Python 3.11
python3.11 -m venv .venv

# Activar
.venv\Scripts\activate

# Verificar
python --version  # Debe mostrar Python 3.11.x
```

### Opción B: Con pyenv (gestor de versiones)

```powershell
# Instalar pyenv (si no lo tienes)
# Ve a: https://github.com/pyenv-win/pyenv-win

pyenv install 3.11.0
pyenv local 3.11.0

python --version  # Debe mostrar Python 3.11.0
```

## Una vez que tengas Python 3.11

### Lanzar A2C

```powershell
# Opción 1: Directamente
python -m scripts.run_a2c_only --config configs/default.yaml

# Opción 2: Con verificación de seguridad
python launch_a2c_safe.py

# Opción 3: Con PowerShell
.\launch_a2c_python311_check.ps1
```

## Verificación Final

Para asegurar que todo está bien:

```powershell
python verify_system.py
```

Debe mostrar:
```
✓ Python 3.11 OK
✓ CUDA/GPU detectado
✓ Dataset listo
✓ Todo OK - puedes ejecutar A2C
```

---

## ⏱️ Tiempo estimado

- Descargar Python 3.11: 2 minutos
- Instalar: 2 minutos
- Lanzar A2C: 1 minuto

**Total: 5 minutos**

---

## 🆘 Si tienes problemas

1. **"Python command not found"**
   - Reinicia PowerShell después de instalar
   - Verifica que Python esté en PATH

2. **"Python 3.11 is not installed"**
   - Descarga e instala Python 3.11 desde python.org

3. **"Still getting a different version"**
   - Desinstala esa versión completamente
   - Limpia PATH: Remove rutas conflictivas
   - Reinicia PowerShell

---

## 📝 Resumen de acciones

| Acción | Comando/Pasos |
|--------|---------------|
| Descargar Python 3.11 | https://www.python.org/downloads/ → Busca 3.11 |
| Instalar | Ejecuta el .exe y marca "Add to PATH" |
| Verificar | `python --version` |
| Crear venv (alternativa) | `python3.11 -m venv .venv` |
| Activar venv | `.venv\Scripts\activate` |
| Lanzar A2C | `python -m scripts.run_a2c_only --config configs/default.yaml` |

¡Listo! Una vez que tengas Python 3.11, todo funcionará.
