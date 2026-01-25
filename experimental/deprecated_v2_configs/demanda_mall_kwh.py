"""
Módulo de Análisis de Demanda Real del Mall con Control Operativo Insertado.

Este módulo integra la demanda real del mall (demandamallkwh.csv) con el 
comportamiento del control operativo (despacho de prioridades P1-P5) para 
visualizar cómo interactúan:

1. Demanda base del mall (no controlable, 87.5% Building_1)
2. Demanda de EV (controlable mediante dispatch)
3. Generación solar PV (controlable mediante dispatch)
4. BESS carga/descarga (controlable mediante dispatch)
5. CO₂ total (minimizar mediante RL + despacho)

Mantiene frozen dataclasses como patrón del proyecto.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass(frozen=True)
class MallDemandaHoraria:
    """Datos de demanda base del mall para una hora específica."""
    
    # Identificadores
    timestamp: datetime
    hora_dia: int  # 0-23
    
    # Demanda del mall (non-shiftable, real desde CSV)
    demanda_mall_kwh: float  # Building_1: 87.5%, Building_2: 12.5%
    
    # Factores externos
    generacion_pv_kwh: float  # PV disponible (controlado por dispatch P2)
    tarifa_usd_kwh: float  # Tarifa actual ($0.20 típico)
    
    # Metadata
    season: str = "dry"  # dry/wet estacional
    
    @classmethod
    def from_row(cls, 
                 timestamp: datetime,
                 demanda_mall_kwh: float,
                 generacion_pv_kwh: float,
                 tarifa_usd_kwh: float = 0.20) -> "MallDemandaHoraria":
        """Crear desde datos procesados."""
        return cls(
            timestamp=timestamp,
            hora_dia=timestamp.hour,
            demanda_mall_kwh=demanda_mall_kwh,
            generacion_pv_kwh=generacion_pv_kwh,
            tarifa_usd_kwh=tarifa_usd_kwh,
        )


@dataclass(frozen=True)
class DispatchControlInsertado:
    """Control de despacho insertado en la hora (P1-P5)."""
    
    # Prioridades de despacho (kWh en la hora)
    p1_pv_a_ev_directo_kwh: float  # Solar → EV directo
    p2_pv_a_bess_kwh: float        # Solar → BESS (carga)
    p3_bess_a_ev_kwh: float        # BESS → EV (principalmente en pico)
    p4_grid_a_bess_kwh: float      # Grid → BESS (reserva)
    p5_grid_a_ev_kwh: float        # Grid → EV (último recurso)
    
    # Acción de BESS
    bess_soc_antes: float  # Estado carga antes (%)
    bess_soc_despues: float  # Estado carga después (%)
    bess_ciclos_incrementales: float  # Ciclos de degradación
    
    # Acción de EVs
    ev_cargados_numero: int  # Cuántos EV cargados (0-128)
    ev_potencia_promedio_kw: float  # Potencia promedio en chargers
    
    @property
    def energia_total_despacho_kwh(self) -> float:
        """Total de energía despachada en la hora."""
        return (self.p1_pv_a_ev_directo_kwh + 
                self.p2_pv_a_bess_kwh + 
                self.p3_bess_a_ev_kwh + 
                self.p4_grid_a_bess_kwh + 
                self.p5_grid_a_ev_kwh)
    
    @property
    def pv_aprovechado_pct(self) -> float:
        """% de PV aprovechado sin pérdidas (P1+P2)."""
        if (self.p1_pv_a_ev_directo_kwh + self.p2_pv_a_bess_kwh) == 0:
            return 0.0
        return 100.0  # Ideal si está en P1/P2


@dataclass(frozen=True)
class BalanceHorario:
    """Balance de energía para una hora con control insertado."""
    
    # Entradas
    demanda_mall_kwh: float
    ev_demanda_kwh: float  # Demanda de EV (controlable, <256 kWh/h teórico)
    pv_disponible_kwh: float
    bess_disponible_descarga_kwh: float
    grid_disponible_kwh: float  # "Infinito" pero costoso
    
    # Flujos (del dispatch)
    pv_a_ev_directo: float  # P1
    pv_a_bess: float        # P2
    bess_a_ev: float        # P3
    grid_a_bess: float      # P4
    grid_a_ev: float        # P5
    grid_a_mall: float      # Grid import (no controllable)
    
    # Resultados
    import_grid_total_kwh: float  # Total import (mall + deficit)
    export_grid_kwh: float  # Export si hay exceso
    co2_total_kg: float  # kg CO2 de esta hora
    costo_usd: float    # $ de esta hora
    
    @property
    def balance_energy(self) -> float:
        """Verificación de balance (debe ser ~0)."""
        entradas = (self.pv_disponible_kwh + 
                   self.bess_disponible_descarga_kwh +
                   self.grid_disponible_kwh)
        salidas = (self.pv_a_ev_directo + 
                  self.pv_a_bess +
                  self.bess_a_ev +
                  self.grid_a_bess +
                  self.grid_a_ev +
                  self.grid_a_mall)
        return entradas - salidas
    
    @property
    def eficiencia_pv_pct(self) -> float:
        """% de PV aprovechado sin conversión (P1+P2)."""
        pv_sin_perdida = self.pv_a_ev_directo + self.pv_a_bess
        if self.pv_disponible_kwh == 0:
            return 0.0
        return (pv_sin_perdida / self.pv_disponible_kwh) * 100


@dataclass(frozen=True)
class HoraConControlInsertado:
    """Snapshot completo: demanda mall + control + resultado."""
    
    demanda: MallDemandaHoraria
    dispatch: DispatchControlInsertado
    balance: BalanceHorario
    
    # Metadata
    episodio: int = 0
    timestep: int = 0  # 0-8759


class AnalizadorDemandaMallKwh:
    """Analiza comportamiento de demanda mall con control insertado."""
    
    def __init__(self, cfg: Dict):
        """
        Inicializar analizador.
        
        Args:
            cfg: Config con parámetros OE3
        """
        self.cfg = cfg
        self.factor_co2_grid = cfg.get("oe3", {}).get("co2_emissions", {}).get(
            "grid_import_factor_kg_kwh", 0.4521
        )
        self.tarifa_kwh = cfg.get("oe3", {}).get("tariff_usd_kwh", 0.20)
        
        # Cache de datos cargados
        self._df_mall_cache: Optional[pd.DataFrame] = None
        self._df_pv_cache: Optional[pd.DataFrame] = None
    
    def cargar_demanda_mall_real(self, 
                                 interim_dir: Path) -> pd.DataFrame:
        """
        Cargar demanda real del mall desde CSV.
        
        Args:
            interim_dir: Ruta a data/interim/oe2/demandamallkwh/
        
        Returns:
            DataFrame con columnas [timestamp, demanda_mall_kwh]
        """
        if self._df_mall_cache is not None:
            return self._df_mall_cache
        
        mall_path = interim_dir / "demandamallkwh" / "demandamallkwh.csv"
        if not mall_path.exists():
            raise FileNotFoundError(f"No encontrado: {mall_path}")
        
        # Cargar con separador automático
        header_line = mall_path.read_text(encoding='utf-8', errors='ignore').split('\n')[0]
        sep = ";" if ";" in header_line else ","
        
        df = pd.read_csv(mall_path, sep=sep)
        
        # Normalizar nombres de columnas
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        
        # Encontrar columnas de fecha y demanda
        date_col = None
        for candidate in ["fecha", "timestamp", "datetime", "horafecha"]:
            if candidate in df.columns:
                date_col = candidate
                break
        if date_col is None:
            date_col = df.columns[0]
        
        demand_col = None
        for candidate in ["demanda_kwh", "demandamallkwh", "kwh", "power_kw"]:
            if candidate in df.columns:
                demand_col = candidate
                break
        if demand_col is None:
            demand_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        
        # Procesar: resample 15min → 1 hora si es necesario
        df['datetime'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        df['demanda_kw'] = pd.to_numeric(df[demand_col], errors='coerce')
        df = df[['datetime', 'demanda_kw']].dropna().set_index('datetime')
        
        # Detectar intervalo
        if len(df) > 1:
            interval_min = (df.index[1] - df.index[0]).total_seconds() / 60
        else:
            interval_min = 15
        
        # Si es energía (kWh), convertir a potencia (kW)
        if "kwh" in demand_col.lower():
            df['demanda_kw'] = df['demanda_kw'] * 60 / interval_min
        
        # Resample a hora
        df_hourly = df['demanda_kw'].resample('h').mean().to_frame('demanda_mall_kwh')
        
        # Llenar año completo si falta
        if len(df_hourly) < 8760:
            # Usar conversion para acceder a las horas de forma segura
            index_as_datetime = pd.to_datetime(df_hourly.index)
            df_hourly['hora'] = index_as_datetime.hour
            hourly_profile = df_hourly.groupby('hora')['demanda_mall_kwh'].mean()
            
            full_idx = pd.date_range(start=f'{pd.to_datetime(df_hourly.index[0]).year}-01-01',
                                     periods=8760, freq='h')
            df_full = pd.DataFrame(index=full_idx)
            df_full['hora'] = full_idx.hour
            df_full['demanda_mall_kwh'] = df_full['hora'].map(hourly_profile)
            df_hourly = df_full.drop(columns=['hora'])
        
        self._df_mall_cache = df_hourly
        return df_hourly
    
    def crear_hora_con_control(self,
                              timestamp: datetime,
                              demanda_mall_kwh: float,
                              pv_disponible_kwh: float,
                              dispatch_acciones: Dict) -> HoraConControlInsertado:
        """
        Crear snapshot de una hora con demanda + control.
        
        Args:
            timestamp: Hora
            demanda_mall_kwh: Demanda real del mall
            pv_disponible_kwh: PV disponible en esa hora
            dispatch_acciones: Dict con P1-P5 en kWh
        
        Returns:
            HoraConControlInsertado con todo integrado
        """
        # 1. Demanda
        demanda = MallDemandaHoraria.from_row(
            timestamp=timestamp,
            demanda_mall_kwh=demanda_mall_kwh,
            generacion_pv_kwh=pv_disponible_kwh,
            tarifa_usd_kwh=self.tarifa_kwh,
        )
        
        # 2. Dispatch (acciones de control)
        dispatch = DispatchControlInsertado(
            p1_pv_a_ev_directo_kwh=dispatch_acciones.get('p1', 0.0),
            p2_pv_a_bess_kwh=dispatch_acciones.get('p2', 0.0),
            p3_bess_a_ev_kwh=dispatch_acciones.get('p3', 0.0),
            p4_grid_a_bess_kwh=dispatch_acciones.get('p4', 0.0),
            p5_grid_a_ev_kwh=dispatch_acciones.get('p5', 0.0),
            bess_soc_antes=dispatch_acciones.get('bess_soc_antes', 50.0),
            bess_soc_despues=dispatch_acciones.get('bess_soc_despues', 50.0),
            bess_ciclos_incrementales=dispatch_acciones.get('ciclos', 0.0),
            ev_cargados_numero=dispatch_acciones.get('ev_count', 0),
            ev_potencia_promedio_kw=dispatch_acciones.get('ev_power', 0.0),
        )
        
        # 3. Balance de energía
        ev_demanda = dispatch.energia_total_despacho_kwh - demanda_mall_kwh
        grid_import = max(0, demanda_mall_kwh + ev_demanda - pv_disponible_kwh)
        
        balance = BalanceHorario(
            demanda_mall_kwh=demanda_mall_kwh,
            ev_demanda_kwh=ev_demanda,
            pv_disponible_kwh=pv_disponible_kwh,
            bess_disponible_descarga_kwh=dispatch.p3_bess_a_ev_kwh,
            grid_disponible_kwh=999999,  # "Infinito"
            pv_a_ev_directo=dispatch.p1_pv_a_ev_directo_kwh,
            pv_a_bess=dispatch.p2_pv_a_bess_kwh,
            bess_a_ev=dispatch.p3_bess_a_ev_kwh,
            grid_a_bess=dispatch.p4_grid_a_bess_kwh,
            grid_a_ev=dispatch.p5_grid_a_ev_kwh,
            grid_a_mall=grid_import,
            import_grid_total_kwh=grid_import,
            export_grid_kwh=max(0, pv_disponible_kwh - ev_demanda - demanda_mall_kwh),
            co2_total_kg=grid_import * self.factor_co2_grid,
            costo_usd=grid_import * self.tarifa_kwh,
        )
        
        return HoraConControlInsertado(
            demanda=demanda,
            dispatch=dispatch,
            balance=balance,
        )
    
    def generar_reporte_24h(self,
                           horas_con_control: List[HoraConControlInsertado],
                           out_file: Optional[Path] = None) -> str:
        """
        Generar reporte de comportamiento en 24 horas.
        
        Args:
            horas_con_control: Lista de HoraConControlInsertado (24 elementos)
            out_file: Archivo para guardar (opcional)
        
        Returns:
            String con reporte formateado
        """
        if len(horas_con_control) < 24:
            raise ValueError("Se requieren al menos 24 horas para reporte")
        
        horas = horas_con_control[:24]
        
        # Encabezado
        lineas = [
            "=" * 140,
            "DEMANDA DEL MALL CON CONTROL OPERATIVO INSERTADO - REPORTE 24 HORAS",
            "=" * 140,
            "",
        ]
        
        # Tabla de datos
        lineas.append(
            "Hora | Demanda | PV Disp | P1→EV  | P2→BESS| P3←BESS| "
            "P4←Grid| P5←Grid| Grid Imp | CO₂(kg)| BESS% |  EV# | Efic%"
        )
        lineas.append("-" * 140)
        
        total_co2 = 0
        total_grid = 0
        
        for h in horas:
            h_idx = h.demanda.hora_dia
            demand = h.demanda.demanda_mall_kwh
            pv = h.demanda.generacion_pv_kwh
            p1 = h.dispatch.p1_pv_a_ev_directo_kwh
            p2 = h.dispatch.p2_pv_a_bess_kwh
            p3 = h.dispatch.p3_bess_a_ev_kwh
            p4 = h.dispatch.p4_grid_a_bess_kwh
            p5 = h.dispatch.p5_grid_a_ev_kwh
            grid = h.balance.import_grid_total_kwh
            co2 = h.balance.co2_total_kg
            bess_soc = h.dispatch.bess_soc_despues
            ev_count = h.dispatch.ev_cargados_numero
            efic = h.balance.eficiencia_pv_pct
            
            total_co2 += co2
            total_grid += grid
            
            linea = (f" {h_idx:2d}  | {demand:7.0f} | {pv:7.0f} | "
                    f"{p1:6.0f} | {p2:6.0f} | {p3:6.0f} | "
                    f"{p4:6.0f} | {p5:6.0f} | {grid:8.0f} | "
                    f"{co2:7.0f} | {bess_soc:5.1f} | {ev_count:3d} | {efic:5.1f}")
            lineas.append(linea)
        
        # Totales
        lineas.append("-" * 140)
        lineas.append(f"TOTALES 24h    | Grid Import: {total_grid:.0f} kWh | "
                      f"CO₂: {total_co2:.0f} kg | Promedio CO₂/h: {total_co2/24:.0f} kg")
        lineas.append("=" * 140)
        lineas.append("")
        
        reporte = "\n".join(lineas)
        
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(reporte)
        
        return reporte
    
    def generar_reporte_diario(self,
                              horas_con_control: List[HoraConControlInsertado],
                              out_file: Optional[Path] = None) -> Dict:
        """
        Generar resumen diario (JSON).
        
        Args:
            horas_con_control: 24 horas
            out_file: Archivo JSON para guardar
        
        Returns:
            Dict con métricas diarias
        """
        demandas = [h.demanda.demanda_mall_kwh for h in horas_con_control]
        grid_imports = [h.balance.import_grid_total_kwh for h in horas_con_control]
        co2_values = [h.balance.co2_total_kg for h in horas_con_control]
        pv_disponibles = [h.demanda.generacion_pv_kwh for h in horas_con_control]
        
        resumen = {
            "fecha": horas_con_control[0].demanda.timestamp.isoformat(),
            "demanda_mall": {
                "min_kwh": float(np.min(demandas)),
                "max_kwh": float(np.max(demandas)),
                "promedio_kwh": float(np.mean(demandas)),
                "total_kwh": float(np.sum(demandas)),
            },
            "generacion_pv": {
                "min_kwh": float(np.min(pv_disponibles)),
                "max_kwh": float(np.max(pv_disponibles)),
                "promedio_kwh": float(np.mean(pv_disponibles)),
                "total_kwh": float(np.sum(pv_disponibles)),
            },
            "grid_import": {
                "min_kwh": float(np.min(grid_imports)),
                "max_kwh": float(np.max(grid_imports)),
                "promedio_kwh": float(np.mean(grid_imports)),
                "total_kwh": float(np.sum(grid_imports)),
            },
            "co2_emitido": {
                "min_kg": float(np.min(co2_values)),
                "max_kg": float(np.max(co2_values)),
                "promedio_kg": float(np.mean(co2_values)),
                "total_kg": float(np.sum(co2_values)),
                "factor_grid_kg_kwh": self.factor_co2_grid,
            },
            "control_insertado": {
                "dispatch_priorities": "P1→P5 active",
                "bess_utilizado": True,
                "pv_aprovechado_pct": float(
                    np.mean([h.balance.eficiencia_pv_pct for h in horas_con_control])
                ),
            }
        }
        
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(resumen, indent=2))
        
        return resumen


def create_demanda_mall_analyzer(cfg: Dict) -> AnalizadorDemandaMallKwh:
    """Factory function."""
    return AnalizadorDemandaMallKwh(cfg)
