#!/usr/bin/env python
import pandas as pd
import json

# Cargar demanda mall
df = pd.read_csv("data/interim/oe2/demandamallkwh/demandamallkwh.csv", sep=";")
df.columns = ["timestamp", "kWh"]

# Extraer hora de timestamp
df['hora'] = pd.to_datetime(df['timestamp'], format='mixed', dayfirst=True).dt.hour

print("DEMANDA DEL MALL - PERFIL DE 24 HORAS")
print("="*80)
print()

# Perfil de 24 horas (promedio por hora del día)
perfil_24h = df.groupby('hora')['kWh'].agg(['mean', 'min', 'max', 'std']).round(1)
print("PERFIL DE CARGA DE 24 HORAS (promedio todas las fechas):")
print()
print(perfil_24h)
print()

valores_24h = df.groupby('hora')['kWh'].mean().sort_index()
print("VALORES DE 24 HORAS:")
print()
print("Hora | Demanda (kWh)")
print("─────┼──────────────")
for hora, demanda in valores_24h.items():
    print(f" {hora:2d}  | {demanda:8.1f}")
print()

# Guardar como JSON
perfil_dict = {
    "type": "mall_load_profile_24h",
    "unit": "kWh per hour",
    "values": {str(int(h)): float(round(v, 1)) for h, v in valores_24h.items()},
    "statistics": {
        "min": float(valores_24h.min()),
        "max": float(valores_24h.max()),
        "mean": float(valores_24h.mean()),
        "std": float(valores_24h.std())
    }
}

json_path = "data/interim/oe2/demandamallkwh/demandamallkwh_profile_24h.json"
with open(json_path, 'w') as f:
    json.dump(perfil_dict, f, indent=2)

print(f"✅ Guardado en: {json_path}")
print()
print(json.dumps(perfil_dict, indent=2))
