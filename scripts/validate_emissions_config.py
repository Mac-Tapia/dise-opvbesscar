"""
Script de validación de configuración de emisiones.

Verifica que todos los archivos YAML, JSON y constantes en código estén sincronizados.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Agregar src al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from iquitos_citylearn.config import load_config
from iquitos_citylearn.oe3.emissions_constants import EMISSIONS, validate_config_consistency


def main():
    print("=" * 80)
    print("VALIDACIÓN DE CONFIGURACIÓN DE EMISIONES")
    print("=" * 80)
    print()

    # Cargar configuración
    config_path = project_root / "configs" / "default.yaml"
    print(f"Cargando configuración: {config_path}")
    cfg = load_config(config_path)
    print("✓ Configuración cargada correctamente")
    print()

    # Validar consistencia
    print("Validando consistencia de constantes...")
    errors = validate_config_consistency(cfg)

    if errors:
        print("❌ ERRORES ENCONTRADOS:")
        for error in errors:
            print(f"  - {error}")
        print()
        print("Por favor, sincroniza los valores en configs/default.yaml")
        return 1

    print("✓ Todas las constantes están sincronizadas")
    print()

    # Mostrar valores actuales
    print("VALORES ACTUALES:")
    print("-" * 80)
    print(f"Grid CO₂ factor:        {EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH} kg CO₂/kWh")
    print(f"EV eficiencia:          {EMISSIONS.EV_KM_PER_KWH} km/kWh")
    print(f"ICE eficiencia:         {EMISSIONS.ICE_KM_PER_GALLON} km/galón")
    print(f"ICE emisiones:          {EMISSIONS.ICE_KGCO2_PER_GALLON} kg CO₂/galón")
    print()
    print("CÁLCULOS DERIVADOS:")
    print("-" * 80)
    print(f"ICE CO₂ por km:         {EMISSIONS.ice_kgco2_per_km:.4f} kg CO₂/km")
    print(f"EV CO₂ por km (grid):   {EMISSIONS.ev_kgco2_per_km_grid:.4f} kg CO₂/km")
    print(f"Reducción CO₂ por km:   {EMISSIONS.co2_reduction_per_km:.4f} kg CO₂/km")
    print()

    # Ejemplo de cálculo
    print("EJEMPLO DE CÁLCULO:")
    print("-" * 80)
    ev_kwh_ejemplo = 100.0  # 100 kWh cargados
    km_recorridos = ev_kwh_ejemplo * EMISSIONS.EV_KM_PER_KWH
    gallons_evitados = km_recorridos / EMISSIONS.ICE_KM_PER_GALLON
    co2_combustion = gallons_evitados * EMISSIONS.ICE_KGCO2_PER_GALLON
    co2_grid = ev_kwh_ejemplo * EMISSIONS.GRID_CO2_FACTOR_KG_PER_KWH
    co2_neto_evitado = co2_combustion - co2_grid

    print(f"Si se cargan {ev_kwh_ejemplo} kWh en vehículos eléctricos:")
    print(f"  - km recorridos:           {km_recorridos:.1f} km")
    print(f"  - Gasolina evitada:        {gallons_evitados:.2f} galones")
    print(f"  - CO₂ combustión evitado:  {co2_combustion:.2f} kg")
    print(f"  - CO₂ grid importado:      {co2_grid:.2f} kg")
    print(f"  - CO₂ NETO evitado:        {co2_neto_evitado:.2f} kg")
    print()

    print("=" * 80)
    print("✓ VALIDACIÓN EXITOSA - Todos los archivos están sincronizados")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
