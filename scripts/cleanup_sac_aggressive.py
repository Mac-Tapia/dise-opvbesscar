#!/usr/bin/env python3
"""
Cleanup Script for SAC Checkpoints - v8.0 FIX REWARDS OVERFLOW
Remove corrupted checkpoints to allow fresh training with corrected reward scaling.
SAFE: Only removes SAC/ directory, preserves PPO/ and A2C/
"""

import os
import shutil
from pathlib import Path

def cleanup_sac_checkpoints():
    """Delete SAC checkpoints to start fresh with v8.0 reward scaling."""
    
    workspace_root = Path("d:\\diseñopvbesscar")
    sac_checkpoint_dir = workspace_root / "checkpoints" / "SAC"
    
    # Safety checks
    if not workspace_root.exists():
        print(f"ERROR: Workspace not found: {workspace_root}")
        return False
    
    if not sac_checkpoint_dir.exists():
        print(f"✓ SAC checkpoint directory doesn't exist - nothing to clean")
        return True
    
    # List what will be deleted
    files_to_delete = list(sac_checkpoint_dir.glob("*"))
    if files_to_delete:
        print(f"\n🗑️  SAC CHECKPOINT CLEANUP - v8.0 FIX")
        print(f"{'='*60}")
        print(f"Location: {sac_checkpoint_dir}")
        print(f"Files to delete: {len(files_to_delete)}")
        for f in files_to_delete:
            print(f"  - {f.name}")
        print("=" * 60)
        
        # Perform deletion
        try:
            shutil.rmtree(sac_checkpoint_dir)
            os.makedirs(sac_checkpoint_dir)  # Recreate empty directory
            print(f"\n✅ SAC checkpoints cleaned successfully!")
            print(f"   New training will start fresh with v8.0 reward scaling")
            return True
        except Exception as e:
            print(f"\n❌ ERROR: Failed to delete SAC checkpoints: {e}")
            return False
    else:
        print(f"✓ SAC checkpoint directory is already empty")
        return True

if __name__ == "__main__":
    success = cleanup_sac_checkpoints()
    exit(0 if success else 1)
