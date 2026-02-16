#!/usr/bin/env python3
"""
Verification script for training_results_archive.json
Ensures the archive file is valid and contains all expected training data.
"""

import json
import sys
from pathlib import Path


def verify_archive(archive_path: Path) -> tuple[bool, list[str]]:
    """
    Verify the training results archive file.
    
    Args:
        archive_path: Path to training_results_archive.json
        
    Returns:
        Tuple of (is_valid, list of issues/messages)
    """
    issues = []
    
    # Check file exists
    if not archive_path.exists():
        return False, [f"✗ Archive file not found: {archive_path}"]
    
    # Load JSON
    try:
        with open(archive_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"✗ Invalid JSON: {e}"]
    except Exception as e:
        return False, [f"✗ Error reading file: {e}"]
    
    # Validate structure
    required_sections = ['metadata', 'baseline', 'agents', 'comparison_summary']
    for section in required_sections:
        if section not in data:
            issues.append(f"✗ Missing section: {section}")
    
    # Validate metadata
    if 'metadata' in data:
        metadata = data['metadata']
        required_meta = ['project', 'timestamp_generated', 'total_agents_trained', 
                        'all_trainings_completed', 'archive_version']
        for key in required_meta:
            if key not in metadata:
                issues.append(f"✗ Missing metadata field: {key}")
    
    # Validate agents
    if 'agents' in data:
        expected_agents = ['SAC', 'PPO', 'A2C']
        for agent_name in expected_agents:
            if agent_name not in data['agents']:
                issues.append(f"✗ Missing agent: {agent_name}")
            else:
                agent = data['agents'][agent_name]
                required_fields = ['algorithm_name', 'status', 'training_configuration', 
                                 'final_metrics', 'reductions_vs_baseline']
                for field in required_fields:
                    if field not in agent:
                        issues.append(f"✗ Agent {agent_name} missing field: {field}")
    
    # Validate baseline
    if 'baseline' in data:
        baseline = data['baseline']
        required_baseline = ['scenario', 'annual_grid_import_kwh', 'annual_co2_kg']
        for key in required_baseline:
            if key not in baseline:
                issues.append(f"✗ Missing baseline field: {key}")
    
    is_valid = len(issues) == 0
    return is_valid, issues


def print_summary(archive_path: Path) -> None:
    """Print a summary of the archive contents."""
    with open(archive_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "=" * 70)
    print("TRAINING RESULTS ARCHIVE SUMMARY")
    print("=" * 70)
    
    # Metadata
    metadata = data.get('metadata', {})
    print(f"\nProject: {metadata.get('project', 'N/A')}")
    print(f"Location: {metadata.get('location', 'N/A')}")
    print(f"Generated: {metadata.get('timestamp_generated', 'N/A')}")
    print(f"Archive Version: {metadata.get('archive_version', 'N/A')}")
    print(f"Total Agents Trained: {metadata.get('total_agents_trained', 'N/A')}")
    print(f"All Trainings Completed: {metadata.get('all_trainings_completed', 'N/A')}")
    
    # Baseline
    baseline = data.get('baseline', {})
    print(f"\nBaseline ({baseline.get('scenario', 'N/A')}):")
    print(f"  Annual Grid Import: {baseline.get('annual_grid_import_kwh', 0):,} kWh")
    print(f"  Annual CO₂: {baseline.get('annual_co2_kg', 0):,} kg")
    
    # Agents
    if 'agents' in data:
        print("\nAgents:")
        for agent_name, agent_data in data['agents'].items():
            status = agent_data.get('status', 'UNKNOWN')
            algorithm = agent_data.get('algorithm_name', 'N/A')
            
            metrics = agent_data.get('final_metrics', {})
            grid_import = metrics.get('grid_import_kwh_annual', 0)
            co2 = metrics.get('co2_kg_annual', 0)
            
            reductions = agent_data.get('reductions_vs_baseline', {})
            co2_reduction = reductions.get('co2_reduction_pct', 0)
            
            print(f"\n  {agent_name} ({algorithm}):")
            print(f"    Status: {status}")
            print(f"    Annual Grid Import: {grid_import:,} kWh")
            print(f"    Annual CO₂: {co2:,} kg")
            print(f"    CO₂ Reduction: {co2_reduction:.2f}%")
    
    # Comparison
    if 'comparison_summary' in data:
        summary = data['comparison_summary']
        print("\nComparison Summary:")
        print(f"  Best Energy Efficiency: {summary.get('best_energy_efficiency', 'N/A')}")
        print(f"  Fastest Training: {summary.get('fastest_training', 'N/A')}")
        print(f"  Highest Reward: {summary.get('highest_reward', 'N/A')}")
        print(f"  Best All-Around: {summary.get('best_all_around', 'N/A')}")
    
    print("\n" + "=" * 70)


def main():
    """Main verification routine."""
    archive_path = Path(__file__).parent / 'training_results_archive.json'
    
    print("Verifying training results archive...")
    print(f"File: {archive_path}")
    
    is_valid, issues = verify_archive(archive_path)
    
    if is_valid:
        print("\n✓ Archive file is VALID")
        print_summary(archive_path)
        return 0
    else:
        print("\n✗ Archive file has ISSUES:")
        for issue in issues:
            print(f"  {issue}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
