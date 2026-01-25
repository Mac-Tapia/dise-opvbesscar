#!/usr/bin/env python3
"""
GENERADOR DE 101 ESCENARIOS DE CARGA - RESOLUCIÓN 15 MINUTOS
==============================================================
Genera perfiles anuales de carga para dos playas (Motos y Mototaxis)
con 35,040 timesteps cada uno (365 días × 24 horas × 4 intervalos de 15 min).

Características:
- Variabilidad aleatoria realista (día a día, hora a hora)
- Patrones consistentes dentro de cada escenario
- Compatible con CityLearn v2
- Optimizado para entrenar agentes en OE3
"""

import csv
import json
import random
import math
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass

# Rutas
SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT = SCRIPT_DIR.parent.absolute()
OE2_DIR = ROOT / "data" / "oe2"
OUTPUT_BASE = OE2_DIR / "escenarios_101" / "perfiles_15min"

print("=" * 90)
print("🎯 GENERADOR DE 101 ESCENARIOS - PERFILES DE CARGA (15 MINUTOS)")
print("=" * 90)
print()

# ============================================================================
# CARGAR TABLA DE ESCENARIOS Y GENERAR 101 VARIACIONES
# ============================================================================

print("📥 Cargando tabla de escenarios y generando 101 variaciones...")

escenarios_file = OE2_DIR / "tabla_escenarios_vehiculos.csv"

