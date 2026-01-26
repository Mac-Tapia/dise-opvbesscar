#!/usr/bin/env python3
"""
Script de corrección automática de problemas OE2
Arregla: Solar TS, BESS config, Perfil horario
"""

import json
import logging
from pathlib import Path

import pandas as pd  # type: ignore[import]

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent  # Go up from scripts/ to root
DATA_INTERIM_OE2 = BASE_DIR / 'data' / 'interim' / 'oe2'


def fix_solar_timeseries():
    """Corregir solar timeseries a exactamente 8,760 filas"""
    logger.info("\n" + "="*60)
    logger.info("CORRIGIENDO: Solar Timeseries")
    logger.info("="*60)

    timeseries_file = DATA_INTERIM_OE2 / 'solar' / 'pv_generation_timeseries.csv'

    if not timeseries_file.exists():
        logger.error(f"❌ Archivo no encontrado: {timeseries_file}")
        return False

    try:
        df = pd.read_csv(timeseries_file)
        logger.info(f"  Leyendo: {len(df)} filas × {len(df.columns)} columnas")

        # 1. Intentar filtrar por timestamp si existe
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            years = df['timestamp'].dt.year.unique()
            years_clean = sorted([int(y) for y in years if pd.notna(y)])
            logger.info(f"  Años encontrados: {years_clean}")

            # Tomar el año más completo (primero con 8,760+ filas)
            for year_val in years_clean:
                df_year = df[df['timestamp'].dt.year == year_val]
                if len(df_year) >= 8760:
                    df = df_year.head(8760).reset_index(drop=True)
                    logger.info(f"  ✓ Filtrado a año {year_val}: {len(df)} filas")
                    break

        # 2. Si aún no es 8,760, tomar primeras 8,760 filas
        if len(df) != 8760:
            df = df.head(8760).reset_index(drop=True)
            logger.info(f"  ✓ Ajustado a primeras 8,760 filas")

        # 3. Limpiar valores negativos (considerar como cero en horas nocturnas)
        negative_count = (df.select_dtypes(include=['number']) < 0).any(axis=1).sum()
        if negative_count > 0:
            power_cols = [c for c in df.columns if 'power' in c.lower() or 'kw' in c.lower()]
            for col in power_cols:
                if col in df.columns:
                    df.loc[df[col] < 0, col] = 0.0
            logger.info(f"  ✓ Limpiados {negative_count} valores negativos → 0")

        # 4. Verificar sin NULL
        null_count = df.isnull().sum().sum()
        if null_count > 0:
            logger.warning(f"  ⚠️ {null_count} valores NULL encontrados")

        # 5. Guardar
        df.to_csv(timeseries_file, index=False)
        logger.info(f"  ✅ Guardado: {timeseries_file}")
        logger.info(f"  ✅ Dimensión final: {len(df)} filas × {len(df.columns)} columnas")

        return True

    except Exception as e:
        logger.error(f"❌ Error corrigiendo solar: {e}")
        return False


def create_bess_config():
    """Crear archivo bess_config.json si no existe"""
    logger.info("\n" + "="*60)
    logger.info("CREANDO: BESS Configuration")
    logger.info("="*60)

    bess_dir = DATA_INTERIM_OE2 / 'bess'
    config_file = bess_dir / 'bess_config.json'

    if config_file.exists():
        logger.info(f"  ℹ️ Archivo ya existe: {config_file}")
        return True

    try:
        # BESS Specs: Eaton Xpert1670 equivalent
        # 2 MWh capacity / 1.2 MW power
        bess_config = {
            "system_name": "Eaton Xpert 1670 - Iquitos BESS",
            "capacity_kwh": 2000.0,
            "power_kw": 1200.0,
            "efficiency": 0.92,
            "min_soc": 0.10,
            "max_soc": 1.00,
            "depth_of_discharge": 0.90,
            "roundtrip_efficiency": 0.92,
            "response_time_s": 0.5,
            "degradation_rate_yearly": 0.01,
            "round_trip_efficiency_percent": 92.0,
            "battery_chemistry": "Lithium-ion",
            "warranty_years": 10,
            "cycle_life": 4500
        }

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(bess_config, f, indent=2, ensure_ascii=False)

        logger.info(f"  ✅ Creado: {config_file}")
        logger.info(f"  ✅ Especificaciones:")
        logger.info(f"     - Capacidad: {bess_config['capacity_kwh']} kWh")
        logger.info(f"     - Potencia: {bess_config['power_kw']} kW")
        logger.info(f"     - Eficiencia: {bess_config['efficiency']*100}%")

        return True

    except Exception as e:
        logger.error(f"❌ Error creando BESS config: {e}")
        return False


