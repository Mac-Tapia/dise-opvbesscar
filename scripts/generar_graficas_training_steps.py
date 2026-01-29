"""
Script para generar gráficas de entrenamiento paso a paso (step-by-step)
Muestra la evolución de cada agente desde checkpoint inicial hasta final
"""

from __future__ import annotations

import re
from pathlib import Path
import numpy as np
import pandas as pd  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.ticker as mticker  # type: ignore
import seaborn as sns  # type: ignore

# Configuración de estilo
sns.set_style("darkgrid", {'axes.facecolor': '#f5f5f5'})
COLORS = {
    'SAC': '#FF6B6B',
    'PPO': '#4ECDC4',
    'A2C': '#45B7D1',
}

OUTPUT_DIR = Path('analyses/oe3/training/graphics/step_by_step')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_DIR = Path('analyses/oe3/training/checkpoints')


def extract_step_from_checkpoint(filename: str) -> int | None:
    """Extrae el número de step del nombre del checkpoint"""
    match = re.search(r'step_(\d+)', filename)
    if match:
        return int(match.group(1))
    return None


def get_checkpoint_steps(agent: str) -> list[tuple[int, Path]]:
    """Obtiene lista de checkpoints disponibles para un agente"""
    agent_dir = CHECKPOINT_DIR / agent
    checkpoints = []

    for checkpoint in agent_dir.glob('*_step_*.zip'):
        step = extract_step_from_checkpoint(checkpoint.name)
        if step:
            checkpoints.append((step, checkpoint))

    return sorted(checkpoints)


def plot_training_steps_timeline() -> None:
    """
    Gráfica principal: Evolución temporal de pasos de entrenamiento para cada agente
    """
    print("[GRAFICAS] Generando grafica de evolucion temporal...")

    _, ax = plt.subplots(figsize=(14, 8), dpi=300)

    for agent in ['SAC', 'PPO', 'A2C']:
        checkpoints = get_checkpoint_steps(agent)
        steps = [step for step, _ in checkpoints]

        # Crear línea de progreso
        ax.plot(range(len(steps)), steps, marker='o', label=agent,
               color=COLORS[agent], linewidth=2.5, markersize=6, alpha=0.8)

    ax.set_xlabel('Número de Checkpoint', fontsize=12, fontweight='bold')
    ax.set_ylabel('Pasos de Entrenamiento', fontsize=12, fontweight='bold')
    ax.set_title('Evolución de Pasos de Entrenamiento por Agente\n(Checkpoint Progress)',
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{int(x):,}'))

    plt.tight_layout()
    output_file = OUTPUT_DIR / 'training_steps_timeline.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"OK {output_file.name}")


def plot_checkpoint_count_by_agent() -> None:
    """
    Gráfica: Cantidad de checkpoints disponibles por agente
    """
    print("[GRAFICAS] Generando grafica de checkpoints por agente...")

    _, ax = plt.subplots(figsize=(10, 6), dpi=300)

    agents = ['SAC', 'PPO', 'A2C']
    counts = [len(get_checkpoint_steps(agent)) for agent in agents]

    bars = ax.bar(agents, counts, color=[COLORS[a] for a in agents], alpha=0.8, edgecolor='black', linewidth=2)

    # Añadir valores en las barras
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{int(count)}',
               ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax.set_ylabel('Número de Checkpoints', fontsize=12, fontweight='bold')
    ax.set_title('Checkpoints Disponibles por Agente\n(Total Guardados Durante Entrenamiento)',
                fontsize=14, fontweight='bold', pad=20)
    ax.set_ylim(0, max(counts) * 1.1)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    output_file = OUTPUT_DIR / 'checkpoint_count_by_agent.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"OK {output_file.name}")


def plot_step_intervals() -> None:
    """
    Gráfica: Intervalos entre checkpoints (muestra patrón de guardado)
    """
    print("[GRAFICAS] Generando grafica de intervalos de checkpoint...")

    _, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=300)

    for idx, agent in enumerate(['SAC', 'PPO', 'A2C']):
        ax = axes[idx]
        checkpoints = get_checkpoint_steps(agent)
        steps = [step for step, _ in checkpoints]

        if len(steps) > 1:
            intervals = [steps[i+1] - steps[i] for i in range(len(steps)-1)]
            ax.bar(range(len(intervals)), intervals, color=COLORS[agent], alpha=0.7, edgecolor='black')
            ax.set_xlabel('Checkpoint Index', fontsize=10, fontweight='bold')
            ax.set_ylabel('Intervalo (pasos)', fontsize=10, fontweight='bold')
            ax.set_title(f'{agent}\nIntervalo Promedio: {np.mean(intervals):.0f} pasos',
                        fontsize=11, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Intervalos de Guardado de Checkpoints por Agente',
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_file = OUTPUT_DIR / 'checkpoint_intervals.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"OK {output_file.name}")


def plot_cumulative_steps() -> None:
    """
    Gráfica: Pasos cumulativos de entrenamiento por agente
    """
    print("[GRAFICAS] Generando grafica de pasos acumulativos...")

    _, ax = plt.subplots(figsize=(14, 8), dpi=300)

    for agent in ['SAC', 'PPO', 'A2C']:
        checkpoints = get_checkpoint_steps(agent)
        steps = [step for step, _ in checkpoints]

        # Crear línea de progreso acumulativo
        ax.plot(steps, steps, marker='s', label=agent,
               color=COLORS[agent], linewidth=3, markersize=5, alpha=0.8)

    ax.set_xlabel('Indice de Checkpoint', fontsize=12, fontweight='bold')
    ax.set_ylabel('Pasos Acumulativos de Entrenamiento', fontsize=12, fontweight='bold')
    ax.set_title('Acumulacion de Pasos de Entrenamiento por Agente\n(Checkpoint Progress Timeline)',
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{int(x):,}'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{int(x):,}'))

    plt.tight_layout()
    output_file = OUTPUT_DIR / 'cumulative_training_steps.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"OK {output_file.name}")


