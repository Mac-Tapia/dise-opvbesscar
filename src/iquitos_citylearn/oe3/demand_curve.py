"""
VISUALIZADOR DE CURVA DE DEMANDA ESTABLE
=========================================

Muestra cómo mantener demanda sin variaciones bruscas:
- Demanda real del mall
- Demanda de EVs
- Demanda total
- Suavización mediante control RL
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class DemandCurveAnalyzer:
    """
    Analiza y visualiza curvas de demanda.
    """

    def __init__(self, peak_hours: Tuple[int, int] = (18, 21)):
        """
        Inicializar analizador.

        Args:
            peak_hours: Horas de pico (start, end)
        """
        self.peak_hours = peak_hours
        self.demand_history: List[float] = []
        self.ev_demand_history: List[float] = []

    def get_typical_mall_demand(self, hour: int) -> float:
        """
        Obtener demanda típica del mall por hora.

        Iquitos EV Mall: demanda variable según ocupación

        Args:
            hour: Hora del día (0-23)

        Returns:
            Demanda en kW
        """
        # Perfil típico de mall
        # Mañana: baja (5-9am)
        # Mediodía: media (12-2pm)
        # Tarde: alta (3-6pm)
        # Pico: muy alta (6-9pm)
        # Noche: baja (10pm-5am)

        if hour < 5 or hour >= 23:
            return 80.0  # Nocturno bajo
        elif 5 <= hour < 9:
            return 150.0  # Mañana temprana
        elif 9 <= hour < 12:
            return 200.0  # Mañana
        elif 12 <= hour < 15:
            return 180.0  # Mediodía
        elif 15 <= hour < 18:
            return 220.0  # Tarde
        elif self.peak_hours[0] <= hour < self.peak_hours[1]:
            return 350.0  # PICO (6-9pm)
        else:
            return 250.0  # Resto tarde

    def get_typical_ev_demand(self, hour: int, occupancy_rate: float = 0.5) -> float:
        """
        Obtener demanda típica de EVs por hora.

        Mayor en:
        - Mañana (5-9am): usuarios llegan
        - Tarde (4-8pm): usuarios van al trabajo
        - Noche (8pm-10pm): usuarios salen

        Args:
            hour: Hora del día (0-23)
            occupancy_rate: Tasa de ocupación de chargers [0, 1]

        Returns:
            Demanda en kW
        """
        # Perfil de ocupación EV
        if hour < 6 or hour >= 23:
            base_demand = 10.0  # Nocturnos bajo
        elif 6 <= hour < 9:
            base_demand = 80.0  # Mañana (usuarios llegan)
        elif 9 <= hour < 12:
            base_demand = 50.0  # Mañana media
        elif 12 <= hour < 15:
            base_demand = 40.0  # Mediodía (menos carga)
        elif 15 <= hour < 18:
            base_demand = 100.0  # Tarde (usuarios salen)
        elif 18 <= hour < 21:
            base_demand = 150.0  # Pico (muchos cargando)
        else:
            base_demand = 60.0  # Noche

        return base_demand * occupancy_rate

    def calculate_total_demand(
        self,
        mall_demand_kw: float,
        ev_demand_kw: float,
    ) -> float:
        """
        Calcular demanda total (mall + EVs).

        Returns:
            Demanda total en kW
        """
        return mall_demand_kw + ev_demand_kw

    def calculate_demand_variation(
        self,
        demands: List[float],
    ) -> Dict[str, float]:
        """
        Calcular métricas de variación de demanda.

        Returns:
            {
                "mean": demanda promedio,
                "std": desviación estándar,
                "cv": coeficiente de variación,
                "max": máximo,
                "min": mínimo,
                "ramp_max": cambio máximo entre steps,
            }
        """
        demands_array = np.array(demands)

        ramps = np.abs(np.diff(demands_array))

        return {
            "mean": float(np.mean(demands_array)),
            "std": float(np.std(demands_array)),
            "cv": float(np.std(demands_array) / np.mean(demands_array)) if np.mean(demands_array) > 0 else 0,
            "max": float(np.max(demands_array)),
            "min": float(np.min(demands_array)),
            "ramp_max": float(np.max(ramps)) if len(ramps) > 0 else 0,
            "ramp_mean": float(np.mean(ramps)) if len(ramps) > 0 else 0,
        }

    def smooth_demand(
        self,
        demands: List[float],
        window_size: int = 3,
    ) -> List[float]:
        """
        Suavizar curva de demanda usando media móvil.

        Args:
            demands: Lista de demandas por hora
            window_size: Tamaño de ventana para promedio móvil

        Returns:
            Lista suavizada
        """
        if len(demands) < window_size:
            return demands

        kernel = np.ones(window_size) / window_size
        demands_array = np.array(demands)

        # Padding para mantener mismo tamaño
        smoothed = np.convolve(
            np.concatenate([np.full(window_size//2, demands[0]), demands_array, np.full(window_size//2, demands[-1])]),
            kernel,
            mode='valid'
        )

        return smoothed[:len(demands)].tolist()

    def print_demand_curve(
        self,
        demand_data: Dict[str, List[float]],
        title: str = "CURVA DE DEMANDA",
    ) -> None:
        """
        Imprimir curva de demanda con ASCII art.

        Args:
            demand_data: {"baseline": [...], "controlled": [...], ...}
            title: Título del gráfico
        """
        print(f"\n{'='*120}")
        print(f"{title:^120}")
        print(f"{'='*120}\n")

        # Encontrar máximo para escala
        all_values = np.concatenate([np.array(v) for v in demand_data.values()])
        max_value = np.max(all_values)

        # Altura del gráfico
        graph_height = 20
        graph_width = 24  # Una columna por hora (24 horas)

        # Crear gráfico vacío
        graph = [[' ' for _ in range(graph_width)] for _ in range(graph_height)]

        # Colores por tipo de demanda
        symbols = {
            "baseline": '█',
            "controlled": '▓',
            "smoothed": '░',
        }

        # Dibujar para cada tipo
        for demand_type, demands in demand_data.items():
            if demand_type not in symbols:
                continue

            symbol = symbols[demand_type]

            for hour, value in enumerate(demands):
                # Normalizar a altura de gráfico
                height = int((value / max_value) * (graph_height - 1)) if max_value > 0 else 0
                height = min(height, graph_height - 1)

                # Dibujar columna (de abajo hacia arriba)
                for y in range(graph_height - 1 - height, graph_height):
                    if graph[y][hour] == ' ':
                        graph[y][hour] = symbol
                    else:
                        # Sobreposición: usar carácter mixto
                        graph[y][hour] = '▓'

        # Imprimir gráfico con etiquetas
        print(f"{'Potencia (kW)':>10} │", end='')
        print(''.join(str(i).rjust(1) if i % 2 == 0 else ' ' for i in range(24)), end='')
        print(f" │ {'Hora':>5}")
        print('─' * 12 + '┼' + '─' * 28 + '┼' + '─' * 10)

        for y in range(graph_height):
            label_value = int((graph_height - 1 - y) / (graph_height - 1) * max_value)
            print(f"{label_value:>6} kW │", end='')
            print(''.join(graph[y]), end='')
            print("│")

        print('─' * 12 + '┼' + '─' * 28 + '┼' + '─' * 10)
        print(f"{'':>10} │ ", end='')
        print(' '.join(str(h).zfill(2) for h in range(0, 24, 2)), end='')
        print(" │")
        print('=' * 60)

        # Leyenda
        print("\nLeyenda:")
        for demand_type, symbol in symbols.items():
            if demand_type in demand_data:
                stats = self.calculate_demand_variation(demand_data[demand_type])
                print(
                    f"  {symbol} {demand_type:>12}: "
                    f"μ={stats['mean']:.0f} kW, σ={stats['std']:.1f}, CV={stats['cv']:.2f}, "
                    f"Ramp Max={stats['ramp_max']:.0f} kW/h"
                )

        print(f"\n{'='*120}\n")

    def compare_control_strategies(
        self,
        hours: List[int],
        mall_demand: List[float],
        ev_demand_uncontrolled: List[float],
        ev_demand_controlled: List[float],
    ) -> None:
        """
        Comparar demanda sin control vs con control RL.

        Muestra cómo el control RL suaviza picos.
        """
        # Calcular demandas totales
        baseline = [m + e for m, e in zip(mall_demand, ev_demand_uncontrolled)]
        controlled = [m + e for m, e in zip(mall_demand, ev_demand_controlled)]
        smoothed = self.smooth_demand(controlled, window_size=3)

        print(f"\n{'='*120}")
        print(f"{'COMPARACIÓN: SIN CONTROL vs CON CONTROL RL':^120}")
        print(f"{'='*120}\n")

        print(f"{'Hora':<8} {'Pico':<8} {'Sin Ctrl':<12} {'Con Ctrl':<12} {'Suavizado':<12} {'Mejora':<12}")
        print(f"{'-'*120}")

        for hour, base, ctrl, smooth in zip(hours, baseline, controlled, smoothed):
            is_peak = self.peak_hours[0] <= hour < self.peak_hours[1]
            peak_mark = "🔴" if is_peak else "  "

            improvement = ((base - ctrl) / base * 100) if base > 0 else 0
            improvement_mark = f"{improvement:>+6.1f}%"

            if improvement > 10:
                improvement_mark += " ✓"
            elif improvement < -10:
                improvement_mark += " ✗"

            print(
                f"{hour:>2}:00   {peak_mark}  "
                f"{base:>8.0f} kW  "
                f"{ctrl:>8.0f} kW  "
                f"{smooth:>8.0f} kW  "
                f"{improvement_mark}"
            )

        # Estadísticas
        stats_baseline = self.calculate_demand_variation(baseline)
        stats_controlled = self.calculate_demand_variation(controlled)
        stats_smoothed = self.calculate_demand_variation(smoothed)

        print(f"\n{'-'*120}")
        print(f"{'Métrica':<20} {'Sin Control':<20} {'Con Control':<20} {'Suavizado':<20}")
        print(f"{'-'*120}")
        print(
            f"{'Demanda Promedio':<20} {stats_baseline['mean']:>8.0f} kW        "
            f"{stats_controlled['mean']:>8.0f} kW        "
            f"{stats_smoothed['mean']:>8.0f} kW"
        )
        print(
            f"{'Desv. Estándar':<20} {stats_baseline['std']:>8.0f} kW        "
            f"{stats_controlled['std']:>8.0f} kW        "
            f"{stats_smoothed['std']:>8.0f} kW"
        )
        print(
            f"{'Coef. Variación':<20} {stats_baseline['cv']:>8.2f}        "
            f"{stats_controlled['cv']:>8.2f}        "
            f"{stats_smoothed['cv']:>8.2f}"
        )
        print(
            f"{'Ramp Máx':<20} {stats_baseline['ramp_max']:>8.0f} kW/h    "
            f"{stats_controlled['ramp_max']:>8.0f} kW/h    "
            f"{stats_smoothed['ramp_max']:>8.0f} kW/h"
        )
        print(
            f"{'Ramp Promedio':<20} {stats_baseline['ramp_mean']:>8.0f} kW/h    "
            f"{stats_controlled['ramp_mean']:>8.0f} kW/h    "
            f"{stats_smoothed['ramp_mean']:>8.0f} kW/h"
        )

        print(f"\n{'='*120}\n")

        # Evaluación
        print("EVALUACIÓN:")
        print(f"  • CV Mejorado: {(1 - stats_controlled['cv'] / stats_baseline['cv']) * 100:+.1f}%")
        print(f"  • Ramps Reducidos: {(1 - stats_controlled['ramp_max'] / stats_baseline['ramp_max']) * 100:+.1f}%")
        print(f"  • Estabilidad: {'✓ MEJORADA' if stats_controlled['cv'] < stats_baseline['cv'] else '✗ IGUAL'}\n")
