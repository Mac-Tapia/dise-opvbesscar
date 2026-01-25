"""
Cargador robusto de datos OE2 para construcción de dataset.

Responsabilidades:
1. Cargar solar, chargers, BESS, mall desde archivos OE2
2. Validar integridad de datos (8,760 horas, valores positivos, etc.)
3. Normalizar a formato temporal estándar (DatetimeIndex)
4. Generar perfiles horarios enriquecidos
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SolarData:
    """Datos de generación solar OE2."""
    timeseries: pd.Series  # 8,760 valores horarios kW
    config: Dict[str, Any]
    results: Dict[str, Any]

    def validate(self) -> bool:
        """Validar integridad solar."""
        if len(self.timeseries) != 8760:
            logger.error(f"Solar timeseries length {len(self.timeseries)} != 8760")
            return False
        if self.timeseries.min() < 0:
            logger.error(f"Solar generation negativa: min={self.timeseries.min()}")
            return False
        if self.timeseries.max() > 10000:  # Sanidad: max ~4000 kW esperado
            logger.warning(f"Solar generation muy alta: max={self.timeseries.max()}")
        logger.info(f"✓ Solar validado: min={self.timeseries.min():.1f} "
                   f"max={self.timeseries.max():.1f} mean={self.timeseries.mean():.1f}")
        return True


@dataclass
class ChargerData:
    """Datos de cargadores EV OE2."""
    individual_chargers: list  # Lista de cargadores individuales (32 total)
    hourly_profiles: Dict[str, pd.Series]  # charger_id -> Series 8,760 valores
    summary: Dict[str, Any]

    def validate(self) -> bool:
        """Validar integridad cargadores."""
        # Permitir 32 o 128 (si 4 sockets cada uno)
        if len(self.individual_chargers) not in [32, 128]:
            logger.warning(f"Número de cargadores {len(self.individual_chargers)}, esperado 32 o 128")

        # Verificar que tenemos 128 perfiles (incluso si 32 chargers fisicos)
        if len(self.hourly_profiles) != 128:
            logger.warning(f"Perfiles disponibles {len(self.hourly_profiles)}, esperado 128")

        # Verificar que cada perfil tiene 8,760 horas
        for charger_id, profile in self.hourly_profiles.items():
            if len(profile) != 8760:
                logger.warning(f"Charger {charger_id} profile length {len(profile)}, ajustando a 8760")
                # Ajustar
                if len(profile) < 8760:
                    padded = np.pad(profile.values, (0, 8760-len(profile)), mode='edge')
                    self.hourly_profiles[charger_id] = pd.Series(padded,
                        index=pd.date_range('2024-01-01', periods=8760, freq='h'))
                else:
                    self.hourly_profiles[charger_id] = profile.iloc[:8760]

            if self.hourly_profiles[charger_id].min() < 0:
                logger.warning(f"Charger {charger_id} demanda negativa, ajustando a 0")
                self.hourly_profiles[charger_id] = self.hourly_profiles[charger_id].clip(lower=0)

        logger.info(f"✓ Chargers validados: {len(self.individual_chargers)} cargadores, "
                   f"{len(self.hourly_profiles)} perfiles, 128 sockets esperados")
        return True


@dataclass
class BESSData:
    """Datos de BESS OE2."""
    capacity_kwh: float
    power_kw: float
    efficiency: float
    min_soc: float
    max_soc: float
    config: Dict[str, Any]

    def validate(self) -> bool:
        """Validar BESS."""
        if self.capacity_kwh <= 0:
            logger.error(f"BESS capacity inválida: {self.capacity_kwh}")
            return False
        if self.power_kw <= 0:
            logger.error(f"BESS power inválida: {self.power_kw}")
            return False
        if not (0 < self.efficiency <= 1):
            logger.error(f"BESS efficiency inválida: {self.efficiency}")
            return False
        logger.info(f"✓ BESS validado: {self.capacity_kwh:.0f} kWh, "
                   f"{self.power_kw:.0f} kW, η={self.efficiency:.1%}")
        return True


@dataclass
class MallData:
    """Datos de demanda Mall OE2."""
    timeseries: pd.Series  # 8,760 valores horarios kW

    def validate(self) -> bool:
        """Validar Mall."""
        if len(self.timeseries) != 8760:
            logger.error(f"Mall timeseries length {len(self.timeseries)} != 8760")
            return False
        if self.timeseries.min() < 0:
            logger.error(f"Mall demand negativa: min={self.timeseries.min()}")
            return False
        logger.info(f"✓ Mall validado: min={self.timeseries.mean():.1f} "
                   f"max={self.timeseries.max():.1f} mean={self.timeseries.mean():.1f}")
        return True


class OE2DataLoader:
    """Cargador de datos OE2 con validación robusta."""

    def __init__(self, oe2_dir: Path | str):
        self.oe2_dir = Path(oe2_dir)
        self.solar_dir = self.oe2_dir / "solar"
        self.chargers_dir = self.oe2_dir / "chargers"
        self.bess_dir = self.oe2_dir / "bess"
        self.demandmall_dir = self.oe2_dir / "demandamallkwh"

        logger.info(f"OE2DataLoader initialized: {self.oe2_dir}")

    def load_all(self) -> Tuple[SolarData, ChargerData, BESSData, MallData]:
        """Cargar todo con validación."""
        logger.info("=== Cargando datos OE2 ===")

        solar = self.load_solar()
        chargers = self.load_chargers()
        bess = self.load_bess()
        mall = self.load_mall()

        # Validar todos
        solar_ok = solar.validate()
        chargers_ok = chargers.validate()
        bess_ok = bess.validate()
        mall_ok = mall.validate()

        # Todos deben pasar (si no, excepción)
        if not (solar_ok and chargers_ok and bess_ok):
            raise ValueError("OE2 solar/chargers/bess validation failed")

        # Mall es opcional
        if not mall_ok:
            logger.warning("Mall validation failed, pero continuando...")
        logger.info("✓ Todos los datos OE2 validados correctamente\n")
        return solar, chargers, bess, mall

    def load_solar(self) -> SolarData:
        """Cargar generación solar."""
        pv_gen_file = self.solar_dir / "pv_generation_timeseries.csv"
        config_file = self.solar_dir / "solar_config.json"
        results_file = self.solar_dir / "solar_results.json"

        logger.info(f"Cargando solar desde {pv_gen_file}...")

        # Cargar timeseries
        df = pd.read_csv(pv_gen_file)

        # Buscar columna de generación (puede ser 'pv_generation', 'PV Generation', etc)
        gen_col = None
        for col in df.columns:
            if 'generat' in col.lower() or 'output' in col.lower() or 'power' in col.lower():
                gen_col = col
                break

        if gen_col is None and len(df.columns) > 1:
            gen_col = df.columns[1]  # Asumir segunda columna
        elif gen_col is None:
            gen_col = df.columns[0]

        ts = pd.Series(df[gen_col].values, index=pd.date_range('2024-01-01', periods=8760, freq='h'))

        # Cargar config y resultados
        config = json.load(open(config_file)) if config_file.exists() else {}
        results = json.load(open(results_file)) if results_file.exists() else {}

        return SolarData(timeseries=ts, config=config, results=results)

    def load_chargers(self) -> ChargerData:
        """Cargar datos de cargadores."""
        individual_file = self.chargers_dir / "individual_chargers.json"
        logger.info(f"Cargando cargadores desde {individual_file}...")

        # Cargar cargadores individuales
        with open(individual_file) as f:
            individual_chargers = json.load(f)

        if isinstance(individual_chargers, dict):
            individual_chargers = list(individual_chargers.values())

        logger.info(f"  → {len(individual_chargers)} cargadores cargados")

        # Cargar perfiles horarios
        hourly_profiles = {}
        profile_files = list(self.chargers_dir.glob("charger_*_profile.csv"))

        if not profile_files:
            # Intentar alternativa: generar desde perfil único
            profile_file = self.chargers_dir / "perfil_horario_carga.csv"
            if profile_file.exists():
                logger.info(f"  → Cargando perfil base desde {profile_file}")
                base_profile = pd.read_csv(profile_file)

                # Expandir a 8,760 horas (24×365)
                col_data = base_profile.iloc[:, 1].values if len(base_profile.columns) > 1 else base_profile.iloc[:, 0].values
                base_hourly = np.array(col_data, dtype=float)

                if len(base_hourly) == 24:
                    hourly_expanded = np.tile(base_hourly, 365)
                else:
                    hourly_expanded = base_hourly[:8760]

                # Distribuir entre cargadores según potencia
                for i, charger in enumerate(individual_chargers):
                    charger_id = charger.get('charger_id', f'charger_{i}')
                    power = float(charger.get('power_kw', 2.5))  # Promedio ~2.5 kW

                    # Escalar según potencia del cargador
                    profile = np.array(hourly_expanded) * (power / 2.5)  # Normalizar a 2.5 kW base
                    hourly_profiles[charger_id] = pd.Series(profile,
                        index=pd.date_range('2024-01-01', periods=8760, freq='h'))
        else:
            # Cargar perfiles individuales
            for profile_file in profile_files:
                charger_id = profile_file.stem.replace("_profile", "")
                df = pd.read_csv(profile_file)
                ts = pd.Series(df.iloc[:, 1].values if len(df.columns) > 1 else df.iloc[:, 0].values,
                             index=pd.date_range('2024-01-01', periods=min(8760, len(df)), freq='h'))

                # Completar a 8,760 si es necesario
                if len(ts) < 8760:
                    ts = pd.Series(np.pad(ts.values, (0, 8760-len(ts)), mode='edge'),
                                 index=pd.date_range('2024-01-01', periods=8760, freq='h'))

                hourly_profiles[charger_id] = ts

        logger.info(f"  → {len(hourly_profiles)} perfiles horarios cargados")

        # Generar resumen
        summary = {
            'n_chargers': len(individual_chargers),
            'total_sockets': sum(c.get('sockets', 4) for c in individual_chargers),
            'total_power_kw': sum(c.get('power_kw', 2.5) for c in individual_chargers),
        }

        return ChargerData(
            individual_chargers=individual_chargers,
            hourly_profiles=hourly_profiles,
            summary=summary
        )

    def load_bess(self) -> BESSData:
        """Cargar configuración BESS."""
        config_file = self.bess_dir / "bess_config.json"
        logger.info(f"Cargando BESS desde {config_file}...")

        with open(config_file) as f:
            config = json.load(f)

        return BESSData(
            capacity_kwh=config.get('capacity_kwh', 2000),
            power_kw=config.get('power_kw', 1200),
            efficiency=config.get('efficiency', 0.95),
            min_soc=config.get('min_soc', 0.20),
            max_soc=config.get('max_soc', 1.00),
            config=config
        )

    def load_mall(self) -> MallData:
        """Cargar demanda Mall (prioriza archivo transformado horario)."""
        mall_files = list(self.demandmall_dir.glob("*.csv"))

        if not mall_files:
            logger.warning("No mall demand files found, usando demanda cero")
            ts = pd.Series(np.zeros(8760), index=pd.date_range('2024-01-01', periods=8760, freq='h'))
        else:
            # Priorizar archivo transformado (horario)
            hourly_file = self.demandmall_dir / "demanda_mall_horaria_anual.csv"
            mall_file = hourly_file if hourly_file.exists() else mall_files[0]

            logger.info(f"Cargando demanda Mall desde {mall_file.name}...")
            df = pd.read_csv(mall_file)

            # Buscar columna de demanda
            demand_col = None
            for col in df.columns:
                if 'demand' in col.lower() or 'power' in col.lower() or 'kwh' in col.lower():
                    demand_col = col
                    break

            if demand_col is None:
                demand_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

            # Convertir a float (manejar strings)
            values = pd.to_numeric(df[demand_col], errors='coerce').fillna(0).values[:8760]
            ts = pd.Series(values, index=pd.date_range('2024-01-01', periods=len(values), freq='h'))

            if len(ts) < 8760:
                ts = pd.Series(np.pad(ts.values, (0, 8760-len(ts)), mode='edge'),
                             index=pd.date_range('2024-01-01', periods=8760, freq='h'))

        return MallData(timeseries=ts)
