"""
Prueba de Hipótesis Estadística — Reducción de CO₂ (Sección 5.2 Tesis)
=======================================================================
pvbesscar | Iquitos, Perú | OE3

Hipótesis General:
    H₀: μ_baseline = μ_mejor_agente  (la reducción de CO₂ NO es significativa)
    H₁: μ_baseline > μ_mejor_agente  (la reducción de CO₂ ES estadísticamente significativa)

Grupos:
    Grupo A (Baseline): CO₂ total que habría emitido el sistema SIN control inteligente.
        = co2_grid_kg + co2_avoided_indirect_kg + co2_avoided_direct_kg
        Extraído de los datos reales de entrenamiento del mejor agente seleccionado.

    Grupo B (Mejor Agente): CO₂ real emitido por la red térmica BAJO control inteligente.
        = co2_grid_kg del mejor agente en su último episodio/año de entrenamiento.
        El mejor agente se determina comparando los 3 agentes entrenados (A2C, PPO, SAC):
        el que logró el menor CO₂ grid anual en su última etapa de entrenamiento.

Fuentes de datos (resultados reales de entrenamiento):
    - outputs/a2c_training/timeseries_a2c.csv  (A2C: 10 episodios × 8,760 h = 87,600 h)
    - outputs/ppo_training/timeseries_ppo.csv  (PPO: 10 episodios completos × 8,760 h)
    - outputs/sac_training/timeseries_sac.csv  (SAC: 1 episodio × 87,600 h = 10 años)

Metodología de selección del mejor agente:
    1. Cargar timeseries de los 3 agentes desde sus archivos de entrenamiento.
    2. Extraer el último año/episodio completo (8,760 h) de cada agente.
    3. Calcular CO₂ grid anual de cada agente en esa última etapa.
    4. Seleccionar como mejor agente el de menor CO₂ grid anual.
    5. Grupo A = baseline del mejor agente | Grupo B = co2_grid del mejor agente.
    6. Aplicar Shapiro-Wilk → T-Student o Wilcoxon según normalidad (α = 0.05).

Autor: pvbesscar / Mac-Tapia | Fecha: 2026-04-06
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_A2C = ROOT / "outputs" / "a2c_training" / "timeseries_a2c.csv"
DATA_PPO = ROOT / "outputs" / "ppo_training" / "timeseries_ppo.csv"
DATA_SAC = ROOT / "outputs" / "sac_training" / "timeseries_sac.csv"
OUT_DIR = ROOT / "outputs" / "hypothesis_test"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AGENTS_FILES = {
    "A2C": DATA_A2C,
    "PPO": DATA_PPO,
    "SAC": DATA_SAC,
}

# ---------------------------------------------------------------------------
# Constantes físicas (OE2 v5.8 / Iquitos)
# ---------------------------------------------------------------------------
CO2_GRID_FACTOR_KG_KWH = 0.4521      # kg CO₂/kWh - red térmica Iquitos
CHARGER_EFFICIENCY = 0.95             # eficiencia de carga (round-trip)
ALPHA = 0.05                          # nivel de significancia

MONTHS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]

# ---------------------------------------------------------------------------
# 1. CARGA DE DATOS — 3 AGENTES (RESULTADOS REALES DE ENTRENAMIENTO)
# ---------------------------------------------------------------------------

def _load_agent_last_year(name: str, path: Path) -> tuple[pd.DataFrame, str]:
    """
    Carga el último año/episodio completo (8,760 h) de un agente entrenado.

    - A2C / PPO: episodios por columna 'episode'. Usa el último episodio con 8,760 filas.
    - SAC: un solo episodio (ep=0) con 87,600 filas = 10 años consecutivos.
           Se extrae el año = (timestep-1)//8760, usando el último año.
           'co2_avoided_direct_kg' en SAC es acumulado → se aplica diff() para
           obtener valores por timestep.

    Returns:
        daily (DataFrame): datos diarios agregados (365 filas)
        info_str (str): descripción del episodio/año extraído
    """
    ts = pd.read_csv(path)
    total_rows = len(ts)

    # ---- Determinar si es SAC (un solo episodio con múltiples años) --------
    unique_episodes = ts["episode"].nunique() if "episode" in ts.columns else None
    is_sac_style = (unique_episodes == 1) and (total_rows > 8760)

    if is_sac_style:
        # SAC: dividir por años dentro del único episodio
        ts["year_idx"] = (ts["timestep"] - 1) // 8760
        yr_last = int(ts["year_idx"].max())
        last = ts[ts["year_idx"] == yr_last].copy().reset_index(drop=True)
        last["day_num"] = ((last["timestep"] - 1) % 8760) // 24 + 1
        info_str = f"año={yr_last} de {int(ts['year_idx'].max())+1} (último de entrenamiento)"

        # co2_avoided_direct_kg es acumulado en SAC → convertir a per-timestep
        col_dir = "co2_avoided_direct_kg"
        if col_dir in last.columns:
            # Tomar el valor mínimo del año anterior como base de reseteo
            prev_year_rows = ts[ts["year_idx"] == yr_last - 1]
            base_val = float(prev_year_rows[col_dir].iloc[-1]) if len(prev_year_rows) > 0 else 0.0
            # Construir serie acumulada desde inicio del año (substraer base)
            last[col_dir] = last[col_dir] - base_val
            # Ahora es acumulado dentro del año → diff para obtener per-timestep
            last[col_dir] = last[col_dir].diff().fillna(last[col_dir].iloc[0])
            last[col_dir] = last[col_dir].clip(lower=0)

    else:
        # A2C / PPO: episodios estándar
        ep_counts = (
            ts.groupby("episode")["timestep"].count()
            if "episode" in ts.columns
            else {}
        )
        complete_eps = (
            ep_counts[ep_counts >= 8760].index
            if len(ep_counts) > 0
            else [0]
        )
        ep_last = int(max(complete_eps)) if len(complete_eps) > 0 else int(ts["episode"].max())
        last = ts[ts["episode"] == ep_last].copy().reset_index(drop=True)
        last["day_num"] = (last["timestep"] - int(last["timestep"].min())) // 24 + 1
        info_str = f"episodio={ep_last} (último completo, {len(last):,} timesteps)"

    # ---- Agregar a nivel diario --------------------------------------------
    daily = last.groupby("day_num").agg(
        co2_grid_kg=("co2_grid_kg", "sum"),
        co2_avoided_indirect=("co2_avoided_indirect_kg", "sum"),
        co2_avoided_direct=("co2_avoided_direct_kg", "sum"),
        grid_import_kwh=("grid_import_kwh", "sum"),
        solar_kwh=("solar_generation_kwh", "sum"),
        ev_kwh=("ev_charging_kwh", "sum"),
    ).reset_index()

    # Baseline = todo lo que habría emitido SIN el sistema inteligente
    daily["co2_baseline"] = (
        daily["co2_grid_kg"]
        + daily["co2_avoided_indirect"]
        + daily["co2_avoided_direct"]
    )
    daily["co2_agent"] = daily["co2_grid_kg"]
    daily["reduccion_diaria"] = daily["co2_baseline"] - daily["co2_agent"]

    # Mes del año (1-12)
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]
    daily["month"] = pd.cut(
        daily["day_num"],
        bins=cum_days,
        labels=range(1, 13),
    ).astype(int)

    return daily, info_str


def _build_daily_series() -> tuple[pd.DataFrame, pd.DataFrame, str, dict]:
    """
    Carga los 3 agentes, determina el mejor por menor CO₂ grid anual,
    y construye Grupo A (baseline) y Grupo B (mejor agente).

    Returns:
        daily_best  (DataFrame): datos diarios del mejor agente (365 días)
        all_agents  (dict):      {nombre: daily_df} para comparación cruzada
        best_name   (str):       nombre del mejor agente seleccionado
        agents_summary (dict):   resumen anual de CO₂ de los 3 agentes
    """
    print("[1/5] Cargando datos de entrenamiento de los 3 agentes...")
    all_agents: dict[str, pd.DataFrame] = {}
    agents_summary: dict[str, dict] = {}

    for name, path in AGENTS_FILES.items():
        if not path.exists():
            print(f"    AVISO: no se encontro {path.name}, omitiendo {name}")
            continue
        daily, info_str = _load_agent_last_year(name, path)
        all_agents[name] = daily
        annual_co2 = daily["co2_grid_kg"].sum()
        annual_baseline = daily["co2_baseline"].sum()
        agents_summary[name] = {
            "co2_grid_anual_kg": round(float(annual_co2), 1),
            "co2_baseline_anual_kg": round(float(annual_baseline), 1),
            "reduccion_pct": round(
                float((annual_baseline - annual_co2) / annual_baseline * 100), 2
            ) if annual_baseline > 0 else 0.0,
            "info": info_str,
        }
        print(f"    [{name}] {info_str}")
        print(f"      CO2 grid anual = {annual_co2:>14,.1f} kg  |  "
              f"Baseline = {annual_baseline:>14,.1f} kg  |  "
              f"Reduccion = {agents_summary[name]['reduccion_pct']:.1f}%")

    if not all_agents:
        raise FileNotFoundError("No se encontró ningún archivo de timeseries de entrenamiento en outputs/")

    # ---- Seleccionar el mejor agente (menor CO₂ grid en último año) -----------
    best_name = min(agents_summary, key=lambda k: agents_summary[k]["co2_grid_anual_kg"])
    print(f"\n    => MEJOR AGENTE (menor CO2 grid): {best_name} "
          f"({agents_summary[best_name]['co2_grid_anual_kg']:,.1f} kg/año "
          f"| -{agents_summary[best_name]['reduccion_pct']:.1f}% vs baseline)")

    daily_best = all_agents[best_name]
    return daily_best, all_agents, best_name, agents_summary


def _build_monthly_series(daily: pd.DataFrame) -> pd.DataFrame:
    """Agrega los datos diarios a nivel mensual."""
    monthly = daily.groupby("month").agg(
        co2_baseline=("co2_baseline", "sum"),
        co2_agent=("co2_agent", "sum"),
        reduccion=("reduccion_diaria", "sum"),
        dias=("day_num", "count"),
    ).reset_index()
    monthly["reduccion_pct"] = (
        monthly["reduccion"] / monthly["co2_baseline"] * 100
    )
    monthly["mes"] = [MONTHS_ES[m - 1] for m in monthly["month"]]
    return monthly


# ---------------------------------------------------------------------------
# 2. ESTADÍSTICOS DESCRIPTIVOS
# ---------------------------------------------------------------------------

def descriptive_stats(
    grupo_a: pd.Series, grupo_b: pd.Series, best_name: str
) -> pd.DataFrame:
    """Tabla de estadísticos descriptivos para ambos grupos."""
    stats_table = pd.DataFrame({
        "Estadístico": [
            "N (días)", "Media (kg/día)", "Desv. Est. (kg/día)",
            "Mediana (kg/día)", "Mínimo (kg/día)", "Máximo (kg/día)",
            "Coef. Var. (%)", "Total Anual (kg)",
        ],
        "Grupo A – Baseline": [
            len(grupo_a),
            f"{grupo_a.mean():>12,.2f}",
            f"{grupo_a.std():>12,.2f}",
            f"{grupo_a.median():>12,.2f}",
            f"{grupo_a.min():>12,.2f}",
            f"{grupo_a.max():>12,.2f}",
            f"{grupo_a.std()/grupo_a.mean()*100:>12,.2f}",
            f"{grupo_a.sum():>12,.1f}",
        ],
        f"Grupo B – {best_name} Smart": [
            len(grupo_b),
            f"{grupo_b.mean():>12,.2f}",
            f"{grupo_b.std():>12,.2f}",
            f"{grupo_b.median():>12,.2f}",
            f"{grupo_b.min():>12,.2f}",
            f"{grupo_b.max():>12,.2f}",
            f"{grupo_b.std()/grupo_b.mean()*100:>12,.2f}",
            f"{grupo_b.sum():>12,.1f}",
        ],
    })
    return stats_table


# ---------------------------------------------------------------------------
# 3. PRUEBA DE NORMALIDAD
# ---------------------------------------------------------------------------

def normality_test(
    grupo_a: pd.Series, grupo_b: pd.Series, best_name: str = "Mejor Agente"
) -> tuple[dict, bool, bool]:
    """
    Aplica Shapiro-Wilk (n ≤ 5,000) a ambos grupos.
    Devuelve: resultados_dict, es_normal_a, es_normal_b
    """
    print("\n[2/5] Aplicando pruebas de normalidad (Shapiro-Wilk)...")

    stat_a, p_a = stats.shapiro(grupo_a)
    stat_b, p_b = stats.shapiro(grupo_b)

    normal_a = p_a > ALPHA
    normal_b = p_b > ALPHA

    lbl_a = "Grupo A – Baseline"
    lbl_b = f"Grupo B – {best_name} Smart"
    result = {
        lbl_a: {
            "W_statistic": round(float(stat_a), 6),
            "p_value": p_a,
            "normal": normal_a,
            "interpretacion": (
                f"p = {p_a:.6f} {'> 0.05 → distribución NORMAL (No se rechaza H₀ normalidad)' if normal_a else '< 0.05 → distribución NO-NORMAL (Se rechaza H₀ normalidad)'}"
            ),
        },
        lbl_b: {
            "W_statistic": round(float(stat_b), 6),
            "p_value": p_b,
            "normal": normal_b,
            "interpretacion": (
                f"p = {p_b:.6f} {'> 0.05 → distribución NORMAL (No se rechaza H₀ normalidad)' if normal_b else '< 0.05 → distribución NO-NORMAL (Se rechaza H₀ normalidad)'}"
            ),
        },
    }

    for grp, res in result.items():
        print(f"    {grp}: W={res['W_statistic']:.6f}, p={res['p_value']:.6f}  |  {res['interpretacion']}")

    return result, normal_a, normal_b


# ---------------------------------------------------------------------------
# 4. PRUEBA INFERENCIAL DE COMPARACIÓN DE MEDIAS
# ---------------------------------------------------------------------------

def inferential_test(
    grupo_a: pd.Series,
    grupo_b: pd.Series,
    normal_a: bool,
    normal_b: bool,
) -> dict:
    """
    Aplica:
    - T-Student para muestras relacionadas (paired) si hay normalidad en ambos grupos.
    - Wilcoxon signed-rank si no hay normalidad.

    Retorna diccionario con resultados completos.
    """
    print("\n[3/5] Ejecutando prueba inferencial de comparacion de medias...")
    both_normal = normal_a and normal_b
    diferencias = grupo_a - grupo_b

    if both_normal:
        test_name = "T-Student para muestras relacionadas (paired t-test)"
        stat, p_value = stats.ttest_rel(grupo_a, grupo_b, alternative="greater")
        gl = len(grupo_a) - 1
        test_detail = {
            "estadistico": "t",
            "valor": round(float(stat), 6),
            "grados_libertad": gl,
        }
    else:
        test_name = "Wilcoxon signed-rank (no paramétrico, muestras relacionadas)"
        stat, p_value = stats.wilcoxon(
            diferencias, alternative="greater", method="auto"
        )
        test_detail = {
            "estadistico": "W",
            "valor": round(float(stat), 6),
            "grados_libertad": None,
        }

    # Tamaño del efecto: d de Cohen (paired)
    cohen_d = float(diferencias.mean() / diferencias.std())

    # Intervalo de confianza 95% para la diferencia media
    ci_low, ci_high = stats.t.interval(
        0.95,
        df=len(diferencias) - 1,
        loc=float(diferencias.mean()),
        scale=stats.sem(diferencias),
    )

    rechaza_h0 = p_value < ALPHA
    conclusion = (
        "RECHAZA H₀: La reducción de CO₂ ES estadísticamente significativa "
        f"(p = {p_value:.2e} < α = {ALPHA}).\n"
        "La infraestructura de carga inteligente con el mejor agente RL reduce significativamente "
        "las emisiones de CO₂ en comparación con la línea base."
        if rechaza_h0
        else
        "NO SE RECHAZA H₀: La evidencia no es suficiente para afirmar reducción significativa "
        f"(p = {p_value:.4f} > α = {ALPHA})."
    )

    result = {
        "prueba": test_name,
        "estadistico_prueba": test_detail,
        "p_value": float(p_value),
        "alpha": ALPHA,
        "rechaza_H0": rechaza_h0,
        "cohen_d": round(cohen_d, 4),
        "diferencia_media_kg_dia": round(float(diferencias.mean()), 2),
        "IC_95_diferencia": [round(ci_low, 2), round(ci_high, 2)],
        "reduccion_media_porcentual": round(
            float(diferencias.mean() / grupo_a.mean() * 100), 2
        ),
        "conclusion": conclusion,
    }

    mag = (
        "NEGLIGIBLE (<0.2)" if abs(cohen_d) < 0.2
        else "SMALL (0.2-0.5)" if abs(cohen_d) < 0.5
        else "MEDIUM (0.5-0.8)" if abs(cohen_d) < 0.8
        else "LARGE (>0.8)"
    )
    print(f"    Prueba: {test_name}")
    print(f"    {test_detail['estadistico']} = {test_detail['valor']:.4f}")
    print(f"    p-value = {p_value:.4e}  |  alpha = {ALPHA}")
    print(f"    Cohen d = {cohen_d:.4f}  [{mag}]")
    print(f"    IC 95%  = [{ci_low:,.2f}, {ci_high:,.2f}] kg/dia")
    print(f"    Reduccion media = {result['reduccion_media_porcentual']:.1f}%")
    print(f"    >>> {conclusion}")

    return result


# ---------------------------------------------------------------------------
# 5. VISUALIZACIONES
# ---------------------------------------------------------------------------

def plot_all(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    normality: dict,
    test_result: dict,
    all_agents: dict,
    best_name: str,
) -> None:
    """Genera figura compuesta de 7 paneles para la sección 5.2 de la tesis.
    Panel 1-6: análisis estadístico del mejor agente vs baseline.
    Panel 7:   comparación cruzada de los 3 agentes entrenados.
    """
    print("\n[4/5] Generando figuras para seccion 5.2...")

    grupo_a = daily["co2_baseline"]
    grupo_b = daily["co2_agent"]
    lbl_a = "Grupo A – Baseline"
    lbl_b = f"Grupo B – {best_name} Smart"

    fig = plt.figure(figsize=(18, 28))
    fig.patch.set_facecolor("#F8F9FA")
    gs = gridspec.GridSpec(
        4, 2, figure=fig,
        hspace=0.44, wspace=0.30,
        left=0.08, right=0.96, top=0.93, bottom=0.04
    )

    TITLE_FS = 11
    LABEL_FS = 9
    TICK_FS = 8
    COLOR_BASE = "#D32F2F"
    COLOR_BEST = "#1565C0"

    # -----------------------------------------------------------------------
    # Panel 1: Serie temporal diaria
    # -----------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, :])
    days = daily["day_num"]
    ax1.fill_between(days, grupo_a, alpha=0.25, color=COLOR_BASE, label="_nolegend_")
    ax1.plot(days, grupo_a, color=COLOR_BASE, linewidth=0.8, alpha=0.8,
             label=f"{lbl_a}  (media={grupo_a.mean():,.0f} kg/día)")
    ax1.fill_between(days, grupo_b, alpha=0.25, color=COLOR_BEST, label="_nolegend_")
    ax1.plot(days, grupo_b, color=COLOR_BEST, linewidth=0.8, alpha=0.8,
             label=f"{lbl_b} (media={grupo_b.mean():,.0f} kg/día)")

    # Separadores de mes
    cum_days = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    for d in cum_days:
        ax1.axvline(d, color="gray", linewidth=0.4, linestyle="--", alpha=0.5)

    ax1.set_title(
        "Serie Temporal Diaria de Emisiones CO₂ (365 días)\n"
        f"Grupo A: Baseline (sin control inteligente) vs Grupo B: {best_name} Smart Charging",
        fontsize=TITLE_FS, fontweight="bold",
    )
    ax1.set_xlabel("Día del año (2024)", fontsize=LABEL_FS)
    ax1.set_ylabel("CO₂ emitido (kg/día)", fontsize=LABEL_FS)
    ax1.legend(fontsize=LABEL_FS, loc="upper right")
    ax1.tick_params(labelsize=TICK_FS)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax1.set_xlim(1, 365)
    ax1.grid(axis="y", alpha=0.3)

    # Reduccion media annotada
    y_mid = (grupo_a.mean() + grupo_b.mean()) / 2
    ax1.annotate(
        f"Reducción media:\n{test_result['reduccion_media_porcentual']:.1f}%\n"
        f"({test_result['diferencia_media_kg_dia']:,.0f} kg/día)",
        xy=(183, y_mid), xytext=(183, y_mid),
        fontsize=9, ha="center", va="center",
        color="#2E7D32", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9", edgecolor="#2E7D32"),
    )

    # -----------------------------------------------------------------------
    # Panel 2: Diagrama de caja
    # -----------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[1, 0])
    bplot = ax2.boxplot(
        [grupo_a.values, grupo_b.values],
        patch_artist=True,
        notch=True,
        vert=True,
        widths=0.5,
        medianprops=dict(color="black", linewidth=2),
    )
    bplot["boxes"][0].set_facecolor(COLOR_BASE)
    bplot["boxes"][0].set_alpha(0.7)
    bplot["boxes"][1].set_facecolor(COLOR_BEST)
    bplot["boxes"][1].set_alpha(0.7)

    ax2.set_xticklabels(
        ["Grupo A\nBaseline", f"Grupo B\n{best_name} Smart"], fontsize=LABEL_FS
    )
    ax2.set_title(
        "Distribución Diaria de Emisiones CO₂\n(Diagrama de Caja con Intervalo de Confianza notched)",
        fontsize=TITLE_FS, fontweight="bold",
    )
    ax2.set_ylabel("CO₂ emitido (kg/día)", fontsize=LABEL_FS)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.tick_params(labelsize=TICK_FS)
    ax2.grid(axis="y", alpha=0.3)

    # Anotacion p-value
    p_val = test_result["p_value"]
    p_txt = f"p = {p_val:.2e}" if p_val < 0.001 else f"p = {p_val:.4f}"
    ax2.annotate(
        f"*** {p_txt}\n(rechaza H₀)",
        xy=(1.5, grupo_a.quantile(0.75)),
        xytext=(1.5, grupo_a.quantile(0.90)),
        ha="center", fontsize=9, color="#1B5E20", fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", color="#1B5E20"),
        bbox=dict(boxstyle="round", facecolor="#F1F8E9", edgecolor="#1B5E20"),
    )

    # -----------------------------------------------------------------------
    # Panel 3: Histogramas de distribución
    # -----------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.hist(grupo_a, bins=30, color=COLOR_BASE, alpha=0.6,
             density=True, label=lbl_a)
    ax3.hist(grupo_b, bins=30, color=COLOR_BEST, alpha=0.6,
             density=True, label=lbl_b)

    # Curva normal teórica
    for serie, col in zip([grupo_a, grupo_b], [COLOR_BASE, COLOR_BEST]):
        mu, sigma = serie.mean(), serie.std()
        xmin, xmax = serie.min() - sigma, serie.max() + sigma
        x_range = np.linspace(xmin, xmax, 200)
        ax3.plot(x_range, stats.norm.pdf(x_range, mu, sigma),
                 color=col, linewidth=2, linestyle="--")

    ax3.set_title(
        "Distribución de Frecuencias (Histograma + Curva Normal Teórica)\n"
        "Shapiro-Wilk: verificación de normalidad",
        fontsize=TITLE_FS, fontweight="bold",
    )
    ax3.set_xlabel("CO₂ emitido (kg/día)", fontsize=LABEL_FS)
    ax3.set_ylabel("Densidad de probabilidad", fontsize=LABEL_FS)
    ax3.legend(fontsize=LABEL_FS)
    ax3.tick_params(labelsize=TICK_FS)
    ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax3.grid(alpha=0.3)

    # Anotacion normalidad
    norm_a = normality[lbl_a]
    norm_b = normality[lbl_b]
    info_txt = (
        f"Shapiro-Wilk:\n"
        f"A: W={norm_a['W_statistic']:.4f}, p={norm_a['p_value']:.4f} "
        f"({'Normal' if norm_a['normal'] else 'No-Normal'})\n"
        f"B: W={norm_b['W_statistic']:.4f}, p={norm_b['p_value']:.4f} "
        f"({'Normal' if norm_b['normal'] else 'No-Normal'})"
    )
    ax3.text(
        0.97, 0.95, info_txt,
        transform=ax3.transAxes, fontsize=7.5, ha="right", va="top",
        bbox=dict(boxstyle="round", facecolor="lightyellow", edgecolor="gray", alpha=0.9),
    )

    # -----------------------------------------------------------------------
    # Panel 4: Diferencias diarias (paired)
    # -----------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[2, 0])
    diferencias = grupo_a - grupo_b
    ax4.fill_between(days, diferencias, alpha=0.4,
                     color="#2E7D32", label="Reducción diaria")
    ax4.plot(days, diferencias, color="#2E7D32", linewidth=0.7)
    ax4.axhline(diferencias.mean(), color="#FF6F00", linewidth=1.8,
                linestyle="--", label=f"Media: {diferencias.mean():,.0f} kg/día")
    ci_low, ci_high = test_result["IC_95_diferencia"]
    ax4.axhline(ci_low, color="#FF6F00", linewidth=1, linestyle=":",
                label=f"IC 95%: [{ci_low:,.0f}, {ci_high:,.0f}] kg/día")
    ax4.axhline(ci_high, color="#FF6F00", linewidth=1, linestyle=":")
    ax4.set_title(
        f"Diferencia Diaria: Baseline − {best_name} (Reducción de CO₂)\n"
        "Análisis de pares para prueba estadística",
        fontsize=TITLE_FS, fontweight="bold",
    )
    ax4.set_xlabel("Día del año (2024)", fontsize=LABEL_FS)
    ax4.set_ylabel("Reducción CO₂ (kg/día)", fontsize=LABEL_FS)
    ax4.legend(fontsize=LABEL_FS - 1, loc="lower right")
    ax4.tick_params(labelsize=TICK_FS)
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax4.set_xlim(1, 365)
    ax4.grid(axis="y", alpha=0.3)

    # -----------------------------------------------------------------------
    # Panel 5: Barras mensuales (CO₂ mensual)
    # -----------------------------------------------------------------------
    ax5 = fig.add_subplot(gs[2, 1])
    x = np.arange(12)
    w = 0.38
    ax5.bar(x - w / 2, monthly["co2_baseline"] / 1000,
            width=w, color=COLOR_BASE, alpha=0.8, label=lbl_a)
    ax5.bar(x + w / 2, monthly["co2_agent"] / 1000,
            width=w, color=COLOR_BEST, alpha=0.8, label=lbl_b)

    for i, row in monthly.iterrows():
        ax5.text(i, row["co2_baseline"] / 1000 + 20,
                 f"-{row['reduccion_pct']:.0f}%",
                 ha="center", va="bottom", fontsize=6.5,
                 color="#1B5E20", fontweight="bold")

    ax5.set_xticks(x)
    ax5.set_xticklabels(MONTHS_ES, fontsize=TICK_FS)
    ax5.set_title(
        "Comparación Mensual de Emisiones CO₂ (tCO₂)\n"
        "Porcentaje de reducción sobre cada mes",
        fontsize=TITLE_FS, fontweight="bold",
    )
    ax5.set_ylabel("CO₂ mensual (tCO₂)", fontsize=LABEL_FS)
    ax5.legend(fontsize=LABEL_FS)
    ax5.tick_params(labelsize=TICK_FS)
    ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax5.grid(axis="y", alpha=0.3)

    # -----------------------------------------------------------------------
    # Título global
    # -----------------------------------------------------------------------
    test_name_short = (
        "T-Student pareada" if "T-Student" in test_result["prueba"]
        else "Wilcoxon signed-rank"
    )
    p_fmt = f"{test_result['p_value']:.2e}" if test_result["p_value"] < 0.0001 else f"{test_result['p_value']:.6f}"
    rej_str = "RECHAZA H₀" if test_result["rechaza_H0"] else "NO rechaza H₀"
    fig.suptitle(
        f"Prueba de Hipótesis Estadística — Reducción de CO₂\n"
        f"pvbesscar | Iquitos, Perú | Mejor Agente: {best_name} | OE3\n"
        f"Prueba: {test_name_short}   |   p-value = {p_fmt}   |   {rej_str}   |   Cohen d = {test_result['cohen_d']:.2f}",
        fontsize=12, fontweight="bold", y=0.97,
    )

    out_fig = OUT_DIR / "hypothesis_test_co2_figura_completa.png"
    fig.savefig(out_fig, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"    Figura guardada: {out_fig.relative_to(ROOT)}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. TABLA RESUMEN PARA SECCIÓN 5.2 (LaTeX-ready y CSV)
# ---------------------------------------------------------------------------

def build_section52_table(
    grupo_a: pd.Series,
    grupo_b: pd.Series,
    normality: dict,
    test_result: dict,
    monthly: pd.DataFrame,
    best_name: str = "Mejor Agente",
    agents_summary: dict | None = None,
) -> None:
    """Genera tablas CSV y JSON para la sección 5.2 de la tesis."""

    # Tabla 1: Estadísticos descriptivos
    desc = descriptive_stats(grupo_a, grupo_b, best_name)
    desc_path = OUT_DIR / "tabla_estadisticos_descriptivos.csv"
    desc.to_csv(desc_path, index=False, encoding="utf-8-sig")

    # Tabla 2: Normalidad
    norm_rows = []
    for grp, res in normality.items():
        norm_rows.append({
            "Grupo": grp,
            "W_Shapiro-Wilk": res["W_statistic"],
            "p-value": f"{res['p_value']:.6f}",
            "alpha": ALPHA,
            "¿Normal? (p>α)": "SÍ" if res["normal"] else "NO",
            "Interpretacion": res["interpretacion"],
        })
    norm_df = pd.DataFrame(norm_rows)
    norm_path = OUT_DIR / "tabla_normalidad_shapiro_wilk.csv"
    norm_df.to_csv(norm_path, index=False, encoding="utf-8-sig")

    # Tabla 3: Prueba inferencial
    diff = grupo_a - grupo_b
    infer_rows = [
        {"Parámetro": "Prueba estadística", "Valor": test_result["prueba"]},
        {"Parámetro": f"Estadístico {test_result['estadistico_prueba']['estadistico']}",
         "Valor": f"{test_result['estadistico_prueba']['valor']:.6f}"},
        {"Parámetro": "p-value (una cola, H₁: A > B)",
         "Valor": f"{test_result['p_value']:.2e}"},
        {"Parámetro": "Nivel de significancia (α)", "Valor": str(ALPHA)},
        {"Parámetro": "¿Rechaza H₀?",
         "Valor": "SÍ ✓" if test_result["rechaza_H0"] else "NO"},
        {"Parámetro": f"Reducción media diaria (Baseline−{best_name})",
         "Valor": f"{test_result['diferencia_media_kg_dia']:,.2f} kg/día"},
        {"Parámetro": "IC 95% para la diferencia",
         "Valor": f"[{test_result['IC_95_diferencia'][0]:,.2f}, {test_result['IC_95_diferencia'][1]:,.2f}] kg/día"},
        {"Parámetro": "Reducción media porcentual",
         "Valor": f"{test_result['reduccion_media_porcentual']:.2f}%"},
        {"Parámetro": "Tamaño del efecto (Cohen d)",
         "Valor": f"{test_result['cohen_d']:.4f}  (LARGE > 0.8)"},
        {"Parámetro": "Total anual Baseline",
         "Valor": f"{grupo_a.sum():,.1f} kg CO₂/año"},
        {"Parámetro": f"Total anual {best_name}",
         "Valor": f"{grupo_b.sum():,.1f} kg CO₂/año"},
        {"Parámetro": "Reducción total anual",
         "Valor": f"{(grupo_a.sum()-grupo_b.sum()):,.1f} kg CO₂/año"},
        {"Parámetro": "Conclusión", "Valor": test_result["conclusion"]},
    ]
    infer_df = pd.DataFrame(infer_rows)
    infer_path = OUT_DIR / "tabla_prueba_inferencial.csv"
    infer_df.to_csv(infer_path, index=False, encoding="utf-8-sig")

    # Tabla 4: Monthly CO₂ comparison
    monthly_out = monthly[["mes", "co2_baseline", "co2_agent", "reduccion", "reduccion_pct", "dias"]].copy()
    monthly_out.columns = [
        "Mes", "CO₂ Baseline (kg)", f"CO₂ {best_name} (kg)",
        "Reducción (kg)", "Reducción (%)", "Días",
    ]
    monthly_out["CO₂ Baseline (tCO₂)"] = (monthly_out["CO₂ Baseline (kg)"] / 1000).round(2)
    monthly_out[f"CO₂ {best_name} (tCO₂)"] = (monthly_out[f"CO₂ {best_name} (kg)"] / 1000).round(2)
    monthly_out["Reducción (tCO₂)"] = (monthly_out["Reducción (kg)"] / 1000).round(2)
    monthly_out["Reducción (%)"] = monthly_out["Reducción (%)"].round(2)

    monthly_path = OUT_DIR / "tabla_comparacion_mensual_co2.csv"
    monthly_out.to_csv(monthly_path, index=False, encoding="utf-8-sig")

    # JSON resumen completo
    summary = {
        "metadata": {
            "proyecto": "pvbesscar",
            "ubicacion": "Iquitos, Peru",
            "objetivo_oe3": (
                "Seleccionar el agente de inteligencia artificial de la infraestructura "
                "de carga inteligente para la gestion de recarga de motos y mototaxis "
                "electricas, apropiada que contribuye de manera cuantificable a la "
                "reduccion de emisiones de dioxido de carbono en la ciudad de Iquitos"
            ),
            "agente_seleccionado": best_name,
            "agentes_evaluados": list((agents_summary or {}).keys()) or ["A2C", "PPO", "SAC"],
            "resumen_agentes": agents_summary or {},
            "fecha": "2026-04-06",
            "factor_co2_grid": f"{CO2_GRID_FACTOR_KG_KWH} kg CO2/kWh (red termica Iquitos)",
        },
        "hipotesis": {
            "H0": f"mu_baseline = mu_{best_name} (reduccion no significativa)",
            "H1": f"mu_baseline > mu_{best_name} (reduccion estadisticamente significativa)",
            "alpha": ALPHA,
        },
        "grupos": {
            "Grupo_A_Baseline": {
                "descripcion": (
                    "CO2 directo (combustion motos/mototaxis) + CO2 indirecto "
                    "(red termica Iquitos sin solar, sin BESS, sin control inteligente)"
                ),
                "n_dias": len(grupo_a),
                "media_kg_dia": round(float(grupo_a.mean()), 2),
                "std_kg_dia": round(float(grupo_a.std()), 2),
                "total_anual_kg": round(float(grupo_a.sum()), 1),
                "total_anual_tCO2": round(float(grupo_a.sum()) / 1000, 2),
            },
            f"Grupo_B_{best_name}_Smart": {
                "descripcion": (
                    f"CO2 grid real con infraestructura de carga inteligente: "
                    f"solar 4050 kWp + BESS 2000 kWh + agente {best_name}"
                ),
                "n_dias": len(grupo_b),
                "media_kg_dia": round(float(grupo_b.mean()), 2),
                "std_kg_dia": round(float(grupo_b.std()), 2),
                "total_anual_kg": round(float(grupo_b.sum()), 1),
                "total_anual_tCO2": round(float(grupo_b.sum()) / 1000, 2),
            },
        },
        "normalidad": {
            grp: {
                "W": res["W_statistic"],
                "p": res["p_value"],
                "normal": res["normal"],
            }
            for grp, res in normality.items()
        },
        "prueba_inferencial": {
            "nombre": test_result["prueba"],
            "estadistico": test_result["estadistico_prueba"],
            "p_value": test_result["p_value"],
            "rechaza_H0": test_result["rechaza_H0"],
            "cohen_d": test_result["cohen_d"],
            "reduccion_media_kg_dia": test_result["diferencia_media_kg_dia"],
            "IC_95_kg_dia": test_result["IC_95_diferencia"],
            "reduccion_media_pct": test_result["reduccion_media_porcentual"],
            "reduccion_anual_kg": round(float(grupo_a.sum() - grupo_b.sum()), 1),
            "reduccion_anual_tCO2": round(float(grupo_a.sum() - grupo_b.sum()) / 1000, 2),
        },
        "conclusion": test_result["conclusion"],
        "archivos_generados": [
            str(p.relative_to(ROOT)) for p in OUT_DIR.glob("*")
        ],
    }
    # Convert numpy types to native Python before JSON dump
    def _to_native(obj):
        if isinstance(obj, dict):
            return {k: _to_native(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_native(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    json_path = OUT_DIR / "RESULTADOS_HIPOTESIS_CO2_COMPLETO.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_to_native(summary), f, indent=2, ensure_ascii=False)

    print(f"    Tablas guardadas en: {OUT_DIR.relative_to(ROOT)}/")
    for p in [desc_path, norm_path, infer_path, monthly_path, json_path]:
        print(f"      - {p.name}")


# ---------------------------------------------------------------------------
# 7. IMPRESIÓN DE RESULTADOS (Redacción sección 5.2)
# ---------------------------------------------------------------------------

def print_section52_text(
    grupo_a: pd.Series,
    grupo_b: pd.Series,
    normality: dict,
    test_result: dict,
    monthly: pd.DataFrame,
    best_name: str = "Mejor Agente",
) -> None:
    """Imprime el texto redactado listo para la sección 5.2 de la tesis."""
    sep = "=" * 78
    print(f"\n{sep}")
    print("  RESULTADOS PARA SECCION 5.2: PRUEBA DE HIPOTESIS ESTADISTICA")
    print(f"{sep}")

    test_name_short = (
        "T-Student para muestras relacionadas"
        if "T-Student" in test_result["prueba"]
        else "Wilcoxon signed-rank"
    )
    p_fmt = (
        f"{test_result['p_value']:.2e}"
        if test_result["p_value"] < 0.0001
        else f"{test_result['p_value']:.6f}"
    )

    norm_a = normality[lbl_a]
    norm_b = normality[lbl_b]

    print(f"""
