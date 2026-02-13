# 🚀 Sistema de Dimensionamiento de Cargadores - Documentación

## 📋 Archivos de Documentación

### 1. **[RESUMEN_MAIN_DIMENSIONAMIENTO.md](RESUMEN_MAIN_DIMENSIONAMIENTO.md)** 
   - **Propósito:** Resumen ejecutivo de trabajo realizado
   - **Contenido:** Descripción de scripts creados, problemas resueltos, resultados de pruebas
   - **Para quién:** Gerentes, revisores, cualquiera que quiera ver qué se hizo
   - **Tiempo de lectura:** 5-10 minutos

### 2. **[DIMENSIONAMIENTO_QUICK_START.md](DIMENSIONAMIENTO_QUICK_START.md)**
   - **Propósito:** Guía de uso rápido del sistema
   - **Contenido:** Cómo ejecutar, qué datos genera, interpretación de resultados
   - **Para quién:** Usuarios finales que necesitan calcular dimensionamiento
   - **Tiempo de lectura:** 10-15 minutos

---

## 🎯 Flujo de Lectura Recomendado

### Si quieres entender qué se hizo:
1. Lee este archivo (índice)
2. Lee [RESUMEN_MAIN_DIMENSIONAMIENTO.md](RESUMEN_MAIN_DIMENSIONAMIENTO.md)
3. Ejecuta: `python scripts/main_dimensionamiento.py --lista`

### Si quieres usar el sistema:
1. Lee [DIMENSIONAMIENTO_QUICK_START.md](DIMENSIONAMIENTO_QUICK_START.md)
2. Ejecuta: `python scripts/main_dimensionamiento.py --todos`
3. Abre el archivo JSON generado: `outputs/dimensionamiento/escenarios_dimensionamiento.json`

### Si necesitas resolver problemas:
1. Busca en la sección "Troubleshooting" de [DIMENSIONAMIENTO_QUICK_START.md](DIMENSIONAMIENTO_QUICK_START.md)
2. Revisa "Problemas Resueltos" en [RESUMEN_MAIN_DIMENSIONAMIENTO.md](RESUMEN_MAIN_DIMENSIONAMIENTO.md)

---

## 📦 Archivos del Sistema

### Scripts Ejecutables

```
scripts/
├── main_dimensionamiento.py        (347 líneas) - Script principal CLI
├── run_dimensionamiento.ps1        (150+ líneas) - Menú Windows  
└── run_dimensionamiento.sh         (60+ líneas) - Menú Linux/Mac
```

### Salida Generada

```
outputs/dimensionamiento/
├── escenarios_dimensionamiento.json  - Datos estructurados (JSON)
└── escenarios_dimensionamiento.csv   - Tabla Excel-compatible
```

---

## 🚀 Formas de Ejecutar

### Opción 1: Línea de Comando (Recomendado para Automatización)

```bash
# Ver todos los escenarios disponibles
python scripts/main_dimensionamiento.py --lista

# Calcular un escenario específico
python scripts/main_dimensionamiento.py --escenario RECOMENDADO

# Calcular todos los escenarios
python scripts/main_dimensionamiento.py --todos
```

### Opción 2: Menú Interactivo Windows

```powershell
.\scripts\run_dimensionamiento.ps1
# Selecciona opción 1-6 del menú
```

### Opción 3: Menú Interactivo Linux/Mac

```bash
./scripts/run_dimensionamiento.sh
# Selecciona opción 1-6 del menú
```

---

## 📊 Resultados Esperados

### Escenarios Disponibles

| Nombre | PE | FC | Cargadores | Tomas | CO₂ Evitado/año |
|--------|----|----|-----------|-------|-----------------|
| CONSERVADOR | 10% | 80% | 4 | 16 | 155K kg |
| MEDIANO | 55% | 60% | 20 | 80 | 641K kg |
| **RECOMENDADO** | **90%** | **90%** | **33** | **132** | **2,723K kg** |
| MÁXIMO | 100% | 100% | 35 | 140 | 3,361K kg |

**PE** = Penetración (% flota que carga)  
**FC** = Factor Carga (% energía utilizada)  
**CO₂ Evitado** = Vs gasolina + grid térmico Iquitos

---

## ✅ Sistema Validado

- ✅ CLI con 3 modos (--todos, --escenario, --lista)
- ✅ Menús interactivos para Windows, Linux, Mac
- ✅ Generación automática JSON/CSV
- ✅ Integración con funciones base de chargers.py
- ✅ Validación contra Tabla 13 OE2
- ✅ Cálculo de CO₂ (directo + indirecto)

**Estado:** 🟢 **PRODUCCIÓN LISTA**

---

## 📚 Documentación Relacionada

- [QUICKSTART.md](QUICKSTART.md) - Inicio rápido general del proyecto
- [docs/BASELINE_COMPARISON_GUIDE.md](docs/BASELINE_COMPARISON_GUIDE.md) - Baselines CO₂
- [src/iquitos_citylearn/oe2/chargers.py](src/iquitos_citylearn/oe2/chargers.py) - Funciones base

---

**Última actualización:** 2026-02-04  
**Estado de Verificación:** ✅ OPERACIONAL
