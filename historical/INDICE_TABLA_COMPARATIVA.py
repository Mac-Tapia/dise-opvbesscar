#!/usr/bin/env python3
"""
ÍNDICE DE CÓDIGO - DÓNDE ENCONTRAR CADA COMPONENTE DE LA TABLA COMPARATIVA

Este documento indica la ubicación exacta de cada función y variable relacionada
con la generación de la tabla comparativa de agentes y métricas de entrenamiento.
"""

# ============================================================================
# TABLA COMPARATIVA DE AGENTES - UBICACIONES
# ============================================================================

"""
PREGUNTA: "¿Verifica si genera la tabla comparativa?"

RESPUESTA: SÍ

UBICACIÓN PRINCIPAL:
  Archivo: scripts/run_oe3_co2_table.py
  Función: main() línea 24-55

FLUJO:
  1. Cargar config                    → load_all()
  2. Cargar summary JSON              → load_summary()
  3. Computar comparación agentes     → compute_agent_comparison()
  4. Escribir salidas Markdown        → write_outputs()

SALIDA:
  Archivo: analyses/oe3/AGENT_COMPARISON.md
  Contiene: Ranking de SAC, PPO, A2C con CO₂ y autosuficiencia
"""

# PASO 1: Script de entrada
# =====================================================================
# Archivo: scripts/run_oe3_co2_table.py
# Línea:   24-55

def main_location():
    """
    def main() -> None:
        ap = argparse.ArgumentParser()
        ap.add_argument("--config", default="configs/default.yaml")
        args = ap.parse_args()

        setup_logging()
        cfg, rp = load_all(args.config)

        summary_path = rp.outputs_dir / "oe3" / "simulations" / "simulation_summary.json"
        summary = load_summary(summary_path)

        factors = EmissionsFactors(...)
        city_baseline = CityBaseline(...)

        # ← AQUÍ SE GENERA LA TABLA COMPARATIVA
        agent_comparison = compute_agent_comparison(summary, factors)

        # ← Y SE ESCRIBE AL ARCHIVO
        write_outputs(df, rp.analyses_dir / "oe3", agent_comparison, ...)
    """
    pass


# PASO 2: Función de computación
# =====================================================================
# Archivo: src/iquitos_citylearn/oe3/co2_table.py
# Función: compute_agent_comparison()
# Línea:   35-98

def compute_agent_comparison_location():
    """
    def compute_agent_comparison(summary: dict[str, Any],
                                 factors: EmissionsFactors) -> pd.DataFrame:
        '''Compara todos los agentes entrenados para seleccionar el mejor.

        Evaluación multicriterio basada en:
        1. Emisiones CO₂ (peso alto)
        2. Costo eléctrico
        3. Autoconsumo solar
        4. Satisfacción EV
        5. Estabilidad de red
        '''

        pv_results = summary.get("pv_bess_results", {})
        rows: List[Dict[str, Any]] = []

        for agent_name, res in pv_results.items():
            # ← AQUÍ SE EXTRAEN MÉTRICAS DE CADA AGENTE
            ev_kwh_y = annualize(res["ev_charging_kwh"], res["simulated_years"])
            ...

            # ← AQUÍ SE CALCULA AUTOSUFICIENCIA
            autosuficiencia = 100.0 * (1 - import_kwh_y / max(...))

            # ← AQUÍ SE EXTRAEN REWARDS MULTIOBJETIVO
            r_co2 = res.get("reward_co2_mean", 0.0)
            r_cost = res.get("reward_cost_mean", 0.0)
            r_solar = res.get("reward_solar_mean", 0.0)
            r_ev = res.get("reward_ev_mean", 0.0)
            r_grid = res.get("reward_grid_mean", 0.0)
            r_total = res.get("reward_total_mean", 0.0)

            # ← AQUÍ SE CONSTRUYE FILA DE LA TABLA
            rows.append({
                "agente": agent_name,
                "ev_kwh_anual": ev_kwh_y,
                "pv_kwh_anual": pv_kwh_y,
                "import_red_kwh_anual": import_kwh_y,
                "export_red_kwh_anual": export_kwh_y,
                "ev_import_red_kwh_anual": ev_import_kwh_y,
                "carbon_kg_anual": carbon_kg_y,
                "carbon_tco2_anual": carbon_kg_y / 1000.0,
                "autosuficiencia_pct": autosuficiencia,
                # Multiobjetivo
                "mo_priority": mo_priority,
                "reward_co2": r_co2,
                "reward_cost": r_cost,
                "reward_solar": r_solar,
                "reward_ev": r_ev,
                "reward_grid": r_grid,
                "reward_total": r_total,
            })

        df = pd.DataFrame(rows)

        # ← AQUÍ SE ORDENA POR CRITERIOS (CO2 PRIMERO)
        df = df.sort_values(
            ["carbon_kg_anual", "autosuficiencia_pct", "reward_total"],
            ascending=[True, False, False],
        ).reset_index(drop=True)
        df["ranking"] = range(1, len(df) + 1)

        return df
    """
    pass