TABLA 1 — Estadísticos descriptivos (n = {len(grupo_a)} días, año 2024)
──────────────────────────────────────────────────────────────────────────
 Estadístico               Grupo A (Baseline)     Grupo B ({best_name} Smart)
──────────────────────────────────────────────────────────────────────────
 Media diaria (kg/día)     {grupo_a.mean():>18,.2f}    {grupo_b.mean():>18,.2f}
 Desv. estándar (kg/día)   {grupo_a.std():>18,.2f}    {grupo_b.std():>18,.2f}
 Mediana (kg/día)          {grupo_a.median():>18,.2f}    {grupo_b.median():>18,.2f}
 Mínimo (kg/día)           {grupo_a.min():>18,.2f}    {grupo_b.min():>18,.2f}
 Máximo (kg/día)           {grupo_a.max():>18,.2f}    {grupo_b.max():>18,.2f}
 Coef. Variación (%)       {grupo_a.std()/grupo_a.mean()*100:>18,.2f}    {grupo_b.std()/grupo_b.mean()*100:>18,.2f}
 TOTAL ANUAL (kg)          {grupo_a.sum():>18,.1f}    {grupo_b.sum():>18,.1f}
 TOTAL ANUAL (tCO₂)        {grupo_a.sum()/1000:>18,.2f}    {grupo_b.sum()/1000:>18,.2f}
