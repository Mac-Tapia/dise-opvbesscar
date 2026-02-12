# Documentación Completa del Sistema pvbesscar v5.3

## 📋 Resumen Ejecutivo

**Proyecto:** Optimización de carga de vehículos eléctricos con energía solar y almacenamiento BESS mediante aprendizaje por refuerzo.

**Ubicación:** Mall de Iquitos, Loreto, Perú (sistema eléctrico aislado 100% térmico diésel)

**Objetivo Principal:** Minimizar emisiones de CO₂ optimizando la carga de 309 vehículos eléctricos/día (270 motos + 39 mototaxis)

---

## 🏗️ Arquitectura del Sistema

### Infraestructura Física (v5.2)

| Componente | Especificación | Valor |
|------------|----------------|-------|
| **Sistema Solar PV** | Potencia DC | 4,162 kWp |
| | Potencia AC | 3,201 kW |
| | Módulos | 200,632 unidades |
| | Generación anual | 8,292,514 kWh/año |
| **Cargadores EV** | Total cargadores | 19 unidades |
| | Sockets totales | 38 (19 × 2) |
| | Potencia por socket | 7.4 kW (Mode 3, 32A @ 230V) |
| | Potencia instalada | 281.2 kW |
| **BESS** | Capacidad | 940-4,520 kWh |
| | Potencia nominal | 342 kW |
| | DoD | 80% |
| | Eficiencia round-trip | 95% |

### Cargas del Sistema

| Carga | Demanda | Consumo Anual |
|-------|---------|---------------|
| **Mall** | ~100 kW base (constante) | 12,403,168 kWh/año |
| **Cargadores EV** | ~50 kW promedio | 453,349 kWh/año |
| **Total** | 150 kW promedio | 12,856,517 kWh/año |

---

## 📊 Datasets Generados (OE2)

### 1. Dataset Solar (`pv_generation_hourly_citylearn_v2.csv`)

**Ubicación:** `data/oe2/Generacionsolar/`

**Estructura:** 8,760 filas × 18 columnas

| Columna | Descripción | Unidad |
|---------|-------------|--------|
| `datetime` | Timestamp horario 2024 | ISO 8601 |
| `ghi_wm2` | Irradiancia Global Horizontal | W/m² |
| `dni_wm2` | Irradiancia Normal Directa | W/m² |
| `dhi_wm2` | Irradiancia Difusa Horizontal | W/m² |
| `temp_air_c` | Temperatura ambiente | °C |
| `wind_speed_ms` | Velocidad del viento | m/s |
| `dc_power_kw` | Potencia DC generada | kW |
| `ac_power_kw` | Potencia AC (post-inversor) | kW |
| `dc_energy_kwh` | Energía DC por hora | kWh |
| `ac_energy_kwh` | Energía AC por hora | kWh |
| `is_hora_punta` | Flag HP (18:00-22:59) | 0/1 |
| `tarifa_aplicada_soles` | Tarifa OSINERGMIN aplicada | S/./kWh |
| `ahorro_solar_soles` | Ahorro por generación solar | S/. |
| `reduccion_indirecta_co2_kg` | CO₂ evitado total | kg |
| `co2_evitado_mall_kg` | CO₂ evitado atribuible al Mall (67%) | kg |
| `co2_evitado_ev_kg` | CO₂ evitado atribuible a EV (33%) | kg |
| `pv_kwh` | Alias de ac_energy_kwh | kWh |
| `pv_kw` | Alias de ac_power_kw | kW |

**Métricas Anuales:**
- Generación total: **8,292,514 kWh/año**
- Potencia máxima: **2,886.7 kW**
- Horas con generación: **4,259 horas** (49% del año)
- CO₂ evitado indirecto: **3,749 ton/año**

---

### 2. Dataset Cargadores EV (`chargers_ev_ano_2024_v3.csv`)

**Ubicación:** `data/oe2/chargers/`

**Estructura:** 8,760 filas × 353 columnas

#### Columnas por Socket (38 sockets × 9 columnas = 342)

| Patrón | Descripción | Unidad |
|--------|-------------|--------|
| `socket_XXX_charger_power_kw` | Potencia nominal cargador | kW (7.4) |
| `socket_XXX_battery_kwh` | Capacidad batería vehículo | kWh (4.6 moto / 7.4 taxi) |
| `socket_XXX_vehicle_type` | Tipo de vehículo | MOTO / MOTOTAXI |
| `socket_XXX_soc_current` | SOC actual durante carga | 0-1 |
| `socket_XXX_soc_arrival` | SOC al llegar | 0-1 |
| `socket_XXX_soc_target` | SOC objetivo | 0-1 (típ. 1.00) |
| `socket_XXX_active` | Socket ocupado | 0/1 |
| `socket_XXX_charging_power_kw` | Potencia real instantánea | kW |
| `socket_XXX_vehicle_count` | Contador vehículos atendidos | entero |

#### Columnas Agregadas OSINERGMIN/CO₂ (10 columnas nuevas)

