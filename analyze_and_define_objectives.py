#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALISIS DE DATOS Y OBJETIVOS POR COMPONENTE
Lee datasets REALES y define metas cuantificables para entrenamiento SAC
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ComponentObjectives:
    """Objetivos cuantificables para cada componente"""
    name: str
    description: str
    objectives: Dict[str, float]  # Clave: descripcion, Valor: meta numerica
    current_performance: Dict[str, float] = None
    success_metrics: Dict[str, float] = None  # % cumplimiento


class DatasetAnalyzer:
    """Analiza datos REALES de cada componente y define objetivos"""
    
    def __init__(self, data_path: Path = Path('data')):
        self.data_path = data_path
        self.components = {}
    
    def load_solar_data(self) -> Tuple[np.ndarray, Dict]:
        """Cargar y analizar generacion SOLAR"""
        # Buscar archivo de generacion solar
        solar_candidates = [
            self.data_path / 'oe2' / 'Generacionsolar' / 'pv_daily_energy.csv',
            self.data_path / 'oe2' / 'citylearn' / 'bess_solar_generation.csv',
        ]
        
        solar_path = None
        for p in solar_candidates:
            if p.exists():
                solar_path = p
                break
        
        if solar_path is None:
            print(f"[ERROR] Solar data no encontrado")
            return np.zeros(8760), {}
        
        try:
            df = pd.read_csv(solar_path)
            
            # Buscar columna de potencia
            solar_col = None
            for col in df.columns:
                if 'power' in col.lower() or 'generation' in col.lower() or 'energia' in col.lower():
                    solar_col = col
                    break
            
            if solar_col is None:
                solar_col = df.columns[-1]  # Ultima columna
            
            # Si es daily, expandir a hourly
            if len(df) == 365:
                daily_energy_kwh = pd.to_numeric(df[solar_col].values, errors='coerce')
                solar_kw = np.repeat(daily_energy_kwh, 24)[:8760]
            else:
                solar_kw = pd.to_numeric(df[solar_col].values, errors='coerce').values[:8760]
            
            solar_kw = np.nan_to_num(solar_kw, nan=0.0)
        except Exception as e:
            print(f"[ERROR] Leyendo solar: {e}")
            return np.zeros(8760), {}
        
        print(f"\n[SOLAR] Datos cargados: {len(solar_kw)} timesteps desde {solar_path.name}")
        print(f"  Generacion total: {solar_kw.sum():,.0f} kWh/ano")
        print(f"  Generacion promedio: {np.mean(solar_kw):.1f} kW")
        print(f"  Pico generacion: {np.max(solar_kw):.1f} kW")
        print(f"  Min generacion: {np.min(solar_kw):.1f} kW")
        print(f"  Horas sin solar: {np.sum(solar_kw < 1)}")
        
        return solar_kw, {
            'total_kwh': solar_kw.sum(),
            'avg_kw': np.mean(solar_kw),
            'peak_kw': np.max(solar_kw),
            'min_kw': np.min(solar_kw),
            'zero_hours': np.sum(solar_kw < 1),
            'hours_above_1000kw': np.sum(solar_kw > 1000),
        }
    
    def load_chargers_data(self) -> Tuple[np.ndarray, Dict]:
        """Cargar y analizar demanda de CHARGERS"""
        chargers_path = self.data_path / 'oe2' / 'chargers' / 'chargers_ev_ano_2024_v3.csv'
        
        if not chargers_path.exists():
            print(f"[ERROR] Chargers data no encontrado: {chargers_path}")
            return np.zeros((8760, 38)), {}
        
        try:
            df = pd.read_csv(chargers_path)
        except Exception as e:
            print(f"[ERROR] Leyendo chargers: {e}")
            return np.zeros((8760, 38)), {}
        
        # Extraer columnas de sockets (socket_000_charger_power_kw ... socket_037_charger_power_kw)
        socket_cols = [col for col in df.columns if 'socket_' in col and 'charger_power' in col]
        
        if len(socket_cols) < 38:
            print(f"[ADVERTENCIA] Encontrados {len(socket_cols)} sockets (esperado 38)")
        
        chargers_data = df[socket_cols[:38]].astype(float).values if socket_cols else np.zeros((len(df), 38))
        if len(chargers_data) < 8760:
            chargers_data = np.vstack([chargers_data, np.zeros((8760 - len(chargers_data), 38))])
        chargers_data = chargers_data[:8760]
        
        chargers_kw = chargers_data.sum(axis=1)
        
        # Separar motos (sockets 0-29) y mototaxis (sockets 30-37)
        motos_data = chargers_data[:, :30]
        mototaxis_data = chargers_data[:, 30:38]
        
        motos_kw = motos_data.sum(axis=1)
        mototaxis_kw = mototaxis_data.sum(axis=1)
        
        print(f"\n[CHARGERS] Datos cargados: {chargers_data.shape}")
        print(f"  Total energia cargada: {float(chargers_kw.sum()):,.0f} kWh/ano")
        print(f"  Demanda promedio: {np.mean(chargers_kw):.1f} kW")
        print(f"  Pico demanda: {np.max(chargers_kw):.1f} kW")
        print()
        print(f"  MOTOS (30 sockets):")
        print(f"    Energia total: {float(motos_kw.sum()):,.0f} kWh/ano")
        print(f"    Demanda promedio: {np.mean(motos_kw):.1f} kW")
        print(f"    Horas con carga: {np.sum(motos_kw > 0)}")
        print()
        print(f"  MOTOTAXIS (8 sockets):")
        print(f"    Energia total: {float(mototaxis_kw.sum()):,.0f} kWh/ano")
        print(f"    Demanda promedio: {np.mean(mototaxis_kw):.1f} kW")
        print(f"    Horas con carga: {np.sum(mototaxis_kw > 0)}")
        
        return chargers_data, {
            'total_kwh': float(chargers_kw.sum()),
            'avg_kw': float(np.mean(chargers_kw)),
            'peak_kw': float(np.max(chargers_kw)),
            'hours_active': int(np.sum(chargers_kw > 0)),
            'motos_total_kwh': float(motos_kw.sum()),
            'motos_avg_kw': float(np.mean(motos_kw)),
            'motos_peak_kw': float(np.max(motos_kw)),
            'mototaxis_total_kwh': float(mototaxis_kw.sum()),
            'mototaxis_avg_kw': float(np.mean(mototaxis_kw)),
            'mototaxis_peak_kw': float(np.max(mototaxis_kw)),
        }
    
    def load_mall_data(self) -> Tuple[np.ndarray, Dict]:
        """Cargar y analizar demanda del MALL"""
        mall_path = self.data_path / 'oe2' / 'demandamallkwh' / 'demandamallhorakwh.csv'
        
        if not mall_path.exists():
            print(f"[ERROR] Mall data no encontrado: {mall_path}")
            return np.zeros(8760), {}
        
        try:
            df = pd.read_csv(mall_path)
        except Exception as e:
            print(f"[ERROR] Leyendo mall: {e}")
            return np.zeros(8760), {}
        
        # Obtener columna de demanda
        demand_col = None
        for col in df.columns:
            if 'kWh' in col or 'kwh' in col.lower() or 'power' in col.lower():
                demand_col = col
                break
        
        if demand_col is None:
            demand_col = df.columns[-1]
        
        mall_kw = pd.to_numeric(df[demand_col], errors='coerce').values
        mall_kw = np.nan_to_num(mall_kw, nan=0.0)
        
        if len(mall_kw) < 8760:
            mall_kw = np.hstack([mall_kw, np.zeros(8760 - len(mall_kw))])
        mall_kw = mall_kw[:8760]
        
        # Identificar horas pico
        pico_hours = []
        normal_hours = []
        for h in range(len(mall_kw)):
            hour_of_day = h % 24
            if 18 <= hour_of_day <= 22:
                pico_hours.append(h)
            else:
                normal_hours.append(h)
        
        pico_demand = np.array([mall_kw[h] for h in pico_hours])
        normal_demand = np.array([mall_kw[h] for h in normal_hours])
        
        print(f"\n[MALL] Datos cargados: {len(mall_kw)} timesteps")
        print(f"  Demanda total: {float(mall_kw.sum()):,.0f} kWh/ano")
        print(f"  Demanda promedio: {np.mean(mall_kw):.1f} kW")
        print(f"  Pico demanda: {float(np.max(mall_kw)):.1f} kW")
        print()
        print(f"  HORAS NORMALES (0-17:59, 22:00-23:59):")
        print(f"    Demanda promedio: {np.mean(normal_demand):.1f} kW")
        print(f"    Demanda max: {float(np.max(normal_demand)):.1f} kW")
        print()
        print(f"  HORAS PICO (18:00-22:00):")
        print(f"    Demanda promedio: {np.mean(pico_demand):.1f} kW")
        print(f"    Demanda max: {float(np.max(pico_demand)):.1f} kW")
        print(f"    Horas con demanda >2000kW: {np.sum(pico_demand > 2000)}")
        
        return mall_kw, {
            'total_kwh': float(mall_kw.sum()),
            'avg_kw': float(np.mean(mall_kw)),
            'peak_kw': float(np.max(mall_kw)),
            'peak_hours_above_2000kw': int(np.sum(pico_demand > 2000)),
            'pico_avg_kw': float(np.mean(pico_demand)),
            'normal_avg_kw': float(np.mean(normal_demand)),
        }
    
    def load_bess_data(self) -> Tuple[np.ndarray, Dict]:
        """Cargar y analizar simulacion BESS"""
        bess_path = self.data_path / 'oe2' / 'bess' / 'bess_ano_2024.csv'
        
        if not bess_path.exists():
            print(f"[ERROR] BESS data no encontrado: {bess_path}")
            return np.zeros(8760), {}
        
        try:
            df = pd.read_csv(bess_path)
        except Exception as e:
            print(f"[ERROR] Leyendo BESS: {e}")
            return np.zeros(8760), {}
        
        soc = pd.to_numeric(df['bess_soc_percent'].values, errors='coerce') if 'bess_soc_percent' in df.columns else np.zeros(8760)
        co2_avoided = pd.to_numeric(df['co2_avoided_indirect_kg'].values, errors='coerce') if 'co2_avoided_indirect_kg' in df.columns else np.zeros(8760)
        
        # Extraer flujos si existen
        charge = pd.to_numeric(df['bess_charge_kwh'].values, errors='coerce') if 'bess_charge_kwh' in df.columns else np.zeros(8760)
        discharge = pd.to_numeric(df['bess_discharge_kwh'].values, errors='coerce') if 'bess_discharge_kwh' in df.columns else np.zeros(8760)
        
        soc = np.nan_to_num(soc, nan=50.0)
        
        print(f"\n[BESS] Datos cargados: {len(soc)} timesteps")
        print(f"  SOC promedio: {np.mean(soc):.1f}%")
        print(f"  SOC min: {np.min(soc):.1f}%")
        print(f"  SOC max: {np.max(soc):.1f}%")
        print(f"  Horas con SOC <20%: {np.sum(soc < 20)}")
        print(f"  Horas con SOC >80%: {np.sum(soc > 80)}")
        print()
        print(f"  Energia cargada total: {float(charge.sum()):,.0f} kWh/ano")
        print(f"  Energia descargada total: {float(discharge.sum()):,.0f} kWh/ano")
        print(f"  CO2 evitado indirect: {float(co2_avoided.sum()):,.0f} kg/ano")
        
        return soc, {
            'avg_soc': float(np.mean(soc)),
            'min_soc': float(np.min(soc)),
            'max_soc': float(np.max(soc)),
            'hours_low_soc': int(np.sum(soc < 20)),
            'hours_high_soc': int(np.sum(soc > 80)),
            'charge_total_kwh': float(charge.sum()),
            'discharge_total_kwh': float(discharge.sum()),
            'co2_avoided_kg': float(co2_avoided.sum()),
        }
    
    def analyze_all(self) -> Dict[str, ComponentObjectives]:
        """Analizar todos los componentes y generar objetivos"""
        
        print("\n" + "="*80)
        print("ANALISIS DE DATASETS Y GENERACION DE OBJETIVOS")
        print("="*80)
        
        # Cargar datos
        solar_kw, solar_stats = self.load_solar_data()
        chargers_data, chargers_stats = self.load_chargers_data()
        mall_kw, mall_stats = self.load_mall_data()
        bess_soc, bess_stats = self.load_bess_data()
        
        # Definir objetivos por componente
        objectives = {}
        
        # OBJETIVO 1: MOTOS (30 sockets)
        print("\n" + "-"*80)
        print("DEFINIENDO OBJETIVOS: MOTOS (30 sockets)")
        print("-"*80)
        
        # En el dataset hay X horas de carga motos
        motos_data_horas = chargers_data[:, :30]
        motos_with_demand_hours = np.sum(motos_data_horas.sum(axis=1) > 1.0)  # Horas con carga >1kW
        
        # Objetivo: cargar el maximo posible dado tiempo disponible
        # 270 motos/dia * 365 dias = 98,550 ciclos/ano
        # Si disponemos energia para 25 motos/dia * 365 = 9,125 cargas completas
        motos_target_charged_100_per_day = 25  # Meta: 25 motos a 100% por dia (83% de 30)
        motos_target_per_year = motos_target_charged_100_per_day * 365
        
        print(f"\n  Dataset MOTOS:")
        print(f"    Horas con demanda: {motos_with_demand_hours}")
        print(f"    Energia media por hora de carga: {chargers_stats['motos_avg_kw']:.2f} kW")
        
        print(f"\n  OBJETIVOS MOTOS:")
        print(f"    Meta 1: Cargar {motos_target_charged_100_per_day} motos a 100% cada dia")
        print(f"    Meta 2: Cargar {motos_target_per_year} motos a 100% en el ano")
        print(f"    Meta 3: Mantener SOC promedio motos >60%")
        print(f"    Meta 4: Resolver 95% de urgencias (tiempo bajo)")
        
        objectives['motos'] = ComponentObjectives(
            name='Motos (30 sockets)',
            description='Cargar personal motorcycles durante disponibilidad solar + BESS',
            objectives={
                'charged_100_per_day': motos_target_charged_100_per_day,
                'charged_100_per_year': motos_target_per_year,
                'avg_soc_target': 0.60,
                'urgent_resolution_rate': 0.95,
                'energy_efficiency': 0.85,  # % energia solar+BESS vs grid
            }
        )
        
        # OBJETIVO 2: MOTOTAXIS (8 sockets)
        print("\n" + "-"*80)
        print("DEFINIENDO OBJETIVOS: MOTOTAXIS (8 sockets)")
        print("-"*80)
        
        mototaxis_data_horas = chargers_data[:, 30:38]
        mototaxis_with_demand_hours = np.sum(mototaxis_data_horas.sum(axis=1) > 1.0)
        
        # 39 mototaxis/dia * 365 dias = 14,235 ciclos/ano
        # Meta: 7.5 mototaxis a 100% por dia (94% de 8)
        mototaxis_target_charged_100_per_day = 7.5
        mototaxis_target_per_year = int(mototaxis_target_charged_100_per_day * 365)
        
        print(f"\n  Dataset MOTOTAXIS:")
        print(f"    Horas con demanda: {mototaxis_with_demand_hours}")
        print(f"    Energia media por hora de carga: {chargers_stats['mototaxis_avg_kw']:.2f} kW")
        
        print(f"\n  OBJETIVOS MOTOTAXIS:")
        print(f"    Meta 1: Cargar {mototaxis_target_charged_100_per_day:.1f} mototaxis a 100% cada dia")
        print(f"    Meta 2: Cargar {mototaxis_target_per_year} mototaxis a 100% en el ano")
        print(f"    Meta 3: Mantener SOC promedio mototaxis >70% (viajes largos)")
        print(f"    Meta 4: Resolver 99% de urgencias (viajes largos prioritarios)")
        
        objectives['mototaxis'] = ComponentObjectives(
            name='Mototaxis (8 sockets)',
            description='Cargar taxi motorcycles con prioridad por viajes largos',
            objectives={
                'charged_100_per_day': mototaxis_target_charged_100_per_day,
                'charged_100_per_year': mototaxis_target_per_year,
                'avg_soc_target': 0.70,
                'urgent_resolution_rate': 0.99,
                'energy_efficiency': 0.88,
            }
        )
        
        # OBJETIVO 3: BESS
        print("\n" + "-"*80)
        print("DEFINIENDO OBJETIVOS: BESS (940 kWh)")
        print("-"*80)
        
        # BESS debe mantener SOC >30% durante pico (18:00-22:00)
        pico_hours = [h for h in range(8760) if (h % 24) >= 18 and (h % 24) <= 22]
        pico_soc = np.array([bess_stats['avg_soc'] if i < len(bess_soc) else 50 for i, h in enumerate(pico_hours)])
        
        print(f"\n  Dataset BESS:")
        print(f"    SOC promedio dataset: {bess_stats['avg_soc']:.1f}%")
        print(f"    Horas bajo 20%: {bess_stats['hours_low_soc']}")
        print(f"    CO2 evitado dataset: {bess_stats['co2_avoided_kg']:,.0f} kg/ano")
        
        print(f"\n  OBJETIVOS BESS:")
        print(f"    Meta 1: Mantener SOC >30% durante picos (18:00-22:00)")
        print(f"    Meta 2: Descargar >1.2 GWh/ano (electricidad que desplaza grid)")
        print(f"    Meta 3: Cargar desde solar excedente (min 50% de carga)")
        print(f"    Meta 4: Ciclos <500/ano (evitar degradacion)")
        
        pico_bess_target_soc = 0.30
        bess_discharge_target_kwh = 1200000  # 1.2 GWh
        
        objectives['bess'] = ComponentObjectives(
            name='BESS (940 kWh)',
            description='Almacenar solar, ayudar EVs, cortar demanda mall >2000kW',
            objectives={
                'pico_min_soc': pico_bess_target_soc,
                'discharge_target_kwh': bess_discharge_target_kwh,
                'charge_from_solar_ratio': 0.50,
                'max_cycles_per_year': 500,
                'solar_curtailment_avoided_kwh': 500000,  # Evitar perder 500 MWh solar
            }
        )
        
        # OBJETIVO 4: MALL
        print("\n" + "-"*80)
        print("DEFINIENDO OBJETIVOS: MALL")
        print("-"*80)
        
        high_demand_hours = np.sum(mall_kw > 2000)  # Horas con demanda >2000kW
        
        print(f"\n  Dataset MALL:")
        print(f"    Demanda total: {mall_stats['total_kwh']:,.0f} kWh/ano")
        print(f"    Horas demanda >2000kW: {high_demand_hours}")
        print(f"    Pico máximo: {mall_stats['peak_kw']:.1f} kW")
        
        print(f"\n  OBJETIVOS MALL:")
        print(f"    Meta 1: Suministrar 100% demanda en horas normales")
        print(f"    Meta 2: EN PICOS (>2000kW): cortar a 0% (prioridad EVs)")
        print(f"    Meta 3: Usar 40% solar + 20% BESS en horas normales")
        print(f"    Meta 4: No importar >80% de demanda del grid")
        
        objectives['mall'] = ComponentObjectives(
            name='Mall',
            description='Suministro con corte inteligente en picos',
            objectives={
                'normal_hours_supply_100': 1.0,
                'peak_hours_cutoff_to_zero': 1.0,
                'solar_penetration_normal': 0.40,
                'bess_penetration_normal': 0.20,
                'grid_import_ratio_max': 0.80,
            }
        )
        
        # OBJETIVO GLOBAL: CO2
        print("\n" + "-"*80)
        print("DEFINIENDO OBJETIVOS GLOBALES: REDUCCION CO2")
        print("-"*80)
        
        print(f"\n  BASELINE (sin control):")
        print(f"    Grid import: ~70% de demanda total")
        print(f"    CO2 anual: ~640,000 kg (7800 kg/GWh, demanda 82 GWh)")
        
        print(f"\n  OBJETIVO CON CONTROL:")
        print(f"    Grid import: <30% de demanda total")
        print(f"    CO2 anual: <350,000 kg (reduccion >46%)")
        print(f"    Solar utilizado: >90% (evitar cortaduras)")
        
        objectives['co2'] = ComponentObjectives(
            name='CO2 Global',
            description='Minimizar emisiones red térmica',
            objectives={
                'grid_import_ratio_max': 0.30,
                'annual_co2_kg_max': 350000,
                'solar_utilization_ratio': 0.90,
                'ev_co2_displacement_kg': 2000000,  # Motos evitan 2M kg CO2 vs gasolina
            }
        )
        
        return objectives