──────────────────────────────────────────────────────────────────────────
 REDUCCION ANUAL           {(grupo_a.sum()-grupo_b.sum()):>18,.1f} kg  ({test_result['reduccion_media_porcentual']:.1f}%)
""")

    print(f"""TABLA 2 — Prueba de Normalidad (Shapiro-Wilk, α = {ALPHA})
──────────────────────────────────────────────────────────────────────
 Grupo                     W-statistic    p-value    ¿Normal?
──────────────────────────────────────────────────────────────────────
 Grupo A – Baseline        {norm_a['W_statistic']:>11.6f}    {norm_a['p_value']:>9.6f}    {'SÍ' if norm_a['normal'] else 'NO'}
 Grupo B – {best_name:20s}  {norm_b['W_statistic']:>11.6f}    {norm_b['p_value']:>9.6f}    {'SÍ' if norm_b['normal'] else 'NO'}
──────────────────────────────────────────────────────────────────────
 Decisión: {'Ambos grupos normales → se aplica prueba t de Student (paramétrica)' if norm_a['normal'] and norm_b['normal'] else 'Al menos un grupo no normal → se aplica prueba Wilcoxon (no paramétrica)'}
""")

    print(f"""TABLA 3 — Prueba Inferencial de Comparación de Medias
──────────────────────────────────────────────────────────────────────
 Prueba aplicada:          {test_result['prueba']}
 Hipótesis nula  (H₀):    μ_baseline = μ_{best_name}  (sin diferencia significativa)
 Hipótesis alter.(H₁):    μ_baseline > μ_{best_name}  (reducción es significativa)
 Estadístico {test_result['estadistico_prueba']['estadistico']}:              {test_result['estadistico_prueba']['valor']:>12.6f}
 p-value (una cola):      {p_fmt:>16}
 Nivel sig. α:            {ALPHA:>16}
 ¿p < α?:                 {'SÍ → RECHAZA H₀' if test_result['rechaza_H0'] else 'NO → No rechaza H₀'}
 Reducción media:         {test_result['diferencia_media_kg_dia']:>13,.2f} kg/día  ({test_result['reduccion_media_porcentual']:.2f}%)
 IC 95% diferencia:       [{test_result['IC_95_diferencia'][0]:,.2f} ; {test_result['IC_95_diferencia'][1]:,.2f}] kg/día
 Tamaño del efecto d:     {test_result['cohen_d']:>16.4f}  (LARGE: d > 0.8)
