# 📚 GUÍA DE MANTENIMIENTO: Mantener src/agents/ Limpio

**Creado**: 2026-02-04  
**Propósito**: Mantener src/agents/ limpio y optimizado después de la limpieza

---

## 🎯 OBJETIVO

Establecer prácticas para prevenir acumulación de cachés obsoletos y mantener la carpeta `src/agents/` limpia y eficiente.

---

## 🔍 QUÉ SON LOS CACHÉS PYTHON

### `__pycache__/` - Bytecode Cache
- **Qué es**: Archivos `.pyc` compilados por Python
- **Propósito**: Acelerar importaciones (Python interpreta bytecode pre-compilado)
- **Creado por**: Python automáticamente al importar módulos
- **Ubicación**: Una carpeta `__pycache__/` por cada carpeta con .py
- **Tamaño**: ~50-100 KB por archivo .py
- **Riesgo si se Borra**: NINGUNO (se regenera automáticamente)
- **Riesgo si se Mantiene**: Basura, confusión, warnings en git

### `.mypy_cache/` - Type Checking Cache
- **Qué es**: Caché de análisis de tipos para mypy
- **Propósito**: Acelerar mypy type checking
- **Creado por**: mypy cuando ejecutas `mypy src/`
- **Ubicación**: Una carpeta `.mypy_cache/` en la raíz del proyecto
- **Tamaño**: ~2-5 MB
- **Riesgo si se Borra**: NINGUNO (se regenera automáticamente)
- **Riesgo si se Mantiene**: Puede crecer excesivamente, confusión

---

## 📋 CHECKLIST DE MANTENIMIENTO

### Mensual (O cuando notarás cambios)

- [ ] Ejecutar: `python -c "from src.agents import *"`
  - Verifica que importa funcionan
  - Regenera __pycache__ automáticamente

- [ ] Revisar tamaño: `du -sh src/agents/`
  - Si > 2 MB (sin contar .venv), hay problema
  - Si > 5 MB, ejecutar limpieza

- [ ] Verificar `.gitignore` contiene:
  ```
  __pycache__/
  *.pyc
  .mypy_cache/
  ```

### Cuando Agregarás Nuevos Agentes

- [ ] Crear archivos .py en `src/agents/` (ej: `new_agent.py`)
- [ ] NO crear archivos .pyc manualmente
- [ ] NO crear scripts de testing dentro de src/agents/
  - 👉 Crear en `scripts/` en cambio
- [ ] Actualizar `src/agents/__init__.py` con nuevos imports
- [ ] Ejecutar: `python -c "from src.agents import ..."`

### Cuando Harás Cambios Mayores

- [ ] Ejecutar tests: `pytest tests/`
- [ ] Ejecutar type checking: `mypy src/agents/`
- [ ] Limpiar cachés: `Remove-Item -Recurse -Force src/agents/__pycache__`
- [ ] Verificar nuevamente

### Antes de Hacer Commit a Git

- [ ] Verificar: `git status | grep __pycache__`
  - Debe estar VACÍO (no debe aparecer __pycache__)
  - Si aparece, revisar .gitignore

- [ ] Verificar: `git status | grep .mypy_cache`
  - Debe estar VACÍO (no debe aparecer .mypy_cache/)
  - Si aparece, revisar .gitignore

- [ ] Si aparecen archivos .pyc:
  ```bash
  git rm --cached src/agents/__pycache__
  # Esto no borra los archivos, solo los remueve de git
  ```

---

## 🛠️ COMANDOS ÚTILES

### Limpiar __pycache__ en src/agents/
```bash
# Windows PowerShell
Remove-Item -Recurse -Force "src\agents\__pycache__"

# Linux/Mac
rm -rf src/agents/__pycache__
```

### Limpiar __pycache__ en TODO el proyecto
```bash
# Windows PowerShell
Get-ChildItem -Recurse -Directory -Name "__pycache__" | ForEach-Object {
    Remove-Item -Recurse -Force $_
}

# Linux/Mac
find . -type d -name __pycache__ -exec rm -rf {} +
```

