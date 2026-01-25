# Python 3.11 Setup Guide for pvbesscar

## ⚠️ CRITICAL: Project Requires Python 3.11 ONLY

**Current Status**:

- System Python: 3.13.9 (installed)
- Project Configuration: 3.11 only (specified in `pyproject.toml`, `setup.py`,
  - `.python-version`)
- Issue: CityLearn (via scikit-learn) **FAILS** to compile on Python 3.13 with
  - Cython errors

## Problem

scikit-learn fails to build on Python 3.13.9 due to Cython compilation errors:

```bash
Cython.Compiler.Errors.CompileError: sklearn\linear_model\_cd_fast.pyx
```bash

**Solution**: Use Python 3.11 exclusively.

---

## Installation Options

### Option 1: Download Python 3.11 from python.org (Recommended)

1. **Visit**: <https://www.python.org/downloads/release/python-3110/>
2. **Download**: "Windows installer (64-bit)" (e.g., `python-3.11.0-amd64.exe`)
3. **Install**:
   - Run installer
   - ✅ Check: **Add python.exe to PATH**
   - ✅ Check: **Install for all users** (optional but recommended)
   - Complete installation

4. **Verify**:

   ```bash
   python3.11 --version
   # Should output: Python 3.11.0 (or similar 3.11.x)
```bash

---

### Option 2: Use pyenv (Windows + Git Bash)

1. **Install pyenv-windows**:

   ```bash
   # In PowerShell or Git Bash
   git clone https://github.com/pyenv-win/pyenv-win.git ~/.pyenv
```bash

2. **Add to PATH** (PowerShell):

   ```powershell
   [Environment]::SetEnvironmentVariable("PYENV", "$home\.pyenv\pyenv-win", "User")
   [Environment]::SetEnvironmentVariable("PATH", "$env:PYENV\bin;$env:PATH", "User")
```bash

3. **Install Python 3.11**:

   ```bash
   pyenv install 3.11.0
   pyenv global 3.11.0
```bash

4. **Verify**:

   ```bash
   python --version
   # Should output: Python 3.11.0
```bash

---

### Option 3: Use pyenv with Chocolatey (Windows)

1. **Install Chocolatey** (if not installed):

   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
   iex ((New-Object System.Net.WebClient).DownloadString('[url0]))
```bash

2. **Install pyenv**:

   ```bash
   choco install pyenv-win
```bash

3. **Install Python 3.11**:

   ```bash
   pyenv install 3.11.0
   pyenv global 3.11.0
```bash

---

### Option 4: Fresh Virtual Environment with Python 3.11

Once Python 3.11 is installed:

```bash
# Navigate to project
cd d:\diseñopvbesscar

# Delete old venv (if exists and using 3.13)
rmdir /s /q .venv

# Create new venv with Python 3.11
python3.11 -m venv .venv

# Activate
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Verify Python version
python --version  # Should show 3.11.x

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-training.txt
```bash

---

## Verification

After installing Python 3.11 and creating `.venv`:

```bash
# Activate venv
.venv\Scripts\activate

# Check Python version
python --version
# Output: Python 3.11.x (where x >= 0)

# Check critical packages
python -c "import pandas,
    numpy,
    stable_baselines3,
    gymnasium; print('✅ All packages OK')"

# Check CityLearn specifically
python -c "import citylearn; print('✅ CityLearn installed')"
```bash

---

## Phase 7 Execution with Python 3.11

Once Python 3.11 is configured:

```bash
# Activate venv (2)
.venv\Scripts\activate

# Run Phase 7 tests
python phase7_test_pipeline.py

# Expected output:
# ✅ All tests passed!
# NEXT STEPS:
#   1. Run: python -m scripts.run_oe3_build_dataset --config configs/default.yaml
#   2. Test agent training: python scripts/train_quick.py --episodes 1
#   3. Commit changes
```bash

---

## Troubleshooting

### "Python 3.11 not found"

**Solution**:

- Ensure Python 3.11 installer ran with "Add to PATH" checked
- Restart terminal/IDE after installation
- Use `where python3.11` to verify path

### "ModuleNotFoundError: No module named 'citylearn'"

**Cause**: Using wrong Python environment (3.13 instead of 3.11)

**Solution**:

```bash
# Verify active Python
python --version
# If 3.13, activate .venv:
.venv\Scripts\activate
# Re-run: python --version (should be 3.11)
```bash

### Cython compilation errors during pip install

**Cause**: Using Python 3.13 (scikit-learn incompatible)

**Solution**: Use Python 3.11 (guaranteed compatibility)

---

## Project Configuration (Already Done ✅)

The following files have been updated to enforce Python 3.11:

- ✅ `.python-version` - Created with "3.11.0"
- ✅ `pyproject.toml` - requires-python = ">=3.11,<3.12"
- ✅ `setup.py` - python_requires = ">=3.11,<3.12"
- ✅ `.github/workflows/test-and-lint.yml` - python-version: ["3.11"]
- ✅ `scripts/analysis/EJECUTAR_OPCION_4_INFRAESTRUCTURA.py` - Classifiers
  - updated

---

## Next Steps

1. **Install Python 3.11** (using one of the 4 options above)
2. **Create fresh virtual environment** with Python 3.11
3. **Run Phase 7 tests**:

   ```bash
   python phase7_test_pipeline.py
```bash

4. **Build CityLearn dataset**:

   ```bash
   python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```bash

5. **Test agent training**:

   ```bash
   python scripts/train_quick.py --episodes 1
```bash

6. **Commit**:

   ```bash
   git add -A
   git commit -m "feat: Phase 6-7 complete - OE2->OE3 integration with Python 3.11"
```bash

---

## References

- **Python 3.11 Downloads**:
  - <https://www.python.org/downloads/release/python-3110/>
- **pyenv-win**: <https://github.com/pyenv-win/pyenv-win>
- **Chocolatey**: <https://chocolatey.org/>
- **Project README**: [README.md](README.md)
- **Copilot Instructions**:
  - [.github/copilot-instructions.md](.github/copilot-instructions.md)

---

**Last Updated**: 2026-01-24  
**Status**: Phase 7 - Awaiting Python 3.11 Installation
