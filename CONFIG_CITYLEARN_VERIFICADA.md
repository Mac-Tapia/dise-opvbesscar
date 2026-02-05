# ✅ CONFIGURACION CITYLEARN v2 - IQUITOS EV CHARGING OE3

**Resumen: UN EDIFICIO, DOS PLAYAS, 128 PUERTOS, HORARIO REAL**

---

## 1️⃣ ARQUITECTURA - UN SOLO EDIFICIO

```
Mall_Iquitos (ÚNICO BUILDING)
├── Playa_Motos
│   ├── 28 cargadores
│   ├── 4 tomas/charger = 112 puertos
│   └── Potencia: 2.0 kW/puerto (224 kW total)
│
└── Playa_Mototaxis
    ├── 4 cargadores
    ├── 4 tomas/charger = 16 puertos
    └── Potencia: 3.0 kW/puerto (48 kW total)
```

**Total: 32 cargadores × 4 tomas = 128 puertos/sockets**

**Recursos NO-OE2 eliminados:**
- ✅ washing_machines
- ✅ cooling_device / heating_device / dhw_device
- ✅ cooling_storage / heating_storage / dhw_storage
- ✅ electric_vehicle_chargers (CityLearn v2 usa "chargers")

---

## 2️⃣ HORARIO DE OPERACIÓN

| Parámetro | Valor | 
|-----------|-------|
| **Inicio operación** | 9 AM (09:00) |
| **Cierre operación** | 10 PM (22:00) |
| **Duración diaria** | 13 horas |
| **Punta/Peak horas** | 6 PM a 9 PM (18:19:20:21) |
| **Duración punta** | 4 horas |

Configuración en `src/rewards/rewards.py` (IquitosContext):
```python
operation_start_hour: int = 9      # 9 AM
operation_end_hour: int = 22        # 10 PM
operation_duration_hours: int = 13
peak_hours: Tuple[int, ...] = (18, 19, 20, 21)  # 6-9 PM
```

---

## 3️⃣ TIPO DE CARGA - MODO 3 CON COMUNICACION Y PROTECCIÓN

### Motos (112 puertos)
```
Batería: 2.5 kWh
Potencia carga: 2.0 kW
SOC inicial: 20% (degradado → requiere carga)
DOD máximo: 90%
Eficiencia: 95%
```

### Mototaxis (16 puertos)
```
Batería: 4.5 kWh
Potencia carga: 3.0 kW
SOC inicial: 20% (degradado → requiere carga)
DOD máximo: 90%
Eficiencia: 95%
```

**Características:**
- ✅ Modo 3: Comunicación bidireccional EV ↔ Charger
- ✅ Protección de batería: Límites SOC/DOD configurados
- ✅ Estados de carga múltiples: Initial SOC 20% permite amplio margen de carga
- ✅ Permite agente superar demanda diaria normal (2,060 veh/día)

---

## 4️⃣ ESTADOS DE CARGA PARA SUPERAR DEMANDA DIARIA

**Capacidad diaria:**
- Motos: 1,800 vehículos/día
- Mototaxis: 260 vehículos/día
- **Total: 2,060 vehículos/día**

**Sockets simultáneos disponibles:**
- Motos: 112 sockets × 2.0 kW = 224 kW
- Mototaxis: 16 sockets × 3.0 kW = 48 kW
- **Total simultáneo: 272 kW**

**Energía máxima disponible (13h operación):**
- Potencia máxima × Duración = 272 kW × 13h = 3,536 kWh/día
- Solo solar + BESS disponible para distribuir

**Estados de carga configurados:**
1. **SOC Inicial 20%** - Todos EVs llegan degradados → deben cargarse
2. **DOD 90%** - Cada puerto puede descargar hasta 90% → más energía disponible
3. **Target SOC 90%** - Agente intenta llevar a 90% antes de cierre (10 PM)
4. **Penalización < 80%** - Castigo en reward si avg_soc < 80% (penaliza carga insuficiente)

