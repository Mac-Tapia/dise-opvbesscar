"""Especificaciones de cargadores de EV para OE2.

Define estructuras de datos inmutables para cargadores y sus características.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
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


def create_iquitos_chargers() -> ChargerSet:
    """Crea el conjunto de cargadores estándar para Iquitos.

    Especificación:
    - 28 cargadores para motos (112 motos total × 1 socket, pero con agrupación)
    - 4 cargadores para mototaxis (16 mototaxis × 1 socket, pero con agrupación)
    - Cada cargador tiene 4 sockets
    - Total: 32 cargadores × 4 sockets = 128 acciones controlables

    Returns:
        ChargerSet inmutable con especificaciones
    """
    specs = []

    # Motos: 28 cargadores × 4 sockets = 112 sockets (112 motos)
    for i in range(28):
        specs.append(ChargerSpec(
            charger_id=i,
            max_power_kw=2.125,  # Estándar OE2
            vehicle_type="moto",
            sockets=4
        ))

    # Mototaxis: 4 cargadores × 4 sockets = 16 sockets (16 mototaxis)
    for i in range(28, 32):
        specs.append(ChargerSpec(
            charger_id=i,
            max_power_kw=2.125,  # Estándar OE2
            vehicle_type="mototaxi",
            sockets=4
        ))

    return ChargerSet(chargers=tuple(specs))


def validate_charger_set(charger_set: ChargerSet) -> dict[str, Any]:
    """Valida un conjunto de cargadores.

    Verifica:
    - Mínimo 32 cargadores base
    - Máximo 256 sockets
    - Distribución correcta (motos + mototaxis)
    - IDs únicos y secuenciales

    Args:
        charger_set: Conjunto a validar

    Returns:
        Diccionario con resultados de validación
    """
    results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }

    # Verificar cantidad mínima
    if charger_set.count < 32:
        results["errors"].append(f"Too few chargers: {charger_set.count} < 32")
        results["is_valid"] = False

    # Verificar cantidad máxima de sockets
    if charger_set.total_sockets > 256:
        results["errors"].append(
            f"Too many sockets: {charger_set.total_sockets} > 256"
        )
        results["is_valid"] = False

    # Verificar IDs únicos y secuenciales
    ids = [c.charger_id for c in charger_set.chargers]
    if len(ids) != len(set(ids)):
        results["errors"].append("Charger IDs are not unique")
        results["is_valid"] = False

    if ids != list(range(len(ids))):
        results["warnings"].append(
            f"Charger IDs are not sequential: {ids}"
        )

    # Verificar distribución
    if charger_set.motos_count == 0:
        results["warnings"].append("No chargers for motos")

    if charger_set.mototaxis_count == 0:
        results["warnings"].append("No chargers for mototaxis")

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
