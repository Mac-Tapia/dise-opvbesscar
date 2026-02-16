# 🗺️ MAPA RÁPIDO DE REFERENCIA: LÍNEAS CLAVE DE CO2 EN SAC v7.1

## 📍 RUTAS PRINCIPALES

### 🔴 CARGUE DE DATASETS (Línea 600+)

```python
Línea 726-851    ← DOCUMENTACION ESTRUCTURAL DE CO2 (COMIENZA AQUI)
Línea 745        ← SOLAR: pv_generation_citylearn_enhanced_v2.csv (16 columnas)
Línea 833        ← CHARGERS: chargers_ev_ano_2024_v3.csv (38 sockets)
Línea 913        ← MALL: demandamallhorakwh.csv (6 columnas)
Línea 965        ← BESS: bess_ano_2024.csv (25 columnas)
```

**LEE ESTO PRIMERO:** Líneas 726-851 → Explicación completa de datasets

---

### 🔴 CÁLCULO DE CO2 EN STEP() (Línea 1850+)

```
Línea 1850-1880     ← DOCUMENTO ESTRUCTURA CO2 v7.1
Línea 1872-1888     ← CO2 DIRECTO (Solo EV)
Línea 1890-1928     ← CO2 INDIRECTO SOLAR (PV→EV,BESS,Mall,Red)
Línea 1930-1965     ← CO2 INDIRECTO BESS (Con condición > 2000 kW)
Línea 1944-1955     ← PEAK SHAVING FACTOR DINAMICO
Línea 1967-1983     ← MALL EMITE CO2 (NO REDUCE)
Línea 1984          ← CO2 GRID (importacion)
```

**FLUJO DE EJECUCIÓN:** 1872 → 1890 → 1930 → 1944 → 1967 → 1984

---

### 🔴 ACUMULACIÓN DE METRICAS (Línea 2216+)

```python
Línea 2216-2232     ← ACUMULAR TOTALES POR EPISODIO
  2217              ← episode_co2_directo_evitado_kg
  2218              ← episode_co2_indirecto_evitado_kg
  2219              ← episode_co2_indirecto_solar_kg         [v7.1 nuevo]
  2220              ← episode_co2_indirecto_bess_kg          [v7.1 nuevo]
  2221              ← episode_co2_mall_emitido_kg            [v7.1 nuevo]
  2222              ← episode_co2_grid_kg
```

---

### 🔴 COMPONENTES DE REWARD (Línea 2108+)

```python
Línea 2108-2116     ← PESOS DEL REWARD (Total = 1.0)
  2109              ← W_CO2 = 0.45    (45% - MAXIMA PRIORIDAD)
  2110              ← W_SOLAR = 0.15
  2111              ← W_VEHICLES = 0.20
  2112              ← W_COMPLETION = 0.10
  Línea 2125        ← co2_component: -grid_import × 45%
```

**INCENTIVO PRINCIPAL:** Minimizar grid_import = minimizar CO2

---

## 📊 TABLA DE CORRESPONDENCIA: DATOS → LINEA → VARIABLE

| Dato Real | Dataset CSV | Línea Carga | Variable | Línea Uso | Componente |
|---|---|---|---|---|---|
| Reducción directa EV | chargers_ev_ano..v3 | 854 | reduccion_directa_co2_kg | 1876 | CO2 DIRECTO |
| Solar → EV/BESS/Mall | pv_generation...v2 | 789 | reduccion_indirecta_co2_kg_total | 1900 | CO2 INDIRECTO SOLAR |
| BESS → EV | bess_ano_2024 | 1110 | bess_to_ev_kwh | 1934 | CO2 INDIRECTO BESS |
| BESS → MALL | bess_ano_2024 | 1110 | bess_to_mall_kwh | 1937 | CO2 INDIRECTO BESS |
| Mall emite | demandamallhorakwh | 931 | mall_co2_indirect_kg | 1971 | CO2 MALL |
| Grid import | energy_flows | 1147 | grid_import_total_kwh | 1984 | CO2 GRID |

---

## 🔍 BUSQUEDA RAPIDA POR COMPONENTE

### Si quieres entender CO2 DIRECTO:
```
1. Lee líneas 726-751   ← Concepto en español
2. Mira línea 854       ← Carga de chargers_data['reduccion_directa_co2_kg']
3. Ve línea 1872-1888   ← Implementación: co2_directo_evitado_kg = 
4. Revisa 2217         ← Acumulación: selbst.episode_co2_directo_evitado_kg +=
```

### Si quieres entender CO2 INDIRECTO SOLAR:
```
1. Lee líneas 749-767   ← Concepto en español
2. Mira línea 789       ← Carga de solar_data['reduccion_indirecta_co2_kg_total']
3. Ve línea 1890-1928   ← Implementación: co2_indirecto_solar_kg = 
4. Revisa 2219         ← Acumulación: self.episode_co2_indirecto_solar_kg +=
```

### Si quieres entender CO2 INDIRECTO BESS:
```
1. Lee líneas 752-765   ← Concepto en español CON CONDICION
2. Mira línea 1110      ← Carga de energy_flows['bess_to_ev_kwh', 'bess_to_mall_kwh']
3. Ve línea 1930-1965   ← Implementación CON PEAK SHAVING
4. Revisa 1944-1955     ← Peak shaving factor: if mall_demand > 2000 kW
5. Revisa 2220          ← Acumulación: self.episode_co2_indirecto_bess_kg +=
```

