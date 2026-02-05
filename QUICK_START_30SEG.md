# ⚡ QUICK START - DIMENSIONAMIENTO EN 30 SEGUNDOS

## 🚀 Ejecución Rápida

### Opción 1: Ver Escenarios (5 segundos)
```bash
python scripts/main_dimensionamiento.py --lista
```
**Salida**: Lista de 4 escenarios (CONSERVADOR, MEDIANO, RECOMENDADO, MÁXIMO)

### Opción 2: Análisis Completo (10 segundos)
```bash
python scripts/main_dimensionamiento.py --todos
```
**Salida**: 
- Tabla de 4 escenarios en consola
- Archivo `outputs/dimensionamiento/escenarios_dimensionamiento.csv`
- Archivo `outputs/dimensionamiento/escenarios_dimensionamiento.json`

### Opción 3: Escenario Específico (5 segundos)
```bash
python scripts/main_dimensionamiento.py --escenario RECOMENDADO
```
**Salida**: Datos detallados del escenario RECOMENDADO

### Opción 4: Menú Interactivo (Windows)
```powershell
.\scripts\run_dimensionamiento.ps1
```

### Opción 5: Menú Interactivo (Linux/Mac)
```bash
./scripts/run_dimensionamiento.sh
```

---

## 📊 Resultado: Escenario RECOMENDADO

| Métrica | Valor |
|---------|-------|
| **Cargadores** | 33 unidades |
| **Tomas** | 132 sockets |
| **Vehículos/día** | 927 (810 motos + 117 mototaxis) |
| **Energía/día** | 3,252 kWh |
| **CO₂ Evitado/año** | 2,723,446 kg |

---

## 📂 Archivos Generados

```
outputs/dimensionamiento/
├── escenarios_dimensionamiento.csv   ← Abrir en Excel
└── escenarios_dimensionamiento.json  ← Usar en análisis
```

---

## ✅ Validación

```bash
# Verificar que existe el CSV
cat outputs/dimensionamiento/escenarios_dimensionamiento.csv

# Verificar que existe el JSON  
cat outputs/dimensionamiento/escenarios_dimensionamiento.json

# Contar filas
wc -l outputs/dimensionamiento/escenarios_dimensionamiento.csv
# Debe ser: 5 (header + 4 escenarios)
```

---

## 🎯 Próximos Pasos

1. **Importar a Excel**: Abre `escenarios_dimensionamiento.csv`
2. **Usar en OE3**: Entrada para simulación de agentes
3. **Personalizar**: Edita `DEFAULT_CONFIG` en `main_dimensionamiento.py`
4. **Leer Docs**: Ve a `DIMENSIONAMIENTO_QUICK_START.md` para más detalles

---

## 🐍 Python Requerido

- Python 3.11+ (verificar: `python --version`)
- Módulos: Ya instalados en `requirements.txt`

---

## 🆘 Problemas?

1. **ImportError**: `pip install -r requirements.txt`
2. **UnicodeError**: Asegúrate de usar Python 3.11+
3. **FileNotFoundError**: Corre el comando desde la raíz del proyecto
4. **Permission Denied**: En Linux/Mac, ejecuta: `chmod +x scripts/run_dimensionamiento.sh`

---

## 📌 Resumen de 4 Escenarios

```
┌──────────────┬──────┬────────┬──────────┬────────┐
│ Escenario    │ PE % │ FC %   │Cargadores│CO₂/año │
├──────────────┼──────┼────────┼──────────┼────────┤
│CONSERVADOR   │ 10%  │ 80%    │    4     │155 K kg│
│MEDIANO       │ 55%  │ 60%    │   20     │641 K kg│
│RECOMENDADO   │ 90%  │ 90%    │   33     │2.7M kg │
│MÁXIMO        │100%  │100%    │   35     │3.4M kg │
└──────────────┴──────┴────────┴──────────┴────────┘
```

PE = Penetración | FC = Factor de Carga | CO₂ = CO₂ Total Evitado/año

---

**¡Listo! Tu sistema de dimensionamiento está operacional.** 🎉