escenarios_base = []
with open(escenarios_file, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        escenarios_base.append({
            'nombre': row.get('Escenario', 'Sin nombre'),
            'pe': float(row.get('PE', 0.5)),
            'fc': float(row.get('FC', 0.6)),
            'chargers': int(float(row.get('Cargadores', 20))),
            'sockets': int(float(row.get('Tomas', 80))),
            'energy_day_kwh': float(row.get('Energía/Día (kWh)', 1738.80)),
        })

print(f"✅ {len(escenarios_base)} escenarios base cargados")

# Generar 101 escenarios interpolando entre base y agregando variación
escenarios = []

# Interpolar entre los escenarios base
rng = random.Random(42)
energy_min = min(e['energy_day_kwh'] for e in escenarios_base)
energy_max = max(e['energy_day_kwh'] for e in escenarios_base)

for idx in range(1, 102):
    # Interpolar energía entre min y max de forma no lineal
    t = (idx - 1) / 100.0  # 0 a 1

    # Usar spline cúbica para transición suave
    t_smooth = t * t * (3 - 2 * t)

    energy_day = energy_min + (energy_max - energy_min) * t_smooth

    # Agregar pequeña variación aleatoria
    energy_day *= rng.gauss(1.0, 0.05)

    # Interpolar PE y FC también
    pe = 0.10 + (1.00 - 0.10) * t_smooth
    fc = 0.40 + (1.00 - 0.40) * t_smooth

    # Derivar cargadores y sockets basado en PE y FC
    chargers = int(4 + (35 - 4) * t_smooth)
    sockets = int(16 + (140 - 16) * t_smooth)

    escenarios.append({
        'id': idx,
        'escenario': f'Escenario_{idx:03d}',
        'pe': pe,
        'fc': fc,
        'chargers': chargers,
        'sockets': sockets,
        'energy_day_kwh': energy_day,
    })

print(f"✅ {len(escenarios)} escenarios interpolados generados")
print(f"   Energía min: {min(e['energy_day_kwh'] for e in escenarios):.2f} kWh/día")
print(f"   Energía max: {max(e['energy_day_kwh'] for e in escenarios):.2f} kWh/día")
print(f"   Energía prom: {sum(e['energy_day_kwh'] for e in escenarios)/len(escenarios):.2f} kWh/día")

# ============================================================================
# DEFINIR PLAYAS
# ============================================================================

@dataclass
class PlayaConfig:
    """Configuración de una playa de estacionamiento"""
    nombre: str
    vehiculos_pico: str  # "Motos" o "Mototaxis"
    ratio: float  # Proporción de energía de ese tipo
    perfil_horario: dict  # Distribución horaria

# Playa Motos: 112 sockets × 80% = más demanda
PLAYA_MOTOS = PlayaConfig(
    nombre="Playa_Motos",
    vehiculos_pico="Motos",
    ratio=0.75,
    perfil_horario={
        # Patrón de llegada de motos durante el día
        0: 0.02,   1: 0.01,   2: 0.01,   3: 0.00,   4: 0.00,   5: 0.01,
        6: 0.03,   7: 0.08,   8: 0.15,   9: 0.18,  10: 0.18,  11: 0.15,
        12: 0.10,  13: 0.12,  14: 0.14,  15: 0.15,  16: 0.18,  17: 0.22,
        18: 0.25,  19: 0.22,  20: 0.18,  21: 0.12,  22: 0.08,  23: 0.03,
    }
)

# Playa Mototaxis: 16 sockets × 80% = menos demanda
PLAYA_MOTOTAXIS = PlayaConfig(
    nombre="Playa_Mototaxis",
    vehiculos_pico="Mototaxis",
    ratio=0.25,
    perfil_horario={
        # Patrón diferente: más concentrado en noches
        0: 0.01,   1: 0.00,   2: 0.00,   3: 0.00,   4: 0.00,   5: 0.00,
        6: 0.01,   7: 0.02,   8: 0.04,   9: 0.06,  10: 0.07,  11: 0.06,
        12: 0.04,  13: 0.05,  14: 0.06,  15: 0.08,  16: 0.10,  17: 0.14,
        18: 0.18,  19: 0.18,  20: 0.16,  21: 0.12,  22: 0.06,  23: 0.02,
    }
)

# ============================================================================
# GENERADOR DE PERFILES
# ============================================================================

class PerfilCargaAnual:
    """Generador de perfil anual con variabilidad realista"""

    def __init__(self, energia_dia_kwh, playa_config, seed):
        self.energia_dia_kwh = energia_dia_kwh
        self.playa = playa_config
        self.seed = seed
        self.rng = random.Random(seed)

        # Parámetros de variabilidad
        self.var_dia = 0.10  # ±10% variación día a día
        self.var_intervalo = 0.15  # ±15% variación intervalo a intervalo

    def generar_año(self):
        """Genera 365 días × 96 intervalos = 35,040 timesteps"""

        timesteps = []

        for day in range(365):
            # Variación día a día (ej: lunes-viernes vs fin de semana)
            weekday = day % 7
            if weekday < 5:  # Lunes-Viernes
                factor_dia = self.rng.gauss(1.0, self.var_dia / 2)
            else:  # Sábado-Domingo
                factor_dia = self.rng.gauss(1.1, self.var_dia / 2)  # +10% fin de semana

            # Generar 96 intervalos de 15 min para este día
            energia_dia_ajustada = self.energia_dia_kwh * factor_dia

            for intervalo in range(96):
                hora = intervalo // 4
                minuto = (intervalo % 4) * 15

                # Factor horario del perfil
                factor_horario = self.playa.perfil_horario.get(hora, 0.05)

                # Variación aleatoria del intervalo
                factor_intervalo = self.rng.gauss(1.0, self.var_intervalo)
                factor_intervalo = max(0.3, min(1.5, factor_intervalo))  # Limitar

                # Energía para este intervalo (kWh en 15 min)
                energia_intervalo = (energia_dia_ajustada / 96) * factor_horario * factor_intervalo
                energia_intervalo = max(0, energia_intervalo)

                # Potencia en kW (energía / 0.25h)
                potencia_kw = energia_intervalo / 0.25

                timesteps.append({
                    'day': day,
                    'hour': hora,
                    'minute': minuto,
                    'interval': intervalo,
                    'energy_kwh': energia_intervalo,
                    'power_kw': potencia_kw,
                })

        return timesteps

# ============================================================================
# CREAR DIRECTORIO DE SALIDA
# ============================================================================

OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
print(f"\n✅ Directorio de salida: {OUTPUT_BASE}")
print()

# ============================================================================
# GENERAR 101 ESCENARIOS
# ============================================================================

print("=" * 90)
print("🔧 Generando 101 escenarios × 2 playas × 35,040 timesteps...")
print("=" * 90)
print()

resultados = {
    'motos': {},
    'mototaxis': {},
    'resumen': []
}

for idx, escenario in enumerate(escenarios, 1):
    print(f"[{idx:3d}/101] Escenario {escenario['escenario']:30s} ", end='', flush=True)

    # Energía total para el escenario
    energia_total = escenario['energy_day_kwh']

    # Distribución: Motos (75%) y Mototaxis (25%)
    energia_motos = energia_total * PLAYA_MOTOS.ratio
    energia_mototaxis = energia_total * PLAYA_MOTOTAXIS.ratio

    # ===== PLAYA MOTOS =====
    generador_motos = PerfilCargaAnual(energia_motos, PLAYA_MOTOS, seed=escenario['id'] * 1000)
    timesteps_motos = generador_motos.generar_año()

    # Guardar CSV
    archivo_motos = OUTPUT_BASE / f"escenario_{escenario['id']:03d}_motos.csv"
    with open(archivo_motos, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['day', 'hour', 'minute', 'interval', 'energy_kwh', 'power_kw'])
        writer.writeheader()
        for ts in timesteps_motos:
            writer.writerow({
                'day': ts['day'],
                'hour': ts['hour'],
                'minute': ts['minute'],
                'interval': ts['interval'],
                'energy_kwh': f"{ts['energy_kwh']:.4f}",
                'power_kw': f"{ts['power_kw']:.4f}",
            })

    energia_total_motos = sum(ts['energy_kwh'] for ts in timesteps_motos)

    # ===== PLAYA MOTOTAXIS =====
    generador_mototaxis = PerfilCargaAnual(energia_mototaxis, PLAYA_MOTOTAXIS, seed=escenario['id'] * 2000)
    timesteps_mototaxis = generador_mototaxis.generar_año()

    # Guardar CSV
    archivo_mototaxis = OUTPUT_BASE / f"escenario_{escenario['id']:03d}_mototaxis.csv"
    with open(archivo_mototaxis, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['day', 'hour', 'minute', 'interval', 'energy_kwh', 'power_kw'])
        writer.writeheader()
        for ts in timesteps_mototaxis:
            writer.writerow({
                'day': ts['day'],
                'hour': ts['hour'],
                'minute': ts['minute'],
                'interval': ts['interval'],
                'energy_kwh': f"{ts['energy_kwh']:.4f}",
                'power_kw': f"{ts['power_kw']:.4f}",
            })

    energia_total_mototaxis = sum(ts['energy_kwh'] for ts in timesteps_mototaxis)

    resultados['motos'][escenario['id']] = {
        'archivo': str(archivo_motos.name),
        'energia_anual_kwh': energia_total_motos,
        'energia_diaria_kwh': energia_total_motos / 365,
        'potencia_max_kw': max(ts['power_kw'] for ts in timesteps_motos),
        'potencia_promedio_kw': energia_total_motos / 365 / 24,
    }

    resultados['mototaxis'][escenario['id']] = {
        'archivo': str(archivo_mototaxis.name),
        'energia_anual_kwh': energia_total_mototaxis,
        'energia_diaria_kwh': energia_total_mototaxis / 365,
        'potencia_max_kw': max(ts['power_kw'] for ts in timesteps_mototaxis),
        'potencia_promedio_kw': energia_total_mototaxis / 365 / 24,
    }

    resultados['resumen'].append({
        'escenario_id': escenario['id'],
        'escenario_nombre': escenario['escenario'],
        'chargers': escenario['chargers'],
        'sockets': escenario['sockets'],
        'energia_total_kwh': energia_total_motos + energia_total_mototaxis,
        'energia_motos_kwh': energia_total_motos,
        'energia_mototaxis_kwh': energia_total_mototaxis,
    })

    print(f"✅ ({energia_total_motos/365:.1f} + {energia_total_mototaxis/365:.1f} kWh/día)")

print()
print("=" * 90)
print("✅ GENERACIÓN COMPLETADA")
print("=" * 90)
print()

# ============================================================================
# GUARDAR METADATOS
# ============================================================================

# Resumen de escenarios
resumen_file = OUTPUT_BASE / "escenarios_resumen.json"
with open(resumen_file, 'w') as f:
    json.dump(resultados, f, indent=2)

print(f"📊 Metadatos guardados: {resumen_file.name}")

# ============================================================================
# ESTADÍSTICAS FINALES
# ============================================================================

print()
print("📈 ESTADÍSTICAS DE LOS 101 ESCENARIOS")
print("-" * 90)

total_motos = sum(r['energia_motos_kwh'] for r in resultados['resumen'])
total_mototaxis = sum(r['energia_mototaxis_kwh'] for r in resultados['resumen'])
total_combinado = total_motos + total_mototaxis

print(f"\n🏢 DEMANDA TOTAL (101 escenarios × 365 días):")
print(f"   • Playas Motos: {total_motos/1e6:.2f} M kWh/año")
print(f"   • Playas Mototaxis: {total_mototaxis/1e6:.2f} M kWh/año")
print(f"   • TOTAL: {total_combinado/1e6:.2f} M kWh/año")

# Por escenario
energias_diarias = [r['energia_motos_kwh']/365 + r['energia_mototaxis_kwh']/365 for r in resultados['resumen']]
print(f"\n📊 DISTRIBUCIÓN POR ESCENARIO:")
print(f"   • Mínimo: {min(energias_diarias):.2f} kWh/día")
print(f"   • Máximo: {max(energias_diarias):.2f} kWh/día")
print(f"   • Promedio: {sum(energias_diarias)/len(energias_diarias):.2f} kWh/día")

# Timesteps
print(f"\n⏱️  TIMESTEPS POR ESCENARIO:")
print(f"   • 1 año = 365 días")
print(f"   • 1 día = 24 horas × 4 intervalos = 96 intervalos")
print(f"   • TOTAL: 365 × 96 = 35,040 timesteps/escenario/playa")
print(f"   • Total timesteps: 101 escenarios × 2 playas × 35,040 = 7,078,080 timesteps")

# Archivos
print(f"\n📁 ARCHIVOS GENERADOS:")
archivos_motos = len(list(OUTPUT_BASE.glob("escenario_*_motos.csv")))
archivos_mototaxis = len(list(OUTPUT_BASE.glob("escenario_*_mototaxis.csv")))
print(f"   • CSV Motos: {archivos_motos}")
print(f"   • CSV Mototaxis: {archivos_mototaxis}")
print(f"   • TOTAL: {archivos_motos + archivos_mototaxis}")

# Tamaño
total_size = sum(f.stat().st_size for f in OUTPUT_BASE.glob("*.csv")) / 1e6
print(f"   • Tamaño total: {total_size:.1f} MB")

print()
print("=" * 90)
print("🎮 LISTO PARA ENTRENAR AGENTES EN OE3 CON CITYLEARN V2")
print("=" * 90)
print()

print("📚 PRÓXIMOS PASOS:")
print()
print("1. Integrar perfiles en CityLearn v2:")
print(f"   $ python -m src.iquitos_citylearn.oe2.train_citylearn_oe3_v2 \\")
print(f"       --config data/oe2/citylearn/training_data/citylearn_config.json \\")
print(f"       --scenarios-dir {OUTPUT_BASE} \\")
print(f"       --episodes 50 \\")
print(f"       --device cuda")
print()

print("2. Estructura de acceso a escenarios:")
print()
print(f"   from pathlib import Path")
print(f"   import pandas as pd")
print(f"   ")
print(f"   scenarios_dir = Path('{OUTPUT_BASE}')")
print(f"   ")
print(f"   # Cargar escenario 1, Playa Motos")
print(f"   df = pd.read_csv(scenarios_dir / 'escenario_001_motos.csv')")
print(f"   print(f'Timesteps: {{len(df)}}')")
print(f"   print(f'Energía anual: {{df[\"energy_kwh\"].sum():.0f}} kWh')")
print()

print("=" * 90)