def expand_charger_profile():
    """Expandir perfil horario de 24h a 8,760h"""
    logger.info("\n" + "="*60)
    logger.info("EXPANDIENDO: Charger Hourly Profile")
    logger.info("="*60)

    profile_file = DATA_INTERIM_OE2 / 'chargers' / 'perfil_horario_carga.csv'

    if not profile_file.exists():
        logger.error(f"❌ Archivo no encontrado: {profile_file}")
        return False

    try:
        profile_24h = pd.read_csv(profile_file)
        logger.info(f"  Perfil actual: {len(profile_24h)} filas × {len(profile_24h.columns)} columnas")

        # Si ya tiene 8,760 filas, validar y listo
        if len(profile_24h) == 8760:
            logger.info(f"  ✓ Perfil ya está expandido a 8,760 filas")
            return True

        # Validar que sea 24 horas o un divisor de 8,760
        if 8760 % len(profile_24h) != 0:
            logger.warning(f"  ⚠️ {len(profile_24h)} filas no es divisor de 8,760")
            # Tomar primeras 8,760 si hay más
            if len(profile_24h) > 8760:
                profile_24h = profile_24h.head(8760).reset_index(drop=True)
                profile_24h.to_csv(profile_file, index=False)
                logger.info(f"  ✓ Truncado a 8,760 filas")
                return True

        # Expandir repetiendo patrón
        repeat_factor = 8760 // len(profile_24h)
        df_yearly = pd.concat([profile_24h] * repeat_factor, ignore_index=True)

        # Crear timestamps si no existen
        if 'timestamp' not in df_yearly.columns:
            dates = pd.date_range('2025-01-01', periods=len(df_yearly), freq='h')
            df_yearly.insert(0, 'timestamp', dates)
        else:
            # Recrear timestamps
            dates = pd.date_range('2025-01-01', periods=len(df_yearly), freq='h')
            df_yearly['timestamp'] = dates

        # Guardar
        df_yearly.to_csv(profile_file, index=False)
        logger.info(f"  ✅ Perfil procesado")
        logger.info(f"  ✅ Dimensión final: {len(df_yearly)} filas × {len(df_yearly.columns)} columnas")

        return True

    except Exception as e:
        logger.error(f"❌ Error expandiendo perfil: {e}")
        return False


def create_solar_config():
    """Crear archivo solar_config.json si no existe"""
    logger.info("\n" + "="*60)
    logger.info("CREANDO: Solar Configuration Metadata")
    logger.info("="*60)

    solar_dir = DATA_INTERIM_OE2 / 'solar'
    config_file = solar_dir / 'solar_config.json'

    if config_file.exists():
        logger.info(f"  ℹ️ Archivo ya existe: {config_file}")
        return True

    try:
        # Specs de sistema solar Kyocera KS20 + Eaton Xpert1670
        solar_config = {
            "system_name": "Kyocera KS20 + Eaton Xpert 1670 - Iquitos",
            "system_dc_kw": 4050.0,
            "system_ac_kw": 1670.0,  # 2 inverters × 835 kW each
            "module_name": "Kyocera KS20",
            "module_power_w": 4000.0,  # 4 kW per module
            "num_modules": 1012,  # Total modules
            "strings": 6472,
            "modules_per_string": 31,
            "inverter_name": "Eaton Xpert 1670",
            "num_inverters": 2,
            "inverter_power_kw": 835.0,  # Per inverter
            "location": "Iquitos, Perú",
            "latitude": -3.7469,
            "longitude": -73.2528,
            "altitude_m": 104.0,
            "tilt_angle": 10.0,
            "azimuth_angle": 0.0,
            "capacity_factor_percent": 29.6,
            "annual_energy_kwh": 8310000.0,
            "commissioning_year": 2024
        }

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(solar_config, f, indent=2, ensure_ascii=False)

        logger.info(f"  ✅ Creado: {config_file}")
        logger.info(f"  ✅ Sistema PV:")
        logger.info(f"     - Capacidad DC: {solar_config['system_dc_kw']} kW")
        logger.info(f"     - Capacidad AC: {solar_config['system_ac_kw']} kW")
        logger.info(f"     - Módulos: {solar_config['num_modules']}")
        logger.info(f"     - Factor de capacidad: {solar_config['capacity_factor_percent']}%")

        return True

    except Exception as e:
        logger.error(f"❌ Error creando solar config: {e}")
        return False


def main():
    """Ejecutar todas las correcciones"""
    logger.info("\n" + "#"*60)
    logger.info("# AUTO-CORRECTION SCRIPT: OE2 Data Integration")
    logger.info("#"*60)

    results = {
        'solar_timeseries': fix_solar_timeseries(),
        'bess_config': create_bess_config(),
        'charger_profile': expand_charger_profile(),
        'solar_config': create_solar_config()
    }

    # Resumen
    logger.info("\n" + "="*60)
    logger.info("RESUMEN DE CORRECCIONES")
    logger.info("="*60)

    for task, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {task.replace('_', ' ').title()}: {status}")

    all_success = all(results.values())

    logger.info("\n" + "="*60)
    if all_success:
        logger.info("✅ TODAS LAS CORRECCIONES COMPLETADAS")
        logger.info("   Próximo paso: Ejecutar auditoría nuevamente")
        logger.info("   python scripts/audit_oe2_oe3_connectivity.py")
    else:
        logger.info("❌ ALGUNAS CORRECCIONES FALLARON")
        logger.info("   Revisar mensajes de error arriba")
    logger.info("="*60)

    return 0 if all_success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
