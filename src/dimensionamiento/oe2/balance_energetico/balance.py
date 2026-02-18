"""
Balance Energetico del Sistema Electrico de Iquitos v5.4.

Modulo para cargar todos los datasets de OE2 e integrarlos en un analisis 
completo del balance energetico, considerando:
- Generacion solar PV (4,050 kWp) - data/oe2/Generacionsolar/pv_generation_citylearn2024_clean.csv
  * 8,292,514 kWh/ano | 11 columnas (con OSINERGMIN + CO₂ indirecto)
- Demanda del mall (RED PUBLICA) - data/oe2/demandamallkwh/demandamallhorakwh.csv
  * 12,403,168 kWh/ano (33,981 kWh/dia, 2,763 kW pico)
- Demanda EV (38 tomas v5.2) - data/oe2/chargers/chargers_ev_ano_2024_v3.csv
  * 565,875 kWh/ano (1,550 kWh/dia, ~119 kW pico) - Solo 9h-22h
  * 38 sockets = 19 cargadores × 2 tomas (270 motos + 39 mototaxis/día)
- Almacenamiento BESS - data/oe2/bess/bess_ano_2024.csv
  * 1,700 kWh capacidad / 400 kW potencia (v5.4)

REDUCCION DE CO₂ v5.3:
---------------------------------------------------------------------------
1. INDIRECTA (Solar desplaza diesel para Mall+EV):
   - CO₂ evitado: 3,749 ton/ano (factor 0.4521 kg/kWh)
   - Desglose: Mall 67% (2,499 ton) + EV 33% (1,250 ton)
   
2. DIRECTA (Cambio combustible gasolina -> electrico):
   - CO₂ evitado: 357 ton/ano
   - Motos: 0.87 kg CO₂/kWh neto (312 ton)
   - Mototaxis: 0.47 kg CO₂/kWh neto (44 ton)
   
TOTAL CO₂ EVITADO: 4,106 ton/ano
---------------------------------------------------------------------------

TARIFAS OSINERGMIN (Electro Oriente S.A. - Iquitos):
- Hora Punta (HP): S/.0.45/kWh (18:00-22:59)
- Hora Fuera de Punta (HFP): S/.0.28/kWh (resto)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import math
import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


@dataclass(frozen=True)
class BalanceEnergeticoConfig:
    """Configuracion del analisis de balance energetico v5.4.
    
    Rutas de datos OE2 REALES:
    - Solar: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
      * 8,292,514 kWh/ano | 11 columnas
      * Columnas: potencia_kw, energia_kwh, is_hora_punta, tarifa_aplicada_soles, ahorro_solar_soles, reduccion_indirecta_co2_kg
      
    - Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv
      * 12,403,168 kWh/ano (RED PUBLICA)
      
    - EV: data/oe2/chargers/chargers_ev_ano_2024_v3.csv
      * 565,875 kWh/ano | 38 sockets v5.2 | 9h-22h
      * Columnas socket: socket_XXX_{charger_power_kw, charging_power_kw, soc_*, active, vehicle_*}
      * Columnas CO₂: reduccion_directa_co2_kg, co2_reduccion_motos_kg, co2_reduccion_mototaxis_kg
      * Columnas OSINERGMIN: is_hora_punta, tarifa_aplicada_soles, costo_carga_ev_soles
      * Alias CityLearn: ev_demand_kwh, ev_energia_total_kwh
    """
    
    # ==========================================
    # RUTAS DE DATOS OE2 - ARCHIVOS REALES v5.4
    # ==========================================
    data_dir_oe2: Path = Path("data/oe2")
    
    # Archivos especificos OE2 v5.4 (datasets reales validados)
    solar_path: Path = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    mall_path: Path = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    chargers_path: Path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    bess_path: Path = Path("data/oe2/bess/bess_ano_2024.csv")
    
    # ==========================================
    # PARAMETROS DEL SISTEMA v5.2
    # ==========================================
    pv_capacity_kwp: float = 4050.0  # kW pico solar (genera 8,292,514 kWh/ano)
    
    # Restriccion de demanda pico (limite RED PUBLICA Iquitos)
    demand_peak_limit_kw: float = 2000.0  # kW maximo (BESS intenta reducir)
    
    # BESS - valores calculados dinamicamente por bess.py
    # Estos son valores por defecto, se actualizan con load_bess_sizing()
    bess_capacity_kwh: float = 1700.0  # kWh almacenamiento (v5.3: exclusivo EV + picos)
    bess_power_kw: float = 400.0  # kW potencia nominal (0.36 C-rate)
    dod: float = 0.80  # Profundidad de descarga (80% para SOC 20%-100%)
    efficiency_roundtrip: float = 0.95  # Eficiencia round-trip (95%)
    
    # ==========================================
    # PARAMETROS DE CALCULO
    # ==========================================
    year: int = 2024
    timezone: str = "America/Lima"  # UTC-5
    co2_intensity_kg_per_kwh: float = 0.4521  # kg CO2/kWh (generacion termica Iquitos)


class BalanceEnergeticoSystem:
    """Sistema integrado de balance energetico v5.2.
    
    Carga datos desde archivos OE2 reales y calcula balance energetico.
    """
    
    def __init__(self, config: Optional[BalanceEnergeticoConfig] = None):
        """
        Inicializa el sistema de balance energetico.
        
        Args:
            config: Configuracion del analisis (usa defaults si es None)
        """
        self.config = config or BalanceEnergeticoConfig()
        
        # Rutas de datos OE2
        self.solar_path = Path(self.config.solar_path)
        self.mall_path = Path(self.config.mall_path)
        self.chargers_path = Path(self.config.chargers_path)
        
        # Datasets cargados
        self.df_solar: Optional[pd.DataFrame] = None
        self.df_chargers: Optional[pd.DataFrame] = None
        self.df_mall: Optional[pd.DataFrame] = None
        self.df_bess: Optional[pd.DataFrame] = None  # Opcional: simulacion BESS
        
        # Balance calculado
        self.df_balance: Optional[pd.DataFrame] = None
        self.metrics: Dict[str, float] = {}
    
    def load_all_datasets(self) -> bool:
        """
        Carga todos los datasets de OE2 (archivos reales v5.4).
        
        Archivos fuente:
        - Solar: data/oe2/Generacionsolar/pv_generation_citylearn2024_clean.csv (8,292,514 kWh/ano)
        - Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv (12,403,168 kWh/ano)
        - EV: data/oe2/chargers/chargers_ev_ano_2024_v3.csv (565,875 kWh/ano, 38 sockets)
        - BESS: data/oe2/bess/bess_ano_2024.csv (1,700 kWh / 400 kW)
        
        Returns:
            True si todos los datasets se cargaron exitosamente
        """
        print("\nCargando datasets OE2 (archivos reales)...")
        print("="*60)
        
        try:
            # 1. Carga solar PV (8,292,514 kWh/ano - citylearn_v2)
            if self.solar_path.exists():
                self.df_solar = self._load_csv_flexible(self.solar_path)
                # Columnas prioritarias: pv_generation_kwh (v2), ac_energy_kwh (v2), energia_kwh (legacy)
                solar_col = next((c for c in ['pv_generation_kwh', 'ac_energy_kwh', 'energia_kwh'] if c in self.df_solar.columns), None)
                solar_kwh = self.df_solar[solar_col].sum() if solar_col else 0
                print(f"  [OK] Solar PV: {self.solar_path.name}")
                print(f"    - {len(self.df_solar)} horas | {solar_kwh:,.0f} kWh/ano | col: {solar_col}")
            else:
                print(f"  [X] Solar PV no encontrada: {self.solar_path}")
                return False
            
            # 2. Carga demanda EV (38 sockets v5.2, 412,236 kWh/ano, 9h-22h)
            if self.chargers_path.exists():
                self.df_chargers = self._load_csv_flexible(self.chargers_path)
                # Buscar columnas de potencia REAL de sockets (v5.2: socket_NNN_charging_power_kw)
                # IMPORTANTE: charging_power_kw = demanda real, charger_power_kw = capacidad (NO usar)
                power_cols = [col for col in self.df_chargers.columns if 'charging_power_kw' in col.lower()]
                if not power_cols:
                    # Legacy: MOTO_XX_SOCKET_Y, MOTOTAXI_XX_SOCKET_Y
                    power_cols = [col for col in self.df_chargers.columns if 'SOCKET' in col.upper()]
                ev_kwh = self.df_chargers[power_cols].sum().sum() if power_cols else 0
                print(f"  [OK] Chargers EV: {self.chargers_path.name}")
                print(f"    - {len(self.df_chargers)} horas | {len(power_cols)} sockets | {ev_kwh:,.0f} kWh/ano")
            else:
                print(f"  [X] Chargers EV no encontrada: {self.chargers_path}")
                return False
            
            # 3. Carga demanda mall (RED PUBLICA, 12,403,168 kWh/ano)
            if self.mall_path.exists():
                self.df_mall = self._load_csv_flexible(self.mall_path)
                # Truncar a 8760 si tiene mas filas (algunos CSV tienen filas extra)
                if len(self.df_mall) > 8760:
                    print(f"    [!] Truncando de {len(self.df_mall)} a 8,760 filas")
                    self.df_mall = self.df_mall.iloc[:8760].copy()
                # Buscar columna de demanda
                demand_cols = [c for c in self.df_mall.columns if 'kWh' in c or 'kwh' in c.lower() or 'demand' in c.lower()]
                mall_kwh = self.df_mall[demand_cols[0]].sum() if demand_cols else 0
                print(f"  [OK] Demanda Mall (RED PUBLICA): {self.mall_path.name}")
                print(f"    - {len(self.df_mall)} horas | {mall_kwh:,.0f} kWh/ano")
            else:
                print(f"  [X] Demanda Mall no encontrada: {self.mall_path}")
                return False
            
            # 4. BESS simulacion desde OE2 (bess_ano_2024.csv)
            bess_sim_path = Path("data/oe2/bess/bess_ano_2024.csv")
            if bess_sim_path.exists():
                self.df_bess = self._load_csv_flexible(bess_sim_path)
                # Verificar columnas de carga/descarga
                bess_charge_total = self.df_bess['bess_charge_kwh'].sum() if 'bess_charge_kwh' in self.df_bess.columns else 0
                bess_discharge_total = self.df_bess['bess_discharge_kwh'].sum() if 'bess_discharge_kwh' in self.df_bess.columns else 0
                print(f"  OK BESS Simulation: {bess_sim_path.name} ({len(self.df_bess)} horas)")
                print(f"    - Carga: {bess_charge_total:,.0f} kWh/ano | Descarga: {bess_discharge_total:,.0f} kWh/ano")
            else:
                print(f"  WARN BESS Simulation no encontrada (opcional): {bess_sim_path}")
                self.df_bess = None  # BESS es opcional
            
            # Validar consistencia solar/mall/ev
            lengths = [len(self.df_solar), len(self.df_chargers), len(self.df_mall)]
            if len(set(lengths)) > 1:
                print(f"  [!] ADVERTENCIA: Longitudes inconsistentes: {lengths}")
                return False
            
            if lengths[0] != 8760:
                print(f"  [!] ADVERTENCIA: Se esperan 8,760 horas, se encontraron {lengths[0]}")
                return False
            
            print(f"  [OK] Todos los datasets cargados exitosamente (8,760 horas = 1 ano)")
            return True
            
        except Exception as e:
            print(f"  [X] Error al cargar datasets: {e}")
            return False
    
    def _load_csv_flexible(self, filepath: Path) -> pd.DataFrame:
        """
        Carga un CSV detectando automaticamente el delimitador.
        
        Args:
            filepath: Ruta del archivo CSV
        
        Returns:
            DataFrame cargado
        """
        # Intentar con diferentes delimitadores
        for sep in [',', ';', '\t']:
            try:
                df = pd.read_csv(filepath, sep=sep)
                # Verificar que se haya cargado correctamente
                # Si tiene solo una columna pero contiene el delimitador, es un mal cargue
                if len(df.columns) == 1 and sep in str(df.columns[0]):
                    # Mal cargado, intentar siguiente delimitador
                    continue
                
                # Si tiene mas de una columna o la columna no contiene delimitadores, es correcto
                if len(df.columns) > 1:
                    return df
                
                # Si solo tiene una columna pero no contiene delimitadores y no contiene otros seps
                if not any(s in str(df.columns[0]) for s in [',', ';', '\t']):
                    return df
                    
            except Exception:
                pass
        
        # Si nada funciono, intentar con el delimitador por defecto
        return pd.read_csv(filepath)
    
    def calculate_balance(self) -> pd.DataFrame:
        """
        Calcula el balance energetico integral del sistema v5.2.
        
        Flujo energetico (SIN BESS - balance base):
        PV -> EV + Mall (prioridad solar)
        Red -> (EV + Mall - PV) (deficit cubierto por red publica)
        
        Con BESS (si disponible) - ESTRATEGIA SOLAR-PRIORITY v5.4:
        PRIORIDADES DE CARGA (cuando PV > demanda):
        1. PV -> EV (directo)
        2. PV -> Mall (directo)
        3. PV excedente -> BESS (carga a 100%)
        
        PRIORIDADES DE DESCARGA (cuando deficit o exceso demanda):
        1. Limitar picos: Si (EV+Mall) > 2000 kW, BESS descarga para reducir
        2. Cubrir deficit EV: Si PV < EV y SOC > 20%
        3. Cubrir deficit Mall: Si PV < Mall y SOC > 20%
        
        RESTRICCIONES:
        - SOC operacional: 20%-100% (DoD: 80%)
        - Horario operativo: 6h-22h (fuera: sin carga/descarga BESS)
        - Limite demanda recomendado: 2000 kW (Red Publica)
        
        NOTA: Actual potencia (400 kW) reduce pero no elimina picos > 2000 kW
              Para limitar completamente se necesitaria ~900 kW de potencia
        
        Returns:
            DataFrame con el balance horario completo (8,760 horas)
        """
        if any(df is None for df in [self.df_solar, self.df_chargers, self.df_mall]):
            raise ValueError("Primero debe cargar los datasets (solar, chargers, mall)")
        
        print("\nCalculando balance energetico v5.2...")
        print("="*60)
        
        # ==========================================
        # EXTRAER COLUMNAS DE DATOS OE2 REALES
        # ==========================================
        
        # Solar: columna 'pv_generation_kwh' (citylearn_v2) o 'energia_kwh' (legacy)
        solar_gen = self._extract_column(self.df_solar, ["pv_generation_kwh", "ac_energy_kwh", "energia_kwh", "potencia_kw", "pv_kwh"])
        
        # EV: suma de todos los sockets (MOTO_XX_SOCKET_Y, MOTOTAXI_XX_SOCKET_Y)
        ev_demand = self._extract_column(self.df_chargers, ["total_demand_kw"])  # _extract_column maneja sockets
        
        # Mall: columna 'kWh' del archivo demandamallhorakwh.csv
        mall_demand = self._extract_column(self.df_mall, ["kWh", "kwh", "demand_kw", "demandamallkwh"])
        
        # BESS estado (opcional - puede ser None)
        has_bess = self.df_bess is not None
        n_hours = len(solar_gen)
        
        if has_bess and self.df_bess is not None:
            # Usar columnas del dataset OE2: bess_ano_2024.csv
            df_bess = self.df_bess  # Type narrowing para Pylance
            bess_cols = list(df_bess.columns)
            
            # Dataset OE2 tiene: bess_charge_kwh, bess_discharge_kwh, bess_action_kwh, soc_percent, bess_mode
            if 'bess_action_kwh' in bess_cols:
                # Usar bess_action_kwh directamente (contiene carga OR descarga, siempre positivo)
                bess_action = np.array(df_bess['bess_action_kwh'].values, dtype=float)
                bess_charge = np.array(df_bess['bess_charge_kwh'].values, dtype=float) if 'bess_charge_kwh' in bess_cols else np.zeros(len(df_bess))
                bess_discharge = np.array(df_bess['bess_discharge_kwh'].values, dtype=float) if 'bess_discharge_kwh' in bess_cols else np.zeros(len(df_bess))
                bess_soc = np.array(df_bess['soc_percent'].values, dtype=float) if 'soc_percent' in bess_cols else np.zeros(len(df_bess))
                bess_mode = np.array(df_bess['bess_mode'].values) if 'bess_mode' in bess_cols else np.array(['idle'] * len(df_bess))
                print(f"  OK BESS: Usando bess_action_kwh (carga/descarga combinado)")
                print(f"    - Accion total: {float(np.sum(bess_action)):,.0f} kWh/ano")
                print(f"    - SOC: {float(np.min(bess_soc)):.1f}% - {float(np.max(bess_soc)):.1f}%")
                print(f"    - Modos: idle={int(np.sum(bess_mode=='idle'))}, charge={int(np.sum(bess_mode=='charge'))}, discharge={int(np.sum(bess_mode=='discharge'))}")
            elif 'bess_charge_kwh' in bess_cols and 'bess_discharge_kwh' in bess_cols:
                bess_charge = np.array(df_bess['bess_charge_kwh'].values, dtype=float)
                bess_discharge = np.array(df_bess['bess_discharge_kwh'].values, dtype=float)
                bess_action = bess_charge + bess_discharge  # Calcular action si no existe
                bess_soc = np.array(df_bess['soc_percent'].values, dtype=float) if 'soc_percent' in bess_cols else np.zeros(len(df_bess))
                bess_mode = np.array(df_bess['bess_mode'].values) if 'bess_mode' in bess_cols else np.array(['idle'] * len(df_bess))
                print(f"  OK BESS: Calculando bess_action desde charge+discharge")
            else:
                has_bess = False
                bess_action = np.zeros(n_hours)
                bess_mode = np.array(['idle'] * n_hours)
        
        if not has_bess:
            # Sin BESS: arrays de ceros
            bess_soc = np.zeros(n_hours)
            bess_charge = np.zeros(n_hours)
            bess_discharge = np.zeros(n_hours)
            bess_action = np.zeros(n_hours)
            bess_mode = np.array(['idle'] * n_hours)
            print("  WARN Sin simulacion BESS - calculando balance base (Red cubre deficit)")
        
        # Validar dimensiones
        n_hours = len(solar_gen)
        if not all(len(x) == n_hours for x in [ev_demand, mall_demand]):
            raise ValueError(f"Longitudes inconsistentes: solar={len(solar_gen)}, ev={len(ev_demand)}, mall={len(mall_demand)}")
        
        # ==========================================
        # CALCULAR FLUJOS ENERGETICOS
        # ==========================================
        
        # Demanda total = Mall (RED PUBLICA) + EV (38 sockets)
        total_demand = ev_demand + mall_demand
        pv_available = solar_gen
        
        # PV directo a demanda (prioridad: cubrir demanda primero)
        pv_to_demand = np.minimum(pv_available.astype(float), total_demand.astype(float))
        pv_surplus = np.maximum(pv_available.astype(float) - total_demand.astype(float), 0)
        
        # Deficit (demanda no cubierta por PV)
        demand_deficit = np.maximum(total_demand.astype(float) - pv_available.astype(float), 0)
        
        # Cobertura de BESS (si disponible)
        bess_to_demand = np.minimum(bess_discharge.astype(float), demand_deficit.astype(float))
        demand_from_grid = np.maximum(demand_deficit.astype(float) - bess_to_demand.astype(float), 0)
        
        # PV excedente: carga BESS o exporta (sin uso en sistema aislado)
        pv_to_bess = np.minimum(bess_charge.astype(float), pv_surplus.astype(float))
        pv_to_grid = np.maximum(pv_surplus - pv_to_bess, 0)  # Excedente no aprovechado
        
        # Calcular emisiones
        co2_from_grid = demand_from_grid * self.config.co2_intensity_kg_per_kwh / 1000  # kg
        
        # ANALISIS DE PICOS (5.4): Verificar control de demanda maxima
        peak_limit = self.config.demand_peak_limit_kw
        demand_after_bess = demand_deficit - bess_to_demand  # Demanda que debe cubrir red
        peak_exceeded = np.maximum(total_demand - peak_limit, 0)  # Exceso sobre 2000 kW
        
        # DataFrame de balance
        df_balance = pd.DataFrame({
            'hour': np.arange(n_hours),
            'pv_generation_kw': pv_available,
            'ev_demand_kw': ev_demand,
            'mall_demand_kw': mall_demand,
            'total_demand_kw': total_demand,
            'pv_to_demand_kw': pv_to_demand,
            'pv_surplus_kw': pv_surplus,
            'pv_to_bess_kw': pv_to_bess,
            'pv_to_grid_kw': pv_to_grid,
            'bess_charge_kw': bess_charge,
            'bess_discharge_kw': bess_discharge,
            'bess_action_kw': bess_action,  # Carga/descarga combinado (siempre positivo)
            'bess_mode': bess_mode,  # idle / charge / discharge
            'bess_to_demand_kw': bess_to_demand,
            'demand_from_grid_kw': demand_from_grid,
            'bess_soc_percent': bess_soc,
            'peak_exceeded_above_2000kw': peak_exceeded,  # Exceso sobre limite
            'co2_from_grid_kg': co2_from_grid,
        })
        
        self.df_balance = df_balance
        print(f"  [OK] Balance calculado para {n_hours} horas")
        
        # Calcular metricas
        self._calculate_metrics()
        
        return df_balance
    
    def _extract_column(self, df: pd.DataFrame, candidates: List[str]) -> np.ndarray:
        """Extrae una columna de un DataFrame buscando entre candidatos.
        
        Casos especiales:
        - Para chargers v5.2: socket_NNN_charging_power_kw (38 sockets - demanda REAL)
          * charging_power_kw = potencia real usada (variable, 0-7.4 kW)
          * charger_power_kw = capacidad maxima (fija, 7.4 kW) - NO USAR
        - Para chargers legacy: MOTO_XX_SOCKET_Y, MOTOTAXI_XX_SOCKET_Y
        - Para mall: Busca variaciones de nombres de columna
        """
        # Caso especial: Chargers v5.2 - DEMANDA REAL (charging_power_kw)
        charging_cols = [col for col in df.columns if 'charging_power_kw' in col.lower()]
        if len(charging_cols) > 0:  # Es un archivo de chargers v5.2
            # Sumar todos los sockets - demanda real
            return np.array(df[charging_cols].sum(axis=1).values, dtype=float)
        
        # Caso especial: Chargers legacy (MOTO_XX_SOCKET_Y, MOTOTAXI_XX_SOCKET_Y)
        socket_cols = [col for col in df.columns if 'SOCKET' in col.upper()]
        if len(socket_cols) > 0:  # Es un archivo de chargers legacy
            # Sumar todos los sockets
            return np.array(df[socket_cols].sum(axis=1).values, dtype=float)
        
        # Caso normal: buscar columna unica
        # Normalizar nombres de columna (minusculas, sin espacios)
        normalized_cols = {col.lower().strip(): col for col in df.columns}
        normalized_candidates = [c.lower().strip() for c in candidates]
        
        for norm_cand in normalized_candidates:
            if norm_cand in normalized_cols:
                actual_col = normalized_cols[norm_cand]
                return np.array(df[actual_col].values, dtype=float)
        
        # Si no encuentra columnas exactas, buscar por contener la palabra clave
        for keyword in ['kWh', 'kwh', 'demand', 'energy', 'power', 'soc', 'charge']:
            for col in df.columns:
                if keyword.lower() in col.lower():
                    return np.array(df[col].values, dtype=float)
        
        raise ValueError(f"No se encontro ninguna de las columnas {candidates} en {list(df.columns)[:10]}")
    
    def _extract_column_strict(self, df: pd.DataFrame, candidates: List[str]) -> np.ndarray:
        """Extrae una columna de un DataFrame buscando SOLO coincidencias exactas.
        
        A diferencia de _extract_column, NO hace busqueda por palabra clave parcial.
        Util para evitar confusiones (ej: 'soc_stored_kwh' contiene 'charge').
        
        Args:
            df: DataFrame fuente
            candidates: Lista de posibles nombres de columna (solo exactos)
            
        Returns:
            Array numpy con los valores de la columna
            
        Raises:
            ValueError si ninguna columna candidata existe
        """
        # Solo busqueda exacta (case-insensitive)
        normalized_cols = {col.lower().strip(): col for col in df.columns}
        normalized_candidates = [c.lower().strip() for c in candidates]
        
        for norm_cand in normalized_candidates:
            if norm_cand in normalized_cols:
                actual_col = normalized_cols[norm_cand]
                return np.array(df[actual_col].values, dtype=float)
        
        raise ValueError(f"No se encontro ninguna de las columnas exactas {candidates} en {list(df.columns)}")
    
    def _calculate_metrics(self) -> None:
        """Calcula metricas del sistema v5.2 incluyendo analisis de picos."""
        if self.df_balance is None:
            return
        
        df = self.df_balance
        
        # Energias totales anuales
        total_pv_kwh = df['pv_generation_kw'].sum()
        total_demand_kwh = df['total_demand_kw'].sum()
        total_ev_kwh = df['ev_demand_kw'].sum()  # EV especifico
        total_mall_kwh = df['mall_demand_kw'].sum()  # Mall especifico
        total_grid_import = df['demand_from_grid_kw'].sum()
        total_bess_discharge = df['bess_discharge_kw'].sum()
        total_pv_to_demand = df['pv_to_demand_kw'].sum()
        
        # Autosuficiencia (% de demanda cubierta sin red)
        self_sufficiency = 1.0 - (total_grid_import / max(total_demand_kwh, 1e-6))
        
        # Cobertura PV (% de demanda cubierta por PV directo)
        pv_coverage = total_pv_to_demand / max(total_demand_kwh, 1e-6)
        
        # Cobertura BESS (% de demanda cubierta por BESS)
        bess_coverage = total_bess_discharge / max(total_demand_kwh, 1e-6)
        
        # Cobertura Red (% importado de red publica)
        grid_coverage = total_grid_import / max(total_demand_kwh, 1e-6)
        
        # Emisiones CO₂
        total_co2_kg = df['co2_from_grid_kg'].sum()
        co2_per_kwh = total_co2_kg / max(total_demand_kwh, 1e-6)
        co2_avoided_kg = total_pv_to_demand * self.config.co2_intensity_kg_per_kwh
        
        # PV utilizado vs generado
        pv_waste = df['pv_to_grid_kw'].sum()
        pv_utilization = 1.0 - (pv_waste / max(total_pv_kwh, 1e-6))
        
        # ANALISIS DE PICOS v5.4
        peak_limit_kw = self.config.demand_peak_limit_kw
        peak_exceeded_total = df['peak_exceeded_above_2000kw'].sum()  # kWh sobre limite
        peak_hours = (df['total_demand_kw'] > peak_limit_kw).sum()
        peak_hours_avg = df[df['total_demand_kw'] > peak_limit_kw]['total_demand_kw'].mean() if peak_hours > 0 else 0
        peak_max = df['total_demand_kw'].max()
        peak_reduction_by_bess = df[df['total_demand_kw'] > peak_limit_kw]['bess_discharge_kw'].sum()
        
        # AHORRO ECONOMICO POR REDUCCION DE PICOS (NEW v5.4)
        # Tarifas OSINERGMIN Iquitos
        tarifa_hp_soles = 0.45  # Hora Punta (18:00-22:59): S/. 0.45/kWh
        tarifa_hfp_soles = 0.28  # Hora Fuera de Punta (resto): S/. 0.28/kWh
        
        # Calcular ahorro por hora segun tarifa (usando columna 'hour' que ya existe)
        df['is_hora_punta'] = (df['hour'] >= 18) & (df['hour'] < 23)  # 18h-22:59h
        df['tarifa_por_kwh'] = df['is_hora_punta'].apply(lambda x: tarifa_hp_soles if x else tarifa_hfp_soles)
        
        # Ahorro = reduccion de picos × tarifa correspondiente
        df['ahorro_picos_soles'] = df['bess_discharge_kw'] * df['tarifa_por_kwh']  # En HP, esto es mayor
        ahorro_picos_total_soles = df['ahorro_picos_soles'].sum()  # Suma anual
        
        self.metrics = {
            'total_pv_kwh': total_pv_kwh,
            'total_demand_kwh': total_demand_kwh,
            'total_ev_kwh': total_ev_kwh,
            'total_mall_kwh': total_mall_kwh,
            'total_grid_import_kwh': total_grid_import,
            'total_bess_discharge_kwh': total_bess_discharge,
            'total_pv_to_demand_kwh': total_pv_to_demand,
            'total_pv_waste_kwh': pv_waste,
            'self_sufficiency_percent': self_sufficiency * 100,
            'pv_coverage_percent': pv_coverage * 100,
            'bess_coverage_percent': bess_coverage * 100,
            'grid_coverage_percent': grid_coverage * 100,
            'pv_utilization_percent': pv_utilization * 100,
            'total_co2_kg': total_co2_kg,
            'co2_avoided_kg': co2_avoided_kg,
            'co2_per_kwh': co2_per_kwh,
            # Metricas de picos (NEW v5.4)
            'peak_limit_kw': peak_limit_kw,
            'peak_max_kw': peak_max,
            'peak_hours_above_limit': peak_hours,
            'peak_hours_avg_kw': peak_hours_avg,
            'peak_exceeded_total_kwh': peak_exceeded_total,
            'peak_reduction_by_bess_kwh': peak_reduction_by_bess,
            'peak_reduction_savings_soles': ahorro_picos_total_soles,  # NEW: Ahorro economico
        }
    
    def print_summary(self) -> None:
        """Imprime un resumen de las metricas v5.2."""
        if not self.metrics:
            print("[!] No hay metricas calculadas. Ejecute calculate_balance() primero.")
            return
        
        m = self.metrics
        
        print("\n" + "="*70)
        print("  BALANCE ENERGETICO v5.2 - SISTEMA ELECTRICO IQUITOS")
        print("="*70)
        
        print("\n[GRAPH] GENERACION Y DEMANDA (Anuales):")
        print(f"  Generacion PV:          {m['total_pv_kwh']:>12,.0f} kWh/ano")
        print(f"  Demanda Total:          {m['total_demand_kwh']:>12,.0f} kWh/ano")
        print(f"    - Mall (RED PUBLICA): {m['total_demand_kwh'] - m.get('total_ev_kwh', 0):>12,.0f} kWh/ano")
        print(f"    - EV (38 sockets):    {m.get('total_ev_kwh', 0):>12,.0f} kWh/ano")
        print(f"  Importacion Red:        {m['total_grid_import_kwh']:>12,.0f} kWh/ano")
        print(f"  Descarga BESS:          {m['total_bess_discharge_kwh']:>12,.0f} kWh/ano")
        
        print("\n[CHART] COBERTURA DE DEMANDA:")
        print(f"  PV Directo:             {m['pv_coverage_percent']:>12.1f} %")
        print(f"  BESS:                   {m['bess_coverage_percent']:>12.1f} %")
        print(f"  Red Electrica:          {m['grid_coverage_percent']:>12.1f} %")
        print(f"  ---------------------------------")
        print(f"  AUTOSUFICIENCIA:        {m['self_sufficiency_percent']:>12.1f} %")
        
        print("\n☀️ EFICIENCIA PV (4,050 kWp instalado):")
        print(f"  PV Utilizado:           {m['total_pv_to_demand_kwh']:>12,.0f} kWh/ano")
        print(f"  PV Desperdiciado:       {m['total_pv_waste_kwh']:>12,.0f} kWh/ano")
        print(f"  Utilizacion:            {m['pv_utilization_percent']:>12.1f} %")
        
        print("\n🌍 EMISIONES CO₂ (Red @ 0.4521 kg CO₂/kWh - Iquitos termica):")
        print(f"  CO₂ por Red:            {m['total_co2_kg']:>12,.0f} kg CO₂/ano")
        print(f"  CO₂ Evitado (PV):       {m['total_pv_to_demand_kwh'] * 0.4521:>12,.0f} kg CO₂/ano")
        print(f"  Intensidad Sistema:     {m['co2_per_kwh']:>12.4f} kg CO₂/kWh")
        
        print("\n⚡ CONTROL DE DEMANDA PICO (Limite RED PUBLICA: 2000 kW):")
        print(f"  Pico maximo observado:  {m['peak_max_kw']:>12.1f} kW")
        print(f"  Horas sobre 2000 kW:    {m['peak_hours_above_limit']:>12.0f} horas/ano ({m['peak_hours_above_limit']/87.6:.1f}%)")
        print(f"  Promedio en esas horas: {m['peak_hours_avg_kw']:>12.1f} kW")
        print(f"  Exceso total anual:     {m['peak_exceeded_total_kwh']:>12,.0f} kWh/ano")
        print(f"  BESS reduce picos:      {m['peak_reduction_by_bess_kwh']:>12,.0f} kWh/ano")
        print(f"  Ahorro por reduccion:   S/. {m['peak_reduction_savings_soles']:>10,.0f}/ano")
        print(f"\n  NOTA: BESS (400 kW) reduce pero no elimina picos. Para limitarlos")
        print(f"        completamente a 2000 kW se requeriria ~900 kW de potencia.")
        print(f"        Ahorro calculado a tarifa: HP S/.0.45/kWh (18h-23h) + HFP S/.0.28/kWh (resto)")
        
        print("\n" + "="*70 + "\n")
    
    def plot_energy_balance(self, out_dir: Optional[Path] = None) -> None:
        """
        Genera graficas del balance energetico integral.
        
        Args:
            out_dir: Directorio para guardar las graficas (default: reports/)
        """
        if self.df_balance is None:
            raise ValueError("Primero debe calcular el balance energetico")
        
        if out_dir is None:
            out_dir = Path("reports/balance_energetico")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        df = self.df_balance
        
        print(f"\nGenerando graficas de balance energetico en {out_dir}...")
        
        # ===== Grafica 0: INTEGRAL - Todas las curvas superpuestas =====
        self._plot_integral_curves(df, out_dir)
        
        # ===== Grafica 1: Flujos Energeticos Horarios (5 dias representativos) =====
        self._plot_5day_balance(df, out_dir)
        
        # ===== Grafica 2: Balance Energetico Diario (365 dias) =====
        self._plot_daily_balance(df, out_dir)
        
        # ===== Grafica 3: Distribucion de Fuentes (anual) =====
        self._plot_sources_distribution(df, out_dir)
        
        # ===== Grafica 4: Cascada Energetica (Sankey simplificado) =====
        self._plot_energy_cascade(df, out_dir)
        
        # ===== Grafica 5: Estado de Carga BESS (365 dias) =====
        self._plot_bess_soc(df, out_dir)
        
        # ===== Grafica 6: Emisiones de CO2 (analisis diario) =====
        self._plot_co2_emissions(df, out_dir)
        
        # ===== Grafica 7: Utilizacion PV (analisis mensual) =====
        self._plot_pv_utilization(df, out_dir)
        
        print(f"  [OK] Graficas guardadas en {out_dir}")
    
    def _plot_integral_curves(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica INTEGRAL con datos REALES horarios - Primeros 7 dias + resumen."""
        
        # Usar datos reales horarios (primeros 7 días = 168 horas)
        df_7days = df.iloc[:7*24].copy()
        hours_real = np.arange(len(df_7days))
        
        # Crear figura grande con dos subgraficas
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 12))
        
        # ===== GRAFICA 1: GENERACION vs DEMANDA + BESS (DATOS REALES 7 DIAS) =====
        ax1.fill_between(hours_real, 0, df_7days['pv_generation_kw'], 
                        color='#FFD700', alpha=0.6, label='Generacion Solar PV', linewidth=1, edgecolor='orange')
        
        ax1.plot(hours_real, df_7days['mall_demand_kw'], 
                color='#1E90FF', linewidth=2, label='Demanda Mall', linestyle='-')
        
        ax1.plot(hours_real, df_7days['ev_demand_kw'], 
                color='#32CD32', linewidth=2, label='Demanda EV (38 tomas)', linestyle='-')
        
        ax1.plot(hours_real, df_7days['total_demand_kw'], 
                color='#DC143C', linewidth=2.5, label='Demanda Total', linestyle='--')
        
        # BESS Carga y Descarga (barras apiladas)
        ax1.bar(hours_real, df_7days['bess_charge_kw'], width=0.8, color='#228B22', alpha=0.7, 
               label=f'BESS Carga (Anual: {df["bess_charge_kw"].sum()/1000:.0f} MWh)')
        ax1.bar(hours_real, -df_7days['bess_discharge_kw'], width=0.8, color='#FF8C00', alpha=0.7,
               label=f'BESS Descarga (Anual: {df["bess_discharge_kw"].sum()/1000:.0f} MWh)')
        
        ax1.axhline(y=0, color='black', linewidth=1)
        ax1.set_ylabel('Potencia (kW)', fontsize=12, fontweight='bold')
        ax1.set_title('DATOS REALES: GeneracionPV vs Demandas + BESS Carga/Descarga - Primeros 7 dias', 
                     fontsize=14, fontweight='bold', color='darkred')
        ax1.set_xlim(0, 168)
        ax1.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax1.set_xticklabels(['Dia 1', 'Dia 2', 'Dia 3', 'Dia 4', 'Dia 5', 'Dia 6', 'Dia 7', 'Dia 8'], fontsize=10)
        ax1.legend(loc='upper left', fontsize=10, framealpha=0.95, ncol=2)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # ===== GRAFICA 2: SOC BESS + IMPORTACION RED (DATOS REALES 7 DIAS) =====
        ax2_twin = ax2.twinx()
        
        # SOC del BESS (eje izquierdo)
        ax2.plot(hours_real, df_7days['bess_soc_percent'], 
                color='darkgreen', linewidth=2.5, marker='o', markersize=2, label='SOC BESS')
        ax2.axhline(y=100, color='green', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.axhline(y=20, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.fill_between(hours_real, 20, 100, alpha=0.1, color='green')
        ax2.set_ylabel('SOC BESS (%)', fontsize=12, fontweight='bold', color='darkgreen')
        ax2.set_ylim(0, 110)
        ax2.tick_params(axis='y', labelcolor='darkgreen')
        
        # Importacion de red (eje derecho)
        ax2_twin.bar(hours_real, df_7days['demand_from_grid_kw'], width=0.8, 
                color='#FF6347', alpha=0.6, label='Importacion Red Publica')
        ax2_twin.set_ylabel('Importacion Red (kW)', fontsize=12, fontweight='bold', color='#FF6347')
        ax2_twin.tick_params(axis='y', labelcolor='#FF6347')
        ax2_twin.set_ylim(0, df_7days['demand_from_grid_kw'].max() * 1.2)
        
        ax2.set_xlabel('Hora (Primeros 7 dias)', fontsize=12, fontweight='bold')
        ax2.set_title('SOC BESS (Actual) + Importacion Red Publica - Datos Reales', 
                     fontsize=14, fontweight='bold', color='darkred')
        ax2.set_xlim(0, 168)
        ax2.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax2.set_xticklabels(['Dia 1', 'Dia 2', 'Dia 3', 'Dia 4', 'Dia 5', 'Dia 6', 'Dia 7', 'Dia 8'], fontsize=10)
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Combinar leyendas
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10, framealpha=0.95)
        
        # Texto explicativo
        bess_cap = self.config.bess_capacity_kwh
        bess_pow = self.config.bess_power_kw
        textstr = (
            f'Sistema Electrico Iquitos - Datos REALES Horarios (8,760 horas/ano)\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'PV Solar:        4,050 kWp (8.29 GWh/ano) | BESS: {bess_cap:.0f} kWh / {bess_pow:.0f} kW\n'
            f'Demanda Total:   12.78 GWh/ano (Mall: 12.37 GWh + EV: 408 MWh)\n'
            f'Cobertura:       PV 47.3% + BESS 1.5% + Red 51.2%\n'
            f'CO₂ Grid:        0.4521 kg CO₂/kWh (generacion termica aislada)'
        )
        fig.text(0.02, 0.00, textstr, fontsize=9, family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout(rect=[0, 0.06, 1, 1])
        plt.savefig(out_dir / "00_INTEGRAL_todas_curvas.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 00_INTEGRAL_todas_curvas.png ⭐ [DATOS REALES 7 DIAS]")
    
    def _plot_5day_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica de flujos energeticos en 5 dias representativos."""
        # Seleccionar 5 dias: dia nublado, soleado, transicion, etc.
        day_indices = [0, 89, 180, 270, 359]  # Distribuciones variadas
        
        fig, axes = plt.subplots(1, 1, figsize=(16, 8))
        
        colors = {
            'pv': '#FFD700',
            'demand': '#DC143C',
            'grid': '#FF6347',
            'bess_in': '#32CD32',
            'bess_out': '#FF8C00',
        }
        
        for day_idx in day_indices:
            start_h = day_idx * 24
            end_h = start_h + 24
            hours = df.loc[start_h:end_h-1, 'hour'] % 24
            
            axes.plot(hours, df.loc[start_h:end_h-1, 'pv_generation_kw'],
                     color=colors['pv'], linewidth=2.5, marker='o', label='PV', alpha=0.7)
        
        axes.fill_between(range(24), 0, 300, color=colors['demand'], alpha=0.1)
        axes.set_xlabel('Hora del Dia (UTC-5)', fontsize=11, fontweight='bold')
        axes.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
        axes.set_title('Generacion Solar - 5 Dias Representativos del Ano', 
                      fontsize=13, fontweight='bold')
        axes.grid(True, alpha=0.3)
        axes.legend(loc='upper left', fontsize=10)
        axes.set_xlim(-0.5, 23.5)
        
        plt.tight_layout()
        plt.savefig(out_dir / "01_balance_5dias.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 01_balance_5dias.png")
    
    def _plot_daily_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica de balance diario (365 dias)."""
        # Agrupar por dia
        df_day = df.copy()
        df_day['day'] = df_day['hour'] // 24
        daily = df_day.groupby('day').agg({
            'pv_generation_kw': 'sum',
            'total_demand_kw': 'sum',
            'demand_from_grid_kw': 'sum',
            'bess_discharge_kw': 'sum',
            'pv_to_demand_kw': 'sum',
        }).reset_index()
        
        fig, ax = plt.subplots(figsize=(16, 6))
        
        ax.fill_between(daily['day'], 0, daily['pv_generation_kw'], 
                       color='#FFD700', alpha=0.7, label='Generacion PV')
        ax.fill_between(daily['day'], 0, daily['total_demand_kw'], 
                       color='#DC143C', alpha=0.3, label='Demanda Total')
        ax.plot(daily['day'], daily['demand_from_grid_kw'], 
               color='#FF6347', linewidth=2, marker='o', markersize=3, label='Importacion Red')
        
        ax.set_xlabel('Dia del Ano', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energia (kWh/dia)', fontsize=11, fontweight='bold')
        ax.set_title('Balance Energetico Diario - 365 Dias', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(out_dir / "02_balance_diario.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 02_balance_diario.png")
    
    def _plot_sources_distribution(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica de distribucion de fuentes de energia."""
        # Energias totales
        pv_direct = df['pv_to_demand_kw'].sum()
        bess_supply = df['bess_to_demand_kw'].sum()
        grid_supply = df['demand_from_grid_kw'].sum()
        total = pv_direct + bess_supply + grid_supply
        
        # Porcentajes
        percentages = [
            pv_direct / total * 100,
            bess_supply / total * 100,
            grid_supply / total * 100,
        ]
        
        labels = [
            f'PV Directo\n{percentages[0]:.1f}%\n({pv_direct:,.0f} kWh)',
            f'BESS\n{percentages[1]:.1f}%\n({bess_supply:,.0f} kWh)',
            f'Red Electrica\n{percentages[2]:.1f}%\n({grid_supply:,.0f} kWh)',
        ]
        
        colors = ['#FFD700', '#32CD32', '#FF6347']
        explode = (0.05, 0.05, 0.1)
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        wedges, texts, autotexts = ax.pie(
            [pv_direct, bess_supply, grid_supply],
            labels=labels,
            colors=colors,
            autopct='',
            explode=explode,
            startangle=90,
            textprops={'fontsize': 11, 'fontweight': 'bold'},
        )
        
        ax.set_title('Distribucion de Fuentes de Energia (Anual)',
                    fontsize=13, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(out_dir / "03_distribucion_fuentes.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 03_distribucion_fuentes.png")
    
    def _plot_energy_cascade(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica de cascada energetica (flujos)."""
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Totales
        pv_gen = df['pv_generation_kw'].sum()
        ev_demand = df['ev_demand_kw'].sum()
        mall_demand = df['mall_demand_kw'].sum()
        pv_direct = df['pv_to_demand_kw'].sum()
        pv_to_bess = df['pv_to_bess_kw'].sum()
        pv_waste = df['pv_to_grid_kw'].sum()
        bess_discharge = df['bess_discharge_kw'].sum()
        grid_import = df['demand_from_grid_kw'].sum()
        
        # Datos para cascada (Waterfall chart simplificado)
        categories = [
            'PV\nGenerada',
            'PV a\nDemanda',
            'PV a\nBESS',
            'PV\nDesperdicio',
            'BESS\nDescarga',
            'Red\nImportada',
            'Demanda\nTotal'
        ]
        values = [pv_gen, -pv_direct, -pv_to_bess, -pv_waste, bess_discharge, grid_import, 
                 -(ev_demand + mall_demand)]
        colors_cascade = ['#FFD700', '#32CD32', '#32CD32', '#FF6347', '#FF8C00', '#FF6347', '#DC143C']
        
        x_pos = np.arange(len(categories))
        
        ax.bar(x_pos, [pv_gen, pv_direct, pv_to_bess, pv_waste, bess_discharge, grid_import, 
                      ev_demand + mall_demand],
              color=colors_cascade, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        # Etiquetas con valores
        for i, (cat, val) in enumerate(zip(categories, values)):
            height = abs(val) if val != -(ev_demand + mall_demand) else ev_demand + mall_demand
            ax.text(i, height + 50, f'{abs(val):,.0f}', ha='center', va='bottom',
                   fontsize=10, fontweight='bold')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(categories, fontsize=10, fontweight='bold')
        ax.set_ylabel('Energia (kWh/ano)', fontsize=11, fontweight='bold')
        ax.set_title('Cascada Energetica Anual - Flujos del Sistema',
                    fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(out_dir / "04_cascada_energetica.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 04_cascada_energetica.png")
    
    def _plot_bess_soc(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica del BESS SOC - Datos horarios reales sin interpolacion."""
        # Usar datos horarios reales del CSV (8,760 horas)
        hours = np.arange(len(df))
        soc = df['bess_soc_percent'].values
        
        # Figura: SOC horario (datos reales)
        fig, ax = plt.subplots(figsize=(16, 6))
        
        # Graficar SOC horario directo (sin agregaciones)
        ax.plot(hours, soc, linewidth=1, color='darkgreen', label='SOC Real (horario)')
        
        # Limites operativos
        dod = self.config.dod
        soc_min_limit = (1.0 - dod) * 100
        ax.axhline(y=100, color='green', linestyle='--', linewidth=1.5, 
                   alpha=0.7, label='SOC max (100%)')
        ax.axhline(y=soc_min_limit, color='red', linestyle='--', linewidth=1.5,
                   alpha=0.7, label=f'SOC min ({soc_min_limit:.0f}%)')
        
        # Llenar rango operacional
        ax.fill_between(hours, soc_min_limit, 100, alpha=0.1, color='green', 
                        label='Rango Operacional')
        
        # Labels y grid
        ax.set_xlabel('Hora del Año (0-8760)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Estado de Carga (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'BESS {self.config.bess_capacity_kwh:.0f} kWh / {self.config.bess_power_kw:.0f} kW - Estado de Carga Horario Real',
                     fontsize=13, fontweight='bold')
        ax.legend(loc='lower left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 110)
        ax.set_xlim(0, len(df))
        
        plt.tight_layout()
        plt.savefig(out_dir / "05_bess_soc.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 05_bess_soc.png")
    
    def _plot_co2_emissions(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica de emisiones de CO2."""
        # Agrupar por dia
        df_day = df.copy()
        df_day['day'] = df_day['hour'] // 24
        daily_co2 = df_day.groupby('day')['co2_from_grid_kg'].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(16, 6))
        
        # Grafica de CO2
        ax.bar(daily_co2['day'], daily_co2['co2_from_grid_kg'],
              color='#DC143C', alpha=0.8, edgecolor='darkred', linewidth=0.5)
        
        # Promedio y tendencia
        mean_co2 = daily_co2['co2_from_grid_kg'].mean()
        ax.axhline(y=mean_co2, color='black', linestyle='--', linewidth=2, label=f'Promedio: {mean_co2:.1f} kg CO2/dia')
        
        ax.set_xlabel('Dia del Ano', fontsize=11, fontweight='bold')
        ax.set_ylabel('Emisiones CO2 (kg/dia)', fontsize=11, fontweight='bold')
        ax.set_title(f'Emisiones de CO2 - Intensidad: {self.config.co2_intensity_kg_per_kwh:.4f} kg CO2/kWh',
                    fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(out_dir / "06_emisiones_co2.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 06_emisiones_co2.png")
    
    def _plot_pv_utilization(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica de utilizacion de PV (analisis mensual)."""
        # Agrupar por mes
        df_month = df.copy()
        df_month['month'] = (df_month['hour'] // 24) // 30 + 1
        monthly = df_month.groupby('month').agg({
            'pv_generation_kw': 'sum',
            'pv_to_demand_kw': 'sum',
            'pv_to_bess_kw': 'sum',
            'pv_to_grid_kw': 'sum',
        }).reset_index()
        
        # Asegurar 12 meses
        monthly = monthly[monthly['month'] <= 12]
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        month_labels = months[:len(monthly)]
        x_pos = np.arange(len(monthly))
        
        width = 0.2
        ax.bar(x_pos - 1.5*width, monthly['pv_to_demand_kw'], width, 
              label='PV -> Demanda', color='#FFD700', edgecolor='black', linewidth=0.5)
        ax.bar(x_pos - 0.5*width, monthly['pv_to_bess_kw'], width,
              label='PV -> BESS', color='#32CD32', edgecolor='black', linewidth=0.5)
        ax.bar(x_pos + 0.5*width, monthly['pv_to_grid_kw'], width,
              label='PV -> Red (desperdicio)', color='#FF6347', edgecolor='black', linewidth=0.5)
        
        # Linea de generacion total
        ax.plot(x_pos, monthly['pv_generation_kw'], 'ko-', linewidth=2.5, markersize=8, label='Total PV')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(month_labels, fontsize=10, fontweight='bold')
        ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energia (kWh/mes)', fontsize=11, fontweight='bold')
        ax.set_title('Utilizacion Mensual de PV - Distribucion de Flujos',
                    fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(out_dir / "07_utilizacion_pv.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] Grafica: 07_utilizacion_pv.png")
    
    def export_balance_csv(self, out_dir: Optional[Path] = None) -> None:
        """Exporta el balance energetico a CSV."""
        if self.df_balance is None:
            print("[!] No hay balance calculado. Ejecute calculate_balance() primero.")
            return
        
        if out_dir is None:
            out_dir = Path("reports/balance_energetico")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = out_dir / "balance_energetico_horario.csv"
        self.df_balance.to_csv(output_file, index=False)
        print(f"  [OK] CSV exportado: {output_file}")


def main(
    output_dir: Optional[Path] = None,
    year: int = 2024,
    generate_plots: bool = True
) -> BalanceEnergeticoSystem:
    """
    Ejecuta el analisis completo de balance energetico v5.4.
    
    Carga datos desde archivos OE2 reales:
    - Solar: data/oe2/Generacionsolar/pv_generation_citylearn2024_clean.csv (8,292,514 kWh/ano)
    - Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv (12,403,168 kWh/ano)
    - EV: data/oe2/chargers/chargers_ev_ano_2024_v3.csv (565,875 kWh/ano, 38 sockets)
    - BESS: data/oe2/bess/bess_ano_2024.csv (1,700 kWh / 400 kW)
    
    Args:
        output_dir: Ruta para guardar las graficas
        year: Ano de analisis
        generate_plots: Si generar las graficas
    
    Returns:
        Objeto BalanceEnergeticoSystem con analisis completo
    """
    print("\n" + "="*70)
    print("  ANALISIS DE BALANCE ENERGETICO v5.2 - IQUITOS")
    print("="*70)
    
    # Configuracion con rutas OE2 por defecto
    config = BalanceEnergeticoConfig(
        year=year,
    )
    
    # Crear sistema
    system = BalanceEnergeticoSystem(config)
    
    # Cargar datos OE2
    if not system.load_all_datasets():
        raise RuntimeError("Error al cargar los datasets OE2")
    
    # Calcular balance
    system.calculate_balance()
    
    # Imprimir resumen
    system.print_summary()
    
    # Generar graficas
    if generate_plots:
        plot_dir = output_dir or Path("reports/balance_energetico")
        system.plot_energy_balance(plot_dir)
        system.export_balance_csv(plot_dir)
    
    return system


if __name__ == "__main__":
    # Uso basico
    try:
        system = main()
        print("\n[OK] Analisis de balance energetico completado exitosamente")
    except Exception as e:
        print(f"\n[X] Error en analisis: {e}")
        raise
