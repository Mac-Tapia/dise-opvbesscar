#!/usr/bin/env python
"""
Cleanup src/baseline/ folder - Remove v5.4 files and unused examples.

ANALYSIS RESULTS:
- src/baseline/ contains v5.4 code and legacy examples NOT used in current training
- No training scripts (train_sac.py, train_ppo.py, train_a2c.py) import from src/baseline/
- Actual no_control agent is in src/agents/no_control.py (used in src/agents/__init__.py)
- src/baseline/no_control.py is duplicate/legacy copy

ACTIONS:
✓ KEEP: __init__.py (namespace marker, safe to keep)
✓ KEEP: no_control.py (duplicate but safe; src/agents/no_control.py is the live version)

✗ DELETE: baseline_definitions_v54.py (v5.4 - outdated)
✗ DELETE: BASELINE_INTEGRATION_v54_README.md (v5.4 - outdated)
✗ DELETE: example_agent_training_with_baseline.py (unused example)
✗ DELETE: baseline_simulator.py (unused)
✗ DELETE: baseline_calculator_v2.py (unused)
✗ DELETE: citylearn_baseline_integration.py (unused)
✗ DELETE: agent_baseline_integration.py (unused)

TOTAL: Removing 7/9 files in src/baseline/
"""

from __future__ import annotations

import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

BASELINE_DIR = Path(__file__).parent.parent / "src" / "baseline"

# Files to delete (not referenced in current training)
DELETE_FILES = [
    "baseline_definitions_v54.py",
    "BASELINE_INTEGRATION_v54_README.md",
    "example_agent_training_with_baseline.py",
    "baseline_simulator.py",
    "baseline_calculator_v2.py",
    "citylearn_baseline_integration.py",
    "agent_baseline_integration.py",
]

# Files to keep
KEEP_FILES = [
    "__init__.py",
    "no_control.py",  # Duplicate but safe to keep for backward compatibility
]

def main():
    """Execute baseline cleanup."""
    
    print("=" * 70)
    print("BASELINE CLEANUP v5.5 - Remove unused v5.4 code and examples")
    print("=" * 70)
    print()
    
    # Verify dir exists
    if not BASELINE_DIR.exists():
        logger.error(f"❌ src/baseline/ not found at {BASELINE_DIR}")
        return False
    
    # List current files
    current_files = sorted([f.name for f in BASELINE_DIR.glob("*") if f.is_file()])
    logger.info(f"📁 Current files in src/baseline/: {len(current_files)}")
    for f in current_files:
        logger.info(f"   - {f}")
    print()
    
    # Show what will be deleted
    logger.info("🗑️  FILES TO DELETE (7 total):")
    for f in DELETE_FILES:
        file_path = BASELINE_DIR / f
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            logger.info(f"   ✗ {f} ({size_kb:.1f} KB)")
        else:
            logger.info(f"   ✗ {f} (not found)")
    print()
    
    logger.info("✓ FILES TO KEEP (2 total):")
    for f in KEEP_FILES:
        file_path = BASELINE_DIR / f
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            logger.info(f"   ✓ {f} ({size_kb:.1f} KB)")
        else:
            logger.info(f"   ✓ {f} (doesn't exist, will not create)")
    print()
    
    # Execute deletion
    logger.info("🔄 EXECUTING CLEANUP...")
    deleted = 0
    failed = 0
    
    for f in DELETE_FILES:
        file_path = BASELINE_DIR / f
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"   ✅ Deleted {f}")
                deleted += 1
            except Exception as e:
                logger.error(f"   ❌ Failed to delete {f}: {e}")
                failed += 1
        else:
            logger.info(f"   ⚠️  {f} not found (skipped)")
    
    print()
    logger.info("=" * 70)
    logger.info(f"✅ CLEANUP COMPLETE")
    logger.info(f"   • Deleted: {deleted}/{len(DELETE_FILES)}")
    if failed > 0:
        logger.warning(f"   • Failed: {failed}")
    logger.info(f"   • Kept: {len(KEEP_FILES)}")
    print()
    
    # List final files
    final_files = sorted([f.name for f in BASELINE_DIR.glob("*") if f.is_file()])
    logger.info(f"📊 Final state of src/baseline/: {len(final_files)} files")
    for f in final_files:
        logger.info(f"   - {f}")
    
    print()
    logger.info("=" * 70)
    logger.info("✨ src/baseline/ is now clean (v5.5 ready)")
    logger.info("=" * 70)
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
