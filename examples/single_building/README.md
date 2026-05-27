# Single-Building Example: Iquitos BESS Mall

Reproducible example of the PVBESSCAR framework applied to one building.
Validates the published results: **SAC achieves 62.8% CO₂ reduction vs F₀ baseline**.

## Quick start

```bash
# Random agent (no checkpoint required)
python examples/single_building/run.py --random-agent

# SAC agent (requires checkpoint in checkpoints/SAC/)
python examples/single_building/run.py --episodes 3

# Train first
python scripts/train/train_sac_citylearn.py
```

## Expected output

```
Ep 1: reward=  +482.3  CO₂_evitado= 2621.4 t/año  EV_sat=0.947  grid=  18432 kWh  (4.2s)
...
CO₂ evitado (media): 2621.4 t/año  (37.2% de baseline F₀)
```

---

## Mathematical Model

### 1. Energy Balance (Wali et al., 2025)

At each hourly timestep *t*, the power balance must hold:

```
P_PV(t) + P_grid(t) = P_load_fixed(t) + P_EV(t) + P_BESS_charge(t) - P_BESS_discharge(t)
```

where:
- `P_PV(t)` — photovoltaic generation (kW), computed from PVLib with irradiance and temperature
- `P_grid(t)` — net grid import/export (kW); negative = export
- `P_load_fixed(t)` — inelastic building load (kW): mall, offices
- `P_EV(t)` — total EV charging demand served (kW): `Σ_j min(P_EV,j(t), π_j(t) · P_EV,j_max)`
- `P_BESS_charge(t)`, `P_BESS_discharge(t)` — BESS power flows (kW, both ≥ 0)

### 2. BESS State-of-Charge Dynamics

BESS SoC evolves each hour according to:

```
SoC(t+1) = SoC(t) + [P_ch(t)·η_c - P_dis(t)/η_d] / E_cap
```

where the round-trip efficiency `η_rt = η_c · η_d`, so:

```
η_c = η_d = √η_rt          (symmetric model, IEC 62933-2-1)
```

Operational bounds are enforced by the agent action mapping:

```
SoC_min ≤ SoC(t) ≤ SoC_max     (DoD constraint)
|P_BESS(t)| ≤ P_BESS_max        (power constraint)
```

For Iquitos: `η_rt = 0.95`, `SoC_min = 0.20`, `SoC_max = 1.00`, `P_BESS_max = 400 kW`.

### 3. EV Fleet Demand Model (Nikolay et al., 2025 — EV-GNN)

Fleet demand for vehicle type *j* at hour *t* is modeled stochastically:

```
P_EV,j(t) = N_j · U_j · s_j(t) · E_session,j / Δt
```

where:
- `N_j` — number of vehicles of type *j*
- `U_j` — daily utilization factor (fraction active)
- `s_j(t)` — session arrival rate at hour *t* (shaped by peak/offpeak profile)
- `E_session,j` — mean energy per session (kWh)
- `Δt = 1 h` (hourly resolution)

The RL agent controls the service fraction `π_j(t) ∈ [0, 1]` per type, with debt tracking:

```
Debt_j(t+1) = max(0, Debt_j(t) + P_EV,j(t) - π_j(t)·P_EV,j(t))
```

### 4. PV Generation Model (pvlib)

```
P_PV(t) = A · η_panel · f_cov · G_eff(t) · η_inv · (1 - f_loss)
```

where `G_eff(t)` is the plane-of-array irradiance (W/m²) computed by PVLib from GHI,
temperature, wind speed, tilt, and azimuth.

For Iquitos: `A = 15,200 m²`, `η = 19.9%`, `f_cov = 0.65`, `η_inv = 95.6%`.
Peak installed: **4,050 kWp**.

### 5. CO₂ Accounting — Dual Model

The framework separates two complementary CO₂ savings mechanisms:

#### 5a. Direct savings (vehicle fuel displacement)

Electrifying vehicle type *j* avoids internal combustion emissions:

```
ΔCO₂_direct,j(t) = κ_j · P_EV,j_served(t)
```

| Type | κ_j (kg CO₂/kWh) | Source |
|------|------------------|--------|
| Moto | 0.87 | IPCC AR6 (gasoline, Loreto factor) |
| Mototaxi | 0.54 | IPCC AR6 (gas natural) |
| Carro eléctrico | 0.32 | IPCC AR6 (gasoline, Lima) |

#### 5b. Indirect savings (displacing grid CO₂)

Each kWh of PV self-consumed (or BESS discharge during peak) avoids grid-imported electricity:

```
ΔCO₂_indirect(t) = α_grid · (P_PV_selfcons(t) + P_BESS_dis_selfcons(t))
```

where `α_grid` is the grid CO₂ intensity factor:
- **Iquitos** (isolated diesel): 0.4521 kg CO₂/kWh (MINEM/OSINERGMIN 2024)
- **Lima SIN** (hydro+gas mix): 0.23 kg CO₂/kWh (MINEM Boletín 2024)

Total CO₂ avoided:

