# Integración del Perfil de EV desde Chargers.py hacia Balance.py

**Estado**: Análisis completado (2026-02-19)  
**Objetivo**: Asegurar que balance.py refleje la lógica real de carga desde chargers.py

---

## 1. Diferencias Identificadas

### 1.1 Información en chargers.py (COMPLETA)
```python
# FACTORES OPERACIONALES HORARIOS (chargers.py:901)
def get_operational_factor(hour_of_day: int) -> float:
    """
    0-8h: 0% (cerrado)
    9-10h: 30% (apertura)
    10-18h: rampa lineal 30% -> 100%
    18-21h: 100% (punta)
    21-24h: 0% (cierre realista)
    """
    
# ESPECIFICACIONES DE VEHÍCULOS (chargers.py:200-250)
MOTO_SPEC = VehicleType(
    name="MOTO",
    lambda_arrivals=8.76,  # Llegadas Poisson por hora
    power_kw=7.4,  # Nominal
    capacity_kwh=4.6,  # Batería
    soc_arrival_mean=0.245,  # Media SOC llegada
    soc_arrival_std=0.10,  # Desv std SOC llegada
    soc_target=0.78,  # SOC objetivo
    soc_target_std=0.12  # Variabilidad SOC objetivo
)

MOTOTAXI_SPEC = VehicleType(
    name="MOTOTAXI",
    lambda_arrivals=1.06,  # Menos frecuentes
    power_kw=7.4,  # Mismo que motos
    capacity_kwh=7.4,  # Batería más grande
    soc_arrival_mean=0.245,
    soc_arrival_std=0.10,
    soc_target=0.78,
    soc_target_std=0.12
)

# EFICIENCIA REAL (chargers.py:280)
CHARGING_EFFICIENCY = 0.62  # 62% potencia nominal
  → 7.4 kW nominal → 4.6 kW efectivos reales
  → Incluye pérdidas en cargador, cable, batería, taper

# ENERGÍA ESTÁNDAR POR CARGA (chargers.py:310)
MOTO_ENERGY_TO_CHARGE_KWH = 0.60 * 4.6 / 0.95 = 2.906 kWh  # SOC 20%-80%
MOTOTAXI_ENERGY_TO_CHARGE_KWH = 0.60 * 7.4 / 0.95 = 4.674 kWh
```

### 1.2 Información en balance.py (INCOMPLETA)
```python
# CARGA BRUTA DESDE CSV (balance.py:277)
ev_demand = self._extract_column(self.df_chargers, ["total_demand_kw"])

# PROBLEMAS:
# 1. No aplica factores operacionales horarios (¿carga 24/7?)
# 2. No diferencia motos vs mototaxis en análisis
# 3. No captura SOC variables por vehículo
# 4. No usa la eficiencia real 62%
# 5. No verifica restricciones de horario (cerrado 0-9h, 22-24h)
# 6. No captura la lógica estocástica real (Poisson, colas, etc.)
```

---

## 2. Información Correcta a Jalar desde Chargers.py

