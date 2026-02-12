"""Especificaciones de cargadores de EV para OE2 - VERSIÓN v5.2 (Modo 3 @ 7.4 kW)

Define estructuras de datos inmutables para cargadores y sus características.
Implementa simulación estocástica realista por toma con:
- 19 cargadores Modo 3 × 2 tomas = 38 tomas totales
- Potencia: 7.4 kW por toma (monofásico 32A @ 230V)
- Flota efectiva: 270 motos + 39 mototaxis/día
- Llegadas estocásticas (Poisson)
- SOC dinámico multifactorial
- Colas independientes por toma
- Horario operativo realista (9am-22pm, mall Iquitos)

TIEMPOS REALES DE CARGA (incluye pérdidas y taper):
- Moto (4.6 kWh @ 7.4 kW): ideal 41 min → real ~60 min (50-70)
- Mototaxi (7.4 kWh @ 7.4 kW): ideal 67 min → real ~90 min (75-105)

Factores aplicados a CANTIDADES de vehículos (no a energía):
- pe (penetración): 0.30 = 30% de vehículos son EVs
- fc (factor carga): 0.55 = 55% de EVs cargan cada día
- Vehículos que cargan = Base × pe × fc
- Energía por carga = Batería completa (4.6 kWh moto, 7.4 kWh mototaxi)

Escenario RECOMENDADO basado en:
- IEA Global EV Outlook 2024 (penetración 30% mercados emergentes 2030)
- BNEF Electric Vehicle Outlook 2025 (2/3 ruedas Asia emergente)
- ICCT Electric two/three-wheelers India (2022)
- NREL EV Charging Behavior Study (fc=0.55)

Autor: pvbesscar project
Versión: 5.2 (2026-02-11)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChargerSpec:
    """Especificación inmutable de un cargador.

    Attributes:
        charger_id: ID único (0-31, típicamente)
        max_power_kw: Potencia máxima en kW
        vehicle_type: "moto" o "mototaxi"
        sockets: Número de puertos de carga
    """
    charger_id: int
    max_power_kw: float
    vehicle_type: str
    sockets: int

    def __post_init__(self):
        if self.charger_id < 0:
            raise ValueError(f"charger_id must be >= 0, got {self.charger_id}")
        if self.max_power_kw <= 0:
            raise ValueError(f"max_power_kw must be > 0, got {self.max_power_kw}")
        if self.vehicle_type not in ("moto", "mototaxi"):
            raise ValueError(f"vehicle_type must be 'moto' or 'mototaxi', got {self.vehicle_type}")
        if self.sockets < 1:
            raise ValueError(f"sockets must be >= 1, got {self.sockets}")


@dataclass(frozen=True)
class ChargerSet:
    """Conjunto inmutable de especificaciones de cargadores.

    Attributes:
        chargers: Lista de ChargerSpec
    """
    chargers: tuple[ChargerSpec, ...]

    @property
    def count(self) -> int:
        """Número total de cargadores base."""
        return len(self.chargers)

    @property
    def total_sockets(self) -> int:
        """Número total de sockets (acciones controlables)."""
        return sum(c.sockets for c in self.chargers)

    @property
    def motos_count(self) -> int:
        """Número de cargadores para motos."""
        return sum(1 for c in self.chargers if c.vehicle_type == "moto")

    @property
    def mototaxis_count(self) -> int:
        """Número de cargadores para mototaxis."""
        return sum(1 for c in self.chargers if c.vehicle_type == "mototaxi")

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Convierte a lista de diccionarios para serializar."""
        return [
            {
                "charger_id": c.charger_id,
                "max_power_kw": c.max_power_kw,
                "vehicle_type": c.vehicle_type,
                "sockets": c.sockets,
            }
            for c in self.chargers
        ]

    def __iter__(self):
        """Permite iterar sobre los chargers."""
        return iter(self.chargers)

    def __len__(self):
        """Retorna número de cargadores base."""
        return len(self.chargers)


# ============================================================================
# DATACLASSES PARA SIMULACIÓN ESTOCÁSTICA v3.0
# ============================================================================

@dataclass(frozen=True)
class VehicleType:
    """Especificación de tipo de vehículo para simulación de carga.
    
    Attributes:
        name: Nombre del tipo (e.g., 'MOTO', 'MOTOTAXI')
        lambda_arrivals: Tasa de llegadas Poisson (vehículos/socket/hora)
        power_kw: Potencia de carga estándar (kW)
        capacity_kwh: Capacidad de batería (kWh)
        soc_arrival_mean: SOC medio en llegada (%)
        soc_arrival_std: Desviación estándar SOC en llegada (%)
        soc_target: SOC objetivo de carga (%)
    """
    name: str
    lambda_arrivals: float
    power_kw: float
    capacity_kwh: float
    soc_arrival_mean: float
    soc_arrival_std: float
    soc_target: float


# Especificaciones de tipos de vehículo - ESCENARIO RECOMENDADO (pe=0.30, fc=0.55)
# ============================================================================
# PASO 1: APLICAR pe×fc UNA SOLA VEZ a las cantidades base
# ─────────────────────────────────────────────────────────────────────────────
#   Base estacionados diario (mall Iquitos):
#     - Motos: 1,636 vehículos/día
#     - Mototaxis: 236 vehículos/día
#   
#   Factores (se aplican UNA VEZ):
#     - pe (penetración EV): 0.30 = 30% son eléctricos
#     - fc (factor carga diaria): 0.55 = 55% de EVs cargan cada día
#   
#   Vehículos que cargan = Base × pe × fc:
#     - Motos: 1,636 × 0.30 × 0.55 = 270 motos/día
#     - Mototaxis: 236 × 0.30 × 0.55 = 39 mototaxis/día
#
# PASO 2: DISTRIBUIR EN PUNTA vs FUERA DE PUNTA
# ─────────────────────────────────────────────────────────────────────────────
#   Punta (55% de cargas, 16h-21h = 5 horas):
#     - Motos punta: 270 × 0.55 = 149 motos en 5h → 30 motos/hora
#     - Mototaxis punta: 39 × 0.55 = 21 mototaxis en 5h → 4.2 mototaxis/hora
#   
#   Fuera de punta (45% de cargas, 9h-16h = 7 horas):
#     - Motos fuera punta: 270 × 0.45 = 122 motos en 7h → 17 motos/hora
#     - Mototaxis fuera punta: 39 × 0.45 = 18 mototaxis en 7h → 2.6/hora
#
# PASO 3: DIMENSIONAR CARGADORES (PLAYAS SEPARADAS motos vs mototaxis)
# ─────────────────────────────────────────────────────────────────────────────
#   Tiempos reales de carga (incluye pérdidas ~38% y taper):
#     - Moto 4.6 kWh: 60 min real → 1.0 cargas/hora/toma
#     - Mototaxi 7.4 kWh: 90 min real → 0.67 cargas/hora/toma
#   
#   PLAYA MOTOS (dimensionar por punta):
#     - Demanda punta: 30 motos/hora
#     - Capacidad por toma: 1.0 cargas/hora
#     - Tomas necesarias: 30 ÷ 1.0 = 30 tomas → 15 CARGADORES
#     - Verificación fuera punta: 17/h ÷ 1.0 = 17 tomas ✓ (cubierto con 30)
#   
#   PLAYA MOTOTAXIS (dimensionar por punta):
#     - Demanda punta: 4.2 mototaxis/hora
#     - Capacidad por toma: 0.67 cargas/hora (90 min cada uno)
#     - Tomas necesarias: 4.2 ÷ 0.67 = 6.3 → 7 tomas → 4 CARGADORES (8 tomas)
#     - Verificación fuera punta: 2.6/h ÷ 0.67 = 3.9 tomas ✓ (cubierto con 8)
#   
#   TOTAL: 15 + 4 = 19 CARGADORES × 2 tomas = 38 TOMAS (281.2 kW)
#
# ENERGÍA POR CARGA (batería completa, NO afectada por fc):
#   - Moto: 4.6 kWh/carga
#   - Mototaxi: 7.4 kWh/carga
#   - Energía diaria (9h-22h): 270×4.6 + 39×7.4 = 1,129 kWh/día (412,236 kWh/año)
#
# Referencias: IEA GEO 2024, BNEF EVO 2025, ICCT India 2022, NREL 2021
# ============================================================================

# EFICIENCIA DE CARGA REAL (considera pérdidas en cargador, cable, batería y taper)
# - Eficiencia cargador: ~92-95%
# - Pérdidas cable/conexión: ~2-3%
# - Pérdidas conversión batería: ~5-8%
# - Reducción por taper (CV phase): ~10-15% tiempo adicional
# - Eficiencia total: ~62% de potencia nominal
# Resultado: 7.4 kW nominal → 4.6 kW efectivos reales
CHARGING_EFFICIENCY = 0.62  # 62% = potencia efectiva / potencia nominal

MOTO_SPEC = VehicleType(
    name="MOTO",
    lambda_arrivals=0.69,    # 270 motos / (30 tomas × 13h operativas)
    power_kw=7.4,            # Modo 3 monofásico 32A @ 230V
    capacity_kwh=4.6,        # Batería completa moto eléctrica
    soc_arrival_mean=0.20,   # 20% SOC medio al llegar (batería baja)
    soc_arrival_std=0.10,    # ±10%
    soc_target=1.00          # 100% objetivo (carga completa ~60 min real)
)

