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

<!-- markdownlint-disable MD013 -->
```bash
Cython.Compiler.Errors.CompileError: sklearn\linear_model\_cd_fast.pyx
```bash
<!-- markdownlint-enable MD013 -->

**Solution**: Use Python 3.11 exclusively.

---

## Installation Options

### Option 1: Download Python 3.11 from python.org (Recommended)

1. **Visit**: <https://www.python.org/downloads/release/python-3110/>
2. **Download**: "Windows installer (64-bit)" (e.g., `python-3.11.0-amd64.e...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

### Option 2: Use pyenv (Windows + Git Bash)

1. **Install pyenv-windows**:

<!-- markdownlint-disable MD013 -->
   ```bash
   # In PowerShell or Git Bash
   git clone https://github.com/pyenv-win/pyenv-win.git ~/.pyenv
```bash
<!-- markdownlint-enable MD013 -->

2. **Add to PATH** (PowerShell):

<!-- markdownlint-disable MD013 -->
   ```powershell
   [Environment]::SetEnvironmentVariable("PYENV", "$home\.pyenv\pyenv-win", "User")
   [Environment]::SetEnvironmentVariable("PATH", "$env:PYENV\bin;$env:PATH", "User")
```b...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

4. **Verify**:

<!-- markdownlint-disable MD013 -->
   ```bash
   python --version
   # Should output: Python 3.11.0
```bash
<!-- markdownlint-enable MD013 -->

---

### Option 3: Use pyenv with Chocolatey (Windows)

1. **Install Chocolatey** (if not installed):

<!-- markdownlint-disable MD013 -->
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::Secu...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

3. **Install Python 3.11**:

<!-- markdownlint-disable MD013 -->
   ```bash
   pyenv install 3.11.0
   pyenv global 3.11.0
```bash
<!-- markdownlint-enable MD013 -->

---

### Option 4: Fresh Virtual Environment with Python 3.11

Once Python 3.11 is installed:

<!-- markdownlint-disable MD013 -->
```bash
# Navigate to project
cd d:\diseñopvbesscar

# Delete old venv (if exists and using 3.13)
rmdir /s /q .venv

# Create new venv with Python 3.11
python3.11 -m venv .venv

...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## Verification

After installing Python 3.11 and creating `.venv`:

<!-- markdownlint-disable MD013 -->
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
<!-- markdownlint-enable MD013 -->

---

## Phase ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

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

<!-- markdownlint-disable MD013 -->
```bash
# Verify active Python
python --version
# If 3.13, activate .venv:
.venv\Scripts\activate
# Re-run: python --version (should be 3.11)
```bash
<!-- markdownlint-enable MD013 -->

### Cython compilation errors during pip install

**Cause**: Using Python 3.13 (scikit-learn incompatible)

**Solution**: Use Python 3.11 (guaranteed compatibility)

---

## Project Configuration (Already Done ✅)

The foll...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

4. **Build CityLearn dataset**:

<!-- markdownlint-disable MD013 -->
   ```bash
   python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```bash
<!-- markdownlint-enable MD013 -->

5. **Test agent training**:

<!-- markdownlint-disable MD013 -->
   ```bash
   python scripts/train_quick.py --episodes 1
```bash
<!-- markdownlint-enable MD013 -->

6. **Commit**:

<!-- markdownlint-disable MD013 -->
   ```bash
   git add -A
   git commit -m "feat: Phase 6-7 complete - OE2->OE3 integration with Python 3.11"
```bash
<!-- markdownlint-enable MD013 -->

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
