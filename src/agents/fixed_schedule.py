"""Re-export FixedScheduleAgent from citylearnv2.progress for backward compatibility."""

from __future__ import annotations

from ..citylearnv2.progress.fixed_schedule import FixedScheduleAgent, make_fixed_schedule

__all__ = ["FixedScheduleAgent", "make_fixed_schedule"]