# PASO 3: Escritura de salida
# =====================================================================
# Archivo: src/iquitos_citylearn/oe3/co2_table.py
# Función: write_outputs()
# Línea:   376-445

def write_outputs_location():
    """
    def write_outputs(
        df: pd.DataFrame,
        out_dir: Path,
        agent_comparison: pd.DataFrame = None,
        breakdown: pd.DataFrame = None,
        control_comparison: pd.DataFrame = None,
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)

        # ← AQUÍ SE ESCRIBE TABLA PRINCIPAL
        (out_dir / "CO2_REDUCTION_TABLE.md").write_text(...)

        # ← AQUÍ SE ESCRIBE TABLA COMPARATIVA (LA QUE BUSCAS)
        if agent_comparison is not None and len(agent_comparison) > 0:
            md = _build_agent_comparison_markdown(agent_comparison)
            (out_dir / "AGENT_COMPARISON.md").write_text(md)
    """
    pass


# ============================================================================
# MÉTRICAS DE ENTRENAMIENTO - UBICACIONES
# ============================================================================

"""
PREGUNTA: "¿Está considerando las métricas de entrenamiento?"

RESPUESTA: SÍ

UBICACIONES PRINCIPALES:

1. DEFINICIÓN DE MÉTRICAS
   Archivo: src/iquitos_citylearn/oe3/simulate.py
   Línea:   65-83
   Clase:   SimulationResult (dataclass)

2. CÁLCULO DE COMPONENTES DE RECOMPENSA
   Archivo: src/iquitos_citylearn/oe3/rewards.py
   Línea:   127-263
   Función: MultiObjectiveReward.compute()

3. REGISTRO POR EPISODIO
   Archivo: src/iquitos_citylearn/oe3/simulate.py
   Línea:   900-930
   Dentro:  def simulate()

4. ALMACENAMIENTO EN JSON
   Archivo: src/iquitos_citylearn/oe3/simulate.py
   Línea:   915-935
   Variable: mo_metrics

5. VISUALIZACIÓN EN TABLA
   Archivo: src/iquitos_citylearn/oe3/co2_table.py
   Línea:   410-415
   Función: _build_agent_comparison_markdown()
"""


# ============================================================================
# 1. DEFINICIÓN DE MÉTRICAS
# ============================================================================
# Archivo: src/iquitos_citylearn/oe3/simulate.py
# Línea:   65-83

def metrics_definition_location():
    """
    @dataclass(frozen=True)
    class SimulationResult:
        agent: str
        steps: int
        seconds_per_time_step: int
        simulated_years: float
        grid_import_kwh: float
        grid_export_kwh: float
        net_grid_kwh: float
        ev_charging_kwh: float
        building_load_kwh: float
        pv_generation_kwh: float
        carbon_kg: float
        results_path: str
        timeseries_path: str
        # ← MÉTRICAS MULTIOBJETIVO
        multi_objective_priority: str = "balanced"
        reward_co2_mean: float = 0.0      # ← MÉTRICA 1
        reward_cost_mean: float = 0.0     # ← MÉTRICA 2
        reward_solar_mean: float = 0.0    # ← MÉTRICA 3
        reward_ev_mean: float = 0.0       # ← MÉTRICA 4
        reward_grid_mean: float = 0.0     # ← MÉTRICA 5
        reward_total_mean: float = 0.0    # ← MÉTRICA 6
    """
    pass


# ============================================================================
# 2. CÁLCULO DE COMPONENTES DE RECOMPENSA
# ============================================================================
# Archivo: src/iquitos_citylearn/oe3/rewards.py
# Función: MultiObjectiveReward.compute()
# Línea:   127-263