| Columna | Descripción | Unidad |
|---------|-------------|--------|
| `is_hora_punta` | Flag Hora Punta (18:00-22:59) | 0/1 |
| `tarifa_aplicada_soles` | Tarifa OSINERGMIN (HP/HFP) | S/./kWh |
| `ev_energia_total_kwh` | Energía total cargada por hora | kWh |
| `costo_carga_ev_soles` | Costo de carga EV por hora | S/. |
| `ev_energia_motos_kwh` | Energía motos (sockets 0-29) | kWh |
| `ev_energia_mototaxis_kwh` | Energía mototaxis (sockets 30-37) | kWh |
| `co2_reduccion_motos_kg` | CO₂ evitado por motos | kg |
| `co2_reduccion_mototaxis_kg` | CO₂ evitado por mototaxis | kg |
| `reduccion_directa_co2_kg` | CO₂ total evitado (cambio combustible) | kg |
| `ev_demand_kwh` | Alias para CityLearn | kWh |

**Métricas Anuales:**
- Energía total cargada: **453,349 kWh/año**
  - Motos (30 sockets): 359,149 kWh
  - Mototaxis (8 sockets): 94,201 kWh
- Costo total OSINERGMIN: **S/.161,105/año**
  - Hora Punta (HP): S/.90,442 (200,982 kWh)
  - Fuera de Punta (HFP): S/.70,663 (252,368 kWh)
- CO₂ evitado directo: **356.7 ton/año**
  - Motos: 312.5 ton
  - Mototaxis: 44.3 ton
- Gasolina evitada: **154,430 L/año**

---

## ⚡ Tarifas OSINERGMIN (Electro Oriente S.A.)

**Pliego Tarifario MT3** - Media Tensión Comercial/Industrial  
**Vigente desde:** 2024-11-04  
**Referencia:** OSINERGMIN Resolución N° 047-2024-OS/CD

| Período | Horario | Tarifa Energía |
|---------|---------|----------------|
| Hora Punta (HP) | 18:00 - 22:59 | S/.0.45/kWh |
| Hora Fuera de Punta (HFP) | 00:00 - 17:59, 23:00 - 23:59 | S/.0.28/kWh |

---

## 🌿 Análisis de CO₂

### Factor de Emisión Base

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Factor CO₂ red eléctrica Iquitos | 0.4521 kg CO₂/kWh | MINEM/OSINERGMIN |
| Factor CO₂ gasolina | 2.31 kg CO₂/L | IPCC |

**Contexto:** Iquitos opera con un sistema eléctrico aislado 100% térmico (diésel + fuel oil residual), NO conectado al SEIN.

### Tipos de Reducción de CO₂

#### 1. Reducción INDIRECTA (Generación Solar)

La energía solar desplaza generación térmica diésel que alimentaría las cargas del proyecto.

| Carga | Proporción | CO₂ Evitado |
|-------|------------|-------------|
| Mall | 67% (100 kW / 150 kW) | 2,499.4 ton/año |
| Cargadores EV | 33% (50 kW / 150 kW) | 1,249.7 ton/año |
| **Total** | 100% | **3,749.0 ton/año** |

**Equivalencia:** 1,398,898 L diésel evitados/año

#### 2. Reducción DIRECTA (Cambio de Combustible)

Los vehículos eléctricos evitan emisiones de gasolina de motos/mototaxis tradicionales.

**Metodología de Cálculo:**

```
Para MOTOS (4.6 kWh batería):
1. EV recorre: 20 km/kWh
2. Moto gasolina 2T: 35 km/L
3. Por cada kWh cargado:
   - EV recorre 20 km
   - Moto gasolina consumiría: 20 km ÷ 35 km/L = 0.57 L
   - CO₂ evitado bruto: 0.57 L × 2.31 kg/L = 1.32 kg
4. MENOS emisiones indirectas electricidad: 1 kWh × 0.4521 = 0.45 kg
5. REDUCCIÓN NETA = 1.32 - 0.45 = 0.87 kg CO₂/kWh

Para MOTOTAXIS (7.4 kWh batería):
- Rendimiento menor: 10 km/kWh, 25 km/L gasolina
- Factor neto: 0.47 kg CO₂/kWh
```

| Tipo | Factor Neto | Energía | CO₂ Evitado |
|------|-------------|---------|-------------|
| Motos | 0.87 kg CO₂/kWh | 359,149 kWh | 312.5 ton/año |
| Mototaxis | 0.47 kg CO₂/kWh | 94,201 kWh | 44.3 ton/año |
| **Total** | 0.75 kg CO₂/kWh (prom.) | 453,349 kWh | **356.7 ton/año** |

**Equivalencia:** 154,430 L gasolina evitados/año

### Resumen CO₂ Total del Proyecto

| Tipo de Reducción | CO₂ Evitado | Porcentaje |
|-------------------|-------------|------------|
| Indirecta (Solar → Desplaza diésel) | 3,749.0 ton/año | 91.3% |
| Directa (EV → No gasolina) | 356.7 ton/año | 8.7% |
| **TOTAL** | **4,105.7 ton/año** | 100% |

---

## 🔧 Archivos Principales del Sistema

