"""Initialize baseline module (v5.5 - legacy baseline removed).

This module contains stub baseline implementations for backward compatibility.
Most baseline functionality was migrated to src/agents/ in v5.5.

The primary no_control baseline is in src/agents/no_control.py.
This folder is kept for legacy compatibility only.
"""

from __future__ import annotations

from .no_control import NoControlAgent, make_no_control, make_uncontrolled, UncontrolledChargingAgent

__all__ = [
    'NoControlAgent',
    'make_no_control',
    'make_uncontrolled',
    'UncontrolledChargingAgent',
]