def compute_reward_components_location():
    """
    def compute(self, ...) -> Tuple[float, Dict[str, float]]:
        components = {}
        is_peak = hour in self.context.peak_hours

        # 1. Recompensa CO₂ (minimizar)
        # Línea: 156-169
        co2_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh
        if is_peak:
            r_co2 = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline_peak)
        else:
            r_co2 = 1.0 - 1.0 * min(1.0, grid_import_kwh / co2_baseline_offpeak)
        r_co2 = np.clip(r_co2, -1.0, 1.0)
        components["r_co2"] = r_co2  # ← ALMACENADO

        # 2. Recompensa Costo (minimizar)
        # Línea: 171-176
        cost_usd = (grid_import_kwh - grid_export_kwh) * self.context.tariff_usd_per_kwh
        r_cost = 1.0 - 2.0 * min(1.0, max(0, cost_usd) / cost_baseline)
        r_cost = np.clip(r_cost, -1.0, 1.0)
        components["r_cost"] = r_cost  # ← ALMACENADO

        # 3. Recompensa Autoconsumo Solar (maximizar)
        # Línea: 178-188
        if solar_generation_kwh > 0:
            solar_used = min(solar_generation_kwh, ev_charging_kwh + ...)
            self_consumption_ratio = solar_used / solar_generation_kwh
            r_solar = 2.0 * self_consumption_ratio - 1.0
        else:
            r_solar = 0.0
        r_solar = np.clip(r_solar, -1.0, 1.0)
        components["r_solar"] = r_solar  # ← ALMACENADO

        # 4. Recompensa Satisfacción EV (maximizar)
        # Línea: 190-199
        ev_satisfaction = min(1.0, ev_soc_avg / self.context.ev_soc_target)
        r_ev = 2.0 * ev_satisfaction - 1.0
        if solar_generation_kwh > 0 and ev_charging_kwh > 0:
            solar_ev_ratio = min(1.0, ev_charging_kwh / solar_generation_kwh)
            r_ev += 0.1 * solar_ev_ratio
        r_ev = np.clip(r_ev, -1.0, 1.0)
        components["r_ev"] = r_ev  # ← ALMACENADO

        # 5. Recompensa Estabilidad Red (minimizar picos)
        # Línea: 201-213
        demand_ratio = grid_import_kwh / max(1.0, self.context.peak_demand_limit_kw)
        if is_peak:
            r_grid = 1.0 - 4.0 * min(1.0, demand_ratio)
        else:
            r_grid = 1.0 - 2.0 * min(1.0, demand_ratio)
        r_grid = np.clip(r_grid, -1.0, 1.0)
        components["r_grid"] = r_grid  # ← ALMACENADO

        # Recompensa total ponderada
        # Línea: 240-251
        reward = (
            self.weights.co2 * r_co2 +
            self.weights.cost * r_cost +
            self.weights.solar * r_solar +
            self.weights.ev_satisfaction * r_ev +
            self.weights.grid_stability * r_grid +
            0.10 * soc_penalty
        )
        reward = np.clip(reward, -1.0, 1.0)
        components["reward_total"] = reward  # ← ALMACENADO

        self._reward_history.append(components)
        return reward, components
    """
    pass


# ============================================================================
# 3. REGISTRO POR EPISODIO
# ============================================================================
# Archivo: src/iquitos_citylearn/oe3/simulate.py
# Función: def simulate() -> Dict[str, Any]
# Línea:   900-935

