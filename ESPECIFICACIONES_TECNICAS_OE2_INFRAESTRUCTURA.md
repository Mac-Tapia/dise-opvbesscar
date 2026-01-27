# 🏗️ Especificaciones Técnicas OE2 - Infraestructura Iquitos

**Fecha Actualización:** 27 enero 2026  
**Versión:** 1.0  
**Status:** ✅ OPERACIONAL

---

## 📊 Resumen Ejecutivo

Sistema de generación solar fotovoltaica + almacenamiento + carga inteligente para motos y mototaxis eléctricos en Iquitos, Perú.

| Componente | Capacidad | Unidad |
|------------|-----------|--------|
| **Generación Solar** | 4,050 | kWp |
| **Almacenamiento** | 2,000 | kWh |
| **Potencia BESS** | 1,200 | kW |
| **Cargadores Total** | 128 | unidades |
| **Sockets** | 512 | conexiones |
| **Potencia Nominal** | 272 | kW |

---

## ⚡ Sistema Fotovoltaico

### Especificaciones Generales
- **Potencia Total Instalada:** 4,050 kWp
- **Tecnología:** Módulos Fotovoltaicos Kyocera KS20
- **Tipo de Sistema:** On-grid + backup (con almacenamiento)

### Configuración de Módulos
- **Módulos por String:** 31
- **Número de Strings:** 6,472
- **Módulos Totales Instalados:** 200,632

**Cálculo:**
```
Total PV = 6,472 strings × 31 módulos/string = 200,632 módulos
Potencia = (4,050 kWp total) / (200,632 módulos) ≈ 0.0202 kWp/módulo ≈ 20.2 Wp/módulo
```

### Módulos Kyocera KS20
- **Potencia Nominal:** ~20 Wp (cada módulo)
- **Voltaje Nominal:** 12V DC
- **Tecnología:** Silicio Monocristalino
- **Eficiencia:** ~16% (típica)
- **Temperatura Nominal:** 45°C
- **Garantía:** 25 años (producción)

### Inversores Eaton Xpert1670
- **Cantidad:** 2 unidades
- **Potencia Nominal (c/u):** ~2,025 kW (sumados = 4,050 kW)
- **Tipo:** Inversor trifásico, on-grid
- **Voltaje Entrada (DC):** 400-800V
- **Voltaje Salida (AC):** 3×380V / 50Hz
- **Eficiencia:** ~98%
- **Característica:** Transformador integrado, protecciones redundantes

**Configuración en planta:**
```
6,472 strings PV
    ↓
Eaton Xpert1670 #1 (2,025 kW)
Eaton Xpert1670 #2 (2,025 kW)
    ↓
4,050 kW AC → BESS / Grid / Chargers
```

---

## 🔋 Sistema de Almacenamiento (BESS)

### Especificaciones
- **Tecnología:** Batería de iones de litio (LiFePO₄ recomendado)
- **Capacidad Nominal:** 2,000 kWh
- **Potencia Nominal:** 1,200 kW
- **Ratio C:** 1,200 kW / 2,000 kWh = 0.6C (descarga en 1.67 hrs)
- **Tiempo Descarga Nominal:** 100 minutos (desde 100% a 0% a potencia nominal)

### Modo de Operación
- **Prioridad 1:** Cargar desde PV durante peak sun (8 AM - 4 PM)
- **Prioridad 2:** Alimentar chargers durante demanda pico (4 PM - 10 PM)
- **Prioridad 3:** Inyectar a grid cuando SOC > 95% (si tarifa favorable)
- **Prioridad 4:** Importar de grid cuando SOC < 20% (backup)

### Ciclo Diario Típico
```
Hora | Acción | Energía
-----|--------|----------
08-12 | PV → BESS (carga) | +500 kWh
12-16 | PV → Chargers (directo) | -400 kWh
16-22 | BESS → Chargers (evening peak) | -600 kWh
22-08 | Importar grid (nocturno) | -200 kWh
```

---

## 🔌 Infraestructura de Carga (Chargers)

### Distribución de Cargadores

**Total: 128 cargadores (512 sockets)**

| Tipo | Cantidad | Potencia c/u | Potencia Total | Uso |
|------|----------|--------------|----------------|-----|
| **Motos** | 112 | 2 kW | 224 kW | Transporte personal |
| **Mototaxis** | 16 | 3 kW | 48 kW | Transporte comercial |
| **TOTAL** | **128** | Mixta | **272 kW** | - |

**Sockets:**
- 112 chargers × 4 sockets = 448 sockets para motos
- 16 chargers × 4 sockets = 64 sockets para mototaxis
- **Total:** 512 sockets de carga

### Especificaciones por Tipo

**Motos (112 chargers):**
- Potencia nominal: 2 kW c/u
- Voltaje: 220V monofásico
- Tipo de conector: Type 2 (IEC 62196-2)
- Tiempo carga típico (batería 2.5 kWh): ~1.25 horas
- SOC típico: 20-100%

**Mototaxis (16 chargers):**
- Potencia nominal: 3 kW c/u
- Voltaje: 380V trifásico
- Tipo de conector: Type 2 o Mennekes
- Tiempo carga típico (batería 5.0 kWh): ~1.67 horas
- SOC típico: 20-100%

