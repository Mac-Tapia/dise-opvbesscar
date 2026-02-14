"""Re-export FixedScheduleAgent from citylearnv2.dataset_builder for backward compatibility."""

from __future__ import annotations

from ..citylearnv2.dataset_builder.fixed_schedule import FixedScheduleAgent, make_fixed_schedule

__all__ = ["FixedScheduleAgent", "make_fixed_schedule"]
