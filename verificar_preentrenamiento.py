#!/usr/bin/env python3
"""
VERIFICACION PRE-ENTRENAMIENTO
==============================

Antes de entrenar, verificar que TODO esté listo:
- Solar data: 8,760 rows, 8.03 GWh
- Chargers: 128 sockets configurados
- BESS: 2 MWh / 1.2 MW
- GPU: CUDA disponible
- Configs: default.yaml actualizado
"""

import sys
from pathlib import Path
import json
import pandas as pd  # type: ignore[import]
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        pass

def check_file(path, description):
    """Verificar que un archivo existe."""
    p = Path(path)
    if p.exists():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description}: {path} (NO ENCONTRADO)")
        return False

def check_solar_data():
    """Verificar datos solares 8,760 rows, 8.03 GWh."""
    solar_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    if not solar_path.exists():
        print("✗ Solar data: NO ENCONTRADO")
        return False

    try:
        df = pd.read_csv(solar_path)
        rows = len(df)
        annual_kwh = df.get('ac_power_kw', df.iloc[:, 1]).sum()

        checks = []
        if rows == 8760:
            print(f"  ✓ Filas: {rows} (correcto)")
            checks.append(True)
        else:
            print(f"  ✗ Filas: {rows} (esperado 8760)")
            checks.append(False)

        if 7_800_000 < annual_kwh < 8_300_000:  # 7.8-8.3 GWh
            print(f"  ✓ Generación anual: {annual_kwh/1e6:.2f} GWh (correcto)")
            checks.append(True)
        else:
            print(f"  ✗ Generación anual: {annual_kwh/1e6:.2f} GWh (esperado ~8.03 GWh)")
            checks.append(False)

        return all(checks)
    except Exception as e:
        print(f"✗ Error leyendo solar data: {e}")
        return False

def check_chargers():
    """Verificar 128 sockets (32 chargers × 4)."""
    chargers_path = Path("data/interim/oe2/chargers/individual_chargers.json")
    if not chargers_path.exists():
        print("✗ Chargers config: NO ENCONTRADO")
        return False

    try:
        with open(chargers_path) as f:
            data = json.load(f)

        num_chargers = len(data)
        sockets = num_chargers * 4

        if num_chargers == 32 and sockets == 128:
            print(f"✓ Chargers: {num_chargers} chargers = {sockets} sockets")
            return True
        else:
            print(f"✗ Chargers: {num_chargers} chargers = {sockets} sockets (esperado 32 × 4 = 128)")
            return False
    except Exception as e:
        print(f"✗ Error leyendo chargers: {e}")
        return False

def check_bess():
    """Verificar BESS 2 MWh / 1.2 MW."""
    bess_path = Path("data/interim/oe2/bess/bess_config.json")
    if not bess_path.exists():
        print("✗ BESS config: NO ENCONTRADO")
        return False

    try:
        with open(bess_path) as f:
            data = json.load(f)

        capacity = data.get('capacity_kwh', 0)
        power = data.get('max_power_kw', 0)

        checks = []
        if capacity == 2000:
            print(f"  ✓ Capacidad: {capacity} kWh (correcto)")
            checks.append(True)
        else:
            print(f"  ✗ Capacidad: {capacity} kWh (esperado 2000)")
            checks.append(False)

        if power == 1200:
            print(f"  ✓ Potencia: {power} kW (correcto)")
            checks.append(True)
        else:
            print(f"  ✗ Potencia: {power} kW (esperado 1200)")
            checks.append(False)

        return all(checks)
    except Exception as e:
        print(f"✗ Error leyendo BESS: {e}")
        return False