### OE2 - Dimensionamiento

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| `solar_pvlib.py` | `src/dimensionamiento/oe2/generacionsolar/disenopvlib/` | Generación solar con pvlib + PVGIS TMY |
| `chargers.py` | `src/dimensionamiento/oe2/disenocargadoresev/` | Simulación estocástica de cargadores v5.2 |
| `balance.py` | `src/dimensionamiento/oe2/balance_energetico/` | Balance energético integrado |
| `bess.py` | `src/dimensionamiento/oe2/bess/` | Dimensionamiento BESS |

### OE3 - Control (CityLearn)

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| `sac.py` | `src/agents/` | Agente Soft Actor-Critic |
| `ppo_sb3.py` | `src/agents/` | Agente PPO (stable-baselines3) |
| `a2c_sb3.py` | `src/agents/` | Agente A2C (stable-baselines3) |
| `dataset_builder.py` | `src/citylearnv2/dataset_builder/` | Constructor de datasets CityLearn |

### Datasets Generados

| Dataset | Ruta | Filas × Columnas |
|---------|------|------------------|
| Solar PV | `data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv` | 8,760 × 18 |
| Chargers EV | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` | 8,760 × 353 |
| Demanda Mall | `data/oe2/demandamallkwh/demandamallhorakwh.csv` | 8,760 × N |
| BESS Simulation | `data/oe2/bess/bess_simulation_hourly.csv` | 8,760 × N |

---

## 🚀 Comandos de Ejecución

### Generar Dataset Solar
```bash
python -m src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib
# Output: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
```

### Generar Dataset Chargers
```bash
python -m src.dimensionamiento.oe2.disenocargadoresev.chargers
# Output: data/oe2/chargers/chargers_ev_ano_2024_v3.csv
```

### Calcular Balance Energético
```bash
python -m src.dimensionamiento.oe2.balance_energetico.balance
```

### Verificar Datasets
```python
import pandas as pd

# Solar
df_solar = pd.read_csv('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
assert len(df_solar) == 8760, f"ERROR: {len(df_solar)} != 8760"
print(f"Solar OK: {df_solar['ac_energy_kwh'].sum():,.0f} kWh/año")

# Chargers
df_ev = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
assert len(df_ev) == 8760, f"ERROR: {len(df_ev)} != 8760"
print(f"EV OK: {df_ev['ev_energia_total_kwh'].sum():,.0f} kWh/año")
```

---

## 📐 Constantes del Sistema

### solar_pvlib.py

```python
# Tarifas OSINERGMIN
TARIFA_ENERGIA_HP_SOLES = 0.45     # S/./kWh Hora Punta
TARIFA_ENERGIA_HFP_SOLES = 0.28    # S/./kWh Fuera de Punta
HORA_INICIO_HP = 18
HORA_FIN_HP = 23

# Factor CO₂ red
FACTOR_CO2_KG_KWH = 0.4521  # kg CO₂/kWh (sistema térmico)

# Cargas
DEMANDA_MALL_KW = 100.0     # kW
DEMANDA_EV_KW = 50.0        # kW
DEMANDA_TOTAL_KW = 150.0    # kW
```

### chargers.py

```python
# Tarifas OSINERGMIN (mismas que solar)
TARIFA_ENERGIA_HP_SOLES = 0.45
TARIFA_ENERGIA_HFP_SOLES = 0.28

# Factores CO₂ cambio combustible
FACTOR_CO2_GASOLINA_KG_L = 2.31         # kg CO₂/L (IPCC)
FACTOR_CO2_RED_DIESEL_KG_KWH = 0.4521   # kg CO₂/kWh
FACTOR_CO2_NETO_MOTO_KG_KWH = 0.87      # kg CO₂/kWh neto
FACTOR_CO2_NETO_MOTOTAXI_KG_KWH = 0.47  # kg CO₂/kWh neto

# Eficiencia de carga
CHARGING_EFFICIENCY = 0.62  # 62% (pérdidas cargador + cable + batería + taper)
```

---

## 📈 Resultados Esperados

### Balance Energético Anual

| Flujo | Valor | Porcentaje |
|-------|-------|------------|
| Generación Solar PV | 8,292,514 kWh | - |
| Demanda Total (Mall + EV) | 12,856,517 kWh | 100% |
| Solar → Demanda | ~6,500,000 kWh | ~50% |
| Importación Red | ~6,300,000 kWh | ~50% |

### KPIs Objetivo (con RL)

| Métrica | Baseline | Meta RL |
|---------|----------|---------|
| Autosuficiencia | 50% | 60-70% |
| Autoconsumo solar | 75% | 85-95% |
| CO₂ reducido | 4,106 ton | +5-10% adicional |
| Costo energía | S/.161k (EV) | -10-15% |

---

## 📅 Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v5.2 | 2026-02-11 | Chargers 19×2=38 sockets, simulación estocástica |
| v5.3 | 2026-02-12 | Columnas OSINERGMIN/CO₂ en chargers.py y solar_pvlib.py |

---

**Última actualización:** 2026-02-12  
**Autor:** pvbesscar project
