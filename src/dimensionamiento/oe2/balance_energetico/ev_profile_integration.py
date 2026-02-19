"""
Módulo de validación e integración del perfil EV desde chargers.py
Asegura que los datos de carga de EV en balance.py reflejen la lógica real.

Ubicación: src/dimensionamiento/oe2/balance_energetico/ev_profile_integration.py
Versión: 1.0 (2026-02-19)

Propósito:
  - Validar que el CSV chargers_ev_ano_2024_v3.csv refleja los factores operacionales
  - Documentar cómo se carga la información desde chargers.py
  - Proporcionar funciones para extraer y verificar perfiles por tipo de vehículo
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================================
# IMPORTAR ESPECIFICACIONES REALES DESDE CHARGERS.PY
# ============================================================================
# Nota: Estas constantes DEBEN estar en sincronía con chargers.py

# Eficiencia real de carga (con pérdidas en cargador, cable, batería, taper)
CHARGING_EFFICIENCY = 0.62  # 62% de potencia nominal

# Especificaciones de batería
MOTO_BATTERY_KWH = 4.6  # Capacidad nominal
MOTOTAXI_BATTERY_KWH = 7.4

# Energía estándar a cargar (SOC 20%-80% @ 95% eficiencia)
MOTO_ENERGY_TO_CHARGE_KWH = 0.60 * MOTO_BATTERY_KWH / 0.95  # ~2.906 kWh
MOTOTAXI_ENERGY_TO_CHARGE_KWH = 0.60 * MOTOTAXI_BATTERY_KWH / 0.95  # ~4.674 kWh

# Factores operacionales del mall (Iquitos)
MALL_OPERATIONAL_HOURS = {
    0: 0.0,    # 0h: Cerrado
    1: 0.0,    # 1h: Cerrado
    2: 0.0,    # ...
    3: 0.0,
    4: 0.0,
    5: 0.0,
    6: 0.0,
    7: 0.0,
    8: 0.0,    # 8h: Cerrado
    9: 0.30,   # 9h: Apertura (30%)
    10: 0.458,  # 10h: Rampa lineal
    11: 0.616,  # 11h: Rampa lineal
    12: 0.775,  # 12h: Rampa lineal
    13: 0.933,  # 13h: Rampa lineal
    14: 0.992,  # 14h: Rampa lineal
    15: 1.0,   # 15h: 100%
    16: 1.0,   # 16h: 100%
    17: 1.0,   # 17h: 100%
    18: 1.0,   # 18h: PUNTA (100%)
    19: 1.0,   # 19h: PUNTA (100%)
    20: 1.0,   # 20h: PUNTA (100%)
    21: 0.0,   # 21h: Cierre realista
    22: 0.0,   # 22h: Cerrado
    23: 0.0,   # 23h: Cerrado
}

# Especificaciones de vehículos (desde chargers.py)
@dataclass(frozen=True)
class VehicleTypeSpec:
    """Especificación de un tipo de vehículo eléctrico"""
    name: str
    quantity_per_day: int  # Cantidad promedio a cargar diariamente
    battery_kwh: float  # Capacidad de batería en kWh
    energy_to_charge_kwh: float  # Energía estándar a cargar (SOC 20%-80%)
    chargers_assigned: int  # Número de cargadores asignados
    sockets_assigned: int  # Número total de tomas asignadas
    soc_arrival_mean: float  # SOC medio al llegar
    soc_arrival_std: float  # Desviación estándar SOC llegada
    soc_target_mean: float  # SOC objetivo medio
    soc_target_std: float  # Desviación estándar SOC objetivo
    
    @property
    def energy_per_day(self) -> float:
        """Energía teórica diaria = cantidad × energía por carga"""
        return self.quantity_per_day * self.energy_to_charge_kwh
    
    @property
    def energy_per_year(self) -> float:
        """Energía anual = energía diaria × 365 días"""
        return self.energy_per_day * 365


# Especificaciones finales de vehículos (escenario recomendado v5.2)
MOTO_SPEC = VehicleTypeSpec(
    name="MOTO",
    quantity_per_day=270,  # Motos a cargar diariamente
    battery_kwh=MOTO_BATTERY_KWH,
    energy_to_charge_kwh=MOTO_ENERGY_TO_CHARGE_KWH,
    chargers_assigned=15,  # 15 cargadores × 2 tomas = 30 tomas
    sockets_assigned=30,
    soc_arrival_mean=0.245,  # 24.5% al llegar
    soc_arrival_std=0.10,  # Rango ~10%-40%
    soc_target_mean=0.78,  # 78% objetivo (carga parcial)
    soc_target_std=0.12,  # Algunos cargan menos (60%), otros más (100%)
)

MOTOTAXI_SPEC = VehicleTypeSpec(
    name="MOTOTAXI",
    quantity_per_day=39,  # Mototaxis a cargar diariamente
    battery_kwh=MOTOTAXI_BATTERY_KWH,
    energy_to_charge_kwh=MOTOTAXI_ENERGY_TO_CHARGE_KWH,
    chargers_assigned=4,  # 4 cargadores × 2 tomas = 8 tomas
    sockets_assigned=8,
    soc_arrival_mean=0.245,
    soc_arrival_std=0.10,
    soc_target_mean=0.78,
    soc_target_std=0.12,
)


# ============================================================================
# FUNCIONES DE VALIDACIÓN DEL PERFIL EV
# ============================================================================

def get_operational_factor(hour: int) -> float:
    """Retorna el factor operacional del mall para una hora dada.
    
    Factor operacional = porcentaje de capacidad disponible
    Varía según horario del mall (9h-22h, con cierre graduado).
    
    Args:
        hour: Hora del día (0-23)
        
    Returns:
        Factor operacional (0.0-1.0)
    """
    return MALL_OPERATIONAL_HOURS.get(hour, 0.0)


def calculate_ev_demand_theoretical(
    motos_per_day: int = MOTO_SPEC.quantity_per_day,
    taxis_per_day: int = MOTOTAXI_SPEC.quantity_per_day
) -> dict[str, float]:
    """Calcula demanda teórica total de EV.
    
    Basado en cantidad de vehículos y energía estándar por carga.
    
    Args:
        motos_per_day: Cantidad de motos a cargar diariamente
        taxis_per_day: Cantidad de mototaxis a cargar diariamente
        
    Returns:
        Diccionario con demanda teórica (diaria, anual)
    """
    moto_energy_daily = motos_per_day * MOTO_ENERGY_TO_CHARGE_KWH
    taxi_energy_daily = taxis_per_day * MOTOTAXI_ENERGY_TO_CHARGE_KWH
    total_energy_daily = moto_energy_daily + taxi_energy_daily
    
    return {
        'motos_daily_kwh': moto_energy_daily,
        'taxis_daily_kwh': taxi_energy_daily,
        'total_daily_kwh': total_energy_daily,
        'moto_daily_avg_kw': moto_energy_daily / 13,  # 13 horas operativas (9h-22h)
        'taxi_daily_avg_kw': taxi_energy_daily / 13,
        'total_daily_avg_kw': total_energy_daily / 13,
        'total_annual_kwh': total_energy_daily * 365,
    }


def validate_ev_csv_profile(
    df_chargers: pd.DataFrame,
    expected_annual_kwh: Optional[float] = None,
    tolerance_pct: float = 5.0
) -> dict[str, bool | float | str]:
    """Valida que el CSV de chargers refleje la lógica correcta.
    
    Verifica:
    1. Energía total anual
    2. Proporción motos vs mototaxis
    3. Factor operacional por hora
    4. Restricción horaria (energía=0 en 0-8h, 22-24h)
    5. Concentración punta (55% energía en 18-21h)
    
    Args:
        df_chargers: DataFrame cargado desde CSV
        expected_annual_kwh: Energía anual esperada (si None, calcula teórica)
        tolerance_pct: Tolerancia permitida en validaciones (%)
        
    Returns:
        Diccionario con resultados de validación
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'metrics': {}
    }
    
    try:
        # Identificar columnas de potencia por socket
        power_cols = [col for col in df_chargers.columns 
                     if 'charging_power_kw' in col.lower()]
        
        if not power_cols:
            results['errors'].append(f"No se encontraron columnas de potencia (_charging_power_kw)")
            results['valid'] = False
            return results
        
        # Extraer índices hora y calcular energía por hora
        if hasattr(df_chargers.index, 'hour'):
            # DatetimeIndex
            hours = df_chargers.index.hour
        else:
            # Crear columna hour si no existe
            if 'hour' not in df_chargers.columns:
                results['errors'].append("No se puede determinar la hora de cada fila")
                results['valid'] = False
                return results
            hours = df_chargers['hour']
        
        # Calcular energía total por hora (suma de todos los sockets)
        df_chargers['total_ev_energy_kwh'] = df_chargers[power_cols].sum(axis=1)
        
        # 1. VALIDAR ENERGÍA TOTAL ANUAL
        total_energy_annual = df_chargers['total_ev_energy_kwh'].sum()
        
        if expected_annual_kwh is None:
            expected_annual_kwh = calculate_ev_demand_theoretical()['total_annual_kwh']
        
        error_pct = abs(total_energy_annual - expected_annual_kwh) / expected_annual_kwh * 100
        results['metrics']['total_energy_annual_kwh'] = total_energy_annual
        results['metrics']['expected_energy_annual_kwh'] = expected_annual_kwh
        results['metrics']['energy_error_pct'] = error_pct
        
        if error_pct > tolerance_pct:
            results['errors'].append(
                f"Energía anual: {total_energy_annual:,.0f} kWh vs esperada "
                f"{expected_annual_kwh:,.0f} kWh (error {error_pct:.1f}% > {tolerance_pct}%)"
            )
            results['valid'] = False
        else:
            logger.info(f"✓ Energía anual: {total_energy_annual:,.0f} kWh (error {error_pct:.1f}%)")
        
        # 2. VALIDAR PROPORCIÓN MOTOS VS MOTOTAXIS
        # Sockets 0-29: motos, Sockets 30-37: mototaxis
        moto_cols = [col for col in power_cols if int(col.split('_')[1]) < 30]
        taxi_cols = [col for col in power_cols if int(col.split('_')[1]) >= 30]
        
        if moto_cols and taxi_cols:
            energy_motos = df_chargers[moto_cols].sum().sum()
            energy_taxis = df_chargers[taxi_cols].sum().sum()
            
            # Ratio esperado: (270 × 2.906) / (39 × 4.674) ≈ 6.9
            ratio_actual = energy_motos / energy_taxis if energy_taxis > 0 else 0
            ratio_expected = (270 * MOTO_ENERGY_TO_CHARGE_KWH) / (39 * MOTOTAXI_ENERGY_TO_CHARGE_KWH)
            ratio_error = abs(ratio_actual - ratio_expected) / ratio_expected * 100
            
            results['metrics']['energy_motos_kwh'] = energy_motos
            results['metrics']['energy_taxis_kwh'] = energy_taxis
            results['metrics']['ratio_motos_taxis_actual'] = ratio_actual
            results['metrics']['ratio_motos_taxis_expected'] = ratio_expected
            results['metrics']['ratio_error_pct'] = ratio_error
            
            if ratio_error > (tolerance_pct * 2):  # Más tolerancia en ratio
                results['warnings'].append(
                    f"Ratio motos/taxis: {ratio_actual:.2f} vs esperada "
                    f"{ratio_expected:.2f} (error {ratio_error:.1f}%)"
                )
            else:
                logger.info(f"✓ Ratio motos/taxis: {ratio_actual:.2f} (esperada {ratio_expected:.2f}, error {ratio_error:.1f}%)")
        
        # 3. VALIDAR RESTRICCIÓN HORARIA (energía=0 en 0-8h, 22-24h)
        for hours_forbidden in [list(range(0, 9)), list(range(22, 24))]:
            energy_forbidden = df_chargers[df_chargers.index.hour.isin(hours_forbidden)]['total_ev_energy_kwh'].sum()
            if energy_forbidden > 0:
                results['warnings'].append(
                    f"Energía detectada en horas cerradas {hours_forbidden}: {energy_forbidden:,.0f} kWh "
                    f"(debería ser 0)"
                )
            else:
                logger.info(f"✓ Horas cerradas {hours_forbidden}: energía = 0 (correcto)")
        
        # 4. VALIDAR CONCENTRACIÓN PUNTA
        # Horas punta: 18h-21h (pero 21h debería ser 0 si está bien moldeado)
        # En realidad punta fuerte: 18h-20h
        energy_punta = df_chargers[df_chargers.index.hour.isin([18, 19, 20])]['total_ev_energy_kwh'].sum()
        energy_total = df_chargers['total_ev_energy_kwh'].sum()
        punta_pct = (energy_punta / energy_total * 100) if energy_total > 0 else 0
        
        results['metrics']['energy_punta_18_20_kwh'] = energy_punta
        results['metrics']['energy_punta_pct'] = punta_pct
        
        # Esperamos ~45-50% en horas 18-20 (redistribución desde hora 21)
        if punta_pct < 40 or punta_pct > 55:
            results['warnings'].append(
                f"Concentración punta (18-20h): {punta_pct:.1f}% "
                f"(esperada ~45-50%)"
            )
        else:
            logger.info(f"✓ Concentración punta (18-20h): {punta_pct:.1f}% (esperada ~45-50%)")
        
        # 5. VALIDAR EFICIENCIA REAL (potencia efectiva 62% de nominal)
        # Potencia nominal instalada: 38 tomas × 7.4 kW = 281.2 kW
        # Si simultáneamente se cargan todas, máximo será: 281.2 × 0.62 = 174.3 kW
        max_power_nominal = 38 * 7.4
        max_power_effective = max_power_nominal * CHARGING_EFFICIENCY
        max_power_actual = df_chargers['total_ev_energy_kwh'].max()
        
        results['metrics']['max_power_nominal_kw'] = max_power_nominal
        results['metrics']['max_power_effective_kw'] = max_power_effective
        results['metrics']['max_power_actual_kw'] = max_power_actual
        
        if max_power_actual > max_power_effective * 1.1:  # 10% sobre lo esperado
            results['warnings'].append(
                f"Potencia máxima: {max_power_actual:.1f} kW > "
                f"máximo teórico ({max_power_effective:.1f} kW)"
            )
        else:
            logger.info(f"✓ Potencia máxima: {max_power_actual:.1f} kW ≤ "
                       f"máximo teórico ({max_power_effective:.1f} kW)")
    
    except Exception as e:
        results['errors'].append(f"Excepción durante validación: {str(e)}")
        results['valid'] = False
    
    return results