MOTOTAXI_SPEC = VehicleType(
    name="MOTOTAXI",
    lambda_arrivals=0.375,   # 39 mototaxis / (8 tomas × 13h operativas)
    power_kw=7.4,            # Modo 3 monofásico 32A @ 230V
    capacity_kwh=7.4,        # Batería completa mototaxi
    soc_arrival_mean=0.20,   # 20% SOC medio al llegar (batería baja)
    soc_arrival_std=0.10,    # ±10%
    soc_target=1.00          # 100% objetivo (carga completa ~90 min real)
)


# ============================================================================
# TARIFAS OSINERGMIN - Electro Oriente S.A. (Iquitos, Loreto)
# Pliego Tarifario MT3 - Media Tensión Comercial/Industrial
# Vigente desde 2024-11-04
# Referencia: OSINERGMIN Resolución N° 047-2024-OS/CD
# ============================================================================
# Hora Punta (HP): 18:00 - 23:00 (5 horas)
# Hora Fuera de Punta (HFP): 00:00 - 17:59, 23:00 - 23:59 (19 horas)
# ============================================================================

# Tarifas de Energía (S/./kWh)
TARIFA_ENERGIA_HP_SOLES = 0.45     # Hora Punta: S/.0.45/kWh
TARIFA_ENERGIA_HFP_SOLES = 0.28    # Hora Fuera de Punta: S/.0.28/kWh

# Horas de periodo punta (18:00 - 22:59, inclusive)
HORA_INICIO_HP = 18
HORA_FIN_HP = 23  # Exclusivo (hasta las 22:59)


# ============================================================================
# REDUCCIÓN DIRECTA DE CO2 POR CAMBIO DE COMBUSTIBLE (Gasolina → Eléctrico)
# ============================================================================
# CONTEXTO: Motos y mototaxis tradicionales usan GASOLINA
# Al electrificarse, evitan emisiones directas del motor de combustión.
#
# METODOLOGÍA DE CÁLCULO:
# ─────────────────────────────────────────────────────────────────────────────
# 1. Factor emisión gasolina: 2.31 kg CO2/litro (IPCC)
#
# 2. Consumo típico moto gasolina 2T (110-150cc):
#    - 2.5-3.5 L/100 km (rendimiento 30-40 km/L)
#    - Usamos: 2.86 L/100 km (35 km/L)
#
# 3. Consumo moto eléctrica equivalente:
#    - Batería 4.6 kWh → 80-100 km autonomía → 5 kWh/100 km
#    - Rendimiento: 20 km/kWh
#
# 4. Por cada kWh cargado en EV:
#    - EV recorre: 20 km
#    - Moto gasolina para 20 km: 20/35 = 0.57 L gasolina
#    - CO2 evitado bruto: 0.57 L × 2.31 kg/L = 1.32 kg CO2
#
# 5. MENOS emisiones indirectas de electricidad (red diésel Iquitos):
#    - Factor red: 0.4521 kg CO2/kWh (sistema aislado térmico)
#    - CO2 indirecto: 1 kWh × 0.4521 = 0.45 kg CO2
#
# 6. REDUCCIÓN NETA = 1.32 - 0.45 = 0.87 kg CO2/kWh (moto)
#
# Para mototaxi (ligeramente menos eficiente):
#    - Autonomía 7.4 kWh → 60-80 km → 10 km/kWh
#    - Gasolina 3-wheelers: 4 L/100 km (25 km/L)
#    - Por kWh: 10 km → 0.40 L → 0.92 kg CO2 bruto
#    - Neto: 0.92 - 0.45 = 0.47 kg CO2/kWh
#
# FACTOR PROMEDIO PONDERADO (70% motos, 30% mototaxis):
#    0.70 × 0.87 + 0.30 × 0.47 = 0.75 kg CO2/kWh
# ============================================================================

FACTOR_CO2_GASOLINA_KG_L = 2.31         # kg CO2 / litro gasolina (IPCC)
FACTOR_CO2_RED_DIESEL_KG_KWH = 0.4521   # kg CO2 / kWh (red Iquitos)

# Factores de reducción NETA de CO2 por cambio de combustible
FACTOR_CO2_NETO_MOTO_KG_KWH = 0.87      # kg CO2 evitado / kWh cargado (moto)
FACTOR_CO2_NETO_MOTOTAXI_KG_KWH = 0.47  # kg CO2 evitado / kWh cargado (mototaxi)
FACTOR_CO2_NETO_PROMEDIO_KG_KWH = 0.75  # Promedio ponderado (70% moto, 30% taxi)


@dataclass
class Vehicle:
    """Estado de un vehículo durante carga.
    
    Attributes:
        vehicle_id: Identificador único
        arrival_hour: Hora de llegada (0-23)
        soc_arrival: SOC en llegada (0-1)
        soc_target: SOC objetivo (0-1)
        soc_current: SOC actual durante carga (0-1)
        power_kw: Potencia de carga (kW)
        capacity_kwh: Capacidad de batería (kWh)
        charging: True si está cargando
        hours_charged: Horas acumuladas de carga
    """
    vehicle_id: int
    arrival_hour: int
    soc_arrival: float
    soc_target: float
    soc_current: float
    power_kw: float
    capacity_kwh: float
    charging: bool = True
    hours_charged: float = 0.0
    
    def charge_for_hour(self) -> float:
        """Carga el vehículo por una hora. Retorna energía cargada (kWh).
        
        Considera CHARGING_EFFICIENCY (62%) para tiempos reales:
        - Moto 4.6 kWh: 7.4 kW × 0.62 = 4.6 kW efectivos → ~60 min
        - Mototaxi 7.4 kWh: 7.4 kW × 0.62 = 4.6 kW efectivos → ~96 min
        """
        if not self.charging:
            return 0.0
        
        # Energía que se puede cargar en esta hora (con eficiencia real)
        # power_kw = 7.4 kW nominal, efectivo = 7.4 × 0.62 = 4.6 kW
        effective_power_kw = self.power_kw * CHARGING_EFFICIENCY
        energy_capacity = effective_power_kw * 1.0  # 1 hora
        energy_to_target = (self.soc_target - self.soc_current) * self.capacity_kwh
        
        # Toma el mínimo entre lo disponible y lo necesario
        energy_charged = min(energy_capacity, energy_to_target)
        
        # Actualiza SOC
        self.soc_current += energy_charged / self.capacity_kwh
        self.hours_charged += 1.0
        
        # Si alcanzó objetivo, termina carga
        if self.soc_current >= self.soc_target:
            self.charging = False
            self.soc_current = min(self.soc_current, 1.0)
        
        return energy_charged
    
    def should_depart(self) -> bool:
        """Determina si el vehículo debe partir (SOC suficiente)."""
        return self.soc_current >= self.soc_target or self.hours_charged > 8


class SocketSimulator:
    """Simulador de una toma (socket) individual con cola estocástica.
    
    Mantiene:
    - Una cola FIFO de vehículos esperando
    - Un vehículo siendo cargado (máximo 1)
    - Registro de energía cargada por hora
    """
    
    def __init__(self, socket_id: int, vehicle_type: VehicleType, rng: np.random.RandomState):
        """Inicializa el simulador.
        
        Args:
            socket_id: Identificador de la toma
            vehicle_type: Especificación de tipo de vehículo
            rng: Generador de números aleatorios (para reproducibilidad)
        """
        self.socket_id = socket_id
        self.vehicle_type = vehicle_type
        self.rng = rng
        self.queue: deque[Vehicle] = deque()
        self.current_vehicle: Vehicle | None = None
        self.hourly_energy: list[float] = []
        self.vehicle_count = 0
        
    def hourly_step(self, hour: int, operational_factor: float) -> float:
        """Simula una hora de operación.
        
        Args:
            hour: Hora actual (0-23)
            operational_factor: Factor de operación (0-1, tipicamente 0 en 22-9h)
        
        Returns:
            Energía cargada esta hora (kWh)
        """
        # Generar nuevas llegadas de Poisson (solo si hay operación)
        if operational_factor > 0:
            num_arrivals = self.rng.poisson(self.vehicle_type.lambda_arrivals * operational_factor)
            for _ in range(num_arrivals):
                soc_arr = np.clip(
                    self.rng.normal(self.vehicle_type.soc_arrival_mean, 
                                   self.vehicle_type.soc_arrival_std),
                    0.0, 1.0
                )
                vehicle = Vehicle(
                    vehicle_id=self.vehicle_count,
                    arrival_hour=hour,
                    soc_arrival=soc_arr,
                    soc_target=self.vehicle_type.soc_target,
                    soc_current=soc_arr,
                    power_kw=self.vehicle_type.power_kw,
                    capacity_kwh=self.vehicle_type.capacity_kwh
                )
                self.queue.append(vehicle)
                self.vehicle_count += 1
        
        # Procesar vehículo actual
        energy_hour = 0.0
        if self.current_vehicle is not None:
            energy_hour = self.current_vehicle.charge_for_hour()
            if self.current_vehicle.should_depart():
                self.current_vehicle = None
        
        # Traer siguiente de la cola si no hay uno cargando
        if self.current_vehicle is None and len(self.queue) > 0:
            self.current_vehicle = self.queue.popleft()
        
        self.hourly_energy.append(energy_hour)
        return energy_hour
    
    def get_annual_energy(self) -> float:
        """Retorna energía total cargada en el año (kWh)."""
        return sum(self.hourly_energy)
    
    def get_occupancy(self) -> float:
        """Retorna factor de ocupación (fracción de horas con carga)."""
        total_hours = len(self.hourly_energy)
        occupied = sum(1 for e in self.hourly_energy if e > 0)
        return occupied / total_hours if total_hours > 0 else 0.0