### 2.1 FACTORES OPERACIONALES HORARIOS
**Ubicación**: [src/dimensionamiento/oe2/disenocargadoresev/chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py#L901)

**Función clave**: `get_operational_factor(hour_of_day: int) -> float`

**Patrón realista del mall**:
```
Hora  |  Factor  |  Estado
------|----------|----------
0-8   |   0%     |  CERRADO
9-10  |  30%     |  Iniciando operación
10-18 |  30→100% |  Rampa lineal (8 horas)
18-21 |  100%    |  PUNTA MÁXIMA (3 horas)
21-24 |   0%     |  CERRADO (cierre realista)
```

**Uso en balance.py**:
```python
# Actualmente: lee CSV sin considerar horario
ev_demand_raw = self.df_chargers[power_cols].sum()  # ← Suma directa

# Debería: aplicar factor operacional a demanda teórica
operational_factor = get_operational_factor(hour_of_day)
ev_demand = ev_demand_base * operational_factor  # ← Con modulación horaria
```

### 2.2 ESPECIFICACIONES DE VEHÍCULOS POR TIPO

**Ubicación**: [src/dimensionamiento/oe2/disenocargadoresev/chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py#L250-330)

**Tabla comparativa**:

| Parámetro | MOTOS | MOTOTAXIS | En Balance? |
|-----------|-------|-----------|------------|
| **Cantidad/día** | 270 | 39 | ✗ NO |
| **Capacidad batería (kWh)** | 4.6 | 7.4 | ✗ NO |
| **Potencia nominal (kW)** | 7.4 | 7.4 | ✗ NO |
| **Potencia efectiva (kW)** | 4.6 | 4.6 | ✗ NO (usa 7.4) |
| **SOC llegada media** | 24.5% | 24.5% | ✗ NO |
| **SOC objetivo media** | 78% | 78% | ✗ NO |
| **Energía por carga** | 2.906 kWh | 4.674 kWh | ✗ NO |
| **Cargadores asignados** | 15 | 4 | ✓ SÍ (en estructura) |
| **Tomas asignadas** | 30 | 8 | ✓ SÍ (38 total) |

### 2.3 RESTRICCIONES OPERACIONALES

**Ubicación**: [src/dimensionamiento/oe2/disenocargadoresev/chargers.py](../src/dimensionamiento/oe2/disenocargadoresev/chargers.py#L500-600)

| Restricción | Especificación | En Balance? |
|-------------|----------------|------------|
| **Horario operativo** | 9h-22h (21h cierre) | ✗ NO verificado |
| **SOC mínimo operacional** | 20% (DoD 80%) | ✓ SÍ (en BESS) |
| **SOC máximo** | 100% | ✓ SÍ |
| **Factor de carga día** | 55% (feriales) | ✗ NO |
| **Distribución punta** | 55% cargas 18-22h | ✗ NO |
| **Eficiencia de carga** | 62% potencia real | ✗ NO (asume 7.4 kW) |

---

## 3. Lógica de Carga Correcta (según chargers.py)

### 3.1 FASE 1: CARGA INICIAL (9h-18h)

**Contexto**: Motos llegan con SOC bajo (media 24%, rango 10%-40%)

```python
# chargers.py: Vehicle.charge_for_hour()
# Para cada vehículo que llega a un socket:

1. Generar SOC_ARRIVAL ~ Normal(0.245, 0.10)  # Qué carga trae
2. Generar SOC_TARGET ~ Normal(0.78, 0.12)    # Adónde quiere cargar
3. ENERGÍA A CARGAR = (SOC_target - SOC_arrival) × capacity_kwh
   Ejemplos reales:
   - Moto 10%→80%: (0.70) × 4.6 = 3.22 kWh → ~42 min
   - Moto 25%→78%: (0.53) × 4.6 = 2.44 kWh → ~32 min
   - Moto 35%→100%: (0.65) × 4.6 = 2.99 kWh → ~39 min
   
4. Potencia efectiva = 7.4 × 0.62 = 4.6 kW (con pérdidas)
5. Checkear: SOLO cargar durante 9h-21h (cerrado 0-9h, 22-24h)
```

**En balance.py actualmente**:
- ✗ No captura SOC variable
- ✗ Asume carga fija (all-or-nothing)
- ✗ No diferencia por tipo de vehículo

### 3.2 FASE 2: CONCENTRACIÓN PUNTA (18h-21h)

**Contexto**: 55% de cargas diarias se concentran en 3 horas

```python
# chargers.py: get_operational_factor(18-21h) = 1.0
# Factor de simultaneidad = cantidad motos simultáneas / 30 sockets

Demanda PUNTA:
- Motos: 30 motos/hora ÷ 1.0 carga/hora = 30 tomas activas
- Mototaxis: 4.2 taxis/hora ÷ 0.67 cargas/hora = 6 tomas activas
- Total PUNTA: 36 de 38 tomas activas = 94% ocupación
  → Factor simultaneidad = 22.9 vehículos / 38 = 60% (realista)
```

**En balance.py**:
- ✗ No refleja que PUNTA es fase concentrada
- ✗ No diferencia demanda fuera punta vs punta

### 3.3 FASE 3: CIERRE OPERACIONAL (21h-24h)

**Contexto**: Hora 21 es CIERRE REAL (no hay nuevas llegadas Poisson)

```python
# chargers.py: get_operational_factor(21) = 0.0
# Esto significa:
#   - Nuevas llegadas = Poisson(λ × 0.0) = 0 (nadie llega)
#   - Vehículos en carga SE DESCONECTAN (no pueden quedarse)
#   - Energía de hora 21 se redistribuye a 18-20h

# Pero balance.py usa CSV ya simulado que ya tiene redistribución
```

---

## 4. Recomendaciones de Mejora para Balance.py

### 4.1 CORTO PLAZO (Validación)

**Paso 1**: Verificar que CSV desde chargers refleja:
```python
# En balance.py, después de cargar CSV:

# 1. Validar factor operacional
df_chargers['hour'] = pd.to_datetime(df_chargers.index).hour
for hour in range(24):
    hour_data = df_chargers[df_chargers['hour'] == hour]
    factor = get_operational_factor(hour)
    energia_esperada = energia_base * factor
    energia_actual = hour_data[socket_cols].sum().sum()
    assert energia_actual ≈ energia_esperada, f"Hour {hour} no coincide"

# 2. Validar proporción motos vs mototaxis
energia_motos = sum de sockets 0-29
energia_taxis = sum de sockets 30-37
ratio = energia_motos / energia_taxis
assert 6.5 < ratio < 7.5, f"Ratio motos/taxis inválida: {ratio}"
  # Basado en: (energía_motos / energía_taxis) = 
  # (270 × 2.906) / (39 × 4.674) = 6.9

# 3. Verificar energía total
energia_total_csv = sum de todas las celdas
energia_esperada = (270 × 2.906 + 39 × 4.674) × 365
assert energia_total_csv ≈ energia_esperada, "Energía anual no coincide"
```

### 4.2 MEDIANO PLAZO (Documentación)

**Paso 2**: Crear módulo de conexión con chargers:
```python
# src/dimensionamiento/oe2/balance_energetico/ev_profile_loader.py

from src.dimensionamiento.oe2.disenocargadoresev.chargers import (
    get_operational_factor,
    MOTO_SPEC,
    MOTOTAXI_SPEC,
    CHARGING_EFFICIENCY,
    MOTO_ENERGY_TO_CHARGE_KWH,
    MOTOTAXI_ENERGY_TO_CHARGE_KWH
)

class EVProfileConfig:
    """Configuración del perfil EV desde chargers.py"""
    
    # Factores operacionales horarios
    operational_factors = [
        get_operational_factor(h) for h in range(24)
    ]
    
    # Especificaciones de vehículos
    moto_spec = MOTO_SPEC
    mototaxi_spec = MOTOTAXI_SPEC
    
    # Eficiencia y energía
    charging_efficiency = CHARGING_EFFICIENCY  # 62%
    moto_energy_per_charge = MOTO_ENERGY_TO_CHARGE_KWH  # 2.906 kWh
    mototaxi_energy_per_charge = MOTOTAXI_ENERGY_TO_CHARGE_KWH  # 4.674 kWh
    
    # Restricciones
    operational_hours = (9, 22)  # 9h-22h
    soc_min = 0.20  # 20% mínimo
    soc_max = 1.00  # 100% máximo
    dod_max = 0.80  # Profundidad descarga máxima
    
    @classmethod
    def get_hourly_profile_factor(cls, hour: int) -> float:
        """Retorna factor operacional para hora dada"""
        return cls.operational_factors[hour % 24]
```

### 4.3 LARGO PLAZO (Integración)

**Paso 3**: Enriquecer balance.py con información detallada:
```python
# En balance.py.calculate_balance():

# Agregar información de perfil EV a cada fila
def _calculate_ev_profile():
    ev_profile_data = []
    
    for hour_idx in range(8760):
        hour = hour_idx % 24
        
        # Factor operacional
        op_factor = get_operational_factor(hour)
        
        # Demanda teórica vs actual
        demanda_teorica_motos = 270 * 2.906 / 365  # Promedio diario
        demanda_teorica_taxis = 39 * 4.674 / 365
        demanda_real_motos = demanda_motos[hour_idx] *  op_factor
        demanda_real_taxis = demanda_taxis[hour_idx] * op_factor
        
        ev_profile_data.append({
            'hour': hour,
            'operational_factor': op_factor,
            'demanda_teorica_motos_kwh': demanda_teorica_motos,
            'demanda_teorica_taxis_kwh': demanda_teorica_taxis,
            'demanda_real_motos_kwh': demanda_real_motos,
            'demanda_real_taxis_kwh': demanda_real_taxis,
        })
    
    return pd.DataFrame(ev_profile_data)
```

---

## 5. Checklist de Validación

- [ ] **Chargers.py**: Verificar `get_operational_factor()` retorna valores correctos 0-100%
- [ ] **CSV chargers**: Validar que energía por hora < demanda máxima teórica
- [ ] **Balance.py**: Verificar que total_demand_kw no es constante 24h
- [ ] **Proporción**: Validar ratio motos/taxis en demanda (6.5-7.5)
- [ ] **Horario**: Confirmar energía=0 en horas 0-8 y 22-23
- [ ] **Punta**: Validar que 18h-21h concentran 55% de energía
- [ ] **Eficiencia**: Verificar que potencia efectiva = 7.4 × 0.62 = 4.6 kW
- [ ] **SOC variable**: Confirmar energía por vehículo varía (2.5-4.5 kWh motos)

---

## 6. Referencias Cruzadas

| Aspecto | Chargers.py | Balance.py | Status |
|---------|-------------|-----------|--------|
| Factores operacionales | L901 | ✗ | FALTANTE |
| Especificaciones vehículos | L200-330 | ✓ CSV | INCOMPLETO |
| Restricciones horarias | L500-600 | ✓ BESS | PARCIAL |
| Eficiencia real (62%) | L280 | ✗ (asume 7.4) | FALTANTE |
| Energía por carga variable | L540-600 | ✗ | FALTANTE |
| Colas estocásticas | L800+ | ✓ CSV | AGREGADO |

---

**Conclusión**: Balance.py carga datos FINALES desde CSV (chargers_ev_ano_2024_v3.csv), 
pero no documenta ni valida que estos datos reflejen la lógica correcta de chargers.py.
Se recomienda crear módulo de validación y documentación de esta integración.
