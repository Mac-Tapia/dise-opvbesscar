# ⚡ Quick Start: Cómo Ejecutar PVBESSCAR

Este es el punto de entrada más simple para ejecutar el sistema de optimización de carga EV.

## 🚀 Inicio Rápido (3 Pasos)

### 1️⃣ Ver Demo (5 segundos)
```bash
python demo_ejecucion.py
```
Muestra toda la información del sistema sin necesidad de entrenar.

### 2️⃣ Validar Sistema (10 segundos)
```bash
python ejecutar.py --validate
```
Verifica que todo esté listo para entrenar:
- ✅ Python 3.11/3.12
- ✅ Dependencias instaladas
- ✅ Datasets disponibles
- ✅ GPU detectada (opcional)

### 3️⃣ Entrenar A2C (2 horas)
```bash
python ejecutar.py --agent a2c
```
Entrena el agente A2C (RECOMENDADO: 64.3% reducción CO₂).

---

## 📖 Comandos Disponibles

```bash
# Ver ayuda completa
python ejecutar.py --help

# Solo validar (sin entrenar)
python ejecutar.py --validate

# Entrenar A2C (RECOMENDADO)
python ejecutar.py --agent a2c

# Entrenar PPO (alternativa)
python ejecutar.py --agent ppo

# Entrenar SAC (alternativa)
python ejecutar.py --agent sac

# Ver demo informativo
python demo_ejecucion.py
```

---

## 🎯 ¿Qué Agente Elegir?

| Agente | CO₂ Reducción | Tiempo | Recomendación |
|--------|---------------|--------|---------------|
| **A2C** | **64.3%** | **2h** | ⭐ **USAR ESTE** |
| PPO | 47.5% | 2.5h | Solo si A2C falla |
| SAC | 43.3% | 10h | Solo para investigación |

**Recomendación clara:** Usar **A2C** para producción.

---

## 📊 Resultados Esperados

Después de entrenar A2C, obtendrás:

### Archivos Generados
```
checkpoints/A2C/latest.zip           # Modelo entrenado
outputs/a2c_training/                # Métricas y logs
entrenamiento_a2c.log                # Log completo
```

### Métricas Clave
- **CO₂ Reducción:** 64.3% (vs baseline)
- **Solar Autoconsumo:** 51.7%
- **Cost Savings:** $1.73M USD/año
- **Grid Import Reducción:** 45%

---

## ❓ Problemas Comunes

### Error: Dependencias no instaladas
```bash
pip install -r requirements.txt
pip install -r requirements-training.txt  # Para GPU
```

### Error: GPU no disponible
El entrenamiento funcionará con CPU, solo será más lento (6-8h vs 2h).

### Error: Datasets no encontrados
Verifica que los archivos estén en `data/interim/oe2/`.

---

## 📚 Documentación Completa

- **GUIA_EJECUCION.md** - Guía detallada paso a paso
- **README.md** - Descripción general del proyecto
- **IMPLEMENTACION_COMPLETADA.md** - Resumen de implementación

---

## 🆘 Soporte

1. **Revisar esta guía**
2. **Consultar GUIA_EJECUCION.md**
3. **Abrir issue en GitHub** con logs completos

---

**¿Primera vez?** → Comienza con: `python demo_ejecucion.py`

**¿Ya validaste?** → Ejecuta: `python ejecutar.py --agent a2c`

**¿Necesitas ayuda?** → Ver: `GUIA_EJECUCION.md`
