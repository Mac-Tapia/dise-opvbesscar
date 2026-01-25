import json
from pathlib import Path

json_path = Path("data/interim/oe2/chargers/chargers_results.json")

if json_path.exists():
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    print("=" * 70)
    print("VERIFICACIÓN DE VALORES EN chargers_results.json")
    print("=" * 70)

    print("\n[+] CAPACIDAD DE INFRAESTRUCTURA (32 cargadores × 4 tomas = 128 tomas):")
    print(f"   Diario:   {data.get('capacidad_infraestructura_dia', 'NO ENCONTRADO'):,} vehículos")
    print(f"   Mensual:  {data.get('capacidad_infraestructura_mes', 'NO ENCONTRADO'):,} vehículos")
    print(f"   Anual:    {data.get('capacidad_infraestructura_anio', 'NO ENCONTRADO'):,} vehículos")
    print(f"   20 años:  {data.get('capacidad_infraestructura_20anios', 'NO ENCONTRADO'):,} vehículos")

    print("\n[+] POTENCIA INSTALADA (cargadores × tomas × potencia):")
    print(f"   Motos:     {data.get('potencia_instalada_motos_kw', 'NO ENCONTRADO')} kW")
    print(f"   Mototaxis: {data.get('potencia_instalada_mototaxis_kw', 'NO ENCONTRADO')} kW")
    print(f"   TOTAL:     {data.get('potencia_total_instalada_kw', 'NO ENCONTRADO')} kW")

    print("\n[+] VEHÍCULOS EN HORA PICO (4h: 18-22h):")
    print(f"   Motos:     {data.get('n_motos_pico', 'NO ENCONTRADO')}")
    print(f"   Mototaxis: {data.get('n_mototaxis_pico', 'NO ENCONTRADO')}")

    print("\n[+] FLOTA DIARIA TOTAL (9am-10pm, pico=50% de demanda):")
    print(f"   Motos:     {data.get('n_motos_dia_total', 'NO ENCONTRADO')}")
    print(f"   Mototaxis: {data.get('n_mototaxis_dia_total', 'NO ENCONTRADO')}")
    print(f"   Peak share: {data.get('peak_share_day', 'NO ENCONTRADO')}")

    print("\n" + "=" * 70)
    print("✓ VERIFICACIÓN COMPLETA")
    print("=" * 70)
else:
    print(f"ERROR: No se encontró el archivo {json_path}")
