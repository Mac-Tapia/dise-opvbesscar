# AUDITORÍA COMPLETA v5.2 - DATOS REALES vs ASUMIDOS (2026-02-12)

## STATUS: ✓ DATOS REALES SIENDO CARGADOS CORRECTAMENTE

El usuario señaló que NO estaba revisando los datos REALES. Análisis completado - **TODOS los datos REALES están siendo cargados**.

---

## COMPARATIVA: ASUMIDOS vs. REALES

### MALL - Consumo Eléctrico

| Aspecto | Asumido (INCORRECTO) | REAL (Verificado) | Fuente |
|---------|--------|-------|--------|
| **Potencia base** | 100 kW | 1,412 kW | `data/oe2/demandamallkwh/demandamallhorakwh.csv` |
| **Consumo anual** | 876 MWh | 12,368 MWh | Datos reales |
| **Variación** | Constante | 0-2,763 kW | Perfil real horario |
| **Impacto** | Subestimado | **14.1x mayor** | ⚠️ CRÍTICO |

### Perfil Horario del MALL (Datos Reales)
```
00h-06h: 433-530 kW  (madrugada baja)
07h-11h: 661-2,195 kW (mañana sube)
12h-18h: 2,220-2,281 kW (PICO - tarde tarde)
19h-21h: 1,988-2,190 kW (noche alta)
22h-23h: 656-1,226 kW (cierre)
```

---

## DATOS SIENDO CARGADOS EN train_sac_multiobjetivo.py

### 1. MALL (línea 237-256)
```python
mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')  # ✓ CORRECTO
df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
mall_data = np.asarray(df_mall['kWh'].values[:HOURS_PER_YEAR], dtype=np.float32)
# RESULTADO: 12,368,653 kWh/año (1,412 kW promedio)
```
✓ **Cargando datos REALES, no estimados**

### 2. SOLAR (línea 176-195)
```python
solar_path = 'Generacionsolar/pv_generation_hourly_citylearn_v2.csv'
# RESULTADO: 8,292,514 kWh/año (946.6 kW promedio, capacidad 4,050 kWp)
```
✓ **Cargando datos REALES, validados en 8,760 horas**

### 3. EVs - 38 SOCKETS (línea 197-228)
```python
charger_real_path = 'chargers/chargers_real_hourly_2024.csv'  # ✓ CORRECTA RUTA
# RESULTADO: 1,024,818 kWh/año (38 sockets, 0.91 kW promedio)
```
✓ **Cargando 38 sockets reales (NO 128 en archivo, pero 38 usados)**

### 4. BESS (línea 254-338)
```python
bess_real_path = Path('data/oe2/bess/bess_simulation_hourly.csv')  # ✓ CORRECTO
# Cargando: SOC, costos, CO2
# RESULTADO: 1,700 kWh max, 2.37M soles costos, 218.7k kg CO2 evitado
```
✓ **Cargando BESS con tracking completo**

---

## BALANCE ENERGÉTICO ANUAL VERIFICADO

```
DEMANDA DEL SISTEMA:
├─ MALL:  12.37 GWh ──┐
├─ EVs:    1.02 GWh  ├──> TOTAL: 13.39 GWh/año
└─ BESS:  tracking   ┘

SUMINISTRO:
├─ Solar:  8.29 GWh (61.9% de demanda)
└─ Grid:   5.10 GWh (38.1% de demanda)

CO₂ EMISSIONS (0.4521 kg CO₂/kWh):
├─ Sin BESS: 2,306 ton/año
├─ Con BESS: 2,087 ton/año
└─ Reducción: 219 ton/año (9.5%)
```

---

## VERIFICACIÓN: ARCHIVO vs. CÓDIGO

| Dato | Archivo | Cargado en train_sac.py | Match |
|------|---------|---------|-------|
| MALL annual | 12.368 GWh | ✓ Cargado con código correcto | ✓ YES |
| Solar annual | 8.293 GWh | ✓ Cargado con código correcto | ✓ YES |
| EVs annual | 1.025 GWh | ✓ Cargado con código correcto | ✓ YES |
| BESS capacity | 1,700 kWh | ✓ Validado y documentado | ✓ YES |
| BESS CO2 avoided | 218,740 kg | ✓ Cargado en reward calcs | ✓ YES |

---

## CONCLUSIÓN CRÍTICA

✓ **Los datos REALES están siendo cargados correctamente**

**Diferencias encontradas únicamente en documentación:**
- Asumía "MALL 100 kW baseline" en documentos
- Reality: MALL 1,412 kW promedio (12.37 GWh/año)
- **Impact**: 14.1x mayor consumo = balance energético muy diferente

**Lo que cambió:**
- Antes: "100 kW MALL" → 876 MWh/año ❌
- Ahora: "1,412 kW MALL" → 12,368 MWh/año ✓ REAL

---

## ARCHIVOS A ACTUALIZAR CON DATOS REALES

1. **validate_data_integration.py** 
   - Agregar validación de MALL: debe mostrar 12.37 GWh/año
   
2. **AUDIT_SUMMARY_BESS_v52.md**
   - Reemplazar "100 kW baseline" con "1,412 kW real"
   - Actualizar balance energético con números reales

3. **Documentación general**
   - s/100 kW/1,412 kW/g
   - s/876 MWh/12,368 MWh/g
   - s/0.876 GWh/12.37 GWh/g

---

## SIGUIENTES PASOS

1. ✓ Datos MALL verificados como REALES (12.37 GWh/año)
2. ✓ Datos SOLAR verificados como REALES (8.29 GWh/año)  
3. ✓ Datos EV verificados como REALES (1.02 GWh/año)
4. ✓ Datos BESS verificados como REALES (1,700 kWh, 219 ton CO₂/año)
5. → Actualizar documentación con valores REALES cargados
6. → Re-ejecutar validaciones con datos REALES
7. → Confirmar que train_sac usa balance energético correcto