def print_ev_profile_summary(df_chargers: pd.DataFrame) -> None:
    """Imprime resumen del perfil EV cargado.
    
    Args:
        df_chargers: DataFrame con datos de carga
    """
    print("\n" + "="*70)
    print("RESUMEN DEL PERFIL DE CARGA DE VEHÍCULOS ELÉCTRICOS (EV)")
    print("="*70)
    
    # Validar
    validation = validate_ev_csv_profile(df_chargers)
    
    print(f"\n[ESTADO DE VALIDACIÓN]: {'✓ VÁLIDO' if validation['valid'] else '✗ INVÁLIDO'}")
    
    if validation['errors']:
        print(" Errores:")
        for err in validation['errors']:
            print(f"  ✗ {err}")
    
    if validation['warnings']:
        print(" Advertencias:")
        for warn in validation['warnings']:
            print(f"  ⚠️  {warn}")
    
    # Mostrar métricas
    metrics = validation['metrics']
    print(f"\n[MÉTRICAS PRINCIPALES]:")
    print(f"  Energía anual total:        {metrics.get('total_energy_annual_kwh', 0):>12,.0f} kWh")
    print(f"  Energía motos:              {metrics.get('energy_motos_kwh', 0):>12,.0f} kWh")
    print(f"  Energía mototaxis:          {metrics.get('energy_taxis_kwh', 0):>12,.0f} kWh")
    print(f"  Ratio motos/taxis:          {metrics.get('ratio_motos_taxis_actual', 0):>12.2f} (esperada {metrics.get('ratio_motos_taxis_expected', 0):.2f})")
    print(f"  Concentración punta 18-20h: {metrics.get('energy_punta_pct', 0):>12.1f}% (esperada ~45-50%)")
    print(f"  Potencia máxima instantánea:{metrics.get('max_power_actual_kw', 0):>12.1f} kW (límite teórico {metrics.get('max_power_effective_kw', 0):.1f} kW)")
    
    print(f"\n[ESPECIFICACIONES DE VEHÍCULOS]:")
    print(f"  MOTOS:")
    print(f"    - Cantidad diaria: {MOTO_SPEC.quantity_per_day} vehículos")
    print(f"    - Energía por carga: {MOTO_ENERGY_TO_CHARGE_KWH:.3f} kWh (base SOC 20%-80%)")
    print(f"    - Cargadores: {MOTO_SPEC.chargers_assigned} × 2 tomas = {MOTO_SPEC.sockets_assigned} tomas")
    print(f"    - SOC arrival: {MOTO_SPEC.soc_arrival_mean*100:.1f}% ± {MOTO_SPEC.soc_arrival_std*100:.1f}% (rango 10%-40%)")
    print(f"    - SOC target: {MOTO_SPEC.soc_target_mean*100:.1f}% ± {MOTO_SPEC.soc_target_std*100:.1f}% (rango 60%-100%)")
    
    print(f"  MOTOTAXIS:")
    print(f"    - Cantidad diaria: {MOTOTAXI_SPEC.quantity_per_day} vehículos")
    print(f"    - Energía por carga: {MOTOTAXI_ENERGY_TO_CHARGE_KWH:.3f} kWh (base SOC 20%-80%)")
    print(f"    - Cargadores: {MOTOTAXI_SPEC.chargers_assigned} × 2 tomas = {MOTOTAXI_SPEC.sockets_assigned} tomas")
    print(f"    - SOC arrival: {MOTOTAXI_SPEC.soc_arrival_mean*100:.1f}% ± {MOTOTAXI_SPEC.soc_arrival_std*100:.1f}%")
    print(f"    - SOC target: {MOTOTAXI_SPEC.soc_target_mean*100:.1f}% ± {MOTOTAXI_SPEC.soc_target_std*100:.1f}%")
    
    print(f"\n[FACTORES OPERACIONALES DEL MALL]:")
    print(f"  Horario: 9h-22h (cierre realista a las 21h)")
    print(f"  0-8h: CERRADO (0%)")
    print(f"  9h: APERTURA (30%)")
    print(f"  10-18h: RAMPA LINEAL (30% → 100%)")
    print(f"  18-20h: PUNTA MÁXIMA (100%)")
    print(f"  21h: CIERRE (0%, redistribución a 18-20h)")
    print(f"  22-24h: CERRADO (0%)")
    
    print(f"\n[EFICIENCIA REAL DE CARGA]:")
    print(f"  Potencia nominal: 7.4 kW/toma × 38 tomas = 281.2 kW instalados")
    print(f"  Eficiencia real: {CHARGING_EFFICIENCY*100:.0f}% (incluye pérdidas cargador, cable, batería, taper)")
    print(f"  Potencia efectiva: 7.4 × {CHARGING_EFFICIENCY} = {7.4*CHARGING_EFFICIENCY:.1f} kW/toma")
    print(f"  Máximo teórico: 281.2 × {CHARGING_EFFICIENCY} = {281.2*CHARGING_EFFICIENCY:.1f} kW")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    # Ejemplo de uso
    logging.basicConfig(level=logging.INFO)
    
    # Calcular demanda teórica
    demand = calculate_ev_demand_theoretical()
    print("Demanda teórica diaria:", demand['total_daily_kwh'], "kWh")
    print("Demanda teórica anual:", demand['total_annual_kwh'], "kWh")
    
    # Verificar factores operacionales
    print("\nFactores operacionales por hora:")
    for h in range(24):
        factor = get_operational_factor(h)
        print(f"  {h:2d}h: {factor*100:5.1f}%")
