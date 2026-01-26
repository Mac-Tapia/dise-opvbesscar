#!/usr/bin/env python3
"""
Script de ejemplo: Analizar demanda del mall con control operativo insertado.

Muestra:
1. Carga de demanda real del mall (demandamallkwh.csv)
2. Simulación de despacho (P1-P5) 
3. Comportamiento de balance energético
4. Generación de reportes 24h y diarios
"""

from pathlib import Path
import pandas as pd
from datetime import timedelta
from scripts._common import load_all
from src.iquitos_citylearn.oe3.demanda_mall_kwh import (
    create_demanda_mall_analyzer,
)


def simular_despacho_24h_ejemplo():
    """
    Simular un día típico con demanda del mall y control operativo.
    Genera reporte de comportamiento.
    """
    
    # 1. Cargar configuración
    print("=" * 80)
    print("SIMULADOR: DEMANDA MALL CON CONTROL OPERATIVO")
    print("=" * 80)
    print()
    
    cfg, rp = load_all("configs/default.yaml")
    rp.ensure()
    
    print("✅ Configuración cargada")
    print()
    
    # 2. Crear analizador
    analyzer = create_demanda_mall_analyzer(cfg)
    print("✅ Analizador de demanda creado")
    print()
    
    # 3. Cargar demanda real del mall
    interim_dir = Path("data/interim/oe2")
    try:
        df_mall = analyzer.cargar_demanda_mall_real(interim_dir)
        print(f"✅ Demanda mall cargada: {len(df_mall)} horas")
        print(f"   Rango: {df_mall.index[0]} a {df_mall.index[-1]}")
        print()
    except FileNotFoundError as e:
        print(f"⚠️  {e}")
        print("   Usando demanda sintética para demo")
        
        # Crear demanda sintética realista
        dates = pd.date_range(start="2024-08-01", periods=8760, freq="h")
        hora_dia = dates.hour
        
        # Perfil típico Iquitos: bajo noche, alto día
        perfil_base = [
            450, 420, 400, 390, 380, 400,  # 0-5: madrugada
            550, 700, 850, 950, 1000, 1050,  # 6-11: mañana
            1100, 1080, 1050, 1000, 1050, 1100,  # 12-17: mediodía/tarde
            1050, 1000, 900, 800,  # 18-21: pico clientes
            600, 500,  # 22-23: cierre
        ]
        
        df_mall = pd.DataFrame({
            'demanda_mall_kwh': [perfil_base[h] for h in hora_dia],
        }, index=dates)
        print("✅ Demanda mall sintética creada (perfil 24h realista)")
        print()
    
    # 4. Cargar PV
    pv_path = interim_dir / "oe2" / "solar" / "solar_generation_kwh.csv"
    if pv_path.exists():
        df_pv = pd.read_csv(pv_path, index_col=0, parse_dates=True)
        print(f"✅ PV cargado: {len(df_pv)} registros")
    else:
        print("⚠️  PV no encontrado, usando perfil sintético")
        
        dates = df_mall.index
        # Convertir a DatetimeIndex para acceder a propiedades de hora
        dates_dt = pd.to_datetime(dates)
        hora_dia = dates_dt.hour
        
        # Perfil solar: máximo mediodía (13-14h)
        def pv_profile(h):
            if h < 6 or h > 18:
                return 0.0
            elif h <= 12:
                return (h - 6) * 60  # Rampa up
            elif h <= 14:
                return 360 + (h - 12) * 80  # Máximo 440-520
            else:
                return max(0, 520 - (h - 14) * 70)  # Rampa down
        
        df_pv = pd.DataFrame({
            'solar_generation_kwh': [pv_profile(h) for h in hora_dia],
        }, index=dates)
        print("✅ PV sintético creado (perfil solar realista)")
    
    print()
    
    # 5. Simular despacho para un día típico
    print("-" * 80)
    print("SIMULACIÓN: DÍA 15 DE AGOSTO 2024 (día típico)")
    print("-" * 80)
    print()
    
    fecha_inicio = df_mall.index[0] + timedelta(days=14)  # Día 15
    fecha_fin = fecha_inicio + timedelta(days=1)
    
    df_dia = df_mall.loc[fecha_inicio:fecha_fin]
    df_pv_dia = df_pv.loc[fecha_inicio:fecha_fin]
    
    # Crear horas con control
    horas_simuladas = []
    
    for i, (ts, row) in enumerate(df_dia.iterrows()):
        if i >= 24:
            break
        
        demanda_mall = row['demanda_mall_kwh']
        pv_disponible = df_pv_dia.iloc[i, 0] if i < len(df_pv_dia) else 0.0
        
        # Simular despacho heurístico
        hora = int(ts) if isinstance(ts, (int, float)) else 0  # Fallback a hora 0
        
        # Estrategia simple:
        # P1: Aprovechar PV directo a EV hasta 100 kWh
        p1 = min(pv_disponible * 0.4, 100)  # 40% a EV directo, máximo 100
        
        # P2: Cargar BESS con PV restante (pre-pico es 16-17h)
        pv_restante = pv_disponible - p1
        if 15 <= hora <= 17:
            p2 = pv_restante * 0.8  # 80% a BESS pre-pico
        else:
            p2 = pv_restante * 0.5  # 50% a BESS otros horarios
        
        # P3: Descargar BESS principalmente en pico (18-21h)
        if 18 <= hora <= 21:
            p3 = 80  # Descargar BESS
        elif 16 <= hora <= 17:
            p3 = 0  # Pre-pico, no descargar
        else:
            p3 = 20  # Mínimo
        
        # P4, P5: Uso mínimo de grid (lo cubre demanda mall)
        p4 = 0
        p5 = max(0, demanda_mall - p1 - pv_restante + p3)  # Si hay déficit
        
        # BESS SOC simulation (simplificado)
        bess_soc_antes = 50 + (p2 - p3) * 0.5  # Cambio simplificado
        bess_soc_despues = min(95, max(10, bess_soc_antes))
        
        # Acciones de EV
        ev_count = int(p1 + p3)  # Número de vehículos cargando
        ev_power = (p1 + p3) / max(1, ev_count) if ev_count > 0 else 0
        
        # Crear hora
        dispatch_acciones = {
            'p1': p1, 'p2': p2, 'p3': p3, 'p4': p4, 'p5': p5,
            'bess_soc_antes': bess_soc_antes,
            'bess_soc_despues': bess_soc_despues,
            'ciclos': 0.1 if p2 > 0 or p3 > 0 else 0,
            'ev_count': ev_count,
            'ev_power': ev_power,
        }
        
        hora_control = analyzer.crear_hora_con_control(
            timestamp=ts,
            demanda_mall_kwh=demanda_mall,
            pv_disponible_kwh=pv_disponible,
            dispatch_acciones=dispatch_acciones,
        )
        
        horas_simuladas.append(hora_control)
    
    print(f"✅ {len(horas_simuladas)} horas simuladas con despacho")
    print()
    
    # 6. Generar reporte 24h
    print("-" * 80)
    print("REPORTE 24 HORAS - DEMANDA MALL + CONTROL OPERATIVO")
    print("-" * 80)
    print()
    
    reporte_24h = analyzer.generar_reporte_24h(horas_simuladas)
    print(reporte_24h)
    
    # Guardar reporte
    out_dir = Path("outputs/oe3/demanda_mall")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = out_dir / "reporte_24h_demanda_control.txt"
    report_file.write_text(reporte_24h)
    print(f"✅ Reporte guardado en: {report_file}")
    print()
    
    # 7. Generar resumen diario
    print("-" * 80)
    print("RESUMEN DIARIO (JSON)")
    print("-" * 80)
    print()
    
    resumen = analyzer.generar_reporte_diario(
        horas_simuladas,
        out_file=out_dir / "resumen_diario_demanda_control.json"
    )
    
    import json
    print(json.dumps(resumen, indent=2))
    print()
    
    # 8. Análisis de eficiencia
    print("-" * 80)
    print("ANÁLISIS DE EFICIENCIA")
    print("-" * 80)
    print()
    
    total_demanda = sum(h.demanda.demanda_mall_kwh for h in horas_simuladas)
    total_pv = sum(h.demanda.generacion_pv_kwh for h in horas_simuladas)
    total_grid = sum(h.balance.import_grid_total_kwh for h in horas_simuladas)
    total_co2 = sum(h.balance.co2_total_kg for h in horas_simuladas)
    
    pv_coverage = (total_pv / total_demanda * 100) if total_demanda > 0 else 0
    grid_ratio = (total_grid / total_demanda * 100) if total_demanda > 0 else 0
    
    print(f"Demanda total del mall:       {total_demanda:>10.0f} kWh")
    print(f"Generación solar disponible:  {total_pv:>10.0f} kWh")
    print(f"Cobertura solar:              {pv_coverage:>10.1f} %")
    print()
    print(f"Grid import total:            {total_grid:>10.0f} kWh")
    print(f"Ratio grid/demanda:           {grid_ratio:>10.1f} %")
    print()
    print(f"CO₂ emitido:                  {total_co2:>10.0f} kg")
    print(f"Intensidad CO₂:               {total_co2/total_grid:>10.4f} kg/kWh")
    print()
    print(f"Costo operativo (24h):        ${total_grid * 0.20:>10.2f}")
    print()
    
    print("=" * 80)
    print("✅ SIMULACIÓN COMPLETADA")
    print("=" * 80)


if __name__ == "__main__":
    simular_despacho_24h_ejemplo()
