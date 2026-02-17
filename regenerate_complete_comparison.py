#!/usr/bin/env python3
"""
REGENERATE COMPLETE COMPARISON GRAPHS
Loads final checkpoints for A2C, PPO, SAC and generates comprehensive comparison analysis
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from stable_baselines3 import A2C, PPO, SAC

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIR = Path("outputs/complete_agent_analysis")
CHECKPOINT_PATHS = {
    "A2C": "checkpoints/A2C/a2c_final_model.zip",
    "PPO": "checkpoints/PPO/ppo_final.zip",
    "SAC": "checkpoints/SAC/sac_model_final_20260216_211845.zip",
}
COLORS = {"A2C": "#FF6B6B", "PPO": "#4ECDC4", "SAC": "#45B7D1"}


class CompleteComparisonGenerator:
    """Generate comprehensive comparison graphs from trained checkpoints."""

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data = {}
        self.metrics = {}
        logger.info(f"✓ Output directory: {self.output_dir}")

    def load_training_results(self) -> None:
        """Load training results JSON files."""
        logger.info("\n" + "="*70)
        logger.info("LOADING TRAINING RESULTS")
        logger.info("="*70)

        for agent in ["A2C", "PPO", "SAC"]:
            agent_lower = agent.lower()
            result_path = Path(f"outputs/{agent_lower}_training/result_{agent_lower}.json")
            
            if result_path.exists():
                with open(result_path) as f:
                    self.data[agent] = json.load(f)
                logger.info(f"✓ {agent} results loaded")
            else:
                logger.warning(f"✗ {agent} results not found at {result_path}")
                self.data[agent] = {}

    def extract_complete_metrics(self) -> None:
        """Extract all metrics from training results."""
        logger.info("\n" + "="*70)
        logger.info("EXTRACTING COMPLETE METRICS")
        logger.info("="*70)

        for agent in ["A2C", "PPO", "SAC"]:
            result = self.data.get(agent, {})
            self.metrics[agent] = {}

            # Training info
            training = result.get("training", {})
            self.metrics[agent]["total_timesteps"] = training.get("total_timesteps", 0)
            self.metrics[agent]["episodes"] = training.get("episodes", 0)
            self.metrics[agent]["duration_seconds"] = training.get("duration_seconds", 0)
            self.metrics[agent]["speed_steps_per_sec"] = training.get("speed_steps_per_second", 0)

            # Hyperparameters
            hyperparams = training.get("hyperparameters", {})
            self.metrics[agent]["learning_rate"] = hyperparams.get("learning_rate", 0)
            self.metrics[agent]["gamma"] = hyperparams.get("gamma", 0)
            self.metrics[agent]["gae_lambda"] = hyperparams.get("gae_lambda", 0)

            # Training evolution
            training_evolution = result.get("training_evolution", {})
            episode_rewards = training_evolution.get("episode_rewards", [])
            
            # SAC stores rewards as strings at root level
            if not episode_rewards and "episode_rewards" in result:
                episode_rewards = [float(r) if isinstance(r, str) else float(r) 
                                  for r in result.get("episode_rewards", [])]

            if episode_rewards:
                self.metrics[agent]["episode_rewards"] = episode_rewards
                self.metrics[agent]["final_reward"] = float(episode_rewards[-1])
                self.metrics[agent]["best_reward"] = float(max(episode_rewards))
                self.metrics[agent]["avg_reward"] = float(np.mean(episode_rewards))

            # CO2 evolution
            episode_co2_grid = training_evolution.get("episode_co2_grid", [])
            if not episode_co2_grid and "episode_co2_grid_kg" in result:
                episode_co2_grid = result.get("episode_co2_grid_kg", [])

            if episode_co2_grid:
                self.metrics[agent]["episode_co2_grid"] = episode_co2_grid
                self.metrics[agent]["final_co2_grid"] = float(episode_co2_grid[-1])
                self.metrics[agent]["best_co2_grid"] = float(min(episode_co2_grid))
                self.metrics[agent]["avg_co2_grid"] = float(np.mean(episode_co2_grid))

            # Validation metrics
            validation = result.get("validation", {})
            self.metrics[agent]["mean_reward"] = validation.get("mean_reward", 0)
            self.metrics[agent]["mean_co2_avoided_kg"] = validation.get("mean_co2_avoided_kg", 0)
            self.metrics[agent]["mean_grid_import_kwh"] = validation.get("mean_grid_import_kwh", 0)
            self.metrics[agent]["mean_solar_kwh"] = validation.get("mean_solar_kwh", 0)

            logger.info(f"✓ {agent}: {len(episode_rewards)} episodes, {self.metrics[agent].get('total_timesteps', 0)} steps")

    def generate_reward_evolution_complete(self) -> None:
        """Generate complete reward evolution comparison."""
        logger.info("\n  Generating reward evolution graphs...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))

        # Individual reward curves
        for idx, agent in enumerate(["A2C", "PPO", "SAC"]):
            if "episode_rewards" in self.metrics[agent]:
                rewards = self.metrics[agent]["episode_rewards"]
                ax = axes[idx // 2, idx % 2]
                ax.plot(range(len(rewards)), rewards, marker="o", color=COLORS[agent], 
                       linewidth=2.5, markersize=8, label=agent)
                ax.fill_between(range(len(rewards)), rewards, alpha=0.3, color=COLORS[agent])
                ax.set_xlabel("Episode", fontsize=11)
                ax.set_ylabel("Reward", fontsize=11)
                ax.set_title(f"{agent} Reward Evolution", fontsize=12, fontweight="bold")
                ax.grid(True, alpha=0.3)
                ax.legend()

        # Comparative bar chart
        ax = axes[1, 1]
        agents = ["A2C", "PPO", "SAC"]
        final_rewards = [self.metrics[a].get("final_reward", 0) for a in agents]
        bars = ax.bar(agents, final_rewards, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Final Reward", fontsize=11)
        ax.set_title("Final Reward Comparison", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}', ha='center', va='bottom', fontsize=10, fontweight="bold")

        plt.tight_layout()
        output_path = self.output_dir / "01_reward_evolution_complete.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"    ✓ Saved: {output_path.name}")

    def generate_co2_evolution_complete(self) -> None:
        """Generate complete CO2 evolution comparison."""
        logger.info("\n  Generating CO2 evolution graphs...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))

        # Individual CO2 curves
        for idx, agent in enumerate(["A2C", "PPO", "SAC"]):
            if "episode_co2_grid" in self.metrics[agent]:
                co2_values = self.metrics[agent]["episode_co2_grid"]
                ax = axes[idx // 2, idx % 2]
                ax.plot(range(len(co2_values)), co2_values, marker="s", color=COLORS[agent],
                       linewidth=2.5, markersize=8, label=agent)
                ax.fill_between(range(len(co2_values)), co2_values, alpha=0.3, color=COLORS[agent])
                ax.set_xlabel("Episode", fontsize=11)
                ax.set_ylabel("CO₂ Grid (kg)", fontsize=11)
                ax.set_title(f"{agent} CO₂ Grid Evolution", fontsize=12, fontweight="bold")
                ax.grid(True, alpha=0.3)
                ax.legend()
                ax.ticklabel_format(style='plain', axis='y')

        # Comparative bar chart
        ax = axes[1, 1]
        agents = ["A2C", "PPO", "SAC"]
        co2_values = [self.metrics[a].get("final_co2_grid", 0) for a in agents]
        bars = ax.bar(agents, co2_values, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Final CO₂ Grid (kg)", fontsize=11)
        ax.set_title("Final CO₂ Comparison", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height/1e6:.2f}M', ha='center', va='bottom', fontsize=10, fontweight="bold")

        plt.tight_layout()
        output_path = self.output_dir / "02_co2_evolution_complete.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"    ✓ Saved: {output_path.name}")

    def generate_training_metrics_dashboard(self) -> None:
        """Generate comprehensive training metrics dashboard."""
        logger.info("\n  Generating training metrics dashboard...")

        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

        # 1. Training duration
        ax = fig.add_subplot(gs[0, 0])
        agents = ["A2C", "PPO", "SAC"]
        durations = [self.metrics[a].get("duration_seconds", 0) for a in agents]
        ax.bar(agents, durations, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Duration (seconds)", fontsize=10)
        ax.set_title("Training Time", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 2. Training speed
        ax = fig.add_subplot(gs[0, 1])
        speeds = [self.metrics[a].get("speed_steps_per_sec", 0) for a in agents]
        ax.bar(agents, speeds, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Steps/Second", fontsize=10)
        ax.set_title("Training Speed", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 3. Total timesteps
        ax = fig.add_subplot(gs[0, 2])
        timesteps = [self.metrics[a].get("total_timesteps", 0) for a in agents]
        ax.bar(agents, timesteps, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Timesteps", fontsize=10)
        ax.set_title("Total Timesteps", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 4. Learning rate
        ax = fig.add_subplot(gs[1, 0])
        lr_values = [self.metrics[a].get("learning_rate", 0) for a in agents]
        ax.bar(agents, lr_values, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Learning Rate", fontsize=10)
        ax.set_title("Learning Rate", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        ax.set_yscale('log')

        # 5. Gamma (discount factor)
        ax = fig.add_subplot(gs[1, 1])
        gamma_values = [self.metrics[a].get("gamma", 0) for a in agents]
        ax.bar(agents, gamma_values, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Gamma", fontsize=10)
        ax.set_title("Discount Factor (γ)", fontweight="bold")
        ax.set_ylim([0.8, 1.0])
        ax.grid(True, alpha=0.3, axis="y")

        # 6. Episodes completed
        ax = fig.add_subplot(gs[1, 2])
        episodes = [self.metrics[a].get("episodes", 0) for a in agents]
        ax.bar(agents, episodes, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Episodes", fontsize=10)
        ax.set_title("Episodes Completed", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 7. Final reward
        ax = fig.add_subplot(gs[2, 0])
        final_rewards = [self.metrics[a].get("final_reward", 0) for a in agents]
        ax.bar(agents, final_rewards, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Reward", fontsize=10)
        ax.set_title("Final Episode Reward", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 8. Best reward
        ax = fig.add_subplot(gs[2, 1])
        best_rewards = [self.metrics[a].get("best_reward", 0) for a in agents]
        ax.bar(agents, best_rewards, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Reward", fontsize=10)
        ax.set_title("Best Episode Reward", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # 9. Average reward
        ax = fig.add_subplot(gs[2, 2])
        avg_rewards = [self.metrics[a].get("avg_reward", 0) for a in agents]
        ax.bar(agents, avg_rewards, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Reward", fontsize=10)
        ax.set_title("Average Episode Reward", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        fig.suptitle("Training Metrics Dashboard - Complete Comparison", fontsize=14, fontweight="bold", y=0.995)
        output_path = self.output_dir / "03_training_metrics_dashboard.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"    ✓ Saved: {output_path.name}")

    def generate_co2_and_energy_dashboard(self) -> None:
        """Generate CO2 and energy metrics dashboard."""
        logger.info("\n  Generating CO2 and energy dashboard...")

        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

        agents = ["A2C", "PPO", "SAC"]

        # 1. Final CO2 Grid
        ax = fig.add_subplot(gs[0, 0])
        co2_values = [self.metrics[a].get("final_co2_grid", 0) for a in agents]
        bars = ax.bar(agents, co2_values, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("CO₂ (kg)", fontsize=10)
        ax.set_title("Final CO₂ from Grid", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height/1e6:.2f}M', 
                   ha='center', va='bottom', fontsize=9)

        # 2. Best CO2 Grid (minimum)
        ax = fig.add_subplot(gs[0, 1])
        best_co2 = [self.metrics[a].get("best_co2_grid", 0) for a in agents]
        bars = ax.bar(agents, best_co2, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("CO₂ (kg)", fontsize=10)
        ax.set_title("Best (Min) CO₂ from Grid", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height/1e6:.2f}M',
                   ha='center', va='bottom', fontsize=9)

        # 3. Average CO2 Grid
        ax = fig.add_subplot(gs[0, 2])
        avg_co2 = [self.metrics[a].get("avg_co2_grid", 0) for a in agents]
        bars = ax.bar(agents, avg_co2, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("CO₂ (kg)", fontsize=10)
        ax.set_title("Average CO₂ from Grid", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height/1e6:.2f}M',
                   ha='center', va='bottom', fontsize=9)

        # 4. Mean CO2 avoided (validation)
        ax = fig.add_subplot(gs[1, 0])
        mean_co2_avoided = [self.metrics[a].get("mean_co2_avoided_kg", 0) for a in agents]
        bars = ax.bar(agents, mean_co2_avoided, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("CO₂ Avoided (kg)", fontsize=10)
        ax.set_title("Mean CO₂ Avoided (Validation)", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height/1e6:.2f}M',
                   ha='center', va='bottom', fontsize=9)

        # 5. Mean grid import
        ax = fig.add_subplot(gs[1, 1])
        mean_grid = [self.metrics[a].get("mean_grid_import_kwh", 0) for a in agents]
        bars = ax.bar(agents, mean_grid, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Grid Import (kWh)", fontsize=10)
        ax.set_title("Mean Grid Import (Validation)", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height/1e6:.2f}M',
                   ha='center', va='bottom', fontsize=9)

        # 6. Mean solar available
        ax = fig.add_subplot(gs[1, 2])
        mean_solar = [self.metrics[a].get("mean_solar_kwh", 0) for a in agents]
        bars = ax.bar(agents, mean_solar, color=[COLORS[a] for a in agents], edgecolor="black", linewidth=1.5)
        ax.set_ylabel("Solar Available (kWh)", fontsize=10)
        ax.set_title("Mean Solar Available (Validation)", fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height/1e6:.2f}M',
                   ha='center', va='bottom', fontsize=9)

        fig.suptitle("CO₂ & Energy Metrics Dashboard", fontsize=14, fontweight="bold", y=0.995)
        output_path = self.output_dir / "04_co2_energy_dashboard.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"    ✓ Saved: {output_path.name}")

    def generate_convergence_analysis(self) -> None:
        """Generate convergence analysis plots."""
        logger.info("\n  Generating convergence analysis...")

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        for idx, agent in enumerate(["A2C", "PPO", "SAC"]):
            ax = axes[idx]
            
            if "episode_rewards" in self.metrics[agent]:
                rewards = self.metrics[agent]["episode_rewards"]
                episodes = range(len(rewards))
                
                # Plot reward evolution
                ax.plot(episodes, rewards, marker="o", color=COLORS[agent], 
                       linewidth=2.5, markersize=8, label="Reward")
                
                # Plot trend line
                if len(rewards) > 1:
                    z = np.polyfit(episodes, rewards, 2)
                    p = np.poly1d(z)
                    ax.plot(episodes, p(episodes), "--", color=COLORS[agent], 
                           alpha=0.6, linewidth=2, label="Trend")
                
                ax.set_xlabel("Episode", fontsize=11)
                ax.set_ylabel("Reward", fontsize=11)
                ax.set_title(f"{agent} Convergence Analysis", fontsize=12, fontweight="bold")
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                # Calculate improvement
                improvement = ((rewards[-1] - rewards[0]) / abs(rewards[0])) * 100 if rewards[0] != 0 else 0
                ax.text(0.5, 0.95, f"Improvement: {improvement:+.1f}%", 
                       transform=ax.transAxes, ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor=COLORS[agent], alpha=0.3),
                       fontsize=10, fontweight="bold")

        plt.tight_layout()
        output_path = self.output_dir / "05_convergence_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"    ✓ Saved: {output_path.name}")

    def save_complete_metrics_csv(self) -> None:
        """Save complete metrics to CSV."""
        logger.info("\n  Saving metrics to CSV...")

        # Flatten hierarchical metrics
        flat_metrics = {}
        for agent, metrics in self.metrics.items():
            flat_metrics[agent] = {}
            for key, value in metrics.items():
                if not isinstance(value, list):
                    flat_metrics[agent][key] = value

        df = pd.DataFrame(flat_metrics).T
        csv_path = self.output_dir / "complete_metrics.csv"
        df.to_csv(csv_path)
        logger.info(f"    ✓ Saved: {csv_path.name}")

        # Also save as JSON for detailed info
        json_path = self.output_dir / "complete_metrics.json"
        with open(json_path, "w") as f:
            json.dump(self.metrics, f, indent=2, default=str)
        logger.info(f"    ✓ Saved: {json_path.name}")

    def generate_summary_report(self) -> None:
        """Generate text summary report."""
        logger.info("\n  Generating summary report...")

        report = "# COMPLETE AGENT COMPARISON REPORT\n\n"
        report += "## TRAINING SUMMARY\n\n"

        for agent in ["A2C", "PPO", "SAC"]:
            m = self.metrics.get(agent, {})
            report += f"### {agent}\n"
            report += f"- **Total Timesteps:** {m.get('total_timesteps', 0):,}\n"
            report += f"- **Episodes:** {m.get('episodes', 0)}\n"
            report += f"- **Training Duration:** {m.get('duration_seconds', 0):.1f} seconds\n"
            report += f"- **Training Speed:** {m.get('speed_steps_per_sec', 0):.1f} steps/sec\n"
            report += f"- **Learning Rate:** {m.get('learning_rate', 0)}\n"
            report += f"- **Gamma:** {m.get('gamma', 0)}\n"
            report += f"- **GAE Lambda:** {m.get('gae_lambda', 0)}\n\n"

        report += "## REWARD METRICS\n\n"
        for agent in ["A2C", "PPO", "SAC"]:
            m = self.metrics.get(agent, {})
            report += f"### {agent}\n"
            report += f"- **Final Reward:** {m.get('final_reward', 0):.2f}\n"
            report += f"- **Best Reward:** {m.get('best_reward', 0):.2f}\n"
            report += f"- **Average Reward:** {m.get('avg_reward', 0):.2f}\n"
            report += f"- **Mean Validation Reward:** {m.get('mean_reward', 0):.2f}\n\n"

        report += "## CO2 METRICS\n\n"
        for agent in ["A2C", "PPO", "SAC"]:
            m = self.metrics.get(agent, {})
            report += f"### {agent}\n"
            report += f"- **Final CO2 Grid (kg):** {m.get('final_co2_grid', 0):.0f}\n"
            report += f"- **Best CO2 Grid (kg):** {m.get('best_co2_grid', 0):.0f}\n"
            report += f"- **Average CO2 Grid (kg):** {m.get('avg_co2_grid', 0):.0f}\n"
            report += f"- **Mean CO2 Avoided (kg):** {m.get('mean_co2_avoided_kg', 0):.0f}\n"
            report += f"- **Mean Grid Import (kWh):** {m.get('mean_grid_import_kwh', 0):.0f}\n"
            report += f"- **Mean Solar Available (kWh):** {m.get('mean_solar_kwh', 0):.0f}\n\n"

        report_path = self.output_dir / "COMPLETE_COMPARISON_REPORT.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"    ✓ Saved: {report_path.name}")

    def run(self) -> None:
        """Execute complete comparison analysis."""
        logger.info("\n" + "="*70)
        logger.info("COMPLETE AGENT COMPARISON - REGENERATING ALL GRAPHS")
        logger.info("="*70)

        self.load_training_results()
        self.extract_complete_metrics()

        logger.info("\n" + "="*70)
        logger.info("GENERATING COMPREHENSIVE GRAPHS")
        logger.info("="*70)

        self.generate_reward_evolution_complete()
        self.generate_co2_evolution_complete()
        self.generate_training_metrics_dashboard()
        self.generate_co2_and_energy_dashboard()
        self.generate_convergence_analysis()
        self.save_complete_metrics_csv()
        self.generate_summary_report()

        logger.info("\n" + "="*70)
        logger.info("✅ COMPLETE ANALYSIS FINISHED")
        logger.info("="*70)
        logger.info(f"\n📁 Output directory: {self.output_dir}")
        logger.info("\n📊 Generated files:")
        for file in sorted(self.output_dir.glob("*")):
            logger.info(f"   - {file.name}")


def main():
    generator = CompleteComparisonGenerator()
    generator.run()
    return 0


if __name__ == "__main__":
    exit(main())
