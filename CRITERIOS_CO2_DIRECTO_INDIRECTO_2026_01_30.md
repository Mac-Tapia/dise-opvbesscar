# 📊 CRITERIOS DE EVALUACIÓN: CO₂ Directo vs Indirecto (2026-01-30)

## Nuevos Criterios de Comparación de Agentes

Ahora la evaluación de SAC vs PPO vs A2C se basa en **DOS COMPONENTES** de reducción de CO₂:

### 1️⃣ **Reducción INDIRECTA de CO₂** (via consumo solar)

**Definición**: Cada kWh de solar que se CONSUME evita importar 1 kWh de la red térmica

**Cálculo**:
```
CO₂ indirect avoided [kg] = Solar consumed [kWh] × 0.4521 [kg CO₂/kWh]
```

**Mecanismo**:
- Solar generado → Carga directo a EVs (PV→EV)
- Solar → Carga BESS (PV→BESS) para noche
- Solar → Demanda MALL (PV→MALL)
- **Resultado**: Grid import reducido = CO₂ grid evitado

**Métrica en logs**:
```
co2_indirect_kg=172.0  ← kg CO₂ evitado por solar
solar_kWh=172.0        ← kWh solar realmente consumido
```

**Importancia**: Refleja qué tan bien el agente **aprovecha recursos renovables** disponibles

---

### 2️⃣ **Reducción DIRECTA de CO₂** (via carga completa de EVs)

**Definición**: Cada moto/mototaxi cargada al 100% reemplaza viaje en combustible (gasolina/diésel)

**Cálculo**:
```
CO₂ direct avoided [kg] = 
    (# motos cargadas × 2.5 kg CO₂/moto) +
    (# mototaxis cargadas × 3.5 kg CO₂/mototaxi)
```

**Factores de CO₂ (vs combustible)**:
- Moto: **2.5 kg CO₂/carga** (reemplaza ~0.5 L gasolina a 5 kg CO₂/L)
- Mototaxi: **3.5 kg CO₂/carga** (mayor consumo de combustible)

**Criterio de "cargada"**: SOC ≥ 90% (0.9)

**Métrica en logs**:
```
co2_direct_kg=52.5     ← kg CO₂ evitado por EVs cargadas
motos_cargadas=18      ← # motos con SOC >= 90%
mototaxis_cargadas=3   ← # mototaxis con SOC >= 90%
```

**Importancia**: Refleja qué tan bien el agente **satisface la demanda de transporte**

---

## Desglose Completo en Logs

**Nuevo formato de logs**:
```
[SAC] paso 500 | ep~1 | pasos_global=500 | reward_avg=29.8 | ... |
  grid_kWh=376.0 | co2_grid_kg=170.2 | solar_kWh=172.0 |
  co2_indirect_kg=172.0 | co2_direct_kg=52.5 | motos_cargadas=18 | mototaxis_cargadas=3 |
  co2_total_avoided_kg=224.5
```

**Componentes**:
1. **Grid**: `grid_kWh=376.0` (solo lo importado, no lo solar)
2. **CO₂ desde grid**: `co2_grid_kg=170.2` (grid_kWh × 0.4521)
3. **Solar consumido**: `solar_kWh=172.0` (EV+BESS+MALL)
4. **CO₂ indirecto evitado**: `co2_indirect_kg=172.0` (solar × 0.4521)
5. **CO₂ directo evitado**: `co2_direct_kg=52.5` (motos + mototaxis cargadas)
6. **EVs cargadas**: `motos_cargadas=18, mototaxis_cargadas=3`
7. **Total evitado**: `co2_total_avoided_kg=224.5` (indirecto + directo)

---

## Comparación de Agentes con Nuevos Criterios

| Métrica | SAC (mejor esperado) | PPO (mejor esperado) | Significado |
|---------|-------------------|-------------------|-------------|
| `co2_indirect_kg` | Más alto | Más bajo | SAC mejor aprovecha solar (menos curtailment) |
| `solar_kWh` | Más alto | Más bajo | SAC consume más solar disponible |
| `co2_direct_kg` | Más bajo | Más alto | PPO carga más EVs completamente (mejor satisfacción) |
| `motos_cargadas` | Menos | Más | PPO prioriza completar carga vs aprovechar solar |
| `mototaxis_cargadas` | Menos | Más | PPO hace más equitativo (completa las demandadas) |
| `co2_total_avoided_kg` | Equilibrio | Equilibrio | Muestra suma de ambos beneficios |

---

## Interpretación de Resultados

### Caso 1: SAC domina
```
SAC:  co2_indirect=200, co2_direct=30, total=230
PPO:  co2_indirect=120, co2_direct=60, total=180
```
→ **SAC es mejor**: Aprovecha más solar (menor curtailment), aunque PPO carga más EVs

### Caso 2: PPO domina
```
SAC:  co2_indirect=150, co2_direct=40, total=190
PPO:  co2_indirect=160, co2_direct=80, total=240
```
→ **PPO es mejor**: Más CO₂ total evitado (solar + EVs), mejor balance

### Caso 3: A2C balance
```
SAC:  co2_indirect=180, co2_direct=50, total=230
PPO:  co2_indirect=170, co2_direct=55, total=225
A2C:  co2_indirect=175, co2_direct=53, total=228
```
→ **A2C equilibra**: Similares en ambos componentes, buen balance operacional

---

## Funciones Implementadas

### En `rewards.py`:

```python
def calculate_co2_reduction_indirect(
    solar_consumed_kwh: float,
    co2_factor_kg_per_kwh: float = 0.4521,
) -> float:
    """CO₂ evitado por solar consumido"""

def calculate_co2_reduction_direct(
    ev_chargers_soc_pct: List[float],
    charger_types: List[str],  # "moto" o "mototaxi"
    co2_factor_moto: float = 2.5,
    co2_factor_mototaxi: float = 3.5,
    soc_threshold_full: float = 0.90,
) -> Dict[str, float]:
    """CO₂ evitado por EVs cargadas"""
```

### En `agents/sac.py` (PPO y A2C similares):

```python
# Métricas acumuladas
self.co2_indirect_avoided_kg = 0.0  # Reducción indirecta
self.co2_direct_avoided_kg = 0.0    # Reducción directa
self.motos_cargadas = 0
self.mototaxis_cargadas = 0

# Se calculan en cada step desde dispatch y charger SOC
# Se resetean al fin de episodio
```

---

## Validación

Compilación sin errores:
```bash
python -m py_compile src/iquitos_citylearn/oe3/rewards.py
python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
```
✅ OK

Funciones disponibles:
```bash
python -c "from src.iquitos_citylearn.oe3.rewards import calculate_co2_reduction_indirect, calculate_co2_reduction_direct; print('✅ Funciones listas')"
```
✅ OK

---

## Próximos Pasos

1. **Reiniciar entrenamiento SAC+PPO** con nuevas métricas
2. **Monitorear logs** para ver CO₂ directo e indirecto
3. **Comparar agentes** usando AMBAS reducciones, no solo grid import
4. **Identificar especialización**: SAC→solar, PPO→EVs, A2C→balance
5. **Optimizar pesos de recompensa** según preferencias (solar vs satisfacción EV)

---

**Fecha**: 2026-01-30
**Versión**: pvbesscar v1.3 (Criterios CO₂ Dual)
**Estado**: ✅ Implementado y listo para entrenamiento

