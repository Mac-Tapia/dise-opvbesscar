# 🚀 GUÍA RÁPIDA - INSTALACIÓN COMPLETADA

**Fecha**: 2026-02-04  
**Estado**: ✅ **COMPLETADO Y VERIFICADO**

---

## 📋 TABLA DE CONTENIDOS

1. [✅ Instalación Completada](#instalación-completada)
2. [📚 Documentación Generada](#documentación-generada)
3. [🛠️ Scripts de Utilidad](#scripts-de-utilidad)
4. [🚀 Próximos Pasos](#próximos-pasos)
5. [⚡ Comandos Rápidos](#comandos-rápidos)
6. [❓ FAQ](#faq)

---

## ✅ Instalación Completada

### Resumen
Se han instalado **36+ paquetes** en un entorno Python 3.11 aislado.

### Versiones Clave
- **Python**: 3.11.9
- **PyTorch**: 2.10.0 (CPU mode)
- **Stable Baselines 3**: 2.7.1
- **CityLearn**: 2.5.0
- **Gymnasium**: 0.28.1

### Estado Actual
```
✅ Todos los paquetes instalados correctamente
✅ Verificación completada
✅ Listo para entrenamientos RL
```

---

## 📚 Documentación Generada

| Archivo | Descripción | Ubicación |
|---------|------------|-----------|
| **INSTALLATION_COMPLETED.md** | Resumen completo de instalación | `/` |
| **INSTALLATION_SUMMARY.md** | Resumen detallado con pasos | `/` |
| **INSTALLATION_QUICK_START.md** | Esta guía rápida | `/` |
| **installation_log.txt** | Log detallado de instalación | `/` |
| **installation_verification.txt** | Resultados de verificación | `/` |
| **installed_packages.txt** | Lista de paquetes instalados | `/` |

---

## 🛠️ Scripts de Utilidad

### 1. Instalación (Ya Ejecutado)
```powershell
.\install_requirements.bat
```
**Instala**: Todos los paquetes de forma individual y visible

### 2. Ajuste de Dependencias (Ya Ejecutado)
```powershell
.\install_citylearn_deps.bat
```
**Ajusta**: Gymnasium a v0.28.1 (requerido por CityLearn)

### 3. Verificación (Recomendado Ejecutar)
```powershell
python verify_installation.py
```
**Verifica**: Que todos los paquetes estén correctamente instalados

### 4. Información del Entorno (Recomendado Ejecutar)
```powershell
python environment_info.py
```
**Muestra**: Información detallada del entorno y configuración

---

## 🚀 Próximos Pasos

### Paso 1: Verificar Instalación (RECOMENDADO)
```powershell
python verify_installation.py
```

**Salida esperada**:
```
✅ TODAS LAS DEPENDENCIAS INSTALADAS CORRECTAMENTE

El entorno está listo para:
  • Entrenamiento de agentes RL (SAC, PPO, A2C)
  • Simulación de CityLearn v2.5.0
  • Análisis de datos con pandas/numpy
  • Visualización con matplotlib
```

### Paso 2: Ver Información (OPCIONAL)
```powershell
python environment_info.py
```

### Paso 3: Entrenar Agente SAC
```powershell
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac
```

### Paso 4: Entrenar Agente PPO
```powershell
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent ppo
```

### Paso 5: Entrenar Agente A2C
```powershell
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent a2c
```

---

## ⚡ Comandos Rápidos

### Verificaciones Simples
```powershell
# Ver versión de Python
python --version

# Ver versión de PyTorch
python -c "import torch; print(torch.__version__)"

# Ver versión de Stable Baselines 3
python -c "import stable_baselines3; print(stable_baselines3.__version__)"

# Ver versión de CityLearn
python -c "import citylearn; print(citylearn.__version__)"

# Ver versión de Gymnasium
python -c "import gymnasium; print(gymnasium.__version__)"
```

### Listar Paquetes Instalados
```powershell
pip list
pip list > installed_packages.txt  # Guardar en archivo
```

### Actualizar un Paquete
```powershell
pip install --upgrade <package_name>
```

### Desinstalar un Paquete
```powershell
pip uninstall <package_name>
```

---

## ❓ FAQ

### P: ¿Por qué Python 3.11?
**R**: El proyecto está desarrollado específicamente para Python 3.11. No es compatible con 3.12+.

### P: ¿Puedo usar Python 3.12 o 3.13?
**R**: No. Causará problemas de compatibilidad. Usa Python 3.11.x obligatoriamente.

### P: ¿Por qué PyTorch está en modo CPU?
**R**: La instalación usa PyTorch CPU. Para GPU NVIDIA, ejecutar:
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### P: ¿Qué es Gymnasium 0.28.1?
**R**: Es el framework de entornos RL. Gymnasium 0.28.1 es específicamente requerido por CityLearn v2.5.0. No usar versiones más nuevas.

### P: ¿Qué pasa si tengo conflictos de dependencias?
**R**: Ejecutar:
```powershell
pip install gymnasium==0.28.1 --force-reinstall
```

### P: ¿Cuánto tiempo tarda el entrenamiento?
**R**: Depende del agente y hardware:
- **SAC**: 5-10 horas (GPU), 24+ horas (CPU)
- **PPO**: 4-6 horas (GPU), 20+ horas (CPU)
- **A2C**: 3-4 horas (GPU), 15+ horas (CPU)

### P: ¿Dónde se guardan los checkpoints?
**R**: En `/checkpoints/{SAC|PPO|A2C}/` por defecto. Configurar en `config.yaml`.

### P: ¿Cómo reinstalar todo desde cero?
**R**:
```powershell
deactivate
rmdir .venv /s /q
python -m venv .venv
.venv\Scripts\activate
.\install_requirements.bat
.\install_citylearn_deps.bat
python verify_installation.py
```

---

## 📞 Troubleshooting

### Error: "ModuleNotFoundError"
```powershell
# Solución:
python verify_installation.py
pip install <module_name>
```

### Error: "gymnasium==0.28.1 but you have gymnasium 0.29.1"
```powershell
# Solución:
pip install gymnasium==0.28.1 --force-reinstall
```

### Error: "CUDA not available"
```powershell
# Es NORMAL en modo CPU. Para activar CUDA:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Error: "citylearn not found"
```powershell
# Solución:
pip install citylearn==2.5.0
```

---

## 📊 Versiones Compatibles (Verificadas)

| Paquete | Versión | Compatible |
|---------|---------|------------|
| Python | 3.11.9 | ✅ REQUERIDO |
| PyTorch | 2.10.0 | ✅ |
| Gymnasium | 0.28.1 | ✅ OBLIGATORIO |
| CityLearn | 2.5.0 | ✅ |
| Stable Baselines 3 | 2.7.1 | ✅ |
| NumPy | 1.26.4 | ✅ |
| Pandas | 2.3.3 | ✅ |
| Matplotlib | 3.10.8 | ✅ |
| pvlib | 0.10.4 | ✅ |

---

## 🎯 Estado Final

```
╔════════════════════════════════════════════╗
║  ✅ ENTORNO 100% FUNCIONAL                ║
╠════════════════════════════════════════════╣
║  Paquetes: 36+                             ║
║  Tamaño: ~5-6 GB                          ║
║  Python: 3.11.9                           ║
║  Modo RL: SAC, PPO, A2C                   ║
║  Simulación: CityLearn v2.5.0             ║
║  Análisis: Pandas + NumPy                 ║
╠════════════════════════════════════════════╣
║  🚀 LISTO PARA ENTRENAMIENTOS             ║
╚════════════════════════════════════════════╝
```

---

## 📞 Próximos Pasos Recomendados

1. ✅ **Ejecutar verificación**:
   ```powershell
   python verify_installation.py
   ```

2. ✅ **Ver información del entorno**:
   ```powershell
   python environment_info.py
   ```

3. ✅ **Iniciar primer entrenamiento**:
   ```powershell
   python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac
   ```

4. 📚 **Leer documentación**:
   - `INSTALLATION_COMPLETED.md`
   - `INSTALLATION_SUMMARY.md`
   - `TRAINING_GUIDE.md`

---

**¡Felicidades!** 🎉  
Tu entorno está completamente configurado y listo para entrenamientos de agentes RL.

**Fecha**: 2026-02-04  
**Versión**: 1.0  
**Estado**: ✅ COMPLETADO
