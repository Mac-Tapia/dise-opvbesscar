"""
Análisis del perfil de carga para dimensionamiento del BESS
Genera consideraciones técnicas y datos para construcción del schema
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Cargar perfil
df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

print("=" * 80)
print("ANÁLISIS PARA DIMENSIONAMIENTO DEL BESS")
print("=" * 80)

# =====================================================================
# 1. ANÁLISIS DEL PERFIL DE DEMANDA EV
# =====================================================================
print("\n" + "=" * 80)
print("1. CARACTERÍSTICAS DEL PERFIL DE DEMANDA EV")
print("=" * 80)

total_energia_dia = df['energy_kwh'].sum()
potencia_maxima = df['power_kw'].max()
potencia_promedio = df[df['power_kw'] > 0]['power_kw'].mean()

print(f"\nEnergía total diaria: {total_energia_dia:,.2f} kWh")
print(f"Potencia máxima: {potencia_maxima:,.2f} kW")
print(f"Potencia promedio (operación): {potencia_promedio:,.2f} kW")
print(f"Horas de operación: 9h - 22h (13 horas)")
print(f"Resolución temporal: 15 minutos (96 intervalos/día)")

# Perfil por hora
print("\n" + "-" * 80)
print("PERFIL HORARIO:")
print("-" * 80)
print(f"{'Hora':<6} {'Energía (kWh)':<15} {'Pot. Max (kW)':<15} {'Pot. Prom (kW)':<15}")
print("-" * 80)

for hora in range(9, 23):
    data_hora = df[df['hour'] == hora]
    if len(data_hora) > 0:
        energia = data_hora['energy_kwh'].sum()
        pot_max = data_hora['power_kw'].max()
        pot_prom = data_hora['power_kw'].mean()
        print(f"{hora:>4}h  {energia:>13.2f}  {pot_max:>13.2f}  {pot_prom:>13.2f}")

# =====================================================================
# 2. IDENTIFICACIÓN DE HORARIO DE DÉFICIT (NECESIDAD DE BESS)
# =====================================================================
print("\n" + "=" * 80)
print("2. HORARIO DE DÉFICIT SOLAR → NECESIDAD DE BESS")
print("=" * 80)

# Asumiendo que la generación solar termina aproximadamente a las 17h
# (basado en análisis previo: generación 5h-17h con pico a mediodía)
hora_fin_solar = 17

print(f"\nGeneración solar estimada: 5h - {hora_fin_solar}h")
print(f"Demanda EV: 9h - 22h")
print(f"\nPERÍODO DE DÉFICIT (sin solar, necesita BESS):")

deficit_horas = df[df['hour'] > hora_fin_solar]
deficit_total = deficit_horas['energy_kwh'].sum()
deficit_pot_max = deficit_horas['power_kw'].max()

print(f"  Horario déficit: {hora_fin_solar+1}h - 22h ({22-hora_fin_solar} horas)")
print(f"  Energía déficit: {deficit_total:,.2f} kWh/día")
print(f"  Potencia máxima en déficit: {deficit_pot_max:,.2f} kW")

print("\n" + "-" * 80)
print("DETALLE HORARIO DEL DÉFICIT:")
print("-" * 80)
print(f"{'Hora':<6} {'Energía (kWh)':<15} {'Pot. Max (kW)':<15} {'% del déficit':<15}")
print("-" * 80)

for hora in range(hora_fin_solar + 1, 23):
    data_hora = df[df['hour'] == hora]
    if len(data_hora) > 0:
        energia = data_hora['energy_kwh'].sum()
        pot_max = data_hora['power_kw'].max()
        porcentaje = (energia / deficit_total) * 100
        print(f"{hora:>4}h  {energia:>13.2f}  {pot_max:>13.2f}  {porcentaje:>13.1f}%")

# =====================================================================
# 3. PARÁMETROS PARA DIMENSIONAMIENTO DEL BESS
# =====================================================================
print("\n" + "=" * 80)
print("3. PARÁMETROS PARA DIMENSIONAMIENTO DEL BESS")
print("=" * 80)

# Parámetros típicos de BESS
DoD = 0.80  # Profundidad de descarga (80%)
eficiencia = 0.95  # Eficiencia round-trip
SOC_min = 0.20  # SOC mínimo al cierre
C_rate = 0.60  # C-rate para potencia

# Capacidad BESS
# Debe cubrir el déficit nocturno con margen para DoD
capacidad_util = deficit_total / eficiencia  # Considerando pérdidas
capacidad_nominal = capacidad_util / DoD  # Considerando DoD

# Potencia BESS
# Debe manejar la potencia máxima del déficit
potencia_nominal = deficit_pot_max / C_rate  # Considerando C-rate

print(f"\nParámetros de diseño:")
print(f"  - Profundidad de descarga (DoD): {DoD*100:.0f}%")
print(f"  - Eficiencia round-trip: {eficiencia*100:.0f}%")
print(f"  - SOC mínimo al cierre: {SOC_min*100:.0f}%")
print(f"  - C-rate: {C_rate:.2f}")

print(f"\nDimensionamiento BESS:")
print(f"  ┌─────────────────────────────────────────────────┐")
print(f"  │ CAPACIDAD NOMINAL: {capacidad_nominal:>10.0f} kWh          │")
print(f"  │ POTENCIA NOMINAL:  {potencia_nominal:>10.0f} kW           │")
print(f"  └─────────────────────────────────────────────────┘")

print(f"\nCálculos detallados:")
print(f"  Energía déficit neta: {deficit_total:,.2f} kWh")
print(f"  Energía útil (con eficiencia): {capacidad_util:,.2f} kWh")
print(f"  Capacidad nominal (DoD {DoD*100:.0f}%): {capacidad_nominal:,.2f} kWh")
print(f"  Potencia pico déficit: {deficit_pot_max:,.2f} kW")
print(f"  Potencia nominal (C-rate {C_rate:.2f}): {potencia_nominal:,.2f} kW")

# =====================================================================
# 4. ESTRATEGIA DE OPERACIÓN DEL BESS
# =====================================================================
print("\n" + "=" * 80)
print("4. ESTRATEGIA DE OPERACIÓN DEL BESS")
print("=" * 80)

print(f"""
REGLAS DE OPERACIÓN:

