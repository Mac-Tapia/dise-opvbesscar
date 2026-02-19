#!/usr/bin/env python
"""
Quick pre-flight verification before running the complete pipeline.
Checks data files, dependencies, and directory structure.
"""

from __future__ import annotations

import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def check_data_files() -> bool:
    """Verify all required OE2 data files exist."""
    logger.info("\n✓ CHECKING DATA FILES")
    logger.info("-" * 60)
    
    required_files = {
        'Solar': Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
        'Chargers': Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
        'BESS': Path('data/oe2/bess/bess_ano_2024.csv'),
    }
    
    all_exist = True
    
    for name, file_path in required_files.items():
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"  ✅ {name:12} {file_path.name:40} ({size_mb:.2f} MB)")
        else:
            logger.error(f"  ❌ {name:12} NOT FOUND: {file_path}")
            all_exist = False
    
    return all_exist


def check_script_files() -> bool:
    """Verify pipeline scripts exist."""
    logger.info("\n✓ CHECKING SCRIPTS")
    logger.info("-" * 60)
    
    required_scripts = {
        'Validation': Path('scripts/validate_and_sync_oe2_citylearn_v2.py'),
        'Analysis': Path('scripts/analyze_training_results.py'),
        'Master': Path('scripts/run_complete_pipeline.py'),
    }
    
    all_exist = True
    
    for name, script_path in required_scripts.items():
        if script_path.exists():
            size_kb = script_path.stat().st_size / 1024
            logger.info(f"  ✅ {name:12} {script_path.name:40} ({size_kb:.1f} KB)")
        else:
            logger.error(f"  ❌ {name:12} NOT FOUND: {script_path}")
            all_exist = False
    
    return all_exist


def check_directories() -> bool:
    """Verify required directories exist and are writable."""
    logger.info("\n✓ CHECKING DIRECTORIES")
    logger.info("-" * 60)
    
    required_dirs = {
        'Logs': Path('logs'),
        'Checkpoints': Path('checkpoints'),
        'Outputs': Path('outputs'),
        'Data': Path('data/oe2'),
    }
    
    all_writable = True
    
    for name, dir_path in required_dirs.items():
        if dir_path.exists():
            try:
                test_file = dir_path / '.write_test'
                test_file.touch()
                test_file.unlink()
                logger.info(f"  ✅ {name:12} {str(dir_path):40} (writable)")
            except:
                logger.warning(f"  ⚠️  {name:12} {str(dir_path):40} (read-only)")
                all_writable = False
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"  ✅ {name:12} {str(dir_path):40} (created)")
            except:
                logger.error(f"  ❌ {name:12} Cannot create {dir_path}")
                all_writable = False
    
    return all_writable


def check_dependencies() -> bool:
    """Verify key dependencies are installed."""
    logger.info("\n✓ CHECKING DEPENDENCIES")
    logger.info("-" * 60)
    
    dependencies = {
        'pandas': 'pd',
        'numpy': 'np',
        'stable_baselines3': 'sb3',
        'gymnasium': 'gym',
        'torch': 'torch (optional)'
    }
    
    all_available = True
    
    for package, import_name in dependencies.items():
        try:
            __import__(package)
            logger.info(f"  ✅ {package:20} installed")
        except ImportError:
            if 'optional' in import_name:
                logger.warning(f"  ⚠️  {package:20} not installed (optional)")
            else:
                logger.error(f"  ❌ {package:20} NOT INSTALLED")
                all_available = False
    
    return all_available


def check_solar_data_quality() -> bool:
    """Quick check of solar data structure."""
    logger.info("\n✓ CHECKING SOLAR DATA QUALITY")
    logger.info("-" * 60)
    
    try:
        import pandas as pd
        
        solar_file = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
        df = pd.read_csv(solar_file, nrows=100)
        
        n_rows = len(pd.read_csv(solar_file))
        n_cols = len(df.columns)
        
        logger.info(f"  ✅ Solar file readable: {n_rows} total rows, {n_cols} columns")
        
        # Check for datetime column
        has_datetime = 'datetime' in df.columns
        has_power = any('potencia' in col.lower() for col in df.columns)
        
        if has_datetime:
            logger.info(f"  ✅ Datetime column found")
        else:
            logger.warning(f"  ⚠️  Datetime column not found")
        
        if has_power:
            power_col = [col for col in df.columns if 'potencia' in col.lower()][0]
            logger.info(f"  ✅ Power column found: {power_col}")
        else:
            logger.warning(f"  ⚠️  Power column not found")
        
        # Check row count
        if n_rows >= 8760:
            logger.info(f"  ✅ Row count valid: {n_rows} rows (≥ 8,760)")
            return True
        else:
            logger.error(f"  ❌ Row count insufficient: {n_rows} rows (< 8,760)")
            return False
        
    except Exception as e:
        logger.error(f"  ❌ Solar data quality check failed: {e}")
        return False


def main() -> bool:
    """Run all pre-flight checks."""
    
    logger.info("\n" + "=" * 60)
    logger.info("PRE-FLIGHT VERIFICATION")
    logger.info("=" * 60)
    
    checks = {
        'Data Files': check_data_files(),
        'Scripts': check_script_files(),
        'Directories': check_directories(),
        'Dependencies': check_dependencies(),
        'Solar Quality': check_solar_data_quality(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status:8} {check_name}")
    
    all_pass = all(checks.values())
    
    logger.info("=" * 60)
    
    if all_pass:
        logger.info("\n✅ ALL CHECKS PASSED - Ready to run pipeline!")
        return True
    else:
        failed = [name for name, result in checks.items() if not result]
        logger.error(f"\n❌ FAILED CHECKS: {', '.join(failed)}")
        logger.error("Please fix issues above before running pipeline.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