def create_iquitos_chargers() -> ChargerSet:
    """Crea el conjunto de cargadores estándar para Iquitos.

    PLAYAS DE ESTACIONAMIENTO SEPARADAS (motos vs mototaxis):
    
    PASO 1: Base × pe × fc (aplicado UNA VEZ)
    - Motos: 1,636 × 0.30 × 0.55 = 270 motos/día que cargan
    - Mototaxis: 236 × 0.30 × 0.55 = 39 mototaxis/día que cargan
    
    PASO 2: Distribución punta (55%) vs fuera punta (45%)
    - Motos punta (5h): 149 motos → 30/hora
    - Motos fuera punta (7h): 122 motos → 17/hora
    - Mototaxis punta (5h): 21 mototaxis → 4.2/hora
    - Mototaxis fuera punta (7h): 18 mototaxis → 2.6/hora
    
    PASO 3: Dimensionar por punta (tiempos reales)
    - PLAYA MOTOS: 30/h ÷ 1.0 cargas/h = 30 tomas → 15 CARGADORES
    - PLAYA MOTOTAXIS: 4.2/h ÷ 0.67 cargas/h = 7 tomas → 4 CARGADORES
    
    RESULTADO:
    - 15 + 4 = 19 cargadores × 2 tomas = 38 tomas
    - Potencia instalada: 38 × 7.4 = 281.2 kW

    Returns:
        ChargerSet inmutable con especificaciones
    """
    specs = []

    # PLAYA MOTOS: 15 cargadores × 2 tomas = 30 tomas
    # Dimensionado por punta: 30 motos/hora ÷ 1.0 cargas/hora/toma = 30 tomas
    for i in range(15):
        specs.append(ChargerSpec(
            charger_id=i,
            max_power_kw=7.4,  # Modo 3 monofásico 32A
            vehicle_type="moto",
            sockets=2
        ))

    # Mototaxis: 4 cargadores × 2 tomas = 8 tomas (39 mototaxis/día, 90 min/carga)
    # PLAYA MOTOTAXIS: 4 cargadores × 2 tomas = 8 tomas
    # Dimensionado por punta: 4.2 mototaxis/hora ÷ 0.67 cargas/hora/toma ≈ 7 tomas → 4 cargadores
    for i in range(15, 19):
        specs.append(ChargerSpec(
            charger_id=i,
            max_power_kw=7.4,  # Modo 3 monofásico 32A
            vehicle_type="mototaxi",
            sockets=2
        ))

    return ChargerSet(chargers=tuple(specs))


def validate_charger_set(charger_set: ChargerSet) -> dict[str, Any]:
    """Valida un conjunto de cargadores para especificación v5.2 (Modo 3 @ 7.4 kW).

    PLAYAS SEPARADAS según dimensionamiento por hora punta:
    - PLAYA MOTOS: 15 cargadores × 2 = 30 tomas (30 motos/hora punta)
    - PLAYA MOTOTAXIS: 4 cargadores × 2 = 8 tomas (4.2 mototaxis/hora punta)
    - Total: 19 cargadores, 38 tomas, 281.2 kW
    - Tiempos reales: 60 min (moto), 90 min (mototaxi)

    Args:
        charger_set: Conjunto a validar

    Returns:
        Diccionario con resultados de validación
    """
    errors: list[str] = []
    warnings: list[str] = []
    is_valid = True

    # Verificar cantidad exacta de cargadores
    if charger_set.count != 19:
        errors.append(f"Expected exactly 19 chargers, got {charger_set.count}")
        is_valid = False

    # Verificar cantidad exacta de tomas
    if charger_set.total_sockets != 38:
        errors.append(
            f"Expected exactly 38 sockets, got {charger_set.total_sockets}"
        )
        is_valid = False

    # Verificar distribución exacta (con tiempos reales)
    if charger_set.motos_count != 15:
        errors.append(f"Expected 15 chargers for motos, got {charger_set.motos_count}")
        is_valid = False

    if charger_set.mototaxis_count != 4:
        errors.append(f"Expected 4 chargers for mototaxis, got {charger_set.mototaxis_count}")
        is_valid = False

    # Verificar IDs únicos y secuenciales (0-18)
    ids = [c.charger_id for c in charger_set.chargers]
    if len(ids) != len(set(ids)):
        errors.append("Charger IDs are not unique")
        is_valid = False

    if ids != list(range(19)):
        errors.append(f"Charger IDs should be 0-18, got {ids}")
        is_valid = False

    # Verificar que cada cargador tiene exactamente 2 tomas (Modo 3)
    for charger in charger_set.chargers:
        if charger.sockets != 2:
            errors.append(f"Charger {charger.charger_id} has {charger.sockets} sockets, expected 2")
            is_valid = False

    results: dict[str, Any] = {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }

    return results


# Singleton global (creado una vez)
_IQUITOS_CHARGERS: ChargerSet | None = None


def get_iquitos_chargers() -> ChargerSet:
    """Obtiene el conjunto de cargadores para Iquitos (con caching).

    Returns:
        ChargerSet inmutable y singleton
    """
    global _IQUITOS_CHARGERS

    if _IQUITOS_CHARGERS is None:
        _IQUITOS_CHARGERS = create_iquitos_chargers()

        # Validar
        validation = validate_charger_set(_IQUITOS_CHARGERS)
        if not validation["is_valid"]:
            logger.error(f"Charger set validation failed: {validation['errors']}")
        else:
            logger.info(
                f"✓ Chargers loaded: {_IQUITOS_CHARGERS.count} units, "
                f"{_IQUITOS_CHARGERS.total_sockets} sockets "
                f"({_IQUITOS_CHARGERS.motos_count} motos + "
                f"{_IQUITOS_CHARGERS.mototaxis_count} mototaxis)"
            )

    return _IQUITOS_CHARGERS


# ============================================================================
# FUNCIONES PARA GENERAR DATASET DETALLADO POR TOMA (SOCKET LEVEL)
# ============================================================================

@dataclass(frozen=True)
class SocketSpec:
    """Especificación de una toma individual (socket).
    
    Attributes:
        socket_id: ID único 0-37 (30 motos + 8 mototaxis)
        charger_id: ID del cargador que contiene (0-18)
        socket_number: Número de toma dentro del cargador (0-1)
        vehicle_type: "moto" o "mototaxi"
        power_kw: Potencia nominal en kW (7.4 kW Modo 3)
    """
    socket_id: int
    charger_id: int
    socket_number: int
    vehicle_type: str
    power_kw: float


def create_socket_specs() -> list[SocketSpec]:
    """Crea especificaciones para cada una de las 38 tomas.
    
    Returns:
        Lista de 38 SocketSpec (30 motos + 8 mototaxis)
    """
    sockets = []
    socket_id = 0
    
    # 30 tomas de motos (15 chargers × 2 tomas)
    for charger_id in range(15):
        for socket_num in range(2):
            sockets.append(SocketSpec(
                socket_id=socket_id,
                charger_id=charger_id,
                socket_number=socket_num,
                vehicle_type="moto",
                power_kw=7.4  # Modo 3 monofásico 32A
            ))
            socket_id += 1
    
    # 8 tomas de mototaxis (4 chargers × 2 tomas)
    for charger_id in range(15, 19):
        for socket_num in range(2):
            sockets.append(SocketSpec(
                socket_id=socket_id,
                charger_id=charger_id,
                socket_number=socket_num,
                vehicle_type="mototaxi",
                power_kw=7.4  # Modo 3 monofásico 32A
            ))
            socket_id += 1
    
    return sockets


# ============================================================================
# FUNCIONES DE HORARIO Y SIMULACIÓN ESTOCÁSTICA v3.0
# ============================================================================

def get_operational_factor(hour_of_day: int) -> float:
    """Retorna el factor de operacion del mall para una hora determinada.
    
    Horario del mall (Iquitos):
    - 0-9h: Cerrado (0%)
    - 9-10h: Apertura y acondicionamiento (30%)
    - 10-18h: Operacion normal lineal (30% -> 100%)
    - 18-21h: Pico de operacion (100%)
    - 21-23h: Cierre gradual (100% -> 50% -> 0%)
    - 23-0h: Cerrado (0%)
    
    Args:
        hour_of_day: Hora del dia (0-23)
        
    Returns:
        Factor de operacion (0.0-1.0)
    """
    if hour_of_day < 9 or hour_of_day >= 23:
        # Cerrado fuera de 9-23h
        return 0.0
    elif hour_of_day == 9:
        # 9-10h: apertura 30%
        return 0.30
    elif 10 <= hour_of_day < 18:
        # 10-18h: rampa lineal 30% -> 100%
        # Interpolacion: 30% + (hour-10) * (100-30) / (18-10)
        progress = (hour_of_day - 10) / 8.0  # 0 a 1 en 8 horas
        return 0.30 + progress * 0.70
    elif 18 <= hour_of_day < 21:
        # 18-21h: operacion plena 100%
        return 1.0
    elif 21 <= hour_of_day < 23:
        # 21-23h: cierre gradual 100% -> 0%
        # hora 21: 100%, hora 22: 50%, hora 23: 0%
        progress = (hour_of_day - 21) / 2.0
        return 1.0 - progress
    else:
        return 0.0