1. CARGA DEL BESS (5h - 17h):
   - Fuente: Excedente de generación solar (después de cubrir mall)
   - Objetivo: Alcanzar SOC 100% antes de las 18h
   - Control: Carga controlada para no sobredimensionar inversor

2. DESCARGA DEL BESS (18h - 22h):
   - Inicio: {hora_fin_solar+1}h (cuando termina generación solar)
   - Fin: 22h (hora de cierre del mall)
   - Objetivo: Cubrir déficit de demanda EV
   - SOC final: Debe llegar a {SOC_min*100:.0f}% a las 22h

3. REPOSO (22h - 5h):
   - BESS en standby
   - Sin carga ni descarga
   - Mantener SOC mínimo ({SOC_min*100:.0f}%)

PERFIL DE DESCARGA ESPERADO:
""")

print(f"{'Hora':<6} {'Demanda (kW)':<15} {'SOC esperado (%)':<20}")
print("-" * 50)

# Simular SOC durante descarga
soc_inicial = 100.0
energia_restante = capacidad_nominal
for hora in range(hora_fin_solar + 1, 23):
    data_hora = df[df['hour'] == hora]
    if len(data_hora) > 0:
        energia_hora = data_hora['energy_kwh'].sum()
        pot_prom = data_hora['power_kw'].mean()

        energia_restante -= energia_hora
        soc_actual = (energia_restante / capacidad_nominal) * 100

        print(f"{hora:>4}h  {pot_prom:>13.2f}  {soc_actual:>18.1f}%")

# =====================================================================
# 5. DATOS PARA CONSTRUCCIÓN DEL SCHEMA
# =====================================================================
print("\n" + "=" * 80)
print("5. DATOS PARA CONSTRUCCIÓN DEL SCHEMA")
print("=" * 80)

# Crear datos para schema
schema_data = {
    # Parámetros del perfil
    "perfil": {
        "resolucion_minutos": 15,
        "intervalos_dia": 96,
        "energia_total_dia_kwh": float(total_energia_dia),
        "potencia_maxima_kw": float(potencia_maxima),
        "potencia_promedio_kw": float(potencia_promedio),
        "hora_apertura": 9,
        "hora_cierre": 22,
        "horas_operacion": 13,
    },

    # Parámetros del BESS
    "bess": {
        "capacidad_nominal_kwh": float(capacidad_nominal),
        "potencia_nominal_kw": float(potencia_nominal),
        "dod": DoD,
        "eficiencia": eficiencia,
        "soc_min": SOC_min,
        "soc_max": 1.0,
        "c_rate": C_rate,
    },

    # Horarios de operación
    "horarios": {
        "carga_bess": {
            "inicio": 5,
            "fin": 17,
            "fuente": "excedente_solar"
        },
        "descarga_bess": {
            "inicio": hora_fin_solar + 1,
            "fin": 22,
            "destino": "demanda_ev"
        },
        "reposo": {
            "inicio": 22,
            "fin": 5,
        }
    },

    # Déficit energético
    "deficit": {
        "energia_total_kwh": float(deficit_total),
        "potencia_maxima_kw": float(deficit_pot_max),
        "horas_deficit": 22 - hora_fin_solar,
        "horario_inicio": hora_fin_solar + 1,
        "horario_fin": 22,
    }
}

# Guardar en JSON
import json
output_path = Path("data/oe2/bess_dimensionamiento_schema.json")
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(schema_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ Schema guardado en: {output_path.resolve()}")

# =====================================================================
# 6. RESUMEN EJECUTIVO
# =====================================================================
print("\n" + "=" * 80)
print("6. RESUMEN EJECUTIVO - DIMENSIONAMIENTO BESS")
print("=" * 80)

print(f"""
┌────────────────────────────────────────────────────────────────────┐
│                  SISTEMA DE ALMACENAMIENTO (BESS)                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  DIMENSIONAMIENTO:                                                 │
│    • Capacidad nominal:  {capacidad_nominal:>10.0f} kWh                       │
│    • Potencia nominal:   {potencia_nominal:>10.0f} kW                        │
│    • Tecnología: Litio-Ion (recomendado)                          │
│                                                                    │
│  PARÁMETROS OPERACIONALES:                                         │
│    • Profundidad de descarga: {DoD*100:.0f}%                                │
│    • SOC operacional: {SOC_min*100:.0f}% - 100%                              │
│    • Eficiencia: {eficiencia*100:.0f}%                                        │
│    • C-rate: {C_rate:.2f}                                                │
│                                                                    │
│  FUNCIÓN:                                                          │
│    • Almacena excedente solar diurno (5h-17h)                     │
│    • Descarga para cubrir demanda EV nocturna (18h-22h)           │
│    • Déficit cubierto: {deficit_total:>10.0f} kWh/día                    │
│                                                                    │
│  BENEFICIOS:                                                       │
│    • Maximiza uso de energía solar                                │
│    • Reduce dependencia de la red                                 │
│    • Habilita carga EV fuera de horario solar                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

PRÓXIMOS PASOS:
  1. Validar perfil solar vs. demanda con datos reales
  2. Ajustar dimensionamiento según disponibilidad de excedente solar
  3. Optimizar estrategia de carga/descarga
  4. Evaluar viabilidad económica (CAPEX/OPEX)
""")

print("=" * 80)