def episode_recording_location():
    """
    def simulate(...) -> Dict[str, Any]:
        ...
        while episode < episodes:
            obs, info = env.reset()
            rewards_per_step = []
            mo_rewards = {
                "r_co2": [],
                "r_cost": [],
                "r_solar": [],
                "r_ev": [],
                "r_grid": [],
                "reward_total": []
            }

            for step in range(8760):
                action, _ = agent.predict(obs, deterministic=False)
                obs, reward, terminated, truncated, info = env.step(action)

                # ← AQUÍ SE REGISTRAN LOS REWARDS CADA TIMESTEP
                mo_rewards["r_co2"].append(wrapper.last_mo_reward.get("r_co2", 0))
                mo_rewards["r_cost"].append(wrapper.last_mo_reward.get("r_cost", 0))
                mo_rewards["r_solar"].append(wrapper.last_mo_reward.get("r_solar", 0))
                mo_rewards["r_ev"].append(wrapper.last_mo_reward.get("r_ev", 0))
                mo_rewards["r_grid"].append(wrapper.last_mo_reward.get("r_grid", 0))
                mo_rewards["reward_total"].append(reward)

            # ← AQUÍ SE CALCULA EL PROMEDIO DEL EPISODIO
            mo_metrics = {
                "r_co2_mean": float(np.mean(mo_rewards["r_co2"])),      # ← MÉTRICA
                "r_cost_mean": float(np.mean(mo_rewards["r_cost"])),    # ← MÉTRICA
                "r_solar_mean": float(np.mean(mo_rewards["r_solar"])),  # ← MÉTRICA
                "r_ev_mean": float(np.mean(mo_rewards["r_ev"])),        # ← MÉTRICA
                "r_grid_mean": float(np.mean(mo_rewards["r_grid"])),    # ← MÉTRICA
                "reward_total_mean": float(np.mean(mo_rewards["reward_total"])),  # ← MÉTRICA
            }

            # ← AQUÍ SE ASIGNAN AL SimulationResult
            result = SimulationResult(
                agent=agent_name,
                steps=episode * 8760,
                ...,
                reward_co2_mean=float(mo_metrics["r_co2_mean"]),      # ← ASIGNADO
                reward_cost_mean=float(mo_metrics["r_cost_mean"]),    # ← ASIGNADO
                reward_solar_mean=float(mo_metrics["r_solar_mean"]),  # ← ASIGNADO
                reward_ev_mean=float(mo_metrics["r_ev_mean"]),        # ← ASIGNADO
                reward_grid_mean=float(mo_metrics["r_grid_mean"]),    # ← ASIGNADO
                reward_total_mean=float(mo_metrics["reward_total_mean"]),  # ← ASIGNADO
            )

            episode += 1
    """
    pass


# ============================================================================
# 4. ALMACENAMIENTO EN JSON
# ============================================================================
# Archivo: src/iquitos_citylearn/oe3/simulate.py
# Función: def simulate()
# Línea:   915-950

def json_storage_location():
    """
    def simulate(...) -> Dict[str, Any]:
        ...
        all_results = {}

        for result in results_list:
            all_results[result.agent] = {
                "agent": result.agent,
                "steps": result.steps,
                "simulated_years": result.simulated_years,
                ...
                # ← AQUÍ SE ALMACENAN LAS MÉTRICAS EN JSON
                "reward_co2_mean": result.reward_co2_mean,      # ← EN JSON
                "reward_cost_mean": result.reward_cost_mean,    # ← EN JSON
                "reward_solar_mean": result.reward_solar_mean,  # ← EN JSON
                "reward_ev_mean": result.reward_ev_mean,        # ← EN JSON
                "reward_grid_mean": result.reward_grid_mean,    # ← EN JSON
                "reward_total_mean": result.reward_total_mean,  # ← EN JSON
            }

        summary = {
            "pv_bess_results": all_results,  # ← AQUÍ SE GUARDA LA COMPARACIÓN
            "best_agent": best_agent,
            "best_result": best_result,
            ...
        }

        # ← AQUÍ SE ESCRIBE AL ARCHIVO JSON
        (output_dir / "simulation_summary.json").write_text(
            json.dumps(summary, indent=2)
        )
    """
    pass


# ============================================================================
# 5. VISUALIZACIÓN EN TABLA MARKDOWN
# ============================================================================
# Archivo: src/iquitos_citylearn/oe3/co2_table.py
# Función: _build_agent_comparison_markdown()
# Línea:   410-415

def markdown_visualization_location():
    """
    def _build_agent_comparison_markdown(agent_comparison: pd.DataFrame) -> str:
        md = [
            "# Comparación de Agentes Inteligentes\\n",
            "\\n",
            "| Ranking | Agente | CO₂ (kg/y) | CO₂ (tCO₂/y) | Autosuficiencia (%) | "
            "R_CO₂ | R_Solar | R_Cost | R_EV | R_Grid | R_Total |\\n",
            "|---------|--------|-----------|------------|------------------|"
            "-------|---------|--------|------|--------|---------|\\n",
        ]

        for _, row in agent_comparison.iterrows():
            # ← AQUÍ SE ESCRIBEN LOS VALORES DE LA TABLA
            md.append(
                f"| {row['ranking']} | {row['agente']} | "
                f"{row['carbon_kg_anual']:,.0f} | {row['carbon_tco2_anual']:.2f} | "
                f"{row['autosuficiencia_pct']:.1f} | "
                f"{row.get('reward_co2', 0):.3f} | "        # ← MÉTRICA EN TABLA
                f"{row.get('reward_solar', 0):.3f} | "      # ← MÉTRICA EN TABLA
                f"{row.get('reward_cost', 0):.3f} | "       # ← MÉTRICA EN TABLA
                f"{row.get('reward_ev', 0):.3f} | "         # ← MÉTRICA EN TABLA
                f"{row.get('reward_grid', 0):.3f} | "       # ← MÉTRICA EN TABLA
                f"{row.get('reward_total', 0):.3f} |\\n"    # ← MÉTRICA EN TABLA
            )

        return "".join(md)
    """
    pass


