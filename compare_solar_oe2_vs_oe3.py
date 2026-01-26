"""
Verificar si los 7.67 GWh calculados son correctos comparando con OE2.
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path

print("=" * 100)
print("COMPARACION: GENERACION SOLAR OE2 vs OE3 (CSV ACTUAL)")
print("=" * 100)

# 1. OE2 - Valor objetivo de configuración
target_kwh_oe2: int = 3_972_478  # del default.yaml
target_gwh_oe2: float = target_kwh_oe2 / 1e6

print(f"\n[OE2] CONFIGURACION EN default.yaml")
print(f"  target_annual_kwh: {target_kwh_oe2:,} kWh")
print(f"  target_annual_gwh: {target_gwh_oe2:.2f} GWh")
print(f"  target_dc_kw:      4,162 kW")
print(f"  target_ac_kw:      3,201.2 kW")

# 2. OE3 - Valor actual en CSV
solar_path: Path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
df: pd.DataFrame = pd.read_csv(solar_path)
ac_power: pd.Series = df['ac_power_kw']
actual_kwh: float = ac_power.sum()
actual_gwh: float = actual_kwh / 1e6

print(f"\n[OE3] CSV ACTUAL (pv_generation_timeseries.csv)")
print(f"  ac_power_kw sum:   {actual_kwh:,.1f} kWh")
print(f"  ac_power_kw gwh:   {actual_gwh:.2f} GWh")
print(f"  ac_power_kw max:   {ac_power.max():,.2f} kW")
print(f"  ac_power_kw mean:  {ac_power.mean():.2f} kW")
print(f"  rows:              {len(df)}")

# 3. Análisis de diferencia
diff_kwh: float = actual_kwh - target_kwh_oe2
diff_pct: float = (diff_kwh / target_kwh_oe2) * 100

print(f"\n[COMPARACION]")
print(f"  OE2 Target:     {target_gwh_oe2:.2f} GWh")
print(f"  OE3 Actual:     {actual_gwh:.2f} GWh")
print(f"  Diferencia:     {diff_kwh:+,.1f} kWh ({diff_pct:+.1f}%)")

# 4. Explicación
print(f"\n[EXPLICACION]")
if abs(diff_pct) < 1:
    print(f"  ✓ Los valores coinciden (< 1% diferencia)")
elif actual_gwh > target_gwh_oe2:
    factor: float = actual_gwh / target_gwh_oe2
    print(f"  ⚠ CSV tiene {factor:.2f}× más energía que OE2 target")
    print(f"  ⚠ CSV tiene {factor:.2f}× más energía que OE2 target")
    print(f"\n  Posible causa:")
    print(f"    1. OE2 calcula con 15 minutos (PVGIS):")
    print(f"       - Datos 15-min se promedian/degradan")
    print(f"       - Incluyen pérdidas de temperatura Sandia")
    print(f"       - Usan Performance Ratio real")
    print(f"\n    2. CSV actual (post-resample):")
    print(f"       - Resample 15-min→1-hora SUM (no degradación)")
    print(f"       - Suma 4 intervalos sin pérdidas")
    print(f"       - Puede sobreestimar energía")
else:
    if 'factor' in locals():
        neg_factor: float = -factor
        print(f"  ⚠ CSV tiene {neg_factor:.2f}× menos energía que OE2 target")
    print(f"\n  Posible causa:")
    print(f"    - Datos incompletos (falta meses)")
    print(f"    - Errores en conversión 15-min→1-hora")

# 5. Verificación de 15 minutos vs 1 hora
print(f"\n[VALIDACION RESAMPLE]")
# Detectar si original fue 15 minutos
df_check = pd.read_csv(solar_path)
n_rows = len(df_check)
print(f"  Filas actuales: {n_rows}")

if n_rows == 8760:
    print(f"  ✓ 8,760 filas = 365 días × 24 horas = HORARIO")
    print(f"    (Si fue 15-min, habría 8,760 × 4 = 35,040 filas)")
elif n_rows == 35040:
    print(f"  ⚠ 35,040 filas = 365 días × 24 horas × 4 = 15-MINUTOS")
    print(f"    (Necesita resample a horario)")
elif n_rows // 4 == 8760:
    print(f"  ⚠ {n_rows} filas podría ser 15-minutos")
    print(f"    ({n_rows} ÷ 4 = {n_rows // 4} horas)")

# 6. Recomendación
print(f"\n[RECOMENDACION]")
if actual_gwh > target_gwh_oe2 * 1.5:
    print(f"  ⚠ ADVERTENCIA: Energía solar ({actual_gwh:.2f} GWh) es muy superior a OE2")
    print(f"    Verificar:")
    print(f"      1. ¿Fue correctamente resampled 15-min→1-hora?")
    print(f"      2. ¿Incluye pérdidas Sandia (temperatura, PoA)?")
    print(f"      3. ¿Escala de módulos/inversores correcto?")
    print(f"\n  Opción 1: Usar OE2 original (3.97 GWh) con PVGIS data")
    print(f"  Opción 2: Escalar CSV a OE2 target (factor = {target_gwh_oe2 / actual_gwh:.3f})")
elif actual_gwh < target_gwh_oe2 * 0.8:
    print(f"  ⚠ ADVERTENCIA: Energía solar ({actual_gwh:.2f} GWh) es muy inferior a OE2")
    print(f"    Datos pueden estar incompletos o degradados")
else:
    print(f"  ✓ Energía solar ({actual_gwh:.2f} GWh) está razonablemente cercana a OE2 ({target_gwh_oe2:.2f} GWh)")
    print(f"    Diferencia de {diff_pct:.1f}% es aceptable")

print(f"\n" + "=" * 100)
