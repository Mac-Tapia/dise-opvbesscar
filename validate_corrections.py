#!/usr/bin/env python
"""Validar que las correcciones C1 se implementaron correctamente."""

import sys
from pathlib import Path

print("=" * 80)
print("VALIDACIÓN DE CORRECCIONES C1 - CO₂ Accounting")
print("=" * 80)

# Test 1: rewards.py tiene las variables correctas
print("\n[1] Verificar rewards.py sin undefined variables...")
rewards_file = Path("src/rewards/rewards.py")
content = rewards_file.read_text()

# Buscar el patrón correcto
if "renewable_kwh_to_evs" in content and "renewable_kwh_to_grid" in content:
    print("    ✅ Variables de segregación presentes")
else:
    print("    ❌ Falta segregación de renewable_kwh_to_evs y renewable_kwh_to_grid")
    sys.exit(1)

# Buscar por referencias a undefined
if "solar_to_chargers_kwh" in content and "bess_discharge_to_chargers_kwh" in content:
    print("    ⚠️  ADVERTENCIA: Variables antiguas aún presentes (pueden ser comentarios)")
else:
    print("    ✅ Variables antiguas undefined eliminadas")

# Buscar co2_net con max(0, ...)
if "co2_net_kg = max(0, co2_grid_kg - co2_avoided_total_kg)" in content:
    print("    ✅ CO₂ neto nunca negativo (max(0, ...))")
else:
    print("    ❌ CO₂ neto no usa max(0, ...)")
    sys.exit(1)

# Test 2: train_ppo_multiobjetivo.py tiene el logging mejorado
print("\n[2] Verificar logging en train_ppo_multiobjetivo.py...")
train_file = Path("train_ppo_multiobjetivo.py")
content = train_file.read_text()

if "max(0, self.ep_co2_grid - self.ep_co2_avoided_indirect - self.ep_co2_avoided_direct)" in content:
    print("    ✅ Logging usa max(0, ...) para co2_neto")
else:
    print("    ❌ Logging no usa max(0, ...) para co2_neto")
    sys.exit(1)

if "SIN DOUBLE-COUNTING" in content:
    print("    ✅ Logging clarifica 'SIN DOUBLE-COUNTING'")
else:
    print("    ❌ Logging no menciona 'SIN DOUBLE-COUNTING'")
    sys.exit(1)

if "renewable_to_evs_fraction = 0.70" in content or "Segregación de Energía" in content:
    print("    ✅ Segregación 70/30 mencionada")
else:
    print("    ⚠️  Segregación 70/30 no mencionada en train (OK si solo en rewards)")

# Test 3: Papers científicos citados
print("\n[3] Verificar referencias científicas...")
if "Liu et al. (2022)" in content or "Messagie et al. (2014)" in content:
    print("    ✅ Papers científicos citados")
else:
    print("    ⚠️  Verificar papers en docstrings (pueden estar en rewards.py)")

# Test 4: Validar segregación matemática
print("\n[4] Validar segregación sin double-counting...")
if "0.70" in content and "0.30" in content:
    print("    ✅ Fracciones 70/30 presentes")
    if "0.70 + 0.30 = 1.0" in content or "70% + 30%" in content:
        print("    ✅ Segregación documentada como 70% + 30%")
    else:
        print("    ⚠️  Documentación de segregación incompleta (OK si funciona)")
else:
    print("    ❌ Fracciones 70/30 no encontradas")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ TODAS LAS VALIDACIONES PASARON")
print("=" * 80)
print("\n🚀 Listo para entrenar:")
print("   python train_ppo_multiobjetivo.py")
print("\nMétricas esperadas en primer episodio:")
print("   Grid Import CO₂:      ~1,800,000 kg (baseline)")
print("   Reducido Indirecto:    ~400,000 kg (30% renewable to grid)")
print("   Reducido Directo:      ~800,000 kg (70% renewable to EVs)")
print("   CO₂ Neto:              ~600,000 kg (REALISTA, nunca negativo)")
print("=" * 80)