### Si quieres entender MALL EMITE:
```
1. Lee líneas 761-768   ← Concepto: "MALL EMITE CO2, NO REDUCE"
2. Mira línea 931-935   ← Carga de mall_data['mall_co2_indirect_kg']
3. Ve línea 1967-1983   ← Implementación: co2_mall_emitido_kg = 
4. Revisa 2221          ← Acumulación: self.episode_co2_mall_emitido_kg +=
```

---

## 🎯 ECUACIÓN FINAL (DONDE SE SUMA TODO)

```python
Línea 2125-2184    ← COMPONENTES DE REWARD (normalizado a [-0.5, +0.5])
Línea 2192         ← SCALING Y CLIP: reward = clip(base × 0.01, -0.02, +0.02)
Línea 2201-2232    ← ACUMULACION DE METRICAS POR EPISODIO
  
CO2_TOTAL por episodio:
  = episode_co2_directo_evitado_kg
  + episode_co2_indirecto_solar_kg
  + episode_co2_indirecto_bess_kg
  - episode_co2_mall_emitido_kg
  - episode_co2_grid_kg
```

---

## 🛠️ CHEATSHEET: CÓMO DEBUGGEAR CO2

### Problema: CO2 demasiado alto?
```
1. Revisa línea 1984: ¿grid_import > 500 kW?
2. Revisa línea 1976: ¿co2_grid_kg > 250 kg/h?
3. Revisa línea 2125: grid_import_normalized × -0.45 → muy negativo?
```

### Problema: CO2 BESS = 0?
```
1. Revisa línea 1934-1937: ¿bess_to_ev_kwh = 0 AND bess_to_mall_kwh = 0?
2. Revisa línea 1944: ¿mall_demand < 2000 kW? (Factor baja)
3. Revisa línea 1955: ¿bess_soc < 0.3? (Sin energia para descargar)
```

### Problema: MALL emite mucho CO2?
```
1. Revisa línea 1971: mall_co2_indirect_kg [h]
2. Revisa línea 2221: episode_co2_mall_emitido_kg muy alto
3. Incentiva: Poner más solar → pv_to_mall en línea 1903
```

### Problema: Solar no reduce CO2?
```
1. Revisa línea 1900: ¿reduccion_indirecta_co2_kg_total[h] = 0?
2. Revisa línea 1910: ¿energy_flows['pv_to_ev_kwh'] = 0?
3. Revisa línea 1915: ¿energy_flows['pv_to_bess_kwh'] = 0?
4. Revisa línea 1903: ¿pv_to_mall_kwh = 0?
```

---

## 📈 MÉTRICAS CLAVE A MONITOREAR

```
Monitor estos en TensorBoard:
  - episode_co2_directo_evitado_kg       (debe crecer)
  - episode_co2_indirecto_solar_kg       (debe crecer)
  - episode_co2_indirecto_bess_kg        (debe crecer)
  - episode_co2_mall_emitido_kg          (debe decrecer)
  - episode_co2_grid_kg                  (debe decrecer)
  - episode_reward                       (debe crecer)
  - training/actor_loss                  (debe decrecer)
  - training/critic_loss                 (debe decrecer)
```

---

## 🚀 FLUJO RÁPIDO: HORA h → CO2

```
h = horario actual (0-8759)

1. Línea 1872: co2_directo_evitado_kg = chargers_data['reduccion_directa_co2_kg'][h]
2. Línea 1890: co2_indirecto_solar_kg = solar_data['reduccion_indirecta_co2_kg_total'][h]
3. Línea 1930: co2_indirecto_bess_kg = energy_flows['bess_to_ev_kwh'][h] × factor
4. Línea 1967: co2_mall_emitido_kg = mall_data['mall_co2_indirect_kg'][h]
5. Línea 1984: co2_grid_kg = (grid_import × 0.4521)
6. Línea 2125: co2_component = -grid_import × 0.45  ← REWARD
7. Línea 2216: Acumular todos en episode_co2_*_kg
```

---

## 📝 ANOTACIONES PERSONALES

Aquí puedes agregar tus propias notas mientras estudias el código:

```
Línea 1944: Peak shaving factor
  - Si mall > 2000 kW: factor sube a 1.5 (BESS es crítico)
  - Si mall < 2000 kW: factor baja a 0.5 (BESS menos crítico)
  - Objetivo: Incentivar descarga de BESS en emergencias

Línea 1976-1983: MALL EMITE
  - mall_co2_indirect[h] = demand sin cubrir × 0.4521
  - Diferencia vs REDUCCION: MALL siempre emite (no reduce)
  - Si solar cubre mall → co2_indirecto_solar sube
  - Si grid cubre mall → co2_mall_emitido sube

Línea 2125: Reward CO2
  - grid_import = 0 → reward = 0 (óptimo)
  - grid_import = 1500 → reward = -0.45 (malo)
  - Penaliza importacion de grid (= penaliza CO2 indirectamente)
```

---

**Última Actualización:** 2026-02-15
**Archivo Base:** train_sac_multiobjetivo.py (v7.1)
**Líneas Clave:** 726-851, 1850-2300
**Estado:** ✅ ESTRUCTURA VERIFICADA Y CORRECTA
