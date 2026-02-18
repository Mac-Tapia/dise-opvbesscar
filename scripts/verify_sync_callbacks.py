#!/usr/bin/env python3
"""
RESUMEN EJECUTIVO - FIX CALLBACKS SAC/A2C v2.0
================================================

Comparativo antes/después de las modificaciones realiz adas en callbacks SAC y A2C
para sincronizar con PPO (33 columnas timeseries, 22 columnas trace).
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

print("="*100)
print("RESUMEN EJECUTIVO: SINCRONIZACIÓN SAC/A2C CON PPO CALLBACKS")
print("="*100)
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ===== ESTADO ACTUAL DE LOS ARCHIVOS =====
outputs_dir = Path("outputs")

print("[1] ESTADO ACTUAL DE ARCHIVOS CSV GENERADOS")
print("-"*100)

datasets_info = {
    "PPO": {
        "timeseries": "ppo_training/timeseries_ppo.csv",
        "trace": "ppo_training/trace_ppo.csv",
    },
    "SAC": {
        "timeseries": "sac_training/timeseries_sac.csv",
        "trace": "sac_training/trace_sac.csv",
    },
    "A2C": {
        "timeseries": "a2c_training/timeseries_a2c.csv",
        "trace": "a2c_training/trace_a2c.csv",
    }
}

table_data = []
for agent, files in datasets_info.items():
    for csv_type, path in files.items():
        full_path = outputs_dir / path
        if full_path.exists():
            df = pd.read_csv(full_path)
            n_cols = len(df.columns)
            n_rows = len(df)
            size_mb = full_path.stat().st_size / 1024 / 1024
            table_data.append({
                "Agent": agent,
                "Tipo": csv_type,
                "Columnas": n_cols,
                "Filas": n_rows,
                "Tamaño (MB)": f"{size_mb:.2f}",
                "Estado": "✅" if n_cols >= (33 if csv_type == "timeseries" else 22) else "❌",
            })
        else:
            table_data.append({
                "Agent": agent,
                "Tipo": csv_type,
                "Columnas": "N/A",
                "Filas": "N/A",
                "Tamaño (MB)": "N/A",
                "Estado": "⚠️ No existe",
            })

df_table = pd.DataFrame(table_data)
print(df_table.to_string(index=False))
print()

# ===== CAMBIOS REALIZADOS =====
print("[2] CAMBIOS REALIZADOS EN ARCHIVOS PYTHON")
print("-"*100)

changes = [
    {
        "Archivo": "scripts/train/train_sac.py",
        "Línea": "~3814",
        "Tipo": "timeseries",
        "Antes": "8 COL",
        "Después": "33 COL",
        "Cambio": "+25 COL",
        "Estado": "✅ HECHO",
    },
    {
        "Archivo": "scripts/train/train_sac.py",
        "Línea": "~3793",
        "Tipo": "trace",
        "Antes": "11 COL",
        "Después": "22 COL",
        "Cambio": "+11 COL",
        "Estado": "✅ HECHO",
    },
    {
        "Archivo": "scripts/train/train_a2c.py",
        "Línea": "~2010",
        "Tipo": "timeseries",
        "Antes": "10 COL",
        "Después": "33 COL",
        "Cambio": "+23 COL",
        "Estado": "✅ HECHO",
    },
    {
        "Archivo": "scripts/train/train_a2c.py",
        "Línea": "~1992",
        "Tipo": "trace",
        "Antes": "13 COL",
        "Después": "22 COL",
        "Cambio": "+9 COL",
        "Estado": "✅ HECHO",
    },
]

df_changes = pd.DataFrame(changes)
print(df_changes.to_string(index=False))
print()

# ===== COLUMNAS SINCRONIZADAS =====
print("[3] COLUMNAS CRÍTICAS AGREGADAS")
print("-"*100)

critical_cols = {
    "SAC timeseries": [
        "✅ co2_grid_kg",
        "✅ co2_avoided_indirect_kg",
        "✅ co2_avoided_direct_kg",
        "✅ co2_avoided_total_kg",
        "✅ motos_charging",
        "✅ mototaxis_charging",
        "✅ ahorro_solar_soles",
        "✅ ahorro_bess_soles",
        "✅ costo_grid_soles",
        "✅ r_co2, r_solar, r_vehicles, r_bess, r_priority",
    ],
    "A2C timeseries": [
        "✅ co2_avoided_total_kg",
        "✅ motos_charging",
        "✅ mototaxis_charging",
        "✅ ahorro_solar_soles",
        "✅ ahorro_bess_soles",
        "✅ costo_grid_soles",
        "✅ r_co2, r_solar, r_vehicles, r_bess (y otros)",
    ],
}

for agent_type, cols in critical_cols.items():
    print(f"\n{agent_type}:")
    for col in cols:
        print(f"  {col}")

print()

# ===== VALIDACIÓN =====
print("[4] VALIDACIÓN DE CAMBIOS")
print("-"*100)

try:
    import py_compile
    files_to_check = [
        "scripts/train/train_sac.py",
        "scripts/train/train_a2c.py",
    ]
    
    for file in files_to_check:
        try:
            py_compile.compile(file, doraise=True)
            print(f"✅ {file}: Compilación OK (sin errores de sintaxis)")
        except py_compile.PyCompileError as e:
            print(f"❌ {file}: ERROR - {str(e)[:80]}")
except Exception as e:
    print(f"⚠️ No se pudo validar compilación: {str(e)[:80]}")

print()

# ===== RECOMENDACIONES =====
print("[5] PRÓXIMOS PASOS")
print("-"*100)
print("""
1. **Re-ejecutar entrenamientos** SAC y A2C con callbacks actualizados:
   python scripts/train/train_sac.py
   python scripts/train/train_a2c.py

2. **Verificar que nuevos CSVs tengan columnas correctas:**
   python scripts/verify_csv_columns.py

3. **Comparar métricas** entre SAC vs PPO vs A2C:
   python analyses/compare_agents_complete.py

4. **Validar gráficas** no tengan paneles vacíos:
   - Revisar outputs/sac_training/dashboard_kpi.png
   - Revisar outputs/a2c_training/dashboard_kpi.png
   - Comparar con outputs/ppo_training/dashboard_kpi.png

5. **Generar reporte final** de sincronización:
   - Documentar diferencias residuales si las hay
   - Proponer mejoras futuras
""")

print()
print("="*100)
print("FIN DE RESUMEN")
print("="*100)
