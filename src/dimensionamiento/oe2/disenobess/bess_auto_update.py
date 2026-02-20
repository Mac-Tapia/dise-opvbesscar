"""
DETECTOR AUTOMATICO DE CAMBIOS BESS

Este módulo se ejecuta automáticamente cuando se importa bess.py
y detecta si los parámetros han cambiado. Si cambiaron, regenera
automáticamente el dataset y los gráficos.
"""

import json
import hashlib
import subprocess
from pathlib import Path

# Archivo donde guardamos el "estado" anterior de parámetros
STATE_FILE = Path('data/.bess_state_cache.json')

PARAMS_TO_MONITOR = [
    ('BESS_CAPACITY_KWH_V53', 'src/dimensionamiento/oe2/disenobess/bess.py'),
    ('BESS_POWER_KW_V53', 'src/dimensionamiento/oe2/disenobess/bess.py'),
    ('BESS_SOC_MIN_V53', 'src/dimensionamiento/oe2/disenobess/bess.py'),
    ('BESS_SOC_MAX_V53', 'src/dimensionamiento/oe2/disenobess/bess.py'),
    ('BESS_DOD_V53', 'src/dimensionamiento/oe2/disenobess/bess.py'),
]

def read_bess_params():
    """Leer parámetros actuales de bess.py"""
    bess_file = Path(PARAMS_TO_MONITOR[0][1])
    
    if not bess_file.exists():
        return None
    
    with open(bess_file) as f:
        content = f.read()
    
    params = {}
    import re
    for param_name, _ in PARAMS_TO_MONITOR:
        pattern = f'{param_name}\\s*=\\s*([0-9.]+)'
        match = re.search(pattern, content)
        if match:
            params[param_name] = float(match.group(1))
    
    return params

def get_params_hash(params):
    """Calcular hash de parámetros para detectar cambios"""
    if not params:
        return None
    
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(params_str.encode()).hexdigest()

def save_state(params):
    """Guardar estado actual de parámetros"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(STATE_FILE, 'w') as f:
        json.dump({
            'params': params,
            'hash': get_params_hash(params)
        }, f, indent=2)

def load_state():
    """Cargar estado anterior guardado"""
    if not STATE_FILE.exists():
        return None
    
    with open(STATE_FILE) as f:
        return json.load(f)

def params_changed():
    """Detectar si los parámetros fueron modificados"""
    current_params = read_bess_params()
    if not current_params:
        return False
    
    previous_state = load_state()
    if not previous_state:
        save_state(current_params)
        return False
    
    current_hash = get_params_hash(current_params)
    previous_hash = previous_state.get('hash')
    
    return current_hash != previous_hash

def auto_regenerate():
    """Regenerar dataset y gráficos automáticamente si detectó cambios"""
    if not params_changed():
        return
    
    print("\n" + "="*80)
    print("🔔 DETECTOR AUTOMATICO: Se detectaron cambios en BESS")
    print("="*80)
    
    current_params = read_bess_params()
    print("\n📊 Parámetros detectados:")
    for param_name, value in current_params.items():
        if 'SOC' in param_name or 'DOD' in param_name:
            print(f"   • {param_name}: {value*100:.1f}%")
        else:
            print(f"   • {param_name}: {value:.0f}")
    
    print("\n⚙️  Regenerando automáticamente...")
    
    steps = [
        ("python scripts/transform_dataset_v57.py", "Transformar dataset"),
        ("python scripts/regenerate_graphics_v57.py", "Regenerar gráficos"),
        ("python verify_soc_min.py", "Validar integridad"),
    ]
    
    all_success = True
    for cmd, description in steps:
        print(f"\n  → {description}...", end=' ', flush=True)
        result = subprocess.run(cmd, shell=True, capture_output=True)
        if result.returncode == 0:
            print("✅")
        else:
            print("❌")
            all_success = False
    
    if all_success:
        # Guardar nuevo estado
        save_state(current_params)
        print("\n✅ Regeneración completada automáticamente")
        print("="*80 + "\n")
    else:
        print("\n❌ Hubo errores en la regeneración")
        print("="*80 + "\n")

# Ejecutar automáticamente al importar este módulo
if __name__ != '__main__':
    try:
        auto_regenerate()
    except Exception as e:
        # No interrumpir si hay error en detección
        pass