**Estrategia:**
- Agente DEBE cargar durante 9 AM-10 PM (13h operación)
- Horas punta (6-9 PM) críticas para demanda
- Solar directo prioriza EVs (mayor CO₂ grid)
- BESS almacena mañana, descarga tarde
- Penalización final 20-21h si SOC bajo

---

## 5️⃣ DATOS REALES OE2 INTEGRADOS

**5 archivos OBLIGATORIOS desde `data/oe2/`:**

| Archivo | Filas | Cols | Contenido |
|---------|-------|------|-----------|
| `chargers/chargers_real_hourly_2024.csv` | 8,760 | 128 | Perfiles reales 128 sockets |
| `chargers/chargers_real_statistics.csv` | - | - | Estadísticas de cargadores |
| `bess/bess_hourly_dataset_2024.csv` | 8,760 | 11 | BESS SOC% horario |
| `demandamallkwh/demandamallhorakwh.csv` | 8,785 | 1 | Demanda mall horaria |
| `Generacionsolar/pv_generation_hourly_citylearn_v2.csv` | 8,760 | - | Solar horaria PVGIS |
  
---

## 6️⃣ PESOS DE RECOMPENSA MULTIOBJETIVO

**Detectado en training (FASE 1 - actualizado 2026-02-05):**

```python
MultiObjectiveWeights:
  co2: 0.35               # Reducción CO₂ grid (prioridad 1)
  solar: 0.20             # Maximizar solar directo (prioridad 2)
  ev_satisfaction: 0.30   # TRIPLICADO: Carga EV (prioridad 3) 
  cost: 0.10              # Reducido: Tarifa baja
  ev_utilization: 0.03    # Bonus utilización
  grid_stability: 0.02    # Bonus ramping suave
```

---

## 7️⃣ VALIDACIÓN COMPLETADA

| Aspecto | Estado |
|---------|--------|
| **1 Edificio** | ✅ Mall_Iquitos único |
| **2 Playas** | ✅ Motos + Mototaxis |
| **128 Puertos** | ✅ 112 motos (2kW) + 16 mototaxis (3kW) |
| **Horario 9-22h** | ✅ 13 horas operación |
| **Punta 18-21h** | ✅ 4 horas peak |
| **Modo 3** | ✅ Comunicación + Protección |
| **Estados SOC** | ✅ Inicial 20%, DOD 90%, Target 90% |
| **Datos reales OE2** | ✅ 4 archivos obligatorios |
| **Recursos NO-OE2** | ✅ Todos eliminados |

---

## 🚀 LISTO PARA ENTRENAR

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

**Agentes entrenarán con:**
- ✅ 5 archivos REALES OE2 obligatorios (NO fallback)
- ✅ Datos reales de 128 cargadores (8,760h)
- ✅ Demanda real de mall
- ✅ BESS real horario
- ✅ Solar real PVGIS 4,050 kWp
- ✅ Penalizaciones reales por carga insuficiente
- ✅ Horas punta reales con peak penalties

**Métricas esperadas:**
- ev_soc_avg: >0.85 (mejorado desde ~0.50 con nuevas pesas)
- co2_reduction: 25-35% vs. baseline
- solar_utilization: 60-75%

---

## 📋 Referencias Código

- **Edificios/Playas:** `src/citylearnv2/dataset_builder/dataset_builder.py` L743-800
- **Horarios:** `src/rewards/rewards.py` L189-197
- **EVs Modo 3:** `src/citylearnv2/dataset_builder/dataset_builder.py` L786-830  
- **5 Datos OE2 OBLIGATORIOS:** `src/citylearnv2/dataset_builder/dataset_builder.py` L246-365
- **Pesos:** `src/rewards/rewards.py` L115-130
- **Penalizaciones:** `src/rewards/rewards.py` L370-390

