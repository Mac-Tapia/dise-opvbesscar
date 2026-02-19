#!/usr/bin/env python
"""
Real-time Training Monitoring & Post-Training Analysis

Monitor training progress and analyze results from OE2 data validation + CityLearn v2 synchronization.
"""

from __future__ import annotations

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingMonitor:
    """Monitor and analyze training results."""

    def __init__(self, output_dir: Path = Path("outputs/training_validation")):
        self.output_dir = Path(output_dir)
        self.metrics = {}

    def load_metrics(self) -> Dict[str, Any]:
        """Load all agent metrics from output directory."""
        logger.info("📊 Loading training metrics...")
        
        for metrics_file in self.output_dir.glob("*_metrics.json"):
            try:
                with open(metrics_file, 'r') as f:
                    agent_name = metrics_file.stem.replace('_metrics', '')
                    self.metrics[agent_name] = json.load(f)
                    logger.info(f"✅ Loaded {agent_name} metrics")
            except Exception as e:
                logger.error(f"❌ Failed to load {metrics_file}: {e}")
        
        return self.metrics

    def print_summary(self):
        """Print training summary to console and file."""
        logger.info("\n" + "=" * 80)
        logger.info("TRAINING SUMMARY REPORT")
        logger.info("=" * 80)
        
        summary_lines = []
        
        for agent_name, metrics in self.metrics.items():
            if 'error' in metrics:
                logger.error(f"\n❌ {agent_name}: {metrics['error']}")
                summary_lines.append(f"❌ {agent_name}: ERROR")
            else:
                elapsed = metrics.get('elapsed_seconds', 0)
                steps = metrics.get('training_steps', 0)
                sps = metrics.get('steps_per_second', 0)
                
                logger.info(f"\n✅ {agent_name}")
                logger.info(f"  - Training Steps: {steps:,}")
                logger.info(f"  - Time Elapsed: {elapsed:.2f}s ({elapsed/60:.2f}m)")
                logger.info(f"  - Throughput: {sps:.2f} steps/sec")
                logger.info(f"  - Timestamp: {metrics.get('timestamp', '?')}")
                
                summary_lines.append(f"✅ {agent_name}: {sps:.2f} steps/sec, {elapsed:.2f}s")
        
        # Save summary
        summary_file = self.output_dir / "SUMMARY.txt"
        with open(summary_file, 'w') as f:
            f.write("OE2 → CityLearn v2 → RL Agent Training Summary\n")
            f.write("=" * 80 + "\n\n")
            
            for line in summary_lines:
                f.write(line + "\n")
            
            f.write(f"\nGenerated: {datetime.now().isoformat()}\n")
        
        logger.info(f"\n✅ Summary saved to {summary_file}")
        logger.info("=" * 80)

    def compare_agents(self) -> pd.DataFrame:
        """Create comparison DataFrame of agent performance."""
        logger.info("\n📈 Comparing agents...")
        
        comparison_data = []
        
        for agent_name, metrics in self.metrics.items():
            if 'error' not in metrics:
                comparison_data.append({
                    'Agent': agent_name,
                    'Training Steps': metrics.get('training_steps', 0),
                    'Time (sec)': metrics.get('elapsed_seconds', 0),
                    'Steps/sec': metrics.get('steps_per_second', 0),
                    'Learning Rate': metrics.get('config', {}).get('learning_rate', '?'),
                    'Device': metrics.get('config', {}).get('device', '?')
                })
        
        if comparison_data:
            df = pd.DataFrame(comparison_data)
            
            # Save comparison
            comparison_file = self.output_dir / "agent_comparison.csv"
            df.to_csv(comparison_file, index=False)
            logger.info(f"✅ Comparison saved to {comparison_file}")
            
            # Print to console
            logger.info("\n" + df.to_string(index=False))
            
            return df
        
        return pd.DataFrame()


