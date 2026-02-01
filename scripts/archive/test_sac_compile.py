#!/usr/bin/env python
"""Test SAC compilation status"""
try:
    from iquitos_citylearn.oe3.agents.sac import SACConfig
    print("✓ SAC compila correctamente")
except Exception as e:
    print(f"❌ SAC error: {e}")
    import traceback
    traceback.print_exc()