def generate_checkpoint_summary_table():
    """
    Generar tabla resumen de checkpoints por agente
    """
    print("📋 Generando tabla resumen...")

    summary_data = []

    for agent in ['SAC', 'PPO', 'A2C']:
        checkpoints = get_checkpoint_steps(agent)
        steps = [step for step, _ in checkpoints]

        if steps:
            summary_data.append({
                'Agente': agent,
                'Checkpoints': len(checkpoints),
                'Inicio': f"{steps[0]:,}",
                'Fin': f"{steps[-1]:,}",
                'Intervalo Típico': f"{(steps[-1] - steps[0]) / (len(steps) - 1):,.0f}",
                'Total Pasos': f"{steps[-1]:,}"
            })

    df = pd.DataFrame(summary_data)

    # Guardar como CSV
    csv_file = OUTPUT_DIR / 'checkpoint_summary.csv'
    df.to_csv(csv_file, index=False)
    print(f"OK {csv_file.name}")

    # Generar tabla visual
    _, ax = plt.subplots(figsize=(14, 4), dpi=300)
    ax.axis('tight')
    ax.axis('off')

    table_data = df.values.tolist()
    table = ax.table(cellText=table_data, colLabels=list(df.columns),
                    cellLoc='center', loc='center', bbox=(0, 0, 1, 1))  # type: ignore

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # Colorear headers
    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Colorear filas
    for i, agent in enumerate(['SAC', 'PPO', 'A2C']):
        table[(i+1, 0)].set_facecolor(COLORS[agent])
        table[(i+1, 0)].set_text_props(weight='bold', color='white')

    plt.title('Resumen de Checkpoints por Agente\n(Training Steps Progress)',
             fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    output_file = OUTPUT_DIR / 'checkpoint_summary_table.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ {output_file.name}")


def create_checkpoint_documentation():
    """
    Crear documentación sobre los checkpoints disponibles
    """
    print("📄 Generando documentación...")

    doc = """# Gráficas de Entrenamiento Paso a Paso (Step-by-Step)

## 📊 Descripción

Este conjunto de gráficas muestra la evolución del entrenamiento de los agentes RL
paso a paso, desde el checkpoint inicial hasta el final.

## 📁 Checkpoints Disponibles

"""

    for agent in ['SAC', 'PPO', 'A2C']:
        checkpoints = get_checkpoint_steps(agent)
        steps = [step for step, _ in checkpoints]

        doc += f"\n### {agent}\n"
        doc += f"- **Total de checkpoints**: {len(checkpoints)}\n"
        doc += f"- **Rango de pasos**: {steps[0]:,} - {steps[-1]:,}\n"

        if len(steps) > 1:
            intervals = [steps[i+1] - steps[i] for i in range(len(steps)-1)]
            doc += f"- **Intervalo promedio**: {np.mean(intervals):,.0f} pasos\n"

        doc += f"- **Primeros 5 pasos**: {steps[:5]}\n"
        doc += f"- **Últimos 5 pasos**: {steps[-5:]}\n"

    sac_count = len(get_checkpoint_steps('SAC'))
    ppo_count = len(get_checkpoint_steps('PPO'))
    a2c_count = len(get_checkpoint_steps('A2C'))

    doc += f"""

## 📈 Gráficas Generadas

1. **training_steps_timeline.png**
   - Evolución temporal de pasos para cada agente
   - Permite visualizar el progreso relativo

2. **checkpoint_count_by_agent.png**
   - Comparativa de cantidad de checkpoints guardados
   - Indica frecuencia de guardado

3. **checkpoint_intervals.png**
   - Intervalos entre checkpoints para cada agente
   - Muestra patrón de guardado

4. **cumulative_training_steps.png**
   - Acumulación total de pasos de entrenamiento
   - Visualiza progreso total

5. **checkpoint_summary_table.png**
   - Tabla resumen con estadísticas por agente
   - Información consolidada fácil de consultar

## 🔍 Interpretación

- **SAC**: {sac_count} checkpoints totales
- **PPO**: {ppo_count} checkpoints totales
- **A2C**: {a2c_count} checkpoints totales

El número de checkpoints refleja:
- Agentes que entrenaron más pasos
- Frecuencia de guardado configurada
- Duración del entrenamiento

## 🔄 Regenerar Gráficas

```bash
python scripts/generar_graficas_training_steps.py
```

## 📊 Datos de Origen

- **Fuente**: `analyses/oe3/training/checkpoints/{{agent}}/`
- **Formato**: .zip (modelos entrenados stable-baselines3)
- **Período**: Entrenamiento completo desde inicio hasta final
- **Resolución**: 300 DPI (publicación profesional)

---
**Generado**: 2026-01-29
**Versión**: v1.0
"""

    doc_file = OUTPUT_DIR / 'TRAINING_STEPS_DOCUMENTATION.md'
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write(doc)

    print(f"✅ {doc_file.name}")


def main() -> None:
    """Función principal"""
    print("\n" + "="*70)
    print("  GENERANDO GRAFICAS DE ENTRENAMIENTO PASO A PASO (STEP-BY-STEP)")
    print("="*70)

    # Verificar que existen checkpoints
    if not CHECKPOINT_DIR.exists():
        print("[ERROR] No se encontro directorio de checkpoints")
        return

    # Generar gráficas
    plot_training_steps_timeline()
    plot_checkpoint_count_by_agent()
    plot_step_intervals()
    plot_cumulative_steps()
    generate_checkpoint_summary_table()
    create_checkpoint_documentation()

    print("\n" + "="*70)
    print("OK GRAFICAS DE ENTRENAMIENTO GENERADAS EXITOSAMENTE")
    print("="*70)
    print(f"\nUbicacion: analyses/oe3/training/graphics/step_by_step")
    print(f"Total de graficas: 5")
    print(f"Documentacion: TRAINING_STEPS_DOCUMENTATION.md")
    print("\nRegenerar:")
    print("   python scripts/generar_graficas_training_steps.py")
    print()


if __name__ == '__main__':
    main()