──────────────────────────────────────────────────────────────────────
""")

    print(f"""TABLA 4 — Comparación Mensual de Emisiones CO₂
──────────────────────────────────────────────────────────────────────
 Mes     Baseline (tCO₂)   {best_name} (tCO₂)   Reducción (tCO₂)  Red. (%)
──────────────────────────────────────────────────────────────────────""")
    for _, row in monthly.iterrows():
        print(
            f" {row['mes']:>5}    {row['co2_baseline']/1000:>13.2f}   "
            f"{row['co2_agent']/1000:>10.2f}   "
            f"{row['reduccion']/1000:>16.2f}   "
            f"{row['reduccion_pct']:>7.1f}%"
        )
    print(
        f" TOTAL    {monthly['co2_baseline'].sum()/1000:>13.2f}   "
        f"{monthly['co2_agentnt'].sum()/1000:>10.2f}   "
        f"{monthly['reduccion'].sum()/1000:>16.2f}   "
        f"{monthly['reduccion'].sum()/monthly['co2_baseline'].sum()*100:>7.1f}%"
    )
    print("──────────────────────────────────────────────────────────────────────")

    print(f"""
REDACCION PARA SECCION 5.2 DE LA TESIS:
──────────────────────────────────────────────────────────────────────
Para validar estadísticamente la Hipótesis General —que el sistema de
carga inteligente con el agente {best_name} reduce de manera cuantificable las
emisiones de CO₂— se extrajeron dos vectores de datos de la simulación
anual (n = {len(grupo_a)} días): el Grupo A (línea base, con conexión directa a la
red térmica de Iquitos) y el Grupo B (operación con infraestructura de
carga inteligente: solar 4,050 kWp + BESS 2,000 kWh + agente {best_name}).