def check_gpu():
    """Verificar GPU CUDA disponible."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"✓ GPU: {gpu_name} ({vram_gb:.1f} GB VRAM)")
            return True
        else:
            print("✗ GPU: CUDA no disponible (training en CPU, MUCHO MÁS LENTO)")
            return False
    except Exception as e:
        print(f"✗ Error detectando GPU: {e}")
        return False

def check_configs():
    """Verificar configs/default.yaml actualizado."""
    config_path = Path("configs/default.yaml")
    if not config_path.exists():
        print("✗ Config: NO ENCONTRADO")
        return False

    try:
        import yaml  # type: ignore[import-untyped]
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        target = cfg.get('oe3', {}).get('target_annual_kwh', 0)
        if 8_000_000 < target < 8_100_000:
            print(f"✓ Config target_annual_kwh: {target} (correcto ~8.03 GWh)")
            return True
        else:
            print(f"✗ Config target_annual_kwh: {target} (esperado ~8,030,000)")
            return False
    except Exception as e:
        print(f"✗ Error leyendo config: {e}")
        return False

def check_python():
    """Verificar Python 3.11+."""
    ver = sys.version_info
    if ver.major == 3 and ver.minor >= 11:
        print(f"✓ Python: {ver.major}.{ver.minor}.{ver.micro} (correcto)")
        return True
    else:
        print(f"✗ Python: {ver.major}.{ver.minor} (requiere 3.11+)")
        return False

def check_venv():
    """Verificar que estamos en .venv."""
    try:
        venv_prefix = sys.prefix
        if ".venv" in venv_prefix or "venv" in venv_prefix:
            print(f"✓ Virtual env: {venv_prefix}")
            return True
        else:
            print(f"⚠ Virtual env: Posible no en .venv ({venv_prefix})")
            return True  # Warning, no fatal
    except Exception as e:
        print(f"⚠ Virtual env: {e}")
        return True

def check_dependencies():
    """Verificar librerías clave."""
    deps = ['torch', 'citylearn', 'stable_baselines3', 'pandas', 'numpy']
    missing = []

    for dep in deps:
        try:
            __import__(dep)
            print(f"  ✓ {dep}")
        except ImportError:
            print(f"  ✗ {dep} (NO INSTALADO)")
            missing.append(dep)

    if missing:
        print(f"\n  ❌ Faltan dependencias: {', '.join(missing)}")
        print(f"  Instalar con: pip install {' '.join(missing)}")
        return False
    return True

print("""
╔════════════════════════════════════════════════════════════════════════════╗
║            VERIFICACION PRE-ENTRENAMIENTO - CHECKLIST                     ║
╚════════════════════════════════════════════════════════════════════════════╝

[SISTEMA]
""")

# System checks
py_ok = check_python()
venv_ok = check_venv()

print("\n[DEPENDENCIAS]")
deps_ok = check_dependencies()

print("\n[DATOS OE2]")
solar_ok = check_solar_data()
chargers_ok = check_chargers()
bess_ok = check_bess()

print("\n[CONFIGURACION]")
config_ok = check_configs()

print("\n[GPU/CUDA]")
gpu_ok = check_gpu()

# Summary
print("\n" + "="*80)
print("RESUMEN:")
print("="*80)

checks = {
    "Python 3.11+": py_ok,
    "Virtual env": venv_ok,
    "Dependencias": deps_ok,
    "Solar data (8,760 rows, 8.03 GWh)": solar_ok,
    "Chargers (128 sockets)": chargers_ok,
    "BESS (2 MWh/1.2 MW)": bess_ok,
    "Config (target_annual_kwh=8.03M)": config_ok,
    "GPU CUDA": gpu_ok,
}

passed = sum(1 for v in checks.values() if v)
total = len(checks)

for check, result in checks.items():
    status = "✓" if result else "✗"
    print(f"  {status} {check}")

print(f"\n{passed}/{total} checks passed")

if passed == total:
    print("\n" + "="*80)
    print("✓✓✓ SISTEMA LISTO PARA ENTRENAR ✓✓✓")
    print("="*80)
    print("\nEjecutar con:")
    print("  python run_training_optimizado.py")
    print("\nO entrenar manualmente:")
    print("  python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5")
    sys.exit(0)
else:
    print("\n" + "="*80)
    print(f"❌ {total - passed} checks fallaron")
    print("="*80)
    print("\nFijas los problemas antes de entrenar:")

    if not solar_ok:
        print("  1. Regenerar solar: python regenerate_solar_oe2_hourly.py")
    if not chargers_ok:
        print("  2. Verificar chargers: python analizar_chargers_json.py")
    if not config_ok:
        print("  3. Actualizar configs/default.yaml con target_annual_kwh=8030119")
    if not gpu_ok:
        print("  4. Instalar CUDA/GPU drivers (o usar CPU si deseas)")

    sys.exit(1)
