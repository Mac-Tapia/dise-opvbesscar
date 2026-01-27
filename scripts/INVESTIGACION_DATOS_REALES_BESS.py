#!/usr/bin/env python3
"""🔍 INVESTIGACIÓN: Encontrar valores REALES de BESS desde OE2.
Tenemos MÚLTIPLES valores diferentes. Este script investiga.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

print("\n" + "="*90)
print("🔍 INVESTIGACIÓN: VALORES REALES DE BESS DE OE2")
print("="*90)

# ============================================================================
# FUENTE 1: bess_config.json (Especificación del producto)
# ============================================================================
logger.info("\n📄 [FUENTE 1] bess_config.json - Especificación técnica del BESS")
logger.info("   Ubicación: data/interim/oe2/bess/bess_config.json")
logger.info("   Tipo: Especificación del producto (Eaton Xpert 1670)")

try:
    bess_config: Dict[str, Any] = json.load(open("data/interim/oe2/bess/bess_config.json"))
    logger.info(f"   ✅ Capacidad: {bess_config.get('capacity_kwh')} kWh")
    logger.info(f"   ✅ Potencia: {bess_config.get('power_kw')} kW")
    efficiency_val = bess_config.get('roundtrip_efficiency', bess_config.get('efficiency', 0))
    logger.info(f"   ✅ Eficiencia: {efficiency_val * 100:.0f}%")
    logger.info(f"   ✅ C-rate: {bess_config.get('c_rate', 'N/A')}")
    bess_config_data = bess_config
except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")
    bess_config_data: Dict[str, Any] = {}

# ============================================================================
# FUENTE 2: bess_results.json (Cálculo OE2 dimensionamiento)
# ============================================================================
logger.info("\n📊 [FUENTE 2] bess_results.json - Cálculo de DIMENSIONAMIENTO OE2")
logger.info("   Ubicación: data/interim/oe2/bess/bess_results.json")
logger.info("   Tipo: Resultado del cálculo de dimensionamiento OE2")

try:
    bess_results: Dict[str, Any] = json.load(open("data/interim/oe2/bess/bess_results.json"))
    logger.info(f"   ✅ Capacidad CALCULADA: {bess_results.get('capacity_kwh', 'N/A')} kWh")
    logger.info(f"   ✅ Potencia CALCULADA: {bess_results.get('nominal_power_kw', 'N/A'):.2f} kW")
    logger.info(f"   ✅ C-rate usado: {bess_results.get('c_rate', 'N/A')}")
    logger.info(f"   ✅ DoD: {bess_results.get('dod', 'N/A')}")
    logger.info(f"   ℹ️ Nota: Este es el cálculo OE2 con EV como carga principal")
    bess_results_data = bess_results
except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")
    bess_results_data: Dict[str, Any] = {}

# ============================================================================
# FUENTE 3: default.yaml (Configuración de pipeline)
# ============================================================================
logger.info("\n⚙️ [FUENTE 3] default.yaml - Configuración del pipeline")
logger.info("   Ubicación: configs/default.yaml")
logger.info("   Tipo: Parámetros de ejecución OE3")

import yaml
try:
    with open("configs/default.yaml") as f:
        config: Dict[str, Any] = yaml.safe_load(f)
    bess_cfg = config.get('oe2', {}).get('bess', {})
    logger.info(f"   ✅ Capacidad YAML: {bess_cfg.get('fixed_capacity_kwh')} kWh")
    logger.info(f"   ✅ Potencia YAML: {bess_cfg.get('fixed_power_kw')} kW")
    logger.info(f"   ⚠️ NOTA: Estos parámetros controlan OE2 dentro del pipeline")
    bess_yaml_data = bess_cfg
except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")
    bess_yaml_data: Dict[str, Any] = {}

# ============================================================================
# FUENTE 4: schema.json (Configuración CityLearn actual)
# ============================================================================
logger.info("\n🏗️ [FUENTE 4] schema.json - Schema CityLearn actual")
logger.info("   Ubicación: data/processed/citylearn/iquitos_ev_mall/schema.json")
logger.info("   Tipo: Schema usado en simulación OE3")

try:
    schema_data: Dict[str, Any] = json.load(open("data/processed/citylearn/iquitos_ev_mall/schema.json"))
    bess_schema_data = schema_data['buildings']['Mall_Iquitos']['electrical_storage']['attributes']
    logger.info(f"   ✅ Capacidad SCHEMA: {bess_schema_data.get('capacity')} kWh")
    logger.info(f"   ✅ Potencia SCHEMA: {bess_schema_data.get('power_output_nominal')} kW")
except Exception as e:
    logger.error(f"   ❌ ERROR: {e}")
    bess_schema_data: Dict[str, Any] = {}

# ============================================================================
# ANÁLISIS: ¿QUÉ ES CORRECTO?
# ============================================================================
logger.info("\n" + "="*90)
logger.info("📋 ANÁLISIS: IDENTIFICAR EL VALOR CORRECTO")
logger.info("="*90)

print("\n┌─ COMPARACIÓN DE VALORES:")
print("│")
print(f"│ BESS CONFIG      (Producto):      {bess_config_data.get('capacity_kwh', 'N/A'):.0f} kWh / {bess_config_data.get('power_kw', 'N/A'):.0f} kW")
print(f"│ BESS RESULTS     (OE2 calc):      {bess_results_data.get('capacity_kwh', 'N/A'):.0f} kWh / {bess_results_data.get('nominal_power_kw', 'N/A'):.1f} kW")
print(f"│ BESS YAML        (Pipeline):      {bess_yaml_data.get('fixed_capacity_kwh', 'N/A'):.0f} kWh / {bess_yaml_data.get('fixed_power_kw', 'N/A'):.0f} kW")
print(f"│ BESS SCHEMA      (CityLearn):     {bess_schema_data.get('capacity', 'N/A'):.0f} kWh / {bess_schema_data.get('power_output_nominal', 'N/A'):.0f} kW")
print("│")

# ============================================================================
# CONCLUSIÓN: QUÉ DEBE SER LA VERDAD
# ============================================================================
logger.info("\n" + "="*90)
logger.info("✅ CONCLUSIÓN: VALOR REAL QUE DEBE USARSE")
logger.info("="*90)

logger.info("""
Análisis de FUENTES REALES:

1. bess_config.json (Especificación técnica):
   • Fuente: Especificación del dispositivo Eaton Xpert 1670
   • Capacidad: 2,000 kWh
   • Potencia: 1,200 kW
   • Confiabilidad: ✅ MÁXIMA (es el dispositivo real)

2. bess_results.json (Cálculo OE2):
   • Fuente: Cálculo de dimensionamiento basado en demanda
   • Capacidad: 1,632 kWh
   • Potencia: 593.45 kW
   • Confiabilidad: ✅ ALTA (es el cálculo energético)

3. default.yaml (Pipeline):
   • Fuente: Configuración de ejecución
   • Capacidad: 4,520 kWh ⚠️ CARRYOVER DE OE2 (INCORRECTO)
   • Potencia: 2,712 kW ⚠️ CARRYOVER DE OE2 (INCORRECTO)
   • Confiabilidad: ❌ BAJA (valores obsoletos)

4. schema.json (CityLearn):
   • Fuente: Schema de simulación
   • Capacidad: 2,000 kWh (correcto)
   • Potencia: 1,200 kW (el usuario dice que INCORRECTO)
   • Confiabilidad: ❓ A VERIFICAR

─────────────────────────────────────────────────────────────────────────

🎯 DECISIÓN TÉCNICA - ¿QUÉ USAR EN OE3 (CityLearn)?

OE3 es la simulación de CONTROL, no de dimensionamiento.
Por lo tanto, debe usar:

✅ CAPACIDAD: 2,000 kWh (especificación del producto instalado)
✅ POTENCIA: 1,200 kW (capacidad del dispositivo)

RAZÓN:
- El dispositivo Eaton Xpert 1670 tiene esos valores
- Son los valores que CityLearn debe simular
- No debemos cambiar valores en OE3 por nuevos cálculos de OE2

❌ NO USAR bess_results.json:
- Esos valores son para DIMENSIONAMIENTO (OE2)
- OE3 ya tiene un BESS instalado, no está dimensionando uno nuevo

❌ NO USAR default.yaml (4520/2712):
- Son carryovers obsoletos de OE2
- NO son los valores del dispositivo real

─────────────────────────────────────────────────────────────────────────

PERO EL USUARIO DICE QUE 1200 kW NO ES CORRECTO...

Necesitamos verificar:
1. ¿Cuál es la POTENCIA REAL del Eaton Xpert 1670?
2. ¿De dónde viene el valor 1200 kW?
3. ¿Qué valores están en otros archivos de configuración?

""")

# ============================================================================
# VERIFICACIÓN: Buscar más fuentes
# ============================================================================
logger.info("\n" + "="*90)
logger.info("🔎 BÚSQUEDA: Otros archivos de configuración")
logger.info("="*90)

# Buscar en schema_oe2
try:
    oe2_schema = json.load(open("data/oe2/citylearn/bess_schema_params.json"))
    logger.info(f"\n📄 bess_schema_params.json:")
    logger.info(f"   Capacidad: {oe2_schema.get('capacity')} kWh")
    logger.info(f"   Potencia: {oe2_schema.get('nominal_power')} kW")
except:
    pass

# Buscar en bess_config más antiguo
try:
    bess_old = json.load(open("data/oe2/bess_dimensionamiento_schema.json"))
    logger.info(f"\n📄 bess_dimensionamiento_schema.json:")
    logger.info(f"   Capacidad: {bess_old.get('capacity')} kWh")
    logger.info(f"   Potencia: {bess_old.get('nominal_power')} kW")
except:
    pass

logger.info("\n" + "="*90)
logger.info("✅ INVESTIGACIÓN COMPLETADA")
logger.info("="*90)
logger.info("""
RECOMENDACIÓN PARA EL USUARIO:

1. ¿Cuál es el DISPOSITIVO real instalado en Iquitos?
   - Si es Eaton Xpert 1670: 2000 kWh / 1200 kW
   - Si es otro: verificar especificaciones

2. ¿Cuáles son los requisitos de OE3?
   - ¿Simular el BESS existente (2000/1200)?
   - ¿O simular nuevo BESS del cálculo OE2 (1632/593)?

3. Decidir la FUENTE DE VERDAD:
   - bess_config.json (producto instalado)
   - bess_results.json (dimensionamiento)
   - O valor completamente nuevo

Luego actualizar TODAS las referencias consistentemente.
""")
