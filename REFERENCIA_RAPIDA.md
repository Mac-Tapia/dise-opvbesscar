# 🎯 REFERENCIA RÁPIDA - ENTRENAMIENTO SERIAL

## ✅ Estado: LISTO

```
✓ Python 3.13.9
✓ Datos OE2: Solar + BESS + Chargers
✓ Dataset OE3: 157 archivos
✓ Config validada
✓ LISTO PARA LANZAR
```

---

## 🚀 LANZAR EN 10 SEGUNDOS

### PowerShell (MEJOR)

```powershell
.\launch_training.ps1
```

### Command Prompt

```cmd
launch_training.bat
```

### Python

```bash
python train_agents_serial_auto.py
```

---

## 📈 Qué Sucederá

```
SAC  (1-2h) → PPO (2-2.5h) → A2C (1-2h)
Total: 4-7 horas
```

---

## 📊 Resultados

```
outputs/oe3/simulations/
├── simulation_summary.json     ← Resultados principales
├── co2_comparison.md           ← Tabla CO₂
├── timeseries_SAC.csv          ← Serie temporal SAC
├── timeseries_PPO.csv          ← Serie temporal PPO
└── timeseries_A2C.csv          ← Serie temporal A2C
```

---

## 🔧 Si se Interrumpe

Simplemente volver a ejecutar:

```bash
python train_agents_serial_auto.py
```

Detecta checkpoints previos y reanuda.

---

## 📚 Documentación Completa

- [RESUMEN_ENTRENAMIENTO_SERIAL.md](RESUMEN_ENTRENAMIENTO_SERIAL.md) - Guía principal
- [VERIFICACION_ENTRENAMIENTO_LISTO.md](VERIFICACION_ENTRENAMIENTO_LISTO.md) - Detalles
- [GUIA_LANZAMIENTO_SERIAL_GPU.md](GUIA_LANZAMIENTO_SERIAL_GPU.md) - Referencia completa

---

**Siguiente paso:** Ejecutar comando de lanzamiento ✨
