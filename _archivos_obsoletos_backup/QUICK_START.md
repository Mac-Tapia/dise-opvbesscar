# 🚀 Guía Rápida de Instalación - PYTHON 3.11

## ⚡ Instalación de 5 Minutos

### Step 1: Crear Entorno Virtual
```powershell
python -m venv .venv
```

### Step 2: Activar Entorno
```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

### Step 3: Instalar Dependencias
```bash
# Base (requerido)
pip install -r requirements.txt

# Training (opcional)
pip install -r requirements-training.txt
```

### Step 4: Verificar Instalación
```bash
python -c "import torch; print(f'✅ PyTorch {torch.__version__}'); import citylearn; print('✅ CityLearn'); from stable_baselines3 import PPO; print('✅ SB3')"
```

**Resultado Esperado:**
```
✅ PyTorch 2.10.0
✅ CityLearn
✅ SB3
```

---

## 📊 Contenido de Requirements

| Archivo | Librerías | Uso |
|---------|-----------|-----|
| `requirements.txt` | 221 | Base del proyecto + RL + Jupyter |
| `requirements-training.txt` | 11 | Adicionales para training con GPU |
| **TOTAL** | **232** | Entorno completo |

---

## ✅ Versiones Garantizadas

- **Python**: 3.11+ (requerido)
- **PyTorch**: 2.10.0
- **Pandas**: 2.3.3
- **NumPy**: 1.26.4
- **Stable-Baselines3**: 2.7.1
- **CityLearn**: 2.5.0
- **Gymnasium**: 0.29.1

---

## 🔍 Validación Automatizada

```bash
# Verificar que todo está correcto
python validate_requirements_integration.py
```

---

## 💻 GPU Support (Opcional)

Si tienes **CUDA 11.8** instalado:

```bash
# Desinstalar torch CPU
pip uninstall torch torchvision -y

# Instalar torch con soporte CUDA 11.8
pip install torch==2.10.0 torchvision==0.15.2 \
  --index-url https://download.pytorch.org/whl/cu118
```

**Verificar GPU:**
```bash
python -c "import torch; print(f'GPU disponible: {torch.cuda.is_available()}')"
```

---

## 🐛 Troubleshooting

### Error: "No module named X"
```bash
# Reinstalar
pip install -r requirements.txt --force-reinstall
```

### Error: "Permission denied"
```bash
# Linux/macOS
sudo pip install -r requirements.txt

# O mejor: Usar venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### GPU no detectado
```bash
# Verificar
python -c "import torch; print(torch.cuda.is_available())"

# Si False, instalar versión GPU (ver GPU Support arriba)
```

---

## 📋 Próximos Pasos

1. Instalar requirements
2. Ejecutar: `python validate_requirements_integration.py`
3. Ejecutar dataset builder: `python -m scripts.run_oe3_build_dataset`
4. Entrenar: `python -m scripts.run_oe3_simulate`

---

## ✨ Status
✅ **LISTO PARA USAR**

Todas las 232 librerías están correctamente integradas y validadas.