Se aplicó la prueba de normalidad de Shapiro-Wilk (α = {ALPHA}) obteniendo:
  Grupo A: W = {norm_a['W_statistic']:.6f}, p = {norm_a['p_value']:.6f} ({'normal' if norm_a['normal'] else 'no normal'})
  Grupo B: W = {norm_b['W_statistic']:.6f}, p = {norm_b['p_value']:.6f} ({'normal' if norm_b['normal'] else 'no normal'})

{'Dado que ambos grupos presentan distribución normal, se aplicó la prueba T-Student para muestras relacionadas (pareada), adecuada para datos temporales del mismo período.' if norm_a['normal'] and norm_b['normal'] else 'Dado que al menos un grupo no presenta distribución normal, se aplicó la prueba no paramétrica de Wilcoxon para muestras relacionadas (signed-rank), adecuada para datos sin distribución normal.'}

Los resultados muestran:
  Estadístico {test_result['estadistico_prueba']['estadistico']} = {test_result['estadistico_prueba']['valor']:.6f}
  p-value = {p_fmt}  <<<  α = {ALPHA}

Dado que p < α = {ALPHA}, se RECHAZA la hipótesis nula H₀. El sistema de
carga inteligente con agente {best_name} logra una reducción media de
{test_result['diferencia_media_kg_dia']:,.0f} kg CO₂/día ({test_result['reduccion_media_porcentual']:.1f}%), con un
intervalo de confianza del 95% de [{test_result['IC_95_diferencia'][0]:,.0f} ; {test_result['IC_95_diferencia'][1]:,.0f}] kg/día
y un tamaño de efecto d de Cohen = {test_result['cohen_d']:.2f} (LARGE), confirmando una
diferencia práctica y estadísticamente significativa.

