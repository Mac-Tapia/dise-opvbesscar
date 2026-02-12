# Balance Energético Real v5.2

**Fecha:** 2026-02-12  
**Fuente de datos:** Dataset generado v5.2 + Demanda real mall (red pública)

---

## Resumen Ejecutivo

| Componente | Anual (kWh) | Diario (kWh) | Pico (kW) |
|------------|-------------|--------------|-----------|
| ☀️ **Solar PV** (4,050 kWp) | 4,775,948 | 13,085 | 1,983 |
| 🏬 **Mall** (red pública) | 12,403,168 | 33,981 | 2,763 |
| 🔌 **EV** (38 sockets v5.2) | 453,349 | 1,242 | 156 |
| **DEMANDA TOTAL** | **12,856,517** | **35,223** | **~2,919** |
| **DÉFICIT (de red)** | **8,080,570** | **22,138** | - |

**Cobertura Solar:** 37.1% de la demanda total

---

## Emisiones CO₂

| Escenario | Emisiones (ton CO₂/año) |
|-----------|-------------------------|
| Sin solar (100% red) | 5,812 |
| Con solar (37.1% solar) | 3,653 |
| **CO₂ evitado** | **2,159** |

*Factor de emisión: 0.4521 kg CO₂/kWh (generación térmica Iquitos)*

---

## Detalle EV v5.2

### Infraestructura de Carga
- **19 cargadores** Modo 3 monofásico
- **38 sockets totales** (2 por cargador)
- **7.4 kW por socket** (32A @ 230V)
- **281.2 kW potencia instalada**

### Distribución de Sockets
| Tipo | Sockets | kWh/día | kWh/año | Batería |
|------|---------|---------|---------|---------|
| Motos eléctricas | 30 (0-29) | 984 | 359,149 | 4.6 kWh |
| Mototaxis eléctricas | 8 (30-37) | 258 | 94,201 | 7.4 kWh |
| **TOTAL** | **38** | **1,242** | **453,349** | - |

### Demanda EV Horaria
- **Pico:** 156 kW (55% de capacidad instalada)
- **Media:** 51.8 kW
- **Operación:** 09:00 - 22:00 (horario comercial)

---

## Componentes del Sistema

### 1. Generación Solar PV
- **Capacidad:** 4,050 kWp
- **Ubicación:** Iquitos, Perú (lat -3.75°)
- **Generación anual:** 4,775,948 kWh
- **Yield:** 1,179 kWh/kWp/año
- **Horas pico solares:** ~5.0 h/día promedio

### 2. Demanda Mall (RED PÚBLICA)
- **Consumo anual:** 12,403,168 kWh (12.4 GWh)
- **Consumo diario:** 33,981 kWh
- **Pico:** 2,763 kW
- **Fuente:** Red pública Electro Oriente
- **Archivo:** `data/oe2/demandamallkwh/demandamallhorakwh.csv`

### 3. Demanda EV (v5.2)
- **Consumo anual:** 453,349 kWh
- **Consumo diario:** 1,242 kWh
- **Pico:** 156 kW
- **Factor de carga:** 51.8 kW / 281.2 kW = 18.4%

---

## Balance Horario Típico

### Horas de Generación Solar (06:00-18:00)
- Generación solar reduce importación de red
- BESS se carga con excedente (si hay)
- Mall + EV consumen ~2,919 kW pico

### Horas Sin Solar (18:00-06:00)
- Demanda 100% de red pública
- BESS descarga para cubrir EV
- Importación de red para mall

---

## Dimensionamiento BESS Recomendado

### Objetivo: Almacenar excedente solar para EV nocturno

La demanda del mall es mucho mayor que la generación solar, por lo que el BESS debería enfocarse en:
1. Almacenar excedente solar durante horas pico de generación
2. Descargar para cubrir demanda EV en horario nocturno

### Opción Recomendada
- **Capacidad:** 1,500 - 2,000 kWh
- **Potencia:** 500 - 750 kW
- **Objetivo:** Cubrir demanda EV cuando no hay sol (~40% de 1,242 kWh = 500 kWh)

---

## Archivos de Datos

| Archivo | Descripción | Filas |
|---------|-------------|-------|
| `data/oe2/Generacionsolar/pv_generation_timeseries.csv` | Generación solar horaria | 8,760 |
| `data/oe2/demandamallkwh/demandamallhorakwh.csv` | Demanda mall REAL (red pública) | 8,785 |
| `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` | Demanda EV horaria v5.2 | 8,760 |

---

*Generado automáticamente con datos del dataset v5.2 y demanda real del mall*
