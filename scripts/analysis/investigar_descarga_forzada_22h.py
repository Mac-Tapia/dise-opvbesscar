"""
INVESTIGACION: ¿Por qué el SOC no baja hasta 20% a las 22h?

Según la lógica de BESS definida en bess.py:
- Restricción de cierre: SOC EXIGIDO a las 22h = exactamente 20% (soc_min)
- Descarga forzada a soc_min si no se alcanza naturalmente

Pero los datos muestran:
- SOC a las 22h: ~69% (promedio)
- SOC esperado: 20% (mínimo requerido)
- Diferencia: 49% (785 kWh) no descargado

¿QUE PASÓ?
1. ¿Bug en simulate_bess_solar_priority() - NO aplica descarga forzada?
2. ¿Bug en balance.py - Lee columna incorrecta del CSV?
3. ¿El CSV bess_ano_2024.csv tiene valores incorrectos?

VERIFICACION:
"""
import pandas as pd
import numpy as np
from pathlib import Path

print("\n" + "="*80)
print("VERIFICACION: SOC A LAS 22h - ¿20% o 69%?")
print("="*80)

# Cargar CSV BESS
bess_csv = Path("data/oe2/bess/bess_ano_2024.csv")
df_bess = pd.read_csv(bess_csv)

print(f"\n[OK] Cargado CSV BESS: {len(df_bess)} registros")
print(f"Columnas: {list(df_bess.columns)}\n")

# Extraer columna SOC del BESS
soc_col = None
for col in ['soc_percent', 'bess_soc_percent', 'SOC_%']:
    if col in df_bess.columns:
        soc_col = col
        break

if soc_col is None:
    print(f"ERROR: No se encontró columna SOC en BESS CSV")
    print(f"Columnas disponibles: {list(df_bess.columns)}")
    exit(1)

print(f"Usando columna SOC: {soc_col}\n")

# Añadir hora del día
df_bess['hour'] = df_bess.index % 24

# Analizar SOC a las 22h para cada día
print("-"*80)
print("SOC A LAS 22h (Hora de cierre) - Primeros 30 días")
print("-"*80)
print(f"{'DIA':<5} {'SOC 22h':<10} {'DISTANCIA A 20%':<20} {'ESPERADO':<10}")
print("-"*80)

soc_cierre_22h = []
for day in range(min(30, 365)):
    idx_22h = day * 24 + 22
    if idx_22h < len(df_bess):
        soc_val = df_bess[soc_col].iloc[idx_22h]
        distancia = soc_val - 20.0
        soc_cierre_22h.append(soc_val)
        
        # Clasificar si es correcto
        if abs(soc_val - 20) < 1:
            estado = "✅ CORRECTO"
        else:
            estado = "❌ INCORRECTO"
        
        print(f"{day+1:<5} {soc_val:>8.2f}% {distancia:>18.2f}% {estado:<10}")

# Estadísticas anuales
print("\n" + "-"*80)
print("ESTADISTICAS ANUALES - SOC A LAS 22h")
print("-"*80)

all_soc_22h = []
for day in range(365):
    idx_22h = day * 24 + 22
    if idx_22h < len(df_bess):
        soc_val = df_bess[soc_col].iloc[idx_22h]
        all_soc_22h.append(soc_val)

all_soc_22h = np.array(all_soc_22h)

print(f"Promedio SOC @ 22h:     {all_soc_22h.mean():.2f}%")
print(f"Mínimo SOC @ 22h:       {all_soc_22h.min():.2f}%")
print(f"Máximo SOC @ 22h:       {all_soc_22h.max():.2f}%")
print(f"Esperado:               20.00%")
print(f"DISTANCIA PROMEDIO:     {all_soc_22h.mean() - 20:.2f}%")
print(f"\n❌ PROBLEMA IDENTIFICADO:")
print(f"   El BESS NO está siendo descargado hasta 20% a las 22h")
print(f"   Está descargando {all_soc_22h.mean() - 20:.2f}% MENOS de lo que debería")

# Investigar la curva completa de un día
print("\n" + "="*80)
print("ANALISIS DETALLADO: DIA 1 - Curva completa 24h")
print("="*80)
print(f"{'H':<3} {'SOC%':<8} {'CAMBIO':<10} {'DESCRIPCION':<30}")
print("-"*80)

for h in range(24):
    idx = 0 * 24 + h  # Día 1
    soc_val = df_bess[soc_col].iloc[idx]
    
    if h > 0:
        soc_prev = df_bess[soc_col].iloc[idx-1]
        cambio = soc_val - soc_prev
    else:
        cambio = 0
    
    # Clasificar
    if h in range(6, 18):
        desc = "⬆️  Horas de carga PV"
    elif h in range(18, 23):
        desc = "🔋 Horas de descarga (crisis solar)"
    else:
        desc = "➡️  Horas reposo nocturno"
    
    if h == 22:
        desc = f"🔴 CIERRE CRITICO @ 22h: {soc_val:.2f}% (espera: 20%)"
    
    print(f"{h:<3} {soc_val:>6.1f}% {cambio:>8.2f}% {desc:<30}")

# Comparar con expected
print("\n" + "="*80)
print("DIAGNOSIS: ¿Qué falta?")
print("="*80)

expected_closing_soc = 20.0
actual_closing_soc = all_soc_22h.mean()
missing_discharge = actual_closing_soc - expected_closing_soc

print(f"""
La lógica de BESS en bess.py define:
  "RESTRICCION DE CIERRE: SOC EXIGIDO a las 22h = exactamente 20%"

Pero los datos muestran:
  SOC Real @ 22h:     {actual_closing_soc:.2f}%
  SOC Esperado @ 22h: {expected_closing_soc:.2f}%
  
  ENERGIA NO DESCARGADA: {missing_discharge:.2f}% 
                        = {missing_discharge * 1700 / 100:.1f} kWh

POSIBLES CAUSAS:
1. ❓ simulate_bess_solar_priority() NO está aplicando 
     la descarga forzada a 20% en la hora 22
     
2. ❓ El código que debería forzar descarga hasta 20% 
     está desactivado o tiene un bug
     
3. ❓ La descarga que debería ocurrir en horas 18-22 
     no es suficiente para llegar a exactamente 20%

ACCION REQUERIDA:
- Revisar simulate_bess_solar_priority() líneas ~1700-1800
- Buscar código de "descarga forzada" o "enforce_soc_min"
- Verificar si se ejecuta en hora 22
- Si no existe, implementar lógica de descarga forzada

""")

print("="*80)