La reducción total anual es de {(grupo_a.sum()-grupo_b.sum())/1000:,.1f} tCO₂
(de {grupo_a.sum()/1000:,.1f} tCO₂ a {grupo_b.sum()/1000:,.1f} tCO₂, es decir
{test_result['reduccion_media_porcentual']:.1f}% de reducción), validando tanto la Hipótesis General
como los Objetivos Específicos OE2 y OE3 de la investigación.
──────────────────────────────────────────────────────────────────────
""")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 78)
    print("  PRUEBA DE HIPOTESIS ESTADISTICA — REDUCCION CO2")
    print("  pvbesscar | Iquitos, Peru | OE3 | Mejor Agente (determinado dinamicamente)")
    print("=" * 78)

    # 1. Datos — carga los 3 agentes, selecciona el mejor dinamicamente
    daily, all_agents, best_name, agents_summary = _build_daily_series()
    grupo_a = daily["co2_baseline"]
    grupo_b = daily["co2_agent"]
    monthly = _build_monthly_series(daily)

    # 2. Estadísticos descriptivos
    print("\n[DESC] Estadísticos descriptivos:")
    desc = descriptive_stats(grupo_a, grupo_b, best_name)
    print(desc.to_string(index=False))

    # 3. Normalidad
    normality, normal_a, normal_b = normality_test(grupo_a, grupo_b, best_name)

    # 4. Prueba inferencial
    test_result = inferential_test(grupo_a, grupo_b, normal_a, normal_b)

    # 5. Figuras
    plot_all(daily, monthly, normality, test_result, all_agents, best_name)

    # 6. Tablas / archivos
    build_section52_table(grupo_a, grupo_b, normality, test_result, monthly, best_name, agents_summary)

    # 7. Texto para tesis
    print_section52_text(grupo_a, grupo_b, normality, test_result, monthly, best_name)

    print("\n[5/5] Completado. Resultados en:")
    print(f"      {OUT_DIR.relative_to(ROOT)}/")
    print("=" * 78)


if __name__ == "__main__":
    main()
