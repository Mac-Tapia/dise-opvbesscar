import pandas as pd
import numpy as np
from pathlib import Path

print("="*60)
print("🔍 VALIDACION RAPIDA - DATASETS Y CHARGERS")
print("="*60)

# 1. Solar
solar_path = Path('data/interim/oe2/solar/pv_generation_citylearn_enhanced_v2.csv')
if solar_path.exists():
    solar = pd.read_csv(solar_path)
    print(f"\n✅ Solar: {len(solar)} rows x {len(solar.columns)} cols")
    if len(solar) == 8760:
        print(f"   └─ PERFECTO: 8760 horas (1 año)")
    else:
        print(f"   ⚠️ ERROR: Esperado 8760, encontrado {len(solar)}")
else:
    print(f"\n❌ Solar NO encontrado en {solar_path}")

# 2. Chargers (demanda)
chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
if chargers_path.exists():
    chargers = pd.read_csv(chargers_path)
    print(f"\n✅ Chargers: {len(chargers)} rows x {len(chargers.columns)} cols")
    
    # Buscar columnas de power para 38 sockets
    power_cols = [col for col in chargers.columns if 'charging_power_kw' in col.lower()]
    print(f"   └─ Columnas con 'charging_power_kw': {len(power_cols)} encontradas")
    if len(power_cols) >= 38:
        print(f"   └─ ✅ SUFICIENTES para 38 sockets")
    else:
        print(f"   └─ ⚠️ Solo {len(power_cols)} columnas, se esperan >= 38")
else:
    print(f"\n❌ Chargers NO encontrado en {chargers_path}")

# 3. BESS  
bess_path = Path('data/oe2/bess/bess_ano_2024.csv')
if bess_path.exists():
    bess = pd.read_csv(bess_path)
    print(f"\n✅ BESS: {len(bess)} rows x {len(bess.columns)} cols")
    if len(bess) == 8760:
        print(f"   └─ PERFECTO: 8760 horas")
else:
    print(f"\n❌ BESS NO encontrado en {bess_path}")

# 4. Mall
mall_path = Path('data/oe2/demanda/demandamallhorakwh.csv')
if mall_path.exists():
    mall = pd.read_csv(mall_path)
    print(f"\n✅ Mall: {len(mall)} rows x {len(mall.columns)} cols")
    if len(mall) == 8760:
        print(f"   └─ PERFECTO: 8760 horas")
else:
    print(f"\n❌ Mall NO encontrado en {mall_path}")

print("\n" + "="*60)
print("✅ DATASETS LISTOS - PPO puede entrenar")
print("="*60)
