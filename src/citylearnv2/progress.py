"""Progress tracking and metrics extraction for RL training.

Provides utilities for:
- Recording episode metrics (reward, energy, CO2)
- Appending progress rows to CSV
- Extracting step-level metrics from CityLearn
- Rendering progress plots
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import csv
import logging
import numpy as np

logger = logging.getLogger(__name__)


def append_progress_row(
    progress_path: Path,
    row: Dict[str, Any],
    headers: Tuple[str, ...] = ("timestamp", "agent", "episode", "episode_reward", "episode_length", "global_step")
) -> None:
    """Append a row to progress CSV file.

    Creates file if it doesn't exist. Ensures headers are present.

    Args:
        progress_path: Path to progress CSV file
        row: Dictionary of values to append
        headers: CSV column headers (default matches typical RL progress format)

    Example:
        >>> row = {
        ...     "timestamp": "2026-02-04T10:30:00",
        ...     "agent": "sac",
        ...     "episode": 1,
        ...     "episode_reward": 0.5,
        ...     "episode_length": 8760,
        ...     "global_step": 8760
        ... }
        >>> append_progress_row(Path("progress.csv"), row)
    """
    progress_path = Path(progress_path)
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists and has content
    file_exists = progress_path.exists() and progress_path.stat().st_size > 0

    try:
        with open(progress_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)

            # Write header if file is new or empty
            if not file_exists:
                writer.writeheader()

            # Write the row, using empty string for missing keys
            row_data = {k: row.get(k, "") for k in headers}
            writer.writerow(row_data)

        logger.debug(f"Progress row appended: episode={row.get('episode', '?')}, step={row.get('global_step', '?')}")

    except (IOError, OSError) as e:
        logger.error(f"Error writing progress CSV: {e}")


def render_progress_plot(
    progress_path: Path,
    output_path: Path,
    title: str = "Training Progress"
) -> None:
    """Render training progress plot from CSV file.

    Reads CSV and generates a PNG plot showing:
    - Episode reward over time
    - Episode length trends
    - Optional: CO2 reduction, energy metrics

    Args:
        progress_path: Path to progress CSV file
        output_path: Path where PNG will be saved
        title: Plot title (defaults to "Training Progress")

    Note:
        Requires matplotlib. If not available, logs warning and returns.

    Example:
        >>> from pathlib import Path
        >>> render_progress_plot(
        ...     Path("progress.csv"),
        ...     Path("progress.png"),
        ...     title="SAC Training"
        ... )
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping plot generation")
        return

    try:
        import pandas as pd
    except ImportError:
        logger.warning("pandas not available, skipping plot generation")
        return

    progress_path = Path(progress_path)
    output_path = Path(output_path)

    if not progress_path.exists():
        logger.warning(f"Progress file not found: {progress_path}")
        return

    try:
        df = pd.read_csv(progress_path)

        if df.empty:
            logger.warning("Progress CSV is empty, skipping plot")
            return

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(title, fontsize=16, fontweight="bold")

        # Plot 1: Episode Reward
        if "episode_reward" in df.columns:
            episodes = df.index
            rewards = df["episode_reward"].fillna(0)
            axes[0, 0].plot(episodes, rewards, marker=".", linestyle="-", alpha=0.7)
            axes[0, 0].set_title("Episode Reward")
            axes[0, 0].set_xlabel("Episode")
            axes[0, 0].set_ylabel("Reward")
            axes[0, 0].grid(True, alpha=0.3)

        # Plot 2: Episode Length
        if "episode_length" in df.columns:
            lengths = df["episode_length"].fillna(8760)
            axes[0, 1].plot(episodes, lengths, marker=".", linestyle="-", color="orange", alpha=0.7)
            axes[0, 1].set_title("Episode Length")
            axes[0, 1].set_xlabel("Episode")
            axes[0, 1].set_ylabel("Steps")
            axes[0, 1].axhline(y=8760, color="r", linestyle="--", label="Expected (8760)")
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)

        # Plot 3: Global Steps
        if "global_step" in df.columns:
            steps = df["global_step"]
            axes[1, 0].plot(episodes, steps, marker=".", linestyle="-", color="green", alpha=0.7)
            axes[1, 0].set_title("Global Training Steps")
            axes[1, 0].set_xlabel("Episode")
            axes[1, 0].set_ylabel("Total Steps")
            axes[1, 0].grid(True, alpha=0.3)

        # Plot 4: Agent Type Distribution (if available)
        if "agent" in df.columns:
            agents = df["agent"].value_counts()
            axes[1, 1].bar(agents.index, agents.values, color="skyblue", alpha=0.7)
            axes[1, 1].set_title("Episodes by Agent")
            axes[1, 1].set_xlabel("Agent")
            axes[1, 1].set_ylabel("Count")
            axes[1, 1].grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close()

        logger.info(f"Progress plot saved: {output_path}")

    except Exception as e:
        logger.error(f"Error rendering progress plot: {e}")