### Limpiar .mypy_cache
```bash
# Windows PowerShell
Remove-Item -Recurse -Force ".mypy_cache"

# Linux/Mac
rm -rf .mypy_cache
```

### Verificar Imports
```bash
python -c "from src.agents import *; print('✅ OK')"
```

### Ejecutar Type Checking
```bash
mypy src/agents/
```

### Ver Tamaño de src/agents/
```bash
# Windows PowerShell
(Get-ChildItem -Recurse src/agents/ | Measure-Object -Property Length -Sum).Sum / 1MB

# Linux/Mac
du -sh src/agents/
```

---

## 🚫 QUÉ NO HACER

### ❌ No Crear Scripts de Testing en src/agents/
```python
# MALO - Crea archivos .pyc innecesarios en __pycache__/
# src/agents/test_my_agent.py
# src/agents/run_training.py
# src/agents/validate_agent.py
```

**Por qué**: Poluciona el __pycache__/ con archivos compilados que no necesitas

**Qué hacer en cambio**:
```bash
# ✅ BUENO - Crear scripts de testing en scripts/
scripts/test_my_agent.py
scripts/run_training.py
scripts/validate_agent.py
```

### ❌ No Commitar __pycache__/
```bash
# MALO
git add src/agents/__pycache__/*.pyc

# BUENO
# (No hagas nada, .gitignore lo previene automáticamente)
```

### ❌ No Editar .pyc Directamente
```python
# MALO - Los .pyc se regeneran automáticamente
# Editar src/agents/__pycache__/sac.cpython-311.pyc
```

**Qué hacer en cambio**:
- Edita `src/agents/sac.py`
- Python regenerará el .pyc automáticamente

### ❌ No Mantener Versiones Antiguas de Agentes
```bash
# MALO - Acumula basura
src/agents/
├─ sac.py           ✅
├─ sac_old.py       ❌ (deprecated)
├─ sac_backup.py    ❌ (backup)
└─ sac_v2.py        ❌ (unused)
```

**Qué hacer en cambio**:
- Usa Git para versioning
- Mantén solo un archivo `sac.py` activo
- Si necesitas versiones, créalas en branches de Git

---

## 📊 ESTRUCTURA RECOMENDADA

### Después de Limpieza (Ahora Mismo)
```
src/agents/
├─ __init__.py              ✅ Module exports
├─ a2c_sb3.py             ✅ Active agent
├─ ppo_sb3.py             ✅ Active agent
├─ rbc.py                 ⚠️ Baseline (optional)
├─ sac.py                 ✅ Active agent
├─ fixed_schedule.py      ✅ Helper
├─ metrics_extractor.py   ✅ Utilities
├─ no_control.py          ✅ Baseline
├─ transition_manager.py  ✅ Utilities
└─ [__pycache__/]         🔴 ELIMINADO (se regenera)

.gitignore debe contener:
├─ __pycache__/
├─ *.pyc
├─ .mypy_cache/
└─ .pytype/
```

### Con Nuevos Agentes (Futuro)
```
src/agents/
├─ __init__.py
├─ a2c_sb3.py
├─ new_agent_v1.py        ✅ Nuevo
├─ new_agent_v2.py        ✅ Nuevo
├─ ppo_sb3.py
├─ rbc.py
├─ sac.py
├─ [otros archivos]
└─ [__pycache__/]         🔴 NO COMMITEAR

scripts/                   ← Donde van los tests
├─ test_agents.py
├─ run_training.py
└─ validate_agents.py
```

---

## 🔐 CÓMO CONFIGURAR .gitignore

### Verificar que existe
```bash
cat .gitignore | grep __pycache__
```

### Si no está, agregarlo
```bash
# Agregar a .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".mypy_cache/" >> .gitignore
echo ".pytest_cache/" >> .gitignore
echo ".mypy/" >> .gitignore
```