def generate_socket_level_dataset_v3(
    output_dir: str | Path = "data/oe2/chargers",
    random_seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera dataset estocástico realista v3.0 con simulación por socket.
    
    Crea simuladores independientes por toma con:
    - Llegadas estocásticas (Poisson) según tipos de vehículo
    - SOC dinámico durante carga
    - Colas FIFO independientes
    - Factor operativo horario (9-22h para mall)
    - Reproducibilidad con random_seed
    
    Retorna:
    - DataFrame anual (8,760 × 643 columnas)
    - DataFrame diario de ejemplo (24 × 643 columnas)
    
    Args:
        output_dir: Directorio para guardar CSVs
        random_seed: Semilla para reproducibilidad
        
    Returns:
        Tupla (df_annual_8760h, df_daily_24h)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(random_seed)
    
    # Crear timestamps
    start_date = datetime(2024, 1, 1)
    timestamps = [start_date + timedelta(hours=i) for i in range(8760)]
    
    # Crear 38 simuladores (30 motos + 8 mototaxis)
    simulators: dict[int, SocketSimulator] = {}
    socket_to_vehicle = {}  # socket_id → vehicle_type
    
    for socket_id in range(30):
        # Tomas 0-29: motos
        socket_to_vehicle[socket_id] = MOTO_SPEC
        simulators[socket_id] = SocketSimulator(socket_id, MOTO_SPEC, rng)
    
    for socket_id in range(30, 38):
        # Tomas 30-37: mototaxis
        socket_to_vehicle[socket_id] = MOTOTAXI_SPEC
        simulators[socket_id] = SocketSimulator(socket_id, MOTOTAXI_SPEC, rng)
    
    # Inicializar estructura de datos (datetime será el índice, sin hour ni day_of_year)
    data_annual: dict[str, list] = {}
    
    # Agregar columnas para cada toma (38 total)
    # POTENCIA CARGADOR vs CAPACIDAD BATERÍA:
    # - charger_power_kw: Potencia nominal del cargador (7.4 kW, constante)
    # - battery_kwh: Capacidad de batería del vehículo (4.6 kWh moto, 7.4 kWh mototaxi)
    # - charging_power_kw: Potencia instantánea de carga (0 si no hay vehículo)
    for socket_id in range(38):
        # Tipo de vehículo para esta toma
        vtype = socket_to_vehicle[socket_id]
        
        # Columnas constantes (se llenan una vez)
        data_annual[f'socket_{socket_id:03d}_charger_power_kw'] = [7.4] * 8760  # Potencia nominal cargador
        data_annual[f'socket_{socket_id:03d}_battery_kwh'] = [vtype.capacity_kwh] * 8760  # Capacidad batería
        data_annual[f'socket_{socket_id:03d}_vehicle_type'] = [vtype.name] * 8760  # Tipo vehículo
        
        # Columnas dinámicas (se llenan en simulación)
        data_annual[f'socket_{socket_id:03d}_soc_current'] = []
        data_annual[f'socket_{socket_id:03d}_soc_arrival'] = []
        data_annual[f'socket_{socket_id:03d}_soc_target'] = []
        data_annual[f'socket_{socket_id:03d}_active'] = []
        data_annual[f'socket_{socket_id:03d}_charging_power_kw'] = []  # Potencia instantánea de carga
        data_annual[f'socket_{socket_id:03d}_vehicle_count'] = []
    
    # Simular 8,760 horas
    logger.info("Iniciando simulación estocástica v3.0 (8,760 horas)...")
    for hour_idx, timestamp in enumerate(timestamps):
        if (hour_idx + 1) % 730 == 0:  # Log cada mes
            logger.info(f"  Simulated {hour_idx + 1}/8760 hours...")
        
        hour_of_day = timestamp.hour
        operational_factor = get_operational_factor(hour_of_day)
        
        # Simular cada toma (38 total)
        for socket_id in range(38):
            simulator = simulators[socket_id]
            simulator.hourly_step(hour_of_day, operational_factor)
            
            # Registrar estado actual
            if simulator.current_vehicle is not None:
                vehicle = simulator.current_vehicle
                data_annual[f'socket_{socket_id:03d}_soc_arrival'].append(vehicle.soc_arrival)
                data_annual[f'socket_{socket_id:03d}_soc_target'].append(vehicle.soc_target)
                data_annual[f'socket_{socket_id:03d}_soc_current'].append(vehicle.soc_current)
                data_annual[f'socket_{socket_id:03d}_active'].append(1)
                # Potencia instantánea de carga (efectiva, con eficiencia)
                effective_power = vehicle.power_kw * CHARGING_EFFICIENCY if vehicle.charging else 0.0
                data_annual[f'socket_{socket_id:03d}_charging_power_kw'].append(effective_power)
                data_annual[f'socket_{socket_id:03d}_vehicle_count'].append(simulator.vehicle_count)
            else:
                data_annual[f'socket_{socket_id:03d}_soc_arrival'].append(0.0)
                data_annual[f'socket_{socket_id:03d}_soc_target'].append(0.0)
                data_annual[f'socket_{socket_id:03d}_soc_current'].append(0.0)
                data_annual[f'socket_{socket_id:03d}_active'].append(0)
                data_annual[f'socket_{socket_id:03d}_charging_power_kw'].append(0.0)
                data_annual[f'socket_{socket_id:03d}_vehicle_count'].append(simulator.vehicle_count)
    
    # Crear DataFrame anual con datetime como índice
    df_annual = pd.DataFrame(data_annual, index=pd.DatetimeIndex(timestamps, name='datetime'))
    
    # ================================================================
    # AGREGAR COLUMNAS DE COSTOS OSINERGMIN Y REDUCCIÓN CO2
    # ================================================================
    # Extraer hora del índice para determinar tarifa aplicable
    hour_of_day = pd.to_datetime(df_annual.index).hour
    
    # Determinar si es hora punta (18:00 - 22:59)
    df_annual["is_hora_punta"] = np.where(
        (hour_of_day >= HORA_INICIO_HP) & (hour_of_day < HORA_FIN_HP), 1, 0
    )
    
    # Tarifa aplicada según hora (S/./kWh)
    df_annual["tarifa_aplicada_soles"] = np.where(
        df_annual["is_hora_punta"] == 1,
        TARIFA_ENERGIA_HP_SOLES,
        TARIFA_ENERGIA_HFP_SOLES
    )
    
    # Calcular energía total cargada por hora (suma de todos los sockets)
    charging_cols = [col for col in df_annual.columns if '_charging_power_kw' in col]
    df_annual["ev_energia_total_kwh"] = df_annual[charging_cols].sum(axis=1)
    
    # Costo de carga EV por hora (S/.) = energía × tarifa aplicable
    df_annual["costo_carga_ev_soles"] = df_annual["ev_energia_total_kwh"] * df_annual["tarifa_aplicada_soles"]
    
    # ================================================================
    # REDUCCIÓN DIRECTA DE CO2 - CAMBIO DE COMBUSTIBLE (Gasolina → EV)
    # ================================================================
    # La reducción DIRECTA es diferente a la indirecta (desplazamiento de diésel).
    # Aquí calculamos el CO2 que se evita porque los vehículos NO usan gasolina.
    #
    # Factores:
    #   MOTO: 0.87 kg CO2/kWh (neto, descontando emisiones de la red)
    #   MOTOTAXI: 0.47 kg CO2/kWh (neto)
    # ================================================================
    
    # Energía por tipo de vehículo (motos: sockets 0-29, mototaxis: 30-37)
    moto_cols = [col for col in df_annual.columns if '_charging_power_kw' in col and int(col.split('_')[1]) < 30]
    taxi_cols = [col for col in df_annual.columns if '_charging_power_kw' in col and int(col.split('_')[1]) >= 30]
    
    df_annual["ev_energia_motos_kwh"] = df_annual[moto_cols].sum(axis=1)
    df_annual["ev_energia_mototaxis_kwh"] = df_annual[taxi_cols].sum(axis=1)
    
    # Reducción directa CO2 por tipo de vehículo
    df_annual["co2_reduccion_motos_kg"] = df_annual["ev_energia_motos_kwh"] * FACTOR_CO2_NETO_MOTO_KG_KWH
    df_annual["co2_reduccion_mototaxis_kg"] = df_annual["ev_energia_mototaxis_kwh"] * FACTOR_CO2_NETO_MOTOTAXI_KG_KWH
    
    # Reducción total directa de CO2 (cambio combustible)
    df_annual["reduccion_directa_co2_kg"] = (
        df_annual["co2_reduccion_motos_kg"] + df_annual["co2_reduccion_mototaxis_kg"]
    )
    
    # Columnas alias para compatibilidad con CityLearn
    df_annual["ev_demand_kwh"] = df_annual["ev_energia_total_kwh"]  # Alias para CityLearn
    
    logger.info("✓ Columnas OSINERGMIN y CO2 agregadas al dataset")
    
    # Guardar CSV anual (datetime como índice)
    output_path_annual = output_dir / 'chargers_ev_ano_2024_v3.csv'
    df_annual.to_csv(output_path_annual, index=True)
    logger.info(f"✓ Annual dataset saved: {output_path_annual}")
    logger.info(f"  Shape: {df_annual.shape} (8,760 rows × {len(df_annual.columns)} columns)")
    
    # Crear DataFrame diario de ejemplo (día 1) - mantener datetime como índice
    df_daily = df_annual.iloc[0:24, :].copy()
    output_path_daily = output_dir / 'chargers_ev_dia_2024_v3.csv'
    df_daily.to_csv(output_path_daily, index=True)
    logger.info(f"✓ Daily dataset saved: {output_path_daily}")
    logger.info(f"  Shape: {df_daily.shape} (24 rows × {len(df_daily.columns)} columns)")
    
    # Calcular estadísticas básicas
    total_sockets = 38
    energy_col_names = [col for col in df_annual.columns if '_charging_power_kw' in col]
    total_energy_kwh = sum(df_annual[col].sum() for col in energy_col_names)
    
    # Ocupancia promedio
    active_col_names = [col for col in df_annual.columns if '_active' in col]
    total_active_hours = sum((df_annual[col] == 1).sum() for col in active_col_names)
    occupancy_rate = total_active_hours / (total_sockets * 8760)
    avg_sockets_active = total_active_hours / 8760
    
    # Estadísticas de costos y CO2
    costo_total = df_annual["costo_carga_ev_soles"].sum()
    costo_hp = df_annual.loc[df_annual["is_hora_punta"] == 1, "costo_carga_ev_soles"].sum()
    costo_hfp = df_annual.loc[df_annual["is_hora_punta"] == 0, "costo_carga_ev_soles"].sum()
    energia_hp = df_annual.loc[df_annual["is_hora_punta"] == 1, "ev_energia_total_kwh"].sum()
    energia_hfp = df_annual.loc[df_annual["is_hora_punta"] == 0, "ev_energia_total_kwh"].sum()
    
    co2_total = df_annual["reduccion_directa_co2_kg"].sum()
    co2_motos = df_annual["co2_reduccion_motos_kg"].sum()
    co2_taxis = df_annual["co2_reduccion_mototaxis_kg"].sum()
    energia_motos = df_annual["ev_energia_motos_kwh"].sum()
    energia_taxis = df_annual["ev_energia_mototaxis_kwh"].sum()
    
    logger.info(f"\n{'='*70}")
    logger.info("ESTADÍSTICAS DE SIMULACIÓN v3.0:")
    logger.info(f"{'='*70}")
    logger.info(f"Total energía cargada: {total_energy_kwh:,.1f} kWh/año")
    logger.info(f"  - Motos (30 sockets):    {energia_motos:,.1f} kWh")
    logger.info(f"  - Mototaxis (8 sockets): {energia_taxis:,.1f} kWh")
    logger.info(f"Ocupancia total: {occupancy_rate*100:.2f}%")
    logger.info(f"Sockets activos simultáneos (promedio): {avg_sockets_active:.2f} / {total_sockets}")
    logger.info(f"\n--- COSTOS OSINERGMIN ---")
    logger.info(f"Costo total anual: S/.{costo_total:,.2f}")
    logger.info(f"  - Hora Punta (HP):     S/.{costo_hp:,.2f} ({energia_hp:,.0f} kWh)")
    logger.info(f"  - Fuera de Punta (HFP): S/.{costo_hfp:,.2f} ({energia_hfp:,.0f} kWh)")
    logger.info(f"\n--- REDUCCIÓN DIRECTA CO2 (Cambio combustible) ---")
    logger.info(f"CO2 evitado total: {co2_total:,.1f} kg ({co2_total/1000:,.2f} ton)")
    logger.info(f"  - Motos (factor {FACTOR_CO2_NETO_MOTO_KG_KWH}):    {co2_motos:,.1f} kg")
    logger.info(f"  - Mototaxis (factor {FACTOR_CO2_NETO_MOTOTAXI_KG_KWH}): {co2_taxis:,.1f} kg")
    logger.info(f"{'='*70}\n")
    
    return df_annual, df_daily


# Mantener compatibilidad: esta función llama a v3
def generate_socket_level_dataset(output_dir: str | Path = "data/oe2/chargers") -> pd.DataFrame:
    """Genera dataset detallado con perfil de carga por CADA toma usando v3.0.
    
    (DEPRECATED: Usar generate_socket_level_dataset_v3 directamente)
    
    Returns:
        DataFrame con 8,760 filas y columnas de estado por socket
    """
    # Simplemente llama a la versión v3.0
    df_annual, _ = generate_socket_level_dataset_v3(output_dir)
    return df_annual


# ============================================================================
# FUNCIONES DE ANÁLISIS PARAMÉTRICO Y GENERACIÓN DE TABLAS
# ============================================================================

# Constantes para cálculo de dimensionamiento
BASE_MOTOS = 1636              # Motos estacionadas/día en mall
BASE_MOTOTAXIS = 236           # Mototaxis estacionados/día en mall
PUNTA_RATIO = 0.55             # 55% de cargas en hora punta
HORAS_PUNTA = 5                # 16h-21h = 5 horas
HORAS_FUERA_PUNTA = 7          # 9h-16h = 7 horas
BATTERY_MOTO = 4.6             # kWh batería moto
BATTERY_MOTOTAXI = 7.4         # kWh batería mototaxi
POWER_CHARGER = 7.4            # kW por toma (Modo 3)
CARGAS_HORA_MOTO = 1.0         # 60 min = 1 carga/hora/toma
CARGAS_HORA_TAXI = 0.67        # 90 min = 0.67 cargas/hora/toma
TOMAS_POR_CARGADOR = 2         # 2 tomas por cargador


def calcular_dimensionamiento(pe: float, fc: float) -> dict[str, float]:
    """Calcula el dimensionamiento de cargadores para un escenario dado.
    
    Args:
        pe: Penetración EV (0.0-1.0)
        fc: Factor de carga diaria (0.0-1.0)
        
    Returns:
        Diccionario con métricas de dimensionamiento
    """
    # PASO 1: Vehículos que cargan (pe×fc aplicado UNA VEZ)
    motos_dia = BASE_MOTOS * pe * fc
    taxis_dia = BASE_MOTOTAXIS * pe * fc
    
    # PASO 2: Distribución punta/fuera punta
    motos_punta = motos_dia * PUNTA_RATIO
    taxis_punta = taxis_dia * PUNTA_RATIO
    motos_hora = motos_punta / HORAS_PUNTA
    taxis_hora = taxis_punta / HORAS_PUNTA
    
    # PASO 3: Dimensionar cargadores (playas separadas)
    tomas_motos = int(np.ceil(motos_hora / CARGAS_HORA_MOTO))
    tomas_taxis = int(np.ceil(taxis_hora / CARGAS_HORA_TAXI))
    
    cargadores_motos = int(np.ceil(tomas_motos / TOMAS_POR_CARGADOR))
    cargadores_taxis = int(np.ceil(tomas_taxis / TOMAS_POR_CARGADOR))
    
    # Tomas reales (cargadores × 2)
    tomas_motos_real = cargadores_motos * TOMAS_POR_CARGADOR
    tomas_taxis_real = cargadores_taxis * TOMAS_POR_CARGADOR
    
    cargadores_total = cargadores_motos + cargadores_taxis
    tomas_total = tomas_motos_real + tomas_taxis_real
    
    # Métricas
    sesiones_pico = motos_punta + taxis_punta
    cargas_dia = motos_dia + taxis_dia
    energia_dia = motos_dia * BATTERY_MOTO + taxis_dia * BATTERY_MOTOTAXI
    potencia_pico = tomas_total * POWER_CHARGER
    
    return {
        'pe': pe,
        'fc': fc,
        'cargadores': cargadores_total,
        'cargadores_motos': cargadores_motos,
        'cargadores_taxis': cargadores_taxis,
        'tomas': tomas_total,
        'tomas_motos': tomas_motos_real,
        'tomas_taxis': tomas_taxis_real,
        'sesiones_pico': sesiones_pico,
        'cargas_dia': cargas_dia,
        'energia_dia': energia_dia,
        'potencia_pico': potencia_pico,
        'motos_dia': motos_dia,
        'taxis_dia': taxis_dia
    }


def generate_scenario_table() -> pd.DataFrame:
    """Genera tabla de 4 escenarios de dimensionamiento.
    
    Escenarios:
    - CONSERVADOR: pe=0.20, fc=0.45
    - MEDIANO: pe=0.25, fc=0.50
    - RECOMENDADO*: pe=0.30, fc=0.55
    - MÁXIMO: pe=0.40, fc=0.65
    
    Returns:
        DataFrame con los 4 escenarios y sus métricas
    """
    escenarios = [
        ('CONSERVADOR', 0.20, 0.45),
        ('MEDIANO', 0.25, 0.50),
        ('RECOMENDADO*', 0.30, 0.55),
        ('MÁXIMO', 0.40, 0.65),
    ]
    
    rows = []
    for nombre, pe, fc in escenarios:
        result = calcular_dimensionamiento(pe, fc)
        rows.append({
            'Escenario': nombre,
            'Penetración (pe)': pe,
            'Factor Carga (fc)': fc,
            'Cargadores (2 tomas)': int(result['cargadores']),
            'Total Tomas': int(result['tomas']),
            'Energía Día (kWh)': round(result['energia_dia'], 1)
        })
    
    return pd.DataFrame(rows)


def generate_parametric_table(n_scenarios: int = 101, random_seed: int = 42) -> pd.DataFrame:
    """Genera tabla parametrizada con estadísticas de N escenarios aleatorios.
    
    Simula variando pe en [0.20, 0.40] y fc en [0.45, 0.65] aleatoriamente.
    
    Args:
        n_scenarios: Número de escenarios a simular (default: 101)
        random_seed: Semilla para reproducibilidad (default: 42)
        
    Returns:
        DataFrame con estadísticas (Mínimo, Máximo, Promedio, Mediana, Desv_Std)
    """
    np.random.seed(random_seed)
    
    # Generar escenarios aleatorios
    pe_samples = np.random.uniform(0.20, 0.40, n_scenarios)
    fc_samples = np.random.uniform(0.45, 0.65, n_scenarios)
    
    results = []
    for pe, fc in zip(pe_samples, fc_samples):
        result = calcular_dimensionamiento(pe, fc)
        results.append([
            result['cargadores'],
            result['tomas'],
            result['sesiones_pico'],
            result['cargas_dia'],
            result['energia_dia'],
            result['potencia_pico']
        ])
    
    df = pd.DataFrame(results, columns=[
        'cargadores', 'tomas', 'sesiones_pico', 
        'cargas_dia', 'energia_dia', 'potencia_pico'
    ])
    
    # Calcular estadísticas
    metrics = [
        ('Cargadores (2 tomas) [unid]', 'cargadores'),
        ('Tomas totales [tomas]', 'tomas'),
        ('Sesiones pico 5h [sesiones]', 'sesiones_pico'),
        ('Cargas día total [cargas]', 'cargas_dia'),
        ('Energía día [kWh]', 'energia_dia'),
        ('Potencia pico agregada [kW]', 'potencia_pico')
    ]
    
    stats_rows = []
    for name, col in metrics:
        d = df[col]
        stats_rows.append({
            'Métrica': name,
            'Mínimo': round(d.min(), 1),
            'Máximo': round(d.max(), 1),
            'Promedio': round(d.mean(), 1),
            'Mediana': round(d.median(), 1),
            'Desv_Std': round(d.std(), 2)
        })
    
    return pd.DataFrame(stats_rows)


def print_scenario_table() -> None:
    """Imprime la tabla de escenarios en formato legible."""
    df = generate_scenario_table()
    
    print("\n" + "="*85)
    print("TABLA DE ESCENARIOS - CARGADORES EV MALL IQUITOS (2 tomas/cargador)")
    print("="*85)
    print()
    print("{:<15} {:>15} {:>15} {:>20} {:>10} {:>15}".format(
        'Escenario', 'Penetración(pe)', 'Factor Carga(fc)', 
        'Cargadores(2 tomas)', 'Tomas', 'Energía Día(kWh)'))
    print("-"*85)
    
    for _, row in df.iterrows():
        print("{:<15} {:>15.2f} {:>15.2f} {:>20} {:>10} {:>15.1f}".format(
            row['Escenario'], row['Penetración (pe)'], row['Factor Carga (fc)'],
            row['Cargadores (2 tomas)'], row['Total Tomas'], row['Energía Día (kWh)']))
    
    print("-"*85)
    print()
    print("Nota: * Escenario recomendado basado en IEA GEO 2024 y NREL EV Charging Study.")
    print("      Cargadores Modo 3 con 2 tomas cada uno @ 7.4 kW/toma.")
    print()


def print_parametric_table(n_scenarios: int = 101) -> None:
    """Imprime la tabla parametrizada con estadísticas."""
    df = generate_parametric_table(n_scenarios)
    
    print("\n" + "="*95)
    print("TABLA PARAMETRIZADA - DIMENSIONAMIENTO CARGADORES EV MALL IQUITOS")
    print("="*95)
    print()
    print("{:<35} {:>10} {:>10} {:>10} {:>10} {:>10}".format(
        'Métrica', 'Mínimo', 'Máximo', 'Promedio', 'Mediana', 'Desv_Std'))
    print("-"*95)
    
    for _, row in df.iterrows():
        print("{:<35} {:>10.1f} {:>10.1f} {:>10.1f} {:>10.1f} {:>10.2f}".format(
            row['Métrica'], row['Mínimo'], row['Máximo'],
            row['Promedio'], row['Mediana'], row['Desv_Std']))
    
    print("-"*95)
    print()
    print(f"Nota: Los valores (Mínimo, Máximo, Promedio) se obtuvieron de la simulación")
    print(f"      de {n_scenarios} escenarios aleatorios variando pe en [0.20, 0.40] y fc en [0.45, 0.65].")
    print("      Fuente: Elaboración propia.")
    print()


def print_calculo_detallado(pe: float = 0.30, fc: float = 0.55) -> None:
    """Imprime el cálculo detallado paso a paso para un escenario.
    
    Args:
        pe: Penetración EV (default: 0.30)
        fc: Factor de carga diaria (default: 0.55)
    """
    print("\n" + "="*80)
    print(f"CALCULO DETALLADO DE DIMENSIONAMIENTO (pe={pe}, fc={fc})")
    print("="*80)
    
    # PASO 1
    motos_dia = BASE_MOTOS * pe * fc
    taxis_dia = BASE_MOTOTAXIS * pe * fc
    
    print("\n--- PASO 1: Aplicar pe x fc UNA SOLA VEZ ---")
    print(f"  Motos: {BASE_MOTOS} x {pe} x {fc} = {motos_dia:.0f} motos/dia")
    print(f"  Mototaxis: {BASE_MOTOTAXIS} x {pe} x {fc} = {taxis_dia:.0f} mototaxis/dia")
    
    # PASO 2
    motos_punta = motos_dia * PUNTA_RATIO
    taxis_punta = taxis_dia * PUNTA_RATIO
    motos_hora = motos_punta / HORAS_PUNTA
    taxis_hora = taxis_punta / HORAS_PUNTA
    
    motos_fuera = motos_dia * (1 - PUNTA_RATIO)
    taxis_fuera = taxis_dia * (1 - PUNTA_RATIO)
    motos_hora_fuera = motos_fuera / HORAS_FUERA_PUNTA
    taxis_hora_fuera = taxis_fuera / HORAS_FUERA_PUNTA
    
    print("\n--- PASO 2: Distribuir Punta (55%) vs Fuera Punta (45%) ---")
    print("  MOTOS:")
    print(f"    Punta: {motos_dia:.0f} x 0.55 = {motos_punta:.0f} en {HORAS_PUNTA}h -> {motos_hora:.1f}/hora")
    print(f"    Fuera punta: {motos_dia:.0f} x 0.45 = {motos_fuera:.0f} en {HORAS_FUERA_PUNTA}h -> {motos_hora_fuera:.1f}/hora")
    print("  MOTOTAXIS:")
    print(f"    Punta: {taxis_dia:.0f} x 0.55 = {taxis_punta:.0f} en {HORAS_PUNTA}h -> {taxis_hora:.1f}/hora")
    print(f"    Fuera punta: {taxis_dia:.0f} x 0.45 = {taxis_fuera:.0f} en {HORAS_FUERA_PUNTA}h -> {taxis_hora_fuera:.1f}/hora")
    
    # PASO 3
    tomas_motos = int(np.ceil(motos_hora / CARGAS_HORA_MOTO))
    tomas_taxis = int(np.ceil(taxis_hora / CARGAS_HORA_TAXI))
    cargadores_motos = int(np.ceil(tomas_motos / TOMAS_POR_CARGADOR))
    cargadores_taxis = int(np.ceil(tomas_taxis / TOMAS_POR_CARGADOR))
    
    print("\n--- PASO 3: Dimensionar Cargadores (Playas Separadas) ---")
    print("  [P] PLAYA MOTOS:")
    print(f"    Demanda punta: {motos_hora:.1f} motos/hora")
    print(f"    Capacidad por toma: {CARGAS_HORA_MOTO} cargas/hora (60 min)")
    print(f"    Tomas necesarias: {motos_hora:.1f} / {CARGAS_HORA_MOTO} = {tomas_motos} tomas")
    print(f"    Cargadores: {tomas_motos} / 2 = {cargadores_motos} CARGADORES")
    tomas_motos_real = cargadores_motos * 2
    print(f"    Verificar fuera punta: {motos_hora_fuera:.1f}/hora < {tomas_motos_real} tomas [OK]")
    
    print("\n  [P] PLAYA MOTOTAXIS:")
    print(f"    Demanda punta: {taxis_hora:.1f} mototaxis/hora")
    print(f"    Capacidad por toma: {CARGAS_HORA_TAXI} cargas/hora (90 min)")
    tomas_calc = taxis_hora / CARGAS_HORA_TAXI
    print(f"    Tomas necesarias: {taxis_hora:.1f} / {CARGAS_HORA_TAXI} = {tomas_calc:.1f} -> {tomas_taxis} tomas")
    print(f"    Cargadores: {tomas_taxis} / 2 = {cargadores_taxis} CARGADORES")
    tomas_taxis_real = cargadores_taxis * 2
    taxis_fuera_tomas = taxis_hora_fuera / CARGAS_HORA_TAXI
    print(f"    Verificar fuera punta: {taxis_hora_fuera:.1f} / {CARGAS_HORA_TAXI} = {taxis_fuera_tomas:.1f} < {tomas_taxis_real} tomas [OK]")
    
    # RESULTADO
    cargadores_total = cargadores_motos + cargadores_taxis
    tomas_total = tomas_motos_real + tomas_taxis_real
    potencia = tomas_total * POWER_CHARGER
    energia = motos_dia * BATTERY_MOTO + taxis_dia * BATTERY_MOTOTAXI
    
    print("\n" + "="*80)
    print(f"RESULTADO: {cargadores_total} CARGADORES x 2 TOMAS = {tomas_total} TOMAS = {potencia:.1f} kW")
    print("="*80)
    print(f"  - PLAYA MOTOS: {cargadores_motos} cargadores x 2 = {tomas_motos_real} tomas")
    print(f"  - PLAYA MOTOTAXIS: {cargadores_taxis} cargadores x 2 = {tomas_taxis_real} tomas")
    print(f"  - Potencia instalada: {tomas_total} x {POWER_CHARGER} kW = {potencia:.1f} kW")
    print(f"  - Energia diaria: {motos_dia:.0f}x{BATTERY_MOTO} + {taxis_dia:.0f}x{BATTERY_MOTOTAXI} = {energia:.1f} kWh/dia")
    print()


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN Y TABLAS RESUMEN v5.2
# ============================================================================

def generate_vehicles_per_period_table(pe: float = 0.30, fc: float = 0.55) -> pd.DataFrame:
    """Genera tabla de vehículos a cargar por período (diario/mensual/anual).
    
    Args:
        pe: Penetración EV (default: 0.30)
        fc: Factor de carga diaria (default: 0.55)
        
    Returns:
        DataFrame con columnas [Periodo, Motos, Mototaxis, Total]
    """
    motos_diario = int(round(BASE_MOTOS * pe * fc))
    mototaxis_diario = int(round(BASE_MOTOTAXIS * pe * fc))
    
    data = [
        {'Periodo': 'Diario', 'Motos': motos_diario, 'Mototaxis': mototaxis_diario},
        {'Periodo': 'Mensual', 'Motos': motos_diario * 30, 'Mototaxis': mototaxis_diario * 30},
        {'Periodo': 'Anual', 'Motos': motos_diario * 365, 'Mototaxis': mototaxis_diario * 365},
    ]
    
    df = pd.DataFrame(data)
    df['Total'] = df['Motos'] + df['Mototaxis']
    return df


def plot_vehicles_per_period(
    pe: float = 0.30, 
    fc: float = 0.55,
    output_path: str | Path = "outputs/vehiculos_por_periodo_v52.png",
    show: bool = False
) -> Path:
    """Genera gráfica de vehículos a cargar por período.
    
    Args:
        pe: Penetración EV (default: 0.30)
        fc: Factor de carga diaria (default: 0.55)
        output_path: Ruta para guardar la imagen
        show: Si True, muestra la gráfica interactivamente
        
    Returns:
        Path al archivo generado
    """
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df = generate_vehicles_per_period_table(pe, fc)
    
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle('Cantidad de Vehiculos a Cargar por Periodo (Escenario Recomendado v5.2)', 
                 fontsize=14, fontweight='bold')
    
    periodos = ['Diario', 'Mensual', 'Anual']
    colors = ['#4A90D9', '#E8A5A5']  # Azul motos, rosa mototaxis
    
    for i, (ax, periodo) in enumerate(zip(axes, periodos)):
        row = df[df['Periodo'] == periodo].iloc[0]
        x = np.array([0, 1])
        valores = [row['Motos'], row['Mototaxis']]
        bars = ax.bar(x, valores, color=colors, width=0.6, edgecolor='black', linewidth=0.5)
        
        for bar, val in zip(bars, valores):
            height = bar.get_height()
            ax.annotate(f'{val:,}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords='offset points',
                        ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_title(periodo, fontsize=12)
        ax.set_ylabel('Cantidad de Vehiculos')
        ax.set_xticks(x)
        ax.set_xticklabels(['Motos', 'Mototaxis'])
        ax.set_ylim(0, max(valores) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return output_path


def plot_hourly_load_profile(
    output_path: str | Path = "outputs/perfil_horario_carga_v52.png",
    show: bool = False
) -> Path:
    """Genera gráfica del perfil horario de carga.
    
    Usa el factor operativo definido en get_operational_factor() para
    calcular la potencia agregada por hora (38 tomas × 7.4 kW × factor).
    
    Args:
        output_path: Ruta para guardar la imagen
        show: Si True, muestra la gráfica interactivamente
        
    Returns:
        Path al archivo generado
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Parámetros v5.2
    tomas = 38
    power_per_socket = POWER_CHARGER  # 7.4 kW
    max_power = tomas * power_per_socket  # 281.2 kW
    
    hours = list(range(24))
    factors = [get_operational_factor(h) for h in hours]
    power_kw = [max_power * f for f in factors]
    
    # Crear gráfica
    fig, ax = plt.subplots(figsize=(12, 6))
    
    colors = ['#4A90D9' if not (18 <= h < 21) else '#E74C3C' for h in hours]
    bars = ax.bar(hours, power_kw, color=colors, edgecolor='black', linewidth=0.5)
    
    # Etiquetas en barras (solo las que tienen valor)
    for h, bar in enumerate(bars):
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{height:.0f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords='offset points',
                        ha='center', va='bottom', fontsize=8)
    
    # Leyenda para pico
    legend_elements = [Patch(facecolor='#E74C3C', edgecolor='black', label='Pico 18-21h')]
    ax.legend(handles=legend_elements, loc='upper left')
    
    ax.set_xlabel('Hora del día')
    ax.set_ylabel('Potencia agregada (kW)')
    ax.set_title('Perfil horario de carga (motos + mototaxis) - v5.2')
    ax.set_xticks(hours)
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(0, max_power * 1.1)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return output_path


def print_vehicles_per_period_table(pe: float = 0.30, fc: float = 0.55) -> None:
    """Imprime la tabla de vehículos por período en formato legible.
    
    Args:
        pe: Penetración EV (default: 0.30)
        fc: Factor de carga diaria (default: 0.55)
    """
    df = generate_vehicles_per_period_table(pe, fc)
    
    print("\n" + "="*60)
    print("VEHÍCULOS A CARGAR POR PERÍODO (pe={:.2f}, fc={:.2f})".format(pe, fc))
    print("="*60)
    print()
    print("{:<10} {:>12} {:>12} {:>12}".format('Periodo', 'Motos', 'Mototaxis', 'Total'))
    print("-"*60)
    
    for _, row in df.iterrows():
        print("{:<10} {:>12,} {:>12,} {:>12,}".format(
            row['Periodo'], row['Motos'], row['Mototaxis'], row['Total']))
    
    print("-"*60)
    print()
    print("Nota: Base = {} motos + {} mototaxis estacionados/día".format(BASE_MOTOS, BASE_MOTOTAXIS))
    print("      Vehículos que cargan = Base × pe × fc")
    print()


def print_hourly_load_profile() -> None:
    """Imprime el perfil horario de carga en formato legible."""
    tomas = 38
    max_power = tomas * POWER_CHARGER
    
    print("\n" + "="*60)
    print("PERFIL HORARIO DE CARGA v5.2 (38 tomas × 7.4 kW)")
    print("="*60)
    print()
    print("{:<8} {:>12} {:>12} {:>10}".format('Hora', 'Factor (%)', 'Potencia (kW)', 'Estado'))
    print("-"*60)
    
    energy_total = 0.0
    for h in range(24):
        factor = get_operational_factor(h)
        power = max_power * factor
        energy_total += power
        
        if power > 0:
            estado = "PICO" if 18 <= h < 21 else ""
            print("{:02d}:00    {:>12.0%} {:>12.1f} {:>10}".format(h, factor, power, estado))
    
    print("-"*60)
    print()
    print("Potencia máxima instalada: {:.1f} kW".format(max_power))
    print("Energía máxima/día (100% ocupación): {:.1f} kWh".format(energy_total))
    print("Pico: 18:00-21:00 (100% capacidad)")
    print()


if __name__ == "__main__":
    # Script para generar dataset al ejecutar el módulo directamente
    print("\n" + "="*100)
    print("GENERADOR DE DATASET ESTOCÁSTICO DE CARGADORES EV v5.2")
    print("Modo 3 @ 7.4 kW - Mall Iquitos - TIEMPOS REALES DE CARGA")
    print("="*100)
    
    # =========================================================================
    # SECCIÓN 1: TABLA DE ESCENARIOS (CONSERVADOR, MEDIANO, RECOMENDADO, MÁXIMO)
    # =========================================================================
    print_scenario_table()
    
    # =========================================================================
    # SECCIÓN 2: TABLA PARAMETRIZADA (101 escenarios aleatorios)
    # =========================================================================
    print_parametric_table(101)
    
    # =========================================================================
    # SECCIÓN 3: CÁLCULO DETALLADO PASO A PASO (escenario recomendado)
    # =========================================================================
    print_calculo_detallado(pe=0.30, fc=0.55)
    
    # =========================================================================
    # SECCIÓN 4: TABLA DE VEHÍCULOS POR PERÍODO
    # =========================================================================
    print_vehicles_per_period_table(pe=0.30, fc=0.55)
    
    # =========================================================================
    # SECCIÓN 5: PERFIL HORARIO DE CARGA
    # =========================================================================
    print_hourly_load_profile()
    
    # =========================================================================
    # SECCION 6: GENERACION DE GRAFICAS
    # =========================================================================
    print("\n[GRAFICAS] Generando graficas...")
    
    path1 = plot_vehicles_per_period(pe=0.30, fc=0.55)
    print(f"   [OK] Grafica vehiculos/periodo: {path1}")
    
    path2 = plot_hourly_load_profile()
    print(f"   [OK] Grafica perfil horario: {path2}")
    
    # =========================================================================
    # SECCION 7: GENERACION DE DATASET ESTOCASTICO
    # =========================================================================
    print("\n[REF] REFERENCIAS METODOLOGICAS:")
    print("   - IEA Global EV Outlook 2024 (pe=30% mercados emergentes 2030)")
    print("   - BNEF Electric Vehicle Outlook 2025 (2/3 ruedas Asia)")
    print("   - ICCT Electric two/three-wheelers India (2022)")
    print("   - NREL EV Charging Behavior Study (fc=0.55)")
    
    print("\n[TIME] TIEMPOS REALES DE CARGA (incluye perdidas y taper):")
    print("   - CHARGING_EFFICIENCY = 0.62 (perdidas cargador + cable + bateria + taper)")
    print("   - Moto 4.6 kWh @ 7.4 kW: ideal 41 min -> real ~60 min (50-70)")
    print("   - Mototaxi 7.4 kWh @ 7.4 kW: ideal 67 min -> real ~90 min (75-105)")
    
    print("\n[SIM] PARAMETROS DE SIMULACION v5.2:")
    print(f"   - Llegadas: Poisson (motos lambda=0.69, taxis lambda=0.375 veh/toma/h)")
    print(f"   - SOC Inicial: N(20%, 10%) -> carga ~80% de bateria")
    print(f"   - Objetivo: 100% SOC (carga completa)")
    print(f"   - Horario Mall: 9-22h (13 horas operativas)")
    print(f"   - Reproducibilidad: random_seed=42")
    
    print("\n[GEN] Generando dataset anual v5.2...")
    df_annual, df_daily = generate_socket_level_dataset_v3()
    
    # Calcular resumen
    total_energy = sum(df_annual[col].sum() for col in df_annual.columns if '_charging_power_kw' in col)
    
    print(f"\n[OK] GENERACION COMPLETADA EXITOSAMENTE")
    print(f"\n   Dataset Anual:")
    print(f"   - Filas: {len(df_annual)} (8,760 horas = 1 ano)")
    print(f"   - Columnas: {len(df_annual.columns)}")
    print(f"   - Energia total: {total_energy:,.0f} kWh/ano")
    print(f"   - Archivo: data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    
    print(f"\n   Columnas por toma (9 cada una, 38 tomas):")
    print(f"     - charger_power_kw: Potencia nominal cargador (7.4 kW)")
    print(f"     - battery_kwh: Capacidad bateria (4.6 moto / 7.4 mototaxi)")
    print(f"     - vehicle_type: Tipo vehiculo (MOTO / MOTOTAXI)")
    print(f"     - soc_current/arrival/target: Estados de carga")
    print(f"     - active: Toma ocupada (0/1)")
    print(f"     - charging_power_kw: Potencia instantanea real")
    print(f"     - vehicle_count: Vehiculos atendidos")
    
    # =========================================================================
    # SECCION 8: COSTOS OSINERGMIN Y REDUCCION CO2
    # =========================================================================
    print(f"\n" + "="*70)
    print("SECCION 8: COSTOS OSINERGMIN Y REDUCCION CO2 (CAMBIO COMBUSTIBLE)")
    print("="*70)
    
    # Estadísticas de costos
    costo_total = df_annual["costo_carga_ev_soles"].sum()
    costo_hp = df_annual.loc[df_annual["is_hora_punta"] == 1, "costo_carga_ev_soles"].sum()
    costo_hfp = df_annual.loc[df_annual["is_hora_punta"] == 0, "costo_carga_ev_soles"].sum()
    energia_hp = df_annual.loc[df_annual["is_hora_punta"] == 1, "ev_energia_total_kwh"].sum()
    energia_hfp = df_annual.loc[df_annual["is_hora_punta"] == 0, "ev_energia_total_kwh"].sum()
    
    print(f"\n[TARIFAS] OSINERGMIN Electro Oriente (Iquitos):")
    print(f"   - Hora Punta (HP):     S/.{TARIFA_ENERGIA_HP_SOLES}/kWh (18:00-22:59)")
    print(f"   - Fuera de Punta (HFP): S/.{TARIFA_ENERGIA_HFP_SOLES}/kWh (resto)")
    
    print(f"\n[COSTOS] Carga EV anual:")
    print(f"   Costo total:           S/.{costo_total:,.2f}")
    print(f"     - Hora Punta (HP):   S/.{costo_hp:,.2f} ({energia_hp:,.0f} kWh)")
    print(f"     - Fuera Punta (HFP): S/.{costo_hfp:,.2f} ({energia_hfp:,.0f} kWh)")
    
    # Estadísticas de CO2
    co2_total = df_annual["reduccion_directa_co2_kg"].sum()
    co2_motos = df_annual["co2_reduccion_motos_kg"].sum()
    co2_taxis = df_annual["co2_reduccion_mototaxis_kg"].sum()
    energia_motos = df_annual["ev_energia_motos_kwh"].sum()
    energia_taxis = df_annual["ev_energia_mototaxis_kwh"].sum()
    
    print(f"\n[CO2] Reduccion DIRECTA por cambio combustible (gasolina -> EV):")
    print(f"   Factor moto:     {FACTOR_CO2_NETO_MOTO_KG_KWH} kg CO2/kWh (neto)")
    print(f"   Factor mototaxi: {FACTOR_CO2_NETO_MOTOTAXI_KG_KWH} kg CO2/kWh (neto)")
    print(f"\n   CO2 evitado total: {co2_total:,.1f} kg ({co2_total/1000:,.2f} ton/ano)")
    print(f"     - Motos ({energia_motos:,.0f} kWh):    {co2_motos:,.1f} kg ({co2_motos/1000:,.2f} ton)")
    print(f"     - Mototaxis ({energia_taxis:,.0f} kWh): {co2_taxis:,.1f} kg ({co2_taxis/1000:,.2f} ton)")
    
    # Equivalencia en litros de gasolina
    litros_gasolina_evitados = co2_total / FACTOR_CO2_GASOLINA_KG_L
    print(f"\n   Equivalente en litros gasolina evitados: {litros_gasolina_evitados:,.0f} L/ano")
    print(f"   (Factor: {FACTOR_CO2_GASOLINA_KG_L} kg CO2/L gasolina)")
    
    print(f"\n[NOTA] Esta es reduccion DIRECTA (cambio de combustible).")
    print(f"       La reduccion INDIRECTA (desplazamiento de diesel en la red)")
    print(f"       se calcula en solar_pvlib.py")
    
    # Nuevas columnas agregadas
    print(f"\n[COLS] Columnas OSINERGMIN y CO2 agregadas:")
    osinergmin_cols = ['is_hora_punta', 'tarifa_aplicada_soles', 'ev_energia_total_kwh',
                       'costo_carga_ev_soles', 'ev_energia_motos_kwh', 'ev_energia_mototaxis_kwh',
                       'co2_reduccion_motos_kg', 'co2_reduccion_mototaxis_kg', 
                       'reduccion_directa_co2_kg', 'ev_demand_kwh']
    for col in osinergmin_cols:
        if col in df_annual.columns:
            print(f"     - {col}")
    
    print(f"\n   Dataset Diario (ejemplo Dia 1):")
    print(f"   - Filas: {len(df_daily)} (24 horas)")
    print(f"   - Archivo: data/oe2/chargers/chargers_ev_dia_2024_v3.csv")
    
    print(f"\n   Ejemplo columnas socket_000 (moto):")
    moto_cols = [c for c in df_annual.columns if 'socket_000_' in c]
    for col in moto_cols:
        print(f"     - {col}")
    
    print(f"\n   Ejemplo columnas socket_030 (mototaxi):")
    taxi_cols = [c for c in df_annual.columns if 'socket_030_' in c]
    for col in taxi_cols:
        print(f"     - {col}")
    
    # Verificación CityLearn
    print(f"\n" + "="*70)
    print("VERIFICACION PARA CITYLEARN")
    print("="*70)
    print(f"\n   Requisitos CityLearn:")
    print(f"     [OK] Filas: {len(df_annual)} (esperado: 8,760)")
    print(f"     [OK] Indice: datetime")
    print(f"     [OK] ev_demand_kwh presente: {'ev_demand_kwh' in df_annual.columns}")
    print(f"     [OK] is_hora_punta presente: {'is_hora_punta' in df_annual.columns}")
    print(f"     [OK] reduccion_directa_co2_kg presente: {'reduccion_directa_co2_kg' in df_annual.columns}")
    
    print("\n" + "="*100 + "\n")