```
ΔCO₂_total(t) = Σ_j ΔCO₂_direct,j(t) + ΔCO₂_indirect(t)
```

### 6. Reward Function — CO2_DUAL_FOCUS (v8.0)

The universal reward aggregates 5 components with site-specific weights:

```
R(t) = Σ_{k=1}^{5} w_k · r_k(t),     Σ w_k = 1
```

| Component | Weight (Iquitos) | Formula |
|-----------|-----------------|---------|
| `r_direct_co2` | 0.35 | `ΔCO₂_direct(t) / CO₂_baseline` |
| `r_co2` | 0.30 | `ΔCO₂_indirect(t) / CO₂_baseline` |
| `r_ev` | 0.25 | `Σ_j EV_sat_j(t) / N_types` |
| `r_solar` | 0.05 | `P_PV_selfcons(t) / P_PV_max` |
| `r_grid` | 0.05 | `−|ΔP_grid(t) − ΔP_grid(t−1)| / P_ramp_base` |

EV satisfaction per type is defined as the cumulative service ratio:

```
EV_sat_j(T) = Σ_{t=0}^{T} P_EV,j_served(t) / max(Σ_{t=0}^{T} P_EV,j(t), ε)
```

All reward components are normalized to `[-1, +1]` before weighting.

### 7. Observation Space

Observation vector `o(t) ∈ ℝ^{obs_dim}` where `obs_dim = 15 + N_types × 3`:

```
o(t) = [
    # Time features [0:5]
    month/12,  hour/23,  weekday/6,  sin(2π·h/24),  cos(2π·h/24),

    # Solar features [5:10]
    GHI/1200,  T_norm,  wind/20,  P_PV/P_PV_max,  P_PV/P_PV_max,

    # BESS features [10:12]
    SoC,  SoC_kwh/E_cap,

    # Grid features [12:15]
    P_grid/P_PV_max,  tariff/tariff_max,  α_grid/α_ref,

    # EV per type j [15 + j*3 : 15 + j*3 + 3]
    P_EV,j/P_EV,j_max,  Debt_j/P_EV,j_max,  EV_sat_j
]
```

This formulation follows **EV-GNN** (Nikolay et al., Nat. Commun. Eng. 2025): per-node feature
encoding with demand transferred, elapsed time, and satisfaction enables a GNN critic that is
size-invariant via mean-pooling — the same model weights apply to 10 or 1,000 EVs.

For Iquitos: `obs_dim = 15 + 2 × 3 = 21`.

### 8. Action Space

Continuous action `a(t) ∈ ℝ^{1 + N_types}`:

```
a(t) = [a_BESS, π_0, π_1, …, π_{N-1}]

a_BESS ∈ [-1, +1]:   -1 = max discharge (P_BESS_max),  +1 = max charge (P_BESS_max)
π_j    ∈ [0, 1]:      fraction of type-j EV demand to serve this hour
```

For Iquitos: `action_dim = 1 + 2 = 3`.

### 9. MDP Formulation

The control problem is a finite-horizon MDP `(S, A, P, R, γ)`:

- **State space** S: `o(t)` as defined above
- **Action space** A: continuous box as defined above
- **Transition** P: deterministic energy balance + stochastic EV arrivals
- **Reward** R: CO2_DUAL_FOCUS, discounted with `γ = 0.99`
- **Episode length**: 8,760 steps (one full year, hourly)

The SAC agent (Haarnoja et al., 2018) maximizes the entropy-regularized objective:

```
J(π) = Σ_t E_{(s,a)~ρ_π} [R(s,a,s') + α·H(π(·|s))]
```

where `α` is the temperature coefficient controlling exploration vs exploitation.

---

## Validated Results

| Metric | F₀ (no control) | F₁ (PV+BESS, no RL) | **F₂ SAC ep48** |
|--------|----------------|---------------------|-----------------|
| CO₂ (kg/año) | 7,054,000 | 5,790,639 | **2,622,735** |
| CO₂ reduction | — | 17.9% | **62.8%** |
| EV satisfaction | — | — | ≥ 0.94 |

**Statistical significance**: Kruskal-Wallis H = 81.65, p = 1.86 × 10⁻¹⁸ (SAC > PPO > A2C).

---

## References

1. Wali, S.B. et al. (2025). *xEV Hybrid Microgrid Energy Management via Deep RL*. IEEE STET.
2. Nikolay, A. et al. (2025). *Scalable EV Charging with Graph Neural Networks*. Nature Communications Engineering.
3. Vazquez-Canteli, J.R. et al. (2021). *CityLearn v1.3: Multi-Agent RL for Buildings*. Applied Energy.
4. Haarnoja, T. et al. (2018). *Soft Actor-Critic: Off-Policy Maximum Entropy Deep RL*. ICML.
5. MINEM/OSINERGMIN (2024). *Factor de emisión de CO₂ red aislada Loreto*. Peru.
6. IEC 62933-2-1 (2021). *Electrical energy storage systems — Unit parameters and testing methods for lithium-ion battery systems*.