# ============================================================================
# OBJETIVO PRINCIPAL - UBICACIONES
# ============================================================================

"""
PREGUNTA: "¿Su objetivo principal es Seleccionar el agente inteligente..."

RESPUESTA: SÍ

UBICACIONES PRINCIPALES:

1. CRITERIO DE SELECCIÓN (CO₂ PRIMARY)
   Archivo: src/iquitos_citylearn/oe3/co2_table.py
   Línea:   96-98
   Código:  df.sort_values(["carbon_kg_anual", ...], ascending=[True, ...])

2. CONTEXTO DE IQUITOS
   Archivo: src/iquitos_citylearn/oe3/rewards.py
   Línea:   72-87
   Clase:   IquitosContext (factor CO₂ = 0.4521 kg/kWh)

3. FUNCIÓN MULTIOBJETIVO CON CO₂ PRINCIPAL
   Archivo: src/iquitos_citylearn/oe3/rewards.py
   Línea:   30-39
   Clase:   MultiObjectiveWeights (co2=0.50)

4. CÁLCULO DE REDUCCIÓN CO₂ CUANTIFICABLE
   Archivo: src/iquitos_citylearn/oe3/co2_table.py
   Línea:   154-171
   Función: compute_table() → reduction_tco2_y, contribution_pct
"""


# ============================================================================
# EJEMPLO DE SALIDA ESPERADA
# ============================================================================

"""
TABLA COMPARATIVA GENERADA (AGENT_COMPARISON.md):

# Comparación de Agentes Inteligentes

| Ranking | Agente | CO₂ (kg/y) | CO₂ (tCO₂/y) | Autosuficiencia (%) | R_CO₂ | R_Solar | R_Cost | R_EV | R_Grid | R_Total |
|---------|--------|-----------|------------|------------------|-------|---------|--------|------|--------|---------|
| 1 | SAC | 2,100,000 | 2.1 | 72.3 | 0.85 | 0.42 | 0.28 | 0.51 | 0.64 | 0.54 |
| 2 | PPO | 2,400,000 | 2.4 | 65.1 | 0.78 | 0.35 | 0.25 | 0.48 | 0.58 | 0.49 |
| 3 | A2C | 2,800,000 | 2.8 | 58.2 | 0.71 | 0.28 | 0.22 | 0.42 | 0.52 | 0.43 |

INTERPRETACIÓN:
- SAC seleccionado como AGENTE ÓPTIMO (menor CO₂ anual)
- Todas las métricas de entrenamiento visibles (6 componentes)
- Reducción cuantificable: 6.4 tCO₂/año vs baseline combustión
- Contribución ciudad: 0.46% del sector transporte Iquitos
"""


# ============================================================================
# COMANDOS PARA GENERAR LA TABLA
# ============================================================================

"""
CUANDO ENTRENAMIENTO TERMINE:

# 1. Generar tabla comparativa
$ cd d:\\diseñopvbesscar
$ .\\\\.\\venv\\Scripts\\python.exe -m scripts.run_oe3_co2_table --config configs/default.yaml

# 2. Salida esperada
✓ analyses/oe3/CO2_REDUCTION_TABLE.md
✓ analyses/oe3/AGENT_COMPARISON.md     ← LA TABLA QUE BUSCAS
✓ analyses/oe3/CONTROL_COMPARISON.md
✓ analyses/oe3/BREAKDOWN_METRICS.md

# 3. Ver tabla en archivo
$ cat analyses/oe3/AGENT_COMPARISON.md

# 4. Ver JSON con datos crudos
$ cat outputs/oe3/simulations/simulation_summary.json | python -m json.tool
"""


if __name__ == "__main__":
    print(__doc__)
    print("\n[ÍNDICE DE UBICACIONES COMPLETADO]")
    print("Para ver el contenido de cada función, ver los docstrings anteriores")
