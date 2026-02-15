"""Metrics extraction utilities for agent training.

Consolidated from old citylearnv2.dataset_builder.metrics_extractor module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class EpisodeMetricsAccumulator:
    """Accumulates metrics over an episode."""
    
    episode_rewards: List[float] = field(default_factory=list)
    episode_co2: List[float] = field(default_factory=list)
    episode_cost: List[float] = field(default_factory=list)
    episode_solar: List[float] = field(default_factory=list)
    
    def add_step_metrics(
        self,
        reward: float,
        co2: float = 0.0,
        cost: float = 0.0,
        solar: float = 0.0,
    ) -> None:
        """Add metrics from a single step."""
        self.episode_rewards.append(reward)
        self.episode_co2.append(co2)
        self.episode_cost.append(cost)
        self.episode_solar.append(solar)
    
    def get_episode_summary(self) -> Dict[str, float]:
        """Get aggregated metrics for entire episode."""
        import statistics
        
        return {
            "episode_reward_total": sum(self.episode_rewards) if self.episode_rewards else 0.0,
            "episode_reward_mean": statistics.mean(self.episode_rewards) if self.episode_rewards else 0.0,
            "episode_reward_min": min(self.episode_rewards) if self.episode_rewards else 0.0,
            "episode_reward_max": max(self.episode_rewards) if self.episode_rewards else 0.0,
            "episode_co2_total": sum(self.episode_co2) if self.episode_co2 else 0.0,
            "episode_cost_total": sum(self.episode_cost) if self.episode_cost else 0.0,
            "episode_solar_total": sum(self.episode_solar) if self.episode_solar else 0.0,
        }
    
    def reset(self) -> None:
        """Reset accumulators for new episode."""
        self.episode_rewards = []
        self.episode_co2 = []
        self.episode_cost = []
        self.episode_solar = []


def extract_step_metrics(
    info: Dict[str, Any],
) -> Dict[str, float]:
    """Extract metrics from step info dict.

    Args:
        info: Info dict from environment step()

    Returns:
        Dict with extracted scalar metrics
    """
    metrics: Dict[str, float] = {}
    
    # Extract multi-objective components if available
    multi_obj = info.get("multi_objective", {})
    
    metrics["reward"] = float(info.get("reward", 0.0))
    metrics["r_co2"] = float(multi_obj.get("r_co2", 0.0))
    metrics["r_solar"] = float(multi_obj.get("r_solar", 0.0))
    metrics["r_ev"] = float(multi_obj.get("r_ev", 0.0))
    metrics["r_grid"] = float(multi_obj.get("r_grid", 0.0))
    metrics["r_cost"] = float(multi_obj.get("r_cost", 0.0))
    metrics["co2_net_kg"] = float(multi_obj.get("co2_net_kg", 0.0))
    metrics["cost_usd"] = float(multi_obj.get("cost_usd", 0.0))
    
    return metrics


__all__ = ["EpisodeMetricsAccumulator", "extract_step_metrics"]
