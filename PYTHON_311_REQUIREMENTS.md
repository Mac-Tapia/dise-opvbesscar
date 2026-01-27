## ⚠️ REQUERIMIENTO CRÍTICO: PYTHON 3.11 EXACTAMENTE

Este proyecto **SOLO soporta Python 3.11 EXACTAMENTE**.

❌ **NO se soportan:**
- Python 3.10
- Python 3.12
- Cualquier otra versión

✅ **REQUERIDO:**
- Python 3.11 EXACTAMENTE

### ¿Por qué Python 3.11 exactamente?

1. **Compatibilidad con librerías**: Certain baselines y dependencias solo funcionan correctamente en 3.11
2. **Compilación de extensiones C**: Los binarios de CityLearn y stable-baselines3 están compilados para 3.11
3. **Tipo hints mejorados**: Python 3.11 tiene mejoras en type hints que el código requiere

### Instalación

#### Opción 1: Usar .python-version (si tienes pyenv)

```bash
pyenv install 3.11.0
cd d:\diseñopvbesscar
pyenv local 3.11.0
```

#### Opción 2: Descargar Python 3.11 desde python.org

1. Descarga Python 3.11 desde https://www.python.org/downloads/
2. Selecciona **Python 3.11** EXACTAMENTE
3. En el instalador, marca "Add Python 3.11 to PATH"
4. Instala

#### Opción 3: Crear venv con Python 3.11

```powershell
# Windows
python3.11 -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3.11 -m venv .venv
source .venv/bin/activate
```

#### Opción 4: Desinstalar versiones conflictivas

Si tienes Python 3.12 u otra versión instalada:

1. Desinstala versiones conflictivas desde "Agregar o quitar programas"
2. Descarga e instala Python 3.11 EXACTAMENTE
3. Verifica:
   ```bash
   python --version  # Debe mostrar Python 3.11.x
   ```

### Verificar Versión

```bash
python --version
```

**Debe mostrar:**
```
Python 3.11.x (donde x es cualquier número)
```

**Si ves:**
```
Python 3.12.x  ← ❌ INCORRECTO
Python 3.10.x  ← ❌ INCORRECTO
```

**Entonces tienes que cambiar a Python 3.11 EXACTAMENTE**

### Lanzar Entrenamiento A2C

Una vez que tengas Python 3.11 EXACTAMENTE:

```powershell
cd d:\diseñopvbesscar
python -m scripts.run_a2c_only --config configs/default.yaml
```

### Validar Setup

Para verificar que todo está configurado correctamente:

```bash
python verify_system.py
```

Si ves:
```
✓ Python 3.11 OK
✓ CUDA/GPU detectado
✓ Dataset listo
```

Entonces todo está bien y puedes lanzar A2C.
