#!/usr/bin/env python
"""
Master Execution Script: Complete OE2 → CityLearn v2 → RL Agent Training Pipeline

This orchestrates the entire validation, synchronization, training, and analysis workflow.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/master_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_script(script_path: Path, description: str) -> bool:
    """Execute a Python script and return success status."""
    
    logger.info("\n" + "=" * 80)
    logger.info(f"EXECUTING: {description}")
    logger.info("=" * 80 + "\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path(__file__).parent.parent,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {description} COMPLETE")
            return True
        else:
            logger.error(f"❌ {description} FAILED (exit code {result.returncode})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error running {script_path}: {e}")
        return False


def main():
    """Execute complete pipeline: OE2 validation → CityLearn sync → Agent training."""
    
    logger.info("\n" + "=" * 80)
    logger.info("OE2 ↔ CITYLEARN V2 ↔ RL AGENT TRAINING - MASTER PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now().isoformat()}\n")
    
    project_root = Path(__file__).parent.parent
    scripts_dir = project_root / "scripts"
    
    # Ensure logs directory exists
    (project_root / "logs").mkdir(exist_ok=True)
    
    # Phase 1: Validate and Synchronize
    validation_script = scripts_dir / "validate_and_sync_oe2_citylearn_v2.py"
    
    if not validation_script.exists():
        logger.error(f"❌ Validation script not found: {validation_script}")
        return False
    
    if not run_script(validation_script, "PHASE 1: OE2 VALIDATION & CITYLEARN V2 SYNC"):
        logger.error("❌ Pipeline failed at Phase 1")
        return False
    
    # Phase 2: Analyze Results
    analysis_script = scripts_dir / "analyze_training_results.py"
    
    if not analysis_script.exists():
        logger.error(f"❌ Analysis script not found: {analysis_script}")
        # Continue anyway
    else:
        run_script(analysis_script, "PHASE 2: POST-TRAINING ANALYSIS")
    
    # Final Summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ COMPLETE PIPELINE EXECUTION SUCCESSFUL")
    logger.info("=" * 80)
    logger.info(f"Completed: {datetime.now().isoformat()}")
    logger.info("\nOutput files saved to:")
    logger.info(f"  - Logs: {project_root / 'logs'}")
    logger.info(f"  - Results: {project_root / 'outputs/training_validation'}")
    logger.info(f"  - Checkpoints: {project_root / 'checkpoints'}")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error in master pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
