# AGENTS.md

## Cursor Cloud specific instructions

This is a Python 3 reinforcement-learning project (`pvbesscar`) that trains SAC/PPO/A2C
agents on real Iquitos OE2 data (solar PV, BESS, EV chargers, mall demand) to minimize
CO₂ from EV charging. It is a script-driven project — there is no long-running server
to keep up.

### Environment
- Dependencies are installed into a virtualenv at `.venv` by the startup update script.
  Use `.venv/bin/python` (or activate `.venv`).
- The update script installs a **curated working dependency set**, NOT `requirements.txt`.
  `requirements.txt` is a broken pip-freeze (e.g. `torch==2.10.0` does not exist,
  `torchvision==0.15.2` is incompatible, `pywinpty`/`iquitos-citylearn`/`librt`/
  `doe_xstock`/`NREL-PySAM` are Windows-only or unavailable). Do **not**
  `pip install -r requirements.txt`.
- System Python is 3.12 (project nominally targets 3.11); the code runs fine on 3.12.
  Do not run `pip install -e .` — its `requires-python = ">=3.11,<3.12"` pin rejects 3.12,
  and it is unnecessary (see PYTHONPATH below).
- `pandas` is pinned to 2.3.3 (pandas 3.x breaks the code). No GPU is present; training
  runs on CPU (≈580 timesteps/s; a full A2C run of 87,600 timesteps + validation
  finishes in ~2.5 min).

### CRITICAL: PYTHONPATH
Always run with both the repo root and `src/` on the path:
```
PYTHONPATH=/workspace:/workspace/src .venv/bin/python <script>
```
`src/agents/__init__.py` imports submodules as top-level modules
(e.g. `from dataset_builder_citylearn.rewards import ...`), so `src/` must be on
`PYTHONPATH` in addition to the repo root. (The `Dockerfile` sets the same
`PYTHONPATH=/app/src:/app`.) Always run scripts from the repo root — trainers use
relative data paths like `data/oe2/...`.

### Entry points (run / build)
The README references `ejecutar.py`, `demo_ejecucion.py`, and `compare_agents_complete.py`
which **do not exist** in the repo. The real training entry points are:
- `scripts/train/train_a2c_multiobjetivo.py`
- `scripts/train/train_ppo_multiobjetivo.py`
- `scripts/train/train_sac_multiobjetivo.py`

Each trains end-to-end and writes results/checkpoints to `outputs/<agent>_training/` and
`checkpoints/<AGENT>/` (plus KPI/dashboard PNGs). Episode count / timesteps are hardcoded
inside `main()` (A2C/PPO: 10 episodes × 8760 = 87,600 timesteps). The `citylearn` package
is optional — the trainers fall back to a self-contained Gymnasium env, so it is not
required.

### Lint / test
Canonical commands come from `.github/workflows/test-and-lint.yml`:
```
.venv/bin/pylint src/ --exit-zero
.venv/bin/flake8 src/ --max-line-length=120 --exit-zero
.venv/bin/black --check src/
```
CI runs all of these with `--exit-zero`/`|| true`; the repo currently has pre-existing
lint/format violations and a couple of files with syntax errors, so non-zero output is
expected. There is **no `tests/` directory** despite the `pytest` config in
`pyproject.toml`, so `pytest` collects nothing.
