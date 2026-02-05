#!/usr/bin/env python3
"""Quick import validation script."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd()))

print("\n" + "="*80)
print("🔍 IMPORT VALIDATION TEST")
print("="*80 + "\n")

test_results = []

# Test 1: Progress module
try:
    from src.citylearnv2.progress import append_progress_row
    print("✅ PASS: from src.citylearnv2.progress import append_progress_row")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.citylearnv2.progress import append_progress_row - {e}")
    test_results.append(False)

# Test 2: Metrics module
try:
    from src.citylearnv2.progress.metrics_extractor import EpisodeMetricsAccumulator
    print("✅ PASS: from src.citylearnv2.progress.metrics_extractor import EpisodeMetricsAccumulator")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.citylearnv2.progress.metrics_extractor import EpisodeMetricsAccumulator - {e}")
    test_results.append(False)

# Test 3: Rewards module - create_iquitos_reward_weights
try:
    from src.rewards.rewards import create_iquitos_reward_weights
    print("✅ PASS: from src.rewards.rewards import create_iquitos_reward_weights")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.rewards.rewards import create_iquitos_reward_weights - {e}")
    test_results.append(False)

# Test 4: SAC agent
try:
    from src.agents.sac import SACAgent
    print("✅ PASS: from src.agents.sac import SACAgent")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.agents.sac import SACAgent - {e}")
    test_results.append(False)

# Test 5: PPO agent
try:
    from src.agents.ppo_sb3 import PPOAgent
    print("✅ PASS: from src.agents.ppo_sb3 import PPOAgent")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.agents.ppo_sb3 import PPOAgent - {e}")
    test_results.append(False)

# Test 6: A2C agent
try:
    from src.agents.a2c_sb3 import A2CAgent
    print("✅ PASS: from src.agents.a2c_sb3 import A2CAgent")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.agents.a2c_sb3 import A2CAgent - {e}")
    test_results.append(False)

# Test 7: Dataset builder
try:
    from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset
    print("✅ PASS: from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset")
    test_results.append(True)
except ImportError as e:
    print(f"❌ FAIL: from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset - {e}")
    test_results.append(False)

# Test 8: Verify function is callable
try:
    from src.rewards.rewards import create_iquitos_reward_weights
    weights = create_iquitos_reward_weights(priority="co2_focus")
    print(f"✅ PASS: create_iquitos_reward_weights('co2_focus') returns {type(weights).__name__}")
    test_results.append(True)
except Exception as e:
    print(f"❌ FAIL: create_iquitos_reward_weights execution - {e}")
    test_results.append(False)

# Summary
print("\n" + "="*80)
passed = sum(test_results)
total = len(test_results)
print(f"SUMMARY: {passed}/{total} tests passed")

if passed == total:
    print("🟢 ALL IMPORTS WORKING CORRECTLY!")
    sys.exit(0)
else:
    print(f"🔴 {total - passed} import(s) failed")
    sys.exit(1)
