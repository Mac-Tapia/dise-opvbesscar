#!/usr/bin/env python3
"""Elimina archivos no usados - versión simplificada"""
import shutil
from pathlib import Path
import sys

try:
    base = Path("data/processed/citylearn/iquitos_ev_mall")
    deleted_count = 0
    
    # Eliminar 38 socket_simulation files
    for i in range(1, 129):
        f = base / f"charger_simulation_{i:03d}.csv"
        try:
            f.unlink()
            deleted_count += 1
        except:
            pass
    
    # Eliminar schema variants
    for f in [base / "schema_grid_only.json", base / "schema_pv_bess.json"]:
        try:
            f.unlink()
            deleted_count += 1
        except:
            pass
    
    # Escribir resultado en archivo para confirmar
    with open("CLEANUP_RESULT.txt", "w") as log:
        log.write(f"Archivos eliminados: {deleted_count}\n")
        log.write(f"Status: {'OK' if deleted_count == 130 else 'PARCIAL'}\n")
        
        # Verificar críticos
        critical = [
            "Generacionsolar/pv_generation_hourly_citylearn_v2.csv",
            "chargers/chargers_real_hourly_2024.csv",
            "chargers/chargers_real_statistics.csv",
            "demandamallkwh/demandamallhorakwh.csv",
            "electrical_storage_simulation.csv",
            "schema.json",
        ]
        
        all_ok = True
        for c in critical:
            exists = (base / c).exists()
            status = "OK" if exists else "FALTA"
            log.write(f"{c}: {status}\n")
            if not exists:
                all_ok = False
        
        log.write(f"\nCríticos: {'OK' if all_ok else 'ERROR'}\n")
    
    sys.exit(0)
except Exception as e:
    with open("CLEANUP_RESULT.txt", "w") as log:
        log.write(f"Error: {str(e)}\n")
    sys.exit(1)