def extract_step_metrics(
    env: Any,
    step_num: int,
    observation: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """Extract metrics from environment at current step.

    Extracts:
    - Grid import (kWh)
    - Solar generation (kWh)
    - CO2 grid (kg)
    - EV charges (count)
    - Battery SOC (%)

    Args:
        env: CityLearn environment
        step_num: Current step number
        observation: Current observation (optional, for logging)

    Returns:
        Dictionary with step metrics

    Example:
        >>> metrics = extract_step_metrics(env, step_num=100, obs=obs)
        >>> print(metrics["grid_kWh"])
        150.5
    """
    metrics: Dict[str, float] = {
        "grid_kWh": 0.0,
        "solar_kWh": 0.0,
        "co2_kg": 0.0,
        "motos_charged": 0,
        "mototaxis_charged": 0,
        "bess_soc": 0.0,
    }

    try:
        # Try to extract from buildings
        buildings = getattr(env, "buildings", [])
        if not buildings:
            return metrics

        for building in buildings:
            try:
                # Grid import
                net_elec = getattr(building, "net_electricity_consumption", None)
                if net_elec is not None and isinstance(net_elec, (list, tuple)) and len(net_elec) > 0:
                    val = net_elec[-1]
                    if val is not None and isinstance(val, (int, float)):
                        metrics["grid_kWh"] += float(max(0.0, val))

                # Solar generation
                solar = getattr(building, "solar_generation", None)
                if solar is not None and isinstance(solar, (list, tuple)) and len(solar) > 0:
                    val = solar[-1]
                    if val is not None and isinstance(val, (int, float)):
                        metrics["solar_kWh"] += float(max(0.0, val))

                # BESS SOC
                storage = getattr(building, "electrical_storage", None)
                if storage is not None:
                    soc = getattr(storage, "state_of_charge", None)
                    if soc is not None:
                        metrics["bess_soc"] = float(soc) * 100.0  # Convert to percentage

                # CO2 calculation (0.4521 kg/kWh for grid in Iquitos)
                if metrics["grid_kWh"] > 0:
                    metrics["co2_kg"] = metrics["grid_kWh"] * 0.4521

            except (AttributeError, IndexError, TypeError, ValueError):
                pass

    except Exception as e:
        logger.debug(f"Error extracting step metrics: {e}")

    return metrics


def get_episode_summary(training_history: list[Dict[str, float]]) -> Dict[str, Any]:
    """Generate summary statistics from training history.

    Calculates:
    - Mean reward per episode
    - Total CO2 reduction
    - Training efficiency metrics

    Args:
        training_history: List of episode dictionaries (output from agent.training_history)

    Returns:
        Summary dictionary with aggregated metrics

    Example:
        >>> history = agent.training_history
        >>> summary = get_episode_summary(history)
        >>> print(f"Mean reward: {summary['mean_reward']:.4f}")
    """
    if not training_history:
        return {
            "num_episodes": 0,
            "mean_reward": 0.0,
            "total_co2_kg": 0.0,
            "mean_grid_kwh": 0.0,
            "mean_solar_kwh": 0.0,
        }

    rewards = [ep.get("mean_reward", 0.0) for ep in training_history]
    co2_vals = [ep.get("episode_co2_kg", 0.0) for ep in training_history]
    grid_vals = [ep.get("episode_grid_kwh", 0.0) for ep in training_history]
    solar_vals = [ep.get("episode_solar_kwh", 0.0) for ep in training_history]

    return {
        "num_episodes": len(training_history),
        "mean_reward": float(np.mean(rewards)) if rewards else 0.0,
        "std_reward": float(np.std(rewards)) if len(rewards) > 1 else 0.0,
        "total_co2_kg": float(np.sum(co2_vals)) if co2_vals else 0.0,
        "mean_grid_kwh": float(np.mean(grid_vals)) if grid_vals else 0.0,
        "mean_solar_kwh": float(np.mean(solar_vals)) if solar_vals else 0.0,
        "max_reward": float(np.max(rewards)) if rewards else 0.0,
        "min_reward": float(np.min(rewards)) if rewards else 0.0,
    }