### Contenido recomendado de .gitignore (Python)
```
# Bytecode
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Testing
.pytest_cache/
.coverage
htmlcov/

# Type checking
.mypy_cache/
.mypy/
.pytype/

# Jupyter
.ipynb_checkpoints/

# Virtual environments
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

## 🧪 TESTS DE VERIFICACIÓN

### Test 1: Imports Funcionan
```python
# Ejecutar cada vez que cambies src/agents/
from src.agents import (
    detect_device,
    make_sac, SACAgent,
    make_ppo, PPOAgent,
    make_a2c, A2CAgent,
    BasicRBCAgent
)
print("✅ All imports work")
```

### Test 2: Device Detection
```python
from src.agents import detect_device
device = detect_device()
print(f"✅ Device: {device}")
```

### Test 3: No Circular Imports
```python
# Si hay imports circulares, verás:
# ImportError: cannot import name 'X' from partially initialized module 'Y'

# Para prevenir:
# - No importes el módulo completo en __init__.py
# - Usa imports locales cuando sea necesario
```

### Test 4: __pycache__ Regenera
```bash
# Después de eliminar __pycache__
python -c "from src.agents import *"

# Verificar que se regeneró
ls src/agents/__pycache__/
# Debería mostrar *.pyc files
```

---

## 🎯 RESUMEN DE BUENAS PRÁCTICAS

| Práctica | Status | Explicación |
|----------|--------|-------------|
| **Mantener solo archivos activos en src/agents/** | ✅ HACER | Reduce clutter |
| **Crear scripts de test en scripts/ NO src/agents/** | ✅ HACER | Mantiene limpio |
| **Dejar que Python regenere __pycache__** | ✅ HACER | Se regenera auto |
| **Ignorar __pycache__ en .gitignore** | ✅ HACER | No commitear cachés |
| **Revisar imports regularmente** | ✅ HACER | Previene errores |
| **Usar versionamiento de Git para versiones viejas** | ✅ HACER | No guardar en disco |
| **Ejecutar mypy type checking** | ✅ HACER | Detecta bugs |
| **Limpiar __pycache__ regularmente** | ✅ HACER | Buena higiene |
| **Commitear archivos .pyc** | ❌ NO HACER | Son regenerables |
| **Mantener versiones viejas de agentes** | ❌ NO HACER | Usa Git en cambio |
| **Editar archivos .pyc directamente** | ❌ NO HACER | Edita .py |
| **Ignorar .gitignore** | ❌ NO HACER | Comitearás basura |

---

## 📞 REFERENCIA RÁPIDA

### Cuando el Proyecto Está Sucio
```bash
# Nuclear option - limpiar TODO
Get-ChildItem -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force ".mypy_cache"
Remove-Item -Recurse -Force ".pytest_cache"

# Verificar
python -c "from src.agents import *"
```

### Cuando Agregas Nuevo Agente
```bash
# 1. Crear archivo
# vim src/agents/my_new_agent.py

# 2. Actualizar imports
# edit src/agents/__init__.py
# Agregar: from .my_new_agent import MyAgent

# 3. Verificar
python -c "from src.agents import MyAgent; print(MyAgent)"
```

### Cuando Necesitas Limpiar Git Completamente
```bash
# Si ya commitiste __pycache__ accidentalmente
git rm -r --cached .
git add .
git commit -m "Remove cachés from git history"
```

---

## 🎊 CONCLUSIÓN

**Mantener limpio es fácil si sigues 3 reglas**:

1. ✅ **Dejar que Python maneje los cachés** (se regeneran solos)
2. ✅ **Ignorar __pycache__ en .gitignore** (no commitear)
3. ✅ **Mantener solo archivos activos** (eliminar viejos mediante Git)

**Si lo haces bien**:
- 🚀 Proyecto siempre limpio
- 📉 Menos basura en disco
- ✨ Mejor rendimiento
- 🔒 Sin errores de import

---

*Guía de mantenimiento creada: 2026-02-04*  
*Status: LISTO PARA USO*