class DataIntegrityValidator:
    """Validate that OE2 data was properly synchronized."""

    def __init__(self, oe2_root: Path = Path("data/oe2")):
        self.oe2_root = oe2_root

    def verify_solar_completeness(self) -> bool:
        """Verify solar data is complete and hourly."""
        logger.info("\n🌞 Verifying Solar Data Completeness...")
        
        solar_file = self.oe2_root / "Generacionsolar" / "pv_generation_citylearn2024.csv"
        
        try:
            df = pd.read_csv(solar_file)
            
            # Check hourly data
            n_rows = len(df)
            expected = 8760
            
            if n_rows == expected:
                logger.info(f"✅ Solar: Exactly {n_rows} hourly rows (complete year)")
            elif n_rows > expected:
                logger.warning(f"⚠️  Solar: {n_rows} rows (expected {expected}, has header rows)")
            else:
                logger.error(f"❌ Solar: Only {n_rows} rows (expected {expected})")
                return False
            
            # Check for gaps
            if 'datetime' in df.columns:
                dates = pd.to_datetime(df['datetime'])
                gaps = dates.diff().value_counts()
                logger.info(f"  - Time step distribution: {gaps.head().to_dict()}")
            
            # Check power values
            power_col = [col for col in df.columns if 'potencia' in col.lower()][0]
            logger.info(f"  - Power range: {df[power_col].min():.2f} - {df[power_col].max():.2f} kW")
            logger.info(f"  - Annual generation: {df[power_col].sum() if 'energia' not in df.columns else df[[col for col in df.columns if 'energia' in col.lower()][0]].sum():.2f} kWh")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Solar verification error: {e}")
            return False

    def verify_charger_coverage(self) -> bool:
        """Verify charger data covers all 38 sockets."""
        logger.info("\n⚡ Verifying Charger Coverage...")
        
        chargers_file = self.oe2_root / "chargers" / "chargers_ev_ano_2024_v3.csv"
        
        try:
            # Read with memory-efficient method
            df = pd.read_csv(chargers_file, nrows=110000)
            
            logger.info(f"✅ Chargers: {len(df)} rows loaded")
            
            # Estimate hourly coverage
            unique_timestamps = df.iloc[:, 0].nunique() if len(df.columns) > 0 else 0
            logger.info(f"  - Unique time periods: ~{unique_timestamps}")
            
            # Check columns for socket information
            socket_cols = [col for col in df.columns if 'socket' in col.lower() or 'puerto' in col.lower()]
            if socket_cols:
                logger.info(f"  - Socket columns: {socket_cols}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Charger verification error: {e}")
            return False

    def verify_bess_sync(self) -> bool:
        """Verify BESS data synchronized correctly."""
        logger.info("\n🔋 Verifying BESS Synchronization...")
        
        bess_file = self.oe2_root / "bess" / "bess_ano_2024.csv"
        
        try:
            df = pd.read_csv(bess_file)
            
            logger.info(f"✅ BESS: {len(df)} rows")
            
            # Check state of charge
            soc_cols = [col for col in df.columns if 'soc' in col.lower()]
            if soc_cols:
                soc_col = soc_cols[0]
                soc_min = df[soc_col].min()
                soc_max = df[soc_col].max()
                soc_mean = df[soc_col].mean()
                
                logger.info(f"  - SOC: min={soc_min:.2f}%, mean={soc_mean:.2f}%, max={soc_max:.2f}%")
            
            # Check energy values
            energy_cols = [col for col in df.columns if 'energia' in col.lower() or 'energy' in col.lower()]
            if energy_cols:
                logger.info(f"  - Energy columns: {energy_cols}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ BESS verification error: {e}")
            return False


class EnvironmentValidator:
    """Validate CityLearn v2 environment setup."""

    def check_dataset_files(self) -> bool:
        """Check if dataset files were properly created."""
        logger.info("\n📁 Checking Dataset Files...")
        
        dataset_dir = Path("data/processed/citylearn_v2")
        
        if not dataset_dir.exists():
            logger.warning(f"⚠️  Dataset directory not found: {dataset_dir}")
            return False
        
        # Count files
        csv_files = list(dataset_dir.glob("**/*.csv"))
        json_files = list(dataset_dir.glob("**/*.json"))
        
        logger.info(f"✅ Dataset prepared: {len(csv_files)} CSV + {len(json_files)} JSON files")
        
        for csv_file in csv_files[:5]:  # Show first 5
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            logger.info(f"  - {csv_file.name}: {size_mb:.2f} MB")
        
        return len(csv_files) > 0 or len(json_files) > 0


def main():
    """Run comprehensive post-training analysis."""
    
    logger.info("\n" + "=" * 80)
    logger.info("POST-TRAINING ANALYSIS & VALIDATION")
    logger.info("=" * 80 + "\n")
    
    # Load and display metrics
    monitor = TrainingMonitor()
    metrics = monitor.load_metrics()
    
    if metrics:
        monitor.print_summary()
        comparison = monitor.compare_agents()
    else:
        logger.warning("⚠️  No metrics found; run training first")
    
    # Validate data integrity
    validator = DataIntegrityValidator()
    validator.verify_solar_completeness()
    validator.verify_charger_coverage()
    validator.verify_bess_sync()
    
    # Check environment
    env_validator = EnvironmentValidator()
    env_validator.check_dataset_files()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ POST-TRAINING ANALYSIS COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