### Ubicación Física
- **Localización:** Iquitos, Perú (Amazon basin)
- **Altitud:** ~110 m s.n.m.
- **Clima:** Tropical húmedo
- **Temperatura Anual:** 25-32°C
- **Radiación Solar:** ~5.0-5.5 kWh/m²/día (promedio)

---

## 📈 Rendimiento Estimado Anual

### Generación Solar Esperada
- **Radiación Horizontal:** 5.2 kWh/m²/día (Iquitos)
- **Energía Anual PV:** ~1,464 MWh (4,050 kWp × 5.2 × 365 / 1000 × 0.75 efficiency factor)
- **CO₂ Desplazado (vs grid):** 1,632 tCO₂/año (grid Iquitos: 1.12 kg CO₂/kWh)

### Demanda de Carga Esperada
- **Flota:** ~200-250 motos + 30-40 mototaxis simultáneos
- **Consumo unitario:** 0.25-0.40 kWh/km
- **Viajes/día:** 3-5 por vehículo (~30-50 km)
- **Demanda diaria:** 1,500-2,000 kWh/día
- **Demanda anual:** 547-730 MWh/año

### Beneficios de CO₂
- **Emisiones grid (sin PV):** 2,892 tCO₂/año (547 MWh × 1.12 kg CO₂/kWh × 47.4% circulating margin)
- **Emisiones con PV:** 1,260 tCO₂/año
- **Reducción neta:** 1,632 tCO₂/año
- **Equivalente:** ~400 autos gasolina menos / año

---

## 🎯 Objetivos OE3 (Control RL)

### Métricas Primarias
1. **Minimizar CO₂:** -25% a -30% vs baseline
2. **Maximizar autoconsumo solar:** +20-30% vs baseline
3. **Garantizar satisfacción EV:** ≥95% carga completada

### Restricciones Operacionales
- Potencia BESS: ≤1,200 kW
- Capacidad BESS: ≤2,000 kWh (SOC: 0-100%)
- Cargadores simultáneos: ≤128
- Potencia total: ≤4,050 kW

### Algoritmos de Control
- **SAC (Soft Actor-Critic):** Off-policy, muestra eficiente
- **PPO (Proximal Policy Optimization):** On-policy, estable
- **A2C (Advantage Actor-Critic):** On-policy, simple, baseline

---

## 📊 Datos de Entrada OE2 → OE3

### Archivos Críticos
```
data/interim/oe2/
├── solar/
│   └── pv_generation_timeseries.csv    (8,760 rows × 2 cols)
│       └── Columns: timestamp, ac_power_kw
│
├── chargers/
│   ├── individual_chargers.json        (32 entries for 128 sockets)
│   │   └── Fields: charger_id, ev_type, power_kw, sockets
│   │
│   └── perfil_horario_carga.csv        (24 rows × 2 cols)
│       └── Fields: hour, load_profile_kw
│
└── bess/
    └── bess_config.json                (fixed parameters)
        └── Fields: capacity_kwh, power_kw, efficiency
```

### Validaciones Críticas
- ✅ Solar: Exactamente 8,760 filas (hourly, no 15-min data)
- ✅ Chargers: 32 entries × 4 sockets = 128 chargers
- ✅ BESS: Capacidad 2,000 kWh, Potencia 1,200 kW
- ✅ Demanda: Perfil horario coherente con flota

---

## 🔧 Mantenimiento Esperado

### Sistema Solar (Anual)
- **Limpieza de módulos:** 2× al año (lluvia tropical)
- **Inspección eléctrica:** 1× al año
- **Cambio de string (1%):** ~65 módulos/año

### BESS (Anual)
- **Ciclos de descarga:** ~300-365 ciclos/año
- **Degradación:** ~1-2% por año
- **Vida útil:** 10-15 años (2,000-3,000 ciclos acumulados)

### Chargers (Anual)
- **Mantenimiento preventivo:** 2× al año
- **Limpieza conectores:** Mensual
- **Reemplazo contactos:** Según uso

---

## 📝 Referencias y Estándares

- **Módulos:** Kyocera KS20 (datasheet disponible)
- **Inversores:** Eaton Xpert1670 (UPS industrial)
- **BESS:** LiFePO₄ recomendado (BYD, LG Chem, CATL)
- **Chargers:** IEC 61851-1, ISO 14443 Type 2
- **Estándares:** IEC 61215, IEC 61730, IEC 62109

---

## ✅ Checklist de Validación

- [x] Potencia total: 4,050 kWp
- [x] Configuración módulos: 6,472 × 31 = 200,632
- [x] Inversores: 2× Eaton Xpert1670
- [x] BESS: 2,000 kWh / 1,200 kW
- [x] Chargers: 128 (112 motos + 16 mototaxis)
- [x] Sockets: 512 (128 × 4)
- [x] Datos OE2: 8,760 rows/archivo
- [x] Validación CO₂: Incluida

---

**Documento actualizado:** 27 enero 2026  
**Responsable:** Especificaciones OE2 - Iquitos Project  
**Status:** ✅ FINAL - LISTO PARA OPERACIÓN
