from __future__ import annotations

import argparse
import logging

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.validate_citylearn_build import validate_citylearn_dataset
from scripts._common import load_all

logger = logging.getLogger(__name__)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--skip-validation", action="store_true", help="Skip post-build validation")
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    logger.info("")
    logger.info("="*80)
    logger.info("STEP 1: BUILD CITYLEARN DATASET")
    logger.info("="*80)
    build_citylearn_dataset(
        cfg=cfg,
        _raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    logger.info("✓ Dataset construction completed")

    # POST-BUILD VALIDATION
    if not args.skip_validation:
        logger.info("")
        logger.info("="*80)
        logger.info("STEP 2: POST-BUILD VALIDATION")
        logger.info("="*80)
        validation_passed = validate_citylearn_dataset(rp.processed_dir)

        if validation_passed:
            logger.info("")
            logger.info("✅ ALL VALIDATIONS PASSED - Dataset ready for training")
            logger.info("")
        else:
            logger.error("")
            logger.error("❌ VALIDATION FAILED - Review errors above")
            logger.error("Use --skip-validation to bypass checks (NOT recommended)")
            logger.error("")
            raise RuntimeError("Dataset validation failed")
    else:
        logger.warning("⚠️ Post-build validation SKIPPED (--skip-validation flag)")
        logger.warning("   Recommended to validate dataset before training")

if __name__ == "__main__":
    main()
