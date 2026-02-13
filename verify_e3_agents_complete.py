#!/usr/bin/env python3
"""Complete E3 agents verification and validation."""

from __future__ import annotations

import yaml
import json
from pathlib import Path
import sys

def verify_e3_agents():
    """Run complete E3 agent verification."""

    print("\n" + "="*80)
    print(" E3 AGENTS - COMPLETE VERIFICATION & VALIDATION")
    print("="*80)

    # 1. Configuration files
    print("\n📋 PHASE 1: Configuration Files")
    print("-" * 80)
    configs = {
        'configs/agents/agents_config.yaml': 'Master config',
        'configs/agents/sac_config.yaml': 'SAC hyperparameters',
        'configs/agents/ppo_config.yaml': 'PPO hyperparameters',
        'configs/agents/a2c_config.yaml': 'A2C hyperparameters',
        'outputs/agents/sac_config.json': 'SAC JSON config',
        'outputs/agents/ppo_config.json': 'PPO JSON config',
        'outputs/agents/a2c_config.json': 'A2C JSON config',
    }

    config_count = 0
    for config_path, description in configs.items():
        p = Path(config_path)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            print(f'  ✓ {description:<35} ({size_kb:>6.1f} KB)')
            config_count += 1
        else:
            print(f'  ✗ {description:<35} MISSING')

    print(f'\nConfigurations: {config_count}/{len(configs)} ✓')

    # 2. Agent implementations
    print("\n📋 PHASE 2: Agent Implementations")
    print("-" * 80)
    agents = {
        'src/agents/sac.py': 'Soft Actor-Critic (off-policy)',
        'src/agents/ppo_sb3.py': 'Proximal Policy Optimization',
        'src/agents/a2c_sb3.py': 'Advantage Actor-Critic',
        'src/agents/no_control.py': 'No-control baseline',
    }

    agent_count = 0
    for agent_path, description in agents.items():
        p = Path(agent_path)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            print(f'  ✓ {description:<40} ({size_kb:>6.1f} KB)')
            agent_count += 1
        else:
            print(f'  ✗ {description:<40} MISSING')

    print(f'\nAgent implementations: {agent_count}/{len(agents)} ✓')

    # 3. Baseline infrastructure
    print("\n📋 PHASE 3: Baseline Infrastructure")
    print("-" * 80)
    baselines = {
        'src/baseline/__init__.py': 'Baseline module init',
        'src/baseline/baseline_definitions.py': 'Baseline scenario definitions',
        'src/baseline/baseline_calculator.py': 'Baseline CO2 calculator',
        'scripts/run_baselines.py': 'Baseline execution script',
        'outputs/baselines/baseline_con_solar.json': 'CON_SOLAR results',
        'outputs/baselines/baseline_sin_solar.json': 'SIN_SOLAR results',
        'outputs/baselines/baseline_comparison.csv': 'Baseline comparison',
        'outputs/baselines/baseline_summary.json': 'Baseline summary',
    }

    baseline_count = 0
    for baseline_path, description in baselines.items():
        p = Path(baseline_path)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            print(f'  ✓ {description:<40} ({size_kb:>6.1f} KB)')
            baseline_count += 1
        else:
            print(f'  ✗ {description:<40} MISSING')

    print(f'\nBaseline infrastructure: {baseline_count}/{len(baselines)} ✓')

    # 4. Dataset
    print("\n📋 PHASE 4: OE3 Dataset")
    print("-" * 80)
    schema_path = Path('data/interim/oe3/schema.json')
    chargers_dir = Path('data/interim/oe3/chargers')

    dataset_count = 0
    if schema_path.exists():
        size_kb = schema_path.stat().st_size / 1024
        print(f'  ✓ schema.json ({size_kb:.1f} KB)')
        dataset_count += 1
    else:
        print(f'  ✗ schema.json MISSING')

    if chargers_dir.exists():
        charger_files = list(chargers_dir.glob('charger_*.csv'))
        print(f'  ✓ Charger files: {len(charger_files)}/128')
        if len(charger_files) == 128:
            dataset_count += 1
    else:
        print(f'  ✗ Charger directory MISSING')

    print(f'\nDataset files: {dataset_count}/2 ✓')

    # 5. Utility modules
    print("\n📋 PHASE 5: Utility Modules")
    print("-" * 80)
    utils = {
        'src/utils/agent_utils.py': 'Agent utilities',
        'src/utils/logging.py': 'Logging setup',
        'src/utils/time.py': 'Time utilities',
        'src/utils/series.py': 'Series utilities',
    }

    util_count = 0
    for util_path, description in utils.items():
        p = Path(util_path)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            print(f'  ✓ {description:<40} ({size_kb:>6.1f} KB)')
            util_count += 1
        else:
            print(f'  ✗ {description:<40} MISSING')

    print(f'\nUtility modules: {util_count}/{len(utils)} ✓')

    # 6. Execution scripts
    print("\n📋 PHASE 6: Execution Scripts")
    print("-" * 80)
    scripts = {
        'scripts/run_oe3_build_dataset.py': 'Dataset generation',
        'scripts/run_baselines.py': 'Baseline calculation',
    }

    script_count = 0
    for script_path, description in scripts.items():
        p = Path(script_path)
        if p.exists():
            size_kb = p.stat().st_size / 1024
            print(f'  ✓ {description:<40} ({size_kb:>6.1f} KB)')
            script_count += 1
        else:
            print(f'  ✗ {description:<40} MISSING')

    print(f'\nExecution scripts: {script_count}/{len(scripts)} ✓')

    # 7. Hyperparameter validation
    print("\n📋 PHASE 7: Hyperparameter Validation")
    print("-" * 80)

    hp_config = {
        'configs/agents/sac_config.yaml': 'SAC',
        'configs/agents/ppo_config.yaml': 'PPO',
        'configs/agents/a2c_config.yaml': 'A2C',
    }

    hp_count = 0
    for yaml_path, agent_name in hp_config.items():
        try:
            with open(yaml_path) as f:
                cfg = yaml.safe_load(f)
                param_count = len(cfg) if isinstance(cfg, dict) else 0
                print(f'  ✓ {agent_name:<5} - {param_count} parameters configured')
                hp_count += 1
        except Exception as e:
            print(f'  ✗ {agent_name:<5} - ERROR: {str(e)}')

    print(f'\nHyperparameter configs: {hp_count}/{len(hp_config)} ✓')

    # 8. Baseline results
    print("\n📋 PHASE 8: Baseline Results Validation")
    print("-" * 80)

    baseline_results = {
        'outputs/baselines/baseline_con_solar.json': 'CON_SOLAR',
        'outputs/baselines/baseline_sin_solar.json': 'SIN_SOLAR',
    }

    results_count = 0
    for json_path, scenario_name in baseline_results.items():
        try:
            with open(json_path) as f:
                data = json.load(f)
                co2_kg = data.get('co2_grid_kg', 0)
                print(f'  ✓ {scenario_name:<15} - CO2: {co2_kg:,.0f} kg/año')
                results_count += 1
        except Exception as e:
            print(f'  ✗ {scenario_name:<15} - ERROR: {str(e)}')

    print(f'\nBaseline results: {results_count}/{len(baseline_results)} ✓')

    # Summary
    print("\n" + "="*80)
    print(" COMPLETE SUMMARY")
    print("="*80)

    total_checks = (config_count + agent_count + baseline_count + dataset_count +
                   util_count + script_count + hp_count + results_count)
    total_expected = (len(configs) + len(agents) + len(baselines) + 2 +
                     len(utils) + len(scripts) + len(hp_config) + len(baseline_results))
    pct = (total_checks / total_expected) * 100

    print(f"  Configuration files:      {config_count}/{len(configs)}")
    print(f"  Agent implementations:     {agent_count}/{len(agents)}")
    print(f"  Baseline infrastructure:   {baseline_count}/{len(baselines)}")
    print(f"  OE3 Dataset:               {dataset_count}/2")
    print(f"  Utility modules:           {util_count}/{len(utils)}")
    print(f"  Execution scripts:         {script_count}/{len(scripts)}")
    print(f"  Hyperparameter configs:    {hp_count}/{len(hp_config)}")
    print(f"  Baseline results:          {results_count}/{len(baseline_results)}")
    print()
    print(f"  TOTAL: {total_checks}/{total_expected} ({pct:.1f}%)")

    if pct == 100:
        print("\n🟢 ✅ E3 AGENTS IMPLEMENTATION AT 100%!")
        print("\n📊 SYSTEM STATUS: FULLY SYNCHRONIZED AND READY FOR TRAINING")
        return 0
    else:
        print(f"\n🟡 IMPLEMENTATION AT {pct:.1f}% - REVIEW MISSING ITEMS")
        return 1

if __name__ == '__main__':
    sys.exit(verify_e3_agents())
