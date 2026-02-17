#!/usr/bin/env python3
import time
from pathlib import Path

print("=" * 70)
print("MONITOREO SAC v9.1 - Verificando estado")
print("=" * 70)

sac_dir = Path("outputs/sac_training")

# Intentos de verificación
for attempt in range(1, 4):
    print(f"\nIntento {attempt}...")
    time.sleep(10)
    
    if sac_dir.exists():
        files = list(sac_dir.glob("*.csv"))
        if files:
            print(f"✓ Archivos encontrados: {len(files)}")
            for f in files:
                with open(f) as fp:
                    lines = len(fp.readlines())
                print(f"  {f.name}: {lines} líneas")
            print(f"\n✓ SAC v9.1 ENTRENANDO - {lines} pasos ejecutados")
            break
    else:
        print(f"  (Sin archivos aún)")
else:
    print("\n✗ No se detectan archivos después de 30 segundos")
    print("Revisar: scripts/train/train_sac_multiobjetivo.py")

print("\n" + "=" * 70)
