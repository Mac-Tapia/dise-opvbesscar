"""
Generar perfil de carga de 15 minutos para EV
Basado en escenario RECOMENDADO (32 cargadores, 3,252 kWh/día)
"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from iquitos_citylearn.oe2.chargers import build_hourly_profile

# Configuración escenario RECOMENDADO
ENERGY_DAY_KWH = 3252.0  # Energía total diaria
OPENING_HOUR = 9         # Mall abre 9 AM
CLOSING_HOUR = 22        # Mall cierra 10 PM
PEAK_HOURS = [18, 19, 20, 21]  # Horas pico 6-10 PM
PEAK_SHARE = 0.40        # 40% de energía en hora pico
MAX_POWER_KW = 272.0     # 112 motos×2kW + 16 mototaxis×3kW = 272 kW

# Generar perfil de 15 minutos
print("=" * 70)
print("GENERANDO PERFIL DE 15 MINUTOS - ESCENARIO RECOMENDADO")
print("=" * 70)
print(f"\nEnergía día: {ENERGY_DAY_KWH:,.2f} kWh")
print(f"Horario: {OPENING_HOUR}:00 - {CLOSING_HOUR}:00")
print(f"Horas pico: {PEAK_HOURS}")
print(f"Fracción pico: {PEAK_SHARE:.0%}")
print(f"Potencia máxima: {MAX_POWER_KW:.0f} kW (límite físico)")

profile = build_hourly_profile(
    energy_day_kwh=ENERGY_DAY_KWH,
    opening_hour=OPENING_HOUR,
    closing_hour=CLOSING_HOUR,
    peak_hours=PEAK_HOURS,
    peak_share_day=PEAK_SHARE,
    max_power_kw=MAX_POWER_KW,
)

# Verificar
print(f"\n{'='*70}")
print("VERIFICACIÓN PERFIL GENERADO")
print("="*70)
print(f"Intervalos: {len(profile)} (esperado: 96)")
print(f"Columnas: {profile.columns.tolist()}")
print(f"\nTotal energía: {profile['energy_kwh'].sum():.2f} kWh")
print(f"Potencia máxima: {profile['power_kw'].max():.2f} kW")
print(f"Energía pico: {profile[profile['is_peak']]['energy_kwh'].sum():.2f} kWh")
print(f"Energía fuera pico: {profile[~profile['is_peak']]['energy_kwh'].sum():.2f} kWh")

# Guardar
out_dir = Path("data/oe2")
out_dir.mkdir(parents=True, exist_ok=True)
output_path = out_dir / "perfil_horario_carga.csv"
profile.to_csv(output_path, index=False)

print(f"\n{'='*70}")
print(f"✅ Perfil guardado en: {output_path.resolve()}")
print("="*70)

# Mostrar muestra
print(f"\n{'='*70}")
print("PRIMERAS 12 INTERVALOS (primeras 3 horas):")
print("="*70)
print(profile.head(12).to_string(index=False))

print(f"\n{'='*70}")
print("INTERVALOS HORA PICO (18h = intervalos 72-75):")
print("="*70)
print(profile.iloc[72:76].to_string(index=False))