def print_training_objectives(objectives: Dict[str, ComponentObjectives]):
    """Imprime resumen de objetivos para entrenamiento"""
    
    print("\n" + "="*80)
    print("RESUMEN DE OBJETIVOS PARA ENTRENAMIENTO SAC")
    print("="*80)
    
    print(f"\nEl agente SAC debe cumplir estos objetivos simultaneamente:")
    
    for comp_name, comp_obj in objectives.items():
        print(f"\n{comp_obj.name}:")
        print(f"  {comp_obj.description}")
        for obj_name, obj_target in comp_obj.objectives.items():
            if isinstance(obj_target, float) and obj_target < 10:
                print(f"    - {obj_name}: {obj_target:.2%}" if obj_target <= 1 else f"    - {obj_name}: {obj_target:.2f}")
            else:
                print(f"    - {obj_name}: {obj_target:,.0f}")


if __name__ == '__main__':
    analyzer = DatasetAnalyzer()
    objectives = analyzer.analyze_all()
    print_training_objectives(objectives)
    
    print("\n" + "="*80)
    print("LISTO PARA ENTRENAMIENTO")
    print("="*80)
    print("\nPasos siguientes:")
    print("  1. Cargar estos objetivos en train_sac_multiobjetivo.py")
    print("  2. Crear reward function que recompense cada objetivo")
    print("  3. Entrenar agente SAC")
    print("  4. Monitorear progreso hacia meta por componente")
    print("  5. Reportar % cumplimiento final de cada objetivo")
