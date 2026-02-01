# Testing - Scripts Esenciales para OE3

## 📊 Propósito

Carpeta de **utilidades de testing y monitoreo** para validar el entrenamiento de agentes RL en OE3.

## ✅ Scripts Esenciales (3)

### 1. `generador_datos_aleatorios.py`
**Propósito:** Generar datos aleatorios para testing/debug de OE3
- Crea conjuntos de datos sintéticos para verificación rápida
- Útil para testing sin ejecutar pipeline completo
- **Uso:** `python generador_datos_aleatorios.py`

### 2. `gpu_usage_report.py`
**Propósito:** Monitoreo de uso de GPU durante entrenamiento
- Reporta utilización de memoria GPU en tiempo real
- Valida que los agentes usen GPU correctamente
- **Uso:** `python gpu_usage_report.py --agent sac` (durante entrenamiento)

### 3. `MAXIMA_GPU_REPORT.py`
**Propósito:** Reporte detallado de máximo uso de GPU
- Genera estadísticas completas de GPU (VRAM, compute, temperatura)
- Ayuda a identificar bottlenecks de recursos
- **Uso:** `python MAXIMA_GPU_REPORT.py`

## 📁 Estructura

```
scripts/testing/
├── README.md (este archivo)
├── generador_datos_aleatorios.py ✅
├── gpu_usage_report.py ✅
├── MAXIMA_GPU_REPORT.py ✅
└── archive/
    ├── VERIFICACION_*.py (18 archivos - OE2 ya completado)
    ├── TEST_PERFIL_15MIN.py
    ├── test_*.py
    └── verificar_*.py
```

## 🚀 Flujo de Uso

### Durante Desarrollo
```bash
# Verificar que GPU está disponible
python MAXIMA_GPU_REPORT.py

# Generar datos de test rápidamente
python generador_datos_aleatorios.py
```

### Durante Entrenamiento
```bash
# Monitorear GPU en tiempo real
python gpu_usage_report.py --agent sac
```

## 📝 Notas

- **Archivos OE2:** Todos los scripts de verificación de OE2 fueron archivados en `archive/` porque OE2 ya está completado y validado
- **Testing Data:** Usar `generador_datos_aleatorios.py` para verificación rápida sin correr pipeline completo
- **GPU Monitoring:** Los reportes GPU son útiles para optimizar parámetros de entrenamiento

## ✅ Estado

- Limpieza: ✅ Completada (18 archivos archivados, 3 esenciales mantenidos)
- Documentación: ✅ Actualizada
- Listo para producción: ✅ Sí
